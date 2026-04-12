# How to Build: Daily Brief App

A vibe-coded daily email digest that aggregates AI, security, startup news and cybersecurity stock data — built entirely with a coding agent (Claude Code), no manual coding.

---

## What it does

Runs on a schedule → fetches news from RSS feeds + scrapes one site → pulls stock prices from Yahoo Finance → builds a dark-theme HTML email → sends it via Resend API.

**Stack:** Python (stdlib only, zero pip installs) · Vercel · Resend · GitHub

---

## Step 1: The Script

**Approach:** One Python file does everything — fetch, parse, render, send.

**What worked:**
- Python stdlib only (`urllib`, `xml`, `smtplib`, `json`) — no dependency management
- Yahoo Finance chart API (`query1.finance.yahoo.com/v8/finance/chart/{symbol}`) for stock data — free, no auth
- TLDR Tech RSS feeds for AI / infosec / startups / product news
- NPR Up First RSS for world news headlines

**What didn't work:**
- AI Daily Brief RSS feed (`aidailybrief.beehiiv.com/feed`) — malformed XML caused parse errors every run
- **Fix:** Scrape the `/archive` page instead — it embeds a `window.__remixContext` JSON blob with all post slugs and dates; fetch the latest post page and extract `<p>` tags for article content

---

## Step 2: Email Delivery

Three attempts to send the email.

### Attempt 1 — Gmail SMTP ❌
```
smtplib.SMTP_SSL("smtp.gmail.com", 465)
server.login(email, app_password)
```
**Problem:** Gmail requires an App Password, which requires 2-Step Verification. Some Google Workspace / managed accounts have App Passwords disabled by the admin — no workaround.

### Attempt 2 — Gmail SMTP with App Password ❌
Created an App Password successfully on a personal account, but got:
```
SMTPAuthenticationError: SMTP auth failed
```
The account in use had App Passwords blocked at the account level.

### Attempt 3 — Resend API ✅ (with a fix)
```python
POST https://api.resend.com/emails
Authorization: Bearer re_xxxx
Content-Type: application/json
```
- Free tier: 100 emails/day, no domain verification needed for testing
- Uses `onboarding@resend.dev` as sender out of the box

**Problem hit 1:** Cloudflare 403 error code 1010 (bot block) on Vercel's servers
**Fix:** Add `User-Agent: Mozilla/5.0 (compatible; DailyBrief/1.0)` header to the request

**Problem hit 2:** First email landed in Gmail spam — `onboarding@resend.dev` is an unknown sender
**Fix:** Add `onboarding@resend.dev` to Gmail contacts (saved as "Anusha's Daily Brief") — Gmail trusts contacts and all future emails go straight to inbox

---

## Step 3: Hosting & Scheduling

### Option 1 — Local cron ✅ (simplest)
```bash
crontab -e
# 0 8 * * 1-5 cd /path && EMAIL_TO=x RESEND_API_KEY=x python3 daily_brief_email.py
```
Works, but requires your machine to be on at 8 AM.

### Option 2 — Vercel Serverless ✅
Created `api/send_brief.py` — a Python handler Vercel picks up automatically from the `api/` folder.

**Problems hit:**
1. Vercel detected `requirements.txt` and tried to run `uv lock` for a Python web framework — got `No project table found in pyproject.toml`
   - **Fix:** Delete `requirements.txt` (no dependencies needed anyway)
2. Without `requirements.txt`, Vercel tried to auto-detect a Python web app entrypoint (`app.py`, `main.py`, etc.) — got `No python entrypoint found`
   - **Fix:** Add `"framework": null` to `vercel.json`
3. Cron jobs (`vercel.json` `crons` field) require Vercel Pro for weekday-only schedules (`1-5`)

**Security:** Vercel injects a `CRON_SECRET` env var and sends it as `Authorization: Bearer` on cron requests — handler verifies this to block unauthorized triggers.

### Option 3 — GitHub Actions ✅ (free cron alternative)
Full cron syntax, free on public repos, run history in the Actions tab. Good fallback if Vercel crons need Pro.

---

## Step 4: Design

All CSS lives in `branding-guidelines.md` inside a fenced code block — the script reads and injects it at runtime. This keeps design separate from logic.

**Design choices:**
- New York Times-inspired: serif font, black/white, clean borders
- Dark stock ticker bar (terminal aesthetic) with 2-row layout per ticker (symbol+price / 1d · 1m changes)
- 3-column newspaper grid for news sections
- Each column stacks its 2 sections directly (no CSS grid row alignment) — avoids whitespace gaps between unequal-height cards

---

## Step 5: GitHub + Vercel

```bash
git init && git branch -M main
gh repo create daily-brief-app --public
git add . && git commit -m "initial"
git push
vercel --yes        # links repo, auto-deploys on every push
```

**Security rules added:**
- No email addresses or secrets in code — all via env vars (`EMAIL_TO`, `EMAIL_FROM`, `RESEND_API_KEY`)
- `daily_brief_preview.html` gitignored (contains external links from feeds)
- `SECURITY.md` documents fetch surface, secret handling, and agentic agent coding rules

---

## Environment Variables (all three required to send)

| Variable | Where to get it |
|----------|----------------|
| `EMAIL_TO` | Your email address |
| `RESEND_API_KEY` | resend.com → API Keys |
| `EMAIL_FROM` | Verified sender in Resend (or leave unset to use `onboarding@resend.dev`) |

---

## Use this yourself

Anyone can fork this repo and have their own daily brief running in under 10 minutes.

**1. Fork & clone**
```bash
# Fork on GitHub, then:
git clone https://github.com/<your-username>/daily-brief-app
cd daily-brief-app
```

**2. Get a Resend API key**
- Sign up free at [resend.com](https://resend.com) (100 emails/day free)
- Dashboard → API Keys → Create key

**3. Run locally**
```bash
export EMAIL_TO='you@gmail.com'
export RESEND_API_KEY='re_xxxxxxxxxxxx'
python3 daily_brief_email.py
```
No `pip install` needed — stdlib only.

**4. Deploy to Vercel**
```bash
npm install -g vercel
vercel --yes
```
Then add `EMAIL_TO` and `RESEND_API_KEY` in the Vercel dashboard under Environment Variables and redeploy.

**5. Whitelist the sender in Gmail**
The first email will go to spam. Add `onboarding@resend.dev` to your Gmail contacts (e.g. as "Daily Brief") and future emails go straight to inbox.

**6. Customise**
- Change tickers: edit `STOCKS` in `daily_brief_email.py`
- Add/remove feeds: edit `NEWS_FEEDS`
- Change the design: edit `branding-guidelines.md`

---

## Key lessons

| Lesson | Detail |
|--------|--------|
| stdlib > dependencies | Zero pip installs = zero deployment headaches |
| RSS feeds break | Always have a scrape fallback; beehiiv RSS was malformed XML |
| Gmail is hard to automate | App Passwords blocked on many accounts; use a dedicated email API |
| Cloudflare blocks headless requests | Always include a `User-Agent` header on outbound HTTP calls |
| Vercel auto-detection is aggressive | `"framework": null` in `vercel.json` opts out of framework detection |
| Keep secrets out from day 1 | Retrofitting env vars after a public push is painful |
