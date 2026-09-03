"""The Trust Ratchet — the core mechanic.  Spec: IMPLEMENTATION_PLAN.md §3.

Design:
  * A PURE core (no I/O) computes decisions and next-states — 100% unit-testable offline.
  * A pluggable TrustStore persists state: InMemoryTrustStore (tests) or a DynamoDB-backed
    store (production, infra/ddb.py). record_outcome/gate_passes accept an optional store.

Invariants (never violate):
  * effective_level = min(earned_level, task_cap)               (§3.2)
  * auto-act only if autonomy gate AND confidence gate pass     (§3.5)
  * promote ONE level after `promotion_threshold` verified-correct actions (§3.3)
  * demote ONE level (reset counter) on verified error / human override    (§3.4)
  * L0-capped task-types ALWAYS escalate, regardless of earned trust
  * trust state is keyed by org_id (institutional persistence, §3.6)
"""
from __future__ import annotations

import os
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path
from typing import Callable, Optional, Protocol

import yaml

CONFIG_PATH = Path(
    os.getenv("RATCHET_CONFIG", Path(__file__).resolve().parent.parent / "config" / "ratchet.yaml")
)

# --- Autonomy levels ---
L_ASSISTED = 0     # propose only; human must approve
L_SUPERVISED = 1   # auto-execute, notify, allow undo
L_AUTONOMOUS = 2   # execute silently
LEVEL_NAMES = {L_ASSISTED: "ASSISTED", L_SUPERVISED: "SUPERVISED", L_AUTONOMOUS: "AUTONOMOUS"}

# --- Decisions (what the gate tells the graph to do) ---
ESCALATE = "escalate"        # route to human_review (L0, or a gate failed)
AUTO_NOTIFY = "auto_notify"  # L1: execute + notify + undo window
AUTO_SILENT = "auto_silent"  # L2: execute silently


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def load_config() -> dict:
    """Load config/ratchet.yaml (cached)."""
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def _cfg() -> dict:
    return load_config()


def task_cap(task_type: str) -> int:
    """Hard ceiling for a task-type (§3.2)."""
    return int(_cfg()["task_caps"][task_type])


def promotion_threshold() -> int:
    return int(_cfg()["promotion_threshold"])


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class TrustState:
    org_id: str
    task_type: str
    current_level: int
    consecutive_verified_correct: int
    cap: int


def default_state(org_id: str, task_type: str) -> TrustState:
    return TrustState(
        org_id=org_id,
        task_type=task_type,
        current_level=int(_cfg()["default_start_level"]),
        consecutive_verified_correct=0,
        cap=task_cap(task_type),
    )


# ---------------------------------------------------------------------------
# PURE decision core (no I/O)
# ---------------------------------------------------------------------------
def effective_level(earned_level: int, task_type: str) -> int:
    """min(earned_level, cap) (§3.2)."""
    return min(int(earned_level), task_cap(task_type))


def confidence_threshold(task_type: str) -> float:
    """Auto-act threshold = max(1 - cost_ratio, global floor) (§3.5)."""
    cfg = _cfg()
    cost_ratio = float(cfg["cost_ratios"].get(task_type, 0.0))
    floor = float(cfg["confidence_floor_global"])
    return max(1.0 - cost_ratio, floor)


def confidence_gate(task_type: str, confidence: float) -> bool:
    """True iff confidence clears the task's threshold (§3.5)."""
    return float(confidence) >= confidence_threshold(task_type)


def decide(earned_level: int, task_type: str, confidence: float) -> str:
    """Pure decision: ESCALATE / AUTO_NOTIFY / AUTO_SILENT (§3.1, §3.5).

    L0 (or capped-L0) always ESCALATEs; a failed confidence gate ESCALATEs;
    otherwise L1 -> AUTO_NOTIFY, L2 -> AUTO_SILENT.
    """
    eff = effective_level(earned_level, task_type)
    if eff <= L_ASSISTED:
        return ESCALATE
    if not confidence_gate(task_type, confidence):
        return ESCALATE
    return AUTO_SILENT if eff >= L_AUTONOMOUS else AUTO_NOTIFY


def apply_outcome(state: TrustState, *, verified_correct: bool, human_override: bool) -> tuple[TrustState, str]:
    """Pure next-state after an action is reviewed. Returns (new_state, reason) (§3.3, §3.4).

    Precedence: a human override or a verified error DEMOTES (reset counter). Otherwise a
    verified-correct action increments the counter and promotes one level at the threshold
    (never above the cap).
    """
    if human_override or not verified_correct:
        new_level = max(L_ASSISTED, state.current_level - 1)
        reason = "demote:human_override" if human_override else "demote:verified_error"
        return replace(state, current_level=new_level, consecutive_verified_correct=0), reason

    counter = state.consecutive_verified_correct + 1
    if counter >= promotion_threshold() and state.current_level < state.cap:
        return (
            replace(state, current_level=state.current_level + 1, consecutive_verified_correct=0),
            f"promote:L{state.current_level}->L{state.current_level + 1}",
        )
    return replace(state, consecutive_verified_correct=counter), "increment"


# ---------------------------------------------------------------------------
# Store (pluggable persistence)
# ---------------------------------------------------------------------------
class TrustStore(Protocol):
    def get(self, org_id: str, task_type: str) -> TrustState: ...
    def put(self, state: TrustState, reason: str) -> None: ...
    def append_audit(self, org_id: str, entry: dict) -> None: ...


class InMemoryTrustStore:
    """Non-persistent store for tests and local runs."""

    def __init__(self) -> None:
        self._states: dict[tuple[str, str], TrustState] = {}
        self.audit: list[dict] = []

    def get(self, org_id: str, task_type: str) -> TrustState:
        return self._states.get((org_id, task_type)) or default_state(org_id, task_type)

    def put(self, state: TrustState, reason: str) -> None:
        self._states[(state.org_id, state.task_type)] = state

    def append_audit(self, org_id: str, entry: dict) -> None:
        self.audit.append(entry)


# A process-wide default store (in-memory). Production injects a DynamoDB store explicitly.
_default_store: TrustStore = InMemoryTrustStore()


def set_default_store(store: TrustStore) -> None:
    global _default_store
    _default_store = store


# ---------------------------------------------------------------------------
# Stateful API (used by the graph/nodes)
# ---------------------------------------------------------------------------
def gate_passes(org_id: str, task_type: str, confidence: float, *, store: Optional[TrustStore] = None) -> bool:
    """True -> the specialist may auto-execute (L1 notify / L2 silent).
    False -> route to human_review (escalate). (§3.5)
    """
    store = store or _default_store
    st = store.get(org_id, task_type)
    return decide(st.current_level, task_type, confidence) != ESCALATE


def decision_for(org_id: str, task_type: str, confidence: float, *, store: Optional[TrustStore] = None) -> str:
    """Full decision (ESCALATE / AUTO_NOTIFY / AUTO_SILENT) for a given org/task."""
    store = store or _default_store
    st = store.get(org_id, task_type)
    return decide(st.current_level, task_type, confidence)


def record_outcome(
    org_id: str,
    task_type: str,
    *,
    verified_correct: bool,
    human_override: bool = False,
    confidence: float | None = None,
    store: Optional[TrustStore] = None,
    sheet_mirror: Optional[Callable[[TrustState], None]] = None,
) -> TrustState:
    """Apply promotion/demotion, persist, audit, and optionally mirror to the Sheet (§3.3–3.6)."""
    store = store or _default_store
    prev = store.get(org_id, task_type)
    new_state, reason = apply_outcome(prev, verified_correct=verified_correct, human_override=human_override)
    store.put(new_state, reason)
    store.append_audit(
        org_id,
        {
            "task_type": task_type,
            "prev_level": prev.current_level,
            "new_level": new_state.current_level,
            "counter": new_state.consecutive_verified_correct,
            "cap": new_state.cap,
            "verified_correct": verified_correct,
            "human_override": human_override,
            "confidence": confidence,
            "reason": reason,
        },
    )
    if sheet_mirror is not None:
        sheet_mirror(new_state)
    return new_state
