"""EventBridge Scheduler → InvokeAgentRuntime (nightly sweep).
Spec: IMPLEMENTATION_PLAN.md §8.8.  Phase: P3.4.

Architecture note (§8.8):
  There is NO native EventBridge→AgentCore target. The pattern is:
    EventBridge Scheduler universal target → InvokeAgentRuntime directly.
  Universal targets are synchronous (~30s timeout), so the entrypoint MUST:
    1. Call app.add_async_task(...) to start the sweep as a background async task.
    2. Return immediately (status 200) with /ping = HealthyBusy.
    3. Call app.complete_async_task(...) when done.

This file provides:
  - create_nightly_schedule(): idempotent boto3 call to set up the schedule.
  - delete_schedule(): teardown helper.
  - IAM helpers: role + policy for scheduler → AgentCore permission.

Environment variables required:
    AGENT_RUNTIME_ARN        — ARN of the deployed AgentCore Runtime
    AWS_REGION               — AWS region
    ORG_ID                   — org identifier
    SCHEDULER_ROLE_ARN       — IAM role ARN for the scheduler (created by create_scheduler_role())
"""
from __future__ import annotations

import json
import os

import boto3
from botocore.exceptions import ClientError


_REGION = os.getenv("AWS_REGION", "us-west-2")
_RUNTIME_ARN = os.getenv("AGENT_RUNTIME_ARN", "")
_ORG_ID = os.getenv("ORG_ID", "demo-pantry")
_SCHEDULE_NAME = os.getenv("SCHEDULE_NAME", "steward-nightly-sweep")
_SCHEDULE_GROUP = os.getenv("SCHEDULE_GROUP", "steward")


# ---------------------------------------------------------------------------
# Schedule management
# ---------------------------------------------------------------------------
def create_nightly_schedule(
    agent_runtime_arn: str,
    org_id: str,
    scheduler_role_arn: str,
    cron: str = "cron(0 6 * * ? *)",  # 06:00 UTC = 11:30 AM IST
    schedule_name: str = _SCHEDULE_NAME,
    group_name: str = _SCHEDULE_GROUP,
    region: str | None = None,
) -> str:
    """Create (or update) the daily EventBridge Scheduler → InvokeAgentRuntime schedule.

    Args:
        agent_runtime_arn:  The AgentCore Runtime ARN to invoke.
        org_id:             Organisation identifier (injected into sweep payload).
        scheduler_role_arn: IAM role ARN the scheduler assumes to call AgentCore.
        cron:               EventBridge cron expression (UTC). Default 06:00 UTC daily.
        schedule_name:      Name for the schedule (idempotent — update if exists).
        group_name:         EventBridge schedule group (created if absent).
        region:             AWS region override.

    Returns:
        The schedule ARN.

    Raises:
        ClientError: on unexpected AWS errors.
    """
    r = region or _REGION
    client = boto3.client("scheduler", region_name=r)

    # Ensure group exists (idempotent)
    _ensure_schedule_group(client, group_name)

    # Sweep payload: mode=sweep so the entrypoint runs the nightly job
    target_input = json.dumps({
        "mode": "sweep",
        "org_id": org_id,
        "trigger": "nightly_scheduler",
    })

    schedule_kwargs = dict(
        Name=schedule_name,
        GroupName=group_name,
        ScheduleExpression=cron,
        ScheduleExpressionTimezone="UTC",
        FlexibleTimeWindow={"Mode": "OFF"},
        State="ENABLED",
        Target={
            # Universal target: calls bedrock-agentcore:InvokeAgentRuntime directly
            "Arn": "arn:aws:scheduler:::aws-sdk:bedrockagentcoreruntime:invokeAgentRuntime",
            "RoleArn": scheduler_role_arn,
            "Input": target_input,
            # Universal target parameters map to SDK call parameters
            "SdkParameters": {
                "AgentRuntimeArn": agent_runtime_arn,
                "Qualifier": "DEFAULT",
                # SessionId stable per org so sweeps resume correctly
                "RuntimeSessionId": f"steward-sweep-{org_id}",
            },
        },
        Description=f"Steward nightly sweep for org {org_id}",
    )

    try:
        resp = client.create_schedule(**schedule_kwargs)
        arn = resp["ScheduleArn"]
        print(f"[scheduler] Created schedule '{schedule_name}': {arn}")
        return arn
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConflictException":
            # Schedule already exists — update it
            resp = client.update_schedule(**schedule_kwargs)
            arn = resp["ScheduleArn"]
            print(f"[scheduler] Updated schedule '{schedule_name}': {arn}")
            return arn
        raise


def delete_schedule(
    schedule_name: str = _SCHEDULE_NAME,
    group_name: str = _SCHEDULE_GROUP,
    region: str | None = None,
) -> None:
    """Delete the nightly schedule (teardown / cleanup)."""
    client = boto3.client("scheduler", region_name=region or _REGION)
    try:
        client.delete_schedule(Name=schedule_name, GroupName=group_name)
        print(f"[scheduler] Deleted schedule '{schedule_name}'.")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            print(f"[scheduler] Schedule '{schedule_name}' not found (already deleted).")
        else:
            raise


def _ensure_schedule_group(client, group_name: str) -> None:
    """Create the EventBridge schedule group if it doesn't exist."""
    try:
        client.create_schedule_group(Name=group_name)
        print(f"[scheduler] Created schedule group '{group_name}'.")
    except ClientError as e:
        if e.response["Error"]["Code"] in ("ConflictException", "ResourceAlreadyExistsException"):
            pass  # already exists — fine
        else:
            raise


# ---------------------------------------------------------------------------
# IAM helpers — role + policy for Scheduler → AgentCore
# ---------------------------------------------------------------------------
_SCHEDULER_ASSUME_POLICY = json.dumps({
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Principal": {"Service": "scheduler.amazonaws.com"},
        "Action": "sts:AssumeRole",
    }],
})

_SCHEDULER_PERMISSION_POLICY = {
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Action": ["bedrock-agentcore:InvokeAgentRuntime"],
        "Resource": "*",  # narrowed to specific ARN when agent_runtime_arn is known
    }],
}


def create_scheduler_role(
    role_name: str = "steward-scheduler-role",
    agent_runtime_arn: str | None = None,
    region: str | None = None,
) -> str:
    """Create (or retrieve) the IAM role the EventBridge Scheduler assumes.

    Args:
        role_name:         IAM role name.
        agent_runtime_arn: If provided, restricts the permission to this ARN.
        region:            AWS region (for STS endpoint).

    Returns:
        The IAM role ARN.
    """
    iam = boto3.client("iam", region_name=region or _REGION)

    # Narrow resource if ARN known
    perm_policy = dict(_SCHEDULER_PERMISSION_POLICY)
    if agent_runtime_arn:
        perm_policy["Statement"][0]["Resource"] = agent_runtime_arn

    try:
        resp = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=_SCHEDULER_ASSUME_POLICY,
            Description="EventBridge Scheduler role for Steward AgentCore invocation",
        )
        role_arn = resp["Role"]["Arn"]
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName="steward-invoke-runtime",
            PolicyDocument=json.dumps(perm_policy),
        )
        print(f"[scheduler] Created IAM role '{role_name}': {role_arn}")
        return role_arn

    except ClientError as e:
        if e.response["Error"]["Code"] == "EntityAlreadyExists":
            role_arn = iam.get_role(RoleName=role_name)["Role"]["Arn"]
            print(f"[scheduler] IAM role '{role_name}' already exists: {role_arn}")
            return role_arn
        raise


# ---------------------------------------------------------------------------
# Async task helpers (used inside app/main.py entrypoint for long sweeps)
# ---------------------------------------------------------------------------
def sweep_payload(org_id: str = _ORG_ID) -> dict:
    """Return the standard sweep payload dict (used by both Scheduler and tests)."""
    return {
        "mode": "sweep",
        "org_id": org_id,
        "trigger": "nightly_scheduler",
    }
