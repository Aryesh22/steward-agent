"""Seed the demo Google Sheet with realistic data.  Spec: §6.1.  Phase: P1.7.

Writes headers + rows for every tab so the local demo has something to act on.
Run after setting GOOGLE_SHEET_ID + GOOGLE_SERVICE_ACCOUNT_FILE (see SETUP.md) and sharing
the Sheet with the service-account email.

    python scripts/seed_sheet.py
"""
from __future__ import annotations

# Demo org: a 3-person food pantry. Phone numbers are placeholders — replace with test numbers.
SEED = {
    "Volunteers": {
        "header": ["volunteer_id", "name", "phone_e164", "skills", "availability",
                   "last_contacted", "reliability_note"],
        "rows": [
            ["v1", "Maria",  "+15550000001", "driver",        "Tue,Thu", "", "reliable"],
            ["v2", "Devon",  "+15550000002", "sorting",       "Mon,Wed", "", ""],
            ["v3", "Aisha",  "+15550000003", "driver,intake", "Fri,Sat", "", "prefers mornings"],
            ["v4", "Sam",    "+15550000004", "driver",        "Thu",     "", "occasional no-show"],
        ],
    },
    "Shifts": {
        "header": ["shift_id", "date", "start", "end", "role", "needed_count",
                   "assigned_ids", "status", "notes"],
        "rows": [
            ["s1", "2026-09-10", "09:00", "12:00", "driver",  "1", "v1", "filled", ""],
            ["s2", "2026-09-11", "14:00", "17:00", "sorting", "2", "v2", "at_risk", "1 slot open"],
            ["s3", "2026-09-12", "08:00", "11:00", "driver",  "1", "",   "open",   ""],
        ],
    },
    "Donations": {
        "header": ["donation_id", "received_at", "item", "qty", "unit", "perishable",
                   "expiry", "donor", "status", "matched_need_id"],
        "rows": [
            ["d1", "2026-09-09", "milk",   "40", "lbs", "TRUE",  "2026-09-11", "GreenGrocer", "new", ""],
            ["d2", "2026-09-09", "canned beans", "120", "cans", "FALSE", "", "FoodCo", "new", ""],
        ],
    },
    "Needs": {
        "header": ["need_id", "item", "qty_needed", "location", "priority", "window_end", "status"],
        "rows": [
            ["n1", "milk", "30", "North shelter", "high", "2026-09-10", "open"],
            ["n2", "canned goods", "200", "Main pantry", "medium", "2026-09-20", "open"],
        ],
    },
    "Grants": {
        "header": ["grant_id", "funder", "amount", "award_date", "report_due", "status", "report_url"],
        "rows": [
            ["g1", "City Community Fund", "5000", "2026-06-01", "2026-09-15", "active", ""],
        ],
    },
    "TrustState": {  # written by Steward at runtime; seed just the header
        "header": ["task_type", "current_level", "consecutive_verified_correct", "cap"],
        "rows": [],
    },
    "AuditLog": {
        "header": ["ts", "task_type", "action", "level", "confidence", "outcome",
                   "reviewer_verdict", "escalated", "notes"],
        "rows": [],
    },
}


def main() -> None:
    from app.tools.sheets import _service, _sheet_id  # local import so module stays importable

    svc = _service().spreadsheets().values()
    sid = _sheet_id()
    for tab, spec in SEED.items():
        values = [spec["header"], *spec["rows"]]
        svc.update(
            spreadsheetId=sid,
            range=f"{tab}!A1",
            valueInputOption="USER_ENTERED",
            body={"values": values},
        ).execute()
        print(f"seeded {tab}: {len(spec['rows'])} rows")


if __name__ == "__main__":  # pragma: no cover
    main()
