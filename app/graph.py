"""Strands Graph orchestrator + Trust Ratchet gate.  Spec: IMPLEMENTATION_PLAN.md §8.3.

Phase: P2.4 — IMPLEMENTED.

Topology:
    router ──(ratchet gate passes)──► execute ──► (review embedded in execute)
    router ──(gate fails)──────────► human_review

The ratchet gate is a conditional edge reading effective_level + confidence from the router's
output. It routes to execute if both the autonomy gate and confidence gate pass, otherwise
to human_review.

For local / offline use the graph is driven directly by run_local_demo.py without
the AgentCore wrapper (see app/main.py for the production wrapper).
"""
from __future__ import annotations

from typing import Any, Optional

from app.ratchet import (
    AUTO_NOTIFY,
    AUTO_SILENT,
    ESCALATE,
    InMemoryTrustStore,
    TrustStore,
    decision_for,
)


# ---------------------------------------------------------------------------
# Ratchet gate condition
# ---------------------------------------------------------------------------
def ratchet_condition(state: dict) -> bool:
    """Conditional edge: True → execute; False → human_review.

    Reads org_id, task_type, confidence from state (set by the router node).
    Uses the store injected via state["_store"] (defaults to the global store).
    """
    org_id: str = state.get("org_id", "")
    task_type: str = state.get("task_type", "")
    confidence: float = float(state.get("confidence", 0.0))
    store: Optional[TrustStore] = state.get("_store")

    decision = decision_for(org_id, task_type, confidence, **({"store": store} if store else {}))
    state["decision"] = decision            # write the decision into state for execute_node
    return decision != ESCALATE


# ---------------------------------------------------------------------------
# Router node wrapper
# ---------------------------------------------------------------------------
def _router_node(state: dict) -> dict:
    """Runs the router and injects task_type + confidence into state."""
    from app.agents.router import classify, RouterResult

    text: str = state.get("input", "")
    org_id: str = state.get("org_id", "demo")
    result: RouterResult = classify(text, org_id=org_id)

    print(f"\n[router] task_type={result.task_type!r} confidence={result.confidence:.2f}")

    return {
        **state,
        "task_type": result.task_type,
        "confidence": result.confidence,
    }


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------
def build_steward_graph(store: Optional[TrustStore] = None):
    """Build and return the Steward graph.

    Args:
        store: Optional TrustStore to inject. If None, uses the global default
               (InMemoryTrustStore for local, DynamoDBTrustStore for prod).

    Returns:
        A callable `run_graph(input_dict) -> output_dict` that executes the full
        router → ratchet_gate → execute/human_review pipeline.

    Note on Strands GraphBuilder:
        The Strands GraphBuilder API (strands.multiagent.GraphBuilder) is used when
        BEDROCK_ENABLED=true and strands is installed. In local/mock mode we provide
        a lightweight Python-native graph runner so tests + demo work offline.
    """
    import os

    if store is not None and hasattr(store, 'get'):
        # Bind the store into state automatically
        _store = store
    else:
        _store = None

    if os.getenv("BEDROCK_ENABLED", "").lower() in ("1", "true", "yes"):
        return _build_strands_graph(_store)
    else:
        return _build_local_graph(_store)


# ---------------------------------------------------------------------------
# Local (mock) graph runner — fully offline, no Strands install required
# ---------------------------------------------------------------------------
def _build_local_graph(store: Optional[TrustStore]):
    """Pure-Python graph runner for offline dev, tests, and local demo."""
    from app.nodes.execute import execute_node
    from app.nodes.human_review import human_review_node

    def run_graph(input_dict: dict) -> dict:
        """Execute the full pipeline: router → gate → execute|human_review."""
        state: dict[str, Any] = dict(input_dict)
        if store is not None:
            state["_store"] = store

        # 1. Router node
        state = _router_node(state)

        # 2. Trust Ratchet gate
        gate_ok = ratchet_condition(state)
        print(f"[graph] ratchet gate: {'PASS → execute' if gate_ok else 'FAIL → human_review'} "
              f"(decision={state.get('decision', '?')})")

        # 3. Execute or escalate
        if gate_ok:
            state = execute_node(state)
        else:
            state = human_review_node(state)

        return state

    return run_graph


# ---------------------------------------------------------------------------
# Strands GraphBuilder graph — real implementation for production
# ---------------------------------------------------------------------------
def _build_strands_graph(store: Optional[TrustStore]):
    """Builds a Strands Graph using GraphBuilder. Requires strands-agents installed."""
    try:
        from strands.multiagent import GraphBuilder
    except ImportError as e:
        raise ImportError(
            "strands-agents is not installed. Run `pip install -r requirements.txt` "
            "or set BEDROCK_ENABLED=false to use the local graph."
        ) from e

    from app.nodes.execute import execute_node
    from app.nodes.human_review import human_review_node

    def router_node_fn(state: dict) -> dict:
        s = _router_node(state)
        if store is not None:
            s["_store"] = store
        return s

    def gate_fn(state: dict) -> bool:
        return ratchet_condition(state)

    b = GraphBuilder()
    b.add_node(router_node_fn, "router")
    b.add_node(execute_node, "execute")
    b.add_node(human_review_node, "human_review")
    b.set_entry_point("router")
    b.add_conditional_edge(
        "router",
        gate_fn,
        {True: "execute", False: "human_review"},
    )
    # No edge out of execute/human_review — they're terminal nodes for this graph
    return b.build()
