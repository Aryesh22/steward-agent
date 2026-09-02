"""GrantAgent — deadline alert / report draft / report file (as-tool).  Spec: §8.2.  Phase: P2.2.

Task-types: grant_deadline_alert (cap L2), grant_report_draft (cap L1),
grant_report_file (cap L0 — ALWAYS asks, irreversible). Uses the HARD model for drafting.
"""
from __future__ import annotations

GRANT_PROMPT = """You track grant deadlines, draft post-award reports from the org's records, and
prepare filings. You NEVER submit a report without explicit human approval (filing is irreversible).
"""


def grant_agent(query: str) -> str:
    """Agents-as-Tools wrapper. P2.2."""
    raise NotImplementedError("P2.2")
