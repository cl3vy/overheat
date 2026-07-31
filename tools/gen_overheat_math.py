#!/usr/bin/env python3
"""OVERHEAT math generator ("spicy" distribution).

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

Outcome distribution (per rig, target T), RTP shares fixed across all rigs so
cross-mode RTP consistency is exact:

  clean shutdown   pays T        84% of RTP
  overdrive        pays 1.5*T     6% of RTP
  critical         pays 3*T       4% of RTP
  golden           pays 10*T      2% of RTP
  scrap salvage    pays 0.4x      4% of RTP  (on ~9.7% of spins; keeps every
                                              mode above the 1-in-20 non-zero
                                              win floor)
  bust             pays 0         remainder

Exactness: each class gets an exact integer total weight (its probability
numerator times a common scale) distributed across its book rows with at most
+-1 spread, so the weighted RTP equals RTP_FRACTION to the digit.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from fractions import Fraction
from pathlib import Path

import zstandard

# ---------------------------------------------------------------- constants

RTP_FRACTION = Fraction(193, 200)  # 96.5%, inside Stake's 90.0-96.70% window
HOUSE_EDGE = float(1 - RTP_FRACTION)
DISPLAY_CAP = 5000  # cosmetic cap on the revealed crash/post-mortem temperature
SIMS_PER_MODE = 100_000
PAYOUT_SCALE = 100  # books/lookup integer scale (matches math-sdk output)
GAME_ID = "overheat_rig"
BASE_SEED = 20260731

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

# win tiers: (tier name, payout as multiple of T, share of total RTP)
WIN_TIERS: list[tuple[str, Fraction, Fraction]] = [
    ("clean", Fraction(1), Fraction(21, 25)),  # 84%
    ("overdrive", Fraction(3, 2), Fraction(3, 50)),  # 6%
    ("critical", Fraction(3), Fraction(1, 25)),  # 4%
    ("golden", Fraction(10), Fraction(1, 50)),  # 2%
]
SALVAGE_PAYOUT = Fraction(2, 5)  # 0.4x stake, deliberately less than the bet
SALVAGE_SHARE = Fraction(1, 25)  # 4% of RTP

MAX_WIN_MULT = Fraction(10)  # golden tier: max win per rig = 10 * T

assert sum(share for _, _, share in WIN_TIERS) + SALVAGE_SHARE == 1


# ---------------------------------------------------------------- math core


def class_table(target: Fraction) -> list[tuple[str, Fraction, Fraction]]:
    """(class name, payout multiple of stake, exact probability) per outcome
    class, bust last. Probability of a class = RTP_share / payout."""
    classes: list[tuple[str, Fraction, Fraction]] = []
    for tier, mult, share in WIN_TIERS:
        payout = mult * target
        classes.append((tier, payout, share * RTP_FRACTION / payout))
    classes.append(("salvage", SALVAGE_PAYOUT, SALVAGE_SHARE * RTP_FRACTION / SALVAGE_PAYOUT))
    p_bust = 1 - sum(p for _, _, p in classes)
    assert p_bust > 0, f"target {target}: win probabilities exceed 1"
    classes.append(("bust", Fraction(0), p_bust))
    # RTP identity: sum(p * payout) == RTP_FRACTION
    assert sum(p * payout for _, payout, p in classes) == RTP_FRACTION
    return classes


def mode_std(target: Fraction) -> float:
    """Exact payout standard deviation for a rig."""
    classes = class_table(target)
    second_moment = sum(p * payout * payout for _, payout, p in classes)
    return float(math.sqrt(second_moment - RTP_FRACTION * RTP_FRACTION))


def draw_bust_crash(rng: random.Random, target: float) -> float:
    """Crash temperature conditional on busting below target.

    Unconditional law: P(C = 1) = 1 - R (fried on boot),
    P(C >= x) = R / x for x > 1. Rejection-sample the bust branch.
    """
    r = float(RTP_FRACTION)
    while True:
        u = rng.random()
        if u >= r:
            return 1.00
        v = rng.random()
        while v == 0.0:
            v = rng.random()
        c = 1.0 / v
        if c < target:
            return c


def draw_post_mortem(rng: random.Random, banked_at: float) -> float:
    """The temperature the silicon 'had in it', conditional on >= bankedAt:
    P(X >= x | X >= b) = b / x."""
    v = rng.random()
    while v == 0.0:
        v = rng.random()
    return min(banked_at / v, DISPLAY_CAP)


def floor2(x: float) -> float:
    return math.floor(x * 100) / 100.0


# ------------------------------------------------------------ book building


def build_win_book(
    sim_id: int, rig_id: str, target: float, tier: str, payout: Fraction, rng: random.Random
) -> dict:
    payout_mult = int(payout * PAYOUT_SCALE)
    assert payout * PAYOUT_SCALE == payout_mult, f"non-integer payout cents for {rig_id}/{tier}"
    banked_at = round(float(payout), 2)
    hashrate = rng.randint(200, 980)
    could_have_reached = max(banked_at, floor2(draw_post_mortem(rng, banked_at)))

    events = [
        {
            "index": 0,
            "type": "boot",
            "rigTier": rig_id,
            "targetTemp": round(target, 2),
            "hashrate": hashrate,
        },
        {"index": 1, "type": "heat", "crashTemp": banked_at},
        {
            "index": 2,
            "type": "shutdown",
            "bankedAt": banked_at,
            "couldHaveReached": could_have_reached,
            "tier": tier,
        },
        {"index": 3, "type": "setTotalWin", "amount": payout_mult},
        {"index": 4, "type": "finalWin", "amount": payout_mult},
    ]
    return {
        "id": sim_id,
        "payoutMultiplier": payout_mult,
        "events": events,
        "criteria": tier,
    }


def build_bust_book(
    sim_id: int, rig_id: str, target: float, salvage: bool, rng: random.Random
) -> dict:
    payout_mult = int(SALVAGE_PAYOUT * PAYOUT_SCALE) if salvage else 0
    hashrate = rng.randint(200, 980)
    crash = draw_bust_crash(rng, target)
    # floor so a 4.999 bust can never display as the 5.0 target
    crash_display = max(1.0, min(floor2(crash), floor2(target - 0.01)))

    events = [
        {
            "index": 0,
            "type": "boot",
            "rigTier": rig_id,
            "targetTemp": round(target, 2),
            "hashrate": hashrate,
        },
        {"index": 1, "type": "heat", "crashTemp": crash_display},
        {"index": 2, "type": "meltdown", "crashTemp": crash_display},
    ]
    next_index = 3
    if salvage:
        events.append({"index": next_index, "type": "salvage", "amount": payout_mult})
        next_index += 1
    events.append({"index": next_index, "type": "setTotalWin", "amount": payout_mult})
    events.append({"index": next_index + 1, "type": "finalWin", "amount": payout_mult})

    return {
        "id": sim_id,
        "payoutMultiplier": payout_mult,
        "events": events,
        "criteria": "salvage" if salvage else "bust",
    }


def class_row_counts(classes: list[tuple[str, Fraction, Fraction]], num_sims: int) -> dict[str, int]:
    """Book rows per class: roughly proportional to probability (for narrative
    variety), at least 1 per class. Exactness comes from the weights, not the
    counts."""
    counts: dict[str, int] = {}
    for name, _, p in classes[:-1]:
        counts[name] = max(1, round(float(p) * num_sims))
    used = sum(counts.values())
    assert used < num_sims, "sims too small for the class layout"
    counts["bust"] = num_sims - used
    return counts


def class_weights(
    classes: list[tuple[str, Fraction, Fraction]], counts: dict[str, int]
) -> dict[str, list[int]]:
    """Per-row integer weights. Each class receives an exact total weight
    a_c * S (a_c = probability numerator over the common denominator D), spread
    across its rows with at most +-1 difference, so class probabilities -- and
    therefore RTP -- are exact regardless of row counts."""
    denominator = math.lcm(*(p.denominator for _, _, p in classes))
    numerators = {name: int(p * denominator) for name, _, p in classes}
    assert sum(numerators.values()) == denominator

    # scale so every row gets weight >= 1, with slack for even spreading
    scale = 4 * max(math.ceil(counts[name] / numerators[name]) for name in numerators)

    weights: dict[str, list[int]] = {}
    for name in numerators:
        total, rows = numerators[name] * scale, counts[name]
        base, extra = divmod(total, rows)
        weights[name] = [base + 1] * extra + [base] * (rows - extra)
        assert base >= 1 and sum(weights[name]) == total
    return weights


def generate_mode(rig_id: str, num_sims: int, compress: bool, out_publish: Path, seed: int) -> dict:
    target_frac = RIGS[rig_id]
    target = float(target_frac)
    rng = random.Random(seed)

    classes = class_table(target_frac)
    counts = class_row_counts(classes, num_sims)
    weights = class_weights(classes, counts)

    books: list[dict] = []
    lut_rows: list[tuple[int, int, int]] = []
    sim_id = 0
    for name, payout, _ in classes:
        for row_weight in weights[name]:
            if name == "bust":
                book = build_bust_book(sim_id, rig_id, target, salvage=False, rng=rng)
            elif name == "salvage":
                book = build_bust_book(sim_id, rig_id, target, salvage=True, rng=rng)
            else:
                book = build_win_book(sim_id, rig_id, target, name, payout, rng=rng)
            books.append(book)
            lut_rows.append((sim_id, row_weight, book["payoutMultiplier"]))
            sim_id += 1

    # shuffle so book ids do not leak the outcome class ordering
    order = list(range(len(books)))
    rng.shuffle(order)
    books = [books[i] for i in order]
    lut_rows = [lut_rows[i] for i in order]
    for new_id, book in enumerate(books):
        book["id"] = new_id
    lut_rows = [(new_id, w, p) for new_id, (_, w, p) in enumerate(lut_rows)]

    books_name = f"books_{rig_id}.jsonl" + (".zst" if compress else "")
    books_path = out_publish / books_name
    payload = "".join(json.dumps(b, separators=(", ", ": ")) + "\n" for b in books).encode()
    if compress:
        payload = zstandard.ZstdCompressor().compress(payload)
    books_path.write_bytes(payload)

    lut_name = f"lookUpTable_{rig_id}_0.csv"
    with open(out_publish / lut_name, "w", newline="") as f:
        writer = csv.writer(f)
        for row in lut_rows:
            writer.writerow(row)

    # weighted RTP, exact by construction (kept as a sanity assertion)
    total_weight = sum(w for _, w, _ in lut_rows)
    rtp = sum(Fraction(p, PAYOUT_SCALE) * w for _, w, p in lut_rows) / total_weight
    assert rtp == RTP_FRACTION, f"{rig_id}: weighted RTP {rtp} != {RTP_FRACTION}"

    nonzero_prob = sum(
        Fraction(w, total_weight) for _, w, p in lut_rows if p > 0
    )
    print(
        f"  {rig_id:>9}: {len(books)} books | weighted RTP exactly {float(rtp):.4f} | "
        f"non-zero win prob {float(nonzero_prob):.4f} | std {mode_std(target_frac):.3f} | "
        f"max win {float(MAX_WIN_MULT * target_frac):.0f}x"
    )

    return {
        "name": rig_id,
        "books_file": books_name,
        "lut_file": lut_name,
        "book_length": len(books),
        "max_win": float(MAX_WIN_MULT * target_frac),
        "std": round(mode_std(target_frac), 4),
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
                "std": m["std"],
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
