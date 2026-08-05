# Overheat Math v4 — Fix Instructions for Remaining 21 Validator Failures

**Context:** `validate_books.py` reports FAILED (21). Books generate, RTP / hit rate / zero rate / break-even / max win / unique counts are green. The failures are all in distribution *shape*: band budgets, std ranges, ETL40, and ladder invariants.

**Do not change any target in §4.2 or the budget matrix in §4.3 of the redesign spec. These are method fixes, not target fixes.**

---

## Root cause (read this first)

All 21 failures trace to **one** cause: too much RTP is stuck near 1×, and the high bands are starved.

The previous fix spread the near-unity mass off the single 1.00x point to kill the 8% concentration rule. But that mass spread *sideways* into the near-unity cluster (0.90–1.25), not upward. So the low region stayed heavy and every band above it stayed underweight. That single defect shows up four ways:

- **Band budgets (§4.3):** high bands underweight, near-unity bands overweight → out of ±0.4 tolerance.
- **Std ranges (§4.2):** volatility comes from the tails; underweight tails → std under the floor.
- **Ladder invariants (I4 std, I7 ETL40):** INFERNO's tops are the emptiest of all, so it ends up flatter and lighter-tailed than FURNACE below it → monotonic ordering breaks.
- **ETL40 (BOOST):** weight piled on the exact 40× endpoint instead of spread through 20–39.

Fix the band fill and the other three largely fix themselves.

---

## Fix 1 — Invert the generation fill order (fixes most reds)

The generator currently fills low-to-high, so the residual RTP lands in the low bands and the tops get whatever is left over (too little). Reverse it.

- Place each **high band's** budgeted RTP **first**, from the mode max downward, and **lock** each band's contribution to its §4.3 target before touching `[1, 2)` and the recovery band `[0.1, 1)`.
- Let `[1, 2)` and `[0.1, 1)` absorb **only the remainder** needed to hit hit-rate and break-even.
- The top bands are hard constraints; the near-unity bands are the flex. This is currently backwards.

Result: high bands stop being empty, band RTP comes into tolerance, and std rises into range because the tail weight is finally present.

## Fix 2 — Hard-fail any empty budgeted band (fixes INFERNO)

INFERNO `[100, 150]` shows 0.00 vs a 6.9 budget — that top band is effectively empty, which is what breaks the ladder.

- The teaser point (0.85 × 150 = 128) and the max (150) must carry real weight after Fix 1.
- Add a per-mode assertion: **every band with a non-zero §4.3 budget must have non-zero achieved RTP.** An empty budgeted band is a hard failure, not a silent pass.

## Fix 3 — Half-open ETL bands + rounding margin (fixes BOOST ETL40)

BOOST ETL40 = 0.0500 fails cap 0.05 on a strict `>`. Weight is piling on the exact 40× endpoint.

- Make the `[20, 40]` band **half-open `[20, 40)`** so 40 belongs to the next band up, and spread its weight across 20–39 per the geometric grid.
- Give the ETL40 cap a **2% safety margin**: target **≤ 0.049**, not ≤ 0.05, so integer rounding can't push it back over.
- Apply the same half-open-at-upper-edge rule to every ETL-relevant band so no cap sits on an endpoint pile.

## Fix 4 — Target centers, not edges (fixes the near-miss std floors)

BOOST 2.197 vs floor 2.2, OVERCLOCK 2.592 vs 2.6, NITRO 3.031 vs 3.1 — all failing by landing just under the floor.

- Target the **center** of each std range in §4.2, not the floor.
- Target the **center** of each band budget in §4.3, not anywhere inside ±0.4.
- Landing on a floor by luck is not acceptable; aim for the midpoint so rounding has room on both sides.

---

## Regression guard (do not skip)

These fixes push mass *away* from near-unity. The previous fix pushed it *toward* near-unity to kill the 8% concentration rule. Do not overshoot and reintroduce that failure.

- After rebalancing, re-verify **no non-zero outcome exceeds 6% of non-zero probability.**
- If any mode cannot satisfy both the 6% cap and its top-band budgets simultaneously, **stop and surface it** — do not silently break one. That is a genuine tension for human review, per §11 of the spec.

---

## Definition of done

Re-run the full harness. All must hold:

- RTP stays **96.5000** exact on every mode.
- Break-even, hit-rate, zero-rate stay green (already passing — must not regress).
- Band budgets within ±0.4 on every band; no empty budgeted band.
- Std inside range on every mode, targeting center.
- ETL40 ≤ 0.049 on every mode; exposure and tail ≥5000× = 0 unchanged.
- Ladder invariants I1–I7 all hold (watch I4 std and I7 ETL40 across FURNACE → INFERNO).
- No non-zero outcome above 6% of non-zero probability.
