# Steward — Setup Checklist (Phase 0)

This file tracks the **account / credential** tasks that a human must do (agents can't log into your accounts).
The **local scaffold** (repo tree, license, config, stubs) is already generated. See `PHASED_IMPLEMENTATION.md` Phase 0.

> ⚠️ **Most urgent:** request the AWS credits **before Sept 11, 2026, 12:00 PM PT** (task P0.2).

## Human-only tasks

- [ ] **P0.1 — AWS account + AWS Builder ID.**
  - Create/confirm an AWS account: https://aws.amazon.com/
  - Create an **AWS Builder ID** (required in the submission): https://profile.aws.amazon.com/
  - Record the Builder ID somewhere safe (you enter it on Devpost).

- [ ] **P0.2 — ⚠️ Request the $50 AWS credits (DEADLINE Sept 11, 12:00 PM PT).**
  - Form: https://forms.gle/Ssr8zLw4afKg114M7
  - New AWS accounts may also get up to $200 Free Tier credits.

- [ ] **P0.3 — Enable Bedrock model access.**
  - Bedrock console → Model access → enable the two tiers:
    - Hard: `global.anthropic.claude-sonnet-4-6`
    - Cheap: a Nova/Haiku model (e.g. `us.amazon.nova-lite-v1:0`)
  - Confirm the **exact inference-profile IDs available in your region** and put them in `.env`
    (`MODEL_HARD`, `MODEL_CHEAP`). Record the region in `IMPLEMENTATION_PLAN.md` §16 D3/D8.

- [ ] **P0.4 — Twilio.**
  - Sign up: https://www.twilio.com/ ; buy an SMS-capable phone number.
  - Copy Account SID, Auth Token, and the from-number into `.env`
    (`TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`). Set `COORDINATOR_PHONE` to your demo phone.

- [ ] **P0.5 — Google Sheets substrate.**
  - Google Cloud console → new project → enable the **Google Sheets API**.
  - Create an **OAuth 2.0 client** (used later by AgentCore Identity's Google provider);
    put client id/secret in `.env`.
  - Create the demo **Google Sheet** with the tabs in `IMPLEMENTATION_PLAN.md` §6.1
    (`Volunteers`, `Shifts`, `Donations`, `Needs`, `Grants`, `TrustState`, `AuditLog`).
    Put its spreadsheet ID in `.env` (`GOOGLE_SHEET_ID`). `scripts/seed_sheet.py` will populate it (Phase 1).

- [ ] **P0.6 — Public git repo.**
  - Local git repo already exists with the plan docs + this scaffold.
  - Create the **public** remote (GitHub/GitLab/Bitbucket) and push. `gh` is not installed here;
    either install it (`brew install gh`) or create the repo in the web UI, then:
    `git remote add origin <url> && git push -u origin main`
  - The **LICENSE** (MIT) is already present — required for eligibility.
  - ⚠️ Commits must fall **inside the submission window** (Aug 10 – Sept 14, 2026).

- [ ] **P0.8 — Residency check.**
  - Confirm **every teammate** is NOT a resident of an excluded jurisdiction
    (`IMPLEMENTATION_PLAN.md` §2.7). India is eligible. Record cleared in §16 D7.

- [ ] **P0.9 — Local AWS credentials.**
  - `aws configure` (or set `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`/`AWS_REGION` in `.env`).

## Local environment (you can run these now)

```bash
# from the repo root
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then fill in the values above
pytest -q                     # ratchet tests are skipped until Phase 1
python -c "import strands, bedrock_agentcore; print('imports OK')"
```

## Exit gate for Phase 0
All boxes above checked; `pip install` succeeds; a trivial `Agent("hi")()` returns a response;
residency cleared. Then proceed to Phase 1 (`PHASED_IMPLEMENTATION.md`).
