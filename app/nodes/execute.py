"""Execute node — dispatch to the right specialist (as-tool).  Spec: §8.3.  Phase: P2.4.

Chooses recruiter/matcher/grant based on task_type, applies the level semantics:
  L1 SUPERVISED → execute + notify coordinator + start undo window
  L2 AUTONOMOUS → execute silently
(L0 never reaches here — it routes to human_review.)

State shape expected:
  state["org_id"]     str
  state["task_type"]  str
  state["confidence"] float
  state["input"]      str  — the original text/payload
  state["decision"]   str  — ESCALATE | AUTO_NOTIFY | AUTO_SILENT (from ratchet)
"""
from __future__ import annotations

import json
import time


# Map task_type → specialist function name
_RECRUITER_TASKS = {"volunteer_reminder", "shift_backfill"}
_MATCHER_TASKS = {"donation_match"}
_GRANT_TASKS = {"grant_deadline_alert", "grant_report_draft", "grant_report_file"}


def execute_node(state: dict) -> dict:
    """Dispatch to the correct specialist and apply level semantics.

    Returns the updated state with an 'action_result' key added.
    """
    from app.ratchet import AUTO_NOTIFY, AUTO_SILENT, decision_for, record_outcome
    from app.agents.reviewer import review_action

    task_type: str = state["task_type"]
    org_id: str = state["org_id"]
    confidence: float = float(state.get("confidence", 0.7))
    text: str = state.get("input", "")
    decision: str = state.get("decision", AUTO_NOTIFY)

    # --- 1. Call the right specialist ---
    result_str = _dispatch(task_type, text)
    try:
        result_data = json.loads(result_str)
    except (json.JSONDecodeError, ValueError):
        result_data = {"raw": result_str}

    print(f"\n[execute] task={task_type} | decision={decision} | result={result_str[:120]}...")

    # --- 2. Apply level semantics ---
    if decision == AUTO_NOTIFY:
        # L1 SUPERVISED: notify coordinator of what was done (SMS in production)
        _notify_l1(org_id, task_type, result_data)
        # Start undo window (in production: set a timer in DynamoDB + allow SMS undo)
        # For local demo: record the undo-window start time
        result_data["undo_window_started_at"] = time.time()
        print(f"[execute] L1 SUPERVISED: notified coordinator; undo window open 15 min.")
    elif decision == AUTO_SILENT:
        # L2 AUTONOMOUS: execute silently, audit-logged only
        print(f"[execute] L2 AUTONOMOUS: action executed silently.")

    # --- 3. ReviewerAgent verification ---
    verdict = review_action({
        "task_type": task_type,
        "action_result": result_data,
        "context": text,
    })
    print(f"[execute] reviewer: correct={verdict['correct']} conf={verdict['confidence']:.2f} "
          f"reason={verdict['reason'][:80]}")

    # --- 4. Record outcome → ratchet update ---
    new_state = record_outcome(
        org_id,
        task_type,
        verified_correct=verdict["correct"],
        human_override=False,
        confidence=confidence,
        store=state.get("_store"),          # injected by the graph or demo script
        sheet_mirror=state.get("_sheet_mirror"),
    )
    print(f"[execute] ratchet: {task_type} now L{new_state.current_level} "
          f"(counter={new_state.consecutive_verified_correct}/{_promotion_threshold()})")

    return {
        **state,
        "action_result": result_data,
        "reviewer_verdict": verdict,
        "new_trust_state": new_state,
    }


def _dispatch(task_type: str, text: str) -> str:
    """Call the appropriate specialist agent."""
    if task_type in _RECRUITER_TASKS:
        from app.agents.recruiter import recruiter_agent
        return recruiter_agent(f"task={task_type} | {text}")

    if task_type in _MATCHER_TASKS:
        from app.agents.matcher import matcher_agent
        return matcher_agent(f"task={task_type} | {text}")

    if task_type in _GRANT_TASKS:
        from app.agents.grant import grant_agent
        return grant_agent(f"task={task_type} | {text}")

    # Unknown task_type — safe no-op
    return json.dumps({"action": "unknown_task_type", "task_type": task_type})


def _notify_l1(org_id: str, task_type: str, result: dict) -> None:
    """Send a coordinator notification for L1 SUPERVISED actions.

    In production: sends an SMS via Twilio with action details + undo instructions.
    In local/mock mode: just prints.
    """
    import os
    if os.getenv("BEDROCK_ENABLED", "").lower() not in ("1", "true", "yes"):
        print(f"[L1-notify] Coordinator alert: {task_type} executed. "
              f"Reply UNDO within 15 min to reverse. Details: {str(result)[:100]}")
        return

    # Production path: SMS the coordinator
    try:
        from app.tools.twilio import send_sms
        coordinator_phone = os.getenv("COORDINATOR_PHONE", "")
        if coordinator_phone:
            action = result.get("action", "action taken")
            notes = result.get("notes", "")
            msg = (
                f"Steward [{org_id}] AUTO-{task_type.upper()}: {action}. "
                f"{notes} Reply UNDO within 15 min to reverse."
            )
            send_sms(coordinator_phone, msg[:160])
    except Exception as e:
        print(f"[L1-notify] Warning: could not send coordinator SMS: {e}")


def _promotion_threshold() -> int:
    from app.ratchet import promotion_threshold
    return promotion_threshold()
