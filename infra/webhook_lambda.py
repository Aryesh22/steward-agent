"""Inbound SMS webhook: Twilio -> API Gateway -> Lambda -> InvokeAgentRuntime.  Spec: §8.8.  Phase: P3.3.

Handles BOTH inbound donation/volunteer SMS (mode="event") and coordinator replies to an
escalation (fed back as an interruptResponse to resume the session). Uses a stable per-org
runtimeSessionId so resumes land on the same session.
"""
from __future__ import annotations


def handler(event, context):  # noqa: ANN001
    """Lambda entry. Parse Twilio payload -> InvokeAgentRuntime. P3.3."""
    raise NotImplementedError("P3.3")
