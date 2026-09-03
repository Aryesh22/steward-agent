# Your Tasks — a step-by-step guide (no experience needed)

This is everything **you** need to do for Phase 0 (accounts) and Phase 1 (turning on the live parts).
Claude has already written all the code. These steps give the code the accounts + keys it needs to run.

> Tip: whenever a step says "run this command", you can paste it into the Claude Code chat starting
> with an exclamation mark, e.g. `!pytest -q`, and the result comes back so Claude can help if it breaks.
> Anything in `code font` is meant to be copied exactly.

**Time needed:** about 1–1.5 hours. You can stop and resume anytime. Do the steps in order.

---

## Part A — Open the Terminal (2 minutes)

1. Press `Cmd + Space`, type **Terminal**, press Enter. A window with text appears.
2. Copy-paste this and press Enter (it moves into your project folder):
   ```
   cd ~/Desktop/aws-winners
   ```
3. That's it. Keep this window open; you'll come back to it in Part G and H.

---

## Part B — AWS account + Builder ID (15 min) — needs a card

1. Go to **https://aws.amazon.com/** → click **Create an AWS Account** (top right).
2. Enter your email (you can use vartika55@gmail.com), pick a password, and an account name like `steward`.
3. It will ask for a **credit/debit card** and a **phone number** for verification. Enter them.
   (You very likely won't be charged — the $50 credits + free tier cover this project — but AWS requires a card to open an account.)
4. Choose the **Basic (Free)** support plan when asked.
5. When done, you can sign in at **https://console.aws.amazon.com/**.
6. Now create an **AWS Builder ID** (a separate free ID the hackathon requires):
   - Go to **https://profile.aws.amazon.com/** → **Create AWS Builder ID** → sign up with your email.
   - **Write down your Builder ID** — you'll type it into the hackathon submission form later.

✅ Done when: you can log into the AWS console, and you have a Builder ID written down.

---

## Part C — ⚠️ Request the $50 free credits (5 min) — DO THIS EARLY

> **Deadline: September 11, 2026, 12:00 PM Pacific Time.** Don't skip or delay this.

1. Open the credits form: **https://forms.gle/Ssr8zLw4afKg114M7**
2. Fill it in with your details (use the same email as your AWS account).
3. Submit. Credits usually arrive by email within a few days.

✅ Done when: you've submitted the form.

---

## Part D — Turn on the AI models in AWS (10 min)

AWS calls its AI service **Bedrock**. You must switch on access to two AI models.

1. Sign in to **https://console.aws.amazon.com/**.
2. In the top search bar, type **Bedrock** and click **Amazon Bedrock**.
3. **Set your region** (top-right corner dropdown): choose **US West (Oregon) us-west-2**.
   (Use this exact region — the code defaults to it.)
4. In the left menu, scroll down to **Model access** (sometimes under "Bedrock configurations").
5. Click **Enable specific models** (or **Manage model access**).
6. Tick the boxes for:
   - **Anthropic – Claude** (any Claude "Sonnet" model listed)
   - **Amazon – Nova** (the "Nova Lite" model)
7. Click **Save changes / Request access**. Access is usually granted within a minute or two.
8. Tell Claude in the chat: *"Bedrock model access is on in us-west-2"* — Claude will confirm the exact
   model names to put in your settings file (Part G).

✅ Done when: Claude Sonnet and Nova show **Access granted** on the Model access page.

---

## Part E — Twilio for text messages (15 min) — free

Twilio is the service that lets Steward send SMS.

1. Go to **https://www.twilio.com/try-twilio** → sign up (free trial).
2. Verify your email and your mobile phone number when asked.
3. On the Twilio **Console dashboard** (https://console.twilio.com/), find the **Account Info** box.
   You'll see two values — copy both somewhere safe:
   - **Account SID** (starts with `AC...`)
   - **Auth Token** (click to reveal)
4. Get a phone number: left menu → **Phone Numbers → Manage → Buy a number** (trial gives you one free).
   Pick any number with **SMS** capability. Copy it (looks like `+15551234567`).
5. **Trial limitation (important):** a free Twilio account can only text **verified** numbers. Add your own
   mobile as a verified number: **Phone Numbers → Verified Caller IDs → Add a number** → verify with the code.
   (For the demo, texting your own phone is all you need.)

✅ Done when: you have the **Account SID**, **Auth Token**, your **Twilio number**, and your own phone verified.

---

## Part F — Google Sheet + access key (20 min) — free

Steward runs "on top of" a normal Google Sheet. You'll create the sheet and a key that lets the code read/write it.

### F1. Create the Sheet
1. Go to **https://sheets.google.com/** → **Blank spreadsheet**.
2. Name it `Steward Demo`.
3. Look at the web address. It looks like
   `https://docs.google.com/spreadsheets/d/`**`1A2b3C...xyz`**`/edit`
   The long code between `/d/` and `/edit` is the **Sheet ID**. Copy it.
   (You don't need to add any tabs by hand — a script fills them in later.)

### F2. Create the access key (a "service account")
1. Go to **https://console.cloud.google.com/**. If it's your first time, accept the terms and create a project
   (top bar → **Select a project → New Project** → name it `steward` → Create). Wait a few seconds, then make
   sure that project is selected in the top bar.
2. Turn on the Sheets API: in the top search bar type **Google Sheets API** → click it → **Enable**.
3. Create the key:
   - Left menu → **APIs & Services → Credentials**.
   - Click **+ Create Credentials → Service account**.
   - Name it `steward-bot` → **Create and continue** → skip the optional steps → **Done**.
   - You'll see the new service account with an **email** like `steward-bot@steward-xxxx.iam.gserviceaccount.com`.
     **Copy that email.**
   - Click the service account → **Keys** tab → **Add key → Create new key → JSON → Create**.
     A `.json` file downloads. This is your key file.
4. Move the key into your project and give it a simple name:
   - In Finder, find the downloaded `.json` file (usually in Downloads).
   - Rename it to `service-account.json` and drag it into the `aws-winners` folder on your Desktop.
5. **Share the Sheet with the bot:** open your `Steward Demo` sheet → click **Share** (top right) → paste the
   **service account email** from step 3 → give it **Editor** → **Send**. (Ignore any "outside org" warning.)

✅ Done when: you have the **Sheet ID**, a file named `service-account.json` inside the project folder, and the
Sheet is shared with the service-account email as Editor.

---

## Part G — Put all your keys into the settings file (10 min)

Now you'll paste everything you collected into one settings file called `.env`.

1. In Terminal (from Part A), run this once to create the file from the template:
   ```
   cp .env.example .env
   ```
2. Open it in a simple editor by running:
   ```
   open -e .env
   ```
   (TextEdit opens.) Fill in the blanks with the values you collected. It looks like this — replace the empty
   parts after each `=` (no spaces, no quotes):

   ```
   AWS_REGION=us-west-2
   AWS_ACCESS_KEY_ID=        <- see step 3 below
   AWS_SECRET_ACCESS_KEY=    <- see step 3 below

   MODEL_HARD=               <- Claude will give you this exact value
   MODEL_CHEAP=              <- Claude will give you this exact value

   TWILIO_ACCOUNT_SID=AC...          (from Part E)
   TWILIO_AUTH_TOKEN=...             (from Part E)
   TWILIO_FROM_NUMBER=+1...          (your Twilio number)
   COORDINATOR_PHONE=+1...           (your own verified mobile)

   GOOGLE_SHEET_ID=...               (from Part F1)
   GOOGLE_SERVICE_ACCOUNT_FILE=./service-account.json

   ORG_ID=demo-pantry
   ```
3. **AWS access keys** (for `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`):
   - In the AWS console, top search bar → **IAM** → left menu **Users** → **Create user** → name `steward` →
     Next → **Attach policies directly** → tick **AdministratorAccess** (fine for a hackathon) → Create.
   - Click the new user → **Security credentials** tab → **Create access key** → choose **Command Line
     Interface (CLI)** → Create. Copy the **Access key** and **Secret access key** into the file.
     (You only see the secret once — if you lose it, just make a new one.)
4. Save the file in TextEdit (`Cmd + S`) and close it.

> 🔒 Safety: `.env` and `service-account.json` hold secrets. The project is set up to **never** upload them to
> GitHub. Don't paste their contents into public places.

✅ Done when: `.env` has every value filled in and is saved.

---

## Part H — Install and run (10 min)

Now the exciting part — turn it on. Run these in Terminal one at a time.

1. Create a workspace and install the code's dependencies (one-time, ~2–3 min):
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Load your settings and check the ratchet logic passes (this needs no accounts — it should already work):
   ```
   pytest -q
   ```
   You should see something like `24 passed`.
3. Load your `.env` values into this terminal:
   ```
   set -a; source .env; set +a
   ```
4. **Phase 1 live step — create the two AWS databases:**
   ```
   python -c "from infra.ddb import create_tables; create_tables(); print('tables created')"
   ```
5. **Phase 1 live step — fill the Google Sheet with demo data:**
   ```
   python scripts/seed_sheet.py
   ```
   Open your Google Sheet — you should now see tabs (Volunteers, Shifts, Donations, etc.) filled in.
6. **Phase 1 live step — send yourself a test text:**
   ```
   python -c "from app.tools.twilio import send_sms; import os; print(send_sms(os.environ['COORDINATOR_PHONE'], 'Hello from Steward!'))"
   ```
   Your phone should get a text. (On a Twilio trial it may start with "Sent from your Twilio trial account".)

✅ Done when: tests pass, the Sheet is filled in, and you received the test text.

---

## Part I — Put the code online (10 min) — can be done anytime before submission

1. Go to **https://github.com/** → sign up / log in.
2. Click **+ (top right) → New repository** → name it `steward` → **Public** → **Create repository**.
3. GitHub shows a page with commands. In Terminal, run (replace `YOUR-USERNAME`):
   ```
   git remote add origin https://github.com/YOUR-USERNAME/steward.git
   git branch -M main
   git push -u origin main
   ```
   If it asks for a password, GitHub now wants a **personal access token** instead — if that happens, tell Claude
   and it'll walk you through making one (2 minutes).

✅ Done when: refreshing your GitHub repo page shows all the project files.

---

## Also do (5 min, no computer needed)

- **Residency check:** confirm every teammate is **not** a resident of: Argentina, Australia, Brazil, Hong Kong,
  Indonesia, Italy, Malaysia, Philippines, Thailand, Vietnam, Singapore, Belarus, UAE, Quebec (Canada), Russia,
  Crimea, Cuba, Iran, North Korea, Syria. (India is fine.)

---

## When you're stuck
Paste the exact error text into the Claude Code chat. Claude wrote all the code and can tell you what to fix.
You do **not** need to understand the errors — just copy them in.

## What happens next
Once Parts B–H are done, Claude can build and actually run **Phase 2** (the agents + decision brain) and beyond,
and you'll be able to see Steward working end-to-end.
