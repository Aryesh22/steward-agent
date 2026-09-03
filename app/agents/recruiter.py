"""RecruiterAgent — volunteer confirm + backfill (as-tool).  Spec: §8.2.  Phase: P2.2.

Task-types: volunteer_reminder (3-touch shift-confirmation SMS), shift_backfill (text
next-eligible volunteer when one drops). Both cap at L2 (fast graduation).

Mock-first: when BEDROCK_ENABLED is unset, recruiter_agent() returns a realistic fake
result so the graph and local demo run offline.
"""
from __future__ import annotations

import json
import os
from datetime import datetime

RECRUITER_PROMPT = """You are Steward's volunteer coordinator for a small community org.

Your tasks:
1. VOLUNTEER_REMINDER: Confirm volunteers for upcoming shifts using a polite 3-touch SMS sequence.
   Touch 1 (5 days out): friendly heads-up. Touch 2 (2 days out): confirmation request.
   Touch 3 (day of): final reminder if not confirmed.
2. SHIFT_BACKFILL: When a volunteer drops, text the next eligible volunteer from the roster
   who has the right skills and availability for that shift.

Rules:
- Be concise and friendly. Use first names.
- Never contact the same person more than the sequence allows.
- When reading the sheet, check 'assigned_ids' against the Volunteers tab.
- Return a JSON summary: {"action": "sent_sms"|"backfill_sent"|"no_action",
  "recipients": [{"name": ..., "phone": ..., "message": ...}],
  "shift_id": ..., "notes": "..."}
"""


def _mock_result(query: str) -> str:
    """Return a realistic fake result for offline/test use."""
    is_backfill = "backfill" in query.lower() or "dropped" in query.lower()
    if is_backfill:
        return json.dumps({
            "action": "backfill_sent",
            "recipients": [{"name": "Aisha", "phone": "+15550000003",
                            "message": "Hi Aisha! Could you cover the Thu 08:00 driver shift? "
                                       "A volunteer had to drop out. Reply YES to confirm."}],
            "shift_id": "s3",
            "notes": "Backfill text sent to next eligible driver.",
        })
    return json.dumps({
        "action": "sent_sms",
        "recipients": [
            {"name": "Maria", "phone": "+15550000001",
             "message": "Hi Maria! Just a reminder: you're scheduled for the Tue 09:00–12:00 "
                        "driver shift. Reply YES to confirm or NO if you can't make it."},
            {"name": "Devon", "phone": "+15550000002",
             "message": "Hi Devon! Quick reminder about your Wed 14:00–17:00 sorting shift. "
                        "Reply YES to confirm!"},
        ],
        "shift_id": "s1",
        "notes": "Touch-1 reminders sent to 2 volunteers.",
    })


def recruiter_agent(query: str) -> str:
    """Confirm/backfill volunteer shifts.

    Agents-as-Tools wrapper (§8.2). When BEDROCK_ENABLED is unset returns a mock
    result; otherwise delegates to a real Strands Agent with Sheets + Twilio tools.

    Args:
        query: A natural-language description of the shift and roster context.

    Returns:
        JSON string summarising the action(s) taken.
    """
    if os.getenv("BEDROCK_ENABLED", "").lower() not in ("1", "true", "yes"):
        return _mock_result(query)

    # --- Real Strands Agent path ---
    from strands import Agent
    from strands.models import BedrockModel
    from app.tools.sheets import as_strands_tools as sheets_tools
    from app.tools.twilio import as_strands_tool as twilio_tool

    cheap_model_id = os.getenv("CHEAP_MODEL_ID", "us.amazon.nova-lite-v1:0")
    region = os.getenv("AWS_REGION", "us-west-2")
    model = BedrockModel(model_id=cheap_model_id, region_name=region, temperature=0.1)

    tools = [*sheets_tools(), twilio_tool()]
    agent = Agent(system_prompt=RECRUITER_PROMPT, tools=tools, model=model)
    result = agent(query)
    return str(getattr(result, "message", result))


# Register as Strands @tool so the orchestrator can call it directly
def as_strands_tool():
    """Return a Strands @tool-decorated version of recruiter_agent."""
    from strands import tool

    @tool
    def recruit_volunteers(query: str) -> str:
        """Confirm upcoming volunteer shifts or find a backfill replacement via SMS.

        Args:
            query: Description of the shift and what action is needed
                   (e.g. 'Send reminder for shift s1' or 'Backfill shift s3, driver dropped').
        """
        return recruiter_agent(query)

    return recruit_volunteers
