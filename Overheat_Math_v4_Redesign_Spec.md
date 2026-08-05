# Overheat Math v4 Redesign Specification

**Game:** Overheat (crash style, overheating mining rig theme)
**Team:** Over Limit | **Current math version:** 3 | **Target version:** 4
**Platform:** Stake Engine | **Bet template:** 2kmax_1cent (min bet 0.01, max bet 2,000)
**Audience for this document:** an implementation agent (Cursor). Every rule is explicit. Do not improvise beyond what is written. Where a value is given as a target with a tolerance, hitting the tolerance is mandatory. Where something is marked VERIFY, it must be checked with the Stake Engine validator before the work is considered done.

---

## 1. Purpose

Version 3 of the math is fully compliant (all validator checks green) but has three structural defects that hurt player experience and long term retention:

1. **Coarse outcome tables.** Each mode has only 17 to 23 unique payout values. In a crash game the rig will visibly die at the same handful of temperatures again and again. Players detect this within roughly 50 rounds and the game starts to feel scripted.
2. **Single band domination.** In 9 of 11 modes one payout band carries 41% to 75% of total RTP. Each mode has one signature outcome and everything else is noise. Reward magnitude becomes predictable, which kills the variable reward effect the genre depends on.
3. **Broken risk ladder at the top.** MELTDOWN (250x max) has higher standard deviation (5.07 vs 4.49) and a higher break even probability (87.8% vs 82.4%) than REACTOR (500x max). PLASMA ties INFERNO on break even. The tier ladder does not mean what it claims to mean.

Version 4 fixes all three while keeping RTP at exactly 96.50% in every mode and staying inside every Stake Engine constraint with wide safety margins.

---

## 2. Hard platform constraints (do not violate any of these)

These are copied from the live Stake Engine validation page for this game (Math Distribution and Summary, Version 3). Every generated book must satisfy all of them. Column two is the 2 Star limit, column three is the 3 Star limit. **Design to the 2 Star limit** (the stricter one) so the game qualifies for both templates.

### 2.1 Global constraints

| Constraint | 2 Star limit | 3 Star limit | v3 value | v4 design rule |
|---|---|---|---|---|
| Max Exposure (max bet x max multiplier) | 15,000,000 | 50,000,000 | 2,000,000 | Max multiplier across all modes times 2,000 must stay at or under 15,000,000. Hence absolute multiplier ceiling is 7,500x. v4 uses 2,500x, exposure 5,000,000. |
| Max Payout Multiplier (template) | 50,000 | 100,000 | 1,000 | v4 max is 2,500. |
| Max Bet Cost | 100,000 | 500,000 | 2,000 | Unchanged. Bet template stays 2kmax_1cent. |
| Cost Multiplier | 1,000 | 2,000 | 1 | Unchanged. All modes remain cost 1.00x. No bonus buy in this version. |
| Base Volatility (Std Dev), reported as max across modes | 50.0 | 60.0 | 5.46 | v4 max mode std target is about 11 (PLASMA). Assert max mode std <= 15. |
| Tail Probability (5,000x) | 0.0100 | 0.0500 | 0 | Keep at exactly 0. No payout in any mode may be at or above 5,000x. v4 ceiling 2,500x guarantees this. |
| Tail Probability (10,000x) | 0.0050 | 0.0100 | 0 | Keep at exactly 0. Guaranteed by the 2,500x ceiling. |
| Risk Limit (CVaR, per stake) | 700.0 | 700.0 | 73.4 | Estimated v4 worst mode value is under 80 (see 8.4). Assert validator value <= 350 (50% of limit). VERIFY with validator since the exact CVaR percentile Stake uses is not published. |
| Risk Limit (CVaR, absolute) | 20,000 | 50,000 | 73.4 | Same as above. VERIFY. |
| Expected Tail Liability (40x) | 0.800 | 0.900 | 0.126 | Per mode sum of probability times payout over all payouts >= 40x. v4 worst mode (PLASMA) is budgeted at about 0.41. Assert <= 0.55 per mode. |
| Expected Tail Liability (10,000x) | 0.600 | 0.800 | 0.000 | Stays 0.000 (no payouts near 10,000x). |
| Expected Tail Liability (Sum) | 1.300 | 1.500 | 0.126 | Assert <= 0.60. VERIFY how the validator aggregates this. |

### 2.2 Per mode compliance checks

| Check | Rule | v4 handling |
|---|---|---|
| Cross Mode RTP Consistency | Spread of RTP across modes <= 0.50% | All modes are built to exactly 96.5000%. Spread is 0.00%. |
| Base Mode Cost | Smallest cost mode must be the 1.00x base game | IDLE stays cost 1.00x. |
| Base Mode STD | Validator shows expected 0.60x and passed v3 at 1.10x, so the exact rule (floor, band, or ceiling) is ambiguous | Keep IDLE std between 1.10 and 1.25. If the validator fails this check at any value above 1.10, regenerate IDLE with the fallback budget in section 6.1 which lands at about 1.12. VERIFY. |
| Bet Level Validator | A valid three star bet level template must exist | Keep 2kmax_1cent. Do not touch bet levels. |
| RTP Range | 90.0% to 96.70% | Exactly 96.50% everywhere. |
| Non Zero Win Hit Rate | At least 1 win in every 50 spins | Worst v4 mode is PLASMA at 22% hit rate, which is 1 in 4.5. Huge margin. |
| Cost Multiplier | <= 2,000x | All modes 1x. |
| Max Payout Multiplier | <= 500,000x per mode | Highest v4 mode max is 2,500x. |

### 2.3 Engine and book format constraints

- Books are weighted outcome tables (payout multiplier, integer weight). RTP is the weight weighted mean of multipliers.
- v3 books used a total of 100,000 simulation entries per mode. v4 must use a total integer weight of exactly **W = 100,000,000 per mode** for precision. If the Stake math SDK requires simulation counts rather than direct weight tables, generate the book as a weight table first and then emit it in whatever format the SDK ingests, preserving weights exactly.
- All payout multipliers must be non negative. Exactly one outcome per mode equals the mode maximum.
- Settlement is payout = bet x multiplier. Multiplier precision rules are in section 7.2 to reduce sub cent rounding artifacts that were flagged in QA.

---

## 3. Current state (v3) reference numbers

These are the numbers the redesign is measured against. Full detail lives in `Overheat_Math_Distribution_Report.md`. Summary:

| Mode | Max | RTP | Hit rate | Zero rate | Std | Break even | Unique payouts | Largest band share of RTP |
|---|---|---|---|---|---|---|---|---|
| IDLE | 12x | 96.50 | 71.98% | 28.02% | 1.1047 | 36.5% | 17 | 75.4% in [1,2) |
| ECO | 15x | 96.50 | 62.60% | 37.40% | 1.2631 | 47.8% | 17 | 69.1% in [1,2) |
| STANDARD | 20x | 96.50 | 52.62% | 47.38% | 1.4838 | 57.8% | 17 | 61.5% in [2,5) |
| BOOST | 30x | 96.50 | 47.57% | 52.43% | 1.8356 | 70.0% | 19 | 61.8% in [2,5) |
| OVERCLOCK | 50x | 96.50 | 38.60% | 61.40% | 2.3485 | 76.3% | 19 | 49.3% in [5,10) |
| NITRO | 70x | 96.50 | 33.79% | 66.21% | 2.7467 | 78.8% | 19 | 45.8% in [5,10) |
| FURNACE | 100x | 96.50 | 29.72% | 70.28% | 3.2303 | 80.3% | 19 | 42.7% in [10,20) |
| INFERNO | 150x | 96.50 | 29.17% | 70.83% | 4.0545 | 84.7% | 19 | 41.0% in [10,20) |
| MELTDOWN | 250x | 96.50 | 27.20% | 72.80% | 5.0707 | 87.8% | 19 | 41.2% in [20,50) |
| REACTOR | 500x | 96.50 | 26.22% | 73.78% | 4.4908 | 23 | 82.4% | best spread, max 17.4% |
| PLASMA | 1,000x | 96.50 | 24.54% | 75.46% | 5.4573 | 84.7% | 23 | 26.8% in [20,50) |

REACTOR is the shape model. Its RTP mass flows smoothly across seven bands with no band above 17.4%. v4 generalizes that shape across the ladder, scaled per tier.

---

## 4. v4 design targets

### 4.1 Ladder invariants (must all hold across modes, in tier order IDLE to PLASMA)

- I1. RTP identical: 96.5000% every mode, tolerance 1e-6 absolute after integer weight rounding.
- I2. Hit rate strictly decreasing.
- I3. Zero rate strictly increasing.
- I4. Standard deviation strictly increasing.
- I5. Break even probability (P(payout < 1.00x bet), includes zeros) strictly increasing.
- I6. Max win strictly increasing.
- I7. Expected tail liability at 40x non decreasing.

v3 violates I4 and I5 at the top (MELTDOWN vs REACTOR vs PLASMA). v4 fixes this by giving REACTOR and PLASMA genuinely heavier tails and by pulling MELTDOWN's mid band mass slightly down.

### 4.2 Per mode target table

Tolerances: hit rate, zero rate, break even within plus or minus 1.5 percentage points of target. Std within the stated range. Max win exact. ETL(40x) at or under the stated cap.

| Mode | Max win | Zero rate | Hit rate | Break even | Std range | ETL(40x) cap | Max band share cap | Min unique payouts |
|---|---|---|---|---|---|---|---|---|
| IDLE | 20x | 28% | 72% | 38% | 1.10 to 1.30 | 0.02 | 65% | 80 |
| ECO | 25x | 38% | 62% | 48% | 1.45 to 1.70 | 0.03 | 52% | 85 |
| STANDARD | 30x | 47% | 53% | 58% | 1.80 to 2.10 | 0.04 | 48% | 90 |
| BOOST | 40x | 52% | 48% | 65% | 2.20 to 2.50 | 0.05 | 43% | 95 |
| OVERCLOCK | 50x | 61% | 39% | 72% | 2.60 to 3.00 | 0.12 | 36% | 100 |
| NITRO | 75x | 66% | 34% | 76% | 3.10 to 3.50 | 0.16 | 33% | 105 |
| FURNACE | 100x | 70% | 30% | 80% | 3.80 to 4.30 | 0.20 | 30% | 110 |
| INFERNO | 150x | 72% | 28% | 82% | 4.60 to 5.20 | 0.24 | 26% | 115 |
| MELTDOWN | 250x | 74% | 26% | 84% | 5.60 to 6.30 | 0.30 | 26% | 120 |
| REACTOR | 500x | 76% | 24% | 86% | 6.90 to 7.80 | 0.38 | 20% | 130 |
| PLASMA | 2,500x | 78% | 22% | 88% | 10.0 to 12.0 | 0.55 | 18% | 150 |

Notes:

- Max win changes: IDLE 12 to 20, ECO 15 to 25, STANDARD 20 to 30, BOOST 30 to 40, NITRO 70 to 75, PLASMA 1,000 to 2,500. FURNACE, INFERNO, MELTDOWN, REACTOR unchanged. Rationale: round number ceilings, a coherent doubling rhythm, and a marketable 2,500x top prize while exposure stays at one third of the 2 Star limit.
- Every max win stays far below the per mode 500,000x check and the 50,000x template cap.
- The 2,500x ceiling keeps both tail probability constraints at exactly zero by construction.

### 4.3 RTP contribution budget matrix (the core spec)

This matrix is the heart of the redesign. Each cell is the number of RTP percentage points that band must contribute in that mode. Columns sum to 96.5 exactly. Bands are half open intervals [a, b) on the payout multiplier, except the last listed band of each mode which is closed at the mode max.

The generator (section 7) must reproduce these budgets with a per band tolerance of plus or minus 0.4 percentage points, while total RTP stays exact.

| Band | IDLE | ECO | STANDARD | BOOST | OVERCLOCK | NITRO | FURNACE | INFERNO | MELTDOWN | REACTOR | PLASMA |
|---|---|---|---|---|---|---|---|---|---|---|---|
| (0, 0.1) | 0.1 | 0.1 | 0.1 | 0.1 | 0.1 | 0.1 | 0.1 | 0.1 | 0.1 | 0.1 | 0.1 |
| [0.1, 1) | 6.1 | 7.1 | 7.9 | 8.5 | 7.9 | 7.5 | 6.9 | 6.5 | 6.0 | 5.5 | 4.9 |
| [1, 2) | 62.0 | 48.0 | 22.0 | 14.0 | 11.0 | 10.0 | 9.0 | 8.0 | 7.0 | 7.0 | 6.0 |
| [2, 5) | 18.0 | 26.0 | 45.0 | 40.0 | 20.0 | 18.0 | 16.0 | 13.0 | 12.0 | 11.0 | 10.0 |
| [5, 10) | 5.5 | 8.0 | 12.0 | 18.0 | 33.0 | 30.0 | 14.0 | 12.0 | 11.0 | 12.0 | 10.0 |
| [10, 20) | 4.8 | n/a | n/a | 9.0 | 13.0 | 15.0 | 28.0 | 24.0 | 14.0 | 13.0 | 12.0 |
| [10, 25] | n/a | 7.3 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| [10, 30] | n/a | n/a | 9.5 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| [20, 40] | n/a | n/a | n/a | 6.9 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| [20, 50) | n/a | n/a | n/a | n/a | 11.5 | 10.0 | 12.0 | 18.0 | 24.0 | 18.0 | 16.1 |
| [50, 75] | n/a | n/a | n/a | n/a | n/a | 5.9 | n/a | n/a | n/a | n/a | n/a |
| [50, 100) | n/a | n/a | n/a | n/a | n/a | n/a | 10.5 | 8.0 | 12.0 | 14.0 | 13.0 |
| [100, 150] | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 6.9 | n/a | n/a | n/a |
| [100, 250] | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 10.4 | n/a | n/a |
| [100, 200) | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 9.0 | 10.0 |
| [200, 500] | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 6.9 | 8.0 |
| [500, 1000) | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 3.6 |
| [1000, 2500] | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 2.8 |

For IDLE the top band [10, 20) is interpreted as [10, 20], closed at the 20x max. For OVERCLOCK the [20, 50) band is closed at the 50x max.

Verification of column sums (must be asserted in code):
IDLE 96.5, ECO 96.5, STANDARD 96.5, BOOST 96.5, OVERCLOCK 96.5, NITRO 96.5, FURNACE 96.5, INFERNO 96.5, MELTDOWN 96.5, REACTOR 96.5, PLASMA 96.5.

### 4.4 Why these shapes work (design rationale, for the human reviewer)

- The dominant band problem is capped: the worst concentration falls from 75.4% (v3 IDLE) to 62/96.5 = 64% on IDLE by design (the entry tier is intentionally tame) and every mode from OVERCLOCK up sits at or below 36%, with the top three at or below 26/20/18. Reward magnitude stops being predictable exactly where players are betting for the thrill.
- Each tier still has a personality: the largest band walks upward with tier (IDLE lives in [1,2), BOOST in [2,5), OVERCLOCK and NITRO in [5,10), FURNACE and INFERNO in [10,20), MELTDOWN in [20,50)), but the mass around it is thick enough that adjacent outcomes happen constantly.
- REACTOR and PLASMA get true tail weight. PLASMA carries 24.4 RTP points above 100x versus 9.3 in v3, which is what makes it feel like the top tier, and its std roughly doubles. The ladder invariants I4 and I5 now hold.
- The recovery band [0.1, 1) is deliberately shrunk as tiers rise (6.1 down to 4.9 points). High tiers should feel binary: you either escape with real money or the rig burns. Partial refunds at high tiers read as insults, at low tiers they read as consolation.

---

## 5. Player experience and revenue logic (context, not code)

RTP is pinned at 96.50%, so operator margin is a fixed 3.5% of turnover in every mode. Revenue therefore scales only with total wagered volume, which scales with session length and return frequency. The math levers for that are:

1. **Perceived continuity.** 80 to 150 unique crash points per mode makes the temperature curve feel continuous and fair. This is the single biggest fix for the scripted feeling.
2. **Variable reward magnitude.** Flattening band concentration means the same mode can pay 2.1x, 4.7x, or 13x on consecutive wins. Unpredictable magnitude at a stable frequency is the strongest known driver of continued play in this genre.
3. **Near max teasers.** Each mode includes an outcome at roughly 0.85 times the mode max with at least twice the weight of the max outcome (section 7.3). Players see almost jackpot events often enough to believe in the jackpot.
4. **Anchor wins.** Round numbers (10x, 25x, 50x, 100x, 250x) are forced grid points so screenshots and chat brags read cleanly.
5. **Coherent ladder.** When each tier is strictly riskier than the one below, tier progression itself becomes the meta game. v3 broke this at the top; v4 restores it.
6. **Session pacing stays humane at entry tiers.** IDLE keeps a win every ~1.4 spins and profit every ~2.6 spins so new players calibrate before climbing. Worst case loss streaks at the top (about 55 spins at 1 in 1000 for PLASMA at 88% break even) are intrinsic to the tier and disclosed by the on screen stats.

The displayed crash temperature must remain a deterministic function of the drawn multiplier. Never decouple display from settlement.

---

## 6. Outcome grid specification

### 6.1 Grid construction (identical algorithm per mode)

1. Build a geometric grid from m_min = 0.10 to the mode max with ratio r = 1.06: m_k = 0.10 x 1.06^k, stopping at the largest value below max, then append max itself.
2. Round every grid value: below 10 round to 2 decimals, from 10 to below 100 round to 1 decimal, at 100 and above round to the nearest integer. Deduplicate after rounding.
3. Force include the anchor set intersected with values at or below the mode max: {0.20, 0.50, 1.00, 1.20, 1.50, 2.00, 2.50, 3.00, 5.00, 7.50, 10, 15, 20, 25, 30, 40, 50, 75, 100, 150, 250, 500, 1000, 2500}.
4. Force include the teaser point: round(0.85 x max) using the rounding rule above (IDLE 17, ECO 21.3 rounds to 21.3 (1 decimal), STANDARD 25.5, BOOST 34, OVERCLOCK 42.5, NITRO 63.8, FURNACE 85, INFERNO 128, MELTDOWN 213, REACTOR 425, PLASMA 2125).
5. Add exactly one zero outcome (multiplier 0.00) which absorbs the zero rate.
6. Expected grid sizes: IDLE about 90, PLASMA about 175. Assert against the minimum unique payout column in 4.2. Unique payout count is counted after weight assignment, excluding any grid point that ends with weight 0 (allowed, but the count after exclusion must still meet the minimum).

**IDLE fallback budget** (use only if the Base Mode STD validator check fails with the primary budget): (0,0.1) 0.1, [0.1,1) 6.1, [1,2) 68.0, [2,5) 14.5, [5,10) 4.0, [10,20] 3.8. This lands std near 1.12 while keeping about 85 unique outcomes.

### 6.2 Multiplier precision and sub cent handling

QA previously flagged sub cent payouts rounding away at 0.01 bets. Rules:

- No multiplier may have more than 2 decimal places. From 10x up, at most 1 decimal. From 100x up, integers only.
- Do not place any non zero multiplier below 0.02.
- Document in the game rules that payouts are rounded down to the currency's smallest unit. The math book itself needs no other change; RTP impact of floor rounding at 0.01 stake is below 0.5% of RTP and only at the minimum bet. VERIFY that the validator computes RTP from the book, not from rounded settlements (it did in v3).

---

## 7. Weight generation algorithm

Implement exactly this. Language: Python, inside the existing math generation module.

### 7.1 Inputs per mode

- Grid G = {0} plus the sorted non zero grid from 6.1.
- Band budget vector B from the matrix in 4.3, in RTP points (divide by 100 to get expected value units).
- Zero rate target z from 4.2.
- Break even target from 4.2.
- Total weight W = 100,000,000.

### 7.2 Within band weight profile

For each band [a, b) with budget c (in expected value units, e.g. 0.062 for 6.2 points):

1. Let x_1 < x_2 < ... < x_n be the grid points inside the band.
2. Assign unnormalized weights u_i = x_i^(-beta) with beta = 1.5 as the default decay.
3. The band's contribution shares are s_i = (u_i x_i) / (sum_j u_j x_j) x c.
4. Point probabilities are p_i = s_i / x_i.
5. The band's total probability is P_band = sum_i p_i and its mean multiplier is x_bar = c / P_band.

beta is the tuning knob:

- Raising beta shifts mass toward the low edge of the band, raising P_band and lowering x_bar.
- The generator must tune beta per band by bisection in the range [0.3, 3.0] to satisfy the break even and std targets, as follows.

### 7.3 Special weight rules

- **Teaser rule:** after profile assignment, set the weight of the teaser point (0.85 x max) to exactly 2.5 times the weight of the max outcome, then renormalize the top band so its budget is unchanged.
- **Max outcome floor and ceiling:** the max outcome probability must land between 1 in 3,000,000 and 1 in 100,000 for modes up to MELTDOWN, and between 1 in 3,000,000 and 1 in 300,000 for REACTOR and PLASMA. With W = 100,000,000 that means an integer weight between 34 and 1,000 (top two modes: 34 to 334). If the profile produces a value outside this window, clamp it and rebalance the band.
- **Smoothness rule:** within a band, weights must be non increasing as the multiplier rises, except the teaser point. No single non zero outcome may hold more than 8% of total non zero probability. If the profile violates this (possible in the dominant band of IDLE and ECO), split that grid point's weight across itself and its two neighbors 50/25/25.
- **Dust rule:** after integer rounding, delete any outcome with weight 0 and any outcome with weight below 3; add the removed weight to the nearest lower neighbor in the same band.

### 7.4 Break even calibration

Break even = z + P(0 < payout < 1). The sub unit probability comes from the (0, 0.1) and [0.1, 1) bands: P_sub = 0.001/x_bar_tiny + b_recovery/x_bar_recovery, where b_recovery is the recovery band budget in EV units. Solve for the recovery band's x_bar (via beta bisection) so that z + P_sub hits the break even target within 1.5 points. The implied x_bar values are all inside (0.55, 0.95) for the budgets given, so a solution exists in every mode. The (0, 0.1) band uses a fixed representative point at 0.05 (plus 0.02 and 0.08 as minor neighbors) and contributes about 2 points of probability in every mode.

### 7.5 Zero weight, normalization, and exact RTP

1. Compute all non zero integer weights w_i = round(p_i x W).
2. Set the zero outcome weight w_0 = W minus the sum of non zero weights. Assert w_0 / W is within 1.5 points of the zero rate target.
3. Compute the achieved RTP = (sum_i w_i x_i) / W. Let delta = 0.9650 minus achieved RTP (signed).
4. Correct exactly by moving weight between the zero outcome and the 1.00x anchor: dw = round(delta x W / 1.00). Add dw to the 1.00x weight and subtract dw from w_0. This changes RTP by exactly dw/W and leaves total weight at W.
5. Re assert |RTP - 0.9650| <= 1e-6. If the residual after integer rounding exceeds 1e-6, distribute a final correction of at most 5 weight units between the 1.00x and 2.00x anchors (moving one unit between them changes RTP by 1e-8 per unit).
6. Assert every ladder invariant and every target in 4.2 on the finished book.

### 7.6 Determinism

Seed nothing. The algorithm above is fully deterministic given the config, so regenerating the books always yields identical files. Version the config (v4.0.0) and write it into the book file header or an adjacent manifest.

---

## 8. Validation harness

Build `validate_books.py` that loads all 11 v4 books and produces a markdown report. It must compute and assert, per mode:

### 8.1 Core metrics

- RTP (exact), hit rate, zero rate, break even probability, standard deviation, min and max multiplier, unique payout count.
- Band RTP contribution table matched against the budget matrix (tolerance 0.4 points per band).
- Largest band share against the cap column in 4.2.
- Largest single outcome share of non zero probability (<= 8%).

### 8.2 Stake constraint replicas

- Exposure: 2,000 x global max multiplier <= 15,000,000.
- Tail probabilities: P(payout >= 5,000) = 0 and P(payout >= 10,000) = 0.
- ETL(40x) per mode: sum over payouts >= 40 of p x payout, against the per mode caps in 4.2 and the platform limit 0.800.
- ETL(10,000x) = 0.
- Max mode std <= 15 (platform limit 50).
- Hit rate <= 1 in 50 (i.e., win probability >= 2%).
- RTP within [90.0%, 96.70%] and cross mode spread <= 0.50%.
- Per mode max <= 500,000x.

### 8.3 Ladder invariants

Assert I1 through I7 from 4.1 across the ordered mode list.

### 8.4 CVaR estimate

The exact percentile Stake uses is unpublished, so compute expected shortfall at the 99.0%, 99.5%, and 99.9% levels per mode and report all three. Rough expectation from the budgets: PLASMA ES(99%) is near 47 (total RTP mass above roughly 25x divided by 0.01), well under the 700 limit. If any computed value exceeds 350, stop and flag for human review before uploading. Final authority is the Stake validator. VERIFY.

### 8.5 Regression table

Emit a v3 versus v4 comparison table (all columns of section 3) so the diff is reviewable at a glance.

### 8.6 Definition of done

1. `validate_books.py` passes every assertion locally.
2. Books uploaded as math version 4 to Stake Engine.
3. The live validator page shows Valid overall, 8/8 per mode compliance on all 11 modes, and every global constraint at or below 60% of its 2 Star limit (except RTP, which sits by design at 96.50 inside its band).
4. The Base Mode STD check passes; if not, IDLE is regenerated with the 6.1 fallback budget and steps 2 and 3 repeat.
5. Frontend smoke test: each mode boots, the temperature curve renders distinct crash points across 100 manual rounds with no visibly repeating crash temperature more than a few times, and settlement matches book payouts exactly.

---

## 9. Repository deliverables

```
math/
  config_v4.py        # dataclasses: ModeConfig(name, max_win, zero_rate, band_budgets,
                      #   std_range, break_even, etl40_cap, band_share_cap, min_unique)
                      # plus the full 11 mode config exactly as specified in sections 4 and 6
  grid.py             # section 6 grid builder (pure function, unit tested)
  generate_books.py   # section 7 generator, writes books/<mode>_v4.csv with columns
                      #   multiplier, weight and a manifest.json with config hash
  validate_books.py   # section 8 harness, writes reports/v4_validation.md
  tests/
    test_grid.py          # grid sizes, anchors present, rounding rules, dedup
    test_generator.py     # per mode: RTP exactness, budget tolerance, weight rules 7.3
    test_invariants.py    # ladder invariants I1..I7, constraint replicas 8.2
    test_regression.py    # v3 book metrics recomputed from the existing books to
                          #   guarantee the harness reproduces the report numbers
```

test_regression.py matters: before trusting the harness on v4, run it against the v3 books and confirm it reproduces the values in section 3 (RTP 96.5000, IDLE std 1.1047, PLASMA max win hit rate about 1 in 127,302, and so on). If the harness cannot reproduce v3, fix the harness first.

---

## 10. Explicitly out of scope for v4

- No bonus buy or cost multiplier modes (allowed up to 2,000x by the platform; candidate for v5 once v4 is approved).
- No RTP changes and no per mode RTP differentiation (the 0.50% cross mode rule makes it pointless).
- No new modes and no renames. The known UI naming mismatch (math book tier "meltdown" versus UI "SUPERNOVA", with MELTDOWN reused as the bust label) is a frontend ticket, not a math ticket, but do not rename anything in the books.
- No changes to the bet template, bet levels, or currency handling.
- No changes to the frontend temperature mapping beyond consuming the denser book (the mapping function must simply pass the new multipliers through; verify it has no hardcoded lookup of the 17 to 23 old values, and if it does, replace it with a pure function of the multiplier).

---

## 11. Known ambiguities the implementer must not resolve alone

1. Base Mode STD expected value semantics (section 2.2). Resolution path: generate with the primary IDLE budget, run the validator, fall back if needed.
2. CVaR percentile definition (section 8.4). Resolution path: report three percentiles locally, trust the validator, escalate if the validator value exceeds half the limit.
3. ETL(Sum) aggregation rule (section 2.1). Resolution path: keep every component small enough that any plausible aggregation passes with margin.
4. Whether the SDK ingests weight tables directly or requires simulation output (section 2.3). Resolution path: inspect the existing v3 build pipeline in the repo and mirror its output format with the new weights.

If anything in the validator output contradicts this spec, stop and surface it rather than adjusting targets silently.
