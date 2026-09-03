"""Twilio SMS tool.  Spec: IMPLEMENTATION_PLAN.md §8.7.  Phase: P1.6 (local) -> P4.2 (Gateway).

Local implementation uses the Twilio REST API directly (HTTP Basic auth) — no SDK dependency.
Migrate to an AgentCore Gateway OpenAPI target (API-key provider) in P4. Requires env:
  TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER
Needs live credentials to run; not exercised by offline unit tests.
"""
from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request


class TwilioError(RuntimeError):
    pass


def _creds() -> tuple[str, str, str]:
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_FROM_NUMBER")
    if not all((sid, token, from_number)):
        raise TwilioError("Missing TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_FROM_NUMBER")
    return sid, token, from_number  # type: ignore[return-value]


def send_sms(to_e164: str, body: str) -> str:
    """Send an SMS; return the Twilio message SID. P1.6."""
    sid, token, from_number = _creds()
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    data = urllib.parse.urlencode({"To": to_e164, "From": from_number, "Body": body}).encode()

    req = urllib.request.Request(url, data=data, method="POST")
    # HTTP Basic auth: base64(sid:token)
    auth = base64.b64encode(f"{sid}:{token}".encode()).decode()
    req.add_header("Authorization", f"Basic {auth}")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode())
            return payload.get("sid", "")
    except urllib.error.HTTPError as e:  # pragma: no cover - needs network
        raise TwilioError(f"Twilio API error {e.code}: {e.read().decode()}") from e


# --- Strands @tool wrapper (registered on the specialist agents) ---
def as_strands_tool():
    """Return a Strands @tool-decorated callable. Imported lazily so this module
    stays importable without strands installed."""
    from strands import tool

    @tool
    def send_text(to: str, message: str) -> str:
        """Send an SMS to a phone number (E.164, e.g. +15551234567).

        Args:
            to: recipient phone number in E.164 format
            message: the SMS body
        """
        return send_sms(to, message)

    return send_text
