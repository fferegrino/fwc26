#!/usr/bin/env python3
"""
Convert got.json (Panini-style { PREFIX: [[num, count], ...], ... }) to CSV.

Output rows are:
  sticker_code,quantity

Examples:
  python3 utils/got_json_to_csv.py
  python3 utils/got_json_to_csv.py -i got.json -o got.csv
  python3 utils/got_json_to_csv.py --include-zero
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Iterable


def _got_key_rank(k: str) -> tuple[int, str]:
    if k == "00":
        return (0, "")
    if k == "FWC":
        return (1, "")
    return (2, str(k))


def _sorted_got_keys(keys: Iterable[str]) -> list[str]:
    return sorted(keys, key=_got_key_rank)


def _sticker_code(prefix: str, num: int) -> str:
    # For codes without digits (e.g. "00"), got.json uses 0 as the number.
    if num == 0 and prefix == "00":
        return prefix
    return f"{prefix}{num}"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "-i",
        "--input",
        type=Path,
        default=Path("got.json"),
        help="Input got.json path (default: got.json)",
    )
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("got.csv"),
        help="Output CSV path (default: got.csv)",
    )
    p.add_argument(
        "--include-zero",
        action="store_true",
        help="Include entries with quantity=0 (default: omit them)",
    )
    args = p.parse_args()

    inp: Path = args.input
    if not inp.is_file():
        raise SystemExit(f"Not a file: {inp}")

    data = json.loads(inp.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("Expected a JSON object at the root (dict of prefix -> rows).")

    rows_out: list[tuple[str, int]] = []
    for prefix in _sorted_got_keys(map(str, data.keys())):
        rows = data.get(prefix)
        if not isinstance(rows, list):
            continue
        for pair in rows:
            if (
                isinstance(pair, list)
                and len(pair) >= 2
                and isinstance(pair[0], int)
                and isinstance(pair[1], int)
            ):
                num, qty = pair[0], pair[1]
                if qty == 0 and not args.include_zero:
                    continue
                rows_out.append((_sticker_code(prefix, num), qty))

    out: Path = args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sticker_code", "quantity"])
        w.writerows(rows_out)

    print(f"Wrote {out} ({len(rows_out)} rows)")


if __name__ == "__main__":
    main()
