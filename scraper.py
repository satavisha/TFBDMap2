# scraper.py
import os, json, re
from datetime import datetime, date
from pathlib import Path

from dateutil import parser as dateparser
from scrapegraphai.graphs import SmartScraperGraph

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

WEBSITES_FILE = ROOT / "websites_list.txt"
OUT_ALL = DATA_DIR / "events.json"
OUT_UP = DATA_DIR / "events_upcoming.json"
OUT_PAST = DATA_DIR / "events_past.json"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError(
        "Missing OPENAI_API_KEY. Set it in your environment or GitHub Actions secret."
    )

# You can change model later for cost/quality tradeoffs.
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # fallback to "gpt-3.5-turbo" if needed

def normalize_date(s: str) -> str:
    """Return dd/mm/yyyy if parseable, else original string."""
    if not s:
        return ""
    s = s.strip()
    # already looks like dd/mm/yyyy?
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        d, mth, y = m.groups()
        return f"{int(d):02d}/{int(mth):02d}/{y}"
    # try a flexible parse (dayfirst=True handles '08/11/2025' as 8 Nov)
    try:
        dt = dateparser.parse(s, dayfirst=True, fuzzy=True)
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return s  # leave it as-is if we cannot parse

def is_upcoming(start_date_str: str) -> bool:
    """Event is upcoming if start_date >= today. Unparseable -> treat as upcoming."""
    s = normalize_date(start_date_str)
    try:
        dt = datetime.strptime(s, "%d/%m/%Y").date()
        return dt >= date.today()
    except Exception:
        return True

def clean_text(x):
    return (x or "").strip()

def to_event(obj: dict) -> dict:
    # Accept keys the LLM might produce; map to our schema
    name = clean_text(obj.get("name") or obj.get("event_name") or obj.get("title"))
    start = normalize_date(obj.get("start_date") or obj.get("from") or obj.get("start"))
    end = normalize_date(obj.get("end_date") or obj.get("to") or obj.get("end") or "")
    loc = clean_text(obj.get("location") or obj.get("place") or obj.get("city") or "")
    url = clean_text(obj.get("url") or obj.get("link") or obj.get("page") or "")
    return {
        "name": name,
        "start_date": start,
        "end_date": end,
        "location": loc,
        "url": url,
    }

def dedupe(events):
    seen = set()
    unique = []
    for e in events:
        key = (e["name"].lower(), e["start_date"], e["location"].lower(), e["url"].lower())
        if key in seen:
            continue
        seen.add(key)
        unique.append(e)
    return unique

def scrape_url(url: str) -> list[dict]:
    """
    Use SmartScraperGraph to extract events as a structured list.
    The prompt forces a stable JSON shape so our parser is simple.
    """
    prompt = (
        "Extract ALL events on this page as JSON.\n"
        "Return ONLY a JSON object with key 'events' that is an array of objects.\n"
        "Each object MUST have these keys exactly:\n"
        "name, start_date, end_date, location, url.\n"
        "Dates MUST be dd/mm/yyyy. If end date missing, use empty string.\n"
        "Location format: 'State, Country' when possible; else best available.\n"
        "URL must be an absolute link to the event details on this site."
    )

    config = {
        "llm": {
            "provider": "openai",
            "model": MODEL_NAME,
            "api_key": OPENAI_API_KEY,
            "temperature": 0.0,
        },
        # Use Playwright to handle dynamic pages
        "use_playwright": True,
        "verbose": False,
        # You can add headers if any site blocks default UA
        # "headers": {"User-Agent": "Mozilla/5.0 (compatible; TFBDMapBot/1.0)"},
    }

    graph = SmartScraperGraph(
        prompt=prompt,
        source=url,
        config=config,
    )
    result = graph.run()

    # result might be dict with "events", or already a list. Normalize:
    if isinstance(result, dict):
        items = result.get("events") or result.get("data") or []
    elif isinstance(result, list):
        items = result
    else:
        items = []

    return [to_event(x) for x in items if isinstance(x, dict)]

def main():
    urls = [ln.strip() for ln in WEBSITES_FILE.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.strip().startswith("#")]
    all_events = []
    for url in urls:
        try:
            print(f"Scraping: {url}")
            events = scrape_url(url)
            all_events.extend(events)
        except Exception as e:
            print(f"[WARN] Failed {url}: {e}")

    all_events = [e for e in all_events if e.get("name")]  # drop empties
    all_events = [to_event(e) for e in all_events]         # re-normalize
    all_events = dedupe(all_events)

    upcoming = [e for e in all_events if is_upcoming(e["start_date"])]
    past = [e for e in all_events if not is_upcoming(e["start_date"])]

    payload_all = {
        "last_updated": datetime.now().isoformat(timespec="seconds"),
        "upcoming": upcoming,
        "past": past,
    }

    OUT_ALL.write_text(json.dumps(payload_all, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_UP.write_text(json.dumps(upcoming, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_PAST.write_text(json.dumps(past, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"✅ Wrote {OUT_ALL} ({len(upcoming)} upcoming, {len(past)} past)")

if __name__ == "__main__":
    main()
