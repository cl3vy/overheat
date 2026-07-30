#!/usr/bin/env python3
"""OVERHEAT math generator.

Produces the Stake Engine publishable math files for the rig-ladder crash game
directly, without the slot math-sdk scaffolding (brief section 4):

  publish_files/
    index.json
    books_<rig>.jsonl.zst      (or .jsonl uncompressed with --no-compress)
    lookUpTable_<rig>_0.csv    rows: id,weight,payoutMultiplier (uint64)
  configs/
    config.json                ACP math config (sha256 hashes, autoEndRoundDisabled)
    config_fe_overheat_rig.json

Format is matched to the math-sdk's fifty_fifty reference output:
payoutMultiplier is an integer, multiplier x 100 (e.g. a 5x win -> 500),
identical in books and the lookup-table third column (hash verified by RGS).

Lookup weights use two exact integer weight classes (win rows / bust rows),
derived with rational arithmetic so every mode's weighted RTP is exactly
RTP = 1 - HOUSE_EDGE by construction (brief 4.3 allows enforcing the exact
hit rate through weights).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import random
from fractions import Fraction
from pathlib import Path

import zstandard

# ---------------------------------------------------------------- constants

HOUSE_EDGE = 0.03  # e; RTP = 1 - e
DISPLAY_CAP = 5000  # cosmetic cap on the revealed crash temperature
SIMS_PER_MODE = 100_000
PAYOUT_SCALE = 100  # books/lookup integer scale (matches math-sdk output)
GAME_ID = "overheat_rig"
BASE_SEED = 20260730

# rig id -> shutdown temperature T (exact fraction, float for display)
# dense ladder so the frontend temp dial feels like a custom multiplier
RIGS: dict[str, Fraction] = {
    "idle": Fraction(6, 5),  # 1.2x
    "eco": Fraction(3, 2),  # 1.5x
    "standard": Fraction(2),  # 2x
    "boost": Fraction(3),  # 3x
    "overclock": Fraction(5),  # 5x
    "nitro": Fraction(7),  # 7x
    "furnace": Fraction(10),  # 10x
    "inferno": Fraction(15),  # 15x
    "meltdown": Fraction(25),  # 25x
    "reactor": Fraction(50),  # 50x
    "plasma": Fraction(100),  # 100x
}

RTP_FRACTION = 1 - Fraction(HOUSE_EDGE).limit_denominator(10_000)  # 97/100


# ---------------------------------------------------------------- math core


def draw_crash_temp(rng: random.Random, house_edge: float, display_cap: float) -> float:
    """Draw the crash temperature C. P(C >= x) = (1 - e) / x for x >= 1."""
    r = 1.0 - house_edge
    u = rng.random()
    if u >= r:  # probability e: instant bust at boot
        return 1.00
    v = rng.random()
    while v == 0.0:
        v = rng.random()
    c = 1.0 / v  # heavy tail: P(C >= x | survived boot) = 1/x
    return min(c, display_cap)


def draw_crash_temp_conditional_win(rng: random.Random, target: float, display_cap: float) -> float:
    """Draw C conditioned on C >= target: P(C >= x | C >= T) = T/x."""
    v = rng.random()
    while v == 0.0:
        v = rng.random()
    return min(target / v, display_cap)


def floor2(x: float) -> float:
    return math.floor(x * 100) / 100.0


# ------------------------------------------------------------ book building


def build_book(sim_id: int, rig_id: str, target: float, crash: float, rng: random.Random) -> dict:
    """One book per section 3.4 of the brief."""
    win = crash >= target
    payout_mult = int(round(target * PAYOUT_SCALE)) if win else 0
    hashrate = rng.randint(200, 980)

    events: list[dict] = [
        {
            "index": 0,
            "type": "boot",
            "rigTier": rig_id,
            "targetTemp": round(target, 2),
            "hashrate": hashrate,
        }
    ]
    if win:
        could_have_reached = max(round(target, 2), floor2(crash))
        events.append({"index": 1, "type": "heat", "crashTemp": round(target, 2)})
        events.append(
            {
                "index": 2,
                "type": "shutdown",
                "bankedAt": round(target, 2),
                "couldHaveReached": could_have_reached,
            }
        )
    else:
        # floor so a 4.999 bust can never display as the 5.0 target
        crash_display = max(1.0, min(floor2(crash), floor2(target - 0.01)))
        events.append({"index": 1, "type": "heat", "crashTemp": crash_display})
        events.append({"index": 2, "type": "meltdown", "crashTemp": crash_display})

    events.append({"index": 3, "type": "setTotalWin", "amount": payout_mult})
    events.append({"index": 4, "type": "finalWin", "amount": payout_mult})

    return {
        "id": sim_id,
        "payoutMultiplier": payout_mult,
        "events": events,
        "criteria": "win" if win else "bust",
    }


def exact_weights(n_win: int, n_bust: int, target: Fraction) -> tuple[int, int]:
    """Integer weights (win_row_weight, bust_row_weight) so the weighted win
    probability is exactly RTP/T, hence weighted RTP is exactly RTP."""
    p = RTP_FRACTION / target  # win probability, exact
    a = p.numerator * n_bust  # weight per win row
    b = (p.denominator - p.numerator) * n_win  # weight per bust row
    g = math.gcd(a, b)
    return a // g, b // g


def generate_mode(rig_id: str, num_sims: int, compress: bool, out_publish: Path, seed: int) -> dict:
    target_frac = RIGS[rig_id]
    target = float(target_frac)
    rng = random.Random(seed)

    crashes = [draw_crash_temp(rng, HOUSE_EDGE, DISPLAY_CAP) for _ in range(num_sims)]

    # weights need at least one row on each side; force the corner cases
    if not any(c >= target for c in crashes):
        crashes[0] = draw_crash_temp_conditional_win(rng, target, DISPLAY_CAP)
    if not any(c < target for c in crashes):
        crashes[0] = 1.0

    books = [build_book(i, rig_id, target, c, rng) for i, c in enumerate(crashes)]

    n_win = sum(1 for b in books if b["payoutMultiplier"] > 0)
    n_bust = num_sims - n_win
    w_win, w_bust = exact_weights(n_win, n_bust, target_frac)

    books_name = f"books_{rig_id}.jsonl" + (".zst" if compress else "")
    books_path = out_publish / books_name
    payload = "".join(json.dumps(b, separators=(", ", ": ")) + "\n" for b in books).encode()
    if compress:
        payload = zstandard.ZstdCompressor().compress(payload)
    books_path.write_bytes(payload)

    lut_name = f"lookUpTable_{rig_id}_0.csv"
    with open(out_publish / lut_name, "w", newline="") as f:
        writer = csv.writer(f)
        for b in books:
            weight = w_win if b["payoutMultiplier"] > 0 else w_bust
            writer.writerow([b["id"], weight, b["payoutMultiplier"]])

    # weighted RTP, exact by construction (kept as a sanity assertion)
    total_weight = n_win * w_win + n_bust * w_bust
    rtp = Fraction(n_win * w_win, total_weight) * target_frac
    assert rtp == RTP_FRACTION, f"{rig_id}: weighted RTP {rtp} != {RTP_FRACTION}"

    print(
        f"  {rig_id:>9}: {num_sims} sims, {n_win} wins "
        f"(hit rate {n_win / num_sims:.4f}, theoretical {float(RTP_FRACTION / target_frac):.4f}), "
        f"weighted RTP exactly {float(rtp):.4f}"
    )

    return {
        "name": rig_id,
        "books_file": books_name,
        "lut_file": lut_name,
        "book_length": num_sims,
        "max_win": target,
    }


# ---------------------------------------------------------------- configs


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_index(out_publish: Path, mode_infos: list[dict]) -> None:
    index = {
        "modes": [
            {
                "name": m["name"],
                "cost": 1.0,
                "events": m["books_file"],
                "weights": m["lut_file"],
            }
            for m in mode_infos
        ]
    }
    (out_publish / "index.json").write_text(json.dumps(index, indent=4) + "\n")


def write_configs(out_root: Path, out_publish: Path, mode_infos: list[dict]) -> None:
    out_configs = out_root / "configs"
    out_configs.mkdir(parents=True, exist_ok=True)
    rtp = float(RTP_FRACTION)

    fe_config = {
        "providerName": "overheat",
        "gameName": "OVERHEAT",
        "gameID": GAME_ID,
        "rtp": rtp,
        "numReels": 0,
        "numRows": [],
        "betModes": {
            m["name"]: {
                "cost": 1.0,
                "feature": True,
                "buyBonus": False,
                "rtp": rtp,
                "max_win": m["max_win"],
            }
            for m in mode_infos
        },
        "symbols": [],
        "paddingReels": {},
    }
    fe_path = out_configs / f"config_fe_{GAME_ID}.json"
    fe_path.write_text(json.dumps(fe_config, indent=4) + "\n")

    config = {
        "workingName": GAME_ID,
        "frontendConfig": {"file": fe_path.name, "sha256": sha256_of(fe_path)},
        "gameID": GAME_ID,
        "rtp": rtp,
        "betDenomination": 1000,
        "minDenomination": 10,
        "providerNumber": 1,
        "bookShelfConfig": [
            {
                "name": m["name"],
                "tables": [
                    {
                        "file": m["lut_file"],
                        "sha256": sha256_of(out_publish / m["lut_file"]),
                    }
                ],
                "cost": 1.0,
                "rtp": rtp,
                "std": 1.0,
                "bookLength": m["book_length"],
                "feature": True,
                # brief 5.4: frontend settles via /wallet/end-round at the
                # shutdown moment, so disconnected rounds can be resumed
                "autoEndRoundDisabled": True,
                "buyBonus": False,
                "maxWin": m["max_win"],
                "booksFile": {
                    "file": m["books_file"],
                    "sha256": sha256_of(out_publish / m["books_file"]),
                },
            }
            for m in mode_infos
        ],
    }
    (out_configs / "config.json").write_text(json.dumps(config, indent=4) + "\n")


# -------------------------------------------------------------------- main


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate OVERHEAT math files")
    parser.add_argument("--sims", type=int, default=SIMS_PER_MODE, help="simulations per mode")
    parser.add_argument("--modes", default=",".join(RIGS), help="comma-separated rig ids")
    parser.add_argument("--no-compress", action="store_true", help="write plain .jsonl books")
    parser.add_argument("--out", default="math-out", help="output root directory")
    parser.add_argument("--seed", type=int, default=BASE_SEED, help="base RNG seed")
    args = parser.parse_args()

    modes = [m.strip() for m in args.modes.split(",") if m.strip()]
    unknown = [m for m in modes if m not in RIGS]
    if unknown:
        parser.error(f"unknown rig ids: {unknown}; valid: {list(RIGS)}")

    out_root = Path(args.out)
    out_publish = out_root / "publish_files"
    out_publish.mkdir(parents=True, exist_ok=True)

    print(f"Generating OVERHEAT math (RTP {float(RTP_FRACTION)}, {args.sims} sims/mode)")
    mode_infos = []
    for i, rig_id in enumerate(modes):
        mode_infos.append(
            generate_mode(
                rig_id,
                args.sims,
                compress=not args.no_compress,
                out_publish=out_publish,
                seed=args.seed + i * 7919,
            )
        )

    write_index(out_publish, mode_infos)
    write_configs(out_root, out_publish, mode_infos)
    print(f"Done. Publish files in {out_publish}/, configs in {out_root}/configs/")


if __name__ == "__main__":
    main()
