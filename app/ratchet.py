"""The Trust Ratchet — the core mechanic.  Spec: IMPLEMENTATION_PLAN.md §3.

Phase: IMPLEMENTED IN P1.  This file is a stub with the exact signatures and the
config loader wired up; the logic bodies raise NotImplementedError until P1.

Design rules (do not violate):
  * effective_level = min(earned_level, task_cap)              (§3.2)
  * auto-act only if autonomy gate AND confidence gate pass    (§3.5)
  * promote one level after `promotion_threshold` verified-correct actions (§3.3)
  * demote one level (reset counter) on verified error / human override    (§3.4)
  * L0-capped task-types ALWAYS ask, regardless of earned trust
  * trust state is keyed by org_id (institutional persistence, §3.6)
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

CONFIG_PATH = Path(os.getenv("RATCHET_CONFIG", Path(__file__).resolve().parent.parent / "config" / "ratchet.yaml"))

# Autonomy levels
L_ASSISTED = 0
L_SUPERVISED = 1
L_AUTONOMOUS = 2


@lru_cache(maxsize=1)
def load_config() -> dict:
    """Load config/ratchet.yaml (cached)."""
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


@dataclass
class TrustState:
    org_id: str
    task_type: str
    current_level: int
    consecutive_verified_correct: int
    cap: int


def task_cap(task_type: str) -> int:
    """Hard ceiling for a task-type (§3.2)."""
    return int(load_config()["task_caps"][task_type])


def effective_level(earned_level: int, task_type: str) -> int:
    """min(earned_level, cap) (§3.2)."""
    return min(int(earned_level), task_cap(task_type))


def confidence_gate(task_type: str, confidence: float) -> bool:
    """auto-act only if confidence >= 1 - cost_ratio, and >= global floor (§3.5)."""
    raise NotImplementedError("P1.2")


def gate_passes(org_id: str, task_type: str, confidence: float) -> bool:
    """Both the autonomy gate and the confidence gate must pass (§3.5).

    Returns True  -> the specialist may execute (subject to level: L1 notify / L2 silent).
    Returns False -> route to human_review (escalate).
    """
    raise NotImplementedError("P1.2")


def record_outcome(org_id: str, task_type: str, *, verified_correct: bool, human_override: bool) -> TrustState:
    """Apply promotion/demotion after an action is verified (§3.3, §3.4).

    Persists to DynamoDB (infra/ddb.py) and mirrors current levels to the Sheet TrustState tab.
    """
    raise NotImplementedError("P1.2 / P1.5")
