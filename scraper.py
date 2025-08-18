import os
import json
from datetime import datetime
from dateutil import parser as dateparser
from scrapegraphai.graphs import SmartScraperGraph

# Read OpenAI API key from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# File containing the list of websites to scrape
WEBSITE_LIST_FILE = "websites_list.txt"

# Output JSON files
UPCOMING_FILE = "data/events.json"
PAST_FILE = "data/events_past.json"

# Prompt for ScrapeGraphAI
SCRAPE_PROMPT = """
List all events on this page with the following fields:
- name (Event name)
- start_date (in dd/mm/yyyy format)
- end_date (in dd/mm/yyyy format, if available)
- location (City, State, Country if possible)
- link (URL to the event)
"""

def normalize_date(date_str):
    """Try to parse any date string and return dd/mm/yyyy format."""
    if not date_str or date_str.strip() == "":
        return ""
    try:
        dt = dateparser.parse(date_str, dayfirst=True)
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return date_str  # fallback: keep as-is if unparseable

def scrape_site(url):
    """Scrape events from a single website using ScrapeGraphAI."""
    graph_config = {
        "llm": {
            "api_key": OPENAI_API_KEY,
            "model": "gpt-3.5-turbo"
        }
    }

    smart_scraper = SmartScraperGraph(
        prompt=SCRAPE_PROMPT,
        source=url,
        config=graph_config
    )

    try:
        result = smart_scraper.run()
        events = result.get("events", result)  # handle variations
        cleaned = []
        for ev in events:
            start = normalize_date(ev.get("start_date", ""))
            end = normalize_date(ev.get("end_date", ""))
            cleaned.append({
                "name": ev.get("name", "").strip(),
                "start_date": start,
                "end_date": end,
                "location": ev.get("location", "").strip(),
                "link": ev.get("link", url)  # fallback to page url
            })
        return cleaned
    except Exception as e:
        print(f"[WARN] Failed {url}: {e}")
        return []

def main():
    today = datetime.today().date()
    upcoming = []
    past = []

    # Load websites from file
    with open(WEBSITE_LIST_FILE, "r") as f:
        websites = [line.strip() for line in f if line.strip()]

    for site in websites:
        print(f"Scraping: {site}")
        events = scrape_site(site)
        for ev in events:
            try:
                if ev["start_date"]:
                    start_dt = datetime.strptime(ev["start_date"], "%d/%m/%Y").date()
                    if start_dt >= today:
                        upcoming.append(ev)
                    else:
                        past.append(ev)
                else:
                    upcoming.append(ev)
            except Exception:
                upcoming.append(ev)

    # Ensure data folder exists
    os.makedirs("data", exist_ok=True)

    # Write results
    with open(UPCOMING_FILE, "w", encoding="utf-8") as f:
        json.dump({"upcoming": upcoming}, f, indent=2, ensure_ascii=False)

    with open(PAST_FILE, "w", encoding="utf-8") as f:
        json.dump({"past": past}, f, indent=2, ensure_ascii=False)

    print(f"✅ Wrote {UPCOMING_FILE} ({len(upcoming)} upcoming)")
    print(f"✅ Wrote {PAST_FILE} ({len(past)} past)")

if __name__ == "__main__":
    main()
