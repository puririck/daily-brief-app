#!/usr/bin/env python3
"""
Rakesh's Daily Brief
Fetches: Venezuela/oil news + Tesla news + Finance news + portfolio stock prices
Sends a notification email via Resend with a link to the full brief.
"""

import os
import json
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import ssl

# ── Configuration ────────────────────────────────────────────────────────────

BRIEF_NAME   = "Rakesh's Daily Brief"
EMAIL_TO     = os.environ.get("EMAIL_TO", "purirakesh1962@gmail.com")
EMAIL_FROM   = os.environ.get("EMAIL_FROM", "onboarding@resend.dev")
RESEND_KEY   = os.environ.get("RESEND_API_KEY", "")
BRIEF_URL    = os.environ.get("BRIEF_URL", "https://daily-brief-app.vercel.app/brief")

# ── Portfolio Tickers ─────────────────────────────────────────────────────────
# Your Morningstar portfolio tickers + Tesla + Crude Oil ETF

STOCKS = [
    # Your mutual funds / ETFs
    {"symbol": "FXAIX",  "label": "Fidelity S&P 500"},
    {"symbol": "IVV",    "label": "iShares S&P 500"},
    {"symbol": "PRGFX",  "label": "T.Rowe Growth"},
    {"symbol": "PRUFX",  "label": "T.Rowe US Equity"},
    {"symbol": "PRUIX",  "label": "T.Rowe Instl"},
    {"symbol": "PRWCX",  "label": "T.Rowe Capital Apprec"},
    {"symbol": "TRAIX",  "label": "T.Rowe Balanced"},
    {"symbol": "TSCXX",  "label": "T.Rowe Cash"},
    {"symbol": "VFIAX",  "label": "Vanguard 500 Index"},
    {"symbol": "VFTAX",  "label": "Vanguard FTSE Social"},
    {"symbol": "VIGAX",  "label": "Vanguard Growth Index"},
    # Key market watches
    {"symbol": "TSLA",   "label": "Tesla"},
    {"symbol": "USO",    "label": "Oil ETF (USO)"},
    {"symbol": "^GSPC",  "label": "S&P 500"},
    {"symbol": "^IXIC",  "label": "Nasdaq"},
]

# ── News Feeds ────────────────────────────────────────────────────────────────
# Venezuela oil & gas, crude oil prices, Tesla, global finance

NEWS_FEEDS = [
    {
        "title": "Venezuela & Oil News",
        "url": "https://feeds.reuters.com/reuters/businessNews",
        "keywords": ["venezuela", "oil", "crude", "OPEC", "petroleum", "energy", "pdvsa"],
    },
    {
        "title": "Tesla & EV News",
        "url": "https://feeds.feedburner.com/TechCrunch",
        "keywords": ["tesla", "musk", "electric vehicle", "EV", "gigafactory"],
    },
    {
        "title": "Finance & Markets",
        "url": "https://feeds.reuters.com/reuters/businessNews",
        "keywords": ["market", "stock", "fed", "rate", "economy", "inflation", "GDP", "interest"],
    },
    {
        "title": "Energy Markets",
        "url": "https://feeds.reuters.com/reuters/USenergyNews",
        "keywords": [],   # show all from this feed
    },
]

# ── Helpers ───────────────────────────────────────────────────────────────────

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; RakeshDailyBrief/1.0)"}


def fetch_url(url, timeout=10):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  [fetch error] {url}: {e}")
        return ""


def strip_html(text):
    import re
    return re.sub(r"<[^>]+>", "", text or "").strip()


def fetch_stock(symbol):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}?interval=1d&range=1mo"
    try:
        import urllib.parse
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}?interval=1d&range=1mo"
        raw = fetch_url(url)
        if not raw:
            return None
        data = json.loads(raw)
        meta = data["chart"]["result"][0]["meta"]
        price      = meta.get("regularMarketPrice", 0)
        prev_close = meta.get("chartPreviousClose") or meta.get("previousClose") or price
        closes     = data["chart"]["result"][0].get("indicators", {}).get("quote", [{}])[0].get("close", [])
        closes     = [c for c in closes if c is not None]
        mo_ago     = closes[0] if closes else price
        d_chg  = ((price - prev_close) / prev_close * 100) if prev_close else 0
        mo_chg = ((price - mo_ago)    / mo_ago     * 100) if mo_ago     else 0
        return {"price": price, "d_chg": d_chg, "mo_chg": mo_chg}
    except Exception as e:
        print(f"  [stock error] {symbol}: {e}")
        return None


import urllib.parse   # make sure it's imported at top level too


def fetch_news_feed(feed):
    raw = fetch_url(feed["url"])
    if not raw:
        return []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return []
    items = root.findall(".//item")
    results = []
    keywords = [k.lower() for k in feed.get("keywords", [])]
    for item in items[:40]:
        title = strip_html(item.findtext("title", ""))
        desc  = strip_html(item.findtext("description", ""))
        link  = item.findtext("link", "")
        text  = (title + " " + desc).lower()
        if keywords and not any(k in text for k in keywords):
            continue
        results.append({"title": title, "desc": desc[:200], "link": link})
        if len(results) >= 5:
            break
    return results


# ── Build HTML ────────────────────────────────────────────────────────────────

def build_html(stocks_data, news_data):
    today = datetime.now(timezone.utc).strftime("%A, %B %d, %Y")

    # Stock ticker rows
    ticker_rows = ""
    for s in stocks_data:
        sym   = s["symbol"]
        label = s["label"]
        info  = s["info"]
        if info:
            price  = f"${info['price']:,.2f}"
            d_chg  = info['d_chg']
            mo_chg = info['mo_chg']
            d_col  = "#4caf50" if d_chg >= 0 else "#f44336"
            m_col  = "#4caf50" if mo_chg >= 0 else "#f44336"
            d_str  = f"{'▲' if d_chg>=0 else '▼'}{abs(d_chg):.1f}%"
            m_str  = f"{'▲' if mo_chg>=0 else '▼'}{abs(mo_chg):.1f}%"
            ticker_rows += f"""
            <td style="padding:8px 14px;border-right:1px solid #333;white-space:nowrap;">
              <div style="font-weight:700;font-size:13px;color:#fff;">{sym}</div>
              <div style="font-size:11px;color:#aaa;">{label}</div>
              <div style="font-size:14px;color:#fff;">{price}</div>
              <div style="font-size:11px;">
                <span style="color:{d_col};">1D {d_str}</span>
                &nbsp;
                <span style="color:{m_col};">1M {m_str}</span>
              </div>
            </td>"""
        else:
            ticker_rows += f"""
            <td style="padding:8px 14px;border-right:1px solid #333;white-space:nowrap;">
              <div style="font-weight:700;font-size:13px;color:#fff;">{sym}</div>
              <div style="font-size:11px;color:#aaa;">N/A</div>
            </td>"""

    # News sections
    news_html = ""
    for section in news_data:
        articles_html = ""
        for art in section["articles"]:
            articles_html += f"""
            <div style="margin-bottom:16px;padding-bottom:16px;border-bottom:1px solid #e8e8e8;">
              <a href="{art['link']}" style="font-size:15px;font-weight:600;color:#111;text-decoration:none;line-height:1.4;">{art['title']}</a>
              <p style="margin:4px 0 0;font-size:13px;color:#555;line-height:1.5;">{art['desc']}</p>
            </div>"""
        if not articles_html:
            articles_html = "<p style='color:#999;font-size:13px;'>No matching articles today.</p>"
        news_html += f"""
        <div style="margin-bottom:32px;">
          <h2 style="font-size:16px;font-weight:700;text-transform:uppercase;letter-spacing:1px;
                     border-bottom:2px solid #111;padding-bottom:6px;margin-bottom:16px;">
            {section['title']}
          </h2>
          {articles_html}
        </div>"""

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>{BRIEF_NAME}</title></head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:Georgia,serif;">

<div style="max-width:700px;margin:0 auto;background:#fff;">

  <!-- Header -->
  <div style="background:#111;padding:24px 32px;">
    <div style="font-size:11px;color:#888;letter-spacing:2px;text-transform:uppercase;">Daily Intelligence</div>
    <h1 style="margin:4px 0;font-size:28px;color:#fff;font-weight:700;">{BRIEF_NAME}</h1>
    <div style="font-size:13px;color:#aaa;">{today}</div>
  </div>

  <!-- Stock Ticker Bar -->
  <div style="background:#1a1a1a;overflow-x:auto;">
    <table style="border-collapse:collapse;min-width:100%;">
      <tr>{ticker_rows}</tr>
    </table>
  </div>

  <!-- News -->
  <div style="padding:32px;">
    {news_html}
  </div>

  <!-- Footer -->
  <div style="background:#111;padding:16px 32px;text-align:center;">
    <p style="color:#888;font-size:12px;margin:0;">
      {BRIEF_NAME} · Delivered daily at 8am ET
    </p>
  </div>

</div>
</body></html>"""


# ── Send Email via Resend ─────────────────────────────────────────────────────

def send_email(html_body):
    if not RESEND_KEY:
        print("No RESEND_API_KEY set — skipping email send.")
        return False

    today = datetime.now(timezone.utc).strftime("%b %d, %Y")
    payload = json.dumps({
        "from":    EMAIL_FROM,
        "to":      [EMAIL_TO],
        "subject": f"{BRIEF_NAME} — {today}",
        "html":    html_body,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": f"Bearer {RESEND_KEY}",
            "Content-Type":  "application/json",
            "User-Agent":    "RakeshDailyBrief/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, context=ctx) as r:
            resp = json.loads(r.read())
            print(f"Email sent! ID: {resp.get('id')}")
            return True
    except urllib.error.HTTPError as e:
        print(f"Resend error {e.code}: {e.read().decode()}")
        return False


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"=== {BRIEF_NAME} — {datetime.now().strftime('%Y-%m-%d %H:%M')} ===\n")

    # Fetch stocks
    print("Fetching stock prices...")
    import urllib.parse as _up  # ensure available
    stocks_data = []
    for s in STOCKS:
        print(f"  {s['symbol']} ...", end=" ")
        info = fetch_stock(s["symbol"])
        print("ok" if info else "failed")
        stocks_data.append({**s, "info": info})

    # Fetch news
    print("\nFetching news...")
    news_data = []
    for feed in NEWS_FEEDS:
        print(f"  {feed['title']} ...")
        articles = fetch_news_feed(feed)
        print(f"    → {len(articles)} articles")
        news_data.append({"title": feed["title"], "articles": articles})

    # Build & send
    print("\nBuilding HTML...")
    html = build_html(stocks_data, news_data)

    preview_path = "daily_brief_preview.html"
    with open(preview_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Preview saved to {preview_path}")

    print("\nSending email...")
    send_email(html)
    print("\nDone!")


if __name__ == "__main__":
    main()
