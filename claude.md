---
name: daily-brief
description: Run and extend Anusha's Daily Brief (RSS + stocks + HTML email). Use when working with daily_brief_email.py, previews, feeds, stocks, or Gmail setup.
---

# Agentic Daily Brief — Skills & Operating Guide

This document describes **how the Daily Brief works** and **how an AI agent should behave** when helping run, extend, or debug it.

---

## What it is

**Anusha's Daily Brief** is a **deterministic automation**: a single Python script pulls curated news (RSS) and cybersecurity-relevant stock data, builds one HTML email, and sends it (or saves a local preview). There is no in-repo LLM loop—the "agentic" part is the **human + coding agent** (e.g. Cursor, Claude Code) that maintains the script, schedules runs, and fixes failures.

| Piece | Role |
|-------|------|
| `daily_brief_email.py` | End-to-end pipeline: fetch → parse → render → SMTP or preview |
| `daily_brief_preview.html` | Output when Gmail app password is not set |
| `dashboard.html` | Separate "Command Center" UI (local preview via static server) |

---

## Pipeline (how the brief is built)

1. **Market watch** — Yahoo Finance chart API (1mo daily closes) for tickers: ZS, PANW, CRWD, ANET, NTSK;
2. **News** — Parallel RSS fetches per section (TLDR AI / infosec / startups / product, AI Daily Brief, NPR world). Each section has a **per-feed article cap**.
3. **Composition** — HTML email: dark theme, hero, stocks table, sectioned news with relative timestamps ("2h ago").
4. **Delivery** — If `GMAIL_APP_PASSWORD` is set: SMTP SSL to Gmail. Otherwise: write `daily_brief_preview.html` and print setup instructions.

**Agent mental model:** same inputs every run → predictable output. Failures are usually network, RSS shape changes, or auth.

---

## Current Feed Sources

### News Feeds
The brief aggregates from **6 RSS sources** with article limits:

| Section | Source | URL | Max Articles |
|---------|--------|-----|--------------|
| 🤖 AI Models & Research | TLDR AI | `https://tldr.tech/api/rss/ai` | 1 |
| 📡 AI Daily Brief | Beehiiv (web scrape) | `https://aidailybrief.beehiiv.com/archive` | 4 |
| 🛡️ Information Security | TLDR Infosec | `https://tldr.tech/api/rss/infosec` | 1 |
| 🚀 Startups | TLDR Startups | `https://tldr.tech/rss/startups` | 1 |
| 📦 Product Management | TLDR Product | `https://tldr.tech/api/rss/product` | 1 |

| 🌍 Up First (NPR) | NPR Podcast | `https://www.npr.org/podcasts/510318/up-first/` | 3 |

**Note:** NPR Up First section dynamically extracts the top 3 stories from the latest episode transcript (e.g., "US-Iran peace talks in Islamabad collapse after 21 hours of negotiations", "President Trump announces U.S. Navy will blockade Strait of Hormuz", "Trump threatens to destroy Iranian mines and attack any Iranian vessels").

### Stock Data
Real-time market data from **Yahoo Finance API** for cybersecurity stocks:

| Ticker | Company | Notes |
|--------|---------|-------|
| ZS | Zscaler | Public company |
| PANW | Palo Alto Networks | Public company |
| CRWD | CrowdStrike | Public company |
| ANET | Arista Networks | Public company |
| NTSK | Netskope | Public company |

**Data format:** Daily % change + 1-month % change from Yahoo Finance chart API.

---

## Agent skills (what you should do)

### Run & verify

- Run: `python3 daily_brief_email.py` from the project root.
- Without credentials, confirm preview path and open `daily_brief_preview.html` if the user wants to see layout.
- With credentials, never echo or log the app password; confirm "email sent" from script output only.

### Configure safely

- **Email**: `EMAIL_TO` / `EMAIL_FROM` in script (or env-driven if user refactors). App passwords live only in `GMAIL_APP_PASSWORD`.
- **Feeds**: `NEWS_FEEDS` — tuple `(section_label, rss_url, max_items)`. Adjust caps or URLs when sources move.
- **Stocks**: `STOCKS` list of `(ticker, display_name)`. Yahoo symbol must match public chart API.

### Extend the brief

- New section: append to `NEWS_FEEDS`, add `SECTION_COLORS` entry, ensure RSS has standard `<item>` elements.
- New ticker: add to `STOCKS`; handle private companies as a row with `"private": True` like Netskope.
- Styling: `_HTML_STYLE` and `build_email_html()` only—keep table structure for email client compatibility.

### Debug

- **Empty section**: fetch timeout, bad URL, or RSS namespace/structure; check `[WARN]` lines from `fetch_url` / `parse_rss`.
- **Stocks N/A**: API change, rate limit, or symbol typo; verify chart JSON path in `fetch_stock`.
- **SMTP errors**: App Password vs normal password; 2FA required for app passwords.

---

## Related local tooling

- **Dashboard**: `.claude/launch.json` can serve the folder with `python3 -m http.server 8787` — open `dashboard.html` for the Command Center experience (independent of the email script unless wired by the user).

---

## Boundaries

- Do **not** store secrets in the repo; use environment variables only.
- The brief is **aggregation + formatting**, not fact-checking; agents should not claim the email content was "verified" unless the user adds that step.
- RSS descriptions are truncated (~250 chars) for email width; deeper analysis is out of scope unless added explicitly.

---

## One-line summary for other agents

> **Daily Brief skill:** Run `daily_brief_email.py`; it aggregates RSS (AI, security, startups, product, world) + Yahoo stock rows into one HTML email; requires `GMAIL_APP_PASSWORD` to send, else writes `daily_brief_preview.html`. Extend via `NEWS_FEEDS`, `STOCKS`, and `SECTION_COLORS` in `daily_brief_email.py`.
