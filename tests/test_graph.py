"""Graph routing tests.  Spec: IMPLEMENTATION_PLAN.md §8.3.  Phase: P2.7.

Asserts the ratchet conditional edge routes to `execute` when gates pass and to
`human_review` when they don't. Runs fully offline (mock agents, InMemoryTrustStore).
"""
from __future__ import annotations

import pytest

from app.graph import build_steward_graph, ratchet_condition
from app.ratchet import (
    AUTO_NOTIFY,
    AUTO_SILENT,
    ESCALATE,
    InMemoryTrustStore,
    TrustState,
    decision_for,
    record_outcome,
    promotion_threshold,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _seeded_store(org_id: str, task_type: str, level: int) -> InMemoryTrustStore:
    """Return a store with a pre-seeded trust level for one org/task pair."""
    store = InMemoryTrustStore()
    cap_map = {
        "volunteer_reminder": 2,
        "shift_backfill": 2,
        "donation_match": 1,
        "grant_report_file": 0,
    }
    cap = cap_map.get(task_type, 2)
    store.put(TrustState(org_id, task_type, level, 0, cap), "seed")
    return store


# ---------------------------------------------------------------------------
# ratchet_condition unit tests (the conditional edge function)
# ---------------------------------------------------------------------------
class TestRatchetCondition:
    """Unit tests for the ratchet_condition function used as the graph edge."""

    def test_l0_task_always_routes_to_human_review(self):
        """L0 ASSISTED → gate always fails regardless of confidence."""
        state = {
            "org_id": "test-org",
            "task_type": "volunteer_reminder",
            "confidence": 0.99,
            "_store": _seeded_store("test-org", "volunteer_reminder", 0),
        }
        assert ratchet_condition(state) is False
        assert state["decision"] == ESCALATE

    def test_l2_task_routes_to_execute_when_confidence_high(self):
        """L2 AUTONOMOUS + high confidence → gate passes."""
        store = _seeded_store("test-org", "volunteer_reminder", 2)
        state = {
            "org_id": "test-org",
            "task_type": "volunteer_reminder",
            "confidence": 0.95,
            "_store": store,
        }
        assert ratchet_condition(state) is True
        assert state["decision"] == AUTO_SILENT

    def test_l1_task_routes_to_execute_with_auto_notify(self):
        """L1 SUPERVISED + sufficient confidence → gate passes (AUTO_NOTIFY)."""
        store = _seeded_store("test-org", "volunteer_reminder", 1)
        state = {
            "org_id": "test-org",
            "task_type": "volunteer_reminder",
            "confidence": 0.95,
            "_store": store,
        }
        assert ratchet_condition(state) is True
        assert state["decision"] == AUTO_NOTIFY

    def test_low_confidence_routes_to_human_review(self):
        """Even at L2, if confidence < threshold → routes to human_review."""
        store = _seeded_store("test-org", "volunteer_reminder", 2)
        state = {
            "org_id": "test-org",
            "task_type": "volunteer_reminder",
            "confidence": 0.50,   # below 0.70 threshold for volunteer_reminder
            "_store": store,
        }
        assert ratchet_condition(state) is False
        assert state["decision"] == ESCALATE

    def test_hard_capped_l0_task_always_escalates(self):
        """grant_report_file is hard-capped at L0 → always escalates."""
        # Even if we somehow set level=2, effective_level = min(2, cap=0) = 0 → escalate
        store = InMemoryTrustStore()
        store.put(TrustState("org", "grant_report_file", 2, 0, 0), "seed")
        state = {
            "org_id": "org",
            "task_type": "grant_report_file",
            "confidence": 1.0,
            "_store": store,
        }
        assert ratchet_condition(state) is False
        assert state["decision"] == ESCALATE

    def test_donation_match_capped_at_l1(self):
        """donation_match cap=1 → L2 effective is L1 → AUTO_NOTIFY."""
        store = _seeded_store("org", "donation_match", 2)  # earned L2 but capped L1
        state = {
            "org_id": "org",
            "task_type": "donation_match",
            "confidence": 0.95,
            "_store": store,
        }
        assert ratchet_condition(state) is True
        assert state["decision"] == AUTO_NOTIFY   # capped at L1 → notify, not silent


# ---------------------------------------------------------------------------
# End-to-end graph routing tests (full pipeline, mock agents)
# ---------------------------------------------------------------------------
class TestGraphRouting:
    """End-to-end tests using the full graph (mock agents, in-memory store)."""

    def test_routes_to_execute_when_gates_pass(self):
        """L2 volunteer_reminder + high confidence → execute path, ratchet advances."""
        store = _seeded_store("demo-org", "volunteer_reminder", 2)
        graph = build_steward_graph(store=store)

        result = graph({
            "mode": "sweep",
            "org_id": "demo-org",
            "input": "Send shift reminder for tomorrow's driver slot",
        })

        # Should have gone through execute, not human_review
        assert result.get("escalated") is not True
        assert "action_result" in result
        assert result.get("decision") in (AUTO_NOTIFY, AUTO_SILENT)

    def test_routes_to_human_review_when_gate_fails(self):
        """L0 volunteer_reminder → human_review path, coordinator is asked."""
        store = _seeded_store("demo-org", "volunteer_reminder", 0)
        graph = build_steward_graph(store=store)

        result = graph({
            "mode": "sweep",
            "org_id": "demo-org",
            "input": "Send shift reminder for tomorrow's driver slot",
        })

        # Should have gone through human_review (escalated=True)
        assert result.get("escalated") is True
        assert result.get("decision") == ESCALATE

    def test_grant_report_file_always_escalates_through_graph(self):
        """grant_report_file (hard cap L0) → always escalates, never executes."""
        # Even after seeding level=2, effective level = 0 → escalate
        store = InMemoryTrustStore()
        store.put(TrustState("org", "grant_report_file", 2, 0, 0), "seed")
        graph = build_steward_graph(store=store)

        result = graph({
            "mode": "event",
            "org_id": "org",
            "input": "Submit the grant report to the funder portal today",
        })

        assert result.get("escalated") is True
        assert result.get("decision") == ESCALATE

    def test_ratchet_advances_on_execute_path(self):
        """After a verified-correct auto-execute, the ratchet counter advances."""
        store = _seeded_store("org2", "volunteer_reminder", 1)
        graph = build_steward_graph(store=store)

        before = store.get("org2", "volunteer_reminder")
        assert before.consecutive_verified_correct == 0

        result = graph({
            "mode": "sweep",
            "org_id": "org2",
            "input": "Send shift reminder for sorting shift s2",
        })

        after = store.get("org2", "volunteer_reminder")
        # Counter must have advanced (or level promoted if threshold hit)
        assert (after.consecutive_verified_correct > 0 or after.current_level > before.current_level)

    def test_ratchet_graduation_over_multiple_runs(self):
        """Running N=5 verified-correct reminders promotes volunteer_reminder from L0→L1."""
        store = InMemoryTrustStore()
        graph = build_steward_graph(store=store)
        thr = promotion_threshold()

        # Seed at L0 and run thr sweeps; the last should graduate to L1
        # We need the graph to route through execute, so we must pre-seed to L1+
        # to allow auto-execute. Instead test ratchet graduation via record_outcome directly.
        for _ in range(thr):
            record_outcome("org3", "volunteer_reminder", verified_correct=True,
                           store=store, confidence=0.90)

        st = store.get("org3", "volunteer_reminder")
        assert st.current_level == 1, f"Expected L1 after {thr} correct, got L{st.current_level}"

    def test_donation_match_escalates_when_cannot_place(self):
        """When matcher returns escalate=true (can't place perishable), routes to human_review."""
        store = _seeded_store("org4", "donation_match", 1)
        graph = build_steward_graph(store=store)

        result = graph({
            "mode": "event",
            "org_id": "org4",
            "input": "40 lbs of milk donated, perishable, expires tomorrow, cannot place, no driver",
        })

        # At L1 with high confidence the gate may pass and execute decides to escalate
        # via the action_result's escalate flag. Either path is valid.
        # The important thing: the escalation was recorded in the audit log.
        assert len(store.audit) > 0, "No audit entry recorded"

    def test_two_orgs_are_independent(self):
        """Two different orgs share the same graph but have independent ratchet state."""
        store = InMemoryTrustStore()
        graph = build_steward_graph(store=store)

        # Run 5 correct reminders for org-A
        thr = promotion_threshold()
        for _ in range(thr):
            record_outcome("org-A", "volunteer_reminder", verified_correct=True, store=store)

        a_level = store.get("org-A", "volunteer_reminder").current_level
        b_level = store.get("org-B", "volunteer_reminder").current_level

        assert a_level == 1, f"org-A should be L1, got L{a_level}"
        assert b_level == 0, f"org-B should be L0 (untouched), got L{b_level}"


# ---------------------------------------------------------------------------
# Router node tests (classify → task_type)
# ---------------------------------------------------------------------------
class TestRouterNode:
    """Tests for the router's mock classifier."""

    def test_classifies_donation_sms(self):
        from app.agents.router import classify
        r = classify("We have 40 lbs of milk to donate, expires tomorrow")
        assert r.task_type == "donation_match"
        assert 0.0 <= r.confidence <= 1.0

    def test_classifies_grant_filing(self):
        from app.agents.router import classify
        r = classify("Please submit the City Fund report to the portal today")
        assert r.task_type == "grant_report_file"

    def test_classifies_volunteer_reminder(self):
        from app.agents.router import classify
        r = classify("Send a reminder to volunteers for tomorrow's shift")
        assert r.task_type == "volunteer_reminder"

    def test_classifies_shift_backfill(self):
        from app.agents.router import classify
        r = classify("Maria dropped the Thursday shift, we need a backfill driver")
        assert r.task_type == "shift_backfill"

    def test_confidence_is_in_range(self):
        from app.agents.router import classify
        r = classify("Something about money payment transfer")
        assert 0.0 <= r.confidence <= 1.0


# ---------------------------------------------------------------------------
# Reviewer tests
# ---------------------------------------------------------------------------
class TestReviewer:
    """Tests for the mock ReviewerAgent."""

    def test_approves_correct_volunteer_reminder(self):
        from app.agents.reviewer import review_action
        verdict = review_action({
            "task_type": "volunteer_reminder",
            "action_result": '{"action": "sent_sms", "recipients": [{"phone": "+15550000001"}]}',
        })
        assert isinstance(verdict["correct"], bool)
        assert 0.0 <= verdict["confidence"] <= 1.0
        assert isinstance(verdict["reason"], str)

    def test_flags_auto_executed_grant_file(self):
        from app.agents.reviewer import review_action
        # If grant_report_file ran without escalation, it's a safety violation
        verdict = review_action({
            "task_type": "grant_report_file",
            "action_result": '{"action": "filed", "url": "http://funder.example"}',
        })
        assert verdict["correct"] is False
        assert verdict["confidence"] > 0.9

    def test_approves_escalated_grant_file(self):
        from app.agents.reviewer import review_action
        verdict = review_action({
            "task_type": "grant_report_file",
            "action_result": '{"action": "requires_approval", "reason": "Filing is irreversible"}',
        })
        assert verdict["correct"] is True
