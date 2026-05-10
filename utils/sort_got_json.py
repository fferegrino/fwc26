#!/usr/bin/env python3
"""
Sort keys in got.json (Panini-style { PREFIX: [[num, count], ...], ... }).

- Top-level keys: "00" first, "FWC" second, then every other key A–Z.
- Each country's list of pairs is sorted by sticker number (first element).

Usage:
  python3 sort_got_json.py              # rewrite ./got.json in place
  python3 sort_got_json.py -i a.json -o b.json
  python3 sort_got_json.py --dry-run   # print key order only
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _got_key_rank(k: str) -> tuple[int, str]:
    """00 and FWC first (in that order), then all other keys A–Z."""
    if k == "00":
        return (0, "")
    if k == "FWC":
        return (1, "")
    return (2, str(k))


def sorted_got_keys(keys: Any) -> list[str]:
    return sorted(keys, key=_got_key_rank)


def format_got_json(data: dict[str, Any]) -> str:
    """Match the repo’s hand-edited style: 4-space keys, one [n, c] pair per line."""
    lines: list[str] = ["{"]
    keys = sorted_got_keys(data.keys())
    for ki, k in enumerate(keys):
        rows = data[k]
        lines.append(f'    {json.dumps(k)}: [')
        if isinstance(rows, list):
            for ri, row in enumerate(rows):
                comma = "," if ri < len(rows) - 1 else ""
                lines.append(f"        {json.dumps(row)}{comma}")
        lines.append("    ]" + ("," if ki < len(keys) - 1 else ""))
    lines.append("}")
    return "\n".join(lines) + "\n"


def _sort_country_rows(rows: Any) -> Any:
    if not isinstance(rows, list):
        return rows
    out: list[Any] = []
    for item in rows:
        if (
            isinstance(item, list)
            and len(item) >= 2
            and isinstance(item[0], int)
            and isinstance(item[1], int)
        ):
            out.append([item[0], item[1]])
        else:
            out.append(item)
    try:
        out.sort(key=lambda x: (x[0] if isinstance(x, list) and x else 0, str(x)))
    except TypeError:
        pass
    return out


def sort_got(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            k: _sort_country_rows(sort_got(obj[k]))
            for k in sorted_got_keys(obj.keys())
        }
    if isinstance(obj, list):
        return [sort_got(x) for x in obj]
    return obj


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "-i",
        "--input",
        type=Path,
        default=Path("got.json"),
        help="Input JSON path (default: got.json)",
    )
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output path (default: same as input, in-place)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Load, sort, print top-level key order; do not write",
    )
    args = p.parse_args()
    inp = args.input
    if not inp.is_file():
        raise SystemExit(f"Not a file: {inp}")

    data = json.loads(inp.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("Expected a JSON object at the root (dict of country -> rows).")
    sorted_data = sort_got(data)

    if args.dry_run:
        if isinstance(sorted_data, dict):
            print("Top-level keys:", ", ".join(sorted_data.keys()))
        else:
            print("Root is not an object; nothing to list.")
        return

    out = args.output or inp
    text = format_got_json(sorted_data)
    out.write_text(text, encoding="utf-8")
    print(f"Wrote {out} ({len(text)} bytes)")


if __name__ == "__main__":
    main()
