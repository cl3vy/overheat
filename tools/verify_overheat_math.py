#!/usr/bin/env python3
"""Verify generated OVERHEAT math files (checkpoint-banking distribution).

Structural checks, per mode:
  - every book has id, events, payoutMultiplier
  - payoutMultiplier is a ladder bank amount, a tier payout, or 0
  - bank events are monotonically increasing in temp and amount, match the
    rig's ladder rung-for-rung, and the payout equals the last bank (busts)
    or the tier payout (target reached)
  - tier books: boot -> heat -> bank* -> shutdown(tier) -> money events
  - bank/bust books: boot -> heat -> bank* -> meltdown(amount) -> money events,
    crash display temp consistent with the rungs crossed
  - lookup CSV matches books row-for-row (RGS hash check), valid uint64

ACP compliance gates, per mode:
  - weighted RTP exactly RTP_FRACTION, inside Stake's 90.0-96.70% window
  - weighted non-zero win probability >= 5% (1-in-20 rule)
  - payout standard deviation >= 0.6 (base volatility floor)
  - max win == 10*T and nothing at or above the 5,000x tail threshold
  - ETL(40x): payouts >= 40x carry at most MAX_TAIL_SHARE of the RTP, and
    modes with targets above 40x keep P(1x <= payout < 40x) above a floor

Texture gates (the problems from the diagnosis, pinned as regressions):
  - at least MIN_UNIQUE_PAYOUTS distinct non-zero payouts per mode
  - no empty payout band between 1x and the target (bands: 1-2, 2-5, 5-10,
    10-20, 20-50, 50-100, capped at T)
  - profitable (>= 1x) outcome at most MAX_PROFIT_GAP_SPINS apart on average
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
    TIER_SPLIT,
    build_rungs,
)

RTP_WINDOW = (Fraction(90, 100), Fraction(967, 1000))
MIN_NONZERO_PROB = Fraction(1, 20)
MIN_STD = 0.6
TAIL_THRESHOLD_MULT = 5000
MIN_UNIQUE_PAYOUTS = 12
MAX_PROFIT_GAP_SPINS = 15.0
BAND_EDGES = [1, 2, 5, 10, 20, 50, 100]

# Expected tail liability (ETL 40x): the share of RTP carried by payouts at
# or above 40x must stay in line with the rest of the ladder. Conservative
# gate; tighten if ACP still flags a mode.
ETL_MULT = 40
MAX_TAIL_SHARE = 0.15
# and the band the player can feel must actually pay: P(1x <= payout < 40x)
MIN_MID_BAND_PROB = 0.05


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
    target_f = float(target)
    rungs = build_rungs(rig_id)
    bank_cents = [r.bank_cents for r in rungs]
    rung_temps = [r.temp for r in rungs]
    tier_pay = {t: int(mult * target * PAYOUT_SCALE) for t, mult, _ in TIER_SPLIT}
    valid_payouts = {0, *bank_cents, *tier_pay.values()}
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
            fail(f"book {book['id']} payoutMultiplier {pm} not a ladder value")
            continue

        events = book["events"]
        types = [e["type"] for e in events]
        if [e["index"] for e in events] != list(range(len(events))):
            fail(f"book {book['id']} bad event indices")
            continue
        boot = events[0]
        if boot["rigTier"] != rig_id or abs(boot["targetTemp"] - target_f) > 1e-9:
            fail(f"book {book['id']} bad boot event {boot}")
        if types[1] != "heat":
            fail(f"book {book['id']} second event is {types[1]}, not heat")
            continue
        money = [e for e in events if e["type"] in ("setTotalWin", "finalWin")]
        if len(money) != 2 or any(e["amount"] != pm for e in money):
            fail(f"book {book['id']} money events do not match payoutMultiplier")
        if types[-2:] != ["setTotalWin", "finalWin"]:
            fail(f"book {book['id']} money events not last: {types}")

        banks = [e for e in events if e["type"] == "bank"]
        # bank events must be the rig ladder's first N rungs, in order
        for j, bank in enumerate(banks):
            if bank["amount"] != bank_cents[j] or abs(bank["temp"] - rung_temps[j]) > 1e-9:
                fail(f"book {book['id']} bank event {j} mismatches ladder")
                break
        if types.count("bank") != len(banks) or types[2 : 2 + len(banks)] != ["bank"] * len(banks):
            fail(f"book {book['id']} bank events out of place: {types}")

        settle = events[2 + len(banks)]
        crash_temp = events[1].get("crashTemp", 0.0)

        if settle["type"] == "shutdown":
            tier = settle.get("tier")
            if tier_pay.get(tier) != pm:
                fail(f"book {book['id']} tier {tier} mismatches payout {pm}")
            if len(banks) != len(rungs):
                fail(f"book {book['id']} target reached but only {len(banks)} banks")
            expected_banked = round(pm / PAYOUT_SCALE, 2)
            if settle.get("bankedAt") != expected_banked:
                fail(f"book {book['id']} shutdown bankedAt {settle.get('bankedAt')}")
            if settle.get("couldHaveReached", 0) < expected_banked:
                fail(f"book {book['id']} couldHaveReached below bankedAt")
            if crash_temp != expected_banked:
                fail(f"book {book['id']} heat crashTemp != bankedAt")
        elif settle["type"] == "meltdown":
            if settle.get("amount") != pm:
                fail(f"book {book['id']} meltdown amount {settle.get('amount')} != {pm}")
            expected_pay = bank_cents[len(banks) - 1] if banks else 0
            if pm != expected_pay:
                fail(f"book {book['id']} payout {pm} != last bank {expected_pay}")
            lo = rung_temps[len(banks) - 1] if banks else 1.0
            hi = rung_temps[len(banks)] if len(banks) < len(rungs) else target_f
            if not (lo <= crash_temp < hi):
                fail(f"book {book['id']} crashTemp {crash_temp} outside [{lo}, {hi})")
            if abs(settle.get("crashTemp", -1) - crash_temp) > 1e-9:
                fail(f"book {book['id']} meltdown crashTemp != heat crashTemp")
        else:
            fail(f"book {book['id']} unexpected settle event {settle['type']}")

    lut = publish / f"lookUpTable_{rig_id}_0.csv"
    rows = list(csv.reader(lut.open()))
    if len(rows) != len(books):
        fail(f"lookup table has {len(rows)} rows, books {len(books)}")
    dot = Fraction(0)
    second_moment = Fraction(0)
    tail_dot = Fraction(0)
    nonzero_weight = 0
    profit_weight = 0
    mid_band_weight = 0
    total_weight = 0
    max_payout = 0
    payout_weights: dict[int, int] = {}
    etl_cents = ETL_MULT * PAYOUT_SCALE
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
            payout_weights[payout] = payout_weights.get(payout, 0) + weight
        if payout >= PAYOUT_SCALE:
            profit_weight += weight
            if payout < etl_cents:
                mid_band_weight += weight
        if payout >= etl_cents:
            tail_dot += weight * mult
        max_payout = max(max_payout, payout)

    weighted_rtp = dot / total_weight
    nonzero_prob = Fraction(nonzero_weight, total_weight)
    profit_prob = Fraction(profit_weight, total_weight)
    variance = second_moment / total_weight - weighted_rtp * weighted_rtp
    std = math.sqrt(float(variance))
    expected_max = int(MAX_WIN_MULT * target * PAYOUT_SCALE)
    profit_gap = float(1 / profit_prob) if profit_prob else math.inf
    tail_share = float(tail_dot / dot) if dot else 0.0
    mid_band_prob = Fraction(mid_band_weight, total_weight)

    print(
        f"  {rig_id:>9}: {len(books)} books | RTP {float(weighted_rtp):.6f} "
        f"({'exact' if weighted_rtp == RTP_FRACTION else 'OFF TARGET'}) | "
        f"any-pay {float(nonzero_prob):.4f} | profit 1-in-{profit_gap:.1f} | "
        f"{len(payout_weights)} payouts | std {std:.3f} | "
        f"ETL{ETL_MULT} {tail_share * 100:.1f}% | "
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
    if tail_share > MAX_TAIL_SHARE:
        fail(
            f"ETL({ETL_MULT}x): payouts >= {ETL_MULT}x carry {tail_share * 100:.1f}% "
            f"of RTP (max {MAX_TAIL_SHARE * 100:.0f}%)"
        )
    if float(target) > ETL_MULT and mid_band_prob < MIN_MID_BAND_PROB:
        fail(
            f"P(1x <= payout < {ETL_MULT}x) = {float(mid_band_prob):.4f} "
            f"below floor {MIN_MID_BAND_PROB}"
        )

    # --- texture gates (regressions against the diagnosis) ---
    if len(payout_weights) < MIN_UNIQUE_PAYOUTS:
        fail(f"only {len(payout_weights)} distinct payouts, need {MIN_UNIQUE_PAYOUTS}")
    payouts_x = sorted(p / PAYOUT_SCALE for p in payout_weights)
    for lo, hi in zip(BAND_EDGES, BAND_EDGES[1:]):
        if lo >= target_f:
            break
        band_hi = min(hi, target_f)
        if not any(lo <= p <= band_hi for p in payouts_x):
            fail(f"empty payout band [{lo}, {band_hi}] below the target")
    if profit_gap > MAX_PROFIT_GAP_SPINS:
        fail(f"profitable outcome only 1 in {profit_gap:.1f} spins (max {MAX_PROFIT_GAP_SPINS})")
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
