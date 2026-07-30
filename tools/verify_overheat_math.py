#!/usr/bin/env python3
"""Verify generated OVERHEAT math files (brief sections 3.4, 4.3, 7).

Checks, per mode:
  - every book has id, events, payoutMultiplier
  - payoutMultiplier is exactly 0 or T*100
  - event sequence is boot -> heat -> (shutdown|meltdown) -> setTotalWin -> finalWin
  - setTotalWin/finalWin amounts equal payoutMultiplier
  - bust books show crashTemp < T; win books show couldHaveReached >= T
  - lookup CSV third column matches books payoutMultiplier row-for-row (RGS hash check)
  - weighted RTP from the lookup table equals the target RTP
  - empirical (unweighted) hit rate is close to R/T
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from fractions import Fraction
from pathlib import Path

import zstandard

from gen_overheat_math import RIGS, RTP_FRACTION, PAYOUT_SCALE


def load_books(publish: Path, rig_id: str) -> list[dict]:
    zst = publish / f"books_{rig_id}.jsonl.zst"
    plain = publish / f"books_{rig_id}.jsonl"
    if zst.exists():
        raw = zstandard.ZstdDecompressor().decompress(
            zst.read_bytes(), max_output_size=2_000_000_000
        )
    elif plain.exists():
        raw = plain.read_bytes()
    else:
        sys.exit(f"no books file for {rig_id} in {publish}")
    return [json.loads(line) for line in raw.decode().splitlines() if line.strip()]


def verify_mode(publish: Path, rig_id: str) -> bool:
    target = RIGS[rig_id]
    expected_payout = int(target * PAYOUT_SCALE)
    books = load_books(publish, rig_id)
    ok = True

    def fail(msg: str) -> None:
        nonlocal ok
        ok = False
        print(f"  FAIL [{rig_id}] {msg}")

    for book in books:
        for key in ("id", "events", "payoutMultiplier"):
            if key not in book:
                fail(f"book {book.get('id')} missing key {key}")
        pm = book["payoutMultiplier"]
        if pm not in (0, expected_payout):
            fail(f"book {book['id']} payoutMultiplier {pm} not in (0, {expected_payout})")

        types = [e["type"] for e in book["events"]]
        terminal = "shutdown" if pm > 0 else "meltdown"
        if types != ["boot", "heat", terminal, "setTotalWin", "finalWin"]:
            fail(f"book {book['id']} unexpected event sequence {types}")
            continue
        boot, heat, term, set_total, final = book["events"]
        if [e["index"] for e in book["events"]] != [0, 1, 2, 3, 4]:
            fail(f"book {book['id']} bad event indices")
        if boot["rigTier"] != rig_id or abs(boot["targetTemp"] - float(target)) > 1e-9:
            fail(f"book {book['id']} bad boot event {boot}")
        if set_total["amount"] != pm or final["amount"] != pm:
            fail(f"book {book['id']} money events do not match payoutMultiplier")
        if pm > 0:
            if term["bankedAt"] != round(float(target), 2):
                fail(f"book {book['id']} shutdown bankedAt {term['bankedAt']}")
            if term["couldHaveReached"] < float(target):
                fail(f"book {book['id']} couldHaveReached below target")
        else:
            if not (1.0 <= term["crashTemp"] < float(target)):
                fail(f"book {book['id']} bust crashTemp {term['crashTemp']} outside [1, T)")

    lut = publish / f"lookUpTable_{rig_id}_0.csv"
    rows = list(csv.reader(lut.open()))
    if len(rows) != len(books):
        fail(f"lookup table has {len(rows)} rows, books {len(books)}")
    dot = Fraction(0)
    total_weight = 0
    for row, book in zip(rows, books):
        sim_id, weight, payout = int(row[0]), int(row[1]), int(row[2])
        if sim_id != book["id"] or payout != book["payoutMultiplier"]:
            fail(f"lookup row {row} does not match book {book['id']}")
        if weight <= 0 or weight >= 2**64 or payout < 0 or payout >= 2**64:
            fail(f"lookup row {row} not valid uint64")
        dot += weight * Fraction(payout, PAYOUT_SCALE)
        total_weight += weight

    weighted_rtp = dot / total_weight
    n_win = sum(1 for b in books if b["payoutMultiplier"] > 0)
    hit_rate = n_win / len(books)
    theoretical = float(RTP_FRACTION / target)
    print(
        f"  {rig_id:>9}: {len(books)} books | weighted RTP {float(weighted_rtp):.6f} "
        f"({'exact' if weighted_rtp == RTP_FRACTION else 'OFF TARGET'}) | "
        f"empirical hit rate {hit_rate:.4f} vs R/T {theoretical:.4f}"
    )
    if weighted_rtp != RTP_FRACTION:
        fail(f"weighted RTP {float(weighted_rtp)} != {float(RTP_FRACTION)}")
    if len(books) >= 10_000 and abs(hit_rate - theoretical) > 5 * (theoretical**0.5) / (len(books) ** 0.5):
        fail(f"empirical hit rate {hit_rate} implausibly far from {theoretical}")
    return ok


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify OVERHEAT math files")
    parser.add_argument("--out", default="math-out", help="output root directory")
    parser.add_argument("--modes", default=",".join(RIGS), help="comma-separated rig ids")
    args = parser.parse_args()

    publish = Path(args.out) / "publish_files"
    modes = [m.strip() for m in args.modes.split(",") if m.strip()]

    index_path = publish / "index.json"
    if index_path.exists():
        index = json.loads(index_path.read_text())
        listed = {m["name"] for m in index["modes"]}
        print(f"index.json lists modes: {sorted(listed)}")
    else:
        print("WARNING: no index.json found")

    all_ok = True
    for rig_id in modes:
        all_ok &= verify_mode(publish, rig_id)

    if all_ok:
        print("ALL CHECKS PASSED")
    else:
        sys.exit("VERIFICATION FAILED")


if __name__ == "__main__":
    main()
