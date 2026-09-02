"""AgentCore Memory — institutional knowledge (org namespace).  Spec: IMPLEMENTATION_PLAN.md §8.6.

Phase: IMPLEMENTED IN P4.  actor_id == org_id so knowledge survives turnover (§3.6).
Note: docs mark MemoryClient "Legacy" and recommend MemorySessionManager — confirm API in P4.
"""
from __future__ import annotations

import os

MEMORY_NAME = "StewardOrgMemory"


def create_memory(region: str | None = None):
    """Create the Memory resource with semantic + user-preference + summary strategies. P4."""
    raise NotImplementedError("P4.4")
    # from bedrock_agentcore.memory import MemoryClient
    # client = MemoryClient(region_name=region or os.getenv("AWS_REGION", "us-west-2"))
    # return client.create_memory_and_wait(name=MEMORY_NAME, strategies=[
    #     {"semanticMemoryStrategy":     {"name": "OrgFacts",       "namespaceTemplates": ["/orgs/{actorId}/facts/"]}},
    #     {"userPreferenceMemoryStrategy":{"name": "OrgPrefs",      "namespaceTemplates": ["/orgs/{actorId}/prefs/"]}},
    #     {"summaryMemoryStrategy":       {"name": "SessionSummary","namespaceTemplates": ["/orgs/{actorId}/summaries/{sessionId}/"]}},
    # ])


def write_event(memory_id: str, org_id: str, session_id: str, messages: list[tuple[str, str]]):
    """Append a short-term event (org_id as actor). P4."""
    raise NotImplementedError("P4.4")


def retrieve(memory_id: str, org_id: str, query: str, top_k: int = 10):
    """Semantic retrieval of org facts. P4."""
    raise NotImplementedError("P4.4")
