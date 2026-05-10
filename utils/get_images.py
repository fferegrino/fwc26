"""
Download LastSticker card images for Panini WC 2026, normalize to 225x300 JPEG.

Source pattern:
  https://www.laststicker.com/i/cards/<album_id>/<sticker_code_lower>.jpg

Output layout:
  images/<country_slug>/<sticker_code>.jpg
"""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.request
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

DEFAULT_DATA = Path(__file__).resolve().parent / "data.json"
DEFAULT_ALBUM_ID = 12176
TARGET_SIZE = (225, 300)
USER_AGENT = (
    "Mozilla/5.0 (compatible; panini-wc26-get-images/1.0; +https://github.com/)"
)

sticker_code_re = re.compile(r"^(00|[A-Z]{3})\d{0,2}$")


def country_slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return s or "unknown"


def sticker_url(album_id: int, sticker_code: str) -> str:
    return f"https://www.laststicker.com/i/cards/{album_id}/{sticker_code.lower()}.jpg"


def download(url: str, timeout: int) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def ensure_rgb(img: Image.Image) -> Image.Image:
    if img.mode in ("RGBA", "LA"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        alpha = img.split()[-1]
        bg.paste(img.convert("RGBA"), mask=alpha)
        return bg
    if img.mode == "P" and "transparency" in img.info:
        return ensure_rgb(img.convert("RGBA"))
    if img.mode != "RGB":
        return img.convert("RGB")
    return img


def normalize_sticker_image(data: bytes) -> Image.Image:
    with Image.open(BytesIO(data)) as img:
        img = ImageOps.exif_transpose(img)
        img = ensure_rgb(img)
        w, h = img.size
        if w > h:
            img = img.transpose(Image.Transpose.ROTATE_90)
        img = img.resize(TARGET_SIZE, Image.Resampling.LANCZOS)
        return img


def load_rows(data_path: Path) -> list[dict[str, Any]]:
    raw = json.loads(data_path.read_text(encoding="utf-8"))
    rows = raw.get("rows")
    if not isinstance(rows, list):
        raise ValueError(f"{data_path}: expected top-level 'rows' list")
    return rows


def main() -> None:
    p = argparse.ArgumentParser(description="Fetch and normalize LastSticker images.")
    p.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_DATA,
        help=f"Path to data.json (default: {DEFAULT_DATA})",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=Path("images"),
        help="Output root directory (default: ./images)",
    )
    p.add_argument(
        "--album-id",
        type=int,
        default=DEFAULT_ALBUM_ID,
        help=f"LastSticker album id (default: {DEFAULT_ALBUM_ID})",
    )
    p.add_argument("--timeout", type=int, default=30, help="HTTP timeout seconds")
    p.add_argument(
        "--delay",
        type=float,
        default=0.15,
        help="Seconds between requests (default: 0.15)",
    )
    p.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip download if output file already exists",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process at most N stickers (0 = all)",
    )
    args = p.parse_args()

    rows = load_rows(args.data)
    done = 0
    errors: list[str] = []

    for row in rows:
        if args.limit and done >= args.limit:
            break
        code = row.get("sticker_code")
        country = row.get("country")
        if not code or not country:
            continue


        match = sticker_code_re.match(code)
        if not match:
            continue
        prefix = match.group(1)

        # sub = country_slug(str(country))
        out_dir = args.out / prefix
        out_path = out_dir / f"{code}.jpg"

        if args.skip_existing and out_path.exists():
            done += 1
            continue

        url = sticker_url(args.album_id, str(code))
        try:
            raw_bytes = download(url, args.timeout)
            img = normalize_sticker_image(raw_bytes)
            out_dir.mkdir(parents=True, exist_ok=True)
            img.save(out_path, format="JPEG", quality=92, optimize=True)
            print(f"OK {out_path}")
        except urllib.error.HTTPError as e:
            errors.append(f"{code} {url} -> HTTP {e.code}")
            print(f"ERR {code} HTTP {e.code}")
        except Exception as e:  # noqa: BLE001 — report and continue
            errors.append(f"{code} {url} -> {e!r}")
            print(f"ERR {code} {e!r}")

        done += 1
        if args.delay > 0:
            time.sleep(args.delay)

    if errors:
        print(f"\n{len(errors)} error(s). First few:")
        for line in errors[:10]:
            print(" ", line)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
