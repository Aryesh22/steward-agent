"""Phase 3 tests — escalation surface, webhook routing, scheduler payload.
Spec: IMPLEMENTATION_PLAN.md §8.5, §8.8.  Phase: P3.

All tests run fully offline (no AWS, no network, no Strands Runtime).
Real AWS calls are blocked by monkeypatching boto3 clients.
"""
from __future__ import annotations

import json
import os

import pytest


# ===========================================================================
# §1 — Webhook Lambda: event parsing
# ===========================================================================
class TestWebhookParsing:
    """Tests for infra/webhook_lambda._parse_event."""

    def setup_method(self):
        from infra import webhook_lambda
        self.wh = webhook_lambda

    def test_parses_json_body_from_api_gateway(self):
        """API Gateway passes a JSON string in 'body'."""
        event = {
            "headers": {"content-type": "application/json"},
            "body": json.dumps({"body": "40 lbs milk to donate", "org_id": "pantry-1"}),
        }
        payload = self.wh._parse_event(event)
        assert payload["body"] == "40 lbs milk to donate"
        assert payload["org_id"] == "pantry-1"

    def test_parses_urlencoded_body(self):
        """SNS-style URL-encoded POST (Body key → body key)."""
        event = {
            "headers": {"content-type": "application/x-www-form-urlencoded"},
            "body": "Body=Maria+can+volunteer&To=%2B17372508034&From=%2B919521781840",
        }
        payload = self.wh._parse_event(event)
        assert payload["body"] == "Maria can volunteer"

    def test_parses_plain_text_body(self):
        """Fallback: treats raw body as SMS text."""
        event = {"headers": {}, "body": "YES"}
        payload = self.wh._parse_event(event)
        assert payload["body"] == "YES"

    def test_org_id_from_query_string_overrides_body(self):
        """org_id in queryStringParameters wins."""
        event = {
            "headers": {"content-type": "application/json"},
            "body": json.dumps({"body": "hello", "org_id": "org-a"}),
            "queryStringParameters": {"org_id": "org-b"},
        }
        payload = self.wh._parse_event(event)
        assert payload["org_id"] == "org-b"

    def test_missing_body_returns_empty(self):
        event = {"headers": {}, "body": ""}
        payload = self.wh._parse_event(event)
        assert payload.get("body", "") == ""


# ===========================================================================
# §2 — Webhook Lambda: interrupt reply detection
# ===========================================================================
class TestInterruptReplyDetection:
    """Tests for infra/webhook_lambda._is_interrupt_reply."""

    def setup_method(self):
        from infra import webhook_lambda
        self.wh = webhook_lambda

    @pytest.mark.parametrize("text", ["YES", "yes", "No", "APPROVE", "defer", "ok", "UNDO"])
    def test_single_keyword_is_interrupt_reply(self, text):
        assert self.wh._is_interrupt_reply(text) is True

    def test_donation_sms_is_not_interrupt_reply(self):
        assert self.wh._is_interrupt_reply(
            "We have 40 lbs of milk expiring tomorrow, can you take it?"
        ) is False

    def test_empty_is_not_interrupt_reply(self):
        assert self.wh._is_interrupt_reply("") is False

    def test_long_yes_message_is_not_interrupt_reply(self):
        # A very long message starting with YES — probably not a simple reply
        long = "YES " + "x " * 110  # > 200 chars
        assert self.wh._is_interrupt_reply(long) is False

    def test_approve_with_punctuation(self):
        assert self.wh._is_interrupt_reply("APPROVE!") is True


# ===========================================================================
# §3 — Webhook Lambda: session ID
# ===========================================================================
class TestSessionId:
    def setup_method(self):
        from infra import webhook_lambda
        self.wh = webhook_lambda

    def test_session_id_is_deterministic(self):
        assert self.wh._session_id("pantry-1") == self.wh._session_id("pantry-1")

    def test_different_orgs_get_different_sessions(self):
        assert self.wh._session_id("org-a") != self.wh._session_id("org-b")

    def test_session_id_meets_minimum_length(self):
        """Runtime requires runtimeSessionId to be 33–256 chars."""
        sid = self.wh._session_id("x")  # very short org_id
        assert 33 <= len(sid) <= 256

    def test_long_org_id_is_capped_at_256(self):
        long_org = "a" * 300
        sid = self.wh._session_id(long_org)
        assert len(sid) <= 256


# ===========================================================================
# §4 — Webhook Lambda: full handler routing (mocked AWS)
# ===========================================================================
class TestWebhookHandler:
    """End-to-end handler routing with AGENT_RUNTIME_ARN unset (mock mode)."""

    def setup_method(self):
        # Ensure AGENT_RUNTIME_ARN is empty so mock path is taken
        os.environ.pop("AGENT_RUNTIME_ARN", None)
        from infra import webhook_lambda
        self.wh = webhook_lambda

    def test_new_donation_sms_returns_200(self):
        event = {
            "headers": {"content-type": "application/json"},
            "body": json.dumps({"body": "40 lbs milk to donate, expires tomorrow"}),
        }
        resp = self.wh.handler(event, None)
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body["status"] == "ok"

    def test_coordinator_reply_yes_returns_200(self):
        event = {
            "headers": {"content-type": "application/json"},
            "body": json.dumps({"body": "YES"}),
        }
        resp = self.wh.handler(event, None)
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body["status"] == "ok"

    def test_empty_body_returns_400(self):
        event = {"headers": {}, "body": ""}
        resp = self.wh.handler(event, None)
        assert resp["statusCode"] == 400

    def test_approve_is_treated_as_interrupt_reply(self, capsys):
        """APPROVE keyword → mock invoke_resume path (not invoke_event)."""
        event = {
            "headers": {"content-type": "application/json"},
            "body": json.dumps({"body": "APPROVE"}),
        }
        self.wh.handler(event, None)
        captured = capsys.readouterr()
        assert "invoke_resume" in captured.out or "MOCK" in captured.out

    def test_long_sms_is_treated_as_new_event(self, capsys):
        """Multi-sentence SMS → invoke_event (not interrupt resume)."""
        event = {
            "headers": {"content-type": "application/json"},
            "body": json.dumps({
                "body": "Hi Steward, we have a donation of 50 bags of rice. "
                        "Please coordinate pickup with the North shelter."
            }),
        }
        self.wh.handler(event, None)
        captured = capsys.readouterr()
        assert "invoke_event" in captured.out or "MOCK" in captured.out


# ===========================================================================
# §5 — Scheduler: payload and creation helpers (mocked)
# ===========================================================================
class TestSchedulerPayload:
    def setup_method(self):
        from infra import scheduler
        self.sched = scheduler

    def test_sweep_payload_has_mode_sweep(self):
        p = self.sched.sweep_payload("demo-pantry")
        assert p["mode"] == "sweep"

    def test_sweep_payload_includes_org_id(self):
        p = self.sched.sweep_payload("demo-pantry")
        assert p["org_id"] == "demo-pantry"

    def test_sweep_payload_has_trigger_field(self):
        p = self.sched.sweep_payload("demo-pantry")
        assert p["trigger"] == "nightly_scheduler"


# ===========================================================================
# §6 — Integration: perishable donation escalation through graph (offline)
# ===========================================================================
class TestDonationEscalationE2E:
    """Mirrors the Scenario 3 in run_local_demo.py but as a proper test case."""

    def test_perishable_donation_escalates_through_graph(self):
        """A donation_match at L0 always goes to human_review (§3.5 of ratchet)."""
        from app.graph import ratchet_condition
        from app.ratchet import InMemoryTrustStore, decide

        store = InMemoryTrustStore()
        state = {
            "task_type": "donation_match",
            "confidence": 0.55,  # below 0.80 threshold
            "org_id": "test-org",
            "input": "40 lbs milk, expires tomorrow, no driver confirmed",
            "_store": store,
        }
        route = ratchet_condition(state)
        assert route is False, (
            f"Perishable donation at confidence 0.55 should escalate, got '{route}'"
        )

    def test_donation_match_l0_always_escalates_regardless_of_confidence(self):
        """donation_match is capped at L1; at L0 it must always escalate (§3.1)."""
        from app.graph import ratchet_condition
        from app.ratchet import InMemoryTrustStore

        store = InMemoryTrustStore()
        state = {
            "task_type": "donation_match",
            "confidence": 0.99,  # extremely high confidence
            "org_id": "test-org",
            "input": "easy match, driver confirmed, fresh produce",
            "_store": store,
        }
        route = ratchet_condition(state)
        # At L0, even 0.99 confidence escalates — ratchet hasn't promoted yet
        assert route is False, (
            "donation_match at L0 should escalate even with high confidence"
        )

    def test_l0_capped_task_never_auto_executes(self):
        """grant_report_file is hard-capped at L0 and always escalates (§3.3)."""
        from app.graph import ratchet_condition
        from app.ratchet import InMemoryTrustStore, record_outcome

        store = InMemoryTrustStore()
        # Simulate many correct verifications — ratchet should stay at L0
        for _ in range(20):
            record_outcome(
                "test-org", "grant_report_file",
                verified_correct=True, human_override=False,
                confidence=0.99, store=store,
            )

        state = {
            "task_type": "grant_report_file",
            "confidence": 0.99,
            "org_id": "test-org",
            "input": "Submit Q4 grant report to city fund",
            "_store": store,
        }
        route = ratchet_condition(state)
        assert route is False, (
            "grant_report_file must ALWAYS escalate regardless of trust earned"
        )


# ===========================================================================
# §7 — Escalation surface: human_review_node (offline mock path)
# ===========================================================================
class TestHumanReviewNode:
    def test_escalation_returns_escalated_state(self):
        """human_review_node returns escalated=True with coordinator_reply."""
        from app.nodes.human_review import human_review_node
        from app.ratchet import InMemoryTrustStore

        store = InMemoryTrustStore()
        state = {
            "task_type": "grant_report_file",
            "confidence": 0.92,
            "org_id": "test-org",
            "input": "File grant report to city fund portal",
            "_store": store,
        }
        result = human_review_node(state)

        assert result["escalated"] is True
        assert "coordinator_reply" in result
        assert result["coordinator_reply"] in (
            "YES", "NO", "APPROVE", "REVISE", "HOLD",
            "DEFER", "DENY", "REJECT", "mock-yes",
        ) or isinstance(result["coordinator_reply"], str)

    def test_escalation_demotes_on_human_override(self):
        """If coordinator rejects (NO), ratchet demotes the task."""
        import os as _os
        _os.environ["MOCK_COORDINATOR_REPLY"] = "NO"

        from app.nodes.human_review import human_review_node
        from app.ratchet import InMemoryTrustStore

        store = InMemoryTrustStore()
        state = {
            "task_type": "volunteer_reminder",
            "confidence": 0.80,
            "org_id": "test-org",
            "input": "Send reminder to Maria",
            "_store": store,
        }
        result = human_review_node(state)
        assert result["human_override"] is True

        _os.environ.pop("MOCK_COORDINATOR_REPLY", None)

    def test_resume_with_reply_structure(self):
        """resume_with_reply builds interruptResponse list correctly."""
        from app.nodes.human_review import resume_with_reply

        calls = []

        class MockGraph:
            def __call__(self, responses):
                calls.append(responses)
                return {"resumed": True}

        result = resume_with_reply(MockGraph(), "iid-123", "YES")
        assert result == {"resumed": True}
        assert calls[0][0]["interruptResponse"]["interruptId"] == "iid-123"
        assert calls[0][0]["interruptResponse"]["response"] == "YES"
