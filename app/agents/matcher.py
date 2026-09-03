"""MatcherAgent — donation → need matching (as-tool).  Spec: §8.2.  Phase: P2.2 / P3.5.

Task-type: donation_match (cap L1 — supervised: auto-match but notify + undo window).
Prioritizes perishable items by expiry; escalates (returns low confidence) when it can't
place a perishable item in time.

Mock-first: when BEDROCK_ENABLED is unset, matcher_agent() returns a realistic fake result
so the graph and local demo run offline.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

MATCHER_PROMPT = """You are Steward's donation coordinator for a small community org.

Match incoming in-kind / perishable donations to open local needs. Follow these rules:
- Read the Donations tab for items with status='new'.
- Read the Needs tab for open needs (status='open').
- Match by item type and quantity. Prioritize perishable items by expiry (nearest first).
- If a perishable item CANNOT be placed within its expiry window, or you are < 70% confident
  in any match, set can_place=false — Steward will escalate to the coordinator.
- Update Donations.status to 'matched' and record matched_need_id.
- Return JSON: {
    "action": "matched"|"cannot_place"|"no_donations",
    "matches": [{"donation_id":..., "need_id":..., "item":..., "confidence":..., "notes":...}],
    "unplaced": [{"donation_id":..., "item":..., "reason":...}],
    "escalate": bool,
    "escalation_summary": "..." // human-readable, only if escalate=true
  }
"""


def _days_until(date_str: str) -> float:
    """Parse ISO date and return days until expiry (negative = expired)."""
    try:
        expiry = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return (expiry - now).total_seconds() / 86400
    except (ValueError, TypeError):
        return 999.0  # non-perishable / no expiry


def _mock_result(query: str) -> str:
    """Return a realistic fake match result for offline/test use."""
    # Simulate the milk donation scenario from seed_sheet.py
    # milk (d1): 40lbs, perishable, expires 2026-09-11 → matches need n1 (milk, North shelter)
    # Check if query mentions perishable or milk
    lower = query.lower()
    if "milk" in lower or "perishable" in lower or "cannot place" in lower:
        # Simulate the escalation scenario: milk can't be placed in time
        return json.dumps({
            "action": "cannot_place",
            "matches": [],
            "unplaced": [{
                "donation_id": "d1",
                "item": "milk (40 lbs)",
                "reason": "Expiry in < 2 days; no available driver confirmed for North shelter route.",
            }],
            "escalate": True,
            "escalation_summary": (
                "🚨 Perishable donation: 40 lbs of milk expires 2026-09-11. "
                "Matched to North shelter need (n1) but no driver is confirmed. "
                "Should I contact Aisha (+15550000003) as emergency driver? Reply YES or NO."
            ),
        })

    # Happy path: canned beans match canned goods need
    return json.dumps({
        "action": "matched",
        "matches": [{
            "donation_id": "d2",
            "need_id": "n2",
            "item": "canned beans (120 cans)",
            "confidence": 0.91,
            "notes": "Matched 120 cans to Main pantry need (200 cans requested). Partial fill.",
        }],
        "unplaced": [],
        "escalate": False,
        "escalation_summary": "",
    })


def matcher_agent(query: str) -> str:
    """Match incoming donations to local needs.

    Agents-as-Tools wrapper (§8.2). When BEDROCK_ENABLED is unset returns a mock
    result; otherwise delegates to a real Strands Agent with Sheets + Twilio tools.

    Args:
        query: A natural-language description of the donation and context
               (e.g. '40 lbs of milk donated, expires 2026-09-11').

    Returns:
        JSON string with match results and an escalation flag.
    """
    if os.getenv("BEDROCK_ENABLED", "").lower() not in ("1", "true", "yes"):
        return _mock_result(query)

    # --- Real Strands Agent path ---
    from strands import Agent
    from strands.models import BedrockModel
    from app.tools.sheets import as_strands_tools as sheets_tools
    from app.tools.twilio import as_strands_tool as twilio_tool

    # Donation matching needs higher-quality reasoning for ambiguous cases
    hard_model_id = os.getenv("HARD_MODEL_ID", "global.anthropic.claude-sonnet-4-6")
    region = os.getenv("AWS_REGION", "us-west-2")
    model = BedrockModel(model_id=hard_model_id, region_name=region, temperature=0.2)

    tools = [*sheets_tools(), twilio_tool()]
    agent = Agent(system_prompt=MATCHER_PROMPT, tools=tools, model=model)
    result = agent(query)
    return str(getattr(result, "message", result))


def as_strands_tool():
    """Return a Strands @tool-decorated version of matcher_agent."""
    from strands import tool

    @tool
    def match_donation(query: str) -> str:
        """Match an incoming donation to a local need; escalate if perishable can't be placed.

        Args:
            query: Description of the donation (item, qty, expiry) and any known context.
        """
        return matcher_agent(query)

    return match_donation
