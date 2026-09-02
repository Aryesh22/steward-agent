"""ReviewerAgent — externalized verification.  Spec: IMPLEMENTATION_PLAN.md §8.4.  Phase: P2.3.

A SEPARATE agent turn (not self-check) that scores each action. Rationale: self-correction is an
addressability artifact — models miss their own errors but catch external ones (ref §15.3 #4).
Its verdict feeds ratchet.record_outcome() (promotion/demotion). Uses the CHEAP model.

Returns a structured verdict: {"correct": bool, "confidence": float, "reason": str}.
"""
from __future__ import annotations

REVIEWER_PROMPT = """You are an independent reviewer. You are given an action Steward took (or proposes),
its inputs, and its result. Judge whether it is correct and safe. Be skeptical; default to correct=false
if you are unsure. Respond ONLY as JSON: {"correct": bool, "confidence": 0..1, "reason": "..."}.
"""


def review_action(action: dict) -> dict:
    """Return the verdict dict. P2.3."""
    raise NotImplementedError("P2.3")
