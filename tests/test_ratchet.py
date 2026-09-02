"""Trust Ratchet tests.  Spec: IMPLEMENTATION_PLAN.md §3.  Phase: authored in P1.3.

Target: 100% branch coverage of app/ratchet.py. Until P1 implements the logic, the
behavioral tests are skipped; the pure config/ceiling tests already pass so the suite is green.
"""
from __future__ import annotations

import pytest

from app import ratchet


# --- Passing in P0: config + ceiling arithmetic (no unimplemented logic) ---

def test_config_loads_and_has_all_task_caps():
    cfg = ratchet.load_config()
    expected = {
        "volunteer_reminder", "shift_backfill", "grant_deadline_alert", "donation_match",
        "grant_report_draft", "grant_report_file", "money_movement", "pii_disclosure",
    }
    assert expected.issubset(cfg["task_caps"].keys())


def test_hard_capped_tasks_are_l0():
    for t in ("grant_report_file", "money_movement", "pii_disclosure"):
        assert ratchet.task_cap(t) == 0, f"{t} must be permanently L0 (always ask)"


def test_effective_level_never_exceeds_cap():
    # even a fully-earned L2 cannot exceed an L0 cap
    assert ratchet.effective_level(2, "grant_report_file") == 0
    assert ratchet.effective_level(2, "volunteer_reminder") == 2
    assert ratchet.effective_level(1, "donation_match") == 1
    assert ratchet.effective_level(2, "donation_match") == 1


# --- Skipped until P1.2 implements the logic bodies ---

@pytest.mark.skip(reason="P1.2: implement confidence_gate")
def test_confidence_gate_uses_cost_ratio():
    # auto-act only if confidence >= 1 - cost_ratio, and >= global floor
    assert ratchet.confidence_gate("volunteer_reminder", 0.75) is True   # 1-0.30=0.70
    assert ratchet.confidence_gate("volunteer_reminder", 0.60) is False


@pytest.mark.skip(reason="P1.2: implement gate_passes")
def test_gate_passes_combines_autonomy_and_confidence():
    ...


@pytest.mark.skip(reason="P1.2: implement record_outcome promotion")
def test_promotes_after_threshold_verified_correct():
    ...


@pytest.mark.skip(reason="P1.2: implement record_outcome demotion")
def test_demotes_on_verified_error_or_override():
    ...


@pytest.mark.skip(reason="P1.2: promotion moves exactly one level")
def test_promotion_is_one_level_at_a_time():
    ...
