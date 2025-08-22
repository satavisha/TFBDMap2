#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, re, json, argparse
from pathlib import Path
from datetime import datetime, timezone
from dateutil import parser as dateparser

# --- Firecrawl setup ---------------------------------------------------------
# Requires: pip install firecrawl-python
# Add FIRECRAWL_API_KEY as a GitHub secret for the workflow and as an env var locally.
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
if not FIRECRAWL_API_KEY:
    # Allow running read-only for unit tests with a warning
    print("⚠️  FIRECRAWL_API_KEY not set. If scraping fails, set this env var.")
try:
    from firecrawl import FirecrawlApp
    app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)  # type: ignore
except Exception as e:
    print(f"⚠️  Firecrawl import/init warning: {e}")
    app = None  # We'll still try to run, but scraping will fail without app


# --- Config / paths ----------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent
WEBSITE_LIST_FILE = REPO_ROOT / "websites_list.txt"

OUT_DATA = REPO_ROOT / "data"
OUT_DOCS = REPO_ROOT / "docs" / "data"
OUT_PUBLIC = REPO_ROOT / "public" / "data"

OUT_DATA.mkdir(parents=True, exist_ok=True)
OUT_DOCS.mkdir(parents=True, exist_ok=True)
OUT_PUBLIC.mkdir(parents=True, exist_ok=True)

# Primary outputs
DATA_UPCOMING = OUT_DATA / "events.json"           # { "upcoming": [...] }
DATA_PAST     = OUT_DATA / "events_past.json"      # { "past": [...] }

# Mirrors for the two frontends
DOCS_UPCOMING = OUT_DOCS / "events.json"           # { "upcoming": [...] }  (docs site fetches this)
DOCS_PAST     = OUT_DOCS / "events_past.json"      # { "past": [...] }

PUBLIC_UPCOMING_LIST = OUT_PUBLIC / "events_upcoming.json"  # [...] (Next.js fetches this)
PUBLIC_UPCOMING_OBJ  = OUT_PUBLIC / "events.json"            # { "upcoming": [...] }
PUBLIC_PAST_OBJ      = OUT_PUBLIC / "events_past.json"       # { "past": [...] }

# --- Your proven parsing logic (from notebook), tidy-wrapped -----------------
MONTHS = r"(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t|tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
RANGE_SEP = re.compile(r"\s*(?:to|through|until|[-–—~])\s*", re.IGNORECASE)
VENUE_WORDS = re.compile(r"\b(Center|Hall|Auditorium|Masonic|Theatre|Theater|Convention|Expo|Arena|Ballroom|Community|University|Hotel)\b", re.I)

def clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip() if s else ""

def lines_list(markdown: str):
    return [clean(x) for x in markdown.splitlines() if clean(x)]

def parse_date(txt: str):
    if not txt: 
        return None
    for dayfirst in (False, True):
        try:
            return dateparser.parse(txt, dayfirst=dayfirst, fuzzy=True)
        except Exception:
            pass
    return None

def ddmmyyyy(dt): 
    return dt.strftime("%d/%m/%Y") if dt else ""

def find_title(lines):
    for ln in lines:
        if ln.startswith("# "): 
            return clean(ln.lstrip("# ").strip())
    for ln in lines:
        if re.search(r"(Tamarind Union|festival|conference|summit|workshop|expo|event)", ln, re.I):
            return ln
    return "Event"

def find_date_line(lines):
    cands = []
    for i, ln in enumerate(lines):
        if re.search(MONTHS + r"\s+\d{1,2}.*\b\d{4}\b", ln, re.I) and not re.search(r"\b(am|pm)\b", ln, re.I):
            cands.append((i, ln))
    for i, ln in cands:
        if RANGE_SEP.search(ln):
            return i, ln
    return cands[0] if cands else (None, "")

def split_dates(date_line: str):
    if not date_line: 
        return None, None
    if RANGE_SEP.search(date_line):
        a, b = RANGE_SEP.split(date_line, maxsplit=1)
        return parse_date(a), parse_date(b)
    d = parse_date(date_line)
    return d, d

def find_location(lines, date_idx):
    if date_idx is None:
        window = lines[:30]
    else:
        start = max(0, date_idx - 8); end = min(len(lines), date_idx + 8)
        window = lines[start:end]

    venue = address = city_state = ""
    for ln in window:
        if not venue and VENUE_WORDS.search(ln): 
            venue = ln
        if not address and re.search(r"\b\d{3,6}\s+\w+", ln): 
            address = ln      # e.g., 4550 N Pilgrim Rd
        if not city_state and re.search(r",[ ]*[A-Z]{2}(\b|$)", ln): 
            city_state = ln  # ", WI"

    if not city_state:
        for ln in window:
            if re.search(r"\bBrookfield\b", ln, re.I):
                city_state = ln; break

    parts = [p for p in [venue, city_state, address] if p]
    # Unique, order-preserving
    seen, out = set(), []
    for p in parts:
        if p not in seen:
            seen.add(p); out.append(p)
    return ", ".join(out)

def extract_event_from_markdown(md: str, page_url: str):
    if not md:
        return {"name": "Event", "start_date": "", "end_date": "", "location": "", "link": page_url}

    ls = lines_list(md)
    name = find_title(ls)
    date_idx, date_ln = find_date_line(ls)
    d_start, d_end = split_dates(date_ln)
    start_str = ddmmyyyy(d_start) if d_start else ""
    end_str = ddmmyyyy(d_end) if d_end else start_str
    location = find_location(ls, date_idx)

    return {
        "name": name,
        "start_date": start_str,
        "end_date": end_str,
        "location": location,
        "link": page_url
    }

# --- Scrape helpers ----------------------------------------------------------
def firecrawl_markdown_and_html(url: str):
    """Fetch both markdown and html via Firecrawl."""
    if app is None:
        raise RuntimeError("Firecrawl app not initialized (missing FIRECRAWL_API_KEY or import failed).")
    doc = app.scrape(
        url,
        formats=["markdown","html"],
        only_main_content=False,
        timeout=120000
    )
    # Try multiple attribute styles (SDK differences)
    md = getattr(doc, "markdown", None)
    html = getattr(doc, "html", None)
    if hasattr(doc, "model_dump"):
        res = doc.model_dump()
    elif hasattr(doc, "dict"):
        res = doc.dict()
    else:
        res = getattr(doc, "__dict__", {}) or {}

    if not md and isinstance(res, dict):
        md = res.get("markdown")
    if not html and isinstance(res, dict):
        html = res.get("html")
    return md or "", html or ""

def scrape_one_url(url: str) -> dict:
    """Return a single normalized event dict for a page."""
    md, _html = firecrawl_markdown_and_html(url)
    evt = extract_event_from_markdown(md, url)
    # Normalize key naming for both frontends (they accept link or url)
    if "url" not in evt:
        evt["url"] = evt.get("link", url)
    return evt

def parse_ddmmyyyy(s: str):
    try:
        return datetime.strptime(s, "%d/%m/%Y").date()
    except Exception:
        return None

def partition_events(events: list):
    """Split into upcoming vs past using start_date (inclusive today as upcoming)."""
    today = datetime.now(timezone.utc).astimezone().date()  # local date on runner
    upcoming, past = [], []
    for e in events:
        d = parse_ddmmyyyy(e.get("start_date",""))
        if d is None:
            # If no date, default to upcoming to surface it (adjust if you prefer)
            upcoming.append(e)
        elif d >= today:
            upcoming.append(e)
        else:
            past.append(e)
    return upcoming, past

def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)

# --- CLI ---------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Scrape TFBD event pages using Firecrawl and emit JSON.")
    ap.add_argument("--test_url", help="Scrape a single URL and print the parsed event JSON.")
    ap.add_argument("--dry_run", action="store_true", help="Run without writing output files.")
    args = ap.parse_args()

    if args.test_url:
        print(f"Scraping (test): {args.test_url}")
        evt = scrape_one_url(args.test_url)
        print(json.dumps(evt, indent=2, ensure_ascii=False))
        return

    # Read URL list
    urls = []
    if WEBSITE_LIST_FILE.exists():
        with WEBSITE_LIST_FILE.open("r", encoding="utf-8") as f:
            urls = [ln.strip() for ln in f if ln.strip() and not ln.strip().startswith("#")]
    else:
        print(f"⚠️  {WEBSITE_LIST_FILE} not found. Nothing to scrape.")
        urls = []

    all_events = []
    for u in urls:
        try:
            print(f"🔎 Scraping: {u}")
            ev = scrape_one_url(u)
            all_events.append(ev)
            print(f"   → {ev.get('name','(no name)')} | {ev.get('start_date','')} – {ev.get('end_date','')}")
        except Exception as e:
            print(f"❌ Failed {u}: {e}")

    upcoming, past = partition_events(all_events)

    print(f"\nSummary: {len(upcoming)} upcoming, {len(past)} past, total {len(all_events)}")

    if args.dry_run:
        print("🧪 --dry_run specified. Skipping writes.")
        return

    # Primary writes (CI commits these)
    write_json(DATA_UPCOMING, {"upcoming": upcoming})
    write_json(DATA_PAST, {"past": past})

    # Mirrors for your two frontends
    write_json(DOCS_UPCOMING, {"upcoming": upcoming})
    write_json(DOCS_PAST, {"past": past})

    write_json(PUBLIC_UPCOMING_LIST, upcoming)          # array form
    write_json(PUBLIC_UPCOMING_OBJ, {"upcoming": upcoming})
    write_json(PUBLIC_PAST_OBJ, {"past": past})

    print(f"✅ Wrote:")
    print(f"   {DATA_UPCOMING}")
    print(f"   {DATA_PAST}")
    print(f"   {DOCS_UPCOMING}")
    print(f"   {DOCS_PAST}")
    print(f"   {PUBLIC_UPCOMING_LIST}")
    print(f"   {PUBLIC_UPCOMING_OBJ}")
    print(f"   {PUBLIC_PAST_OBJ}")

if __name__ == "__main__":
    main()
