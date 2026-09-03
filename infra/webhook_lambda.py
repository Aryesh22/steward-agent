"""Inbound SMS webhook: API Gateway → Lambda → InvokeAgentRuntime.
Spec: IMPLEMENTATION_PLAN.md §8.8.  Phase: P3.3.

Two event types this Lambda handles:
  1. New inbound SMS (donation offer, volunteer reply, etc.)
     → InvokeAgentRuntime with mode="event", runtimeSessionId stable per org
  2. Coordinator reply to an escalation interrupt (YES / NO / APPROVE / DEFER)
     → InvokeAgentRuntime with an interruptResponse block to *resume* the
       paused session from the interruption point.

The Lambda is triggered by API Gateway (HTTP POST) whose URL is configured as
the webhook endpoint (SNS subscription confirmation or direct POST).

Environment variables required:
    AGENT_RUNTIME_ARN       — ARN of the deployed AgentCore Runtime
    AWS_REGION              — AWS region (us-west-2 default)
    ORG_ID                  — org identifier (single-org MVP)

Session continuity:
    We use a stable runtimeSessionId = "steward-{org_id}" so coordinator
    replies always land on the same session that raised the interrupt.
    The Runtime keeps the session alive while waiting for interruptResponse.
"""
from __future__ import annotations

import json
import os
import re
import urllib.parse
import hashlib
import hmac

import boto3


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_RUNTIME_ARN = os.getenv("AGENT_RUNTIME_ARN", "")
_REGION = os.getenv("AWS_REGION", "us-west-2")
_ORG_ID = os.getenv("ORG_ID", "demo-pantry")

# Keywords that mean the coordinator is replying to an escalation interrupt
_INTERRUPT_REPLY_KEYWORDS = {
    "yes", "no", "approve", "revise", "hold", "defer",
    "ok", "deny", "reject", "undo", "proceed", "skip",
}


# ---------------------------------------------------------------------------
# Lambda entry point
# ---------------------------------------------------------------------------
def handler(event: dict, context) -> dict:  # noqa: ANN001
    """Lambda entry. Routes inbound SMS → InvokeAgentRuntime.

    Supports two caller patterns:
      - API Gateway HTTP (Content-Type: application/json or URL-encoded body)
      - Direct Lambda invoke (testing)

    Returns:
        API Gateway-compatible response dict {statusCode, body}.
    """
    try:
        payload = _parse_event(event)
        org_id = payload.get("org_id", _ORG_ID)
        body_text = payload.get("body", "").strip()
        interrupt_id = payload.get("interrupt_id")  # set by the resume path

        if not body_text and not interrupt_id:
            return _response(400, {"error": "Empty body — nothing to process"})

        session_id = _session_id(org_id)

        if interrupt_id or _is_interrupt_reply(body_text):
            # Path 2: coordinator is replying to an escalation interrupt → resume
            result = _invoke_resume(session_id, interrupt_id or "", body_text)
        else:
            # Path 1: new inbound SMS (donation, volunteer, etc.) → new event
            result = _invoke_event(session_id, org_id, body_text)

        return _response(200, {"status": "ok", "result": result})

    except Exception as exc:  # pragma: no cover
        print(f"[webhook] ERROR: {exc}")
        return _response(500, {"error": str(exc)})


# ---------------------------------------------------------------------------
# InvokeAgentRuntime helpers
# ---------------------------------------------------------------------------
def _agentcore_client():
    """Return a boto3 client for bedrock-agentcore-runtime."""
    return boto3.client("bedrock-agentcore-runtime", region_name=_REGION)


def _invoke_event(session_id: str, org_id: str, sms_body: str) -> str:
    """Invoke the agent with a new inbound SMS event (mode='event')."""
    if not _RUNTIME_ARN:
        # Local / test mode — print and return mock
        print(f"[webhook] MOCK invoke_event session={session_id} body={sms_body!r}")
        return "mock-invoked"

    client = _agentcore_client()
    request_body = json.dumps({
        "mode": "event",
        "org_id": org_id,
        "payload": {"sms": sms_body},
    })
    resp = client.invoke_agent_runtime(
        agentRuntimeArn=_RUNTIME_ARN,
        runtimeSessionId=session_id,
        qualifier="DEFAULT",
        requestBody=request_body.encode(),
    )
    # Streaming response — collect chunks
    return _collect_response(resp)


def _invoke_resume(session_id: str, interrupt_id: str, reply_text: str) -> str:
    """Resume an interrupted session with the coordinator's reply.

    Sends an interruptResponse block back to the paused graph node so it can
    continue from the interruption point (§8.5).
    """
    if not _RUNTIME_ARN:
        print(f"[webhook] MOCK invoke_resume session={session_id} "
              f"interrupt={interrupt_id!r} reply={reply_text!r}")
        return "mock-resumed"

    client = _agentcore_client()
    interrupt_responses = [
        {
            "interruptResponse": {
                "interruptId": interrupt_id or "coordinator-decision",
                "response": reply_text,
            }
        }
    ]
    request_body = json.dumps({
        "mode": "resume",
        "org_id": _ORG_ID,
        "interruptResponses": interrupt_responses,
    })
    resp = client.invoke_agent_runtime(
        agentRuntimeArn=_RUNTIME_ARN,
        runtimeSessionId=session_id,
        qualifier="DEFAULT",
        requestBody=request_body.encode(),
    )
    return _collect_response(resp)


def _collect_response(boto3_response: dict) -> str:
    """Collect streaming chunks from InvokeAgentRuntime response."""
    chunks = []
    stream = boto3_response.get("response") or boto3_response.get("completion", {})
    if hasattr(stream, "__iter__"):
        for chunk in stream:
            if "chunk" in chunk:
                data = chunk["chunk"].get("bytes", b"")
                chunks.append(data.decode() if isinstance(data, bytes) else str(data))
    return "".join(chunks) if chunks else str(boto3_response.get("body", ""))


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------
def _parse_event(event: dict) -> dict:
    """Parse API Gateway or direct Lambda event into a flat payload dict."""
    # Direct Lambda invoke (tests, local)
    if "body" in event and isinstance(event["body"], dict):
        return event["body"]

    # API Gateway HTTP — body may be JSON or URL-encoded (from SNS HTTP subscription)
    raw_body = event.get("body", "") or ""
    if isinstance(raw_body, bytes):
        raw_body = raw_body.decode()

    content_type = ""
    headers = event.get("headers") or {}
    for k, v in headers.items():
        if k.lower() == "content-type":
            content_type = v.lower()
            break

    payload: dict = {}

    if "application/json" in content_type:
        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError:
            payload = {"body": raw_body}

    elif "application/x-www-form-urlencoded" in content_type:
        # SNS HTTP/HTTPS subscription confirmation or standard form post
        parsed = urllib.parse.parse_qs(raw_body, keep_blank_values=True)
        payload = {k: v[0] for k, v in parsed.items()}
        # Normalize: 'Body' (SNS) → 'body'
        if "Body" in payload:
            payload["body"] = payload.pop("Body")

    elif raw_body:
        # Try JSON anyway, fall back to treating as SMS body
        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError:
            payload = {"body": raw_body}

    # Inject org_id from query string if present
    qs = event.get("queryStringParameters") or {}
    if "org_id" in qs:
        payload["org_id"] = qs["org_id"]

    return payload


def _is_interrupt_reply(text: str) -> bool:
    """Heuristic: is this SMS a coordinator reply to an escalation interrupt?

    True if the first word (case-insensitive) is a known reply keyword AND
    the message is short (coordinators don't write essays in SMS replies).
    """
    if not text:
        return False
    first_word = text.strip().lower().split()[0].rstrip(".,!?")
    return first_word in _INTERRUPT_REPLY_KEYWORDS and len(text) < 200


def _session_id(org_id: str) -> str:
    """Stable, deterministic session ID for an org (33–256 chars per Runtime spec)."""
    # Prefix + sanitised org_id, padded to meet the 33-char minimum
    raw = f"steward-{org_id}"
    if len(raw) < 33:
        # Pad with a hash suffix to guarantee minimum length (sha1 is 40 chars)
        raw = raw + "-" + hashlib.sha1(org_id.encode()).hexdigest()
    return raw[:256]


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }
