"""
Merge per-collection sticker folders into one horizontal strip (default 20 × 225 px slots, 300 px tall).

Expects layout like images/NED/NED1.jpg … images/NED/NED20.jpg and images/00/00.jpg.
By default writes PNG strips with fully transparent empty slots.
Use --format webp for much smaller files (still supports transparent empty slots).
Use --format jpeg for solid --bg fills.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageOps

SLOT_DEFAULT = 225
HEIGHT_DEFAULT = 300
COUNT_DEFAULT = 20


def parse_sticker_index(folder_name: str, stem: str) -> int | None:
    """Return 1-based sticker index for a filename stem, or None if it does not match."""
    if folder_name == "00" and stem == "00":
        return 1
    if not stem.startswith(folder_name):
        return None
    suffix = stem[len(folder_name) :]
    if suffix.isdigit():
        return int(suffix)
    return None


def load_cell_image(path: Path, cell_w: int, cell_h: int) -> Image.Image:
    """Resize a cell to slot size, always RGBA (JPEGs get opaque alpha)."""
    with Image.open(path) as img:
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGBA")
        return img.resize((cell_w, cell_h), Image.Resampling.LANCZOS)


def merge_folder(
    folder: Path,
    *,
    slot_w: int,
    height: int,
    slot_count: int,
    bg: tuple[int, int, int],
    transparent_empty: bool,
) -> Image.Image:
    if transparent_empty:
        canvas = Image.new("RGBA", (slot_w * slot_count, height), (0, 0, 0, 0))
    else:
        canvas = Image.new("RGB", (slot_w * slot_count, height), bg)
    mapping: dict[int, Path] = {}
    for p in folder.iterdir():
        if not p.is_file() or p.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
            continue
        idx = parse_sticker_index(folder.name, p.stem)
        if idx is None:
            continue
        mapping[idx] = p

    for i in range(1, slot_count + 1):
        path = mapping.get(i)
        if path is None:
            continue
        x = (i - 1) * slot_w
        cell = load_cell_image(path, slot_w, height)
        if transparent_empty:
            canvas.alpha_composite(cell, dest=(x, 0))
        else:
            rgb = Image.new("RGB", cell.size, bg)
            rgb.paste(cell, mask=cell.split()[-1])
            canvas.paste(rgb, (x, 0))

    return canvas


def main() -> None:
    ap = argparse.ArgumentParser(description="Merge collection folders into horizontal strips.")
    ap.add_argument(
        "--images",
        type=Path,
        default=Path("images"),
        help="Root folder containing one subfolder per collection (default: ./images)",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("images"),
        help="Output directory for merged strips (default: ./images)",
    )
    ap.add_argument(
        "--format",
        choices=("png", "webp", "jpeg"),
        default="webp",
        help="Output format (default: webp). webp: small + transparent empties; jpeg: opaque --bg empties",
    )
    ap.add_argument(
        "--quality",
        type=int,
        default=None,
        metavar="1-100",
        help="JPEG/WebP quality (default: 92 for jpeg, 80 for webp; ignored for png)",
    )
    ap.add_argument(
        "--webp-method",
        type=int,
        default=6,
        choices=range(0, 7),
        help="WebP encoder effort 0=fast/larger … 6=slow/smaller (default: 6)",
    )
    ap.add_argument(
        "--slots",
        type=int,
        default=COUNT_DEFAULT,
        help=f"Number of horizontal slots (default: {COUNT_DEFAULT})",
    )
    ap.add_argument(
        "--slot-width",
        type=int,
        default=SLOT_DEFAULT,
        help=f"Width of each slot in pixels (default: {SLOT_DEFAULT}; total width = slots × this)",
    )
    ap.add_argument(
        "--height",
        type=int,
        default=HEIGHT_DEFAULT,
        help=f"Strip height in pixels (default: {HEIGHT_DEFAULT})",
    )
    ap.add_argument(
        "--bg",
        type=str,
        default="255,255,255",
        help="Background RGB for empty slots when using --format jpeg (comma-separated)",
    )
    args = ap.parse_args()

    if args.quality is not None and not (1 <= args.quality <= 100):
        raise SystemExit("--quality must be between 1 and 100")
    if args.format == "jpeg":
        q = 92 if args.quality is None else args.quality
    elif args.format == "webp":
        q = 80 if args.quality is None else args.quality
    else:
        q = None

    bg_parts = [int(x.strip()) for x in args.bg.split(",")]
    if len(bg_parts) != 3:
        raise SystemExit("--bg must be three comma-separated integers (R,G,B)")
    bg_tuple = (bg_parts[0], bg_parts[1], bg_parts[2])

    if not args.images.is_dir():
        raise SystemExit(f"Not a directory: {args.images}")

    args.out.mkdir(parents=True, exist_ok=True)

    subdirs = sorted(
        [p for p in args.images.iterdir() if p.is_dir() and not p.name.startswith(".")]
    )
    if not subdirs:
        raise SystemExit(f"No subfolders under {args.images}")

    transparent_empty = args.format in ("png", "webp")

    for folder in subdirs:
        strip = merge_folder(
            folder,
            slot_w=args.slot_width,
            height=args.height,
            slot_count=args.slots,
            bg=bg_tuple,
            transparent_empty=transparent_empty,
        )
        ext = {"png": ".png", "webp": ".webp", "jpeg": ".jpg"}[args.format]
        out_path = args.out / f"{folder.name}{ext}"
        if args.format == "png":
            strip.save(out_path, format="PNG", optimize=True)
        elif args.format == "webp":
            strip.save(
                out_path,
                format="WEBP",
                quality=q,
                method=args.webp_method,
            )
        else:
            strip.save(out_path, format="JPEG", quality=q, optimize=True)
        print(out_path)


if __name__ == "__main__":
    main()
