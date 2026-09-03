# Steward — Phase-Wise Implementation Plan

> **Companion to `IMPLEMENTATION_PLAN.md`** (the single source of truth). This file is the *execution sequence*: what to build, in what order, and how to know each phase is done. Every "spec" reference (e.g. §3.3) points to a section in `IMPLEMENTATION_PLAN.md` — read the spec there, execute here.
> **Rule for agents:** Do phases in order. **Do not start a phase until its predecessor's Exit Gate passes.** If you must deviate, record it in `IMPLEMENTATION_PLAN.md` §16 (Open Decisions) with a reason — don't improvise silently.

---

## Phase map (at a glance)

| Phase | Name | Outcome | Approx. week |
|---|---|---|---|
| **P0** | Foundation & accounts | Everything provisioned; empty repo runs | Week 0 |
| **P1** | Trust Ratchet core + data layer | Ratchet logic proven by tests; data stores live | Week 1 |
| **P2** | Agents & Graph (local) | End-to-end volunteer path runs locally | Week 2 |
| **P3** | Escalation + event triggers | Interrupt→SMS→resume; sweep + inbound webhook | Week 3 |
| **P4** | AgentCore integration | Deployed on Runtime; Gateway+Memory+Identity+Observability | Week 4 |
| **P5** | Institutional persistence + demo hardening | Ratchet visibly graduates; proof number measured | Week 5 |
| **P6** | Deliverables & submission | Video, README, diagram, posts, submitted | Week 6 |

**Critical path:** P1 → P2 → P3 → P4 → P5 → P6. P0 must fully complete first (esp. **credits by Sept 11**). Within a phase, tasks marked `∥` can run in parallel.

**Global Definition of Done (every phase):** code committed to the public repo; unit tests green; any decision recorded in §16; a one-paragraph note in the phase's "Exit note" checkbox.

---

## PHASE 0 — Foundation & Accounts

**Objective:** Every external dependency provisioned and access-verified, so no phase later stalls on setup. **This is the highest-urgency phase** because of the credits deadline.

**Entry gate:** none (start here).

### Tasks
- [ ] **P0.1** Create/confirm **AWS account** + **AWS Builder ID** (required for submission — §2.4). `∥`
- [ ] **P0.2** ⚠️ **Request the $50 AWS credits** via `https://forms.gle/Ssr8zLw4afKg114M7` — **before Sept 11, 12:00 PM PT** (§2.8). `∥`
- [ ] **P0.3** In the **Bedrock console**, enable **model access** for the two tiers (Sonnet `global.anthropic.claude-sonnet-4-6` + a cheap model e.g. Nova Lite). Record the exact working inference-profile IDs and region in §16 D3/D8. `∥`
- [ ] **P0.4** ~~Twilio~~ **Amazon SNS** is used for SMS — no separate account needed; SNS is accessed via existing AWS credentials (boto3). Verify `COORDINATOR_PHONE` is set and AWS creds allow `sns:Publish`. `∥`
- [ ] **P0.5** Create a **Google Cloud** project, enable the **Sheets API**, create an OAuth client (for AgentCore Identity's Google provider). Create the demo **Google Sheet** with the tabs in §6.1. `∥`
- [ ] **P0.6** Create a **fresh public GitHub repo** (commits must fall inside the submission window — §2.7). Add **LICENSE (MIT or Apache)** on the first commit (hard gate — §2.6).
- [ ] **P0.7** Scaffold the repo tree from §9 with stub files + `requirements.txt` pinned to §7.1 versions. `python -c "import strands, bedrock_agentcore"` succeeds in a fresh venv (Python 3.10+).
- [ ] **P0.8** **Verify every teammate's residency** against the excluded-jurisdictions list (§2.7). Record cleared in §16 D7.
- [ ] **P0.9** Set AWS credentials/region locally (`AWS_REGION`, keys or profile) per §7.2.

### Exit Gate (all must pass)
- Credits requested; Builder ID exists; Bedrock model access confirmed with real IDs recorded.
- ~~Twilio number~~  **Amazon SNS** + `COORDINATOR_PHONE` verified; Google Sheet + OAuth client exist and are reachable.
- Public repo with LICENSE + scaffolded tree; a trivial `Agent("hi")()` call returns a response locally.
- Residency cleared.
- [ ] **Exit note:** _____

**Risks:** credits deadline (do P0.2 first); model access not granted in-region (P0.3 early).

---

## PHASE 1 — Trust Ratchet core + data layer

**Objective:** The novel mechanic works as *pure, tested logic* before any agent touches it, and the data stores exist. This is the riskiest-to-get-wrong part, so it's isolated and test-driven.

**Entry gate:** P0 Exit Gate passed.

### Tasks
- [ ] **P1.1** Implement `config/ratchet.yaml` exactly per §3.7 (levels, thresholds, task caps, cost ratios).
- [ ] **P1.2** Implement `app/ratchet.py` with pure functions (no I/O in the logic core):
  - `effective_level(current_earned, task_type) -> int` (applies `min(earned, cap)` — §3.2).
  - `gate_passes(org_id, task_type, confidence) -> bool` (autonomy gate **and** confidence gate — §3.5).
  - `record_outcome(org_id, task_type, verified_correct, human_override) -> new_state` (promotion §3.3 / demotion §3.4).
- [ ] **P1.3** Write `tests/test_ratchet.py` covering: promotion after N verified-correct; reset on demotion; ceiling never exceeded (esp. L0-capped `grant_report_file`/`money_movement`/`pii_disclosure` **always** ask); confidence-gate math; one-level-at-a-time movement. **Target: 100% branch coverage of `ratchet.py`.**
- [ ] **P1.4** Create **DynamoDB** tables `steward_trust` and `steward_audit` (`infra/ddb.py`) with the schemas in §6.2; use **atomic conditional updates** for counters. `∥`
- [ ] **P1.5** Wire `ratchet.py` state read/write to `steward_trust`; append every decision to `steward_audit`. Mirror current levels to the Sheet `TrustState` tab (§3.6).
- [ ] **P1.6** Implement local `@tool` wrappers `app/tools/sheets.py` + `app/tools/sms.py` (boto3 SNS — replaces Twilio) — the fast path per §16 D1. `∥`
- [ ] **P1.7** `scripts/seed_sheet.py` populates the demo Sheet with realistic volunteers/shifts/donations/needs/grants.

### Exit Gate
- `pytest tests/test_ratchet.py` green; ceilings provably enforced.
- Reading/writing trust state round-trips through DynamoDB; `TrustState` tab reflects it.
- Sheets/SNS `@tool`s can read a row and send a test SMS.
- [x] **Exit note (2026-09-03 → updated 2026-09-04):** Ratchet **logic complete + proven** — `app/ratchet.py` at **100% coverage, 24 tests pass** offline (ceilings, promotion/demotion, confidence gate, org-keyed persistence). `infra/ddb.py` (DynamoDBTrustStore + create_tables), `app/tools/sms.py` (Amazon SNS — replaces Twilio), `app/tools/sheets.py`, and `scripts/seed_sheet.py` are **written**. SMS now uses SNS (boto3); no Twilio account needed. **45/45 tests green locally.** **Remaining before P2 fully closed:** run `create_tables()` + `seed_sheet.py` once AWS creds are set; send a live SNS test SMS.

**Risks:** race between sweep + inbound events on counters → mitigated by atomic conditional writes (P1.4).

---

## PHASE 2 — Agents & Graph orchestration (local)

**Objective:** The multi-agent brain runs **end-to-end locally** for at least the volunteer-reminder path, with the ratchet gate deciding act-vs-escalate.

**Entry gate:** P1 Exit Gate passed.

### Tasks
- [ ] **P2.1** Implement the **Router/orchestrator** agent (`app/agents/router.py`) — classifies an input into a `task_type` + emits a `confidence`.
- [ ] **P2.2** Implement the three **specialists as Agents-as-Tools** (§8.2), each with its focused prompt + the Sheets/SNS tools: `recruiter.py` (confirm/backfill), `matcher.py` (donation→need), `grant.py` (deadline/draft/file). `∥`
- [ ] **P2.3** Implement the **ReviewerAgent** (`app/agents/reviewer.py`, §8.4) — separate turn returning `{correct, confidence, reason}`. Use the **cheap** model.
- [ ] **P2.4** Build the **Strands Graph** (`app/graph.py`, §8.3): `router → (ratchet_condition) → execute → review`, plus `router → human_review` when the gate fails. Feed reviewer verdict into `record_outcome`.
- [ ] **P2.5** Assign models per agent (§7.2): cheap for router/reviewer/simple steps, Sonnet for grant drafting / ambiguous matching.
- [ ] **P2.6** `scripts/run_local_demo.py` — scripted end-to-end run of the **volunteer-reminder** path (roster → 3-touch SMS → one drops → backfill), driving state through the ratchet.
- [ ] **P2.7** `tests/test_graph.py` — assert the conditional edge routes to `execute` when gates pass and to `human_review` when they don't.

### Exit Gate
- `run_local_demo.py` completes the volunteer path end-to-end locally; audit journal shows each action + reviewer verdict + confidence.
- Ratchet counter advances on verified-correct actions; a forced error demotes.
- Graph routing test green.
- [ ] **Exit note:** _____

**Risks:** scope creep — build the volunteer path first; matcher/grant can be thin until P3/P5.

---

## PHASE 3 — Escalation, interrupts & event triggers

**Objective:** The "surface only for real decisions" behavior works — a Strands interrupt reaches the coordinator by SMS and the session **resumes** on reply — and both triggers (nightly sweep + inbound SMS) invoke the agent.

**Entry gate:** P2 Exit Gate passed.

### Tasks
- [ ] **P3.1** Implement the escalation surface (`app/nodes/human_review.py`, §8.5): `@tool(context=True)` raising `tool_context.interrupt(...)`; entrypoint detects `stop_reason == "interrupt"`, texts `reason.summary` to the coordinator via **Amazon SNS**.
- [ ] **P3.2** Implement **resume**: inbound reply → feed `interruptResponse` block back → graph continues from the interruption point. Requires a stable per-org `runtimeSessionId` (§8.5).
- [ ] **P3.3** Build the **inbound webhook** (`infra/webhook_lambda.py`, §8.8): inbound SMS → API Gateway → Lambda → `InvokeAgentRuntime` (`mode:"event"`). Handles both donation SMS and coordinator replies. *(Inbound SMS can be received via a virtual number service or the demo can use an email/web fallback — no Twilio number required.)* `∥`
- [ ] **P3.4** Implement the **nightly sweep** logic + `infra/scheduler.py`: EventBridge Scheduler universal target → `InvokeAgentRuntime` (`mode:"sweep"`). Use the **async task pattern** (`app.add_async_task`/`complete_async_task`) so the entrypoint returns fast and `/ping` = `HealthyBusy` (§8.8). `∥`
- [ ] **P3.5** Implement the **donation-match escalation** end-to-end: donation arrives → matcher (L1 supervised) → can't place a perishable in time / low confidence → escalate → coordinator decides → resume.
- [ ] **P3.6** Test: an L0-capped task (`grant_report_file`) **always** produces an interrupt (never auto-executes), regardless of earned trust.

### Exit Gate
- Interrupt → coordinator SMS → reply → resume works locally (mock the runtime session) and the decision is applied.
- Both triggers invoke the agent; sweep doesn't time out (async pattern verified).
- The perishable-milk escalation scenario runs end-to-end.
- [ ] **Exit note:** _____

**Risks:** assuming a native Runtime interrupt/EventBridge target — there is none; use the Strands interrupt + Scheduler patterns (§13). Session continuity depends on a stable `runtimeSessionId`.

---

## PHASE 4 — AgentCore integration

**Objective:** Move from local to a real **AgentCore** deployment, converting the "depth" story into reality: Runtime hosting, Gateway MCP tools, Memory, Identity, Observability.

**Entry gate:** P3 Exit Gate passed. (Do this late to conserve credits — §12.)

### Tasks
- [ ] **P4.1** Wrap the app in `BedrockAgentCoreApp` (`app/main.py`, §8.1) and deploy to **Runtime** via the **npm `@aws/agentcore`** CLI (§7.3). Confirm `agentcore invoke` works.
- [ ] **P4.2** Stand up an **AgentCore Gateway**; expose **Google Sheets** and **Amazon SNS** as **OpenAPI targets** → MCP tools (§8.7). Migrate `app/tools/*` from local `@tool` to Gateway calls (§16 D1). `∥`
- [ ] **P4.3** Configure **AgentCore Identity**: Google OAuth (3-legged) for Sheets, IAM role for SNS (already in-account, no extra key provider needed); verify token-vault-backed calls succeed (§8.7). `∥`
- [ ] **P4.4** Create the **AgentCore Memory** resource (`app/memory.py`, §8.6) with semantic + user-preference + summary strategies, **namespaced by `org_id`**. Write session summaries; retrieve org facts in the router. `∥`
- [ ] **P4.5** Enable **Observability**: turn on CloudWatch Transaction Search, instrument with ADOT, confirm traces/spans/token metrics land in CloudWatch (§8.9). Set **log retention + X-Ray sampling** low (cost — §12). `∥`
- [ ] **P4.6** Re-run the full P2/P3 scenarios **against the deployed Runtime** (not local).

### Exit Gate
- Agent runs on AgentCore Runtime; Sheets/SNS calls go through Gateway + Identity.
- Memory reads/writes work at the org namespace.
- Traces visible in CloudWatch.
- End-to-end volunteer + donation + grant scenarios pass on the deployed agent.
- [ ] **Exit note:** _____

**Risks:** CLI verb confusion (use npm CLI); region feature gaps (check the region matrix, §15.2); idle sessions billing (don't hold sessions open, §12).

---

## PHASE 5 — Institutional persistence + demo hardening

**Objective:** Make the *unique* twist and the *proof number* real and visible — the ratchet graduating over a simulated timeline, trust surviving a coordinator swap, and a measured metric for the video.

**Entry gate:** P4 Exit Gate passed.

### Tasks
- [ ] **P5.1** Implement/verify **institutional persistence** (§3.6): swap the coordinator (change the contact identity) and confirm the trust ladder + org knowledge persist (keyed by `org_id`, not user).
- [ ] **P5.2** Build a **simulated accelerated timeline** harness that runs enough verified-correct actions to visibly graduate `volunteer_reminder` L0→L1→L2 while `grant_report_file` stays L0. (Reuse `run_local_demo.py`.)
- [ ] **P5.3** **Instrument the proof metrics** (§11): % reduction in coordinator approvals over the timeline; escalation count (should be few + all real); reviewer-verified-correct count. Log to a small report.
- [ ] **P5.4** Polish the **`TrustState` + `AuditLog` Sheet mirrors** so they read cleanly on camera.
- [ ] **P5.5** **(Stretch, §16 D6)** Build a read-only web dashboard of the trust ladder for the optional **live demo link** (scoring boost).
- [ ] **P5.6** **(Stretch)** Selective-disclosure handling for `pii_disclosure` (CalBench-inspired, §15 ref 6).
- [ ] **P5.7** End-to-end dry run of the **full demo scenario** (§11) start to finish.

### Exit Gate
- A single run demonstrates: reminders graduate to auto, grant-filing stays gated, a perishable escalates, and trust survives a coordinator swap.
- A real proof number is measured and defensible (framed honestly per §13/§15.5).
- [ ] **Exit note:** _____

**Risks:** over-building stretch items before the core demo is solid — do P5.1–P5.4 first.

---

## PHASE 6 — Deliverables & submission

**Objective:** Ship every required artifact and submit before the deadline.

**Entry gate:** P5 Exit Gate passed.

### Tasks
- [ ] **P6.1** Write **`README.md`**: what/why, setup instructions, and the **architecture diagram** (embed §5.1 mermaid or an exported PNG) — required (§2.6). `∥`
- [ ] **P6.2** Finalize **`ARCHITECTURE.md`** (diagram + narrative + AWS-service mapping).
- [ ] **P6.3** Confirm the repo **installs and runs** from a clean clone following the README; LICENSE present.
- [ ] **P6.4** Record the **≤5-min demo video** to the §11 script: human problem in first 10s, live product (not slides), one proof number, cover problem/who/why. Host publicly. `∥`
- [ ] **P6.5** Write **3 builder.aws.com posts** ("Agents for Humans" in each title, published before the deadline) for **+0.6** (§2.5). `∥`
- [ ] **P6.6** **(Optional)** Deploy + link the live demo (§P5.5) for the scoring boost.
- [ ] **P6.7** Complete the **Devpost submission**: description, repo URL, video URL, **AWS Builder ID**, track = **Good Neighbor**, live link if any.
- [ ] **P6.8** Run the **§14 deliverables checklist** top to bottom; fix any gap.
- [ ] **P6.9** **Submit before Sept 14, 5:00 PM PT.** Don't wait for the last hour.

### Exit Gate
- Submission accepted on Devpost with all required fields; video public; repo public with LICENSE + README + diagram; posts published.
- [ ] **Exit note:** _____

**Risks:** last-minute deadline (submit with buffer); video is the primary scored artifact — leave real time for it (P6.4).

---

## Dependency & parallelization notes

- **Strictly sequential:** P0 → P1 → P2 → P3 → P4 → P5 → P6 (each Exit Gate gates the next).
- **Can start early / in parallel with earlier phases:**
  - README/architecture-diagram drafting (P6.1/P6.2) can begin as soon as P2 stabilizes.
  - builder.aws.com posts (P6.5) can be drafted from P3 onward (write as you build — best material).
  - The `∥`-marked tasks inside each phase are independent of each other.
- **Cost timing:** stay **local** through P1–P3; only incur meaningful AgentCore spend in P4–P5 (§12).

## Fallback plan (if behind schedule)
Cut in this order to protect a shippable demo:
1. Drop stretch items (P5.5 dashboard, P5.6 selective disclosure).
2. Reduce to **two** task-types end-to-end: `volunteer_reminder` (graduates) + `grant_report_file` (stays L0) — enough to show the ratchet *and* the ceiling.
3. If AgentCore integration (P4) is at risk, ship on **Strands + local tools** and record the demo there — AgentCore is *recommended, not required* (§2.4). Prioritize a working, on-theme demo over breadth.

---

*Execute top-down. Keep `IMPLEMENTATION_PLAN.md` authoritative for specs; keep this file authoritative for sequence and done-ness.*
