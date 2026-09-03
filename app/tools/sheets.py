"""Google Sheets tool.  Spec: IMPLEMENTATION_PLAN.md §6.1, §8.7.  Phase: P1.6 (local) -> P4.2 (Gateway).

Local implementation uses google-api-python-client with a SERVICE ACCOUNT (simplest for dev):
create a service account, download its JSON key, and SHARE the demo Sheet with the service
account's email. In production, AgentCore Identity's Google OAuth provider handles auth (P4).

Env:
  GOOGLE_SHEET_ID                 the demo spreadsheet id
  GOOGLE_SERVICE_ACCOUNT_FILE     path to the service-account JSON key
Needs live credentials to run; not exercised by offline unit tests.

Standard tabs (headers in row 1): Volunteers, Shifts, Donations, Needs, Grants, TrustState, AuditLog.
"""
from __future__ import annotations

import os
from functools import lru_cache

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


@lru_cache(maxsize=1)
def _service():
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    key_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
    if not key_file:
        raise RuntimeError("Set GOOGLE_SERVICE_ACCOUNT_FILE to the service-account JSON key path")
    creds = Credentials.from_service_account_file(key_file, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def _sheet_id() -> str:
    sid = os.getenv("GOOGLE_SHEET_ID")
    if not sid:
        raise RuntimeError("Set GOOGLE_SHEET_ID")
    return sid


def read_tab(tab: str) -> list[dict]:
    """Return rows of a tab as dicts keyed by the header row. P1.6."""
    resp = _service().spreadsheets().values().get(
        spreadsheetId=_sheet_id(), range=tab
    ).execute()
    rows = resp.get("values", [])
    if not rows:
        return []
    header, *body = rows
    out = []
    for r in body:
        r = r + [""] * (len(header) - len(r))  # pad short rows
        out.append(dict(zip(header, r)))
    return out


def append_row(tab: str, row: dict) -> None:
    """Append a row to a tab, ordering values by the existing header. P1.6."""
    header = _header(tab)
    values = [[row.get(col, "") for col in header]]
    _service().spreadsheets().values().append(
        spreadsheetId=_sheet_id(), range=tab,
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": values},
    ).execute()


def update_row(tab: str, key_col: str, key_val: str, updates: dict) -> None:
    """Update the first row where key_col == key_val. P1.6."""
    header = _header(tab)
    resp = _service().spreadsheets().values().get(
        spreadsheetId=_sheet_id(), range=tab
    ).execute()
    rows = resp.get("values", [])
    key_idx = header.index(key_col)
    for i, r in enumerate(rows[1:], start=2):  # 1-based; skip header
        if len(r) > key_idx and r[key_idx] == key_val:
            r = r + [""] * (len(header) - len(r))
            for col, val in updates.items():
                r[header.index(col)] = val
            _service().spreadsheets().values().update(
                spreadsheetId=_sheet_id(), range=f"{tab}!A{i}",
                valueInputOption="USER_ENTERED", body={"values": [r]},
            ).execute()
            return
    raise KeyError(f"No row in {tab} where {key_col}={key_val}")


def _header(tab: str) -> list[str]:
    resp = _service().spreadsheets().values().get(
        spreadsheetId=_sheet_id(), range=f"{tab}!1:1"
    ).execute()
    vals = resp.get("values", [])
    return vals[0] if vals else []



# --- Strands @tool wrappers (used by specialist agents) ---
def as_strands_tools() -> list:
    """Return Strands @tool-decorated callables for read_tab, append_row, update_row.

    Imported lazily so this module stays importable without strands installed.
    """
    from strands import tool

    @tool
    def read_sheet_tab(tab: str) -> str:
        """Read all rows from a Google Sheet tab, returned as a JSON list of dicts.

        Args:
            tab: The tab name to read (e.g. 'Volunteers', 'Shifts', 'Donations').
        """
        import json
        try:
            rows = read_tab(tab)
            return json.dumps(rows)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @tool
    def append_sheet_row(tab: str, row_json: str) -> str:
        """Append a new row to a Google Sheet tab.

        Args:
            tab: The tab name.
            row_json: JSON object with column names as keys.
        """
        import json
        try:
            row = json.loads(row_json)
            append_row(tab, row)
            return "ok"
        except Exception as e:
            return f"error: {e}"

    @tool
    def update_sheet_row(tab: str, key_col: str, key_val: str, updates_json: str) -> str:
        """Update the first row in a tab where key_col == key_val.

        Args:
            tab: The tab name.
            key_col: Column name to match (e.g. 'donation_id').
            key_val: Value to match.
            updates_json: JSON object of column → new value pairs.
        """
        import json
        try:
            updates = json.loads(updates_json)
            update_row(tab, key_col, key_val, updates)
            return "ok"
        except Exception as e:
            return f"error: {e}"

    return [read_sheet_tab, append_sheet_row, update_sheet_row]


# --- Trust-state mirror (called by ratchet.record_outcome via sheet_mirror callback, §3.6) ---
def mirror_trust_state(state) -> None:  # noqa: ANN001  (app.ratchet.TrustState)
    """Upsert the TrustState tab so the ratchet is visible to humans / on camera. P1.5."""
    from app.ratchet import LEVEL_NAMES
    row = {
        "task_type": state.task_type,
        "current_level": f"L{state.current_level} {LEVEL_NAMES[state.current_level]}",
        "consecutive_verified_correct": state.consecutive_verified_correct,
        "cap": f"L{state.cap}",
    }
    try:
        update_row("TrustState", "task_type", state.task_type, row)
    except KeyError:
        append_row("TrustState", row)
