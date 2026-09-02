"""Execute node — dispatch to the right specialist (as-tool).  Spec: §8.3.  Phase: P2.4.

Chooses recruiter/matcher/grant based on task_type, applies the level semantics:
  L1 SUPERVISED -> execute + notify + start undo window
  L2 AUTONOMOUS -> execute silently
(L0 never reaches here — it routes to human_review.)
"""
from __future__ import annotations


def execute_node(state):  # noqa: ANN001
    """Dispatch + apply level semantics. P2.4."""
    raise NotImplementedError("P2.4")
