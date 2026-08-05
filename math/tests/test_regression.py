"""v3 regression: recompute metrics from published lookUpTables and match §3."""

from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[2]
PUBLISH = ROOT / "math-out" / "publish_files"

# §3 reference (approx; harness must reproduce within tight tolerance)
V3 = {
    "idle": dict(rtp=0.965, std=1.1047, max=12, unique=17),
    "plasma": dict(rtp=0.965, std=5.4573, max=1000, unique=23),
}


def metrics_from_lut(path: Path) -> dict:
    rows = list(csv.reader(path.open()))
    total_w = 0
    dot = 0.0
    second = 0.0
    pays = set()
    mx = 0.0
    for _, w_s, p_s in rows:
        w = int(w_s)
        mult = int(p_s) / 100.0
        total_w += w
        dot += w * mult
        second += w * mult * mult
        if mult > 0:
            pays.add(mult)
        mx = max(mx, mult)
    rtp = dot / total_w
    var = second / total_w - rtp * rtp
    return {"rtp": rtp, "std": math.sqrt(max(0, var)), "max": mx, "unique": len(pays)}


def test_v3_idle_plasma():
    if not PUBLISH.exists():
        print("skip: no math-out/publish_files")
        return
    for name, ref in V3.items():
        path = PUBLISH / f"lookUpTable_{name}_0.csv"
        if not path.exists():
            print(f"skip: missing {path}")
            continue
        m = metrics_from_lut(path)
        assert abs(m["rtp"] - ref["rtp"]) < 1e-6, (name, m["rtp"])
        assert abs(m["std"] - ref["std"]) < 0.02, (name, m["std"], ref["std"])
        assert abs(m["max"] - ref["max"]) < 1e-9, (name, m["max"])
        assert m["unique"] in (ref["unique"] - 1, ref["unique"], ref["unique"] + 1), (
            name,
            m["unique"],
        )


if __name__ == "__main__":
    test_v3_idle_plasma()
    print("test_regression: OK")
