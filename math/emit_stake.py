"""Emit v4 weight tables into Stake publish format (lookUpTable + books + config).

Mirrors the v3 pipeline shape (§11.4) while preserving W=1e8 weights exactly.
Display crash temperature is a pure function of the multiplier (§5 / §10).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import zstandard

from config_v4 import MODE_ORDER, MODE_TARGET, TOTAL_WEIGHT, VERSION, mode_config
from generate_books import Outcome

HERE = Path(__file__).resolve().parent
BOOKS_DIR = HERE / "books"
ROOT = HERE.parent
OUT = ROOT / "math-out"


def load_outcomes(path: Path) -> list[Outcome]:
    from generate_books import Outcome as O

    rows: list[O] = []
    with path.open() as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append(O(float(row["multiplier"]), int(row["weight"])))
    return rows


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def classify_tier(mult: float, target: float) -> str:
    if mult < target - 1e-9:
        return "bust" if mult <= 0 else "bank"
    ratio = mult / target
    if ratio >= 9.5:
        return "golden"
    if ratio >= 2.5:
        return "critical"
    if ratio >= 1.35:
        return "overdrive"
    return "clean"


def build_book(mode: str, oid: int, mult: float, target: float) -> dict:
    """Deterministic book: crashTemp == payout multiplier (or ~1.0 on bust)."""
    pm = int(round(mult * 100))
    tier = classify_tier(mult, target)
    events: list[dict] = [
        {"index": 0, "type": "boot", "rigTier": mode, "targetTemp": target, "hashrate": 400},
    ]
    if mult <= 0:
        events.append({"index": 1, "type": "heat", "crashTemp": 1.0})
        events.append({"index": 2, "type": "meltdown", "crashTemp": 1.0, "amount": 0})
    elif mult < target:
        events.append({"index": 1, "type": "heat", "crashTemp": mult})
        events.append({"index": 2, "type": "meltdown", "crashTemp": mult, "amount": pm})
    else:
        events.append({"index": 1, "type": "heat", "crashTemp": mult})
        events.append(
            {
                "index": 2,
                "type": "shutdown",
                "bankedAt": mult,
                "couldHaveReached": mult,
                "tier": tier if tier in ("clean", "overdrive", "critical", "golden") else "clean",
            }
        )
    events.append({"index": len(events), "type": "setTotalWin", "amount": pm})
    events.append({"index": len(events), "type": "finalWin", "amount": pm})
    return {
        "id": oid,
        "payoutMultiplier": pm,
        "events": events,
        "criteria": tier if tier != "bank" else "bank",
    }


def emit_mode(mode: str, outcomes: list[Outcome], publish: Path) -> dict:
    target = MODE_TARGET[mode]
    # one LUT/book row per outcome (dense table, not 100k sims)
    lut_path = publish / f"lookUpTable_{mode}_0.csv"
    books_path = publish / f"books_{mode}.jsonl.zst"

    with lut_path.open("w", newline="") as f:
        w = csv.writer(f)
        for i, o in enumerate(outcomes):
            w.writerow([i, o.weight, int(round(o.multiplier * 100))])

    raw = "\n".join(
        json.dumps(build_book(mode, i, o.multiplier, target), separators=(",", ":"))
        for i, o in enumerate(outcomes)
    ) + "\n"
    cctx = zstandard.ZstdCompressor(level=10)
    books_path.write_bytes(cctx.compress(raw.encode()))

    cfg = mode_config(mode)
    return {
        "name": mode,
        "cost": 1.0,
        "events": books_path.name,
        "weights": lut_path.name,
        "bookLength": len(outcomes),
        "maxWin": cfg.max_win,
        "weightsSha256": sha256_file(lut_path),
        "booksSha256": sha256_file(books_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()

    publish = args.out / "publish_files"
    configs = args.out / "configs"
    publish.mkdir(parents=True, exist_ok=True)
    configs.mkdir(parents=True, exist_ok=True)

    index = []
    shelf = []
    for mode in MODE_ORDER:
        path = BOOKS_DIR / f"{mode}_v4.csv"
        if not path.exists():
            raise SystemExit(f"missing {path} — run generate_books.py first")
        outcomes = load_outcomes(path)
        assert sum(o.weight for o in outcomes) == TOTAL_WEIGHT
        meta = emit_mode(mode, outcomes, publish)
        index.append(
            {
                "name": meta["name"],
                "cost": 1.0,
                "events": meta["events"],
                "weights": meta["weights"],
            }
        )
        shelf.append(
            {
                "mode": mode,
                "cost": 1.0,
                "bookLength": meta["bookLength"],
                "maxWin": meta["maxWin"],
                "weightsFile": meta["weights"],
                "weightsSha256": meta["weightsSha256"],
                "booksFile": meta["events"],
                "booksSha256": meta["booksSha256"],
                "autoEndRoundDisabled": True,
            }
        )
        print(f"emitted {mode}: {meta['bookLength']} outcomes, max={meta['maxWin']}x")

    (publish / "index.json").write_text(
        json.dumps({"modes": index}, indent=2) + "\n"
    )
    config = {
        "workingName": "overheat_rig",
        "gameID": "overheat_rig",
        "rtp": 0.965,
        "mathVersion": VERSION,
        "totalWeight": TOTAL_WEIGHT,
        "betDenomination": 1000,
        "bookShelfConfig": shelf,
    }
    (configs / "config.json").write_text(json.dumps(config, indent=2) + "\n")

    fe = {
        "betModes": [
            {"key": m, "costMultiplier": 1.0, "maxWin": mode_config(m).max_win} for m in MODE_ORDER
        ]
    }
    (configs / "config_fe_overheat_rig.json").write_text(json.dumps(fe, indent=2) + "\n")
    print(f"wrote publish package under {args.out}")


if __name__ == "__main__":
    main()
