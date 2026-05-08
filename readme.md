## panini-wc26

Scrape `table#checklist` from `laststicker.com` and export it to JSON (and optionally CSV).

### Setup (UV)

Install Python deps:

```bash
uv sync
```

Install the Playwright browser (Chromium):

```bash
uv run python -m playwright install chromium
```

### Run

First run (recommended): open a real browser window once so Cloudflare can set the required cookies, then you can run headless using the same `--user-data-dir`.

```bash
uv run python main.py --headed --user-data-dir .pw-user-data
```

Then run headless using the same profile dir:

```bash
uv run python main.py --user-data-dir .pw-user-data
```

Write to `data.json` (default):

```bash
uv run python main.py
```

Write JSON + CSV:

```bash
uv run python main.py --out-json data.json --out-csv checklist.csv
```

If you want to see the browser:

```bash
uv run python main.py --headed
```
