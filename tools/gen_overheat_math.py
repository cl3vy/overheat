#!/usr/bin/env python3
"""OVERHEAT math generator (checkpoint-banking distribution).

Produces the Stake Engine publishable math files for the rig-ladder crash game
directly, without the slot math-sdk scaffolding (brief section 4):

  publish_files/
    index.json
    books_<rig>.jsonl.zst      (or .jsonl uncompressed with --no-compress)
    lookUpTable_<rig>_0.csv    rows: id,weight,payoutMultiplier (uint64)
  configs/
    config.json                ACP math config (sha256 hashes, autoEndRoundDisabled)
    config_fe_overheat_rig.json
    ladders.json               per-rig ladder tables (also copied into the frontend)

Format is matched to the math-sdk's fifty_fifty reference output:
payoutMultiplier is an integer, multiplier x 100 (e.g. a 5x win -> 500),
identical in books and the lookup-table third column (hash verified by RGS).

Outcome model (per rig, target T) -- checkpoint banking:

  The round is a crash temperature C following the crash law
  P(C >= x) = r / x. A ladder of banking rungs c_1 < ... < c_k < T secures a
  cumulative amount B_i when crossed; frying keeps everything banked so far.
  Surviving to T pays the full target, split into rare tiers above it
  (clean T / overdrive 1.5T / critical 3T / golden 10T), so payouts sweep
  densely from below stake to 10T instead of collapsing to a handful of
  values.

  r is solved exactly so that expected payout equals RTP_FRACTION:
      RTP = r * [ sum_i (B_i - B_{i-1}) / c_i  +  (M*T - B_k) / T ]
  where M is the mean tier multiple. Rung probabilities are exact fractions;
  they are quantized to integer weights summing to TOTAL_WEIGHT with a final
  exact correction (a bounded weight transfer between two payout classes), so
  the weighted RTP in the published lookup tables equals RTP_FRACTION to the
  digit.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

import zstandard

# ---------------------------------------------------------------- constants

RTP_FRACTION = Fraction(193, 200)  # 96.5%, inside Stake's 90.0-96.70% window
HOUSE_EDGE = float(1 - RTP_FRACTION)
DISPLAY_CAP = 5000  # cosmetic cap on the revealed post-mortem temperature
SIMS_PER_MODE = 100_000
PAYOUT_SCALE = 100  # books/lookup integer scale (matches math-sdk output)
GAME_ID = "overheat_rig"
BASE_SEED = 20260731
TOTAL_WEIGHT = 10**12  # lookup weights per mode sum to exactly this

# rig id -> shutdown temperature T (exact fraction, float for display)
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

# Ladder personalities: rigs differ in banking *shape*, not just cap.
#   below: banking rungs strictly below target
#   start: where the first rung sits (fraction of the log temp range)
#   phi0/phi1: banked fraction of the current temp at the first/last rung
#   gamma: >1 back-loads the banked fraction ramp (spike machines)
PROFILES: dict[str, dict] = {
    "drip": {"below": 12, "start": 0.18, "phi0": 0.55, "phi1": 0.90, "gamma": 1.0},
    "balanced": {"below": 14, "start": 0.10, "phi0": 0.38, "phi1": 0.85, "gamma": 1.25},
    "spike": {"below": 14, "start": 0.07, "phi0": 0.25, "phi1": 0.78, "gamma": 1.6},
    # top rigs (50x/100x): dense, rich ladder in the feelable 1x-40x band so
    # the expected tail liability above 40x stays in line with the other modes
    "spike_deep": {"below": 18, "start": 0.05, "phi0": 0.45, "phi1": 0.82, "gamma": 1.1},
}
RIG_PROFILE: dict[str, str] = {
    "idle": "drip",
    "eco": "drip",
    "standard": "drip",
    "boost": "balanced",
    "overclock": "balanced",
    "nitro": "balanced",
    "furnace": "balanced",
    "inferno": "spike",
    "meltdown": "spike",
    "reactor": "spike_deep",
    "plasma": "spike_deep",
}

# Per-rig nudges on top of the shared profile (QA 6.2): the profile buckets
# set the checkpoint *shape* (frequent-small vs rare-big) for the rules
# table, but two profile boundaries left "pays something" non-monotonic --
# inferno (spike) rolled higher than furnace (balanced) and reactor
# (spike_deep) rolled higher than meltdown (spike), even though both sit at
# a higher target. Raising `start` (the first rung moves later in log-temp)
# on just those two rigs restores a strictly decreasing hit rate along the
# whole ladder without touching furnace/meltdown/plasma's own math.
PROFILE_OVERRIDES: dict[str, dict] = {
    "inferno": {"start": 0.105},
    "reactor": {"start": 0.07},
}

# ETL(40x) rebalance for the top rigs: the pure crash law loads ~50% of the
# RTP into payouts >= 40x on REACTOR/PLASMA (target-tier mass), failing the
# expected-tail-liability check and starving the 1x-40x band the player can
# feel. TAIL_DAMP scales the reach-target probability down; the exact-RTP
# solver then pushes the freed EV into the sub-40x banking rungs (r rises,
# every rung pays more often). BANK_CAP_CENTS keeps rung payouts themselves
# below the 40x tail threshold.
TAIL_DAMP: dict[str, Fraction] = {
    "reactor": Fraction(1, 4),
    "plasma": Fraction(1, 5),
}
BANK_CAP_CENTS: dict[str, int] = {
    "reactor": 3899,  # 38.99x
    "plasma": 3899,
}

# Split of the reach-target probability into payout tiers:
# (tier, payout as multiple of T, share of the reach-target mass)
TIER_SPLIT: list[tuple[str, Fraction, Fraction]] = [
    ("clean", Fraction(1), Fraction(9, 10)),
    ("overdrive", Fraction(3, 2), Fraction(3, 50)),
    ("critical", Fraction(3), Fraction(3, 100)),
    ("golden", Fraction(10), Fraction(1, 100)),
]
MAX_WIN_MULT = Fraction(10)  # golden tier: max win per rig = 10 * T

assert sum(share for _, _, share in TIER_SPLIT) == 1
# mean payout multiple of T conditional on reaching the target
TIER_MEAN_MULT = sum(share * mult for _, mult, share in TIER_SPLIT)

# share of bust books displayed as an instant fry at 1.00x (cosmetic)
INSTANT_FRY_DISPLAY = 0.12


# ------------------------------------------------------------------ ladder


@dataclass(frozen=True)
class Rung:
    temp_cents: int  # rung temperature x100
    bank_cents: int  # cumulative banked payout x100 once crossed

    @property
    def temp(self) -> float:
        return self.temp_cents / 100.0

    @property
    def bank(self) -> float:
        return self.bank_cents / 100.0


@dataclass(frozen=True)
class OutcomeClass:
    name: str  # bank1..bankN, clean, overdrive, critical, golden, bust
    kind: str  # "bank" | "tier" | "bust"
    pay_cents: int
    prob: Fraction
    temp_lo: float  # crash display interval (bank/bust classes)
    temp_hi: float
    rungs_crossed: int


def build_rungs(rig_id: str) -> list[Rung]:
    """Banking rungs strictly below the target, geometric temps, banked
    fraction ramping by rig personality."""
    target_c = int(RIGS[rig_id] * 100)
    prof = {**PROFILES[RIG_PROFILE[rig_id]], **PROFILE_OVERRIDES.get(rig_id, {})}
    n = prof["below"]
    ln_t = math.log(float(RIGS[rig_id]))
    ln_start = prof["start"] * ln_t

    rungs: list[Rung] = []
    last_t, last_b = 100, 0
    for i in range(1, n + 1):
        frac = i / (n + 1)
        temp = math.exp(ln_start + (ln_t - ln_start) * frac)
        tc = max(round(temp * 100), last_t + 1)
        if tc >= target_c:
            break  # tiny targets can't fit the full rung count
        phi = prof["phi0"] + (prof["phi1"] - prof["phi0"]) * frac ** prof["gamma"]
        bc = max(round(phi * tc), last_b + 1, 5)
        bc = min(bc, target_c - 1)  # banked amounts stay below the full target
        cap = BANK_CAP_CENTS.get(rig_id)
        if cap is not None:
            # stay under the ETL threshold but keep banks strictly increasing
            bc = min(bc, max(cap, last_b + 1))
        if bc <= last_b:
            continue
        rungs.append(Rung(tc, bc))
        last_t, last_b = tc, bc
    assert rungs, f"{rig_id}: no rungs fit below target"
    return rungs


def mode_classes(rig_id: str) -> tuple[list[OutcomeClass], Fraction, list[Rung]]:
    """Exact outcome classes for a rig. RTP identity holds by construction."""
    target = RIGS[rig_id]
    rungs = build_rungs(rig_id)
    damp = TAIL_DAMP.get(rig_id, Fraction(1))

    # RTP = r * K  =>  r = RTP / K   (all exact fractions)
    # The tier term is scaled by the tail damp: less mass reaches the target,
    # so the solver raises r and the banking rungs pay more often.
    k = Fraction(0)
    prev_bank = Fraction(0)
    for rung in rungs:
        bank = Fraction(rung.bank_cents, 100)
        k += (bank - prev_bank) / Fraction(rung.temp_cents, 100)
        prev_bank = bank
    # Abel summation of the bank classes leaves -B_k/T (undamped: the last
    # bank interval keeps its full crash-law mass); the tier mass carries damp.
    k += (damp * TIER_MEAN_MULT * target - prev_bank) / target
    r = RTP_FRACTION / k

    first_temp = Fraction(rungs[0].temp_cents, 100)
    assert r / first_temp < 1, f"{rig_id}: reach law exceeds 1 at the first rung"

    classes: list[OutcomeClass] = []
    for i, rung in enumerate(rungs):
        c_lo = Fraction(rung.temp_cents, 100)
        c_hi = (
            Fraction(rungs[i + 1].temp_cents, 100) if i + 1 < len(rungs) else target
        )
        prob = r * (1 / c_lo - 1 / c_hi)
        classes.append(
            OutcomeClass(
                f"bank{i + 1}", "bank", rung.bank_cents, prob,
                float(c_lo), float(c_hi), i + 1,
            )
        )

    q_target = damp * r / target
    for tier, mult, share in TIER_SPLIT:
        pay = mult * target * PAYOUT_SCALE
        assert pay.denominator == 1, f"{rig_id}/{tier}: non-integer payout cents"
        classes.append(
            OutcomeClass(
                tier, "tier", int(pay), q_target * share,
                float(target), float(target), len(rungs),
            )
        )

    p_win = sum(c.prob for c in classes)
    assert p_win < 1, f"{rig_id}: win probabilities exceed 1"
    classes.append(
        OutcomeClass("bust", "bust", 0, 1 - p_win, 1.0, float(first_temp), 0)
    )

    # RTP identity, exact
    rtp = sum(c.prob * Fraction(c.pay_cents, PAYOUT_SCALE) for c in classes)
    assert rtp == RTP_FRACTION, f"{rig_id}: class RTP {rtp} != {RTP_FRACTION}"
    return classes, r, rungs


# --------------------------------------------------- exact integer weights


def _egcd(a: int, b: int) -> tuple[int, int, int]:
    if b == 0:
        return a, 1, 0
    g, x, y = _egcd(b, a % b)
    return g, y, x - (a // b) * y


def quantize_weights(classes: list[OutcomeClass], total: int = TOTAL_WEIGHT) -> dict[str, int]:
    """Integer weight per class summing to `total`, with the weighted RTP
    equal to RTP_FRACTION exactly. Quantization error (< one weight unit per
    class) is cancelled by a bounded transfer between two payout classes and
    the bust class, shifting probabilities by under 1e-6 absolute."""
    weights: dict[str, int] = {}
    for c in classes:
        if c.kind != "bust":
            weights[c.name] = int(c.prob * total)  # floor
    weights["bust"] = total - sum(weights.values())

    target_dot = RTP_FRACTION * PAYOUT_SCALE * total
    assert target_dot.denominator == 1
    target_dot = int(target_dot)
    err = target_dot - sum(weights[c.name] * c.pay_cents for c in classes)

    if err != 0:
        paying = [c for c in classes if c.pay_cents > 0]
        adjusted = False
        for ai in range(len(paying)):
            for bi in range(ai + 1, len(paying)):
                pa, pb = paying[ai].pay_cents, paying[bi].pay_cents
                g, x, y = _egcd(pa, pb)
                if err % g:
                    continue
                scale = err // g
                x0, y0 = x * scale, y * scale
                step = pb // g
                t = round(x0 / step)
                dx = x0 - t * step
                dy = y0 + t * (pa // g)
                na, nb = paying[ai].name, paying[bi].name
                if (
                    weights[na] + dx > 0
                    and weights[nb] + dy > 0
                    and weights["bust"] - dx - dy > 0
                ):
                    weights[na] += dx
                    weights[nb] += dy
                    weights["bust"] -= dx + dy
                    adjusted = True
                    break
            if adjusted:
                break
        assert adjusted, "could not cancel the RTP quantization error"

    assert sum(weights.values()) == total
    assert sum(weights[c.name] * c.pay_cents for c in classes) == target_dot
    return weights


def class_row_counts(classes: list[OutcomeClass], num_sims: int) -> dict[str, int]:
    """Book rows per class, roughly proportional to probability (for display
    variety), at least 1. Exactness lives in the weights, not the counts."""
    counts: dict[str, int] = {}
    for c in classes[:-1]:
        counts[c.name] = max(1, round(float(c.prob) * num_sims))
    used = sum(counts.values())
    assert used < num_sims, "sims too small for the class layout"
    counts["bust"] = num_sims - used
    return counts


def spread_weight(total_weight: int, rows: int) -> list[int]:
    base, extra = divmod(total_weight, rows)
    assert base >= 1, "class weight too small for its row count"
    return [base + 1] * extra + [base] * (rows - extra)


# ------------------------------------------------------------ book building


def floor2(x: float) -> float:
    return math.floor(x * 100) / 100.0


def draw_in_interval(rng: random.Random, lo: float, hi: float) -> float:
    """Crash display temperature, hyperbolic law conditional on [lo, hi):
    P(C >= x | interval) via inverse transform. Clamped in integer cents so
    one-cent-wide rungs cannot round outside their interval."""
    u = rng.random()
    x = 1.0 / (1.0 / lo - u * (1.0 / lo - 1.0 / hi))
    lo_c, hi_c = round(lo * 100), round(hi * 100)
    xc = min(max(math.floor(x * 100 + 1e-9), lo_c), hi_c - 1)
    return xc / 100.0


def draw_post_mortem(rng: random.Random, banked_at: float) -> float:
    """The temperature the silicon 'had in it', conditional on >= bankedAt:
    P(X >= x | X >= b) = b / x."""
    v = rng.random()
    while v == 0.0:
        v = rng.random()
    return min(banked_at / v, DISPLAY_CAP)


def bank_events(rungs: list[Rung], crossed: int, start_index: int) -> list[dict]:
    return [
        {
            "index": start_index + j,
            "type": "bank",
            "temp": rungs[j].temp,
            "amount": rungs[j].bank_cents,
        }
        for j in range(crossed)
    ]


def build_book(
    sim_id: int,
    rig_id: str,
    outcome: OutcomeClass,
    rungs: list[Rung],
    rng: random.Random,
) -> dict:
    target = float(RIGS[rig_id])
    pay = outcome.pay_cents
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

    if outcome.kind == "tier":
        banked_at = round(pay / PAYOUT_SCALE, 2)
        could_have = max(banked_at, floor2(draw_post_mortem(rng, banked_at)))
        events.append({"index": 1, "type": "heat", "crashTemp": banked_at})
        events.extend(bank_events(rungs, outcome.rungs_crossed, 2))
        nxt = 2 + outcome.rungs_crossed
        events.append(
            {
                "index": nxt,
                "type": "shutdown",
                "bankedAt": banked_at,
                "couldHaveReached": could_have,
                "tier": outcome.name,
            }
        )
        nxt += 1
    else:
        if outcome.kind == "bust" and rng.random() < INSTANT_FRY_DISPLAY:
            crash_display = 1.00
        else:
            crash_display = draw_in_interval(rng, outcome.temp_lo, outcome.temp_hi)
        events.append({"index": 1, "type": "heat", "crashTemp": crash_display})
        events.extend(bank_events(rungs, outcome.rungs_crossed, 2))
        nxt = 2 + outcome.rungs_crossed
        events.append(
            {"index": nxt, "type": "meltdown", "crashTemp": crash_display, "amount": pay}
        )
        nxt += 1

    events.append({"index": nxt, "type": "setTotalWin", "amount": pay})
    events.append({"index": nxt + 1, "type": "finalWin", "amount": pay})

    return {
        "id": sim_id,
        "payoutMultiplier": pay,
        "events": events,
        "criteria": outcome.name if outcome.kind != "bank" else "bank",
    }


def generate_mode(
    rig_id: str, num_sims: int, compress: bool, out_publish: Path, seed: int
) -> dict:
    rng = random.Random(seed)
    classes, r, rungs = mode_classes(rig_id)
    weights = quantize_weights(classes)
    counts = class_row_counts(classes, num_sims)

    books: list[dict] = []
    lut_rows: list[tuple[int, int, int]] = []
    sim_id = 0
    for outcome in classes:
        for row_weight in spread_weight(weights[outcome.name], counts[outcome.name]):
            book = build_book(sim_id, rig_id, outcome, rungs, rng)
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
    payload = "".join(json.dumps(b, separators=(", ", ": ")) + "\n" for b in books).encode()
    if compress:
        payload = zstandard.ZstdCompressor().compress(payload)
    (out_publish / books_name).write_bytes(payload)

    lut_name = f"lookUpTable_{rig_id}_0.csv"
    with open(out_publish / lut_name, "w", newline="") as f:
        writer = csv.writer(f)
        for row in lut_rows:
            writer.writerow(row)

    # exact stats from the published weights
    total_weight = sum(w for _, w, _ in lut_rows)
    rtp = sum(Fraction(p, PAYOUT_SCALE) * w for _, w, p in lut_rows) / total_weight
    assert rtp == RTP_FRACTION, f"{rig_id}: weighted RTP {rtp} != {RTP_FRACTION}"
    second = sum(Fraction(p, PAYOUT_SCALE) ** 2 * w for _, w, p in lut_rows) / total_weight
    std = math.sqrt(float(second - rtp * rtp))

    any_prob = float(sum(c.prob for c in classes if c.pay_cents > 0))
    profit_prob = float(sum(c.prob for c in classes if c.pay_cents >= PAYOUT_SCALE))
    unique_pays = len({c.pay_cents for c in classes if c.pay_cents > 0})
    print(
        f"  {rig_id:>9}: {len(books)} books | RTP exact {float(rtp):.4f} | "
        f"any-pay {any_prob:.3f} | profit {profit_prob:.3f} "
        f"(1 in {1 / profit_prob:.1f}) | {unique_pays} payouts | "
        f"std {std:.3f} | max {float(MAX_WIN_MULT * RIGS[rig_id]):.0f}x"
    )

    return {
        "name": rig_id,
        "books_file": books_name,
        "lut_file": lut_name,
        "book_length": len(books),
        "max_win": float(MAX_WIN_MULT * RIGS[rig_id]),
        "std": round(std, 4),
        "classes": classes,
        "rungs": rungs,
        "reach_scale": r,
        "any_prob": any_prob,
        "profit_prob": profit_prob,
    }


# ---------------------------------------------------------------- ladders.json


def ladder_payload(mode_infos: list[dict]) -> dict:
    """Per-rig ladder tables consumed by the frontend (display, odds, and the
    Storybook realistic sampler). Probabilities are floats of the exact math."""
    payload: dict[str, dict] = {}
    for m in mode_infos:
        rig_id = m["name"]
        classes: list[OutcomeClass] = m["classes"]
        rungs: list[Rung] = m["rungs"]
        bank_probs = {c.name: float(c.prob) for c in classes}
        payload[rig_id] = {
            "target": float(RIGS[rig_id]),
            "profile": RIG_PROFILE[rig_id],
            "rungs": [
                {
                    "temp": rung.temp,
                    "bank": rung.bank_cents / PAYOUT_SCALE,
                    "prob": bank_probs[f"bank{i + 1}"],
                }
                for i, rung in enumerate(rungs)
            ],
            "tiers": [
                {
                    "tier": c.name,
                    "payout": c.pay_cents / PAYOUT_SCALE,
                    "prob": float(c.prob),
                }
                for c in classes
                if c.kind == "tier"
            ],
            "bustProb": float(next(c.prob for c in classes if c.kind == "bust")),
            "anyPayoutProb": m["any_prob"],
            "profitProb": m["profit_prob"],
            "maxWin": m["max_win"],
            "std": m["std"],
        }
    return payload


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

FRONTEND_LADDERS = (
    Path(__file__).resolve().parents[1]
    / "web-sdk/apps/overheat-rig/src/game/ladders.json"
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate OVERHEAT math files")
    parser.add_argument("--sims", type=int, default=SIMS_PER_MODE, help="simulations per mode")
    parser.add_argument("--modes", default=",".join(RIGS), help="comma-separated rig ids")
    parser.add_argument("--no-compress", action="store_true", help="write plain .jsonl books")
    parser.add_argument("--out", default="math-out", help="output root directory")
    parser.add_argument("--seed", type=int, default=BASE_SEED, help="base RNG seed")
    parser.add_argument(
        "--no-frontend", action="store_true",
        help="skip writing ladders.json into the frontend source tree",
    )
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

    ladders = ladder_payload(mode_infos)
    ladders_text = json.dumps(ladders, indent=1) + "\n"
    (out_root / "configs" / "ladders.json").write_text(ladders_text)
    if not args.no_frontend and set(modes) == set(RIGS):
        FRONTEND_LADDERS.write_text(ladders_text)
        print(f"Ladder tables written to {FRONTEND_LADDERS}")
    print(f"Done. Publish files in {out_publish}/, configs in {out_root}/configs/")


if __name__ == "__main__":
    main()
