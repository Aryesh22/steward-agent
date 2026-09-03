"""Twilio SMS tool — REPLACED by app/tools/sms.py (Amazon SNS).

This file is kept as a compatibility shim so any code still importing
`app.tools.twilio.send_sms` continues to work unchanged.
All calls are forwarded to the SNS-backed implementation.

TODO (P4.2): once Gateway MCP migration is done, remove this file entirely.
"""
from app.tools.sms import send_sms, send_sms_auto, as_strands_tool  # noqa: F401


def as_strands_tool():  # type: ignore[no-redef]
    """Compatibility shim — delegates to sms.py's SNS implementation."""
    from app.tools.sms import send_sms_auto
    from strands import tool

    @tool
    def send_text(to: str, message: str) -> str:
        """Send an SMS to a phone number (E.164, e.g. +15551234567) via Amazon SNS.

        Args:
            to: recipient phone number in E.164 format
            message: the SMS body
        """
        return send_sms_auto(to, message)

    return send_text
