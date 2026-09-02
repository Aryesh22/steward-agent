"""Graph routing tests.  Spec: IMPLEMENTATION_PLAN.md §8.3.  Phase: authored in P2.7.

Asserts the ratchet conditional edge routes to `execute` when gates pass and to
`human_review` when they don't. Skipped until P2 builds the graph.
"""
from __future__ import annotations

import pytest


@pytest.mark.skip(reason="P2: implement build_steward_graph + ratchet_condition routing")
def test_routes_to_execute_when_gates_pass():
    ...


@pytest.mark.skip(reason="P2: implement human_review routing")
def test_routes_to_human_review_when_gate_fails():
    ...
