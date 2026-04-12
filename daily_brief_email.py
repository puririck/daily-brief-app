#!/usr/bin/env python3
"""
Daily Brief — Email Sender
Fetches latest AI/security/startup news and cybersecurity stock data,
then sends a beautifully formatted HTML email via Resend.

Setup:
  1. Sign up at https://resend.com and get an API key
  2. Verify your sender email at resend.com/settings/domains (or use a verified domain)
  3. Set environment variables:
     export EMAIL_TO='you@gmail.com'
     export EMAIL_FROM='Daily Brief <you@yourdomain.com>'
     export RESEND_API_KEY='re_xxxxxxxxxxxx'
  4. Run:
     python3 daily_brief_email.py
"""

import json
import re
import os
import sys
import ssl
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

# ──────────────────────────────────────────────
#  CONFIG
# ──────────────────────────────────────────────
EMAIL_TO      = os.environ.get("EMAIL_TO", "")
EMAIL_FROM    = os.environ.get("EMAIL_FROM", "Daily Brief <onboarding@resend.dev>")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")

STOCKS = [
    ("ZS",   "Zscaler"),
    ("PANW", "Palo Alto Networks"),
    ("CRWD", "CrowdStrike"),
    ("ANET", "Arista Networks"),
    ("NTSK", "Netskope"),
]

NEWS_FEEDS = [
    ("🤖 AI Models & Research",       "https://tldr.tech/api/rss/ai",                       1),
    ("📡 AI Daily Brief",              "https://aidailybrief.beehiiv.com/archive",            4),
    ("🛡️ Information Security",        "https://tldr.tech/api/rss/infosec",                   1),
    ("🚀 Startups",                    "https://tldr.tech/rss/startups",                      1),
    ("📦 Product Management",          "https://tldr.tech/api/rss/product",                   1),

    ("🌍 Up First (NPR)",              "https://www.npr.org/rss/podcast.php?id=510318",       3),
]

SECTION_COLORS = {
    "🤖 AI Models & Research":   "#7b68ee",
    "📡 AI Daily Brief":         "#4da6ff",
    "🛡️ Information Security":   "#ff5c5c",
    "🚀 Startups":               "#23d18b",
    "📦 Product Management":     "#f5a623",

    "🌍 Up First (NPR)":         "#ff6b6b",
}


# ──────────────────────────────────────────────
#  HELPERS
# ──────────────────────────────────────────────
def fetch_url(url: str, timeout: int = 12) -> str | None:
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; DailyBrief/1.0)"}
        )
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  [WARN] fetch failed for {url}: {e}")
        return None


def strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html or "")
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;",  "&", text)
    text = re.sub(r"&lt;",   "<", text)
    text = re.sub(r"&gt;",   ">", text)
    text = re.sub(r"&quot;", '"', text)
    return re.sub(r"\s+", " ", text).strip()


def fmt_pct(v: float | None) -> tuple[str, bool]:
    if v is None:
        return "N/A", False
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.2f}%", v >= 0


def fmt_price(v: float | None) -> str:
    if v is None:
        return "—"
    return f"${v:.2f}"


def fetch_npr_up_first() -> list[dict] | None:
    """Fetch the top 3 stories from the latest NPR Up First episode"""
    rss_url = "https://www.npr.org/rss/podcast.php?id=510318"
    content = fetch_url(rss_url)
    if not content:
        return None
    
    # Parse RSS to get the latest episode
    items = parse_rss(content, 1)  # Get only the latest episode
    if not items:
        return None
    
    latest_episode = items[0]
    # For NPR, get the full description without truncation
    try:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(content)
        ns = {
            'content': 'http://purl.org/rss/1.0/modules/content/',
        }
        item_elements = root.findall(".//item")
        if item_elements:
            # Get content:encoded for full description
            desc_elem = item_elements[0].find("content:encoded", ns)
            if desc_elem is not None and desc_elem.text:
                description = strip_html(desc_elem.text)
            else:
                description = latest_episode.get("desc", "")
        else:
            description = latest_episode.get("desc", "")
    except:
        description = latest_episode.get("desc", "")
    
    # Extract the 3 key stories from the description
    # The description contains sentences separated by periods
    # Split by '. ' to avoid splitting on abbreviations like "W."
    sentences = [s.strip() for s in re.split(r'\.\s+', description) if s.strip() and len(s.strip()) > 10]
    
    # Take up to 3 sentences as the key stories
    key_stories = sentences[:3]
    
    # Build news items
    articles = []
    for story in key_stories:
        articles.append({
            "title": story,
            "link": latest_episode.get("link", "https://www.npr.org/podcasts/510318/up-first/"),
            "desc": "",
            "date": latest_episode.get("date", datetime.now(timezone.utc).isoformat())
        })
    
    return articles


def fetch_ai_daily_brief() -> list[dict] | None:
    """Fetch the most recent post from aidailybrief.beehiiv.com/archive."""
    archive_html = fetch_url("https://aidailybrief.beehiiv.com/archive")
    if not archive_html:
        return None

    # Extract posts array from embedded Remix JSON
    ctx_match = re.search(r'window\.__remixContext\s*=\s*(\{.*?\})\s*;', archive_html, re.DOTALL)
    if not ctx_match:
        return None

    ctx_str = ctx_match.group(1)
    # Pull out each post object: grab slug, title, and date
    post_matches = re.findall(
        r'"slug":"([^"]+)".*?"web_title":"([^"]+)".*?"override_scheduled_at":"([^"]+)"',
        ctx_str
    )
    if not post_matches:
        return None

    # Sort by date descending and take the most recent
    from datetime import datetime, timezone
    def parse_dt(s):
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            return datetime.min.replace(tzinfo=timezone.utc)

    post_matches.sort(key=lambda t: parse_dt(t[2]), reverse=True)
    slug, title, pub_date_str = post_matches[0]
    post_url = f"https://aidailybrief.beehiiv.com/p/{slug}"
    pub_date = parse_dt(pub_date_str)

    # Fetch the post page and extract meaningful paragraphs
    post_html = fetch_url(post_url)
    if not post_html:
        return [{"title": title, "link": post_url, "desc": "", "date": pub_date_str}]

    paras = re.findall(r'<p[^>]*>(.*?)</p>', post_html, re.DOTALL)
    articles = []
    for raw in paras:
        text = re.sub(r'<[^>]+>', '', raw)
        text = re.sub(r'&[a-z]+;', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        # Skip short, CSS/JS, or nav fragments
        if len(text) < 60:
            continue
        if any(kw in text[:80] for kw in ['function', '{', 'var ', 'const ', 'Subscribe', '▶']):
            continue
        # First sentence as title, rest as desc
        parts = re.split(r'(?<=[.!?])\s+', text, maxsplit=1)
        item_title = parts[0].strip()
        item_desc  = parts[1].strip() if len(parts) > 1 else ""
        if len(item_title) > 160:
            item_title = item_title[:157] + "..."
        articles.append({
            "title": item_title,
            "link":  post_url,
            "desc":  item_desc[:200] if item_desc else "",
            "date":  pub_date_str,
        })
        if len(articles) >= 4:
            break

    return articles or [{"title": title, "link": post_url, "desc": "", "date": pub_date_str}]


def fetch_tldr_articles(url: str, headline_phrases: list[str]) -> list[tuple[str, str]] | None:
    """Fetch TLDR daily digest and extract summaries for specific headline phrases"""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; DailyBrief/1.0)"}
        )
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            html_content = resp.read().decode("utf-8", errors="replace")
        
        # Extract articles from sections with their structured summaries
        # Pattern matches: <h3>headline</h3></a><div class="newsletter-html">summary</div>
        article_pattern = r'<h3>([^<]+)</h3>\s*</a>\s*<div class="newsletter-html">([^<]*(?:<[^/][^>]*>[^<]*)*?)</div>'
        matches = re.findall(article_pattern, html_content, re.DOTALL)
        
        if matches:
            articles = []
            for phrase in headline_phrases[:3]:  # Limit to 3 phrases
                phrase_lower = phrase.lower().strip()
                # Find matching article by comparing headline keywords
                for headline, summary in matches:
                    headline_lower = headline.lower()
                    # Check if key words from phrase are in headline
                    words = [w for w in phrase_lower.split() if len(w) > 3]
                    if any(word in headline_lower for word in words[:2]):  # Match first 2 content words
                        # Skip sponsor articles
                        if 'Sponsor' not in headline and 'sponsor' not in summary.lower():
                            # Clean up HTML tags and entities
                            summary_clean = re.sub(r'<[^>]+>', '', summary).strip()
                            summary_clean = re.sub(r'&[a-z]+;', '', summary_clean).strip()
                            
                            # Get first sentence
                            sentences = re.split(r'[.!?]+', summary_clean)
                            first_sentence = sentences[0].strip() if sentences and sentences[0].strip() else None
                            
                            if first_sentence and len(first_sentence) > 5:
                                articles.append((phrase, first_sentence + ('.' if not first_sentence.endswith('.') else '')))
                                break
            
            return articles if articles else None
        
        return None
    except Exception as e:
        # Silently fail - fall back to title parsing
        return None


# ──────────────────────────────────────────────
#  STOCK DATA (Yahoo Finance)
# ──────────────────────────────────────────────
def fetch_stock(symbol: str) -> dict | None:
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        "?range=1mo&interval=1d&includePrePost=false"
    )
    content = fetch_url(url)
    if not content:
        return None
    try:
        data    = json.loads(content)
        result  = data["chart"]["result"][0]
        closes  = [c for c in result["indicators"]["quote"][0]["close"] if c is not None]
        if len(closes) < 2:
            return None
        cur     = closes[-1]
        prev    = closes[-2]
        start   = closes[0]
        return {
            "price": cur,
            "day":   (cur - prev)  / prev  * 100,
            "month": (cur - start) / start * 100,
        }
    except Exception as e:
        print(f"  [WARN] stock parse failed for {symbol}: {e}")
        return None


# ──────────────────────────────────────────────
#  RSS PARSING
# ──────────────────────────────────────────────
def parse_rss(content: str | None, limit: int = 4) -> list[dict]:
    if not content:
        return []
    try:
        # Parse XML with namespace handling
        root = ET.fromstring(content)
        # Define namespace map for common RSS namespaces
        ns = {
            'rss': 'http://purl.org/rss/1.0/',
            'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
            'dc': 'http://purl.org/dc/elements/1.1/',
            'content': 'http://purl.org/rss/1.0/modules/content/',
        }

        items = []
        # Try different ways to find items
        item_elements = root.findall(".//item") or root.findall(".//rss:item", ns) or root.findall(".//{http://purl.org/rss/1.0/}item")

        for item in item_elements[:limit]:
            # Helper function to safely get text
            def safe_text(*paths):
                for path in paths:
                    try:
                        text = item.findtext(path)
                        if text and isinstance(text, str):
                            return text.strip()
                    except:
                        continue
                return ""

            title = safe_text("title", "rss:title", "{http://purl.org/rss/1.0/}title")
            if not title:
                continue

            link = safe_text("link", "rss:link", "{http://purl.org/rss/1.0/}link")
            desc = safe_text("description", "rss:description", "{http://purl.org/rss/1.0/}description", "content:encoded")
            desc = strip_html(desc)[:250] if desc else ""

            date = safe_text("pubDate", "rss:pubDate", "{http://purl.org/rss/1.0/}pubDate", "dc:date")

            items.append({"title": title, "link": link, "desc": desc, "date": date})
        return items
    except Exception as e:
        print(f"  [WARN] RSS parse error: {e}")
        return []


def relative_date(date_str: str) -> str:
    if not date_str:
        return ""
    try:
        # Strip timezone abbreviations that strptime can't handle
        clean = re.sub(r"\s+[A-Z]{2,4}$", "", date_str.strip())
        formats = [
            "%a, %d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S%z",
        ]
        pub = None
        for fmt in formats:
            try:
                pub = datetime.strptime(clean, fmt)
                break
            except ValueError:
                continue
        if pub is None:
            return ""
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        now  = datetime.now(timezone.utc)
        diff = now - pub
        h    = int(diff.total_seconds() // 3600)
        m    = int(diff.total_seconds() // 60)
        if m < 1:   return "just now"
        if m < 60:  return f"{m}m ago"
        if h < 24:  return f"{h}h ago"
        d = diff.days
        return "yesterday" if d == 1 else f"{d}d ago"
    except Exception:
        return ""


# ──────────────────────────────────────────────
#  EMAIL HTML GENERATION
# ──────────────────────────────────────────────

def load_branding_css() -> str:
    """Load CSS styling from branding-guidelines.md"""
    try:
        with open("branding-guidelines.md", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Extract CSS from markdown code block
        import re
        css_match = re.search(r'```css\s*(.*?)\s*```', content, re.DOTALL)
        if css_match:
            return css_match.group(1).strip()
        
        # Fallback: return empty string if not found
        print("  [WARN] Could not extract CSS from branding-guidelines.md")
        return ""
    except Exception as e:
        print(f"  [WARN] Could not load branding CSS: {e}")
        return ""

_HTML_STYLE = load_branding_css()

def build_email_html(stocks_rows: list[dict], news_sections: list[tuple]) -> str:
    today = datetime.now().strftime("%A, %B %d, %Y")

    # ── stock ticker ──
    stock_ticker_html = '<div class="stock-ticker">'
    for i, row in enumerate(stocks_rows):
        sym = row["sym"]
        price_html = fmt_price(row.get("price"))
        day_str, day_up = fmt_pct(row.get("day"))
        month_str, month_up = fmt_pct(row.get("month"))

        if row.get("private"):
            stock_ticker_html += (
                f'<span class="stock-item">'
                f'<span class="stock-top"><span class="stock-symbol">{sym}</span></span>'
                f'<span class="stock-bot"><span class="pvt">PRIVATE</span></span>'
                f'</span>'
            )
        else:
            day_class = "positive" if day_up else ("negative" if day_str != "N/A" else "")
            month_class = "positive" if month_up else ("negative" if month_str != "N/A" else "")
            stock_ticker_html += (
                f'<span class="stock-item">'
                f'<span class="stock-top"><span class="stock-symbol">{sym}</span><span class="stock-price">{price_html}</span></span>'
                f'<span class="stock-bot"><span class="stock-change-label">1d</span><span class="stock-change {day_class}">{day_str}</span><span class="stock-sep-inner">·</span><span class="stock-change-label">1m</span><span class="stock-change {month_class}">{month_str}</span></span>'
                f'</span>'
            )

        if i < len(stocks_rows) - 1:
            stock_ticker_html += '<span class="stock-sep">|</span>'

    stock_ticker_html += '</div>'

    # ── news sections ──
    news_html = ""
    # Arrange sections in specific 3-column layout:
    # Row 1: AI Models & Research, Up First (NPR), Information Security
    # Row 2: Product Management, AI Daily Brief, Startups
    sections_dict = dict(news_sections)
    arranged_sections = [
        ("🤖 AI Models & Research", sections_dict.get("🤖 AI Models & Research", [])),
        ("🌍 Up First (NPR)", sections_dict.get("🌍 Up First (NPR)", [])),
        ("🛡️ Information Security", sections_dict.get("🛡️ Information Security", [])),
        ("📦 Product Management", sections_dict.get("📦 Product Management", [])),
        ("📡 AI Daily Brief", sections_dict.get("📡 AI Daily Brief", [])),
        ("🚀 Startups", sections_dict.get("🚀 Startups", [])),
    ]

    def build_section_html(section_list):
        html = ""
        for section_name, items in section_list:
            print(f"DEBUG: Processing section '{section_name}' with {len(items)} items")
            # Remove emoji from section name for cleaner headings
            clean_section_name = section_name.replace('🤖 ', '').replace('📡 ', '').replace('🛡️ ', '').replace('🚀 ', '').replace('📦 ', '').replace('🌍 ', '')
            html += f'<div class="news-section">'
            html += f'<h3 class="sec-label">{clean_section_name}</h3>'
            if not items:
                print(f"DEBUG: No items for section '{section_name}'")
                html += '<div class="news-item"><span style="color:#666666">No articles available</span></div>'
            else:
                print(f"DEBUG: Processing {len(items)} items for section '{section_name}'")
                for item in items:
                    rel = relative_date(item.get("date",""))
                    # Extract first sentence/line from description
                    desc = item.get("desc", "").strip()
                    if desc:
                        # Get first sentence (up to first period, question mark, or exclamation mark)
                        first_sentence = desc.split('.')[0].split('?')[0].split('!')[0].strip()
                        if len(first_sentence) > 120:  # If too long, truncate
                            first_sentence = first_sentence[:117] + "..."
                        elif not first_sentence.endswith(('.', '!', '?')):
                            first_sentence = first_sentence + "."
                    else:
                        first_sentence = ""

                    # For TLDR feeds, fetch individual articles with summaries
                    is_tldr = 'tldr.tech' in item.get('link', '')
                    if is_tldr:
                        # Extract headline phrases from the title (e.g., "OpenAI $100 plan, Claude Cowork, Perplexity x Plaid")
                        full_title = item['title']
                        # Remove date prefix (e.g., "TLDR AI 2026-04-10")
                        clean_title = re.sub(r'^TLDR\s+\w+\s+\d{4}-\d{2}-\d{2}', '', full_title).strip()
                        
                        # Split by comma to get headline phrases
                        phrases = [p.strip() for p in clean_title.split(',') if p.strip()]
                        
                        # Add the top headline linked to the feed
                        html += f"""
                    <div class="news-item">
                      <h4 class="news-title"><a href="{item['link']}" target="_blank" rel="noopener">{full_title}</a></h4>
                    </div>"""
                        
                        # Try to fetch summaries for these specific phrases
                        articles = fetch_tldr_articles(item['link'], phrases)
                        if articles and len(articles) > 0:
                            # Create news items - one for each headline phrase with summary
                            for article_headline, article_summary in articles:
                                html += f"""
                    <div class="news-item">
                      <h4 class="news-title">{article_headline}</h4>
                      <div class="news-sub">{article_summary}</div>
                    </div>"""
                            continue  # Skip the single item below
                        
                        # Fallback for TLDR feeds - display the 3 headline phrases without summaries
                        for phrase in phrases[:3]:  # Limit to 3 phrases max
                            html += f"""
                    <div class="news-item">
                      <h4 class="news-title">{phrase}</h4>
                    </div>"""
                        continue  # Skip the single item below
                    
                    # For non-TLDR feeds, use normal processing
                    main_content = item['title']
                    sub_html = f'<span class="news-desc">{first_sentence}</span>' if first_sentence else ""

                    html += f"""
                    <div class="news-item">
                      <h4 class="news-title"><a href="{item['link']}" target="_blank" rel="noopener">{main_content}</a></h4>
                      {sub_html}
                    </div>"""
            html += '</div>'
        return html

    news_html = f"""
    <div class="news-container">
      <div class="news-column">{build_section_html([arranged_sections[0]])}{build_section_html([arranged_sections[3]])}</div>
      <div class="news-column">{build_section_html([arranged_sections[1]])}{build_section_html([arranged_sections[4]])}</div>
      <div class="news-column">{build_section_html([arranged_sections[2]])}{build_section_html([arranged_sections[5]])}</div>
    </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <meta name="description" content="Daily brief with AI, security, startup news and market data"/>
  <title>Daily Brief — {today}</title>
  <style>{_HTML_STYLE}</style>
</head>
<body>
<main class="wrap" role="main">

  <!-- Header -->
  <header class="hero">
    <h1 class="hero-title">Anusha's Daily Brief</h1>
    <p class="hero-sub">{today} · AI · Security · Startups · Markets</p>
  </header>

  <!-- Market Watch Section -->
  <section>
    {stock_ticker_html}
  </section>

  <!-- News Section -->
  <section class="card">
    {news_html}
  </section>

  <!-- Footer -->
  <footer class="footer" role="contentinfo">
    <p>
      Sources: <a href="https://tldr.tech/ai" target="_blank" rel="noopener">TLDR AI</a> ·
      <a href="https://tldr.tech/infosec" target="_blank" rel="noopener">TLDR Infosec</a> ·
      <a href="https://tldr.tech/startups" target="_blank" rel="noopener">TLDR Startups</a> ·
      <a href="https://tldr.tech/product" target="_blank" rel="noopener">TLDR Product</a> ·
      <a href="https://aidailybrief.beehiiv.com" target="_blank" rel="noopener">AI Daily Brief</a> ·
      <a href="https://npr.org/podcasts/510318/up-first" target="_blank" rel="noopener">NPR Up First</a><br/>
      Stocks via Yahoo Finance · Anusha's Command Center · Daily Brief at 8 AM PST
    </p>
  </footer>

</main>
</body>
</html>"""


# ──────────────────────────────────────────────
#  SEND EMAIL (Resend API)
# ──────────────────────────────────────────────
def send_email(html: str, subject: str, api_key: str) -> None:
    payload = json.dumps({
        "from":    EMAIL_FROM,
        "to":      [EMAIL_TO],
        "subject": subject,
        "html":    html,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type":  "application/json",
            "User-Agent":    "Mozilla/5.0 (compatible; DailyBrief/1.0)",
        },
        method="POST",
    )
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
        result = json.loads(resp.read().decode())
    print(f"✅  Email sent to {EMAIL_TO} (id: {result.get('id', '?')})")


# ──────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────
def main() -> None:
    print(f"\n{'='*55}")
    print(f"  Daily Brief  —  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*55}\n")

    if not EMAIL_TO:
        print("❌  EMAIL_TO is not set. Run:  export EMAIL_TO='you@gmail.com'")
        sys.exit(1)

    # Stocks
    print("📈 Fetching stock data…")
    stocks_rows = []
    for sym, name in STOCKS:
        data = fetch_stock(sym)
        if data:
            print(f"   {sym}: ${data['price']:.2f}  day={data['day']:+.2f}%  month={data['month']:+.2f}%")
        else:
            print(f"   {sym}: unavailable")
        stocks_rows.append({
            "sym": sym, "name": name,
            "price": data["price"]   if data else None,
            "day":   data["day"]     if data else None,
            "month": data["month"]   if data else None,
            "private": False,
        })

    # News
    print("\n📰 Fetching news feeds…")
    news_sections = []
    for section_name, rss_url, limit in NEWS_FEEDS:
        print(f"   {section_name}…", end=" ", flush=True)
        
        # Special handling for sections that need web scraping
        if section_name == "🌍 Up First (NPR)":
            items = fetch_npr_up_first() or []
        elif section_name == "📡 AI Daily Brief":
            items = fetch_ai_daily_brief() or []
        else:
            content = fetch_url(rss_url)
            items = parse_rss(content, limit)
        
        print(f"{len(items)} articles")
        news_sections.append((section_name, items))

    # Build & send
    print("\n✉️  Building email…")
    today   = datetime.now().strftime("%B %d, %Y")
    subject = f"⚡ Your Daily Brief — {today}"
    html    = build_email_html(stocks_rows, news_sections)

    api_key = RESEND_API_KEY
    if not api_key:
        # Save preview to disk instead of sending
        preview_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "daily_brief_preview.html")
        with open(preview_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"\n⚠️  RESEND_API_KEY not set.")
        print(f"   Preview saved to: {preview_path}")
        print("\n   To enable real sending:")
        print("   1. Sign up at https://resend.com and get an API key")
        print("   2. Run:  export RESEND_API_KEY='re_xxxxxxxxxxxx'")
        print("   3. Re-run this script")
        return

    try:
        send_email(html, subject, api_key)
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"❌  Resend API error {e.code}: {body}")
        sys.exit(1)
    except Exception as e:
        print(f"❌  Failed to send: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
