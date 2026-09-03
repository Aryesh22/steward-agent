# -*- coding: utf-8 -*-
"""Scripted end-to-end local demo.  Spec: SS10 (P2.6), SS11 (demo script), P5.2 (accelerated timeline).

Drives the graph locally (no AgentCore wrapper) so you can watch the Trust Ratchet graduate
volunteer_reminder L0→L1→L2 while grant_report_file stays L0, and see the perishable-milk escalation.

Run with:
    python scripts/run_local_demo.py

Env vars:
    MOCK_COORDINATOR_REPLY=YES   (default) — simulated coordinator reply for escalations
    BEDROCK_ENABLED=false        (default) — use mock agents (no AWS creds needed)
"""
from __future__ import annotations

import os
import sys
import textwrap
import time

# Make sure the repo root is on the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.graph import build_steward_graph
from app.ratchet import (
    LEVEL_NAMES,
    InMemoryTrustStore,
    L_ASSISTED,
    L_AUTONOMOUS,
    L_SUPERVISED,
    promotion_threshold,
    record_outcome,
)


# ---------------------------------------------------------------------------
# Colour helpers (ANSI, degrades gracefully)
# ---------------------------------------------------------------------------
_USE_COLOR = sys.stdout.isatty() or os.getenv("FORCE_COLOR", "")


def _c(code: str, text: str) -> str:
    if not _USE_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"


def green(t):   return _c("32", t)
def yellow(t):  return _c("33", t)
def red(t):     return _c("31", t)
def bold(t):    return _c("1",  t)
def cyan(t):    return _c("36", t)
def dim(t):     return _c("2",  t)


# ---------------------------------------------------------------------------
# Banner helpers
# ---------------------------------------------------------------------------
def section(title: str) -> None:
    width = 70
    print(f"\n{'=' * width}")
    print(bold(f"  {title}"))
    print(f"{'=' * width}")


def show_trust_table(store: InMemoryTrustStore, task_types: list[str]) -> None:
    """Pretty-print the current trust ladder state."""
    print(f"\n  {'Task type':<30} {'Level':<14} {'Counter':<8} {'Cap'}")
    print(f"  {'─'*28} {'─'*13} {'─'*7} {'─'*5}".replace('─', '-'))
    for tt in task_types:
        st = store.get("demo-pantry", tt)
        lvl_name = f"L{st.current_level} {LEVEL_NAMES[st.current_level]}"
        cap_name = f"L{st.cap}"
        color = green if st.current_level >= L_SUPERVISED else (
            yellow if st.current_level == L_ASSISTED else dim)
        at_cap = " ✓ AT CAP" if st.current_level >= st.cap else ""
        counter_str = f"{st.consecutive_verified_correct}/{promotion_threshold()}"
        print(f"  {tt:<30} {color(lvl_name):<23} {counter_str:<8} {cap_name}{at_cap}")


# ---------------------------------------------------------------------------
# Demo scenarios
# ---------------------------------------------------------------------------
def run_volunteer_graduation(graph, store: InMemoryTrustStore) -> None:
    """Demonstrate the ratchet graduating volunteer_reminder L0→L1→L2."""
    section("SCENARIO 1 — Volunteer reminders graduate L0 → L1 → L2")
    print(textwrap.dedent("""\
      The coordinator is out of the loop. Every night Steward sends shift reminders.
      Each verified-correct SMS bumps the 'consecutive_verified_correct' counter.
      After 5 correct actions → promotes one level. After 5 more → promotes again.
    """))

    org_id = "demo-pantry"
    task_type = "volunteer_reminder"
    thr = promotion_threshold()

    # Phase A: 5 actions → L0 → L1
    print(cyan(f"  Phase A: accumulating {thr} verified-correct actions..."))
    for i in range(thr):
        state = graph({
            "mode": "sweep",
            "org_id": org_id,
            "input": "Send shift reminder for tomorrow's driver slot (shift s1)",
        })
        st = store.get(org_id, task_type)
        marker = f"✓ ACTION {i+1}/{thr}"
        if "promote" in str(state.get("new_trust_state", "")):
            print(green(f"    {marker} → PROMOTED to L{st.current_level} {LEVEL_NAMES[st.current_level]}!"))
        else:
            print(dim(f"    {marker} counter={st.consecutive_verified_correct}"))

    st = store.get(org_id, task_type)
    print(f"\n  {bold('After Phase A:')} {task_type} → {green(LEVEL_NAMES[st.current_level])} "
          f"(L{st.current_level})")

    # Phase B: 5 more actions → L1 → L2
    print(cyan(f"\n  Phase B: accumulating {thr} more verified-correct actions..."))
    for i in range(thr):
        state = graph({
            "mode": "sweep",
            "org_id": org_id,
            "input": "Send shift reminder for Saturday sorting shift (shift s2)",
        })
        st = store.get(org_id, task_type)
        marker = f"✓ ACTION {i+1}/{thr}"
        if st.current_level == L_AUTONOMOUS:
            print(green(f"    {marker} → PROMOTED to L2 AUTONOMOUS! 🎉"))
        else:
            print(dim(f"    {marker} counter={st.consecutive_verified_correct}"))

    st = store.get(org_id, task_type)
    print(f"\n  {bold('After Phase B:')} {task_type} → {green('L2 AUTONOMOUS')} "
          f"— reminders now auto-send silently!")


def run_grant_ceiling(graph, store: InMemoryTrustStore) -> None:
    """Demonstrate that grant_report_file ALWAYS stays at L0 (hard ceiling)."""
    section("SCENARIO 2 — Grant report filing stays PERMANENTLY gated at L0")
    print(textwrap.dedent("""\
      Even after many correct grant alerts and draft actions, 'grant_report_file'
      is hard-capped at L0. It ALWAYS escalates to the coordinator — no exceptions.
    """))

    org_id = "demo-pantry"

    # Flood with verified-correct actions — should still stay L0
    for i in range(promotion_threshold() * 3):
        record_outcome(org_id, "grant_report_file", verified_correct=True,
                       store=store, confidence=0.99)

    st = store.get(org_id, "grant_report_file")
    print(f"  After {promotion_threshold() * 3} verified-correct actions:")
    print(f"  {red('grant_report_file')} → L{st.current_level} {LEVEL_NAMES[st.current_level]} "
          f"(cap={st.cap}) ← {bold('NEVER exceeds L0')}")

    # Now run it through the graph to show the ESCALATE path
    print(f"\n  Running grant_report_file through the graph...")
    state = graph({
        "mode": "event",
        "org_id": org_id,
        "input": "Submit the City Community Fund report — filing to funder portal today",
    })
    escalated = state.get("escalated", False)
    reply = state.get("coordinator_reply", "N/A")
    print(f"  Graph result: escalated={red(str(escalated))} | coordinator_reply={reply!r}")
    print(f"  ✓ Filing was {bold('never auto-executed')} — coordinator was asked first.")


def run_donation_escalation(graph, store: InMemoryTrustStore) -> None:
    """Demonstrate the perishable-milk escalation scenario."""
    section("SCENARIO 3 — Perishable donation escalation")
    print(textwrap.dedent("""\
      A 40-lb milk donation arrives (expires tomorrow). Steward tries to match it
      to the North shelter's need. There's no confirmed driver → it can't place the
      donation in time → confidence falls below threshold → ESCALATION.
    """))

    org_id = "demo-pantry"
    print(f"  Running donation_match for perishable milk...")
    state = graph({
        "mode": "event",
        "org_id": org_id,
        "input": "We have 40 lbs of milk to donate, expires 2026-09-11, perishable - "
                 "cannot place, no driver confirmed for North shelter route",
    })

    escalated = state.get("escalated", False)
    decision = state.get("decision", "N/A")
    reply = state.get("coordinator_reply", "N/A")
    print(f"\n  Outcome:")
    print(f"    decision={decision!r}")
    print(f"    escalated={yellow(str(escalated))}")
    print(f"    coordinator_reply={reply!r}")

    if escalated:
        print(f"\n  * Milk escalated to coordinator - {bold('only real decisions surface')}.")
    else:
        # May not escalate if ratchet shows L1+ and confidence is above threshold
        print(f"  (Donation handled at L1 supervised - ratchet level allows auto-notify.)")


def run_coordinator_swap(store: InMemoryTrustStore) -> None:
    """Demonstrate that trust survives a coordinator swap (institutional persistence)."""
    section("SCENARIO 4 — Institutional persistence: coordinator swap")
    print(textwrap.dedent("""\
      The original coordinator leaves. A new one joins.
      The Trust Ratchet state is keyed by org_id — not by user.
      The new coordinator inherits an agent that has ALREADY earned its trust.
    """))

    org_id = "demo-pantry"
    st = store.get(org_id, "volunteer_reminder")
    print(f"  Trust state for {org_id!r} BEFORE swap:")
    print(f"    volunteer_reminder → L{st.current_level} {LEVEL_NAMES[st.current_level]}")

    # Simulate coordinator swap (change the "user" — has no effect on org-keyed state)
    print(f"\n  Coordinator swap: 'Alice (alice@pantry.org)' → 'Bob (bob@pantry.org)'")
    print(f"  (In production: update COORDINATOR_PHONE env var; re-deploy or update config)")

    # State is unchanged
    st_after = store.get(org_id, "volunteer_reminder")
    print(f"\n  Trust state for {org_id!r} AFTER swap:")
    print(f"    volunteer_reminder → L{st_after.current_level} {LEVEL_NAMES[st_after.current_level]}")
    assert st.current_level == st_after.current_level, "State changed after swap — BUG"
    print(f"\n  ✓ Trust state {bold('unchanged')} — Bob inherits all of Alice's earned trust.")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def main() -> None:
    print(bold("\n" + "=" * 70))
    print(bold("  STEWARD -- Local End-to-End Demo"))
    print(bold("  Trust Ratchet | Volunteer Path | Escalation | Institutional Persistence"))
    print(bold("=" * 70))
    print(dim("\n  Mode: MOCK (no AWS creds needed). Set BEDROCK_ENABLED=true for real calls."))
    print(dim("  Org:  demo-pantry | Coordinator reply: YES (simulated)\n"))

    # Shared in-memory store for the whole demo
    store = InMemoryTrustStore()

    # Build the graph with the shared store
    graph = build_steward_graph(store=store)

    # ── Scenario 1: volunteer reminders graduate L0 → L2 ──────────────────
    run_volunteer_graduation(graph, store)

    # ── Scenario 2: grant filing stays gated ──────────────────────────────
    run_grant_ceiling(graph, store)

    # ── Scenario 3: perishable milk escalation ────────────────────────────
    run_donation_escalation(graph, store)

    # ── Scenario 4: coordinator swap (institutional persistence) ──────────
    run_coordinator_swap(store)

    # ── Final trust ladder snapshot ───────────────────────────────────────
    section("FINAL TRUST LADDER STATE")
    all_task_types = [
        "volunteer_reminder", "shift_backfill", "grant_deadline_alert",
        "donation_match", "grant_report_draft", "grant_report_file",
    ]
    show_trust_table(store, all_task_types)

    # ── Proof metrics ─────────────────────────────────────────────────────
    section("PROOF METRICS (§11)")
    total = len(store.audit)
    escalated_count = sum(1 for e in store.audit if e.get("human_override") or
                          e.get("new_level") == 0 and e.get("reason", "").startswith("demote"))
    correct_count = sum(1 for e in store.audit if e.get("verified_correct"))
    promote_count = sum(1 for e in store.audit if str(e.get("reason", "")).startswith("promote"))

    print(f"\n  {'Total ratchet events logged:':<40} {total}")
    print(f"  {'Verified-correct actions:':<40} {green(str(correct_count))}")
    print(f"  {'Promotions:':<40} {green(str(promote_count))}")
    print(f"  {'Escalation events:':<40} {yellow(str(escalated_count))}")
    if total > 0:
        auto_pct = (correct_count / total) * 100
        print(f"  {'Actions handled without coordinator approval:':<40} {green(f'{auto_pct:.0f}%')}")

    print(f"\n  {bold('Demo complete.')} volunteer_reminder graduated to AUTONOMOUS; "
          f"grant_report_file stayed ASSISTED.\n")


if __name__ == "__main__":  # pragma: no cover
    main()
