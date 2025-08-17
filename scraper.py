name: Daily Scrape

on:
  schedule:
    - cron: "30 3 * * *"   # 9:00 AM IST daily (IST = UTC+5:30)
  workflow_dispatch:
  push:
    branches: [ main ]
    paths:
      - ".github/workflows/scrape.yml"
      - "scraper.py"
      - "requirements.txt"
      - "data/**"
      - "websites_list.*"

permissions:
  contents: write

jobs:
  run-scraper:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    concurrency:
      group: tfbdmap-scrape
      cancel-in-progress: true

    env:
      PYTHONUNBUFFERED: "1"
      OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}

    steps:
      - name: Check out repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
          persist-credentials: true

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.10"
          cache: "pip"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Install Playwright (browser + Linux deps)
        run: |
          python -m pip install playwright
          python -m playwright install --with-deps chromium

      - name: Run scraper
        run: |
          python scraper.py

      - name: Show changes
        run: |
          echo "Changed files:"
          git status --porcelain || true

      - name: Commit and push updated data
        run: |
          set -e
          BRANCH="${{ github.ref_name }}"
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add data/*.json || true
          if git diff --cached --quiet; then
            echo "No data changes to commit."
            exit 0
          fi
          DATE_UTC=$(date -u +'%Y-%m-%d')
          git commit -m "chore: update scraped data ($DATE_UTC)"
          git pull --rebase origin "$BRANCH" || true
          git push origin "$BRANCH"
