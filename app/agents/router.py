"""Router / orchestrator agent.  Spec: IMPLEMENTATION_PLAN.md §8.2.  Phase: P2.1.

Classifies an incoming task into a `task_type` (one of the §3.2 keys) and emits a
confidence in [0,1]. Pulls org context from AgentCore Memory (P4). Uses the CHEAP model.

Mock-first: when BEDROCK_ENABLED env var is unset, classify() uses keyword heuristics so
the entire graph can run offline without AWS credentials (good for tests + local demo).
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

ROUTER_PROMPT = """You are Steward's router for an all-volunteer community org.
Given the input text, classify it into EXACTLY ONE task_type from this list:
  volunteer_reminder   - confirming/reminding volunteers about upcoming shifts
  shift_backfill       - finding a replacement when a volunteer drops out
  grant_deadline_alert - alerting about an upcoming grant report deadline
  donation_match       - matching an incoming donation to a local need
  grant_report_draft   - drafting a grant progress/final report
  grant_report_file    - submitting/filing a completed grant report to a funder
  money_movement       - anything involving real financial transactions
  pii_disclosure       - revealing a member's private info to a third party

Respond ONLY with valid JSON: {"task_type": "<one of the above>", "confidence": <0.0..1.0>}
Never invent a task_type outside this list.
"""

# Ordered keyword map for the mock classifier (first match wins).
_KEYWORD_MAP: list[tuple[list[str], str, float]] = [
    (["submit", "file", "filing", "send the report"], "grant_report_file", 0.92),
    (["draft report", "write report", "grant report"], "grant_report_draft", 0.88),
    (["grant deadline", "report due", "upcoming deadline"], "grant_deadline_alert", 0.90),
    (["money", "payment", "transfer", "funds", "invoice"], "money_movement", 0.95),
    (["private", "personal", "address", "pii", "member info"], "pii_disclosure", 0.90),
    (["donate", "donation", "donated", "lbs of", "cans of", "milk", "food drop"], "donation_match", 0.85),
    (["backfill", "replacement", "dropped", "can't make", "cannot make", "cover the shift"], "shift_backfill", 0.87),
    (["remind", "confirm", "reminder", "shift tomorrow", "shift today", "volunteer"], "volunteer_reminder", 0.80),
]


def _mock_classify(text: str) -> "RouterResult":
    """Keyword-heuristic classifier used when Bedrock is unavailable."""
    lower = text.lower()
    for keywords, task_type, confidence in _KEYWORD_MAP:
        if any(kw in lower for kw in keywords):
            return RouterResult(task_type=task_type, confidence=confidence)
    return RouterResult(task_type="volunteer_reminder", confidence=0.55)


@dataclass
class RouterResult:
    task_type: str
    confidence: float


def classify(text: str, org_id: str = "demo") -> RouterResult:
    """Classify *text* into a task_type + confidence.

    Uses the Strands Router Agent when BEDROCK_ENABLED=true, otherwise falls
    back to the mock keyword classifier so the graph runs fully offline.

    Args:
        text: the input text (an SMS body, a sweep trigger description, etc.)
        org_id: the organisation identifier (used for Memory retrieval in P4)

    Returns:
        RouterResult with task_type and confidence in [0,1].
    """
    if os.getenv("BEDROCK_ENABLED", "").lower() not in ("1", "true", "yes"):
        return _mock_classify(text)

    # --- Real Strands Agent path (requires AWS creds + model access) ---
    router = _get_router_agent()
    response = router(f"Org: {org_id}\n\nInput: {text}")
    raw = str(getattr(response, "message", response))
    # Extract the first JSON object from the response
    match = re.search(r'\{[^}]+\}', raw)
    if match:
        try:
            data = json.loads(match.group())
            return RouterResult(
                task_type=str(data.get("task_type", "volunteer_reminder")),
                confidence=float(data.get("confidence", 0.7)),
            )
        except (json.JSONDecodeError, ValueError):
            pass
    # Fallback if the model returns garbage
    return _mock_classify(text)


def _get_router_agent():
    """Build (and cache) the Strands router Agent. Imported lazily."""
    from strands import Agent
    from strands.models import BedrockModel

    cheap_model_id = os.getenv("CHEAP_MODEL_ID", "us.amazon.nova-lite-v1:0")
    region = os.getenv("AWS_REGION", "us-west-2")
    model = BedrockModel(model_id=cheap_model_id, region_name=region, temperature=0.0)
    return Agent(system_prompt=ROUTER_PROMPT, model=model)


def build_router(model=None):  # noqa: ANN001
    """Return the router Strands Agent (for embedding in an orchestrator). P2.1."""
    from strands import Agent

    if model is None:
        from strands.models import BedrockModel
        cheap_model_id = os.getenv("CHEAP_MODEL_ID", "us.amazon.nova-lite-v1:0")
        region = os.getenv("AWS_REGION", "us-west-2")
        model = BedrockModel(model_id=cheap_model_id, region_name=region, temperature=0.0)

    return Agent(system_prompt=ROUTER_PROMPT, model=model)
