"""MatcherAgent — donation -> need matching (as-tool).  Spec: §8.2.  Phase: P2.2 / P3.5.

Task-type: donation_match (cap L1 — supervised: auto-match but notify + undo window).
Prioritizes perishable items by expiry; escalates when it can't place a perishable in time.
Uses the HARD model for ambiguous matches. Tools: sheets, twilio.
"""
from __future__ import annotations

MATCHER_PROMPT = """You match incoming in-kind/perishable donations to local needs before spoilage.
Prioritize by expiry window and priority. If you cannot place a perishable item within its window,
or you are not confident, escalate to the coordinator with a crisp decision instead of guessing.
"""


def matcher_agent(query: str) -> str:
    """Agents-as-Tools wrapper. P2.2."""
    raise NotImplementedError("P2.2")
