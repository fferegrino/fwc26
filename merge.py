"""
Merge per-collection sticker folders into one horizontal strip (default 20 × 255 px slots, 300 px tall).

Expects layout like images/NED/NED1.jpg … images/NED/NED20.jpg and images/00/00.jpg.
Missing files leave a blank (background-colour) cell.
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
    with Image.open(path) as img:
        img = ImageOps.exif_transpose(img)
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA")
        if img.mode == "RGBA":
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1])
            img = bg
        else:
            img = img.convert("RGB")
        return img.resize((cell_w, cell_h), Image.Resampling.LANCZOS)


def merge_folder(
    folder: Path,
    *,
    slot_w: int,
    height: int,
    slot_count: int,
    bg: tuple[int, int, int],
) -> Image.Image:
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
        canvas.paste(cell, (x, 0))

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
        help="Output directory for merged JPEGs (default: ./images)",
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
        help="Background RGB for empty slots, comma-separated (default: 255,255,255)",
    )
    args = ap.parse_args()

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

    for folder in subdirs:
        strip = merge_folder(
            folder,
            slot_w=args.slot_width,
            height=args.height,
            slot_count=args.slots,
            bg=bg_tuple,
        )
        out_path = args.out / f"{folder.name}.jpg"
        strip.save(out_path, format="JPEG", quality=92, optimize=True)
        print(out_path)


if __name__ == "__main__":
    main()
