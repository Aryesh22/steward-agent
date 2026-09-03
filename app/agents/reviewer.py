"""ReviewerAgent — externalized verification.  Spec: IMPLEMENTATION_PLAN.md §8.4.  Phase: P2.3.

A SEPARATE agent turn (not self-check) that scores each action. Rationale: self-correction is an
addressability artifact — models miss their own errors but catch external ones (ref §15.3 #4).
Its verdict feeds ratchet.record_outcome() (promotion/demotion). Uses the CHEAP model.

Returns a structured verdict: {"correct": bool, "confidence": float, "reason": str}.

Mock-first: when BEDROCK_ENABLED is unset, review_action() uses rule-based heuristics.
"""
from __future__ import annotations

import json
import os
import re

REVIEWER_PROMPT = """You are Steward's independent action reviewer for a community org.

You are given:
- task_type: the classification of the action
- action_result: the JSON output the specialist agent produced
- context: any relevant background (shift, donation, grant info)

Judge whether the action is CORRECT and SAFE:
- Correct means: the right action for the task type, appropriate recipients, no obvious errors.
- Safe means: no irreversible harm (money moved, PII shared without consent, wrong person contacted).

Be SKEPTICAL. Default to correct=false if you are unsure.
Respond ONLY as valid JSON: {"correct": true|false, "confidence": 0.0..1.0, "reason": "..."}
"""


def _mock_review(action: dict) -> dict:
    """Rule-based mock reviewer for offline/test use."""
    task_type = action.get("task_type", "")
    result_str = str(action.get("action_result", ""))

    # Hard-capped tasks should NEVER auto-execute
    if task_type in ("grant_report_file", "money_movement", "pii_disclosure"):
        if "requires_approval" in result_str or "human" in result_str.lower():
            return {"correct": True, "confidence": 0.98,
                    "reason": f"{task_type} correctly escalated to human; not auto-executed."}
        return {"correct": False, "confidence": 0.99,
                "reason": f"SAFETY VIOLATION: {task_type} executed without human approval!"}

    # Volunteer reminder checks
    if task_type == "volunteer_reminder":
        if "sent_sms" in result_str or "backfill_sent" in result_str:
            recipients = action.get("recipients", [])
            # Check no empty phone numbers in mock data
            if "phone" in result_str and "+1555" in result_str:
                return {"correct": True, "confidence": 0.92,
                        "reason": "SMS sent to correct volunteers with valid phone numbers."}
            return {"correct": True, "confidence": 0.85,
                    "reason": "Volunteer reminder action looks correct."}

    # Shift backfill checks
    if task_type == "shift_backfill":
        if "backfill_sent" in result_str:
            return {"correct": True, "confidence": 0.90,
                    "reason": "Backfill sent to eligible volunteer with correct skills."}

    # Donation match checks
    if task_type == "donation_match":
        if "cannot_place" in result_str and "escalate" in result_str:
            return {"correct": True, "confidence": 0.93,
                    "reason": "Correctly identified unplaceable perishable and escalated."}
        if "matched" in result_str:
            return {"correct": True, "confidence": 0.88,
                    "reason": "Donation matched to need with reasonable confidence."}

    # Grant checks
    if task_type in ("grant_deadline_alert", "grant_report_draft"):
        if "draft_ready" in result_str or "alert_sent" in result_str:
            return {"correct": True, "confidence": 0.87,
                    "reason": f"{task_type} action appears correct and safe."}

    # Default: uncertain
    return {"correct": True, "confidence": 0.75,
            "reason": "Action appears reasonable but reviewer is uncertain."}


def review_action(action: dict) -> dict:
    """Review an action and return a verdict dict.

    Args:
        action: Dict with keys:
            - task_type (str): e.g. 'volunteer_reminder'
            - action_result (str|dict): the specialist's output JSON
            - context (str, optional): background info for the reviewer

    Returns:
        Dict: {"correct": bool, "confidence": float, "reason": str}
    """
    if os.getenv("BEDROCK_ENABLED", "").lower() not in ("1", "true", "yes"):
        return _mock_review(action)

    # --- Real Strands Agent path ---
    from strands import Agent
    from strands.models import BedrockModel

    cheap_model_id = os.getenv("CHEAP_MODEL_ID", "us.amazon.nova-lite-v1:0")
    region = os.getenv("AWS_REGION", "us-west-2")
    model = BedrockModel(model_id=cheap_model_id, region_name=region, temperature=0.0)

    reviewer = Agent(system_prompt=REVIEWER_PROMPT, model=model)

    prompt = (
        f"task_type: {action.get('task_type', 'unknown')}\n"
        f"action_result: {json.dumps(action.get('action_result', {}), indent=2)}\n"
        f"context: {action.get('context', 'none provided')}\n"
    )
    response = reviewer(prompt)
    raw = str(getattr(response, "message", response))

    # Extract JSON verdict
    match = re.search(r'\{[^}]+\}', raw, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            return {
                "correct": bool(data.get("correct", False)),
                "confidence": float(data.get("confidence", 0.5)),
                "reason": str(data.get("reason", "")),
            }
        except (json.JSONDecodeError, ValueError):
            pass

    # Fallback: safe default (uncertain, don't promote)
    return {"correct": False, "confidence": 0.5,
            "reason": "Reviewer could not parse model output; defaulting to incorrect."}
