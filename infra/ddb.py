"""DynamoDB — trust state + audit journal.  Spec: IMPLEMENTATION_PLAN.md §6.2.  Phase: P1.4/P1.5.

Implements the ratchet.TrustStore protocol against DynamoDB so production uses the exact same
logic the tests prove with InMemoryTrustStore.

Tables:
  steward_trust  (PK org_id, SK task_type)  — current_level, consecutive_verified_correct, cap, updated_at, last_reason
  steward_audit  (PK org_id, SK ts#uuid)    — append-only action log

Counters use conditional/atomic writes to avoid sweep/inbound races.
Requires AWS creds + the tables to exist (create_tables()). Not exercised by offline unit tests.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import boto3

from app.ratchet import TrustState, default_state

TRUST_TABLE = os.getenv("DDB_TRUST_TABLE", "steward_trust")
AUDIT_TABLE = os.getenv("DDB_AUDIT_TABLE", "steward_audit")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resource(region: str | None = None):
    return boto3.resource("dynamodb", region_name=region or os.getenv("AWS_REGION", "us-west-2"))


def create_tables(region: str | None = None) -> None:
    """Create both tables if absent (on-demand billing). Idempotent. P1.4."""
    ddb = _resource(region)
    existing = {t.name for t in ddb.tables.all()}
    if TRUST_TABLE not in existing:
        ddb.create_table(
            TableName=TRUST_TABLE,
            KeySchema=[{"AttributeName": "org_id", "KeyType": "HASH"},
                       {"AttributeName": "task_type", "KeyType": "RANGE"}],
            AttributeDefinitions=[{"AttributeName": "org_id", "AttributeType": "S"},
                                  {"AttributeName": "task_type", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        ).wait_until_exists()
    if AUDIT_TABLE not in existing:
        ddb.create_table(
            TableName=AUDIT_TABLE,
            KeySchema=[{"AttributeName": "org_id", "KeyType": "HASH"},
                       {"AttributeName": "sk", "KeyType": "RANGE"}],
            AttributeDefinitions=[{"AttributeName": "org_id", "AttributeType": "S"},
                                  {"AttributeName": "sk", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        ).wait_until_exists()


class DynamoDBTrustStore:
    """ratchet.TrustStore backed by DynamoDB (§6.2)."""

    def __init__(self, region: str | None = None) -> None:
        ddb = _resource(region)
        self._trust = ddb.Table(TRUST_TABLE)
        self._audit = ddb.Table(AUDIT_TABLE)

    def get(self, org_id: str, task_type: str) -> TrustState:
        item = self._trust.get_item(Key={"org_id": org_id, "task_type": task_type}).get("Item")
        if not item:
            return default_state(org_id, task_type)
        return TrustState(
            org_id=org_id,
            task_type=task_type,
            current_level=int(item["current_level"]),
            consecutive_verified_correct=int(item["consecutive_verified_correct"]),
            cap=int(item["cap"]),
        )

    def put(self, state: TrustState, reason: str) -> None:
        self._trust.put_item(Item={
            "org_id": state.org_id,
            "task_type": state.task_type,
            "current_level": state.current_level,
            "consecutive_verified_correct": state.consecutive_verified_correct,
            "cap": state.cap,
            "updated_at": _now_iso(),
            "last_reason": reason,
        })

    def append_audit(self, org_id: str, entry: dict) -> None:
        ts = _now_iso()
        item = {"org_id": org_id, "sk": f"{ts}#{uuid.uuid4()}", "ts": ts}
        # DynamoDB rejects float; callers pass confidence as float -> stringify defensively.
        for k, v in entry.items():
            item[k] = str(v) if isinstance(v, float) else v
        self._audit.put_item(Item=item)
