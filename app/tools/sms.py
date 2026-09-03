"""SMS tool via Amazon SNS.  Spec: IMPLEMENTATION_PLAN.md §8.7.  Phase: P1.6.

Replaces the original Twilio tool.  Amazon SNS is already part of the AWS stack
(boto3 is a mandatory dependency), so there are zero extra credentials or packages.

Interface:
    send_sms(to_number: str, body: str) -> str   # returns SNS MessageId

Cost note (§12):
    SNS SMS in India costs ~$0.00414/msg (transactional). With the $50 hackathon
    credits this is effectively free for demo purposes (~12,000 messages budget).

Environment variables:
    AWS_REGION              — already required for DynamoDB / Bedrock (default us-east-1 for SNS)
    SNS_SENDER_ID           — optional; alphanumeric sender ID shown on phone (e.g. "Steward")
    COORDINATOR_PHONE       — E.164 number, e.g. +919876543210
"""
from __future__ import annotations

import json
import os

import boto3


def _sns_client():
    # SNS SMS works best out of us-east-1 globally; keep configurable.
    region = os.getenv("SNS_REGION", os.getenv("AWS_REGION", "us-east-1"))
    return boto3.client("sns", region_name=region)


def send_sms(to_number: str, body: str, *, sms_type: str = "Transactional") -> str:
    """Send an SMS via Amazon SNS.

    Args:
        to_number: E.164 phone number, e.g. +919876543210
        body:      Message text (160 chars for single segment; SNS splits automatically)
        sms_type:  "Transactional" (default, higher priority) or "Promotional"

    Returns:
        SNS MessageId string on success.

    Raises:
        Exception: Propagates boto3/SNS errors so callers can decide to log vs. raise.
    """
    client = _sns_client()

    attributes: dict = {
        "AWS.SNS.SMS.SMSType": {
            "DataType": "String",
            "StringValue": sms_type,
        },
    }

    sender_id = os.getenv("SNS_SENDER_ID", "Steward")
    if sender_id:
        attributes["AWS.SNS.SMS.SenderID"] = {
            "DataType": "String",
            "StringValue": sender_id[:11],  # max 11 chars
        }

    response = client.publish(
        PhoneNumber=to_number,
        Message=body,
        MessageAttributes=attributes,
    )
    return response["MessageId"]


def send_coordinator_alert(org_id: str, summary: str, options: list[str] | None = None) -> str:
    """Send a coordinator decision-request SMS (escalation surface, §8.5).

    Args:
        org_id:  Organisation identifier (for context in the message).
        summary: Concise description of the decision needed.
        options: Valid reply options, e.g. ['YES', 'NO']. If None, defaults shown.

    Returns:
        SNS MessageId.
    """
    opts = options or ["YES", "NO"]
    opts_str = " / ".join(opts)
    to_number = os.getenv("COORDINATOR_PHONE", "")
    if not to_number.strip():
        raise ValueError("COORDINATOR_PHONE env var is not set")

    msg = f"[Steward/{org_id}] {summary}\nReply: {opts_str}"
    # Truncate to 160 chars to keep single-segment (SNS auto-splits but let's be explicit)
    if len(msg) > 160:
        msg = msg[:157] + "..."

    return send_sms(to_number, msg)


# ---------------------------------------------------------------------------
# Local mock (used when BEDROCK_ENABLED != true)
# ---------------------------------------------------------------------------
def send_sms_mock(to_number: str, body: str) -> str:
    """Print-only mock for local/offline dev and tests."""
    print(f"[SNS-mock] → {to_number}: {body}")
    return "mock-message-id"


def send_sms_auto(to_number: str, body: str) -> str:
    """Use real SNS if AWS creds present, else fall back to mock."""
    key = os.getenv("AWS_ACCESS_KEY_ID", "").strip()
    profile = os.getenv("AWS_PROFILE", "").strip()
    if not key and not profile:
        return send_sms_mock(to_number, body)
    return send_sms(to_number, body)
