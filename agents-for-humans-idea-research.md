# Agents for Humans Hackathon — Idea Research & Recommendation

> Research brief for the AWS **[Agents for Humans](https://agentsforhumans.devpost.com/)** hackathon.
> Deadline: **Sept 14, 2026 · 5:00pm PDT** · Prize pool **$40,000** · ~6,951 registered participants.

---

## Hackathon profile (the constraints that shape everything)

- **Theme thesis:** AI agents that autonomously handle repetitive real-life tasks, run in the **background**, and **surface only when there's a real human decision to make**.
- **Required tech:** **Strands Agents SDK** (mandatory). **Amazon Bedrock AgentCore** deployment is *recommended* and boosts the Technical Implementation score.
- **Three tracks:** Everyday Agents · Professional Agents · Good Neighbor (community) Agents. Each track: Gold $5k / Silver $3k / Bronze $2k. Grand Prize $10k (+ AWS expert meeting).
- **Judging criteria (5):** Technological Implementation · Design (complete product, not a PoC) · Potential Impact · Creativity & Originality · Presentation.
- **Deliverables:** public GitHub repo (MIT/Apache) · README + **architecture diagram** · **≤5-min demo video** (problem → audience → why it matters) · AWS Builder ID · optional live demo link (boosts score) · bonus: build-story post on builder.aws.com with "Agents for Humans" in the title.
- **Perks:** $50 AWS credits per participant. Solo or team. Beginner-friendly.
- **Note:** several regions are excluded (see rules) — confirm eligibility.

---

## What actually wins this hackathon

From the rules + the 2025 predecessor's winners + Devpost judge commentary:

1. **The theme's literal thesis is the edge.** Most of ~7,000 entries will be **foreground chatbots you talk to.** A genuinely *proactive, event-triggered* agent that acts and only escalates edge cases is on-theme and rare.
2. **Winners are narrow, named, and quantified.** Not "an assistant" — "100% accuracy on Form 1040," "waste-reporting for Timor-Leste." Every past winner has **one memorable proof number** and **one real, identifiable user/community**. The 2025 predecessor's **1st place (EcoLafaek) was a civic/community story.**
3. **Depth = a *named* Strands multi-agent pattern + *visible* AgentCore.** Judges penalize "ambiguity." Show the architecture diagram and the reasoning/tool-call trace, and deploy on AgentCore. Using **long-term Memory + Gateway + interrupts** together is a hard-to-fake depth signal almost no one reaches.
4. **The demo video is the primary scored artifact.** Great build + weak video loses to good build + great video. Open with the human problem in the first 10 seconds; show the product working live (not slides); land one quantified number.
5. **Reliability is the real problem — and your best pitch.** Agents that work in a demo aren't consistent (τ-bench **pass^k collapse: >60% single-run → <25% at 8 runs**), they *bluff instead of escalating*, and **96% of booking failures were silent**. Designing *for* this looks grounded, not naive.

### Crowded lanes to avoid (hundreds of teams will build these)
Generic AI email assistant · meeting summarizer · personal-finance chatbot · resume/job-application coach · plain calendar/scheduling helper · trip planner · "second brain" RAG bot · meal planner. The theme's own examples ("family calendar," "bills") will be the **most copied** — a plain version is the single most crowded lane.

---

## The 3 ideas

Each maps to a different track, hits genuine product whitespace, and has a research spine baked in.

### 💡 Idea 1 — "Steward" · back-office agent for all-volunteer orgs (Good Neighbor) — ⭐ RECOMMENDED

**Problem & who.** Tiny, budget-less, IT-less orgs — a 3-person food pantry, a PTA, a mutual-aid group — run on a group chat and a Google Sheet. >75% of small nonprofits have no AI strategy; ~30% under $500k cite cost as the #1 blocker. Every "nonprofit AI agent" (Blackbaud, Instrumentl) requires an enterprise CRM they don't have.

**What it does (background, event-driven).** Lives *in what they already use* — SMS/WhatsApp + a Google Sheet, **zero migration, zero config**. It autonomously:
- Matches incoming **in-kind/perishable donations → local need** before spoilage.
- Recruits & confirms volunteers via the proven **3-touch SMS** pattern (no-shows ~20–35% → 5–15%), and **auto-backfills** dropped shifts.
- Tracks **grant deadlines and drafts + files post-award reports** — where under-resourced orgs actually lose funders, and which *no product does*.
- Preserves **institutional memory across volunteer turnover**.
- **Surfaces to the coordinator only for a real decision** (e.g., a perishable donation it can't place in time).

**Why it stands out.**
- **Uncontested whitespace #1.** The grassroots end is a near-total product desert; the giants are *retreating* from consumer autonomy (Operator, Mariner shut down 2025).
- **Answers a live research critique.** CHI 2025's *"It Actually Doesn't Feel Very Mutual"* shows current tools centralize control in the login-holder and put members on-record without consent. Steward uses a **selective-disclosure** protocol (CalBench 2026) so it coordinates *without* leaking members' info or concentrating power.
- **Civic story punches above its weight** (see EcoLafaek → 1st).

**Tech depth.** Strands **Graph** (auditable, condition-gated escalation to a `human_review` node) + **Agents-as-Tools** (recruiter / matcher / grant-reporter specialists). AgentCore **Gateway** turns Google Sheets + Twilio into MCP tools; **long-term Episodic + UserPreference Memory** *is* the institutional-memory feature; **EventBridge → async Runtime** does the nightly background sweep; **resumable interrupts** are the escalation surface.

**Killer demo + proof number.** Donation SMS arrives → agent matches it to a need and texts 4 volunteers → one drops → agent silently backfills → a case of milk can't be placed in time → *only now* the coordinator's phone buzzes with a crisp decision. Proof: *"cut volunteer no-shows from 31% to 9% and rescued X lbs of food, on zero new software."*

**Risk.** "Help a food bank" is an obvious feel-good idea, so some teams enter this lane — but the *specific combined mechanics* (perishable matching + no-show backfill + grant-report filing + org memory + selective disclosure, on a bare Sheet+SMS substrate) are non-obvious and unbuilt. Differentiate hard on those.

---

### 💡 Idea 2 — "Kin" · caregiver-bureaucracy advocate (Everyday)

**Problem & who.** ~63M unpaid US family caregivers (~$600B/yr of labor) drowning in eligibility forms, coverage-denial appeals, and bill coordination across Medicare/Medicaid/SSA/insurers *on behalf of someone else*. Congress is drafting the "Alleviating Barriers for Caregivers Act." Near-zero competition; regulatory tailwind.

**What it does.** Acts on behalf of the care recipient, reporting to the caregiver: reads a denial letter → checks coverage → drafts an appeal → fills the eligibility renewal → coordinates bill/appointment — and **surfaces to the exhausted caregiver only when a genuine decision or irreversible action (send/pay/sign) appears.**

**Why it stands out.** The "**acting on behalf of a third party**" framing is genuinely novel and deeply on-theme. Huge invisible population, enormous emotional pitch. <1% of denied insurance claims are ever appealed.

**Tech depth.** AgentCore **Browser tool with live-view human takeover** (portals/forms) as a literal HITL escalation surface; **risk-tiered approval gates** + an **append-only audit journal** (reasoning + confidence + sources, per *Safe & Responsible AI Agents* 2026); **UserPreference Memory** for the care recipient's coverage details.

**Risk (why it's #2).** Convincing live demo is harder — real government/insurer portals, sensitive PII. Demoable on mock portals with the browser tool, but riskier to land cleanly in 6 weeks. Highest ceiling, higher execution risk.

---

### 💡 Idea 3 — "Ratchet" · earned-autonomy back-office for solo operators (Professional)

**Problem & who.** Freelancers/one-person businesses spend ~36% of the week on non-billable admin; 89% hit late payments. Every existing tool owns *one* lane, forcing the operator to stitch five tools — and none earns trust safely.

**The distinctive mechanic (the star, not the tasks).** The agent **starts in approve-everything mode and *earns* autonomy per task-type** as it proves reliability — bookkeeping categorization graduates to auto after N correct approvals; sending invoices stays gated longer; anything touching money never fully auto. It **self-bootstraps** from Gmail + Calendar + Stripe (infers the workflow, no config) with a visible **trust ladder + audit trail.** This makes "surfaces only for real decisions" a *dynamic, provable* property.

**Why it stands out.** Turns the reliability-research spine into the visible product: the **cost-ratio escalation threshold** (*Act or Escalate?* 2026), the **trust ladder** (Assisted → Supervised → Autonomous), and Gartner's warning that >40% of agentic projects get canceled over governance. Nobody packages *earned* trust this way for tiny operators.

**Risk.** Closest to a crowded lane ("AI back-office / invoice chaser"). Only stands out if the **earned-autonomy mechanic is unmistakably the centerpiece.**

---

### 🔗 Idea 4 (integrated) — "Steward" with the **Trust Ratchet** (Good Neighbor) — ⭐⭐ STRONGEST

Fuses Idea 1 (Steward) and Idea 3 (Ratchet). Each idea's weakness is the other's strength: Steward's only gap is *uniqueness* (an obvious feel-good lane); Ratchet's only gap is a *crowded lane* (invoice-chasing). Combine them and both gaps close.

**The one-line idea.** The all-volunteer-org back-office agent (Steward's domain, Sheet+SMS substrate, civic story) whose signature mechanic is **earned autonomy per task-type** (Ratchet's trust ladder) — so a non-technical, high-turnover coordinator can actually *trust* an autonomous agent running on the tools they already have.

**Why the fusion beats either alone.**
- **Fixes Steward's uniqueness gap.** The trust ratchet is a single legible mechanic nobody has shipped — the originality claim stops being "a novel bundle" (weak) and becomes "a mechanism that doesn't exist yet."
- **Fixes Ratchet's crowded-lane gap.** The earned-autonomy mechanic moves off invoice-chasing into a total product desert — no competitor to escape.
- **The mechanic answers the root cause, so it isn't bolted on.** Small nonprofits have "no AI strategy" *because* they have no IT to audit software and can't survive silent failures. Visible, provable, earned autonomy is the reason they'd adopt at all.

**The genuinely-unbuilt twist — *institutional* earned autonomy.** Ratchet's ladder was personal; Steward's killer feature was memory across volunteer turnover. Fuse them: the earned-trust state lives in **org-level long-term Memory**, so autonomy the agent earned **survives coordinator turnover** — a new coordinator inherits a system that already proved itself. No product does org-level earned autonomy that persists across staff churn.

**The ratchet, mapped to the tasks.**

| Task-type | Graduates to auto? | Why |
|---|---|---|
| 3-touch volunteer reminder SMS | Fast (low cost of error) | A wrong reminder is cheap |
| Donation → need matching | Supervised longer | Perishable, real-world stakes |
| Grant-report filing | Stays gated | Funder relationship, irreversible |
| Anything money / PII disclosure | **Never fully auto** | Hard ceiling |

Graduation is **earned on *verified* correctness, not just approvals**: a separate reviewer-agent turn scores each action before it counts toward graduation (research spine #3), and a task-type **demotes** back down on error.

**Tech depth (both stacks fuse cleanly).** Strands **Graph** where the ratchet gate *is* a graph condition (per-task-type autonomy level read from Memory) → **Agents-as-Tools** (recruiter / matcher / grant-reporter) → **externalized verifier turn** feeding graduation → AgentCore **Gateway** (Sheets + Twilio as MCP tools) · **long-term Memory** (institutional trust state + org memory) · **EventBridge → async Runtime** (nightly sweep) · **resumable interrupts** (escalation surface) · **append-only audit journal** + **selective disclosure** (CalBench).

**Killer demo + proof numbers.** Show the ratchet *moving*: Day 1 everything asks → by "Day 30" reminders auto-send silently, matching is supervised, grant-filing still gated → a case of milk can't be placed in time → *only now* the coordinator's phone buzzes. Proof: *"no-shows 31%→9%, X lbs rescued, and coordinator approvals dropped ~80% over 3 weeks as the agent earned autonomy — with zero money or irreversible action ever auto-executed."*

**Risk.** Scope is larger than either idea alone — resist building all of it. Ship the ratchet + one or two task-types end-to-end (reminders auto, grant-filing gated) rather than all five shallow. The ratchet moving on screen is the whole pitch; everything else is supporting cast.

---

## Recommendation: Idea 4 (Steward + Trust Ratchet) — feasible *and* unique

- **Most defensible whitespace** — sits where *both* funding and products have refused to go (ranked #1 across the landscape research).
- **Most feasible *convincing* build** — real Twilio number + real Google Sheet + real Bedrock; no brittle government portals (Idea 2's risk) and no crowded category to escape (Idea 3's risk). A recorded end-to-end run is fully in reach.
- **Best fit for how it's judged** — civic story (impact) + narrow named org + one quantified number + deep *visible* Strands+AgentCore + the theme's exact thesis shown live. Scores across *all five* axes rather than over-indexing one.

---

## Stress-test: Steward vs. what already exists

| Existing solution | What it does | Why Steward isn't it |
|---|---|---|
| **FRANSiS** (text-first volunteer coord.) | SMS reminders, no-show reduction | Closest competitor, but a **paid platform you migrate into**, volunteers only — no donation→need matching, grant-report filing, or org memory. Steward runs *on the org's existing Sheet*. |
| **Golden / Catchafire / VolunteerMatch** | Volunteer directories, corporate CSR | Staff-mediated directories, **not autonomous**, built for corporates/mid-large orgs. |
| **Blackbaud "Development Agent"** | Genuinely autonomous donor fundraising | **Enterprise-only, requires Blackbaud CRM.** Fundraising, not volunteer/food ops. Structurally excludes the target user. |
| **Grantboost / Grantable / Instrumentl** | Grant *drafting* | Draft-only; **none files post-award reports** — the step Steward owns and where orgs lose funders. |
| **GIK Marketplace / DonationMatch** | Corporate surplus → nonprofit | Corporate-scale, not **hyperlocal perishable + volunteer logistics** with spoilage timing. |
| **Zelos / Brightest / Mutual Aid Hub** | Mutual-aid coordination | Basically **no AI**; CHI 2025 shows they **centralize control in the login-holder and put members on-record** — the failure Steward's selective-disclosure design fixes. |
| **Sage Future experiment** | 4 agents raising money | Raised just **$257, stuck on CAPTCHAs** — evidence *full* autonomy fails, validating Steward's escalate-for-decisions design. |

**Verdict:** No existing product closes Steward's loop (donation→need match **+** volunteer confirm/backfill **+** grant-report filing **+** institutional memory) on a **zero-migration Sheet+SMS substrate** for a budget-less org, nor addresses the mutual-aid privacy/power critique. Whitespace is real. Respect the reliability ceiling: **escalate structurally, never fail silently.**

---

## The research spine (say this to judges)

1. **Autonomy is *earned per action*, because agents are capable-but-unreliable** — τ-bench pass^k collapse (>60% → <25% over 8 runs).
2. **When to act vs. surface = a value-of-information decision** (Horvitz mixed-initiative CHI 1999 → VOI 2026), with the **escalation threshold set from the action's cost ratio** (*Act or Escalate?* 2026: escalate when confidence < 1 − cost_of_asking/cost_of_error). Kicker: escalation thresholds are *decoupled from stated confidence* and model-specific — measure your model's real behavior.
3. **Externalize verification** — self-correction is a structural *illusion* (LLMs catch external errors but miss identical errors in their own reasoning); re-route a draft as a separate reviewer turn (near-free reliability lever).
4. **Personalization must change behavior, not just recall** — agents act on only ~⅔ of preferences they remember (*Know It, Act on It* 2026); add an explicit memory-*utilization* check.
5. **Consequential actions → risk-tiered approval gates + append-only audit journal**; multi-human coordination → **selective disclosure** (CalBench 2026).

**Four "make the judge nod" facts:** pass^k reliability collapse · self-correction is an addressability artifact · escalation thresholds are model-specific and decoupled from confidence · agents fail to act on ~⅓ of remembered preferences.

---

## $50-budget notes (AgentCore)

- **Model tokens dwarf infra cost** — your $50 mostly buys Bedrock tokens, not AgentCore. Use cheap models (Nova, Haiku) for routing/sub-agents; reserve Sonnet/Opus for hard steps. Deterministic Graph/Workflow avoid paying tokens for routing.
- **Idle memory billing** — Runtime/Browser/Code-Interpreter sessions bill GB-hours until terminated (15-min default idle timeout). End sessions explicitly.
- **Watch:** Web Search ($7/1k queries — cache), Gateway semantic search ($0.025/1k), uncapped Observability (set sampling/retention).
- **Develop locally against Strands** for most of the 6 weeks (only pay tokens); move to AgentCore Runtime late for the deploy/demo. New AWS accounts may get up to $200 Free Tier credits.

---

## Key sources

**Hackathon & winning patterns:** [rules](https://agentsforhumans.devpost.com/) · [predecessor winners](https://aws-agent-hackathon.devpost.com/updates/38140-congratulations-to-the-winners-of-the-aws-ai-agent-global-hackathon) · [MS AI Agents winners](https://microsoft.github.io/AI_Agents_Hackathon/winners/) · [judge tips](https://info.devpost.com/blog/hackathon-judging-tips) · [demo-video tips](https://info.devpost.com/blog/6-tips-for-making-a-hackathon-demo-video)

**Tech:** [Strands SDK deep dive](https://aws.amazon.com/blogs/machine-learning/strands-agents-sdk-a-technical-deep-dive-into-agent-architectures-and-observability/) · [multi-agent patterns](https://strandsagents.com/docs/user-guide/concepts/multi-agent/multi-agent-patterns/) · [interrupts/HITL](https://strandsagents.com/docs/user-guide/concepts/interrupts/) · [AgentCore overview](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/what-is-bedrock-agentcore.html) · [Memory strategies](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/long-term-configuring-built-in-strategies.md) · [Gateway](https://aws.amazon.com/blogs/machine-learning/introducing-amazon-bedrock-agentcore-gateway-transforming-enterprise-ai-agent-tool-development/) · [pricing](https://aws.amazon.com/bedrock/agentcore/pricing/) · [Strands+AgentCore reference repo](https://github.com/aws-samples/sample-strands-agent-with-agentcore)

**Research:** [Horvitz mixed-initiative (CHI'99)](https://erichorvitz.com/chi99horvitz.pdf) · [Act or Escalate? (2026)](https://arxiv.org/html/2604.08588v1) · [τ-bench / pass^k](https://arxiv.org/pdf/2406.12045) · [Self-Correction Illusion (2026)](https://arxiv.org/html/2606.05976v1) · [Know It, Act on It (2026)](https://arxiv.org/html/2607.29433) · [CalBench multi-human coordination (2026)](https://arxiv.org/pdf/2605.09823) · [Safe & Responsible AI Agents (2026)](https://arxiv.org/html/2601.06223v1) · [VOI framework (2026)](https://arxiv.org/pdf/2601.06407)

**Landscape:** [a16z State of Consumer AI 2025](https://a16z.com/state-of-consumer-ai-2025-product-hits-misses-and-whats-next/) · [Pine AI](https://www.19pine.ai) · [Counterforce Health](https://www.counterforcehealth.org) · [FRANSiS](https://www.fransis.ai/) · [Blackbaud Development Agent](https://www.blackbaud.com/newsroom/article/introducing-development-agent) · ["Not Very Mutual" CHI 2025](https://dl.acm.org/doi/10.1145/3706598.3714192)
