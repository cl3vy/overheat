"""Outcome grid builder for Overheat math v4 (§6.1)."""

from __future__ import annotations

import math

from config_v4 import AnchorSet, ModeConfig

# Near-unity cluster: spreads stake-return mass so IDLE (and every mode) does
# not collapse wins onto a single 1.00x point.
NEAR_UNITY_CLUSTER = (0.90, 0.95, 1.00, 1.05, 1.10, 1.15, 1.20, 1.25)


def round_multiplier(x: float) -> float:
    """Rounding rule §6.1 / §6.2: ≤2dp below 10, ≤1dp in [10,100), integers ≥100.

    Half-up for .5 ties (spec teasers: 127.5→128, 212.5→213), not banker's.
    """
    if x < 10:
        return round(x + 1e-12, 2)
    if x < 100:
        return math.floor(x * 10 + 0.5 + 1e-12) / 10
    return float(math.floor(x + 0.5 + 1e-12))


def geometric_grid(max_win: float, *, ratio: float = 1.06, m_min: float = 0.10) -> list[float]:
    """Geometric sequence from m_min to just below max, then append max."""
    values: list[float] = []
    m = m_min
    while m < max_win - 1e-12:
        values.append(round_multiplier(m))
        m *= ratio
    values.append(round_multiplier(max_win))
    return values


def build_grid(cfg: ModeConfig) -> list[float]:
    """Non-zero grid for a mode (sorted, deduped). Zero is added by the generator."""
    raw = geometric_grid(cfg.max_win)
    forced = [a for a in AnchorSet if a <= cfg.max_win + 1e-12]
    teaser = round_multiplier(0.85 * cfg.max_win)
    tiny = [0.02, 0.05, 0.08]
    cluster = [c for c in NEAR_UNITY_CLUSTER if c <= cfg.max_win + 1e-12]
    merged = {
        round_multiplier(v) for v in (*raw, *forced, teaser, *tiny, *cluster, cfg.max_win)
    }
    cleaned = sorted(v for v in merged if v >= 0.02 - 1e-12)
    max_r = round_multiplier(cfg.max_win)
    if cleaned[-1] != max_r:
        cleaned = [v for v in cleaned if v < max_r] + [max_r]
    return cleaned


def teaser_point(cfg: ModeConfig) -> float:
    return round_multiplier(0.85 * cfg.max_win)


def cluster_neighbors(x: float, grid: list[float] | None = None) -> list[float]:
    """NEAR_UNITY_CLUSTER members within ±0.15 of x (optionally intersected with grid)."""
    members = [c for c in NEAR_UNITY_CLUSTER if abs(c - x) <= 0.15 + 1e-12]
    if grid is not None:
        gset = set(grid)
        members = [c for c in members if c in gset]
    return members
