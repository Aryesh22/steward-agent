"""Trust Ratchet tests.  Spec: IMPLEMENTATION_PLAN.md §3.  Phase: P1.3.

Fully offline (InMemoryTrustStore). Target: 100% branch coverage of app/ratchet.py.
"""
from __future__ import annotations

import pytest

from app import ratchet
from app.ratchet import (
    AUTO_NOTIFY,
    AUTO_SILENT,
    ESCALATE,
    InMemoryTrustStore,
    L_ASSISTED,
    L_AUTONOMOUS,
    L_SUPERVISED,
    TrustState,
    apply_outcome,
    decide,
    decision_for,
    default_state,
    effective_level,
    gate_passes,
    record_outcome,
)


# --------------------------------------------------------------------------- config / caps
def test_config_loads_and_has_all_task_caps():
    caps = ratchet.load_config()["task_caps"]
    expected = {
        "volunteer_reminder", "shift_backfill", "grant_deadline_alert", "donation_match",
        "grant_report_draft", "grant_report_file", "money_movement", "pii_disclosure",
    }
    assert expected.issubset(caps.keys())


def test_hard_capped_tasks_are_l0():
    for t in ("grant_report_file", "money_movement", "pii_disclosure"):
        assert ratchet.task_cap(t) == 0, f"{t} must be permanently L0 (always ask)"


def test_effective_level_never_exceeds_cap():
    assert effective_level(2, "grant_report_file") == 0     # earned L2 but capped L0
    assert effective_level(2, "volunteer_reminder") == 2
    assert effective_level(2, "donation_match") == 1        # capped L1
    assert effective_level(1, "donation_match") == 1
    assert effective_level(0, "volunteer_reminder") == 0


# --------------------------------------------------------------------------- confidence gate
def test_confidence_gate_uses_cost_ratio():
    # volunteer_reminder: cost_ratio 0.30 -> threshold max(0.70, floor 0.55) = 0.70
    assert ratchet.confidence_threshold("volunteer_reminder") == pytest.approx(0.70)
    assert ratchet.confidence_gate("volunteer_reminder", 0.70) is True
    assert ratchet.confidence_gate("volunteer_reminder", 0.699) is False


def test_confidence_floor_applies_when_cost_ratio_high():
    # donation_match: cost_ratio 0.10 -> 0.90 (floor doesn't bind)
    assert ratchet.confidence_threshold("donation_match") == pytest.approx(0.90)


# --------------------------------------------------------------------------- decide()
def test_decide_l0_always_escalates_even_with_full_confidence():
    assert decide(0, "volunteer_reminder", 1.0) == ESCALATE
    # capped-L0 task: even if "earned" L2, still escalate
    assert decide(2, "grant_report_file", 1.0) == ESCALATE


def test_decide_escalates_when_confidence_below_threshold():
    assert decide(2, "volunteer_reminder", 0.60) == ESCALATE     # below 0.70


def test_decide_l1_auto_notify():
    assert decide(1, "volunteer_reminder", 0.95) == AUTO_NOTIFY
    assert decide(2, "donation_match", 0.95) == AUTO_NOTIFY       # capped at L1 -> notify


def test_decide_l2_auto_silent():
    assert decide(2, "volunteer_reminder", 0.95) == AUTO_SILENT


# --------------------------------------------------------------------------- apply_outcome (pure)
def _state(level, counter, task="volunteer_reminder"):
    return TrustState("org", task, level, counter, ratchet.task_cap(task))


def test_increment_below_threshold():
    new, reason = apply_outcome(_state(0, 0), verified_correct=True, human_override=False)
    assert new.current_level == 0 and new.consecutive_verified_correct == 1
    assert reason == "increment"


def test_promotes_after_threshold_verified_correct():
    thr = ratchet.promotion_threshold()
    new, reason = apply_outcome(_state(0, thr - 1), verified_correct=True, human_override=False)
    assert new.current_level == 1 and new.consecutive_verified_correct == 0
    assert reason.startswith("promote")


def test_promotion_is_one_level_at_a_time():
    thr = ratchet.promotion_threshold()
    new, _ = apply_outcome(_state(1, thr - 1), verified_correct=True, human_override=False)
    assert new.current_level == 2  # not 3, not skipping


def test_no_promotion_above_cap():
    thr = ratchet.promotion_threshold()
    # donation_match cap = 1; at L1 with a full counter, must NOT promote to 2
    new, reason = apply_outcome(_state(1, thr - 1, task="donation_match"),
                                verified_correct=True, human_override=False)
    assert new.current_level == 1
    assert reason == "increment"


def test_demotes_on_verified_error():
    new, reason = apply_outcome(_state(2, 3), verified_correct=False, human_override=False)
    assert new.current_level == 1 and new.consecutive_verified_correct == 0
    assert reason == "demote:verified_error"


def test_demotes_on_human_override_even_if_correct():
    new, reason = apply_outcome(_state(2, 3), verified_correct=True, human_override=True)
    assert new.current_level == 1 and new.consecutive_verified_correct == 0
    assert reason == "demote:human_override"


def test_demotion_floors_at_l0():
    new, _ = apply_outcome(_state(0, 0), verified_correct=False, human_override=False)
    assert new.current_level == 0


# --------------------------------------------------------------------------- stateful API + store
def test_gate_passes_reads_store():
    store = InMemoryTrustStore()
    # default level 0 -> escalate -> gate False
    assert gate_passes("org", "volunteer_reminder", 0.99, store=store) is False
    store.put(TrustState("org", "volunteer_reminder", 2, 0, 2), "seed")
    assert gate_passes("org", "volunteer_reminder", 0.99, store=store) is True


def test_decision_for_reflects_stored_level():
    store = InMemoryTrustStore()
    store.put(TrustState("org", "volunteer_reminder", 1, 0, 2), "seed")
    assert decision_for("org", "volunteer_reminder", 0.99, store=store) == AUTO_NOTIFY


def test_record_outcome_graduates_a_task_over_time():
    store = InMemoryTrustStore()
    thr = ratchet.promotion_threshold()
    # feed exactly `thr` verified-correct actions -> promote L0 -> L1
    for _ in range(thr):
        st = record_outcome("org", "volunteer_reminder", verified_correct=True, store=store)
    assert st.current_level == 1
    assert len(store.audit) == thr
    assert store.audit[-1]["reason"].startswith("promote")


def test_record_outcome_l0_capped_task_never_graduates():
    store = InMemoryTrustStore()
    for _ in range(ratchet.promotion_threshold() * 3):
        st = record_outcome("org", "grant_report_file", verified_correct=True, store=store)
    assert st.current_level == 0  # cap L0 forever


def test_record_outcome_mirror_callback_invoked():
    store = InMemoryTrustStore()
    seen: list[TrustState] = []
    record_outcome("org", "volunteer_reminder", verified_correct=True,
                   store=store, sheet_mirror=seen.append)
    assert len(seen) == 1 and seen[0].task_type == "volunteer_reminder"


def test_institutional_persistence_is_keyed_by_org_not_user():
    # two orgs advance independently; state survives regardless of "who" acted
    store = InMemoryTrustStore()
    thr = ratchet.promotion_threshold()
    for _ in range(thr):
        record_outcome("org-A", "volunteer_reminder", verified_correct=True, store=store)
    a = store.get("org-A", "volunteer_reminder")
    b = store.get("org-B", "volunteer_reminder")
    assert a.current_level == 1        # org-A graduated
    assert b.current_level == 0        # org-B untouched -> starts fresh (default)


def test_default_state_starts_assisted():
    st = default_state("org", "volunteer_reminder")
    assert st.current_level == L_ASSISTED and st.consecutive_verified_correct == 0


def test_set_default_store_used_when_no_store_passed():
    store = InMemoryTrustStore()
    store.put(TrustState("org", "volunteer_reminder", 2, 0, 2), "seed")
    ratchet.set_default_store(store)
    try:
        # no explicit store -> uses the injected default
        assert gate_passes("org", "volunteer_reminder", 0.99) is True
    finally:
        ratchet.set_default_store(InMemoryTrustStore())  # reset global
