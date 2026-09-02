"""Strands Graph orchestrator + Trust Ratchet gate.  Spec: IMPLEMENTATION_PLAN.md §8.3.

Phase: IMPLEMENTED IN P2.

Topology:
    router --(ratchet gate passes)--> execute --> review
    router --(gate fails)---------->  human_review
The ratchet gate is a Strands conditional edge reading effective_level + confidence.
"""
from __future__ import annotations

from app.ratchet import gate_passes


def ratchet_condition(state) -> bool:  # noqa: ANN001
    """Conditional edge: True -> execute; False -> human_review (§3.5)."""
    task = state.results.get("router")            # router node emits task_type + confidence
    return gate_passes(state["org_id"], task.task_type, task.confidence)


def build_steward_graph():
    """Build and return the Strands Graph. Implemented in P2."""
    raise NotImplementedError("P2.4")
    # from strands.multiagent import GraphBuilder
    # b = GraphBuilder()
    # b.add_node(router_agent, "router")
    # b.add_node(execute_node, "execute")
    # b.add_node(reviewer_agent, "review")
    # b.add_node(human_review_node, "human_review")
    # b.set_entry_point("router")
    # b.add_edge("router", "execute", condition=ratchet_condition)
    # b.add_edge("router", "human_review", condition=lambda s: not ratchet_condition(s))
    # b.add_edge("execute", "review")
    # return b.build()
