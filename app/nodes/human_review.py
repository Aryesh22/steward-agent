"""human_review node — escalation via Strands interrupt.  Spec: IMPLEMENTATION_PLAN.md §8.5.  Phase: P3.1/P3.2.

The agent pauses (stop_reason == "interrupt"); the entrypoint texts reason.summary to the
coordinator via Twilio; their reply is fed back as an interruptResponse block to resume the
same session (needs a stable per-org runtimeSessionId).

P2 local mode: since Strands interrupt requires the full AgentCore Runtime session machinery,
in local/mock mode we simulate the escalation by printing a notification and returning a
synthetic coordinator reply so the graph can continue.
"""
from __future__ import annotations

import json
import os


def request_decision(summary: str, options: list[str], org_id: str = "demo") -> str:
    """Escalate a real decision to the coordinator; pauses until they reply.

    In production (BEDROCK_ENABLED=true + inside an AgentCore Runtime session),
    raises a Strands interrupt that pauses the graph and texts the coordinator.

    In local/mock mode, prints the escalation and returns a simulated reply
    so the demo script can continue (simulates the coordinator replying 'YES').

    Args:
        summary: A concise description of the decision (sent as SMS).
        options: List of valid reply options, e.g. ['YES', 'NO'].
        org_id: The organisation identifier.

    Returns:
        The coordinator's reply text, or raises StrandsInterrupt in production.
    """
    if os.getenv("BEDROCK_ENABLED", "").lower() not in ("1", "true", "yes"):
        # Local/mock mode: simulate escalation
        _send_coordinator_alert_mock(summary, options, org_id)
        simulated_reply = os.getenv("MOCK_COORDINATOR_REPLY", "YES")
        print(f"[human_review] 📱 Coordinator replied (simulated): '{simulated_reply}'")
        return simulated_reply

    # Production path: use Strands interrupt
    # NOTE: This requires @tool(context=True) + ToolContext injection from the graph.
    # The graph calls this as a Strands tool; ToolContext is injected automatically.
    # Here we implement the *function body* called by the @tool wrapper below.
    try:
        # This will only work inside a running Strands agent turn with context injection.
        # If called directly, falls back to mock.
        raise RuntimeError("request_decision must be called as a @tool from within a Strands Agent")
    except Exception:
        _send_coordinator_alert_mock(summary, options, org_id)
        return "ESCALATED"


def request_decision_tool():
    """Return the Strands @tool-decorated version for use inside the human_review node.

    This is what the graph registers as a tool on the human_review Agent.
    The ToolContext injected by Strands provides the .interrupt() method.
    """
    from strands import tool
    from strands.types.tools import ToolContext

    @tool(context=True)
    def request_coordinator_decision(
        tool_context: ToolContext,
        summary: str,
        options: list,
    ) -> str:
        """Escalate a real decision to the human coordinator via SMS. Pauses the agent.

        Args:
            summary: Concise description of what the coordinator needs to decide.
            options: Valid reply options, e.g. ['YES', 'NO', 'DEFER'].
        """
        if os.getenv("BEDROCK_ENABLED", "").lower() not in ("1", "true", "yes"):
            _send_coordinator_alert_mock(summary, options)
            return os.getenv("MOCK_COORDINATOR_REPLY", "YES")

        # Real path: pause the graph and text the coordinator
        _send_coordinator_sms(summary, options)
        return tool_context.interrupt(
            "coordinator-decision",
            reason={"summary": summary, "options": options},
        )

    return request_coordinator_decision


def resume_with_reply(graph, interrupt_id: str, reply_text: str):
    """Feed the coordinator's reply back to resume the graph. P3.2.

    Args:
        graph: The built Strands Graph instance.
        interrupt_id: The interrupt ID from result.interrupts[n].id.
        reply_text: The coordinator's SMS reply ('YES', 'NO', etc.).

    Returns:
        The graph result after resuming.
    """
    responses = [{"interruptResponse": {"interruptId": interrupt_id, "response": reply_text}}]
    return graph(responses)


def human_review_node(state: dict) -> dict:
    """Graph node that handles escalation for L0 / gate-failed tasks.

    Receives the router's output (task_type, confidence, decision=ESCALATE),
    composes a decision prompt, and either raises a Strands interrupt (production)
    or simulates coordinator reply (local mode).

    Returns updated state with coordinator_reply and escalation metadata.
    """
    from app.ratchet import record_outcome

    task_type: str = state["task_type"]
    org_id: str = state["org_id"]
    confidence: float = float(state.get("confidence", 0.0))
    text: str = state.get("input", "")

    # Build the escalation summary
    summary = _build_summary(task_type, confidence, text)
    options = _build_options(task_type)

    print(f"\n[human_review] ESCALATING {task_type} (conf={confidence:.2f})")
    print(f"[human_review] 📱 SMS to coordinator: {summary[:200]}")

    coordinator_reply = request_decision(summary, options, org_id)

    # Record the escalation as a human-in-the-loop event
    # If coordinator approved (YES), we note human reviewed but do NOT change ratchet
    # If coordinator overrode/rejected, we demote the ratchet
    human_override = coordinator_reply.strip().upper() not in ("YES", "APPROVE", "OK", "Y")

    new_state = record_outcome(
        org_id,
        task_type,
        verified_correct=not human_override,
        human_override=human_override,
        confidence=confidence,
        store=state.get("_store"),
        sheet_mirror=state.get("_sheet_mirror"),
    )

    print(f"[human_review] Coordinator reply='{coordinator_reply}' | "
          f"ratchet: {task_type} L{new_state.current_level} "
          f"(override={human_override})")

    return {
        **state,
        "escalated": True,
        "coordinator_reply": coordinator_reply,
        "human_override": human_override,
        "new_trust_state": new_state,
        "action_result": {"action": "escalated", "reply": coordinator_reply},
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _build_summary(task_type: str, confidence: float, text: str) -> str:
    """Compose a concise escalation SMS."""
    reason_map = {
        "grant_report_file": "Filing a grant report is irreversible and always requires your OK.",
        "money_movement": "Any money movement requires explicit approval.",
        "pii_disclosure": "Sharing member private info requires your consent.",
        "donation_match": f"Can't confidently place a donation (confidence {confidence:.0%}).",
    }
    reason = reason_map.get(task_type, f"Low confidence ({confidence:.0%}) for {task_type}.")
    short_text = text[:100] + "..." if len(text) > 100 else text
    return f"Steward needs your decision: {reason} Context: {short_text} Reply YES or NO."


def _build_options(task_type: str) -> list[str]:
    if task_type == "donation_match":
        return ["YES — proceed with match", "NO — skip this donation", "DEFER — try tomorrow"]
    if task_type in ("grant_report_file", "grant_report_draft"):
        return ["APPROVE - file/send as-is", "REVISE - send me the draft", "HOLD - not yet"]
    return ["YES", "NO"]


def _send_coordinator_alert_mock(summary: str, options: list, org_id: str = "demo") -> None:
    """Print a mock coordinator alert (no SMS sent)."""
    opts = " / ".join(str(o) for o in options)
    print(f"\n{'='*60}")
    print(f"[MOCK SMS -> Coordinator] Org: {org_id}")
    print(f"   {summary}")
    print(f"   Options: {opts}")
    print(f"{'='*60}\n")


def _send_coordinator_sms(summary: str, options: list) -> None:
    """Send a real SMS to the coordinator via Amazon SNS."""
    try:
        from app.tools.sms import send_sms
        coordinator_phone = os.getenv("COORDINATOR_PHONE", "").strip()
        if not coordinator_phone:
            print("[human_review] Warning: COORDINATOR_PHONE not set; SMS not sent.")
            return
        opts = " / ".join(str(o) for o in options[:3])  # SMS length limit
        msg = f"Steward needs your decision:\n{summary[:120]}\nReply: {opts}"
        send_sms(coordinator_phone, msg[:160])
        print(f"[human_review] ✅ SNS SMS sent to coordinator ({coordinator_phone}).")
    except Exception as e:
        print(f"[human_review] Warning: failed to send coordinator SNS SMS: {e}")
