"""EventBridge Scheduler -> InvokeAgentRuntime (nightly sweep).  Spec: §8.8.  Phase: P3.4.

NOTE: there is NO native EventBridge->AgentCore target. Use an EventBridge Scheduler UNIVERSAL
target calling `bedrock-agentcore:InvokeAgentRuntime`. Universal targets are synchronous (~30s
timeout), so the entrypoint must launch work as an async task and return immediately
(app.add_async_task / app.complete_async_task); /ping must report HealthyBusy while running.
"""
from __future__ import annotations


def create_nightly_schedule(agent_runtime_arn: str, org_id: str, cron: str = "cron(0 6 * * ? *)") -> None:
    """Create the daily schedule. P3.4."""
    raise NotImplementedError("P3.4")
