"""RecruiterAgent — volunteer confirm + backfill (as-tool).  Spec: §8.2.  Phase: P2.2.

Task-types: volunteer_reminder (3-touch SMS), shift_backfill (text next-eligible when one drops).
Both cap at L2 (fast graduation). Uses the CHEAP model. Tools: sheets, twilio.
"""
from __future__ import annotations

RECRUITER_PROMPT = """You are Steward's volunteer coordinator. Confirm shifts using a polite
3-touch SMS sequence, and when a volunteer drops, text the next eligible volunteer to backfill.
Be concise and friendly. Never contact the same person more than the sequence allows.
"""


def recruiter_agent(query: str) -> str:
    """Agents-as-Tools wrapper. P2.2."""
    raise NotImplementedError("P2.2")
