#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convert an Excel multilabel dataset to JSONL using a labelmap.

Expected Excel format:
- One text column (e.g., "RequirementText")
- Multiple label columns (e.g., "Functional (F)", "Availability (A)", ...) with 0/1 values

Output JSONL format (default):
{"text": "...", "labels": ["Functional (F)", ...], "label_ids": [0, ...]}

Usage:
  python convert_excel_to_jsonl.py ^
    --in_xlsx Dataset_Full_VI.xlsx ^
    --labelmap labelmap_from_excel.json ^
    --out_jsonl Dataset_Full_VI.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd


def load_labelmap(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        m = json.load(f)
    # basic validation
    for k in ("text_column", "label_names", "label2id"):
        if k not in m:
            raise ValueError(f"labelmap missing key: {k!r}")
    if not isinstance(m["label_names"], list) or not isinstance(m["label2id"], dict):
        raise ValueError("labelmap has invalid schema (label_names must be list, label2id must be dict)")
    return m


def is_positive(v: Any, threshold: float = 0.5) -> bool:
    """Return True if v indicates label is active."""
    if v is None:
        return False
    # pandas NaN
    try:
        if pd.isna(v):
            return False
    except Exception:
        pass

    # bool
    if isinstance(v, bool):
        return bool(v)

    # numbers in string or numeric
    if isinstance(v, (int, float)):
        try:
            return float(v) > threshold
        except Exception:
            return False

    s = str(v).strip().lower()
    if s in {"1", "true", "yes", "y", "on"}:
        return True
    if s in {"0", "false", "no", "n", "off", ""}:
        return False
    # last resort: try float
    try:
        return float(s) > threshold
    except Exception:
        return False


def row_to_labels(
    row: pd.Series,
    label_names: List[str],
    label2id: Dict[str, int],
    threshold: float = 0.5,
) -> Tuple[List[str], List[int]]:
    labels: List[str] = []
    label_ids: List[int] = []
    for name in label_names:
        if name not in row.index:
            continue
        if is_positive(row[name], threshold=threshold):
            labels.append(name)
            label_ids.append(int(label2id[name]))
    # keep stable order (already by label_names)
    return labels, label_ids


def main() -> int:
    ap = argparse.ArgumentParser(description="Convert Excel multilabel dataset to JSONL using a labelmap.")
    ap.add_argument("--in_xlsx", required=True, help="Input Excel file (.xlsx)")
    ap.add_argument("--out_jsonl", required=True, help="Output JSONL path")
    ap.add_argument("--labelmap", required=True, help="Labelmap JSON (contains text_column, label_names, label2id)")
    ap.add_argument("--sheet", default=None, help="Excel sheet name/index (default: first sheet)")
    ap.add_argument("--threshold", type=float, default=0.5, help="Threshold to treat numeric label values as positive")
    ap.add_argument("--include_labels", action="store_true", help="Include 'labels' string list in output (default: ON)")
    ap.add_argument("--no_labels", action="store_true", help="Do NOT include 'labels' string list (only label_ids)")
    ap.add_argument("--skip_no_label", action="store_true", help="Skip rows that have no active labels")
    ap.add_argument("--encoding", default="utf-8", help="Output file encoding (default: utf-8)")
    ap.set_defaults(include_labels=True)

    args = ap.parse_args()

    in_xlsx = Path(args.in_xlsx)
    out_jsonl = Path(args.out_jsonl)
    labelmap_path = Path(args.labelmap)

    if not in_xlsx.exists():
        print(f"ERROR: input Excel not found: {in_xlsx}", file=sys.stderr)
        return 2
    if not labelmap_path.exists():
        print(f"ERROR: labelmap not found: {labelmap_path}", file=sys.stderr)
        return 2

    labelmap = load_labelmap(labelmap_path)
    text_col: str = labelmap["text_column"]
    label_names: List[str] = labelmap["label_names"]
    label2id: Dict[str, int] = labelmap["label2id"]

    # read excel
    try:
        df = pd.read_excel(in_xlsx, sheet_name=args.sheet)
    except Exception as e:
        print(f"ERROR: failed to read excel: {e}", file=sys.stderr)
        return 2

    # validate columns
    missing = [c for c in [text_col, *label_names] if c not in df.columns]
    if missing:
        print("ERROR: Excel missing required columns:", file=sys.stderr)
        for c in missing:
            print(f"  - {c}", file=sys.stderr)
        print("\nAvailable columns:", file=sys.stderr)
        for c in df.columns.tolist():
            print(f"  - {c}", file=sys.stderr)
        return 2

    out_jsonl.parent.mkdir(parents=True, exist_ok=True)

    n_total = 0
    n_written = 0
    n_skipped_empty_text = 0
    n_skipped_no_label = 0

    with out_jsonl.open("w", encoding=args.encoding, newline="\n") as f:
        for _, row in df.iterrows():
            n_total += 1
            text = row.get(text_col, "")
            text = "" if pd.isna(text) else str(text).strip()
            if not text:
                n_skipped_empty_text += 1
                continue

            labels, label_ids = row_to_labels(row, label_names, label2id, threshold=args.threshold)

            if args.skip_no_label and len(label_ids) == 0:
                n_skipped_no_label += 1
                continue

            record: Dict[str, Any] = {"text": text}
            include_labels = args.include_labels and (not args.no_labels)
            if include_labels:
                record["labels"] = labels
            record["label_ids"] = label_ids

            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            n_written += 1

    print("Done.")
    print(f"Input rows: {n_total}")
    print(f"Written:    {n_written}")
    print(f"Skipped (empty text): {n_skipped_empty_text}")
    if args.skip_no_label:
        print(f"Skipped (no labels): {n_skipped_no_label}")
    print(f"Output: {out_jsonl.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
