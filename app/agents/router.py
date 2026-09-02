"""Router / orchestrator agent.  Spec: IMPLEMENTATION_PLAN.md §8.2.  Phase: P2.1.

Classifies an incoming task into a `task_type` (one of the §3.2 keys) and emits a
confidence in [0,1]. Pulls org context from AgentCore Memory (P4). Uses the CHEAP model.
"""
from __future__ import annotations

ROUTER_PROMPT = """You are Steward's router for an all-volunteer community org.
Classify the input into exactly one task_type from:
  volunteer_reminder, shift_backfill, grant_deadline_alert, donation_match,
  grant_report_draft, grant_report_file, money_movement, pii_disclosure.
Return the task_type and a confidence in [0,1]. Never invent a task_type outside this list.
"""


def build_router(model=None):  # noqa: ANN001
    """Return the router Strands Agent. P2.1."""
    raise NotImplementedError("P2.1")
