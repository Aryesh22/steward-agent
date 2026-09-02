"""human_review node — escalation via Strands interrupt.  Spec: IMPLEMENTATION_PLAN.md §8.5.  Phase: P3.1/P3.2.

The agent pauses (stop_reason == "interrupt"); the entrypoint texts reason.summary to the
coordinator via Twilio; their reply is fed back as an interruptResponse block to resume the
same session (needs a stable per-org runtimeSessionId).
"""
from __future__ import annotations


def request_decision(summary: str, options: list[str]):
    """Raise a Strands interrupt asking the coordinator to decide. P3.1.

    Real implementation (needs @tool(context=True) + ToolContext):
        return tool_context.interrupt("coordinator-decision",
                                      reason={"summary": summary, "options": options})
    """
    raise NotImplementedError("P3.1")


def resume_with_reply(graph, interrupt_id: str, reply_text: str):  # noqa: ANN001
    """Feed the coordinator's reply back to resume the graph. P3.2."""
    raise NotImplementedError("P3.2")
    # responses = [{"interruptResponse": {"interruptId": interrupt_id, "response": reply_text}}]
    # return graph(responses)
