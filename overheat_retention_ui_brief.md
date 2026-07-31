# OVERHEAT Console: EV Disclosure and Retention UI Brief

Implementation brief for Cursor. Target: the OVERHEAT // MINING RIG THERMAL CONSOLE crash game (Stake Engine, 96.5% RTP, 11 rig tiers, crash style mechanic themed as an overheating mining rig).

This document covers two coordinated changes:

1. Stop the console from computing the player's expected loss for him (EV leakage).
2. Rebuild the top stats strip so it drives retention instead of advertising exits.

Codebase note: change targets below are named by their on screen label and copy, since exact component and file names are not specified here. Map each item to the component that renders that region.

---

## Core principle

Show the variance, hide the mean. Expose fairness, never expose expected value.

A player is retained by the feeling of a swingy game with reachable peaks. He is deterred by any figure that lets him price the game or read his own running score. Every element on screen should sell upside or invite verification of fairness. Nothing should pre compute his losses or pin his net position where he cannot miss it.

This is framing, and framing is legal and standard. It is not fabrication. See Hard Constraints at the bottom. Every number that renders must stay true.

---

## Part 1: EV leakage in the main console

The console currently prints enough to let a player reconstruct the house edge by hand. Fixes ranked by damage.

### 1.1 Remove the profit frequency string (highest priority)

**Current:** `profit ~1 in 12.3 runs`

**Action:** Delete this string entirely. Do not render it in any tier.

**Why:** This is a plain language statement that the player loses money on roughly 92 percent of runs. No slot and no crash game on a real floor shows net profit frequency. A recreational player reads "1 in 12" and feels the floor drop out with no calculator needed. This single line deters harder than every red number on screen combined.

### 1.2 Never render hit probability and payout for the same outcome together

**Current:** `full send odds: 0.35%` shown alongside the 100.00x target, plus the checkpoint anchors `first lock 0.47x @ 1.84x`, `last 54.46x @ 75.16x`, plus `14 checkpoints` and `locks something 19.1%`.

**Action:** Never display a probability and its payout as a pair. Show one or the other for any given outcome, never the coordinate.

**Why:** Probability times multiplier, summed across the ladder, is the RTP. With two anchor points and the checkpoint count a sharp player interpolates the curve and lands within a few points of 96.5%. The paired figures hand him every term he needs.

### 1.3 Kill the jackpot odds figure specifically

**Current:** `full send odds: 0.35%` next to the 100x fantasy.

**Action:** Remove the odds figure. Keep the 100x target and the payout callout loud.

**Why:** Odds printed next to a 100x payout is the exact EV term for the jackpot leg served on a plate. The fantasy sells. The probability next to it prices the fantasy.

### 1.4 Do not show hit frequency next to profit frequency

**Current:** `locks something: 19.1%` sitting beside the profit frequency string.

**Action:** Once 1.1 is removed, `locks something` can stay as a standalone mode descriptor. It must never share a line or a card with any profit frequency figure.

**Why:** Hit frequency alone is survivable copy. Combined with profit frequency it describes the full payout curve: how often he gets anything, and how often that anything is a profit. The two together rebuild the distribution.

### 1.5 Keep (these sell upside without pricing it)

Retain: the temperature dial, the `safe / spicy` gradient, the flavor line (`this is not mining. this is a star.` / `undervolted. boring. pays the rent.`), the OVERDRIVE and 10x GOLDEN callouts, `max win`, and the recent multiplier chips (see Part 2 for how those render).

### 1.6 Trust hook to add

Crash games on Stake style platforms retain on provably fair, and 96.5% is a good RTP worth surfacing rather than burying. Add a verify affordance that exposes the seed or the provably fair check. "Here is the seed, verify us" builds trust and keeps the player in the tab. This is the opposite of hiding math: remove the aggregate stats that do the losing arithmetic for him, and add the fairness proof that invites him to trust the game.

---

## Part 2: Top stats strip redesign

The strip currently tallies the player's losses three ways in one eyeline: `session -11.0x`, `wins 2/23`, and a red sparkline that only trends down. Three exits stacked on top of each other. The strip should instead surface peaks he has already touched and a streak he is inside, and it should never show the running score.

### 2.1 Kill outright

**Session net P/L and the red sparkline**

- **Current:** `session -11.0x` plus a red sparkline.
- **Action:** Remove the net P/L figure. If a graph stays in that slot, render multiplier history as vertical bars so spikes like 17.49x and 10.04x point upward and grab the eye. Never render a P/L line.
- **Why:** Net P/L is the one number that ends a losing session, which is why no floor machine shows it. A P/L line only ever drifts down for a losing player, so it is pure exit pressure. Vertical multiplier bars point up and read as opportunity.

**Win count over attempt count**

- **Current:** `wins 2/23`.
- **Action:** Drop the denominator. Do not display attempt count anywhere.
- **Why:** A win count over an attempt count is a loss rate wearing a costume. The player divides it in his head. Never show him how many times he pulled.

### 2.2 Reframe (same data, pointed forward)

**Run counter**

- **Current:** `23 runs` (bare tally next to a loss).
- **Action:** Give the counter a job. Render a session progress bar toward a goal, for example "4 runs to STANDARD" or a session XP track.
- **Why:** A bare run count next to a loss just measures how long he has been down. A progress bar turns the same integer into forward motion.

**Streak**

- **Current:** `longest streak 3` (a past record).
- **Action:** Make it live. Render `streak N / best 3`, updating in real time as he plays.
- **Why:** A streak in progress is sticky, because breaking it feels like a fresh loss stacked on the existing one. A streak in the past is trivia.

**Locks something**

- **Current:** `locks something: 62.6%`.
- **Action:** Keep it as a standalone mode descriptor. Enforce the Part 1.4 rule: never on the same line as any profit frequency figure.
- **Why:** On its own it reads as "most runs pay" and points at the current mode. Paired with profit frequency it leaks the edge.

### 2.3 Amplify (this is the fuel: big and first)

**Personal peaks**

- **Current:** `hottest 17.49x`, `best bank 112.50 MW`, `ECO best 4.50x` rendered as small dim text behind the loss tally.
- **Action:** Promote these to the brightest and largest elements in the strip, positioned ahead of everything else.
- **Why:** These are peaks the player personally hit, which makes them the hook: "I did 17x, I can do it again." They are currently buried behind the exit signals. Lead with them.

**Recent chips**

- **Current:** the RECENT strip renders every result at equal visual weight, so fourteen reds read as "losing game."
- **Action:** Stop rendering it as an even ledger. Render green wins large and glowing (10.04x, 17.49x, 3.91x). Render 1.00x and low reds small and dim.
- **Why:** Same numbers, reweighted so the eye lands on wins. Three glowing greens read as "wins happen here." Equal weight reads as a loss log.

### 2.4 New component: live global win feed

Add a ticker of real payouts across the operator, for example "someone just banked 340 MW on PLASMA."

**Why:** Crash games retain on other people winning right now, not on the player's own record. A global feed pulls harder than any personal stat, because the player's own history may be red while the feed can always surface a green win somewhere on the platform. This is the biggest unused lever.

Feed must be sourced from real payout events. See Hard Constraints.

---

## Hard Constraints (compliance and integrity)

Everything above is reweighting and framing, which is legal and standard. The following turn it into a real problem, the kind that gets a Stake Engine submission rejected or a licence questioned. Do not cross these.

- **Keep every rendered number true.** Reweighting what the eye lands on is fair. Changing a displayed value to something false is not.
- **No fabricated win feed.** The global feed must be seeded from real payout events, not invented players or invented wins.
- **No lying streak or stat counters.** A live streak counter must reflect the actual streak.
- **Do not hide a figure a regulator requires on screen.** Where the target jurisdiction mandates RTP or other disclosure, that disclosure stays. Removing the aggregate convenience stats is allowed. Suppressing a mandated figure is not.

Summary: stop stacking the true figures that point at the door. Do not invent figures that point away from it.

---

## Acceptance checklist

- [ ] `profit ~1 in N runs` removed from all tiers
- [ ] No probability rendered adjacent to its payout for any outcome
- [ ] `full send odds` figure removed
- [ ] `locks something` never shares a line with a profit frequency figure
- [ ] Session net P/L removed; any strip graph is upward multiplier bars, not a P/L line
- [ ] Attempt denominator removed from win count
- [ ] Run counter reframed as session progress
- [ ] Streak rendered live as `streak N / best M`
- [ ] Personal peaks promoted to largest and first in the strip
- [ ] Recent chips reweighted: wins large and glowing, low reds small and dim
- [ ] Live global win feed added, sourced from real events
- [ ] Provably fair verify affordance present
- [ ] All rendered numbers verified true; no fabricated feed or counters
- [ ] Any jurisdiction mandated disclosure retained
