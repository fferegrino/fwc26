from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.responses import FileResponse, HTMLResponse, Response


BASE_DIR = Path(__file__).resolve().parent

INDEX_FILE = BASE_DIR / "index.html"
DATA_FILE = BASE_DIR / "data.json"
GOT_FILE = BASE_DIR / "got.json"
APP_JS_FILE = BASE_DIR / "app.js"
STYLES_FILE = BASE_DIR / "styles.css"


app = FastAPI(title="Panini FWC26 Stickers")


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


def _port() -> int:
    # Fly often provides PORT; we keep a sane default for local use.
    return int(os.environ.get("PORT", "8080"))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=_port())

