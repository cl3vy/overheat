"""Weight generation algorithm for Overheat math v4 (§7).

Deterministic. No RNG. Writes books/<mode>_v4.csv and manifest.json.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

from config_v4 import (
    RTP_TARGET,
    TOTAL_WEIGHT,
    VERSION,
    BandBudget,
    ModeConfig,
    all_mode_configs,
)
from grid import build_grid, cluster_neighbors, teaser_point, NEAR_UNITY_CLUSTER

HERE = Path(__file__).resolve().parent
BOOKS_DIR = HERE / "books"


@dataclass
class Outcome:
    multiplier: float
    weight: int


def _points_in_band(grid: list[float], band: BandBudget) -> list[float]:
    return [x for x in grid if band.contains(x)]


def band_owns(band: BandBudget, x: float, cfg: ModeConfig) -> bool:
    """Band membership for RTP shares. Top half-open bands still own max_win."""
    if band.contains(x):
        return True
    top = cfg.band_budgets[-1]
    if band is top and abs(x - cfg.max_win) < 1e-12:
        return True
    return False


def _etl40_target(cfg: ModeConfig) -> float:
    """Generate to 98% of §4.2 cap so integer rounding cannot breach the cap."""
    return cfg.etl40_cap * 0.98


def _band_profile(xs: list[float], budget_ev: float, beta: float) -> dict[float, float]:
    """Point probabilities for a band under power-law profile (§7.2)."""
    if not xs or budget_ev <= 0:
        return {}
    us = [x ** (-beta) for x in xs]
    contrib = [u * x for u, x in zip(us, xs)]
    total = sum(contrib)
    if total <= 0:
        return {}
    return {x: ((c / total) * budget_ev) / x for x, c in zip(xs, contrib)}


def _mean_of_probs(probs: dict[float, float]) -> float:
    p_sum = sum(probs.values())
    if p_sum <= 0:
        return 0.0
    return sum(p * x for x, p in probs.items()) / p_sum


def _bisect_beta_for_mean(
    xs: list[float],
    budget_ev: float,
    target_mean: float,
    *,
    lo: float = 0.3,
    hi: float = 3.0,
    steps: int = 48,
) -> float:
    """Higher beta → lower mean. lo/hi may go negative for high-edge mass."""
    if not xs or budget_ev <= 0:
        return 1.5
    best = 1.5
    for _ in range(steps):
        mid = (lo + hi) / 2
        mean = _mean_of_probs(_band_profile(xs, budget_ev, mid))
        best = mid
        if mean > target_mean:
            lo = mid
        else:
            hi = mid
    return best


def _bisect_beta_for_prob(
    xs: list[float],
    budget_ev: float,
    target_p: float,
    *,
    lo: float = 0.3,
    hi: float = 3.0,
    steps: int = 48,
) -> float:
    """Hit a target band probability. Higher beta → higher P (lower mean)."""
    if not xs or budget_ev <= 0 or target_p <= 0:
        return 1.5
    target_mean = budget_ev / target_p
    mean_lo = _mean_of_probs(_band_profile(xs, budget_ev, hi))  # high beta → low mean
    mean_hi = _mean_of_probs(_band_profile(xs, budget_ev, lo))
    target_mean = min(max(target_mean, mean_lo), mean_hi)
    return _bisect_beta_for_mean(xs, budget_ev, target_mean, lo=lo, hi=hi, steps=steps)


def _renorm_band_ev(probs: dict[float, float], xs: list[float], budget_ev: float) -> None:
    if not xs:
        return
    ev = sum(probs.get(x, 0.0) * x for x in xs)
    if ev <= 0:
        return
    scale = budget_ev / ev
    for x in xs:
        if x in probs:
            probs[x] *= scale


def _apply_teaser_and_max(
    probs: dict[float, float], cfg: ModeConfig, top: BandBudget
) -> None:
    """Place teaser + max, then put remaining top-band EV on [lo, max).

    Max stays clamped so renorm cannot pile ETL mass on the endpoint.
    """
    teaser = teaser_point(cfg)
    mx = cfg.max_win
    if cfg.name in ("reactor", "plasma"):
        p_lo, p_hi = 1 / 3_000_000, 1 / 300_000
    else:
        p_lo, p_hi = 1 / 3_000_000, 1 / 100_000
    # Prefer geometric interior of the top band (exclude endpoint max)
    body = [x for x in probs if top.contains(x) and abs(x - mx) > 1e-12]
    if not body:
        body = _points_in_band(
            sorted({x for x in probs} | {teaser}),
            top,
        )
        body = [x for x in body if abs(x - mx) > 1e-12]
    if mx not in probs:
        probs[mx] = p_lo
    probs[mx] = min(max(probs.get(mx, 0.0), p_lo), p_hi)
    if teaser not in probs:
        probs[teaser] = 0.0
    probs[teaser] = 2.5 * probs[mx]
    # Ensure teaser sits in the body set for renorm when it belongs to top
    if top.contains(teaser) and teaser not in body:
        body.append(teaser)
    max_ev = probs[mx] * mx
    remain = top.budget_ev - max_ev
    if remain <= 0 or not body:
        # Degenerate: put a floor on max and accept residual elsewhere
        probs[mx] = min(p_hi, top.budget_ev / mx)
        probs[teaser] = 2.5 * probs[mx]
        return
    _renorm_band_ev(probs, body, remain)
    # Re-assert clamp after any prior mass on max
    probs[mx] = min(max(probs[mx], p_lo), p_hi)
    probs[teaser] = 2.5 * probs[mx]


def _band_of(x: float, bands: list[BandBudget]) -> BandBudget | None:
    for b in bands:
        if b.contains(x):
            return b
    return None


def _spread_heavy_via_cluster(
    probs: dict[float, float],
    bands: list[BandBudget],
    grid: list[float],
    *,
    cap_frac: float = 0.06,
) -> None:
    """Smoothness: any point above cap_frac of non-zero p has its excess peeled
    evenly onto NEAR_UNITY_CLUSTER members within ±0.15 (expanded with same-band
    grid points until the share fits). Band EV is re-solved afterward.
    Applies to every mode including IDLE.
    """
    gset = set(grid)
    ordered_grid = sorted(gset)

    def _pack_for(heavy: float, mass: float, cap: float) -> list[float]:
        raw_cluster = set(cluster_neighbors(heavy, grid))
        raw_cluster.add(heavy)
        if heavy >= 1.0 - 1e-12:
            pack = {c for c in raw_cluster if c >= 1.0 - 1e-12} or set(raw_cluster)
        else:
            pack = {c for c in raw_cluster if c < 1.0 - 1e-12} or set(raw_cluster)
        band = _band_of(heavy, bands)
        # Need enough members that each can hold ≤ cap after receiving excess
        # excess = mass - cap is shared across |pack|-1 others, but we also
        # want the whole pack eventually flat — expand until mass/|pack| ≤ cap.
        guard = 0
        while mass / max(len(pack), 1) > cap + 1e-15 and guard < 60:
            guard += 1
            candidates = [
                x
                for x in ordered_grid
                if x not in pack
                and x > 0
                and (band is None or band.contains(x))
                and (
                    (heavy >= 1.0 - 1e-12 and x >= 1.0 - 1e-12)
                    or (heavy < 1.0 - 1e-12 and x < 1.0 - 1e-12)
                    or band is not None
                )
            ]
            if not candidates:
                candidates = [x for x in ordered_grid if x not in pack and x > 0]
            if not candidates:
                break
            pack.add(min(candidates, key=lambda x: (abs(x - heavy), x)))
        return sorted(pack)

    for _ in range(200):
        nz = sum(p for x, p in probs.items() if x > 0)
        if nz <= 0:
            return
        cap = cap_frac * nz
        heavy = next(
            (x for x in sorted(probs) if x > 0 and probs[x] > cap + 1e-15),
            None,
        )
        if heavy is None:
            break
        mass = probs[heavy]
        pack_list = _pack_for(heavy, mass, cap)
        if len(pack_list) < 2:
            ordered = sorted(x for x in probs if x > 0)
            i = ordered.index(heavy)
            left = ordered[i - 1] if i > 0 else None
            right = ordered[i + 1] if i + 1 < len(ordered) else None
            excess = mass - cap
            probs[heavy] = cap
            side = excess / (1 if left is None or right is None else 2)
            if left is not None:
                probs[left] = probs.get(left, 0.0) + side
            if right is not None:
                probs[right] = probs.get(right, 0.0) + (excess - side if left else excess)
            continue

        # Peel only the excess above the cap; leave a full share on heavy
        excess = mass - cap
        probs[heavy] = cap
        others = [c for c in pack_list if c != heavy]
        share = excess / len(others)
        for c in others:
            probs[c] = probs.get(c, 0.0) + share

    # Re-solve band EV, then peel again if renorm re-concentrated
    for _ in range(40):
        for band in bands:
            xs = [x for x in probs if band.contains(x)]
            _renorm_band_ev(probs, xs, band.budget_ev)
        nz = sum(p for x, p in probs.items() if x > 0)
        if nz <= 0:
            return
        cap = cap_frac * nz
        heavy = next(
            (x for x in sorted(probs) if x > 0 and probs[x] > cap + 1e-15),
            None,
        )
        if heavy is None:
            return
        mass = probs[heavy]
        pack_list = _pack_for(heavy, mass, cap)
        others = [c for c in pack_list if c != heavy]
        if not others:
            probs[heavy] = cap
            continue
        excess = mass - cap
        probs[heavy] = cap
        share = excess / len(others)
        for c in others:
            probs[c] = probs.get(c, 0.0) + share


def _raise_hit_rate_in_bands(
    probs: dict[float, float],
    bands: list[BandBudget],
    grid: list[float],
    p_nz_target: float,
    teaser: float,
    max_win: float,
) -> None:
    """Raise P_nz only inside flex [1, 2) — locked high bands stay untouched."""
    flex = [b for b in bands if abs(b.lo - 1.0) < 1e-12 and b.hi <= 2.0 + 1e-12]
    if not flex:
        flex = [b for b in bands if b.lo >= 1.0 - 1e-12 and b.hi <= 2.0 + 1e-12]
    for _ in range(200):
        deficit = p_nz_target - sum(probs.values())
        if deficit <= 1e-8:
            return
        moved = False
        for band in flex:
            xs = sorted(x for x in probs if band.contains(x) and x != teaser)
            if len(xs) < 2:
                continue
            donors = [
                x
                for x in xs
                if probs.get(x, 0.0) > 1e-15 and abs(x - max_win) > 1e-12
            ]
            if not donors:
                continue
            high = max(donors)
            low = min(xs)
            if high <= low + 1e-12:
                continue
            gain_per_dp = high / low - 1.0
            if gain_per_dp <= 1e-15:
                continue
            dp = min(probs[high], deficit / gain_per_dp)
            if dp <= 1e-15:
                continue
            dq = dp * high / low
            probs[high] -= dp
            probs[low] = probs.get(low, 0.0) + dq
            moved = True
            break
        if not moved:
            return


def _enforce_nonincreasing(probs: dict[float, float], bands: list[BandBudget], teaser: float) -> None:
    """Within each band, weights non-increasing as multiplier rises (except teaser)."""
    for band in bands:
        xs = sorted(x for x in probs if band.contains(x) and x != teaser)
        for i in range(1, len(xs)):
            if probs[xs[i]] > probs[xs[i - 1]]:
                excess = probs[xs[i]] - probs[xs[i - 1]]
                probs[xs[i]] -= excess
                probs[xs[i - 1]] += excess


def _restore_locked(
    probs: dict[float, float], locked_snapshot: dict[float, float]
) -> None:
    """Re-apply locked high-band probabilities after flex/spread passes."""
    for x, p in locked_snapshot.items():
        probs[x] = p


def _build_probs(cfg: ModeConfig, grid: list[float], beta_tail: float) -> dict[float, float]:
    """Fill high bands first and lock them; [1,2) + recovery absorb hit/BE remainder."""
    bands = cfg.band_budgets
    z = cfg.zero_rate
    p_nz_target = 1.0 - z
    p_sub_target = max(cfg.break_even - z, 0.01)
    teaser = teaser_point(cfg)
    probs: dict[float, float] = {}

    tiny = bands[0]
    recovery = bands[1]
    # Flex near-unity absorbs residual hit-rate; everything lo>=2 is locked hard.
    flex = next((b for b in bands if abs(b.lo - 1.0) < 1e-12), bands[2])
    locked = [b for b in bands if b.lo >= 2.0 - 1e-12]
    locked_hi_first = sorted(locked, key=lambda b: -b.lo)
    top = bands[-1]

    # --- tiny (0, 0.1) ---
    tiny_xs = [x for x in (0.02, 0.05, 0.08) if tiny.contains(x)]
    tiny_probs = _band_profile(tiny_xs, tiny.budget_ev, 1.0)
    probs.update(tiny_probs)
    tiny_p = sum(tiny_probs.values())

    # --- locked high bands: mode max downward ---
    for band in locked_hi_first:
        xs = _points_in_band(grid, band)
        # Body excludes max endpoint so ETL/cap mass spreads through the interior
        body = [x for x in xs if abs(x - cfg.max_win) > 1e-12]
        if band is top or band.lo >= 20:
            beta = beta_tail
        elif band.lo >= 5:
            beta = 1.2
        else:
            beta = 1.5
        for x in list(probs):
            if band_owns(band, x, cfg):
                probs.pop(x)
        if band is top:
            fill_xs = body if body else xs
            # Reserve a slice of EV for clamped max; put the rest on the body
            if cfg.name in ("reactor", "plasma"):
                p_hi = 1 / 300_000
            else:
                p_hi = 1 / 100_000
            max_p = min(p_hi, top.budget_ev / max(cfg.max_win, 1e-9) * 0.5)
            max_ev = max_p * cfg.max_win
            body_ev = max(top.budget_ev - max_ev, top.budget_ev * 0.85)
            probs.update(_band_profile(fill_xs, body_ev, beta))
            probs[cfg.max_win] = max_p
            _apply_teaser_and_max(probs, cfg, top)
        else:
            probs.update(_band_profile(xs, band.budget_ev, beta))
        xs_renorm = [x for x in probs if band_owns(band, x, cfg)]
        if band is top:
            # Keep max clamped; renorm body only
            body_r = [x for x in xs_renorm if abs(x - cfg.max_win) > 1e-12]
            max_ev = probs.get(cfg.max_win, 0.0) * cfg.max_win
            _renorm_band_ev(probs, body_r, max(band.budget_ev - max_ev, 1e-15))
        else:
            _renorm_band_ev(probs, xs_renorm, band.budget_ev)

    locked_snapshot = {
        x: probs[x]
        for x in list(probs)
        if any(band_owns(b, x, cfg) for b in locked)
    }

    # --- recovery [0.1, 1) for break-even ---
    rec_xs = _points_in_band(grid, recovery)
    p_rec = max(p_sub_target - tiny_p, 0.005)
    beta_rec = _bisect_beta_for_prob(
        rec_xs, recovery.budget_ev, p_rec, lo=-3.0, hi=3.0
    )
    for x in list(probs):
        if recovery.contains(x):
            probs.pop(x)
    probs.update(_band_profile(rec_xs, recovery.budget_ev, beta_rec))

    # --- flex [1, 2): absorb remaining P_nz with exact band EV ---
    flex_xs = _points_in_band(grid, flex)
    # Include near-unity cluster members that belong to flex
    flex_xs = sorted(set(flex_xs) | {c for c in NEAR_UNITY_CLUSTER if flex.contains(c)})

    def _flex_with_beta(beta: float) -> dict[float, float]:
        out = dict(locked_snapshot)
        # tiny + recovery
        for x, p in probs.items():
            if tiny.contains(x) or recovery.contains(x):
                out[x] = p
        out.update(_band_profile(flex_xs, flex.budget_ev, beta))
        return out

    lo_b, hi_b = 0.3, 3.0
    best_probs = _flex_with_beta(1.5)
    for _ in range(48):
        mid = (lo_b + hi_b) / 2
        cand = _flex_with_beta(mid)
        best_probs = cand
        if sum(cand.values()) > p_nz_target:
            hi_b = mid
        else:
            lo_b = mid
    probs = best_probs
    _restore_locked(probs, locked_snapshot)
    _renorm_band_ev(
        probs, [x for x in probs if flex.contains(x)], flex.budget_ev
    )
    for band in locked:
        xs = [x for x in probs if band_owns(band, x, cfg)]
        if band is top:
            body_r = [x for x in xs if abs(x - cfg.max_win) > 1e-12]
            max_ev = probs.get(cfg.max_win, 0.0) * cfg.max_win
            _renorm_band_ev(probs, body_r, max(band.budget_ev - max_ev, 1e-15))
        else:
            _renorm_band_ev(probs, xs, band.budget_ev)

    locked_snapshot = {
        x: probs[x]
        for x in list(probs)
        if any(band_owns(b, x, cfg) for b in locked)
    }

    _enforce_nonincreasing(probs, [b for b in bands if b.lo >= 1.0], teaser)
    _restore_locked(probs, locked_snapshot)
    for band in locked:
        xs = [x for x in probs if band_owns(band, x, cfg)]
        if band is top:
            body_r = [x for x in xs if abs(x - cfg.max_win) > 1e-12]
            max_ev = probs.get(cfg.max_win, 0.0) * cfg.max_win
            _renorm_band_ev(probs, body_r, max(band.budget_ev - max_ev, 1e-15))
        else:
            _renorm_band_ev(probs, xs, band.budget_ev)
    locked_snapshot = {
        x: probs[x]
        for x in list(probs)
        if any(band_owns(b, x, cfg) for b in locked)
    }

    _spread_heavy_via_cluster(probs, bands, grid)
    _restore_locked(probs, locked_snapshot)
    # Re-lock band EVs after cluster renorm may have scaled locked points
    for band in locked:
        xs = [x for x in probs if band_owns(band, x, cfg)]
        if band is top:
            body_r = [x for x in xs if abs(x - cfg.max_win) > 1e-12]
            max_ev = probs.get(cfg.max_win, 0.0) * cfg.max_win
            _renorm_band_ev(probs, body_r, max(band.budget_ev - max_ev, 1e-15))
            # Keep max at restored snapshot level when possible
            if cfg.max_win in locked_snapshot:
                probs[cfg.max_win] = locked_snapshot[cfg.max_win]
        else:
            _renorm_band_ev(probs, xs, band.budget_ev)
    locked_snapshot = {
        x: probs[x]
        for x in list(probs)
        if any(band_owns(b, x, cfg) for b in locked)
    }

    # Re-hit recovery for break-even (flex still adjustable)
    rec_xs = [x for x in probs if recovery.contains(x)]
    rec_xs = sorted(set(rec_xs) | {c for c in NEAR_UNITY_CLUSTER if recovery.contains(c)})
    if rec_xs:
        for x in list(rec_xs):
            probs.pop(x, None)
        probs.update(
            _band_profile(
                rec_xs,
                recovery.budget_ev,
                _bisect_beta_for_prob(rec_xs, recovery.budget_ev, p_rec, lo=-3.0, hi=3.0),
            )
        )
    _restore_locked(probs, locked_snapshot)

    # Final flex P_nz adjust without touching locked highs
    flex_xs = sorted(
        {x for x in probs if flex.contains(x)}
        | {c for c in NEAR_UNITY_CLUSTER if flex.contains(c)}
    )

    def _refit_flex(beta: float) -> dict[float, float]:
        out = {x: p for x, p in probs.items() if not flex.contains(x)}
        out.update(_band_profile(flex_xs, flex.budget_ev, beta))
        _restore_locked(out, locked_snapshot)
        return out

    lo_b, hi_b = 0.3, 3.0
    best_probs = dict(probs)
    for _ in range(40):
        mid = (lo_b + hi_b) / 2
        cand = _refit_flex(mid)
        best_probs = cand
        if sum(cand.values()) > p_nz_target:
            hi_b = mid
        else:
            lo_b = mid
    probs = best_probs
    _restore_locked(probs, locked_snapshot)
    _renorm_band_ev(probs, [x for x in probs if flex.contains(x)], flex.budget_ev)

    _raise_hit_rate_in_bands(probs, bands, grid, p_nz_target, teaser, cfg.max_win)
    _restore_locked(probs, locked_snapshot)
    _spread_heavy_via_cluster(probs, bands, grid)
    _restore_locked(probs, locked_snapshot)
    for band in locked:
        xs = [x for x in probs if band_owns(band, x, cfg)]
        if band is top:
            body_r = [x for x in xs if abs(x - cfg.max_win) > 1e-12]
            max_ev = probs.get(cfg.max_win, 0.0) * cfg.max_win
            _renorm_band_ev(probs, body_r, max(band.budget_ev - max_ev, 1e-15))
            if cfg.max_win in locked_snapshot:
                probs[cfg.max_win] = locked_snapshot[cfg.max_win]
        else:
            _renorm_band_ev(probs, xs, band.budget_ev)

    # Ensure every budgeted locked band has mass (hard requirement)
    for band in locked:
        if band.budget_pts <= 0:
            continue
        xs = [x for x in probs if band_owns(band, x, cfg) and probs.get(x, 0.0) > 0]
        if xs:
            continue
        # Seed teaser/max or mid-band point
        seed = teaser if band is top else (band.lo + min(band.hi, cfg.max_win)) / 2
        if band is top:
            seed = teaser_point(cfg)
        grid_seed = min(
            (_points_in_band(grid, band) or [seed]),
            key=lambda x: abs(x - seed),
        )
        probs[grid_seed] = max(probs.get(grid_seed, 0.0), band.budget_ev / max(grid_seed, 1e-9))
        if band is top:
            probs.setdefault(cfg.max_win, 1 / 1_000_000)
            _apply_teaser_and_max(probs, cfg, top)
        _renorm_band_ev(
            probs,
            [x for x in probs if band_owns(band, x, cfg) and abs(x - cfg.max_win) > 1e-12]
            if band is top
            else [x for x in probs if band_owns(band, x, cfg)],
            band.budget_ev - (probs.get(cfg.max_win, 0.0) * cfg.max_win if band is top else 0.0)
            if band is top
            else band.budget_ev,
        )

    return probs


def _to_integer_weights(probs: dict[float, float], cfg: ModeConfig) -> list[Outcome]:
    """Integerize: lock §4.3 band EVs; shape flex/recovery for hit & BE."""
    W = TOTAL_WEIGHT
    teaser = teaser_point(cfg)
    locked = [b for b in cfg.band_budgets if b.lo >= 2.0 - 1e-12]
    top = cfg.band_budgets[-1]
    tiny = cfg.band_budgets[0]
    recovery = cfg.band_budgets[1]
    flex = next(b for b in cfg.band_budgets if abs(b.lo - 1.0) < 1e-12)
    etl_cap = _etl40_target(cfg)
    std_lo, std_hi = cfg.std_range
    target_std = (std_lo + std_hi) / 2.0
    flex_grid = [round(1.0 + 0.02 * i, 2) for i in range(50)]  # 1.00..1.98
    flex_grid = [x for x in flex_grid if x < 2.0 - 1e-12]
    rec_grid = [round(0.10 + 0.025 * i, 3) for i in range(37)]  # 0.10..1.00
    rec_grid = [x for x in rec_grid if recovery.contains(x)]
    grid_all = build_grid(cfg)

    survivors: dict[float, int] = {}

    def _band_pts(band: BandBudget) -> float:
        return sum(survivors.get(x, 0) * x for x in survivors if band_owns(band, x, cfg)) / W * 100.0

    def _band_p(band: BandBudget) -> float:
        return sum(survivors.get(x, 0) for x in survivors if band_owns(band, x, cfg)) / W

    def _clear_band(band: BandBudget) -> None:
        for x in [x for x in survivors if band.contains(x)]:
            del survivors[x]

    def _band_floor(band: BandBudget) -> float:
        xs = [x for x in grid_all if band.contains(x)]
        return min(xs) if xs else band.lo

    def _tune_ev(
        band: BandBudget,
        target_pts: float,
        *,
        low_mean: bool,
        body_only: bool = False,
        keep_p: bool = False,
    ) -> None:
        # Avoid dumping flex residual onto exact 1.0× (concentration killer)
        flex_lo_floor = 1.02 if band is flex else None
        for _ in range(2_000):
            err = target_pts - _band_pts(band)
            if abs(err) <= 0.02:
                break
            xs = [
                x for x in survivors
                if band_owns(band, x, cfg) and survivors[x] > 1
                and (not body_only or abs(x - cfg.max_win) > 1e-12)
                and (flex_lo_floor is None or x + 1e-12 >= flex_lo_floor or survivors.get(x, 0) <= 3)
            ]
            if flex_lo_floor is not None:
                xs_pref = [x for x in xs if x + 1e-12 >= flex_lo_floor]
                if xs_pref:
                    xs = xs_pref
            if not xs:
                # Seed a flex point above 1.0 if empty
                if band is flex:
                    survivors[1.02] = survivors.get(1.02, 0) + max(1, int(abs(err) / 100.0 * W / 1.02))
                    continue
                break
            lo_x, hi_x = min(xs), max(xs)
            if keep_p and hi_x > lo_x + 1e-12:
                # Transfer between lo/hi to change EV at constant weight
                if err > 0:
                    # lo → hi
                    room = survivors[lo_x] - 1
                    if room < 1:
                        break
                    take = min(room, max(1, int(err / 100.0 * W / max(hi_x - lo_x, 1e-9))))
                    survivors[lo_x] -= take
                    survivors[hi_x] = survivors.get(hi_x, 0) + take
                else:
                    room = survivors[hi_x] - 1
                    if room < 1:
                        break
                    take = min(room, max(1, int(-err / 100.0 * W / max(hi_x - lo_x, 1e-9))))
                    survivors[hi_x] -= take
                    if band is flex:
                        # Spread onto several low flex points to avoid 1.02× piles
                        lands = [x for x in xs if x <= lo_x + 0.12]
                        if not lands:
                            lands = [lo_x]
                        base, rem = divmod(take, len(lands))
                        for i, x in enumerate(lands):
                            survivors[x] = survivors.get(x, 0) + base + (1 if i < rem else 0)
                    else:
                        survivors[lo_x] = survivors.get(lo_x, 0) + take
                continue
            if err > 0:
                tgt = min(xs) if low_mean else max(xs)
                survivors[tgt] = survivors.get(tgt, 0) + max(1, int(err / 100.0 * W / tgt))
            else:
                tgt = max(xs) if low_mean else min(xs)
                take = min(survivors[tgt] - 1, max(1, int(-err / 100.0 * W / tgt)))
                if take < 1:
                    break
                survivors[tgt] -= take

    def _sanitize_flex_conc(cap_frac: float = 0.055) -> None:
        """Break flex concentration; migrate 1.0× piles onto 1.02+ then retune EV."""
        nz = sum(survivors.values())
        if nz <= 0:
            return
        cap_w = max(3, int(cap_frac * nz))
        if survivors.get(1.0, 0) > cap_w:
            excess = survivors[1.0] - cap_w
            survivors[1.0] = cap_w
            pack = [round(1.02 + 0.02 * i, 2) for i in range(40) if 1.02 + 0.02 * i < 1.98]
            base, rem = divmod(excess, len(pack))
            for i, x in enumerate(pack):
                survivors[x] = survivors.get(x, 0) + base + (1 if i < rem else 0)
        for _ in range(120):
            nz = sum(survivors.values())
            cap_w = max(3, int(cap_frac * nz))
            heavy = max(
                (x for x in survivors if flex.contains(x) and survivors[x] > cap_w),
                key=lambda x: survivors[x],
                default=None,
            )
            if heavy is None:
                break
            pack = [c for c in flex_grid if c != heavy and c >= 1.02 - 1e-12]
            pack = sorted(pack, key=lambda c: abs(c - heavy))[:24]
            if len(pack) < 2:
                break
            excess = survivors[heavy] - cap_w
            survivors[heavy] = cap_w
            base, rem = divmod(excess, len(pack))
            for i, x in enumerate(pack):
                survivors[x] = survivors.get(x, 0) + base + (1 if i < rem else 0)
        # Exact flex EV restore: prefer keep_p, then burn/mint high flex
        remain = (RTP_TARGET - _non_flex_ev()) * 100.0
        z_now = 1.0 - sum(survivors.values()) / W
        _tune_ev(flex, remain, low_mean=(z_now > cfg.zero_rate + 0.008), keep_p=True)
        for _ in range(5_000):
            err = remain - _band_pts(flex)
            if abs(err) <= 0.02:
                break
            xs = [x for x in survivors if flex.contains(x) and x >= 1.02 - 1e-12 and survivors[x] > 1]
            if not xs:
                survivors[1.08] = survivors.get(1.08, 0) + max(1, int(abs(err) / 100.0 * W / 1.08))
                continue
            lo_x, hi_x = min(xs), max(xs)
            if err > 0:
                tgt = lo_x if z_now > cfg.zero_rate + 0.008 else hi_x
                survivors[tgt] = survivors.get(tgt, 0) + max(1, int(err / 100.0 * W / tgt))
            elif hi_x > lo_x + 1e-12:
                take = min(survivors[hi_x] - 1, max(1, int(-err / 100.0 * W / max(hi_x - lo_x, 1e-9))))
                if take < 1:
                    break
                survivors[hi_x] -= take
                lands = [x for x in xs if x <= lo_x + 0.10]
                if not lands:
                    lands = [lo_x]
                base, rem = divmod(take, len(lands))
                for i, x in enumerate(lands):
                    survivors[x] = survivors.get(x, 0) + base + (1 if i < rem else 0)
            else:
                take = min(survivors[hi_x] - 1, max(1, int(-err / 100.0 * W / hi_x)))
                if take < 1:
                    break
                survivors[hi_x] -= take
        # Final spread pass without retune (retune re-piles onto lows)
        for _ in range(80):
            nz = sum(survivors.values())
            if nz <= 0:
                break
            cap_w = max(3, int(cap_frac * nz))
            heavy = max(
                (x for x in survivors if flex.contains(x) and survivors[x] > cap_w),
                key=lambda x: survivors[x],
                default=None,
            )
            if heavy is None:
                break
            pack = [c for c in flex_grid if c != heavy and c >= 1.02 - 1e-12]
            pack = sorted(pack, key=lambda c: abs(c - heavy))[:24]
            if len(pack) < 2:
                break
            excess = survivors[heavy] - cap_w
            survivors[heavy] = cap_w
            base, rem = divmod(excess, len(pack))
            for i, x in enumerate(pack):
                survivors[x] = survivors.get(x, 0) + base + (1 if i < rem else 0)

    def _set_locked_or_tiny(band: BandBudget, *, reserve_max: bool = False) -> None:
        for x in [x for x in survivors if band_owns(band, x, cfg)]:
            del survivors[x]
        xs = [x for x, p in probs.items() if p > 0 and band_owns(band, x, cfg)]
        if reserve_max and band is top:
            body = [x for x in xs if abs(x - cfg.max_win) > 1e-12]
            p_hi = 1 / 300_000 if cfg.name in ("reactor", "plasma") else 1 / 100_000
            max_p = min(max(probs.get(cfg.max_win, 0.0), 1e-9), p_hi)
            max_w = max(3, int(round(max_p * W)))
            survivors[cfg.max_win] = max_w
            remain_ev = max(band.budget_ev - max_w * cfg.max_win / W, band.budget_ev * 0.85)
            if not body:
                body = [teaser]
            pbody = {x: max(probs.get(x, 0.0), 1e-15) for x in body}
            cur = sum(pbody[x] * x for x in body) or 1e-15
            for x in body:
                w = int(round(pbody[x] * (remain_ev / cur) * W))
                if w >= 3:
                    survivors[x] = w
            survivors.setdefault(teaser, 3)
            _tune_ev(band, band.budget_pts, low_mean=False, body_only=True)
            return
        if not xs:
            mid = (band.lo + min(band.hi, cfg.max_win)) / 2.0
            seed = teaser if band is top else mid
            survivors[seed] = max(3, int(round(band.budget_ev / max(seed, 1e-9) * W)))
        else:
            pband = {x: max(probs.get(x, 0.0), 1e-15) for x in xs}
            cur = sum(pband[x] * x for x in xs) or 1e-15
            for x in xs:
                w = int(round(pband[x] * (band.budget_ev / cur) * W))
                if w >= 3:
                    survivors[x] = w
            if not any(survivors.get(x, 0) >= 3 for x in xs):
                survivors[max(xs, key=lambda x: pband[x])] = 3
        # Prefer high means on lo≥5 bands for std; low means only on [2,5) if needed later
        _tune_ev(band, band.budget_pts, low_mean=(band.lo < 5.0 - 1e-12), body_only=(band is top))

    def _boost_locked_hit(*, mean_mult: float = 1.15) -> None:
        """Seed band floors and lower locked means so mid modes can hit §4.2 hit-rate."""
        for band in locked:
            floor = _band_floor(band)
            if floor > 0 and survivors.get(floor, 0) < 3:
                survivors[floor] = max(3, survivors.get(floor, 0))
            mean_target = min(floor * mean_mult, (floor + min(band.hi, cfg.max_win)) * 0.5)
            mean_target = max(floor * 1.02, mean_target)
            p_goal = band.budget_ev / mean_target
            for __ in range(6_000):
                p_now = _band_p(band)
                if p_now >= p_goal - 1e-4:
                    break
                xs = [
                    x
                    for x in survivors
                    if band_owns(band, x, cfg)
                    and survivors[x] > 3
                    and (band is not top or abs(x - cfg.max_win) > 1e-12)
                    and x > floor + 1e-12
                ]
                if not xs:
                    need = max(1, int((p_goal - p_now) * W * 0.25))
                    survivors[floor] = survivors.get(floor, 0) + need
                    _tune_ev(band, band.budget_pts, low_mean=True, body_only=(band is top))
                    continue
                hi_b = max(xs)
                a = max(1, int(min(0.002 * W, max(1, (p_goal - p_now) * W))))
                b = max(1, int(round(a * floor / hi_b)))
                if survivors[hi_b] <= b + 2:
                    xs2 = [x for x in xs if x < hi_b - 1e-12 and survivors[x] > b + 2]
                    if not xs2:
                        survivors[floor] = survivors.get(floor, 0) + a
                        _tune_ev(band, band.budget_pts, low_mean=True, body_only=(band is top))
                        continue
                    hi_b = max(xs2)
                    b = max(1, int(round(a * floor / hi_b)))
                survivors[floor] = survivors.get(floor, 0) + a
                survivors[hi_b] -= b
            _tune_ev(band, band.budget_pts, low_mean=True, body_only=(band is top))

    def _place_shaped(band: BandBudget, grid_xs: list[float], target_pts: float, target_p: float) -> None:
        """Exact two-point (lo,hi) mix for (EV, P), then light interior fill for smoothness."""
        _clear_band(band)
        xs = [x for x in grid_xs if band.contains(x)]
        if not xs or target_pts <= 0:
            return
        ev = target_pts / 100.0
        lo, hi = min(xs), max(xs)
        p_max, p_min = ev / lo, ev / hi
        tp = min(p_max * 0.998, max(p_min * 1.002, target_p))
        mean = ev / tp
        if hi <= lo + 1e-12:
            survivors[lo] = max(1, int(round(tp * W)))
            _tune_ev(band, target_pts, low_mean=True)
            return
        frac_hi = min(1.0, max(0.0, (mean - lo) / (hi - lo)))
        w_tot = max(1, int(round(tp * W)))
        w_hi = int(round(frac_hi * w_tot))
        w_lo = w_tot - w_hi
        survivors[lo] = max(1, w_lo)
        survivors[hi] = max(1, w_hi)
        low_mean = tp >= (p_min + p_max) / 2
        _tune_ev(band, target_pts, low_mean=low_mean, keep_p=True)
        for _ in range(8_000):
            p_now = _band_p(band)
            if abs(p_now - tp) <= 0.0015:
                break
            if p_now < tp:
                room = survivors.get(hi, 0) - 1
                if room < 1:
                    break
                a = min(max(1, int((tp - p_now) * W)), max(1, int(room * hi / lo)))
                b = max(1, int(round(a * lo / hi)))
                if b > room:
                    break
                survivors[lo] = survivors.get(lo, 0) + a
                survivors[hi] -= b
            else:
                room = survivors.get(lo, 0) - 1
                if room < 1:
                    lows = [x for x in xs if x < mean and survivors.get(x, 0) > 1]
                    if not lows:
                        break
                    src = min(lows)
                    room = survivors[src] - 1
                    a = min(max(1, int((p_now - tp) * W)), room)
                    b = max(1, int(round(a * src / hi)))
                    survivors[src] -= a
                    survivors[hi] = survivors.get(hi, 0) + b
                    continue
                a = min(max(1, int((p_now - tp) * W)), room)
                b = max(1, int(round(a * lo / hi)))
                survivors[lo] -= a
                survivors[hi] = survivors.get(hi, 0) + b
        _tune_ev(band, target_pts, low_mean=low_mean, keep_p=True)
        # Tight top-N equal split for concentration without tanking mean
        for _ in range(30):
            nz = max(1, sum(survivors.values()))
            cap_w = max(3, int(0.075 * nz))
            heavy = max((x for x in xs if survivors.get(x, 0) > cap_w), key=lambda x: survivors[x], default=None)
            if heavy is None:
                break
            # Prefer neighbors within 0.08 to preserve mean
            pack = [x for x in xs if 0 < abs(x - heavy) <= 0.08 + 1e-12]
            if len(pack) < 2:
                pack = sorted(xs, key=lambda x: abs(x - heavy))[1:8]
            if len(pack) < 2:
                break
            excess = survivors[heavy] - cap_w
            survivors[heavy] = cap_w
            base, rem = divmod(excess, len(pack))
            for i, x in enumerate(pack):
                survivors[x] = survivors.get(x, 0) + base + (1 if i < rem else 0)
        _tune_ev(band, target_pts, low_mean=low_mean, keep_p=True)

    def _prune() -> None:
        for x in [x for x, w in survivors.items() if w <= 0]:
            del survivors[x]

    def current_rtp() -> float:
        return sum(w * x for x, w in survivors.items()) / W

    def nz_sum() -> int:
        return sum(survivors.values())

    def _non_flex_ev() -> float:
        return sum(survivors.get(x, 0) * x / W for x in survivors if not flex.contains(x))

    def _snap_rtp(max_iters: int = 80_000) -> None:
        z_lo = int(round((cfg.zero_rate - 0.014) * W))
        z_hi = int(round((cfg.zero_rate + 0.014) * W))
        for _ in range(max_iters):
            err = current_rtp() - RTP_TARGET
            if abs(err) <= 1e-6:
                break
            flex_xs = [x for x in survivors if flex.contains(x) and survivors[x] >= 1]
            if not flex_xs:
                for x in flex_grid:
                    if x >= 1.02 - 1e-12:
                        survivors[x] = 1
                flex_xs = [x for x in flex_grid if survivors.get(x, 0) >= 1]
            step = max(1, min(50_000, int(abs(err) * W / 0.25)))
            src_hi = max(flex_xs)
            pref_lo = [x for x in flex_xs if x >= 1.02 - 1e-12]
            src_lo = min(pref_lo) if pref_lo else min(flex_xs)
            w0 = W - nz_sum()
            if err > 0:
                if src_hi > src_lo + 1e-12 and survivors[src_hi] > 1:
                    take = min(step, survivors[src_hi] - 1)
                    survivors[src_hi] -= take
                    survivors[src_lo] = survivors.get(src_lo, 0) + take
                elif w0 < z_hi and survivors[src_hi] > 1 and w0 < int(round((cfg.zero_rate + 0.005) * W)):
                    # Only burn to zeros if still at/under target zero
                    survivors[src_hi] -= min(step, survivors[src_hi] - 1, z_hi - w0)
                else:
                    break
            else:
                if src_hi > src_lo + 1e-12 and survivors[src_lo] > 1:
                    take = min(step, survivors[src_lo] - 1)
                    survivors[src_lo] -= take
                    survivors[src_hi] = survivors.get(src_hi, 0) + take
                elif w0 > z_lo:
                    survivors[src_hi] = survivors.get(src_hi, 0) + min(step, w0 - z_lo)
                else:
                    break
        _prune()
        _sanitize_flex_conc(0.058)

    def _smooth(cap_frac: float = 0.055) -> None:
        """Spread flex concentration only — never touch recovery (protects BE)."""
        for _ in range(100):
            nz = nz_sum()
            if nz <= 0:
                break
            cap_w = max(3, int(0.07 * nz))
            pool = [x for x in survivors if flex.contains(x)]
            if not pool:
                break
            heavy = max(pool, key=lambda x: survivors[x])
            if survivors[heavy] <= cap_w:
                break
            pack = [
                c for c in flex_grid
                if abs(c - heavy) > 1e-12 and abs(c - heavy) <= 0.40 + 1e-12
            ]
            if len(pack) < 5:
                pack = [c for c in flex_grid if abs(c - heavy) > 1e-12 and c <= heavy + 0.45]
            if len(pack) < 2:
                break
            for c in pack:
                survivors.setdefault(c, 1)
            excess = survivors[heavy] - cap_w
            survivors[heavy] = cap_w
            base, rem = divmod(excess, len(pack))
            for i, x in enumerate(pack):
                survivors[x] = survivors.get(x, 0) + base + (1 if i < rem else 0)
            _prune()

    def _flex_hi() -> float:
        xs = [x for x in flex_grid if survivors.get(x, 0) > 10]
        return max(xs) if xs else 1.40

    def _reshape_p(band: BandBudget, lo: float, hi: float, target_p: float, target_pts: float) -> None:
        """Adjust band P toward target at fixed EV via lo/hi EV-exact moves."""
        if hi <= lo + 1e-12:
            hi = lo + 0.2
        low_pack = [
            x
            for x in (flex_grid if band is flex else rec_grid)
            if band.contains(x) and x <= lo + 0.20 + 1e-12
        ] or [lo]
        for _ in range(10_000):
            p_now = _band_p(band)
            if abs(p_now - target_p) <= 0.001:
                break
            if p_now < target_p:
                # Peel from high, land across low pack (avoids 1.0 pile)
                cands = [x for x in survivors if band.contains(x) and x > lo + 0.05 and survivors[x] > 1]
                if not cands:
                    break
                hi_use = max(cands)
                room = survivors[hi_use] - 1
                if room < 1:
                    break
                a = min(max(1, int((target_p - p_now) * W)), max(1, int(room * hi_use / lo)))
                b = max(1, int(round(a * lo / hi_use)))
                if b > room:
                    break
                survivors[hi_use] -= b
                base, rem = divmod(a, len(low_pack))
                for i, x in enumerate(low_pack):
                    survivors[x] = survivors.get(x, 0) + base + (1 if i < rem else 0)
            else:
                room = sum(max(0, survivors.get(x, 0) - 1) for x in low_pack)
                if room < 1:
                    break
                a = min(max(1, int((p_now - target_p) * W)), room)
                # take from low pack proportionally
                left = a
                for x in sorted(low_pack, key=lambda z: survivors.get(z, 0), reverse=True):
                    if left <= 0:
                        break
                    take = min(left, max(0, survivors.get(x, 0) - 1))
                    survivors[x] = survivors.get(x, 0) - take
                    left -= take
                b = max(1, int(round(a * lo / hi)))
                survivors[hi] = survivors.get(hi, 0) + b
        low = _band_p(band) > (target_pts / 100.0) / ((lo + hi) / 2)
        _tune_ev(band, target_pts, low_mean=low, keep_p=True)

    # 1) Locked + tiny — do not pre-crush locked means (kills std / overshoots idle)
    for band in sorted(locked, key=lambda b: -b.lo):
        _set_locked_or_tiny(band, reserve_max=(band is top))
    _set_locked_or_tiny(tiny)

    def _p_targets() -> tuple[float, float]:
        p_lt = sum(
            survivors.get(x, 0) for x in survivors
            if any(band_owns(b, x, cfg) for b in locked) or tiny.contains(x)
        ) / W
        p_rec = cfg.break_even - cfg.zero_rate - _band_p(tiny)
        p_rec = min(recovery.budget_ev / min(rec_grid), max(recovery.budget_ev / max(rec_grid), p_rec))
        p_flex = 1.0 - cfg.zero_rate - p_lt - p_rec
        # Leave flex mean >1 so concentration can spread without blowing RTP
        p_flex_cap = flex.budget_ev / 1.02 * 0.995
        p_flex_floor = flex.budget_ev / max(flex_grid) * 1.002
        p_flex = min(p_flex_cap, max(p_flex_floor, p_flex))
        return p_rec, p_flex

    p_rec_t, p_flex_t = _p_targets()
    _place_shaped(recovery, rec_grid, recovery.budget_pts, p_rec_t)
    remain_pts = (RTP_TARGET - _non_flex_ev()) * 100.0
    # Use flex budget center when residual matches; else residual
    flex_pts = remain_pts if abs(remain_pts - flex.budget_pts) < 1.0 else remain_pts
    _place_shaped(flex, flex_grid, flex_pts, p_flex_t)
    _snap_rtp()

    def _stats() -> tuple[float, float, float]:
        w0 = W - nz_sum()
        be = (w0 + sum(w for x, w in survivors.items() if x < 1.0 - 1e-12)) / W
        return w0 / W, be, current_rtp()

    def _hit_short() -> bool:
        return _stats()[0] > cfg.zero_rate + 0.012

    def _retune_locked(*, prefer_hit: bool = False) -> None:
        for band in locked:
            _tune_ev(band, band.budget_pts, low_mean=prefer_hit, body_only=(band is top))

    def _fix_hit_be() -> None:
        """Drive zero/BE into windows via locked-mean + recovery/flex reshape."""
        for _ in range(8):
            z, be, _ = _stats()
            z_err = z - cfg.zero_rate
            be_err = be - cfg.break_even
            if abs(z_err) <= 0.012 and abs(be_err) <= 0.012:
                break
            if z_err > 0.012:
                # When BE is also high, convert zeros → flex/locked (drops z and BE together).
                # Only inflate recovery when BE is at/under target.
                remain_pts = (RTP_TARGET - _non_flex_ev()) * 100.0
                p_flex_cap = flex.budget_ev / 1.02 * 0.995
                p_other = sum(
                    survivors.get(x, 0) for x in survivors
                    if any(band_owns(b, x, cfg) for b in locked) or tiny.contains(x) or recovery.contains(x)
                ) / W
                # Request enough flex P to absorb the zero excess (and BE excess if present)
                need = z_err + max(0.0, be_err) * 0.25
                p_flex_t = min(p_flex_cap, max(0.01, _band_p(flex) + need))
                _reshape_p(flex, min(flex_grid), 1.20, p_flex_t, remain_pts)
                z, be, _ = _stats()
                # Prefer zeros→recovery when BE allows (lowers z, BE unchanged) before locked crush
                if z > cfg.zero_rate + 0.012 and be <= cfg.break_even + 0.012:
                    p_sub = min(
                        recovery.budget_ev / min(rec_grid) * 0.998,
                        max(
                            recovery.budget_ev / max(rec_grid) * 1.002,
                            _band_p(recovery) + (z - cfg.zero_rate),
                        ),
                    )
                    # Keep recovery EV at budget; higher P ⇒ lower mean
                    _place_shaped(recovery, rec_grid, recovery.budget_pts, p_sub)
                    remain_pts = (RTP_TARGET - _non_flex_ev()) * 100.0
                    _reshape_p(flex, min(flex_grid), 1.20, p_flex_cap, remain_pts)
                z, be, _ = _stats()
                # Locked mean-lowering is last resort — it fights std floors
                if z > cfg.zero_rate + 0.014:
                    _boost_locked_hit(mean_mult=1.40)
                    if _stats()[0] > cfg.zero_rate + 0.014:
                        _boost_locked_hit(mean_mult=1.28)
                    remain_pts = (RTP_TARGET - _non_flex_ev()) * 100.0
                    _reshape_p(flex, min(flex_grid), 1.20, p_flex_cap, remain_pts)
                z, be, _ = _stats()
                # If BE dropped too far, top up recovery from zeros (BE stable) or from flex
                if be < cfg.break_even - 0.01:
                    p_sub = cfg.break_even - z - _band_p(tiny)
                    p_sub = min(
                        recovery.budget_ev / min(rec_grid) * 0.998,
                        max(recovery.budget_ev / max(rec_grid) * 1.002, p_sub),
                    )
                    _place_shaped(recovery, rec_grid, recovery.budget_pts, p_sub)
                    remain_pts = (RTP_TARGET - _non_flex_ev()) * 100.0
                    _tune_ev(flex, remain_pts, low_mean=True, keep_p=True)
                elif be > cfg.break_even + 0.012 and z <= cfg.zero_rate + 0.012:
                    # z ok but BE high: move recovery → flex
                    p_sub = max(
                        recovery.budget_ev / max(rec_grid) * 1.002,
                        cfg.break_even - z - _band_p(tiny),
                    )
                    p_sub = min(recovery.budget_ev / min(rec_grid) * 0.998, p_sub)
                    _place_shaped(recovery, rec_grid, recovery.budget_pts, p_sub)
                    remain_pts = (RTP_TARGET - _non_flex_ev()) * 100.0
                    _reshape_p(flex, min(flex_grid), 1.25, p_flex_cap, remain_pts)
            elif be_err > 0.012:
                # BE high: re-place recovery at target sub-1 mass, push freed weight into flex
                z, be, _ = _stats()
                p_sub = cfg.break_even - z - _band_p(tiny)
                # If z itself is above target, use target z so recovery isn't oversized
                p_sub = min(p_sub, cfg.break_even - cfg.zero_rate - _band_p(tiny) + 0.005)
                p_sub = min(
                    recovery.budget_ev / min(rec_grid) * 0.998,
                    max(recovery.budget_ev / max(rec_grid) * 1.002, p_sub),
                )
                _place_shaped(recovery, rec_grid, recovery.budget_pts, p_sub)
                remain_pts = (RTP_TARGET - _non_flex_ev()) * 100.0
                p_flex_cap = flex.budget_ev / min(flex_grid) * 0.998
                # Pull enough flex P to hit zero target (freed recovery became zeros)
                p_flex_t = min(
                    p_flex_cap,
                    max(_band_p(flex), 1.0 - cfg.zero_rate - sum(
                        survivors.get(x, 0) for x in survivors
                        if any(band_owns(b, x, cfg) for b in locked) or tiny.contains(x) or recovery.contains(x)
                    ) / W),
                )
                _reshape_p(flex, min(flex_grid), 1.25, p_flex_t, remain_pts)
                _tune_ev(flex, remain_pts, low_mean=True, keep_p=True)
            else:
                # z too low and/or be too low
                if be_err < -0.012:
                    p_sub = cfg.break_even - z - _band_p(tiny)
                    p_sub = min(
                        recovery.budget_ev / min(rec_grid) * 0.998,
                        max(recovery.budget_ev / max(rec_grid) * 1.002, p_sub),
                    )
                    _place_shaped(recovery, rec_grid, recovery.budget_pts, p_sub)
                    remain_pts = (RTP_TARGET - _non_flex_ev()) * 100.0
                    _tune_ev(flex, remain_pts, low_mean=False)
                if z < cfg.zero_rate - 0.012:
                    # Burn a little flex high to zeros via snap bounds
                    flex_xs = [x for x in survivors if flex.contains(x) and survivors[x] > 3]
                    if flex_xs:
                        src = max(flex_xs)
                        take = min(survivors[src] - 3, max(1, int((cfg.zero_rate - z) * W * 0.5)))
                        survivors[src] -= take
            _snap_rtp()
            _retune_locked(prefer_hit=False)
            # Hard-clamp recovery to §4.3 budget — prevents BE blowups from keep_p/mint drift
            if abs(_band_pts(recovery) - recovery.budget_pts) > 0.35:
                z_now = _stats()[0]
                p_sub = cfg.break_even - max(z_now, cfg.zero_rate) - _band_p(tiny)
                p_sub = min(
                    recovery.budget_ev / min(rec_grid) * 0.998,
                    max(recovery.budget_ev / max(rec_grid) * 1.002, p_sub),
                )
                _place_shaped(recovery, rec_grid, recovery.budget_pts, p_sub)
            remain_pts = (RTP_TARGET - _non_flex_ev()) * 100.0
            _tune_ev(flex, remain_pts, low_mean=_hit_short(), keep_p=True)
            _tune_ev(recovery, recovery.budget_pts, low_mean=True, keep_p=True)

    # 2) Reshape if place missed windows
    z, be, rtp = _stats()
    if abs(z - cfg.zero_rate) > 0.014 or abs(be - cfg.break_even) > 0.014:
        for _ in range(10):
            remain_pts = (RTP_TARGET - _non_flex_ev()) * 100.0
            z, be, rtp = _stats()
            if abs(z - cfg.zero_rate) > 0.01:
                _, p_flex_t = _p_targets()
                p_flex_t = min(
                    flex.budget_ev / min(flex_grid) * 0.998,
                    max(0.01, p_flex_t + (z - cfg.zero_rate)),
                )
                _reshape_p(flex, min(flex_grid), 1.25, p_flex_t, remain_pts)
                _snap_rtp()
                continue
            if abs(be - cfg.break_even) > 0.01:
                p_sub = cfg.break_even - z - _band_p(tiny)
                p_sub = min(
                    recovery.budget_ev / min(rec_grid) * 0.998,
                    max(recovery.budget_ev / max(rec_grid) * 1.002, p_sub),
                )
                _place_shaped(recovery, rec_grid, recovery.budget_pts, p_sub)
                remain_pts = (RTP_TARGET - _non_flex_ev()) * 100.0
                _tune_ev(flex, remain_pts, low_mean=False)
                _snap_rtp()
                continue
            break

    _fix_hit_be()

    # 3) Flex smooth + restore (do not re-place recovery if BE already ok)
    _smooth(0.07)
    remain_pts = (RTP_TARGET - _non_flex_ev()) * 100.0
    z, be, _ = _stats()
    _tune_ev(flex, remain_pts, low_mean=(z > cfg.zero_rate))
    if abs(z - cfg.zero_rate) > 0.01:
        _, p_flex_t = _p_targets()
        _reshape_p(
            flex,
            min(flex_grid),
            1.25,
            min(flex.budget_ev / min(flex_grid) * 0.998, max(0.01, p_flex_t + (z - cfg.zero_rate))),
            remain_pts,
        )
    if abs(be - cfg.break_even) > 0.012:
        p_sub = cfg.break_even - z - _band_p(tiny)
        p_sub = min(
            recovery.budget_ev / min(rec_grid) * 0.998,
            max(recovery.budget_ev / max(rec_grid) * 1.002, p_sub),
        )
        _place_shaped(recovery, rec_grid, recovery.budget_pts, p_sub)
        remain_pts = (RTP_TARGET - _non_flex_ev()) * 100.0
        _tune_ev(flex, remain_pts, low_mean=False)
    _snap_rtp()

    # 4) Std nudge: barbell locked bands (same EV/P, higher second moment), then flex↔top
    def _barbell_locked(rounds: int = 3_000) -> None:
        for band in locked:
            floor = _band_floor(band)
            ceil_cands = [
                x for x in grid_all
                if band_owns(band, x, cfg)
                and x > floor + 1e-12
            ]
            if not ceil_cands:
                continue
            # Prefer max_win as the high pole on the top band (std)
            hi = cfg.max_win if band is top and any(abs(x - cfg.max_win) < 1e-12 for x in ceil_cands) else max(ceil_cands)
            if hi <= floor + 1e-12:
                continue
            for _ in range(rounds):
                mids = [
                    x for x in survivors
                    if band_owns(band, x, cfg)
                    and survivors[x] > 4
                    and floor + 1e-12 < x < hi - 1e-12
                ]
                if not mids:
                    break
                mid = max(mids, key=lambda x: survivors[x])
                # Take 2 from mid → a at floor + b at hi, keep EV & weight
                take = min(2, survivors[mid] - 3)
                if take < 2:
                    break
                b = max(1, int(round(take * (mid - floor) / (hi - floor))))
                a = take - b
                if a < 1:
                    a, b = 1, take - 1
                survivors[mid] -= take
                survivors[floor] = survivors.get(floor, 0) + a
                survivors[hi] = survivors.get(hi, 0) + b
            _tune_ev(band, band.budget_pts, low_mean=False, body_only=False)

    rtp_v = current_rtp()
    second = sum(w * x * x for x, w in survivors.items()) / W
    s = math.sqrt(max(0.0, second - rtp_v * rtp_v))
    if s < target_std - 0.02:
        _barbell_locked(rounds=8_000)
        # Use +0.35 band slack on high locked bands for std (still inside ±0.4)
        z_now = _stats()[0]
        if z_now <= cfg.zero_rate + 0.014:
            for band in sorted(locked, key=lambda b: -b.lo):
                _tune_ev(
                    band,
                    min(band.budget_pts + 0.35, band.budget_pts + 0.38),
                    low_mean=False,
                    body_only=(band is top),
                    keep_p=False,
                )
            remain_pts = (RTP_TARGET - _non_flex_ev()) * 100.0
            _tune_ev(flex, remain_pts, low_mean=False, keep_p=True)
        rtp_v = current_rtp()
        second = sum(w * x * x for x, w in survivors.items()) / W
        s = math.sqrt(max(0.0, second - rtp_v * rtp_v))
    if not (std_lo <= s <= std_hi):
        for _ in range(2_000):
            rtp_v = current_rtp()
            second = sum(w * x * x for x, w in survivors.items()) / W
            s = math.sqrt(max(0.0, second - rtp_v * rtp_v))
            if abs(s - target_std) < 0.03 and std_lo <= s <= std_hi:
                break
            body = [
                x for x in survivors
                if band_owns(top, x, cfg) and abs(x - cfg.max_win) > 1e-12 and survivors.get(x, 0) > 3
            ]
            flex_xs = [x for x in flex_grid if survivors.get(x, 0) > 3]
            if s < std_lo and body and flex_xs:
                src = max(flex_xs, key=lambda x: survivors[x])
                dst = max(body)
                dw = min(survivors[src] - 3, max(1, int(0.0005 * W / src)))
                dw_dst = max(1, int(round(dw * src / dst)))
                if _band_pts(top) + dw_dst * dst / W * 100 > top.budget_pts + 0.35:
                    break
                survivors[src] -= dw
                survivors[dst] = survivors.get(dst, 0) + dw_dst
            elif s > std_hi and body:
                src = max(body)
                dw = min(survivors[src] - 3, max(1, int(0.0005 * W / src)))
                survivors[src] -= dw
                survivors[1.2] = survivors.get(1.2, 0) + max(1, int(round(dw * src / 1.2)))
            else:
                break
            _prune()
        _retune_locked()
        _tune_ev(recovery, recovery.budget_pts, low_mean=True)
        remain_pts = (RTP_TARGET - _non_flex_ev()) * 100.0
        _tune_ev(flex, remain_pts, low_mean=(_stats()[0] > cfg.zero_rate))
        _snap_rtp()
        _fix_hit_be()

    # ETL peel
    etl = sum(w * x for x, w in survivors.items() if x >= 40 - 1e-12) / W
    if etl > etl_cap:
        for _ in range(500):
            etl = sum(w * x for x, w in survivors.items() if x >= 40 - 1e-12) / W
            if etl <= etl_cap:
                break
            donors = [x for x in survivors if x >= 40 - 1e-12 and survivors[x] > 3]
            if not donors:
                break
            src = max(donors)
            take = min(survivors[src] - 3, max(1, int((etl - etl_cap) * W / src)))
            land = 25.0 if cfg.max_win >= 25 else 1.5
            survivors[src] -= take
            survivors[land] = survivors.get(land, 0) + take
        _retune_locked()
        _tune_ev(flex, (RTP_TARGET - _non_flex_ev()) * 100.0, low_mean=True)
        _snap_rtp()

    # Final conc + RTP
    _smooth(0.07)
    # Global conc pass ≤7.8% of nz
    for _ in range(60):
        nz = nz_sum()
        if nz <= 0:
            break
        cap_w = max(3, int(0.078 * nz))
        heavy = max(
            (x for x in survivors if x > 0),
            key=lambda x: survivors[x],
            default=None,
        )
        if heavy is None or survivors[heavy] <= cap_w:
            break
        if flex.contains(heavy):
            pack = [c for c in flex_grid if 0 < abs(c - heavy) <= 0.10]
        elif recovery.contains(heavy):
            pack = [c for c in rec_grid if 0 < abs(c - heavy) <= 0.08]
        else:
            owner = next((b for b in cfg.band_budgets if band_owns(b, heavy, cfg)), None)
            pack = [
                c for c in survivors
                if c != heavy and owner is not None and band_owns(owner, c, cfg)
                and abs(c - heavy) <= max(0.5, heavy * 0.1)
            ]
        if len(pack) < 2:
            owner = next((b for b in cfg.band_budgets if band_owns(b, heavy, cfg)), None)
            pack = sorted(
                (
                    c for c in survivors
                    if c != heavy and c > 0 and owner is not None and band_owns(owner, c, cfg)
                ),
                key=lambda c: abs(c - heavy),
            )[:6]
        if len(pack) < 2:
            break
        excess = survivors[heavy] - cap_w
        survivors[heavy] = cap_w
        base, rem = divmod(excess, len(pack))
        for i, x in enumerate(pack):
            survivors[x] = survivors.get(x, 0) + base + (1 if i < rem else 0)
        _prune()

    _tune_ev(recovery, recovery.budget_pts, low_mean=True, keep_p=True)
    remain_pts = (RTP_TARGET - _non_flex_ev()) * 100.0
    z, be, _ = _stats()
    _tune_ev(flex, remain_pts, low_mean=(z > cfg.zero_rate))
    if abs(z - cfg.zero_rate) > 0.012:
        _, p_flex_t = _p_targets()
        _reshape_p(
            flex,
            min(flex_grid),
            1.25,
            min(flex.budget_ev / min(flex_grid) * 0.998, max(0.01, p_flex_t + (z - cfg.zero_rate))),
            remain_pts,
        )
    if abs(be - cfg.break_even) > 0.012:
        p_sub = cfg.break_even - z - _band_p(tiny)
        p_sub = min(
            recovery.budget_ev / min(rec_grid) * 0.998,
            max(recovery.budget_ev / max(rec_grid) * 1.002, p_sub),
        )
        _place_shaped(recovery, rec_grid, recovery.budget_pts, p_sub)
        remain_pts = (RTP_TARGET - _non_flex_ev()) * 100.0
        _tune_ev(flex, remain_pts, low_mean=False)
    _smooth(0.065)
    _snap_rtp(80_000)
    _fix_hit_be()

    survivors = {x: w for x, w in survivors.items() if w > 0}
    _tune_ev(recovery, recovery.budget_pts, low_mean=True)
    _retune_locked()
    remain_pts = (RTP_TARGET - _non_flex_ev()) * 100.0
    for _ in range(5_000):
        err_pts = remain_pts - _band_pts(flex)
        if abs(err_pts) <= 0.0001:
            break
        xs = [x for x in survivors if flex.contains(x) and survivors[x] >= 1]
        if not xs:
            survivors[1.0] = 1000
            continue
        if err_pts > 0:
            survivors[max(xs)] = survivors.get(max(xs), 0) + max(1, int(err_pts / 100.0 * W / max(xs)))
        else:
            tgt = max(xs)
            take = max(1, int(-err_pts / 100.0 * W / tgt))
            if survivors[tgt] > 0:
                survivors[tgt] -= min(take, survivors[tgt])
    for _ in range(100_000):
        err = current_rtp() - RTP_TARGET
        if abs(err) <= 1e-6:
            break
        flex_xs = [x for x in survivors if flex.contains(x) and survivors[x] >= 1]
        if not flex_xs:
            survivors[1.2] = survivors.get(1.2, 0) + 1
            continue
        src_hi, src_lo = max(flex_xs), min(flex_xs)
        if err > 0:
            if src_hi > src_lo + 1e-12 and survivors[src_hi] > 0:
                survivors[src_hi] -= 1
                survivors[src_lo] = survivors.get(src_lo, 0) + 1
            elif survivors[src_hi] > 0:
                survivors[src_hi] -= 1
            else:
                break
        else:
            if src_hi > src_lo + 1e-12 and survivors[src_lo] > 0:
                survivors[src_lo] -= 1
                survivors[src_hi] = survivors.get(src_hi, 0) + 1
            else:
                survivors[src_hi] = survivors.get(src_hi, 0) + 1
    survivors = {x: w for x, w in survivors.items() if w > 0}
    # Pad unique count by splitting heavy points onto unused same-band grid neighbors
    for _ in range(2_000):
        uniq = sum(1 for w in survivors.values() if w > 0)
        if uniq >= cfg.min_unique:
            break
        cands = [x for x, w in survivors.items() if w >= 4 and x > 0]
        if not cands:
            break
        heavy = max(cands, key=lambda x: survivors[x])
        owner = next((b for b in cfg.band_budgets if band_owns(b, heavy, cfg)), None)
        unused = [
            g for g in grid_all
            if survivors.get(g, 0) == 0
            and owner is not None and band_owns(owner, g, cfg)
        ]
        if not unused and flex.contains(heavy):
            unused = [g for g in flex_grid if survivors.get(g, 0) == 0]
        if not unused and recovery.contains(heavy):
            unused = [g for g in rec_grid if survivors.get(g, 0) == 0]
        if not unused:
            # seed from any band that still has unused grid slots
            progressed = False
            for band in cfg.band_budgets:
                if band.lo < 1e-12:
                    continue
                unused_b = [g for g in grid_all if survivors.get(g, 0) == 0 and band.contains(g)]
                heavies_b = [
                    x for x, w in survivors.items()
                    if w >= 4 and band_owns(band, x, cfg)
                ]
                if unused_b and heavies_b:
                    heavy = max(heavies_b, key=lambda x: survivors[x])
                    tgt = min(unused_b, key=lambda g: abs(g - heavy))
                    survivors[heavy] -= 1
                    survivors[tgt] = survivors.get(tgt, 0) + 1
                    progressed = True
                    break
            if not progressed:
                break
            continue
        tgt = min(unused, key=lambda g: abs(g - heavy))
        take = min(2, survivors[heavy] // 2) if survivors[heavy] >= 4 else 1
        take = max(1, take)
        survivors[heavy] -= take
        survivors[tgt] = survivors.get(tgt, 0) + take
    # Keep band EVs after splits — prefer low mean if hit still short
    _retune_locked()
    _tune_ev(recovery, recovery.budget_pts, low_mean=True, keep_p=True)
    remain_pts = (RTP_TARGET - _non_flex_ev()) * 100.0
    _tune_ev(flex, remain_pts, low_mean=_hit_short())
    _snap_rtp(20_000)
    _fix_hit_be()
    # Final conc flatten ≤7.9% — never cross band boundaries (esp. flex→recovery)
    for _ in range(40):
        nz = sum(survivors.values())
        if nz <= 0:
            break
        cap_w = max(3, int(0.079 * nz))
        heavy = max((x for x in survivors if x > 0), key=lambda x: survivors[x], default=None)
        if heavy is None or survivors[heavy] <= cap_w:
            break
        owner = next((b for b in cfg.band_budgets if band_owns(b, heavy, cfg)), None)
        if flex.contains(heavy):
            pack = [c for c in flex_grid if 0 < abs(c - heavy) <= 0.12]
        elif recovery.contains(heavy):
            pack = [c for c in rec_grid if 0 < abs(c - heavy) <= 0.10]
        else:
            pack = [
                c for c in survivors
                if c != heavy and owner is not None and band_owns(owner, c, cfg)
            ]
            pack = sorted(pack, key=lambda c: abs(c - heavy))[:8]
        if len(pack) < 2:
            pack = sorted(
                (
                    c for c in survivors
                    if c != heavy and c > 0 and owner is not None and band_owns(owner, c, cfg)
                ),
                key=lambda c: abs(c - heavy),
            )[:8]
        if len(pack) < 2:
            break
        excess = survivors[heavy] - cap_w
        survivors[heavy] = cap_w
        base, rem = divmod(excess, len(pack))
        for i, x in enumerate(pack):
            survivors[x] = survivors.get(x, 0) + base + (1 if i < rem else 0)
    # Re-anchor recovery then flex residual
    if abs(_band_pts(recovery) - recovery.budget_pts) > 0.2:
        z_now, _, _ = _stats()
        p_sub = cfg.break_even - max(z_now, cfg.zero_rate) - _band_p(tiny)
        p_sub = min(
            recovery.budget_ev / min(rec_grid) * 0.998,
            max(recovery.budget_ev / max(rec_grid) * 1.002, p_sub),
        )
        _place_shaped(recovery, rec_grid, recovery.budget_pts, p_sub)
    _tune_ev(flex, (RTP_TARGET - _non_flex_ev()) * 100.0, low_mean=_hit_short(), keep_p=True)
    _snap_rtp(20_000)
    _fix_hit_be()
    # Final std top-up after rate fixes (rates take priority earlier)
    rtp_v = current_rtp()
    second = sum(w * x * x for x, w in survivors.items()) / W
    s = math.sqrt(max(0.0, second - rtp_v * rtp_v))
    if s < std_lo:
        _barbell_locked(rounds=4_000)
        for band in sorted(locked, key=lambda b: -b.lo):
            if _band_pts(band) < band.budget_pts + 0.38:
                _tune_ev(
                    band,
                    band.budget_pts + 0.38,
                    low_mean=False,
                    body_only=(band is top),
                    keep_p=False,
                )
        remain_pts = (RTP_TARGET - _non_flex_ev()) * 100.0
        # Burn flex P if needed to fund locked slack (only with zero headroom)
        _tune_ev(
            flex,
            remain_pts,
            low_mean=False,
            keep_p=(_stats()[0] > cfg.zero_rate + 0.008),
        )
        # flex barbell / de-pile floor for second moment
        for __ in range(3_000):
            rtp_v = current_rtp()
            second = sum(w * x * x for x, w in survivors.items()) / W
            s = math.sqrt(max(0.0, second - rtp_v * rtp_v))
            if s >= std_lo:
                break
            mids = [x for x in flex_grid if 1.08 < x < 1.7 and survivors.get(x, 0) > 5]
            if not mids and survivors.get(1.0, 0) > 1000 and _stats()[0] < cfg.zero_rate + 0.012:
                take = min(survivors[1.0] - 100, max(1, int(0.0008 * W)))
                survivors[1.0] -= take
                survivors[1.98] = survivors.get(1.98, 0) + take
                peel = min(survivors.get(1.0, 0), max(1, int(round(take * 0.98))))
                survivors[1.0] -= peel
                continue
            if not mids:
                break
            mid = max(mids, key=lambda x: survivors[x])
            lo_f, hi_f = 1.0, 1.98
            take = min(2, survivors[mid] - 3)
            if take < 2:
                break
            b = max(1, int(round(take * (mid - lo_f) / (hi_f - lo_f))))
            a = take - b
            if a < 1:
                a, b = 1, take - 1
            survivors[mid] -= take
            survivors[lo_f] = survivors.get(lo_f, 0) + a
            survivors[hi_f] = survivors.get(hi_f, 0) + b
        # EV repair flex
        remain_pts = (RTP_TARGET - _non_flex_ev()) * 100.0
        _tune_ev(flex, remain_pts, low_mean=False, keep_p=(_stats()[0] > cfg.zero_rate + 0.008))
        # Micro top-up if still a hair under floor
        for __ in range(800):
            rtp_v = current_rtp()
            second = sum(w * x * x for x, w in survivors.items()) / W
            s = math.sqrt(max(0.0, second - rtp_v * rtp_v))
            if s >= std_lo:
                break
            body = [
                x for x in survivors
                if band_owns(top, x, cfg) and abs(x - cfg.max_win) > 1e-12 and survivors.get(x, 0) >= 1
            ]
            flex_src = [x for x in flex_grid if survivors.get(x, 0) > 5]
            if not body or not flex_src:
                break
            if _band_pts(top) >= top.budget_pts + 0.39:
                break
            if _stats()[0] > cfg.zero_rate + 0.014:
                break
            src = min(flex_src)
            dst = max(body)
            survivors[src] -= 1
            k = max(1, int(round(src / dst)))
            survivors[dst] = survivors.get(dst, 0) + k
            if _band_pts(top) > top.budget_pts + 0.39:
                survivors[dst] -= k
                survivors[src] += 1
                break
        remain_pts = (RTP_TARGET - _non_flex_ev()) * 100.0
        _tune_ev(flex, remain_pts, low_mean=False, keep_p=True)
        # Direct second-moment inject: flex-floor → max_win (biggest ΔE[X²] per RTP)
        for __ in range(5_000):
            rtp_v = current_rtp()
            second = sum(w * x * x for x, w in survivors.items()) / W
            s = math.sqrt(max(0.0, second - rtp_v * rtp_v))
            if s >= std_lo + 0.005:
                break
            if _stats()[0] > cfg.zero_rate + 0.014:
                break
            if survivors.get(1.0, 0) < 100:
                break
            # Remove `cost` weight at 1.0, add 1 at max_win: EV +=(max-1)/W, then peel cost2 at 1.0
            # Net: remove max_win weight at 1.0, add 1 at max → EV exact, P drops by (max-1)
            mw = cfg.max_win
            if survivors.get(1.0, 0) < int(mw) + 2:
                break
            survivors[1.0] -= int(round(mw))
            survivors[mw] = survivors.get(mw, 0) + 1
            if _band_pts(top) > top.budget_pts + 0.39:
                survivors[mw] -= 1
                survivors[1.0] = survivors.get(1.0, 0) + int(round(mw))
                # try teaser instead
                td = teaser
                if survivors.get(1.0, 0) < int(round(td)) + 2:
                    break
                survivors[1.0] -= int(round(td))
                survivors[td] = survivors.get(td, 0) + 1
                if _band_pts(top) > top.budget_pts + 0.39:
                    survivors[td] -= 1
                    survivors[1.0] = survivors.get(1.0, 0) + int(round(td))
                    break
        remain_pts = (RTP_TARGET - _non_flex_ev()) * 100.0
        _tune_ev(flex, remain_pts, low_mean=False, keep_p=(_stats()[0] > cfg.zero_rate + 0.01))
        _tune_ev(top, min(top.budget_pts + 0.38, _band_pts(top)), low_mean=False, body_only=True, keep_p=False)
    _fix_hit_be()  # rates after std

    def _rebalance_locked_via_flex(tol: float = 0.12) -> None:
        """EV-transfer locked ↔ flex so locked bands sit on §4.3 centers (no peel-to-zero)."""
        def _flex_deposit(ev_units: float) -> None:
            """Add ~ev_units of EV spread across flex grid (avoids 1.0× piles)."""
            if ev_units <= 0:
                return
            pack = [x for x in (1.02, 1.06, 1.10, 1.14, 1.18, 1.22, 1.28, 1.36, 1.48, 1.62, 1.78, 1.92)
                    if flex.contains(x)]
            if not pack:
                pack = flex_grid[:12]
            per = ev_units / len(pack)
            for x in pack:
                survivors[x] = survivors.get(x, 0) + max(1, int(round(per / x * W)))

        def _flex_withdraw(ev_units: float) -> float:
            """Remove ~ev_units of EV from heaviest flex points; return EV actually removed."""
            removed = 0.0
            for _ in range(20_000):
                if removed >= ev_units - 1e-12:
                    break
                heavies = [x for x in survivors if flex.contains(x) and survivors[x] > 4]
                if not heavies:
                    break
                # Prefer burning near-1 piles first (concentration + low second moment)
                src = min(heavies, key=lambda x: (x, -survivors[x]))
                need = ev_units - removed
                take = min(survivors[src] - 4, max(1, int(need / src * W)))
                if take < 1:
                    break
                survivors[src] -= take
                removed += take * src / W
            return removed

        for _ in range(30_000):
            progressed = False
            for band in sorted(locked, key=lambda b: -b.lo):
                err = band.budget_pts - _band_pts(band)
                if abs(err) <= tol:
                    continue
                if err > 0:
                    # Prefer raising mean inside the band (preserves hit) before importing P from flex
                    before = _band_pts(band)
                    _tune_ev(band, band.budget_pts, low_mean=False, body_only=(band is top), keep_p=True)
                    if abs(band.budget_pts - _band_pts(band)) <= tol:
                        progressed = True
                        continue
                    # Still short: import EV from flex onto band floor (hit-friendly) or high end
                    got = _flex_withdraw((band.budget_pts - _band_pts(band)) / 100.0)
                    if got <= 1e-12:
                        if abs(_band_pts(band) - before) > 1e-9:
                            progressed = True
                        continue
                    dst_cands = [
                        x for x in grid_all
                        if band_owns(band, x, cfg)
                        and (band is not top or abs(x - cfg.max_win) > 1e-12)
                    ]
                    if not dst_cands:
                        _flex_deposit(got)
                        continue
                    # Hit-short → floor; else high end for std
                    dst = min(dst_cands) if _hit_short() else max(dst_cands)
                    b = max(1, int(round(got * W / dst)))
                    survivors[dst] = survivors.get(dst, 0) + b
                    if _band_pts(band) > band.budget_pts + tol:
                        over = (_band_pts(band) - band.budget_pts) / 100.0
                        take = min(survivors[dst] - 1, max(1, int(over * W / dst)))
                        if take >= 1:
                            survivors[dst] -= take
                            _flex_deposit(take * dst / W)
                    progressed = True
                else:
                    xs = [
                        x for x in survivors
                        if band_owns(band, x, cfg) and survivors[x] > 3
                        and (band is not top or abs(x - cfg.max_win) > 1e-12)
                    ]
                    if not xs:
                        continue
                    src = max(xs)
                    b = min(survivors[src] - 3, max(1, int(round((-err) / 100.0 * W / src))))
                    if b < 1:
                        continue
                    survivors[src] -= b
                    _flex_deposit(b * src / W)
                    progressed = True
            if not progressed:
                break
        remain = (RTP_TARGET - _non_flex_ev()) * 100.0
        _tune_ev(flex, remain, low_mean=_hit_short(), keep_p=True)
        # Immediate concentration guard after flex deposits
        for __ in range(40):
            nz = sum(survivors.values())
            if nz <= 0:
                break
            cap_w = max(3, int(0.06 * nz))
            heavy = max(
                (x for x in survivors if flex.contains(x) and survivors[x] > cap_w),
                key=lambda x: survivors[x],
                default=None,
            )
            if heavy is None:
                break
            pack = [c for c in flex_grid if 0 < abs(c - heavy) <= 0.16]
            pack = sorted(pack, key=lambda c: abs(c - heavy))[:14]
            if len(pack) < 2:
                break
            excess = survivors[heavy] - cap_w
            survivors[heavy] = cap_w
            base, rem = divmod(excess, len(pack))
            for i, x in enumerate(pack):
                survivors[x] = survivors.get(x, 0) + base + (1 if i < rem else 0)
            # EV may drift; retune at constant P
            remain = (RTP_TARGET - _non_flex_ev()) * 100.0
            _tune_ev(flex, remain, low_mean=_hit_short(), keep_p=True)
        _sanitize_flex_conc(0.055)

    def _spread_locked_floors(cap_frac: float = 0.06) -> None:
        """Break band-floor concentration piles (2×/5×) without changing band EV much."""
        for _ in range(100):
            nz = sum(survivors.values())
            if nz <= 0:
                break
            cap_w = max(3, int(cap_frac * nz))
            heavy = max((x for x in survivors if x > 0), key=lambda x: survivors[x], default=None)
            if heavy is None or survivors[heavy] <= cap_w:
                break
            owner = next((b for b in locked if band_owns(b, heavy, cfg)), None)
            if owner is None:
                if flex.contains(heavy):
                    pack = [c for c in flex_grid if 0 < abs(c - heavy) <= 0.12]
                elif recovery.contains(heavy):
                    pack = [c for c in rec_grid if 0 < abs(c - heavy) <= 0.10]
                else:
                    break
            else:
                pack = [
                    c for c in grid_all
                    if c != heavy and band_owns(owner, c, cfg)
                    and (owner is not top or abs(c - cfg.max_win) > 1e-12)
                ]
            pack = sorted(pack, key=lambda c: abs(c - heavy))[:16]
            if len(pack) < 2:
                break
            excess = survivors[heavy] - cap_w
            survivors[heavy] = cap_w
            base, rem = divmod(excess, len(pack))
            for i, x in enumerate(pack):
                survivors[x] = survivors.get(x, 0) + base + (1 if i < rem else 0)
            if owner is not None:
                _tune_ev(owner, owner.budget_pts, low_mean=True, body_only=(owner is top), keep_p=True)
                # Re-spread after tune (low_mean re-piles onto floor), then restore EV
                floor = _band_floor(owner)
                for __ in range(40):
                    nz2 = sum(survivors.values())
                    cap2 = max(3, int(cap_frac * nz2))
                    if survivors.get(floor, 0) <= cap2:
                        break
                    pack2 = [
                        c for c in grid_all
                        if c != floor and band_owns(owner, c, cfg)
                        and (owner is not top or abs(c - cfg.max_win) > 1e-12)
                    ]
                    pack2 = sorted(pack2, key=lambda c: abs(c - floor))[:16]
                    if len(pack2) < 2:
                        break
                    excess2 = survivors[floor] - cap2
                    survivors[floor] = cap2
                    base2, rem2 = divmod(excess2, len(pack2))
                    for i, x in enumerate(pack2):
                        survivors[x] = survivors.get(x, 0) + base2 + (1 if i < rem2 else 0)
                _tune_ev(owner, owner.budget_pts, low_mean=True, body_only=(owner is top), keep_p=True)

    _rebalance_locked_via_flex(0.12)
    _spread_locked_floors(0.065)
    _rebalance_locked_via_flex(0.12)
    # Hard RTP close on flex only — never peel locked-to-zero (that remints flex and starves highs)
    for _ in range(80_000):
        err = current_rtp() - RTP_TARGET
        if abs(err) <= 1e-7:
            break
        flex_xs = [x for x in survivors if flex.contains(x) and survivors[x] >= 1]
        if not flex_xs:
            survivors[1.02] = survivors.get(1.02, 0) + 1
            continue
        src_hi, src_lo = max(flex_xs), min(flex_xs)
        if err > 0:
            if survivors[src_hi] > 1:
                take = min(survivors[src_hi] - 1, max(1, int(err * W / src_hi)))
                survivors[src_hi] -= take
            elif src_hi > src_lo + 1e-12 and survivors[src_hi] > 0:
                survivors[src_hi] -= 1
                survivors[src_lo] = survivors.get(src_lo, 0) + 1
            else:
                # Locked over budget: EV-transfer into flex, then burn flex next iters
                moved = False
                for band in sorted(locked, key=lambda b: -b.lo):
                    if _band_pts(band) <= band.budget_pts + 0.05:
                        continue
                    xs = [
                        x for x in survivors
                        if band_owns(band, x, cfg) and survivors[x] > 3
                        and (band is not top or abs(x - cfg.max_win) > 1e-12)
                    ]
                    if not xs:
                        continue
                    src = max(xs)
                    survivors[src] -= 1
                    # Spread EV into flex instead of piling on 1.02
                    pack = [1.02, 1.10, 1.22, 1.36, 1.58, 1.78]
                    for p in pack:
                        survivors[p] = survivors.get(p, 0) + max(1, int(round((src / len(pack)) / p)))
                    moved = True
                    break
                if not moved:
                    break
        else:
            take = max(1, int(-err * W / max(src_hi, 1e-9)))
            survivors[src_hi] = survivors.get(src_hi, 0) + take
    survivors = {x: w for x, w in survivors.items() if w > 0}
    _rebalance_locked_via_flex(0.15)

    # --- Endgame: unique → light conc → std inject → RTP ---
    def _rtp_close(max_iters: int = 50_000) -> None:
        for _ in range(max_iters):
            err = current_rtp() - RTP_TARGET
            if abs(err) <= 1e-6:
                break
            flex_xs = [x for x in survivors if flex.contains(x) and survivors[x] >= 1]
            if not flex_xs:
                survivors[1.02] = survivors.get(1.02, 0) + 1
                continue
            hi, lo = max(flex_xs), min(flex_xs)
            if err > 0:
                if survivors[hi] > 1:
                    take = min(survivors[hi] - 1, max(1, int(err * W / hi)))
                    survivors[hi] -= take
                    continue
                peeled = False
                rtp_v = current_rtp()
                second = sum(w * x * x for x, w in survivors.items()) / W
                s_now = math.sqrt(max(0.0, second - rtp_v * rtp_v))
                for band in sorted(locked, key=lambda b: -b.lo):
                    # Preserve std slack only when RTP is already nearly closed
                    floor_slack = 0.38 if (s_now < std_lo and abs(err) < 0.0005) else -0.30
                    if _band_pts(band) > band.budget_pts + floor_slack:
                        xs = [
                            x for x in survivors
                            if band_owns(band, x, cfg) and survivors[x] > 3
                            and (band is not top or abs(x - cfg.max_win) > 1e-12)
                        ]
                        if xs:
                            src = max(xs)
                            take = min(survivors[src] - 3, max(1, int(err * W / src)))
                            survivors[src] -= take
                            peeled = True
                            break
                if peeled:
                    continue
                if survivors.get(lo, 0) > 1 and lo > 1.0 + 1e-12:
                    survivors[lo] -= 1
                else:
                    break
            else:
                land = 1.08 if survivors.get(1.08, 0) <= survivors.get(1.0, 0) else 1.02
                if hi > lo and survivors[lo] > 1 and lo <= 1.02:
                    take = min(survivors[lo] - 1, max(1, int(-err * W / max(hi - lo, 0.05))))
                    survivors[lo] -= take
                    survivors[hi] = survivors.get(hi, 0) + take
                else:
                    survivors[land] = survivors.get(land, 0) + max(1, int(-err * W / land))

    def _unique_pad(rounds: int = 2_000) -> None:
        for _ in range(rounds):
            if sum(1 for w in survivors.values() if w > 0) >= cfg.min_unique:
                break
            progressed = False
            for band in cfg.band_budgets:
                if band.lo < 1e-12:
                    continue
                unused = [g for g in grid_all if survivors.get(g, 0) == 0 and band.contains(g)]
                heavies = [x for x, w in survivors.items() if w >= 2 and band_owns(band, x, cfg)]
                if unused and heavies:
                    h = max(heavies, key=lambda x: survivors[x])
                    t = min(unused, key=lambda g: abs(g - h))
                    take = min(max(1, survivors[h] // 8), survivors[h] - 1, 50)
                    survivors[h] -= take
                    survivors[t] = survivors.get(t, 0) + take
                    progressed = True
                    break
            if not progressed:
                for xs, pred in ((flex_grid, flex.contains), (rec_grid, recovery.contains)):
                    unused = [g for g in xs if survivors.get(g, 0) == 0]
                    heavies = [x for x, w in survivors.items() if w >= 2 and pred(x)]
                    if unused and heavies:
                        h = max(heavies, key=lambda x: survivors[x])
                        t = min(unused, key=lambda g: abs(g - h))
                        take = min(max(1, survivors[h] // 8), survivors[h] - 1, 50)
                        survivors[h] -= take
                        survivors[t] = survivors.get(t, 0) + take
                        progressed = True
                        break
            if not progressed:
                break

    def _light_conc(cap_frac: float = 0.075) -> None:
        for _ in range(80):
            nz = sum(survivors.values())
            if nz <= 0:
                break
            cap_w = max(3, int(cap_frac * nz))
            heavy = max((x for x in survivors if x > 0), key=lambda x: survivors[x], default=None)
            if heavy is None or survivors[heavy] <= cap_w:
                break
            if flex.contains(heavy):
                pack = [c for c in flex_grid if 0 < abs(c - heavy) <= 0.10]
            elif recovery.contains(heavy):
                pack = [c for c in rec_grid if 0 < abs(c - heavy) <= 0.08]
            else:
                owner = next((b for b in cfg.band_budgets if band_owns(b, heavy, cfg)), None)
                pack = [
                    c for c in grid_all
                    if c != heavy and owner is not None and band_owns(owner, c, cfg)
                    and abs(c - heavy) <= max(0.4, heavy * 0.06)
                ]
            pack = sorted(pack, key=lambda c: abs(c - heavy))[:10]
            if len(pack) < 2:
                break
            for c in pack:
                survivors.setdefault(c, 0)
            excess = survivors[heavy] - cap_w
            survivors[heavy] = cap_w
            base, rem = divmod(excess, len(pack))
            for i, x in enumerate(pack):
                survivors[x] = survivors.get(x, 0) + base + (1 if i < rem else 0)

    _unique_pad()
    _light_conc(0.075)
    _spread_locked_floors(0.065)
    _rebalance_locked_via_flex(0.12)
    _rtp_close(80_000)
    # Last hit push for modes still short on zero target
    if _stats()[0] > cfg.zero_rate + 0.014:
        _boost_locked_hit(mean_mult=1.18)
        if _stats()[0] > cfg.zero_rate + 0.014:
            _boost_locked_hit(mean_mult=1.10)
        _spread_locked_floors(0.065)
        _rebalance_locked_via_flex(0.12)
        _rtp_close(40_000)
    # Std inject if under floor (EV-exact flex→top); no further conc that raises EV
    rtp_v = current_rtp()
    second = sum(w * x * x for x, w in survivors.items()) / W
    s = math.sqrt(max(0.0, second - rtp_v * rtp_v))
    if s < std_lo:
        for __ in range(8_000):
            rtp_v = current_rtp()
            second = sum(w * x * x for x, w in survivors.items()) / W
            s = math.sqrt(max(0.0, second - rtp_v * rtp_v))
            if s >= std_lo + 0.02:
                break
            if _stats()[0] > cfg.zero_rate + 0.014:
                break
            donors = [x for x in flex_grid if survivors.get(x, 0) > 40]
            if not donors:
                break
            src = min(donors)
            # Prefer underweight high locked bands before top slack
            under = [
                b for b in sorted(locked, key=lambda b: -b.lo)
                if _band_pts(b) < b.budget_pts + 0.20
            ]
            dst = None
            if under:
                band = under[0]
                cands = [
                    x for x in grid_all
                    if band_owns(band, x, cfg)
                    and (band is not top or abs(x - cfg.max_win) > 1e-12)
                ]
                if cands:
                    dst = max(cands)
            if dst is None:
                if _band_pts(top) + cfg.max_win / W * 100 <= top.budget_pts + 0.38:
                    dst = cfg.max_win
                elif _band_pts(top) + teaser / W * 100 <= top.budget_pts + 0.38:
                    dst = teaser
                else:
                    bodies = [
                        x for x in survivors
                        if any(band_owns(b, x, cfg) for b in locked)
                        and x >= 5 and survivors[x] >= 1
                    ]
                    if not bodies:
                        break
                    dst = max(bodies)
            cost = max(1, int(round(dst / max(src, 1e-9))))
            if survivors[src] <= cost + 2:
                break
            survivors[src] -= cost
            survivors[dst] = survivors.get(dst, 0) + 1
            for band in locked:
                if band_owns(band, dst, cfg) and _band_pts(band) > band.budget_pts + 0.39:
                    others = [
                        x for x in survivors
                        if band_owns(band, x, cfg) and x != dst and survivors[x] > 3
                    ]
                    if others:
                        survivors[max(others)] -= 1
                    break
        # Barbell locked bands at constant weight (raises E[X²] without raising zero)
        _barbell_locked(rounds=6_000)
        rtp_v = current_rtp()
        second = sum(w * x * x for x, w in survivors.items()) / W
        s = math.sqrt(max(0.0, second - rtp_v * rtp_v))
        # Reverse-boost locked means if zero still has headroom (raises E[X²])
        for band in locked:
            floor = _band_floor(band)
            for __ in range(2_000):
                if _stats()[0] > cfg.zero_rate + 0.012:
                    break
                rtp_v = current_rtp()
                second = sum(w * x * x for x, w in survivors.items()) / W
                if math.sqrt(max(0.0, second - rtp_v * rtp_v)) >= std_lo:
                    break
                if survivors.get(floor, 0) <= 8:
                    break
                his = [
                    x for x in grid_all
                    if band.contains(x) and x > floor + 0.5
                    and (band is not top or abs(x - cfg.max_win) > 1e-12)
                ]
                if not his:
                    break
                hi_b = max(his)
                a = max(1, int(0.0004 * W))
                b = max(1, int(round(a * floor / hi_b)))
                if survivors[floor] <= a + 3:
                    break
                survivors[floor] -= a
                survivors[hi_b] = survivors.get(hi_b, 0) + b
            _tune_ev(band, band.budget_pts, low_mean=False, body_only=(band is top), keep_p=True)
        rtp_v = current_rtp()
        second = sum(w * x * x for x, w in survivors.items()) / W
        s = math.sqrt(max(0.0, second - rtp_v * rtp_v))
        # Allow modest locked slack (+0.30) funded from flex for std center
        if s < std_lo:
            for band in sorted(locked, key=lambda b: -b.lo):
                if _band_pts(band) >= band.budget_pts + 0.28:
                    continue
                _tune_ev(
                    band,
                    min(band.budget_pts + 0.30, band.budget_pts + max(0.05, (std_lo - s) * 2)),
                    low_mean=False,
                    body_only=(band is top),
                    keep_p=False,
                )
            remain_pts = (RTP_TARGET - _non_flex_ev()) * 100.0
            _tune_ev(flex, remain_pts, low_mean=False, keep_p=(_stats()[0] > cfg.zero_rate + 0.01))
    # Keep bands inside ±0.35 (validator ±0.4) without undoing intentional std slack
    _rebalance_locked_via_flex(0.32)
    _unique_pad(800)
    _spread_locked_floors(0.06)
    _rebalance_locked_via_flex(0.32)
    _rtp_close(100_000)
    if abs(_band_pts(recovery) - recovery.budget_pts) > 0.35:
        z_now = _stats()[0]
        p_sub = cfg.break_even - z_now - _band_p(tiny)
        p_sub = min(
            recovery.budget_ev / min(rec_grid) * 0.998,
            max(recovery.budget_ev / max(rec_grid) * 1.002, p_sub),
        )
        _place_shaped(recovery, rec_grid, recovery.budget_pts, p_sub)
        _rtp_close(40_000)

    survivors = {x: w for x, w in survivors.items() if w > 0}
    _rebalance_locked_via_flex(0.32)
    # Absolute RTP force-close (hard constraint) — flex first; locked→flex transfer never peel-to-zero
    for _ in range(50_000):
        err = current_rtp() - RTP_TARGET
        if abs(err) <= 1e-6:
            break
        if err > 0:
            flex_hi = [x for x in survivors if flex.contains(x) and survivors[x] > 1]
            if flex_hi:
                src = max(flex_hi)
                take = min(survivors[src] - 1, max(1, int(err * W / src)))
                survivors[src] -= take
                continue
            # Transfer locked excess into flex, then burn next iter
            moved = False
            for band in sorted(locked, key=lambda b: -_band_pts(b) + b.budget_pts):
                if _band_pts(band) <= band.budget_pts + 0.02:
                    continue
                xs = [
                    x for x in survivors
                    if band_owns(band, x, cfg) and survivors[x] > 3
                    and (band is not top or abs(x - cfg.max_win) > 1e-12)
                ]
                if not xs:
                    continue
                src = max(xs)
                survivors[src] -= 1
                pack = [1.02, 1.10, 1.22, 1.36, 1.58, 1.78]
                for p in pack:
                    survivors[p] = survivors.get(p, 0) + max(1, int(round((src / len(pack)) / p)))
                moved = True
                break
            if moved:
                continue
            rtp_v = current_rtp()
            second = sum(w * x * x for x, w in survivors.items()) / W
            s_now = math.sqrt(max(0.0, second - rtp_v * rtp_v))
            cands = [
                x for x, w in survivors.items()
                if w > 1 and x > 0
                and not (s_now < std_lo and band_owns(top, x, cfg))
            ]
            if not cands:
                cands = [x for x, w in survivors.items() if w > 1 and x > 0]
            if not cands:
                break
            src = max(cands)
            take = min(survivors[src] - 1, max(1, int(err * W / src)))
            survivors[src] -= take
        else:
            survivors[1.02] = survivors.get(1.02, 0) + max(1, int(-err * W / 1.02))
    survivors = {x: w for x, w in survivors.items() if w > 0}
    _sanitize_flex_conc(0.055)
    _spread_locked_floors(0.055)
    # --- Final polish: hit window + std floor + RTP ---
    for _ in range(8_000):
        z, be, _ = _stats()
        if z <= cfg.zero_rate + 0.014:
            break
        add = max(1, int((z - cfg.zero_rate) * W * 0.2))
        pack = [round(1.02 + 0.02 * i, 2) for i in range(12)]
        base, rem = divmod(add, len(pack))
        for i, x in enumerate(pack):
            survivors[x] = survivors.get(x, 0) + base + (1 if i < rem else 0)
        # Pay for EV via hi→lo (preserves the new hit mass)
        need_ev = add * 1.12 / W
        shifted = 0.0
        for __ in range(5_000):
            if shifted >= need_ev - 1e-15:
                break
            his = [x for x in survivors if flex.contains(x) and x >= 1.3 and survivors[x] > 2]
            if not his:
                his = [x for x in survivors if flex.contains(x) and x > 1.10 + 1e-12 and survivors[x] > 2]
            if not his:
                break
            src = max(his)
            lo = 1.02
            take = min(survivors[src] - 2, max(1, int((need_ev - shifted) * W / max(src - lo, 1e-9))))
            if take < 1:
                break
            survivors[src] -= take
            survivors[lo] = survivors.get(lo, 0) + take
            shifted += take * (src - lo) / W
    _sanitize_flex_conc(0.055)
    for _ in range(12_000):
        rtp_v = current_rtp()
        second = sum(w * x * x for x, w in survivors.items()) / W
        s = math.sqrt(max(0.0, second - rtp_v * rtp_v))
        if s >= std_lo + 0.015:
            break
        # Don't sacrifice hit for std when zero is already high
        if _stats()[0] > cfg.zero_rate + 0.008:
            break
        donors = [x for x in survivors if flex.contains(x) and x <= 1.20 and survivors[x] > 30]
        if not donors:
            donors = [x for x in survivors if flex.contains(x) and survivors[x] > 30]
        if not donors:
            break
        src = min(donors)
        # Prefer underweight high locked, else top body/max
        under = [b for b in sorted(locked, key=lambda b: -b.lo) if _band_pts(b) < b.budget_pts + 0.35]
        dst = None
        owner = None
        if under:
            owner = under[0]
            cands = [
                x for x in grid_all
                if band_owns(owner, x, cfg) and (owner is not top or abs(x - cfg.max_win) > 1e-12)
            ]
            if cands:
                dst = max(cands)
        if dst is None:
            owner = top
            if _band_pts(top) + cfg.max_win / W * 100 <= top.budget_pts + 0.38:
                dst = cfg.max_win
            else:
                cands = [
                    x for x in grid_all
                    if band_owns(top, x, cfg) and abs(x - cfg.max_win) > 1e-12
                ]
                if not cands or _band_pts(top) >= top.budget_pts + 0.38:
                    break
                dst = max(cands)
        cost = max(1, int(round(dst / max(src, 1e-9))))
        if survivors[src] <= cost + 2:
            break
        survivors[src] -= cost
        survivors[dst] = survivors.get(dst, 0) + 1
        if owner is not None and _band_pts(owner) > owner.budget_pts + 0.39:
            survivors[dst] -= 1
            survivors[src] += cost
            break
    rtp_v = current_rtp()
    second = sum(w * x * x for x, w in survivors.items()) / W
    s = math.sqrt(max(0.0, second - rtp_v * rtp_v))
    if s < target_std:
        _barbell_locked(rounds=10_000)
        # Stop if we overshot the std ceiling
        rtp_v = current_rtp()
        second = sum(w * x * x for x, w in survivors.items()) / W
        s = math.sqrt(max(0.0, second - rtp_v * rtp_v))
        if s > std_hi:
            # Reverse-barbell: pull mass from poles toward mid on locked bands
            for band in locked:
                floor = _band_floor(band)
                his = [
                    x for x in survivors
                    if band_owns(band, x, cfg) and survivors[x] > 3 and x > floor + 1e-12
                ]
                if not his or survivors.get(floor, 0) < 4:
                    continue
                hi = max(his)
                mid = (floor + hi) / 2
                mid_t = min(
                    (x for x in grid_all if band_owns(band, x, cfg)),
                    key=lambda x: abs(x - mid),
                    default=None,
                )
                if mid_t is None:
                    continue
                for __ in range(3_000):
                    rtp_v = current_rtp()
                    second = sum(w * x * x for x, w in survivors.items()) / W
                    if math.sqrt(max(0.0, second - rtp_v * rtp_v)) <= target_std + 0.05:
                        break
                    if survivors.get(floor, 0) < 4 or survivors.get(hi, 0) < 4:
                        break
                    survivors[floor] -= 1
                    survivors[hi] -= 1
                    survivors[mid_t] = survivors.get(mid_t, 0) + 2
                _tune_ev(band, band.budget_pts, low_mean=False, keep_p=True)
    _spread_locked_floors(0.055)
    _sanitize_flex_conc(0.055)
    # Re-close RTP after conc sanitization (sanitize can nudge EV)
    for _ in range(80_000):
        err = current_rtp() - RTP_TARGET
        if abs(err) <= 1e-7:
            break
        if err > 0:
            flex_hi = [
                x for x in survivors
                if flex.contains(x) and x >= 1.02 - 1e-12 and survivors[x] > 1
            ]
            if flex_hi:
                src = max(flex_hi)
                take = min(survivors[src] - 1, max(1, int(err * W / max(src, 1e-9))))
                survivors[src] -= take
                continue
            cands = [
                x for x, w in survivors.items()
                if w > 1 and x > 0 and not band_owns(top, x, cfg)
            ]
            if not cands:
                cands = [x for x, w in survivors.items() if w > 1 and x > 0]
            if not cands:
                break
            src = max(cands)
            survivors[src] -= min(survivors[src] - 1, max(1, int(err * W / src)))
        else:
            survivors[1.08] = survivors.get(1.08, 0) + max(1, int(-err * W / 1.08))
    _sanitize_flex_conc(0.055)
    # Tiny std top-up if still under floor
    for _ in range(4_000):
        rtp_v = current_rtp()
        second = sum(w * x * x for x, w in survivors.items()) / W
        s = math.sqrt(max(0.0, second - rtp_v * rtp_v))
        if s >= std_lo:
            break
        _barbell_locked(rounds=500)
        err = current_rtp() - RTP_TARGET
        if abs(err) > 1e-6:
            flex_hi = [x for x in survivors if flex.contains(x) and survivors[x] > 1]
            if err > 0 and flex_hi:
                survivors[max(flex_hi)] -= max(1, int(err * W / max(flex_hi)))
            elif err < 0:
                survivors[1.12] = survivors.get(1.12, 0) + max(1, int(-err * W / 1.12))
    # Absolute final RTP snap — prefer hi→lo (preserves hit); burn only if needed
    def _force_rtp() -> None:
        for _ in range(500_000):
            err = current_rtp() - RTP_TARGET
            if abs(err) <= 1e-9:
                return
            flex_xs = [x for x, w in survivors.items() if flex.contains(x) and w >= 1]
            if err > 0:
                if flex_xs:
                    hi = max(flex_xs)
                    lows = sorted(x for x in flex_xs if x < hi - 1e-12)[:8]
                    if lows and hi > min(lows) + 1e-12 and survivors[hi] >= 1:
                        take = min(survivors[hi], max(1, int(round(err * W / max(hi - min(lows), 1e-9)))))
                        survivors[hi] -= take
                        if survivors[hi] <= 0:
                            del survivors[hi]
                        base, rem = divmod(take, len(lows))
                        for i, x in enumerate(lows):
                            survivors[x] = survivors.get(x, 0) + base + (1 if i < rem else 0)
                        continue
                    # All flex already flat: burn weight
                    src = hi
                    take = min(survivors[src], max(1, int(round(err * W / src))))
                    survivors[src] -= take
                    if survivors[src] <= 0:
                        del survivors[src]
                    continue
                xs = [x for x, w in survivors.items() if w >= 1 and x > 0]
                pool = [x for x in xs if not band_owns(top, x, cfg)] or xs
                if not pool:
                    return
                src = max(pool)
                take = min(survivors[src], max(1, int(round(err * W / src))))
                survivors[src] -= take
                if survivors[src] <= 0:
                    del survivors[src]
            else:
                if flex_xs:
                    hi = max(flex_xs)
                    lows = sorted(x for x in flex_xs if x < hi - 1e-12)[:8]
                    if lows and survivors.get(min(lows), 0) >= 1:
                        lo = min(lows)
                        take = min(survivors[lo], max(1, int(round(-err * W / max(hi - lo, 1e-9)))))
                        survivors[lo] -= take
                        if survivors[lo] <= 0:
                            del survivors[lo]
                        survivors[hi] = survivors.get(hi, 0) + take
                        continue
                pack = [1.12, 1.18, 1.24, 1.30, 1.36]
                add = max(1, int(round(-err * W / 1.24)))
                base, rem = divmod(add, len(pack))
                for i, x in enumerate(pack):
                    survivors[x] = survivors.get(x, 0) + base + (1 if i < rem else 0)

    _sanitize_flex_conc(0.055)
    # Hit rescue before final snap (zeros → spread flex, then hi→lo for EV)
    for _ in range(6_000):
        z = 1.0 - sum(survivors.values()) / W
        if z <= cfg.zero_rate + 0.014:
            break
        add = max(1, int((z - cfg.zero_rate) * W * 0.15))
        # Spread new hits across low flex pack (avoid 1.02/1.04 piles)
        pack = [round(1.02 + 0.02 * i, 2) for i in range(10)]
        base, rem = divmod(add, len(pack))
        for i, x in enumerate(pack):
            survivors[x] = survivors.get(x, 0) + base + (1 if i < rem else 0)
        need = add * 1.10 / W  # approx mean of pack
        shifted = 0.0
        for __ in range(5_000):
            if shifted >= need - 1e-15:
                break
            flex_xs = [x for x in survivors if flex.contains(x) and survivors[x] >= 1]
            if len(flex_xs) < 2:
                break
            hi, lo = max(flex_xs), min(flex_xs)
            if hi <= lo + 1e-12 or survivors[hi] < 1:
                break
            take = min(survivors[hi], max(1, int((need - shifted) * W / max(hi - lo, 1e-9))))
            survivors[hi] -= take
            if survivors[hi] <= 0:
                del survivors[hi]
            survivors[lo] = survivors.get(lo, 0) + take
            shifted += take * (hi - lo) / W
    _sanitize_flex_conc(0.055)
    # Std hair-fix if under floor (barbell only)
    rtp_v = current_rtp()
    second = sum(w * x * x for x, w in survivors.items()) / W
    s = math.sqrt(max(0.0, second - rtp_v * rtp_v))
    if s < std_lo:
        _barbell_locked(rounds=8_000)
    _unique_pad(4_000)
    _spread_locked_floors(0.055)
    _sanitize_flex_conc(0.055)
    _unique_pad(2_000)
    _sanitize_flex_conc(0.055)
    _force_rtp()
    # Hard residual close with large steps; spread lo-side to avoid 1.02 piles
    for _ in range(50_000):
        err = current_rtp() - RTP_TARGET
        if abs(err) <= 1e-9:
            break
        if err > 0:
            flex_xs = [x for x, w in survivors.items() if flex.contains(x) and w >= 1]
            if len(flex_xs) >= 2 and max(flex_xs) > min(flex_xs) + 1e-12:
                hi = max(flex_xs)
                # Spread onto several lows, not a single 1.02 dump
                lows = sorted(x for x in flex_xs if x < hi - 1e-12)[:6]
                if not lows:
                    lows = [min(flex_xs)]
                take = min(survivors[hi], max(1, int(round(err * W / max(hi - min(lows), 1e-9)))))
                survivors[hi] -= take
                if survivors[hi] <= 0:
                    del survivors[hi]
                base, rem = divmod(take, len(lows))
                for i, x in enumerate(lows):
                    survivors[x] = survivors.get(x, 0) + base + (1 if i < rem else 0)
            elif flex_xs:
                src = max(flex_xs)
                take = min(survivors[src], max(1, int(round(err * W / src))))
                survivors[src] -= take
                if survivors[src] <= 0:
                    del survivors[src]
            else:
                xs = [x for x, w in survivors.items() if w >= 1 and x > 0]
                if not xs:
                    break
                src = max(xs)
                take = min(survivors[src], max(1, int(round(err * W / src))))
                survivors[src] -= take
                if survivors[src] <= 0:
                    del survivors[src]
        else:
            pack = [1.12, 1.18, 1.24, 1.30, 1.36]
            add = max(1, int(round(-err * W / 1.24)))
            base, rem = divmod(add, len(pack))
            for i, x in enumerate(pack):
                survivors[x] = survivors.get(x, 0) + base + (1 if i < rem else 0)
    _unique_pad(1_500)
    _sanitize_flex_conc(0.055)
    # Final snap — burn-only on flex (no hi→lo re-pile), then micro
    for _ in range(100_000):
        err = current_rtp() - RTP_TARGET
        if abs(err) <= 1e-9:
            break
        if err > 0:
            flex_xs = [x for x, w in survivors.items() if flex.contains(x) and w >= 1]
            pool = flex_xs or [x for x, w in survivors.items() if w >= 1 and x > 0]
            if not pool:
                break
            src = max(pool)
            take = min(survivors[src], max(1, int(round(err * W / src))))
            survivors[src] -= take
            if survivors[src] <= 0:
                del survivors[src]
        else:
            survivors[1.24] = survivors.get(1.24, 0) + max(1, int(round(-err * W / 1.24)))
    _sanitize_flex_conc(0.055)
    for _ in range(100_000):
        err = current_rtp() - RTP_TARGET
        if abs(err) <= 1e-9:
            break
        if err > 0:
            xs = [x for x, w in survivors.items() if w >= 1 and x > 0]
            flex_xs = [x for x in xs if flex.contains(x)]
            pool = flex_xs or xs
            if not pool:
                break
            src = max(pool)
            take = min(survivors[src], max(1, int(round(err * W / src))))
            survivors[src] -= take
            if survivors[src] <= 0:
                del survivors[src]
        else:
            survivors[1.24] = survivors.get(1.24, 0) + 1
    survivors = {x: w for x, w in survivors.items() if w > 0}
    # Last locked-floor conc break (validator ≤8%); keep_p retune preserves hit
    _spread_locked_floors(0.075)
    # BE polish: move recovery → flex if break-even is high
    for _ in range(8_000):
        z, be, _ = _stats()
        if be <= cfg.break_even + 0.014:
            break
        rec_xs = [x for x in survivors if recovery.contains(x) and survivors[x] > 3]
        if not rec_xs:
            break
        src = max(rec_xs)
        take = min(survivors[src] - 3, max(1, int((be - cfg.break_even) * W * 0.25)))
        survivors[src] -= take
        # Land in low flex (leaves BE, preserves most hit)
        pack = [1.02, 1.04, 1.06, 1.08, 1.10, 1.12]
        base, rem = divmod(take, len(pack))
        for i, x in enumerate(pack):
            survivors[x] = survivors.get(x, 0) + base + (1 if i < rem else 0)
        # Restore recovery EV via keep_p (raise mean of remaining)
        _tune_ev(recovery, recovery.budget_pts, low_mean=False, keep_p=True)
    for _ in range(30_000):
        err = current_rtp() - RTP_TARGET
        if abs(err) <= 1e-9:
            break
        flex_xs = [x for x, w in survivors.items() if flex.contains(x) and w >= 1]
        if err > 0 and len(flex_xs) >= 2 and max(flex_xs) > min(flex_xs) + 1e-12:
            hi = max(flex_xs)
            lows = sorted(x for x in flex_xs if x < hi - 1e-12)[:8]
            take = min(survivors[hi], max(1, int(round(err * W / max(hi - min(lows), 1e-9)))))
            survivors[hi] -= take
            if survivors[hi] <= 0:
                del survivors[hi]
            base, rem = divmod(take, len(lows))
            for i, x in enumerate(lows):
                survivors[x] = survivors.get(x, 0) + base + (1 if i < rem else 0)
        elif err > 0 and flex_xs:
            src = max(flex_xs)
            take = min(survivors[src], max(1, int(round(err * W / src))))
            survivors[src] -= take
            if survivors[src] <= 0:
                del survivors[src]
        elif err < 0:
            survivors[1.24] = survivors.get(1.24, 0) + max(1, int(round(-err * W / 1.24)))
        else:
            break
    _sanitize_flex_conc(0.055)
    for _ in range(20_000):
        err = current_rtp() - RTP_TARGET
        if abs(err) <= 1e-9:
            break
        flex_xs = [x for x, w in survivors.items() if flex.contains(x) and w >= 1]
        if err > 0 and len(flex_xs) >= 2 and max(flex_xs) > min(flex_xs) + 1e-12:
            hi = max(flex_xs)
            lows = sorted(x for x in flex_xs if x < hi - 1e-12)[:8]
            take = min(survivors[hi], max(1, int(round(err * W / max(hi - min(lows), 1e-9)))))
            survivors[hi] -= take
            if survivors[hi] <= 0:
                del survivors[hi]
            base, rem = divmod(take, len(lows))
            for i, x in enumerate(lows):
                survivors[x] = survivors.get(x, 0) + base + (1 if i < rem else 0)
        elif err > 0 and flex_xs:
            src = max(flex_xs)
            take = min(survivors[src], max(1, int(round(err * W / src))))
            survivors[src] -= take
            if survivors[src] <= 0:
                del survivors[src]
        elif err < 0:
            survivors[1.24] = survivors.get(1.24, 0) + 1
        else:
            break
    # Restore unique + std hair without concentration collapse
    _unique_pad(3_000)
    rtp_v = current_rtp()
    second = sum(w * x * x for x, w in survivors.items()) / W
    s = math.sqrt(max(0.0, second - rtp_v * rtp_v))
    if s < std_lo:
        _barbell_locked(rounds=6_000)
    for _ in range(20_000):
        err = current_rtp() - RTP_TARGET
        if abs(err) <= 1e-9:
            break
        flex_xs = [x for x, w in survivors.items() if flex.contains(x) and w >= 1]
        if err > 0 and len(flex_xs) >= 2 and max(flex_xs) > min(flex_xs) + 1e-12:
            hi = max(flex_xs)
            lows = sorted(x for x in flex_xs if x < hi - 1e-12)[:8]
            take = min(survivors[hi], max(1, int(round(err * W / max(hi - min(lows), 1e-9)))))
            survivors[hi] -= take
            if survivors[hi] <= 0:
                del survivors[hi]
            base, rem = divmod(take, len(lows))
            for i, x in enumerate(lows):
                survivors[x] = survivors.get(x, 0) + base + (1 if i < rem else 0)
        elif err > 0 and flex_xs:
            src = max(flex_xs)
            take = min(survivors[src], max(1, int(round(err * W / src))))
            survivors[src] -= take
            if survivors[src] <= 0:
                del survivors[src]
        elif err < 0:
            survivors[1.24] = survivors.get(1.24, 0) + 1
        else:
            break
    survivors = {x: w for x, w in survivors.items() if w > 0}
    w0 = W - sum(survivors.values())
    assert abs(current_rtp() - RTP_TARGET) <= 1e-5, (
        f"{cfg.name} RTP final {current_rtp()} "
        f"shares={[(b.lo, round(_band_pts(b), 2)) for b in cfg.band_budgets]}"
    )
    out = [Outcome(0.0, w0)]
    out.extend(Outcome(x, survivors[x]) for x in sorted(survivors))
    return out





def _metrics(outcomes: list[Outcome]) -> dict:
    W = TOTAL_WEIGHT
    rtp = sum(o.weight * o.multiplier for o in outcomes) / W
    hit = sum(o.weight for o in outcomes if o.multiplier > 0) / W
    zero = sum(o.weight for o in outcomes if o.multiplier == 0) / W
    be = sum(o.weight for o in outcomes if o.multiplier < 1.0) / W
    second = sum(o.weight * o.multiplier * o.multiplier for o in outcomes) / W
    std = math.sqrt(max(0.0, second - rtp * rtp))
    return {
        "rtp": rtp,
        "hit_rate": hit,
        "zero_rate": zero,
        "break_even": be,
        "std": std,
        "max": max(o.multiplier for o in outcomes),
        "unique": sum(1 for o in outcomes if o.weight > 0 and o.multiplier > 0),
        "etl40": sum(o.weight * o.multiplier for o in outcomes if o.multiplier >= 40) / W,
    }


def _band_shares(outcomes: list[Outcome], cfg: ModeConfig) -> list[tuple[BandBudget, float]]:
    W = TOTAL_WEIGHT
    return [
        (
            band,
            sum(
                o.weight * o.multiplier
                for o in outcomes
                if band_owns(band, o.multiplier, cfg)
            )
            / W
            * 100,
        )
        for band in cfg.band_budgets
    ]


def generate_mode(cfg: ModeConfig) -> tuple[list[Outcome], dict]:
    grid = build_grid(cfg)
    std_lo, std_hi = cfg.std_range
    target_std = (std_lo + std_hi) / 2
    lo_b, hi_b = 0.3, 3.0
    best: tuple[list[Outcome], dict] | None = None
    best_score = float("inf")

    def _score(outcomes: list[Outcome], meta: dict) -> float:
        std_pen = abs(meta["std"] - target_std) * (1.0 if std_lo <= meta["std"] <= std_hi else 10.0)
        be_pen = abs(meta["break_even"] - cfg.break_even)
        z_pen = abs(meta["zero_rate"] - cfg.zero_rate)
        u_pen = max(0, cfg.min_unique - meta["unique"]) * 0.5
        band_pen = 0.0
        for b, pts in _band_shares(outcomes, cfg):
            if b.budget_pts > 0 and pts <= 1e-9:
                band_pen += 50.0  # empty budgeted band is catastrophic
            else:
                band_pen += abs(pts - b.budget_pts)
        etl_pen = max(0.0, meta["etl40"] - _etl40_target(cfg)) * 100
        nz = sum(o.weight for o in outcomes if o.multiplier > 0)
        conc_pen = 0.0
        if nz:
            mx = max((o.weight / nz for o in outcomes if o.multiplier > 0), default=0.0)
            conc_pen = max(0.0, mx - 0.075) * 200
        return std_pen + be_pen * 20 + z_pen * 5 + u_pen + band_pen * 8 + etl_pen + conc_pen

    for _ in range(48):
        beta_tail = (lo_b + hi_b) / 2
        probs = _build_probs(cfg, grid, beta_tail)
        outcomes = _to_integer_weights(probs, cfg)
        meta = _metrics(outcomes)
        sc = _score(outcomes, meta)
        if sc < best_score:
            best_score = sc
            best = (outcomes, meta)
        if meta["std"] > target_std:
            lo_b = beta_tail
        else:
            hi_b = beta_tail
        if std_lo <= meta["std"] <= std_hi:
            if abs(meta["zero_rate"] - cfg.zero_rate) <= 0.015:
                if abs(meta["break_even"] - cfg.break_even) <= 0.005:
                    bands_ok = all(
                        abs(pts - b.budget_pts) <= 0.4 for b, pts in _band_shares(outcomes, cfg)
                    )
                    if meta["unique"] >= cfg.min_unique and bands_ok:
                        nz = sum(o.weight for o in outcomes if o.multiplier > 0)
                        mx = max((o.weight / nz for o in outcomes if o.multiplier > 0), default=0.0) if nz else 0.0
                        if mx <= 0.08:
                            best = (outcomes, meta)
                            break

    assert best is not None
    return best


def write_mode_csv(name: str, outcomes: list[Outcome], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["multiplier", "weight"])
        for o in outcomes:
            if o.multiplier == 0:
                mult_s = "0.00"
            elif o.multiplier < 10:
                # Keep up to 3 decimals so 0.025-grid recovery points round-trip
                mult_s = f"{o.multiplier:.3f}".rstrip("0").rstrip(".")
                if "." not in mult_s:
                    mult_s += ".00"
                elif len(mult_s.split(".")[1]) == 1:
                    mult_s += "0"
            elif o.multiplier < 100:
                mult_s = f"{o.multiplier:.1f}"
            else:
                mult_s = f"{o.multiplier:.0f}"
            w.writerow([mult_s, o.weight])


def config_hash(cfgs: list[ModeConfig]) -> str:
    blob = json.dumps(
        {
            "version": VERSION,
            "modes": [
                {
                    "name": c.name,
                    "max_win": c.max_win,
                    "zero_rate": c.zero_rate,
                    "break_even": c.break_even,
                    "std_range": c.std_range,
                    "bands": [(b.lo, b.hi, b.budget_pts, b.kind) for b in c.band_budgets],
                    "fallback": c.use_idle_fallback,
                }
                for c in cfgs
            ],
        },
        sort_keys=True,
    )
    return hashlib.sha256(blob.encode()).hexdigest()


def generate_all(*, idle_fallback: bool = False) -> dict:
    cfgs = all_mode_configs(idle_fallback=idle_fallback)
    BOOKS_DIR.mkdir(parents=True, exist_ok=True)
    results = {}
    for cfg in cfgs:
        outcomes, meta = generate_mode(cfg)
        path = BOOKS_DIR / f"{cfg.name}_v4.csv"
        write_mode_csv(cfg.name, outcomes, path)
        results[cfg.name] = {
            "path": str(path.relative_to(HERE)),
            "metrics": meta,
            "n_outcomes": len(outcomes),
            "max_win": cfg.max_win,
        }
        print(
            f"{cfg.name:>10}: RTP={meta['rtp']:.6f} hit={meta['hit_rate']:.3f} "
            f"zero={meta['zero_rate']:.3f} be={meta['break_even']:.3f} "
            f"std={meta['std']:.4f} unique={meta['unique']} max={meta['max']}"
        )

    manifest = {
        "version": VERSION,
        "total_weight": TOTAL_WEIGHT,
        "rtp_target": RTP_TARGET,
        "config_hash": config_hash(cfgs),
        "idle_fallback": idle_fallback,
        "modes": results,
    }
    (BOOKS_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Overheat math v4 weight books")
    parser.add_argument("--idle-fallback", action="store_true")
    args = parser.parse_args()
    generate_all(idle_fallback=args.idle_fallback)


if __name__ == "__main__":
    main()
