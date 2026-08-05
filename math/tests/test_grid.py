"""Grid builder unit tests (§6.1)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config_v4 import MODE_ORDER, mode_config
from grid import build_grid, round_multiplier, teaser_point


def test_rounding_rules():
    assert round_multiplier(1.234) == 1.23
    assert round_multiplier(12.34) == 12.3
    assert round_multiplier(123.4) == 123
    assert round_multiplier(0.02) == 0.02


def test_teaser_points():
    expected = {
        "idle": 17.0,
        "eco": 21.3,
        "standard": 25.5,
        "boost": 34.0,
        "overclock": 42.5,
        "nitro": 63.8,
        "furnace": 85.0,
        "inferno": 128.0,
        "meltdown": 213.0,
        "reactor": 425.0,
        "plasma": 2125.0,
    }
    for name, want in expected.items():
        got = teaser_point(mode_config(name))
        assert got == want, f"{name}: teaser {got} != {want}"


def test_grid_includes_anchors_and_max():
    for name in MODE_ORDER:
        cfg = mode_config(name)
        g = build_grid(cfg)
        assert g[0] >= 0.02
        assert g[-1] == cfg.max_win or abs(g[-1] - cfg.max_win) < 1e-9
        assert teaser_point(cfg) in g
        assert 1.0 in g
        assert len(g) == len(set(g))
        # expected sizes roughly: IDLE ~90, PLASMA ~175 — soft check vs min_unique floor
        assert len(g) >= cfg.min_unique * 0.7, f"{name}: grid too small {len(g)}"


def test_no_sub_002():
    for name in MODE_ORDER:
        g = build_grid(mode_config(name))
        assert all(x >= 0.02 - 1e-12 for x in g)


if __name__ == "__main__":
    test_rounding_rules()
    test_teaser_points()
    test_grid_includes_anchors_and_max()
    test_no_sub_002()
    print("test_grid: OK")
