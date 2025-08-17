# scraper.py
import os, json, re, time
from pathlib import Path
from datetime import datetime, date
from dateutil import parser as dateparser

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

# ---------- Paths ----------
ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

WEBSITES_FILE = ROOT / "websites_list.txt"
OUT_ALL = DATA_DIR / "events.json"
OUT_UP = DATA_DIR / "events_upcoming.json"
OUT_PAST = DATA_DIR / "events_past.json"

# ---------- OpenAI ----------
from openai import OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY environment variable.")
client = OpenAI(api_key=OPENAI_API_KEY)
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # fallback ok; "gpt-3.5-turbo" also fine

# ---------- Helpers ----------
def normalize_date(s: str) -> str:
    """Return dd/mm/yyyy if parseable, else ''. Accepts ranges like 'Aug 8–11, 2025'."""
    if not s:
        return ""
    s = s.strip()
    # If it's a range like "Friday, August 8 ~ Monday, August 11, 2025"
    # grab the first date as start, second as end in post-processing (the LLM will try to split anyway).
    try:
        # Try a direct parse tolerant of dayfirst and text
        dt = dateparser.parse(s, dayfirst=True, fuzzy=True)
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return ""

def is_upcoming(start_date_str: str) -> bool:
    s = start_date_str.strip()
    if not s:
        return True
    try:
        dt = datetime.strptime(s, "%d/%m/%Y").date()
        return dt >= date.today()
    except Exception:
        return True

def dedupe(events):
    seen = set()
    uniq = []
    for e in events:
        key = (e.get("name","").lower(), e.get("start_date",""), e.get("location","").lower(), e.get("url","").lower())
        if key in seen: continue
        seen.add(key); uniq.append(e)
    return uniq

def extract_visible_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    # Remove script/style
    for t in soup(["script", "style", "noscript"]):
        t.decompose()
    text = " ".join(soup.get_text(" ", strip=True).split())
    return text

PROMPT_SYS = (
    "You extract events from web page text and return STRICT JSON.\n"
    "Return ONLY a JSON object with key 'events' (array). Each event MUST have:\n"
    "name (string), start_date (dd/mm/yyyy), end_date (dd/mm/yyyy or empty string),\n"
    "location (format 'State, Country' when possible; else best available),\n"
    "url (absolute URL to the event details on the same site if available; else page URL).\n"
    "If the page shows date ranges (e.g., 'Aug 8–11, 2025'), split into start_date and end_date.\n"
    "If end date missing, use empty string.\n"
)

def ask_llm(page_text: str, page_url: str) -> list[dict]:
    # Keep prompt short to control tokens
    user_msg = f"Source URL: {page_url}\n\nPAGE TEXT:\n{page_text[:12000]}"
    resp = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": PROMPT_SYS},
            {"role": "user", "content": user_msg}
        ],
    )
    content = resp.choices[0].message.content
    try:
        data = json.loads(content)
        events = data.get("events", [])
        # Normalize and ensure required keys exist
        norm = []
        for ev in events:
            name = (ev.get("name") or "").strip()
            start = normalize_date(ev.get("start_date") or "")
            end = normalize_date(ev.get("end_date") or "")
            loc = (ev.get("location") or "").strip()
            url = (ev.get("url") or page_url).strip()
            if name:
                norm.append({
                    "name": name,
                    "start_date": start,
                    "end_date": end,
                    "location": loc,
                    "url": url
                })
        return norm
    except Exception:
        return []

def fetch_html_with_playwright(url: str) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            # Some sites are slow — adjust if needed
            page.goto(url, timeout=60_000)
            page.wait_for_load_state("networkidle", timeout=60_000)
            # Try to click 'Accept cookies' if present (best-effort, no error if not found)
            for sel in ["text=Accept", "text=I agree", "text=OK", "text=Got it"]:
                try:
                    page.locator(sel).first.click(timeout=2000)
                except Exception:
                    pass
            html = page.content()
            return html
        finally:
            browser.close()

def scrape_url(url: str) -> list[dict]:
    print(f"Scraping: {url}")
    html = fetch_html_with_playwright(url)
    text = extract_visible_text(html)
    events = ask_llm(text, url)
    return events

def main():
    urls = [ln.strip() for ln in WEBSITES_FILE.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.strip().startswith("#")]
    all_events = []
    for u in urls:
        try:
            evs = scrape_url(u)
            all_events.extend(evs)
        except Exception as e:
            print(f"[WARN] Failed {u}: {e}")
        time.sleep(1.0)  # be gentle

    all_events = dedupe([e for e in all_events if e.get("name")])
    upcoming = [e for e in all_events if is_upcoming(e.get("start_date",""))]
    past = [e for e in all_events if not is_upcoming(e.get("start_date",""))]

    payload = {
        "last_updated": datetime.now().isoformat(timespec="seconds"),
        "upcoming": upcoming,
        "past": past
    }

    OUT_ALL.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_UP.write_text(json.dumps(upcoming, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_PAST.write_text(json.dumps(past, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ Wrote {OUT_ALL} ({len(upcoming)} upcoming, {len(past)} past)")

if __name__ == "__main__":
    main()
