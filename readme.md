# panini-wc26

Web app for browsing your Panini FIFA World Cup 2026 sticker collection. The UI is static HTML/CSS/JS; a **FastAPI** server serves the assets and builds per-user “owned” data from **published Google Sheets CSV** URLs.

## Requirements

- Python **3.11** (see `.python-version`)
- [Poetry](https://python-poetry.org/docs/#installation)

## Local setup

```bash
poetry install
```

## Run locally

```bash
poetry run uvicorn main:app --reload --host 127.0.0.1 --port 8080
```

Open [http://127.0.0.1:8080/](http://127.0.0.1:8080/) and you are redirected to `/tono/` (default collection). Root assets like `/got.json` still exist if you use a local `got.json` file.

### Per-user pages (Google CSV)

Users are defined in `main.py` as `user_mapping`: each key is a URL path segment, each value is a **CSV export URL** (typically Google Sheets “publish to web” with `output=csv`).

- Collection UI: `http://127.0.0.1:8080/{username}/` (trailing slash matters for asset paths)
- Force refresh of that user’s sheet: `GET http://127.0.0.1:8080/{username}/reload` (redirects back to `/{username}/`)

**CSV format:** a header row with a sticker code column (`sticker_code`, `code`, or `sticker`) and a quantity column (`count`, `quantity`, `qty`, or `owned`). Example:

```csv
sticker_code,quantity
00,1
MEX1,2
```

### Environment variables

| Variable | Default | Meaning |
|----------|---------|---------|
| `PORT` | `8080` | HTTP listen port (Fly sets this automatically). |
| `RELOAD_SECONDS` | `1800` | Background interval (seconds) to re-fetch all users’ CSVs. Set to `0` to disable periodic reload. |

## Deploy on Fly.io

This repo ships a **Dockerfile** that installs dependencies with Poetry and runs **Uvicorn** on `0.0.0.0` using `$PORT` (defaults to `8080`). `fly.toml` expects **`internal_port = 8080`**, which matches the image when Fly does not set `PORT`.

### Prerequisites

- [Fly CLI](https://fly.io/docs/hands-on/install-flyctl/) installed and logged in (`fly auth login`)
- A Fly app name (your `fly.toml` may already set `app = '...'`; change it if that name is taken)

### First-time deploy

From the repository root:

```bash
fly apps create <your-app-name>   # skip if fly.toml already has the right app name
fly deploy
```

If you do not have `fly.toml` yet:

```bash
fly launch
```

Choose **Dockerfile** as the builder when prompted, then adjust `fly.toml` so `[http_service] internal_port` matches the port your process listens on (`8080` with this Dockerfile).

### Set optional secrets / config

Periodic CSV reload uses `RELOAD_SECONDS`. Example (30 minutes):

```bash
fly secrets set RELOAD_SECONDS=1800
```

Or use Fly’s `[env]` in `fly.toml` for non-secret values.

### After deploy

- App URL: `https://<your-app-name>.fly.dev/`
- Per user: `https://<your-app-name>.fly.dev/{username}/`
- Manual refresh: `https://<your-app-name>.fly.dev/{username}/reload`

### Health check

`GET /healthz` returns **204** (no body), suitable for load balancers or uptime checks.

### Updating user spreadsheets

1. Edit `user_mapping` in `main.py` (add users or change CSV URLs).
2. Redeploy: `fly deploy`.

Users can also trigger a reload without redeploying by visiting `/{username}/reload`.

---

## Optional: regenerate `data.json` (scraper)

Sticker metadata in `data.json` can be refreshed using the Playwright-based scraper under `utils/`. That flow is separate from the web server and uses **dev** dependency groups in Poetry.

```bash
poetry install --with dev
poetry run python -m playwright install chromium
```

First run (browser visible, Cloudflare cookies):

```bash
poetry run python utils/main.py --headed --user-data-dir .pw-user-data
```

Then headless with the same profile:

```bash
poetry run python utils/main.py --user-data-dir .pw-user-data
```

Default output is `data.json` in the project root. Commit the updated `data.json` (or your chosen `--out-json` path) before deploying if the album checklist changed.
