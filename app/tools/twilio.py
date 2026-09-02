"""Twilio SMS tool.  Spec: IMPLEMENTATION_PLAN.md §8.7.  Phase: P1.6 (local) -> P4.2 (Gateway).

Sends SMS (volunteer reminders, backfill asks, coordinator escalations). Start as a local
Strands @tool calling the Twilio REST API; migrate to a Gateway OpenAPI target (API-key provider) in P4.
"""
from __future__ import annotations

import os

FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "")


def send_sms(to_e164: str, body: str) -> str:
    """Send an SMS; return the message SID. P1.6."""
    raise NotImplementedError("P1.6")
