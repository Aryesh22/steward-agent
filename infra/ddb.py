"""DynamoDB — trust state + audit journal.  Spec: IMPLEMENTATION_PLAN.md §6.2.  Phase: P1.4/P1.5.

Tables:
  steward_trust  (PK org_id, SK task_type)  — current_level, consecutive_verified_correct, cap, updated_at, last_reason
  steward_audit  (PK org_id, SK ts#uuid)    — append-only action log
Use ATOMIC conditional updates for counters to avoid sweep/inbound races.
"""
from __future__ import annotations

import os

TRUST_TABLE = os.getenv("DDB_TRUST_TABLE", "steward_trust")
AUDIT_TABLE = os.getenv("DDB_AUDIT_TABLE", "steward_audit")


def create_tables() -> None:
    """Create both tables if absent. P1.4."""
    raise NotImplementedError("P1.4")


def get_trust(org_id: str, task_type: str) -> dict | None:
    """Read trust state. P1.5."""
    raise NotImplementedError("P1.5")


def put_trust(org_id: str, task_type: str, current_level: int, counter: int, cap: int, reason: str) -> None:
    """Write trust state (atomic conditional). P1.5."""
    raise NotImplementedError("P1.5")


def append_audit(org_id: str, entry: dict) -> None:
    """Append an audit entry. P1.5."""
    raise NotImplementedError("P1.5")
