"""Google Sheets tool.  Spec: IMPLEMENTATION_PLAN.md §6.1, §8.7.  Phase: P1.6 (local) -> P4.2 (Gateway).

Reads/writes the org's spreadsheet tabs (Volunteers, Shifts, Donations, Needs, Grants, TrustState, AuditLog).
Start as a local Strands @tool calling the Sheets REST API; migrate to an AgentCore Gateway OpenAPI target in P4.
"""
from __future__ import annotations

import os

SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")


def read_tab(tab: str) -> list[dict]:
    """Return rows of a tab as dicts keyed by header. P1.6."""
    raise NotImplementedError("P1.6")


def update_row(tab: str, key_col: str, key_val: str, updates: dict) -> None:
    """Update a row identified by key_col == key_val. P1.6."""
    raise NotImplementedError("P1.6")


def append_row(tab: str, row: dict) -> None:
    """Append a row (e.g. AuditLog / TrustState mirror). P1.6."""
    raise NotImplementedError("P1.6")
