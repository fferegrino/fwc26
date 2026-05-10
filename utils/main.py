from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from io import StringIO
from typing import Any

import pandas as pd
from playwright.sync_api import sync_playwright


DEFAULT_URL = "https://www.laststicker.com/cards/panini_world_cup_2026/"
DEFAULT_USER_DATA_DIR = ".pw-user-data"


@dataclass(frozen=True)
class ScrapeResult:
    url: str
    rows: list[dict[str, Any]]


def _pick_browser(p, browser: str):
    browser = browser.lower().strip()
    if browser == "chromium":
        return p.chromium
    if browser == "firefox":
        return p.firefox
    if browser == "webkit":
        return p.webkit
    raise ValueError(f"Unsupported browser: {browser!r}. Use chromium|firefox|webkit.")


def scrape_checklist_table(
    url: str,
    *,
    headless: bool = True,
    timeout_ms: int = 60_000,
    browser: str = "chromium",
    user_data_dir: str = DEFAULT_USER_DATA_DIR,
) -> ScrapeResult:
    with sync_playwright() as p:
        browser_type = _pick_browser(p, browser)
        context = browser_type.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=headless,
            locale="en-US",
            timezone_id="UTC",
            viewport={"width": 1400, "height": 900},
        )
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)

        title = (page.title() or "").strip().lower()
        if "just a moment" in title:
            context.close()
            raise RuntimeError(
                "Blocked by Cloudflare ('Just a moment...'). "
                "Re-run once with --headed to complete the challenge, then re-run headless.\n\n"
                "Example:\n"
                "  uv run python main.py --headed --user-data-dir .pw-user-data\n"
                "\nIf that still loops, try:\n"
                "  uv run python main.py --headed --browser firefox --user-data-dir .pw-user-data\n"
            )

        table = page.locator("table#checklist")
        table.wait_for(state="attached", timeout=timeout_ms)
        table_html = table.evaluate("el => el.outerHTML")

        context.close()

    dfs = pd.read_html(StringIO(table_html))
    if not dfs:
        raise RuntimeError("Could not parse any tables from table#checklist HTML.")

    df = dfs[0]

    # Normalize columns: some tables parse as MultiIndex.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [
            " ".join([str(v).strip() for v in tup if v is not None and str(v).strip() and str(v) != "nan"]).strip()
            for tup in df.columns.to_list()
        ]
    else:
        df.columns = [str(c) for c in df.columns]

    df = df.loc[:, ~pd.Index(df.columns).str.match(r"^Unnamed:")]
    df = df.dropna(how="all")

    if df.shape[1] < 2:
        raise RuntimeError(f"Expected at least 2 columns in checklist table, got {df.shape[1]}.")

    df = df.iloc[:, :3].copy()
    df.columns = ["sticker_code", "name", "country"]

    # Normalize empties and whitespace.
    df["sticker_code"] = df["sticker_code"].astype(str).str.strip()
    df["name"] = df["name"].astype(str).str.strip()
    df["country"] = df["country"].astype(str).str.strip()
    df = df.replace({"": None, "nan": None, "None": None})

    rows = df.to_dict(orient="records")
    return ScrapeResult(url=url, rows=rows)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Scrape laststicker.com checklist table")
    p.add_argument("--url", default=DEFAULT_URL, help="Page URL to scrape")
    p.add_argument("--out-json", default="data.json", help="Output JSON path")
    p.add_argument("--out-csv", default="", help="Optional output CSV path")
    p.add_argument("--headed", action="store_true", help="Run browser headed (not headless)")
    p.add_argument("--browser", default="chromium", help="Browser engine: chromium|firefox|webkit")
    p.add_argument("--user-data-dir", default=DEFAULT_USER_DATA_DIR, help="Persistent profile directory")
    p.add_argument("--timeout-ms", type=int, default=60_000, help="Navigation/selector timeout in ms")
    return p


def main() -> None:
    args = build_parser().parse_args()

    result = scrape_checklist_table(
        args.url,
        headless=not args.headed,
        timeout_ms=args.timeout_ms,
        browser=args.browser,
        user_data_dir=args.user_data_dir,
    )

    out_json = Path(args.out_json)
    write_json(out_json, {"url": result.url, "rows": result.rows})

    if args.out_csv:
        write_csv(Path(args.out_csv), result.rows)

    print(f"Wrote {len(result.rows)} rows to {out_json}")


if __name__ == "__main__":
    main()
