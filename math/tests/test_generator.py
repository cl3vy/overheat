"""Generator unit smoke tests."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config_v4 import MODE_ORDER, RTP_TARGET, TOTAL_WEIGHT, assert_budget_sums, mode_config
from generate_books import generate_mode
from grid import build_grid


def test_budget_sums():
    assert_budget_sums()


def test_generate_idle_rtp_and_weight():
    cfg = mode_config("idle")
    outcomes, meta = generate_mode(cfg)
    assert abs(meta["rtp"] - RTP_TARGET) <= 1e-6
    assert sum(o.weight for o in outcomes) == TOTAL_WEIGHT
    assert meta["max"] == cfg.max_win
    assert meta["unique"] >= cfg.min_unique * 0.9  # allow slight dust loss


def test_all_modes_rtp():
    for name in MODE_ORDER:
        cfg = mode_config(name)
        _, meta = generate_mode(cfg)
        assert abs(meta["rtp"] - RTP_TARGET) <= 1e-6, name
        assert meta["max"] == cfg.max_win, name


if __name__ == "__main__":
    test_budget_sums()
    test_generate_idle_rtp_and_weight()
    test_all_modes_rtp()
    print("test_generator: OK")
