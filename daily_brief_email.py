#!/usr/bin/env python3
import os
import json
import ssl
import urllib.request
import urllib.error
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

BRIEF_NAME = "Rakesh Daily Brief"
EMAIL_TO   = os.environ.get("EMAIL_TO", "purirakesh1962@gmail.com")
EMAIL_FROM = os.environ.get("EMAIL_FROM", "onboarding@resend.dev")
RESEND_KEY = os.environ.get("RESEND_API_KEY", "")

STOCKS = [
    {"symbol": "FXAIX",  "label": "Fidelity S&P 500"},
    {"symbol": "IVV",    "label": "iShares S&P 500"},
    {"symbol": "PRGFX",  "label": "T.Rowe Growth"},
    {"symbol": "PRUFX",  "label": "T.Rowe US Equity"},
    {"symbol": "PRUIX",  "label": "T.Rowe Instl"},
    {"symbol": "PRWCX",  "label": "T.Rowe Capital"},
    {"symbol": "TRAIX",  "label": "T.Rowe Balanced"},
    {"symbol": "VFIAX",  "label": "Vanguard 500"},
    {"symbol": "VFTAX",  "label": "Vanguard FTSE Social"},
    {"symbol": "VIGAX",  "label": "Vanguard Growth"},
    {"symbol": "TSLA",   "label": "Tesla"},
    {"symbol": "USO",    "label": "Oil ETF"},
    {"symbol": "^GSPC",  "label": "S&P 500"},
    {"symbol": "^IXIC",  "label": "Nasdaq"},
]

NEWS_FEEDS = [
    {
        "title": "Venezuela and Oil News",
        "url": "https://feeds.bbci.co.uk/news/world/rss.xml",
        "keywords": ["venezuela", "oil", "crude", "opec", "petroleum", "energy", "pdvsa"],
    },
    {
        "title": "Venezuela and Oil News 2",
        "url": "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
        "keywords": ["venezuela", "oil", "crude", "opec", "petroleum", "energy"],
    },
    {
        "title": "Tesla and EV News",
        "url": "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "keywords": ["tesla", "musk", "electric vehicle", "ev"],
    },
    {
        "title": "Finance and Markets",
        "url": "https://feeds.bbci.co.uk/news/business/rss.xml",
        "keywords": ["market", "stock", "fed", "rate", "economy", "inflation", "gdp"],
    },
    {
        "title": "Energy Markets",
        "url": "https://finance.yahoo.com/news/rssindex",
        "keywords": ["oil", "energy", "crude", "opec", "venezuela", "tesla"],
    },
]

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; RakeshDailyBrief/1.0)"}


def fetch_url(url, timeout=10):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:
        print("fetch error " + str(e))
        return ""


def strip_html(text):
    import re
    return re.sub(r"<[^>]+>", "", text or "").strip()


def fetch_stock(symbol):
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.parse.quote(symbol) + "?interval=1d&range=1mo"
        raw = fetch_url(url)
        if not raw:
            return None
        data = json.loads(raw)
        meta = data["chart"]["result"][0]["meta"]
        price = meta.get("regularMarketPrice", 0)
        prev  = meta.get("chartPreviousClose") or meta.get("previousClose") or price
        closes = data["chart"]["result"][0].get("indicators", {}).get("quote", [{}])[0].get("close", [])
        closes = [c for c in closes if c is not None]
        mo_ago = closes[0] if closes else price
        d_chg  = ((price - prev)   / prev   * 100) if prev   else 0
        mo_chg = ((price - mo_ago) / mo_ago * 100) if mo_ago else 0
        return {"price": price, "d_chg": d_chg, "mo_chg": mo_chg}
    except Exception as e:
        print("stock error " + symbol + " " + str(e))
        return None


def fetch_news(feed):
    raw = fetch_url(feed["url"])
    if not raw:
        return []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return []
    keywords = [k.lower() for k in feed.get("keywords", [])]
    results = []
    for item in root.findall(".//item"):
        title = strip_html(item.findtext("title", ""))
        desc  = strip_html(item.findtext("description", ""))[:200]
        link  = item.findtext("link", "")
        text  = (title + " " + desc).lower()
        if keywords and not any(k in text for k in keywords):
            continue
        results.append({"title": title, "desc": desc, "link": link})
        if len(results) >= 5:
            break
    return results


def color(val):
    return "#4caf50" if val >= 0 else "#f44336"


def pct(val):
    sign = "+" if val >= 0 else ""
    return sign + "{:.1f}%".format(val)


def build_html(stocks_data, news_data):
    today = datetime.now(timezone.utc).strftime("%A, %B %d, %Y")

    tickers = ""
    for s in stocks_data:
        info = s["info"]
        if info:
            price = "${:,.2f}".format(info["price"])
            tickers += (
                "<td style='padding:8px 12px;border-right:1px solid #333;white-space:nowrap;'>"
                "<div style='font-weight:700;font-size:12px;color:#fff;'>" + s["symbol"] + "</div>"
                "<div style='font-size:10px;color:#aaa;'>" + s["label"] + "</div>"
                "<div style='font-size:13px;color:#fff;'>" + price + "</div>"
                "<div style='font-size:10px;'>"
                "<span style='color:" + color(info["d_chg"]) + ";'>1D " + pct(info["d_chg"]) + "</span> "
                "<span style='color:" + color(info["mo_chg"]) + ";'>1M " + pct(info["mo_chg"]) + "</span>"
                "</div></td>"
            )
        else:
            tickers += (
                "<td style='padding:8px 12px;border-right:1px solid #333;white-space:nowrap;'>"
                "<div style='font-weight:700;font-size:12px;color:#fff;'>" + s["symbol"] + "</div>"
                "<div style='font-size:10px;color:#aaa;'>N/A</div></td>"
            )

    sections = ""
    for section in news_data:
        arts = ""
        for a in section["articles"]:
            arts += (
                "<div style='margin-bottom:14px;padding-bottom:14px;border-bottom:1px solid #eee;'>"
                "<a href='" + a["link"] + "' style='font-size:15px;font-weight:600;color:#111;text-decoration:none;'>"
                + a["title"] + "</a>"
                "<p style='margin:4px 0 0;font-size:13px;color:#555;'>" + a["desc"] + "</p>"
                "</div>"
            )
        if not arts:
            arts = "<p style='color:#999;font-size:13px;'>No matching articles today.</p>"
        sections += (
            "<div style='margin-bottom:28px;'>"
            "<h2 style='font-size:15px;font-weight:700;text-transform:uppercase;"
            "letter-spacing:1px;border-bottom:2px solid #111;padding-bottom:6px;margin-bottom:14px;'>"
            + section["title"] + "</h2>" + arts + "</div>"
        )

    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'></head>"
        "<body style='margin:0;padding:0;background:#f5f5f5;font-family:Georgia,serif;'>"
        "<div style='max-width:700px;margin:0 auto;background:#fff;'>"
        "<div style='background:#111;padding:24px 32px;'>"
        "<div style='font-size:11px;color:#888;letter-spacing:2px;text-transform:uppercase;'>Daily Intelligence</div>"
        "<h1 style='margin:4px 0;font-size:26px;color:#fff;font-weight:700;'>" + BRIEF_NAME + "</h1>"
        "<div style='font-size:13px;color:#aaa;'>" + today + "</div></div>"
        "<div style='background:#1a1a1a;overflow-x:auto;'>"
        "<table style='border-collapse:collapse;'><tr>" + tickers + "</tr></table></div>"
        "<div style='padding:28px;'>" + sections + "</div>"
        "<div style='background:#111;padding:14px 32px;text-align:center;'>"
        "<p style='color:#888;font-size:12px;margin:0;'>" + BRIEF_NAME + " - Delivered daily at 8am ET</p>"
        "</div></div></body></html>"
    )


def send_email(html_body):
    if not RESEND_KEY:
        print("No RESEND_API_KEY - skipping send")
        return False
    today = datetime.now(timezone.utc).strftime("%b %d, %Y")
    payload = json.dumps({
        "from":    EMAIL_FROM,
        "to":      [EMAIL_TO],
        "subject": BRIEF_NAME + " - " + today,
        "html":    html_body,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": "Bearer " + RESEND_KEY,
            "Content-Type":  "application/json",
            "User-Agent":    "RakeshDailyBrief/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, context=CTX) as r:
            resp = json.loads(r.read())
            print("Email sent! ID: " + str(resp.get("id")))
            return True
    except urllib.error.HTTPError as e:
        print("Resend error " + str(e.code) + ": " + e.read().decode())
        return False


def main():
    print("=== " + BRIEF_NAME + " ===")
    print("Fetching stocks...")
    stocks_data = []
    for s in STOCKS:
        print("  " + s["symbol"])
        info = fetch_stock(s["symbol"])
        stocks_data.append({"symbol": s["symbol"], "label": s["label"], "info": info})

    print("Fetching news...")
    news_data = []
    for feed in NEWS_FEEDS:
        print("  " + feed["title"])
        articles = fetch_news(feed)
        print("    " + str(len(articles)) + " articles")
        news_data.append({"title": feed["title"], "articles": articles})

    print("Building and sending...")
    html = build_html(stocks_data, news_data)
    with open("daily_brief_preview.html", "w", encoding="utf-8") as f:
        f.write(html)
    send_email(html)
    print("Done!")


if __name__ == "__main__":
    main()
