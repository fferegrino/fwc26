from __future__ import annotations

import csv
import os
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response


BASE_DIR = Path(__file__).resolve().parent

INDEX_FILE = BASE_DIR / "index.html"
DATA_FILE = BASE_DIR / "data.json"
GOT_FILE = BASE_DIR / "got.json"
APP_JS_FILE = BASE_DIR / "app.js"
STYLES_FILE = BASE_DIR / "styles.css"

user_mapping: dict[str, str] = {
    "tono": "https://docs.google.com/spreadsheets/d/e/2PACX-1vRUU-E9IN010M0NgUAsjNNmGYjEilp-PJHYJf7MQ9rH1--tU6TNBwYP9M_IRtnV2mwnZ8DEJZV79PLG/pub?gid=2042950172&single=true&output=csv",
    "max": "https://docs.google.com/spreadsheets/d/e/2PACX-1vTccdq22tEOEGci1m2gWYPlCML6qoZEIHsxlaiikB0Jl7BKthiCKLmiRobdh1UHP1YbXrRdhreWSeU1/pub?gid=2042950172&single=true&output=csv",
    "example": "https://docs.google.com/spreadsheets/d/e/2PACX-1vShi7E2m1Ph3nIMLQiLdqnyL7KcF3SoP5RcqJ-7OFM_aEHhIssnnmBusCfsF9h5u0lfQuvGAxM8IMVI/pub?gid=2042950172&single=true&output=csv"
}

app = FastAPI(title="Panini FWC26 Stickers")

_got_by_user: dict[str, dict[str, list[list[int]]]] = {}
_got_lock = threading.RLock()
_reload_thread_started = False


def _reload_seconds() -> int:
    try:
        return int(os.environ.get("RELOAD_SECONDS", "1800"))
    except ValueError:
        return 300


def _download_text(url: str) -> str:
    with urllib.request.urlopen(url, timeout=30) as resp:  # nosec - URL comes from server config
        data = resp.read()
    return data.decode("utf-8", errors="replace")


def _got_shape_from_csv_text(csv_text: str) -> dict[str, list[list[int]]]:
    """
    Input CSV rows:
      sticker_code,count
      MEX1,1
      MEX2,0
      00,1

    Output JSON shape (same as previous got.json):
      { "MEX": [[1, 1], [2, 0]], "00": [[0, 1]] }
    """
    out: dict[str, list[list[int]]] = {}
    # Handle common Google/Excel exports with BOM and header variants.
    text = csv_text.lstrip("\ufeff")
    reader = csv.DictReader(text.splitlines())
    if not reader.fieldnames:
        return out

    # Normalize headers so we can tolerate "quantity" instead of "count", etc.
    normalized_headers = {h: (h or "").strip().lower() for h in reader.fieldnames}
    code_header = next(
        (h for h, nh in normalized_headers.items() if nh in {"sticker_code", "code", "sticker"}),
        None,
    )
    count_header = next(
        (h for h, nh in normalized_headers.items() if nh in {"count", "quantity", "qty", "owned"}),
        None,
    )

    for row in reader:
        code = (row.get(code_header or "sticker_code") or "").strip()
        if not code:
            continue
        raw_count = (row.get(count_header or "count") or "").strip()
        try:
            count = int(float(raw_count)) if raw_count else 0
        except ValueError:
            count = 0

        if code == "00":
            prefix = "00"
            num = 0
        else:
            # split prefix letters vs number suffix
            i = 0
            while i < len(code) and code[i].isalpha():
                i += 1
            prefix = code[:i] or code
            try:
                num = int(code[i:]) if i < len(code) else 0
            except ValueError:
                num = 0

        out.setdefault(prefix, []).append([num, count])

    # stable ordering is nice for diffs/debugging
    for prefix in list(out.keys()):
        out[prefix].sort(key=lambda pair: pair[0])
    return out


def _reload_user(username: str) -> dict[str, list[list[int]]]:
    url = user_mapping[username]
    csv_text = _download_text(url)
    return _got_shape_from_csv_text(csv_text)


def _reload_all_users_once() -> None:
    loaded: dict[str, dict[str, list[list[int]]]] = {}
    for username in user_mapping.keys():
        try:
            loaded[username] = _reload_user(username)
        except Exception:
            loaded[username] = {}
    with _got_lock:
        _got_by_user.clear()
        _got_by_user.update(loaded)


def _reload_loop() -> None:
    interval = _reload_seconds()
    if interval <= 0:
        return
    while True:
        time.sleep(interval)
        try:
            _reload_all_users_once()
        except Exception:
            # If a reload fails, keep the old cache and try again later.
            pass


@app.on_event("startup")
def _load_user_got_data() -> None:
    global _reload_thread_started
    _reload_all_users_once()

    if not _reload_thread_started and _reload_seconds() > 0:
        t = threading.Thread(target=_reload_loop, name="got-reload-loop", daemon=True)
        t.start()
        _reload_thread_started = True


@app.get("/healthz", include_in_schema=False)
def healthz() -> Response:
    return Response(status_code=204)


@app.get("/", include_in_schema=False)
def index() -> HTMLResponse:
    return HTMLResponse(INDEX_FILE.read_text(encoding="utf-8"))


@app.get("/app.js", include_in_schema=False)
def app_js() -> FileResponse:
    return FileResponse(APP_JS_FILE, media_type="text/javascript; charset=utf-8")


@app.get("/styles.css", include_in_schema=False)
def styles_css() -> FileResponse:
    return FileResponse(STYLES_FILE, media_type="text/css; charset=utf-8")


@app.get("/data.json", include_in_schema=False)
def data_json() -> FileResponse:
    if not DATA_FILE.exists():
        raise HTTPException(status_code=404, detail="data.json not found")
    return FileResponse(DATA_FILE, media_type="application/json; charset=utf-8")


@app.get("/got.json", include_in_schema=False)
def got_json() -> FileResponse:
    if not GOT_FILE.exists():
        raise HTTPException(status_code=404, detail="got.json not found")
    return FileResponse(GOT_FILE, media_type="application/json; charset=utf-8")


@app.get("/{username}", include_in_schema=False)
def user_root(username: str) -> RedirectResponse:
    # Ensure trailing slash so the frontend's relative fetch("./got.json") resolves to /{username}/got.json
    return RedirectResponse(url=f"/{username}/", status_code=307)


@app.get("/{username}/", include_in_schema=False)
def user_index(username: str) -> HTMLResponse:
    if username not in user_mapping:
        raise HTTPException(status_code=404, detail="Unknown user")
    return HTMLResponse(INDEX_FILE.read_text(encoding="utf-8"))


@app.get("/{username}/got.json", include_in_schema=False)
def user_got_json(username: str) -> JSONResponse:
    if username not in user_mapping:
        raise HTTPException(status_code=404, detail="Unknown user")
    with _got_lock:
        payload: dict[str, Any] = _got_by_user.get(username, {})
    return JSONResponse(payload)


@app.get("/{username}/reload", include_in_schema=False)
def user_reload(username: str) -> RedirectResponse:
    if username not in user_mapping:
        raise HTTPException(status_code=404, detail="Unknown user")
    try:
        fresh = _reload_user(username)
        with _got_lock:
            _got_by_user[username] = fresh
    except Exception:
        # Keep existing cache if reload fails.
        pass
    return RedirectResponse(url=f"/{username}/", status_code=303)


@app.get("/{username}/data.json", include_in_schema=False)
def user_data_json(username: str) -> FileResponse:
    if username not in user_mapping:
        raise HTTPException(status_code=404, detail="Unknown user")
    if not DATA_FILE.exists():
        raise HTTPException(status_code=404, detail="data.json not found")
    return FileResponse(DATA_FILE, media_type="application/json; charset=utf-8")


@app.get("/{username}/app.js", include_in_schema=False)
def user_app_js(username: str) -> FileResponse:
    if username not in user_mapping:
        raise HTTPException(status_code=404, detail="Unknown user")
    return FileResponse(APP_JS_FILE, media_type="text/javascript; charset=utf-8")


@app.get("/{username}/styles.css", include_in_schema=False)
def user_styles_css(username: str) -> FileResponse:
    if username not in user_mapping:
        raise HTTPException(status_code=404, detail="Unknown user")
    return FileResponse(STYLES_FILE, media_type="text/css; charset=utf-8")


def _port() -> int:
    # Fly often provides PORT; we keep a sane default for local use.
    return int(os.environ.get("PORT", "8080"))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=_port())

