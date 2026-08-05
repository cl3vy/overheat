"""Overheat math v4.0.0 — mode configs and RTP band budgets (spec §§4, 6)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

VERSION = "4.0.0"
RTP_TARGET = 0.9650
TOTAL_WEIGHT = 100_000_000  # W per mode

# Mode order IDLE → PLASMA (ladder invariants)
MODE_ORDER = [
    "idle",
    "eco",
    "standard",
    "boost",
    "overclock",
    "nitro",
    "furnace",
    "inferno",
    "meltdown",
    "reactor",
    "plasma",
]

# Cash-out targets (frontend / book boot.targetTemp) — unchanged from v3
MODE_TARGET: dict[str, float] = {
    "idle": 1.2,
    "eco": 1.5,
    "standard": 2.0,
    "boost": 3.0,
    "overclock": 5.0,
    "nitro": 7.0,
    "furnace": 10.0,
    "inferno": 15.0,
    "meltdown": 25.0,
    "reactor": 50.0,
    "plasma": 100.0,
}

AnchorSet = frozenset(
    {
        0.20,
        0.50,
        1.00,
        1.20,
        1.50,
        2.00,
        2.50,
        3.00,
        5.00,
        7.50,
        10,
        15,
        20,
        25,
        30,
        40,
        50,
        75,
        100,
        150,
        250,
        500,
        1000,
        2500,
    }
)

BandKind = Literal["open", "half", "closed"]


@dataclass(frozen=True)
class BandBudget:
    """One RTP contribution band for a mode.

    lo/hi describe the multiplier interval. kind:
      - open: (lo, hi) exclusive both ends — used for (0, 0.1)
      - half: [lo, hi) half-open
      - closed: [lo, hi] inclusive (top band closed at mode max)
    budget_pts: RTP percentage points (column of matrix 4.3).
    """

    lo: float
    hi: float
    budget_pts: float
    kind: BandKind = "half"

    @property
    def budget_ev(self) -> float:
        return self.budget_pts / 100.0

    def contains(self, x: float) -> bool:
        if self.kind == "open":
            return self.lo < x < self.hi
        if self.kind == "half":
            return self.lo <= x < self.hi
        return self.lo <= x <= self.hi


@dataclass
class ModeConfig:
    name: str
    max_win: float
    zero_rate: float
    break_even: float
    std_range: tuple[float, float]
    etl40_cap: float
    band_share_cap: float
    min_unique: int
    band_budgets: list[BandBudget]
    use_idle_fallback: bool = False

    @property
    def target(self) -> float:
        return MODE_TARGET[self.name]

    @property
    def teaser(self) -> float:
        """0.85 × max, rounded per §6.1 rule."""
        import grid as grid_mod

        return grid_mod.round_multiplier(0.85 * self.max_win)


def _bands(*rows: tuple[float, float, float, BandKind]) -> list[BandBudget]:
    return [BandBudget(lo, hi, pts, kind) for lo, hi, pts, kind in rows]


# Primary budgets (§4.3). Column sums asserted = 96.5.
_PRIMARY: dict[str, list[BandBudget]] = {
    "idle": _bands(
        (0.0, 0.1, 0.1, "open"),
        (0.1, 1.0, 6.1, "half"),
        (1.0, 2.0, 62.0, "half"),
        (2.0, 5.0, 18.0, "half"),
        (5.0, 10.0, 5.5, "half"),
        (10.0, 20.0, 4.8, "half"),  # half-open at max; max attributed to top
    ),
    "eco": _bands(
        (0.0, 0.1, 0.1, "open"),
        (0.1, 1.0, 6.1, "half"),  # -1pt from recovery → [1,2)
        (1.0, 2.0, 49.0, "half"),
        (2.0, 5.0, 26.0, "half"),
        (5.0, 10.0, 8.0, "half"),
        (10.0, 25.0, 7.3, "half"),
    ),
    "standard": _bands(
        (0.0, 0.1, 0.1, "open"),
        (0.1, 1.0, 6.9, "half"),  # -1pt from recovery → [1,2)
        (1.0, 2.0, 23.0, "half"),
        (2.0, 5.0, 45.0, "half"),
        (5.0, 10.0, 12.0, "half"),
        (10.0, 30.0, 9.5, "half"),
    ),
    "boost": _bands(
        (0.0, 0.1, 0.1, "open"),
        (0.1, 1.0, 7.5, "half"),  # -1pt from recovery → [1,2) (BE center)
        (1.0, 2.0, 15.0, "half"),
        (2.0, 5.0, 40.0, "half"),
        (5.0, 10.0, 18.0, "half"),
        (10.0, 20.0, 9.0, "half"),
        (20.0, 40.0, 6.9, "half"),  # [20,40); max 40 attributed to top
    ),
    "overclock": _bands(
        (0.0, 0.1, 0.1, "open"),
        (0.1, 1.0, 6.4, "half"),  # -1.5pt from recovery → [1,2) (BE center)
        (1.0, 2.0, 12.5, "half"),
        (2.0, 5.0, 20.0, "half"),
        (5.0, 10.0, 33.0, "half"),
        (10.0, 20.0, 13.0, "half"),
        (20.0, 50.0, 11.5, "half"),
    ),
    "nitro": _bands(
        (0.0, 0.1, 0.1, "open"),
        (0.1, 1.0, 6.5, "half"),  # -1pt from recovery → [1,2)
        (1.0, 2.0, 11.0, "half"),
        (2.0, 5.0, 18.0, "half"),
        (5.0, 10.0, 30.0, "half"),
        (10.0, 20.0, 15.0, "half"),
        (20.0, 50.0, 10.0, "half"),
        (50.0, 75.0, 5.9, "half"),
    ),
    "furnace": _bands(
        (0.0, 0.1, 0.1, "open"),
        (0.1, 1.0, 5.9, "half"),  # -1pt from recovery → [1,2)
        (1.0, 2.0, 10.0, "half"),
        (2.0, 5.0, 16.0, "half"),
        (5.0, 10.0, 14.0, "half"),
        (10.0, 20.0, 28.0, "half"),
        (20.0, 50.0, 12.0, "half"),
        (50.0, 100.0, 10.5, "half"),
    ),
    "inferno": _bands(
        (0.0, 0.1, 0.1, "open"),
        (0.1, 1.0, 6.5, "half"),
        (1.0, 2.0, 8.0, "half"),
        (2.0, 5.0, 13.0, "half"),
        (5.0, 10.0, 12.0, "half"),
        (10.0, 20.0, 24.0, "half"),
        (20.0, 50.0, 18.0, "half"),
        (50.0, 100.0, 8.0, "half"),
        (100.0, 150.0, 6.9, "half"),
    ),
    "meltdown": _bands(
        (0.0, 0.1, 0.1, "open"),
        (0.1, 1.0, 6.0, "half"),
        (1.0, 2.0, 7.0, "half"),
        (2.0, 5.0, 12.0, "half"),
        (5.0, 10.0, 11.0, "half"),
        (10.0, 20.0, 14.0, "half"),
        (20.0, 50.0, 24.0, "half"),
        (50.0, 100.0, 12.0, "half"),
        (100.0, 250.0, 10.4, "half"),
    ),
    "reactor": _bands(
        (0.0, 0.1, 0.1, "open"),
        (0.1, 1.0, 5.5, "half"),
        (1.0, 2.0, 7.0, "half"),
        (2.0, 5.0, 11.0, "half"),
        (5.0, 10.0, 12.0, "half"),
        (10.0, 20.0, 13.0, "half"),
        (20.0, 50.0, 18.0, "half"),
        (50.0, 100.0, 14.0, "half"),
        (100.0, 200.0, 9.0, "half"),
        (200.0, 500.0, 6.9, "half"),
    ),
    "plasma": _bands(
        (0.0, 0.1, 0.1, "open"),
        (0.1, 1.0, 4.9, "half"),
        (1.0, 2.0, 6.0, "half"),
        (2.0, 5.0, 10.0, "half"),
        (5.0, 10.0, 10.0, "half"),
        (10.0, 20.0, 12.0, "half"),
        (20.0, 50.0, 16.1, "half"),
        (50.0, 100.0, 13.0, "half"),
        (100.0, 200.0, 10.0, "half"),
        (200.0, 500.0, 8.0, "half"),
        (500.0, 1000.0, 3.6, "half"),
        (1000.0, 2500.0, 2.8, "half"),
    ),
}

# IDLE fallback (§6.1) — only if Base Mode STD validator fails
_IDLE_FALLBACK = _bands(
    (0.0, 0.1, 0.1, "open"),
    (0.1, 1.0, 6.1, "half"),
    (1.0, 2.0, 68.0, "half"),
    (2.0, 5.0, 14.5, "half"),
    (5.0, 10.0, 4.0, "half"),
    (10.0, 20.0, 3.8, "half"),
)

_TARGETS: dict[str, dict] = {
    "idle": dict(
        max_win=20.0,
        zero_rate=0.28,
        break_even=0.38,
        std_range=(1.10, 1.30),
        etl40_cap=0.02,
        band_share_cap=0.65,
        min_unique=80,
    ),
    "eco": dict(
        max_win=25.0,
        zero_rate=0.38,
        break_even=0.48,
        std_range=(1.45, 1.70),
        etl40_cap=0.03,
        band_share_cap=0.52,
        min_unique=85,
    ),
    "standard": dict(
        max_win=30.0,
        zero_rate=0.47,
        break_even=0.58,
        std_range=(1.80, 2.10),
        etl40_cap=0.04,
        band_share_cap=0.48,
        min_unique=90,
    ),
    "boost": dict(
        max_win=40.0,
        zero_rate=0.52,
        break_even=0.65,
        std_range=(2.20, 2.50),
        etl40_cap=0.05,
        band_share_cap=0.43,
        min_unique=95,
    ),
    "overclock": dict(
        max_win=50.0,
        zero_rate=0.61,
        break_even=0.72,
        std_range=(2.60, 3.00),
        etl40_cap=0.12,
        band_share_cap=0.36,
        min_unique=100,
    ),
    "nitro": dict(
        max_win=75.0,
        zero_rate=0.66,
        break_even=0.76,
        std_range=(3.10, 3.50),
        etl40_cap=0.16,
        band_share_cap=0.33,
        min_unique=105,
    ),
    "furnace": dict(
        max_win=100.0,
        zero_rate=0.70,
        break_even=0.80,
        std_range=(3.80, 4.30),
        etl40_cap=0.20,
        band_share_cap=0.30,
        min_unique=110,
    ),
    "inferno": dict(
        max_win=150.0,
        zero_rate=0.72,
        break_even=0.82,
        std_range=(4.60, 5.20),
        etl40_cap=0.24,
        band_share_cap=0.26,
        min_unique=115,
    ),
    "meltdown": dict(
        max_win=250.0,
        zero_rate=0.74,
        break_even=0.84,
        std_range=(5.60, 6.30),
        etl40_cap=0.30,
        band_share_cap=0.26,
        min_unique=120,
    ),
    "reactor": dict(
        max_win=500.0,
        zero_rate=0.76,
        break_even=0.86,
        std_range=(6.90, 7.80),
        etl40_cap=0.38,
        band_share_cap=0.20,
        min_unique=130,
    ),
    "plasma": dict(
        max_win=2500.0,
        zero_rate=0.78,
        break_even=0.88,
        std_range=(10.0, 12.0),
        etl40_cap=0.55,
        band_share_cap=0.18,
        min_unique=150,
    ),
}


def mode_config(name: str, *, idle_fallback: bool = False) -> ModeConfig:
    name = name.lower()
    meta = _TARGETS[name]
    bands = _IDLE_FALLBACK if (name == "idle" and idle_fallback) else _PRIMARY[name]
    return ModeConfig(
        name=name,
        band_budgets=list(bands),
        use_idle_fallback=bool(name == "idle" and idle_fallback),
        **meta,
    )


def all_mode_configs(*, idle_fallback: bool = False) -> list[ModeConfig]:
    return [mode_config(n, idle_fallback=idle_fallback and n == "idle") for n in MODE_ORDER]


def assert_budget_sums() -> None:
    for name, bands in _PRIMARY.items():
        total = sum(b.budget_pts for b in bands)
        assert abs(total - 96.5) < 1e-9, f"{name} budget sum {total} != 96.5"
    fb = sum(b.budget_pts for b in _IDLE_FALLBACK)
    assert abs(fb - 96.5) < 1e-9, f"idle fallback budget sum {fb} != 96.5"


assert_budget_sums()
