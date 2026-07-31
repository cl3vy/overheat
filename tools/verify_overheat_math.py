#!/usr/bin/env python3
"""Verify generated OVERHEAT math files (spicy distribution).

Structural checks, per mode:
  - every book has id, events, payoutMultiplier
  - payoutMultiplier is one of {0, 0.4x, T, 1.5T, 3T, 10T} in book cents
  - win books: boot -> heat -> shutdown(tier) -> setTotalWin -> finalWin,
    bankedAt matches the tier payout, couldHaveReached >= bankedAt
  - salvage books: boot -> heat -> meltdown -> salvage -> money events (0.4x)
  - bust books: boot -> heat -> meltdown -> money events (0), crashTemp < T
  - lookup CSV matches books row-for-row (RGS hash check), valid uint64

ACP compliance gates, per mode (the checks that failed on Version 1):
  - weighted RTP exactly RTP_FRACTION, inside Stake's 90.0-96.70% window
  - weighted non-zero win probability >= 5% (1-in-20 rule)
  - payout standard deviation >= 0.6 (base volatility floor)
  - max win == 10*T and nothing at or above the 5,000x tail threshold
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from fractions import Fraction
from pathlib import Path

import zstandard

from gen_overheat_math import (
    MAX_WIN_MULT,
    PAYOUT_SCALE,
    RIGS,
    RTP_FRACTION,
    SALVAGE_PAYOUT,
    WIN_TIERS,
)

RTP_WINDOW = (Fraction(90, 100), Fraction(967, 1000))
MIN_NONZERO_PROB = Fraction(1, 20)
MIN_STD = 0.6
TAIL_THRESHOLD_MULT = 5000


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
    tier_payout_cents = {
        tier: int(mult * target * PAYOUT_SCALE) for tier, mult, _ in WIN_TIERS
    }
    salvage_cents = int(SALVAGE_PAYOUT * PAYOUT_SCALE)
    valid_payouts = {0, salvage_cents, *tier_payout_cents.values()}
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
        if pm not in valid_payouts:
            fail(f"book {book['id']} payoutMultiplier {pm} not in {sorted(valid_payouts)}")
            continue

        events = book["events"]
        types = [e["type"] for e in events]
        if [e["index"] for e in events] != list(range(len(events))):
            fail(f"book {book['id']} bad event indices")
        boot = events[0]
        if boot["rigTier"] != rig_id or abs(boot["targetTemp"] - float(target)) > 1e-9:
            fail(f"book {book['id']} bad boot event {boot}")
        money = [e for e in events if e["type"] in ("setTotalWin", "finalWin")]
        if len(money) != 2 or any(e["amount"] != pm for e in money):
            fail(f"book {book['id']} money events do not match payoutMultiplier")

        if pm in tier_payout_cents.values():
            if types != ["boot", "heat", "shutdown", "setTotalWin", "finalWin"]:
                fail(f"book {book['id']} unexpected win sequence {types}")
                continue
            shutdown = events[2]
            expected_banked = round(pm / PAYOUT_SCALE, 2)
            if shutdown.get("bankedAt") != expected_banked:
                fail(f"book {book['id']} shutdown bankedAt {shutdown.get('bankedAt')}")
            if tier_payout_cents.get(shutdown.get("tier")) != pm:
                fail(f"book {book['id']} tier {shutdown.get('tier')} mismatches payout {pm}")
            if shutdown.get("couldHaveReached", 0) < expected_banked:
                fail(f"book {book['id']} couldHaveReached below bankedAt")
            if events[1].get("crashTemp") != expected_banked:
                fail(f"book {book['id']} heat crashTemp != bankedAt")
        elif pm == salvage_cents:
            if types != ["boot", "heat", "meltdown", "salvage", "setTotalWin", "finalWin"]:
                fail(f"book {book['id']} unexpected salvage sequence {types}")
                continue
            if events[3]["amount"] != salvage_cents:
                fail(f"book {book['id']} salvage amount {events[3]['amount']}")
            if not (1.0 <= events[2]["crashTemp"] < float(target)):
                fail(f"book {book['id']} salvage crashTemp outside [1, T)")
        else:
            if types != ["boot", "heat", "meltdown", "setTotalWin", "finalWin"]:
                fail(f"book {book['id']} unexpected bust sequence {types}")
                continue
            if not (1.0 <= events[2]["crashTemp"] < float(target)):
                fail(f"book {book['id']} bust crashTemp outside [1, T)")

    lut = publish / f"lookUpTable_{rig_id}_0.csv"
    rows = list(csv.reader(lut.open()))
    if len(rows) != len(books):
        fail(f"lookup table has {len(rows)} rows, books {len(books)}")
    dot = Fraction(0)
    second_moment = Fraction(0)
    nonzero_weight = 0
    total_weight = 0
    max_payout = 0
    for row, book in zip(rows, books):
        sim_id, weight, payout = int(row[0]), int(row[1]), int(row[2])
        if sim_id != book["id"] or payout != book["payoutMultiplier"]:
            fail(f"lookup row {row} does not match book {book['id']}")
        if weight <= 0 or weight >= 2**64 or payout < 0 or payout >= 2**64:
            fail(f"lookup row {row} not valid uint64")
        mult = Fraction(payout, PAYOUT_SCALE)
        dot += weight * mult
        second_moment += weight * mult * mult
        total_weight += weight
        if payout > 0:
            nonzero_weight += weight
        max_payout = max(max_payout, payout)

    weighted_rtp = dot / total_weight
    nonzero_prob = Fraction(nonzero_weight, total_weight)
    variance = second_moment / total_weight - weighted_rtp * weighted_rtp
    std = math.sqrt(float(variance))
    expected_max = int(MAX_WIN_MULT * target * PAYOUT_SCALE)

    print(
        f"  {rig_id:>9}: {len(books)} books | RTP {float(weighted_rtp):.6f} "
        f"({'exact' if weighted_rtp == RTP_FRACTION else 'OFF TARGET'}) | "
        f"non-zero {float(nonzero_prob):.4f} | std {std:.3f} | "
        f"max {max_payout / PAYOUT_SCALE:.0f}x"
    )

    # --- ACP compliance gates ---
    if weighted_rtp != RTP_FRACTION:
        fail(f"weighted RTP {float(weighted_rtp)} != {float(RTP_FRACTION)}")
    if not (RTP_WINDOW[0] <= weighted_rtp <= RTP_WINDOW[1]):
        fail(f"RTP {float(weighted_rtp)} outside Stake window {RTP_WINDOW}")
    if nonzero_prob < MIN_NONZERO_PROB:
        fail(f"non-zero win probability {float(nonzero_prob):.4f} below 1-in-20 floor")
    if std < MIN_STD:
        fail(f"std {std:.4f} below base volatility floor {MIN_STD}")
    if max_payout != expected_max:
        fail(f"max payout {max_payout} != expected {expected_max}")
    if max_payout >= TAIL_THRESHOLD_MULT * PAYOUT_SCALE:
        fail(f"payout at or above the {TAIL_THRESHOLD_MULT}x tail threshold")
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
