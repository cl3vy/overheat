"""Ladder invariant tests (I1–I7) over freshly generated metrics."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config_v4 import MODE_ORDER, RTP_TARGET, mode_config
from generate_books import generate_mode


def test_ladder_invariants():
    metrics = {}
    for name in MODE_ORDER:
        _, meta = generate_mode(mode_config(name))
        metrics[name] = meta
        assert abs(meta["rtp"] - RTP_TARGET) <= 1e-6

    ordered = [metrics[n] for n in MODE_ORDER]
    for a, b, na, nb in zip(ordered, ordered[1:], MODE_ORDER, MODE_ORDER[1:]):
        assert a["hit_rate"] > b["hit_rate"], f"I2 {na}->{nb}"
        assert a["zero_rate"] < b["zero_rate"], f"I3 {na}->{nb}"
        assert a["std"] < b["std"], f"I4 {na}->{nb}"
        assert a["break_even"] < b["break_even"], f"I5 {na}->{nb}"
        assert a["max"] < b["max"], f"I6 {na}->{nb}"
        assert a["etl40"] <= b["etl40"] + 1e-9, f"I7 {na}->{nb}"


if __name__ == "__main__":
    test_ladder_invariants()
    print("test_invariants: OK")
