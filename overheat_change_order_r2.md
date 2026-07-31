# OVERHEAT: Change Order Round 2 (surgical)

Implementation change order for Cursor. This is not a philosophy doc. Each item is a specific element to remove, move, resize, or a literal string to find and replace. Do the listed changes exactly. Do not redesign beyond what is listed.

Screens referenced:
- CONFIG = the boot screen (the PLASMA and IDLE screenshots)
- REVEAL = the in round screen (the MELTDOWN 6.06x screenshot)

Add the component file paths for CONFIG, REVEAL, and the top stats strip here before running, so the find targets resolve to real files.

---

## PRIORITY 0: Fix the deceptive loop line (integrity, do this first)

The game has no manual cash out. The player sets a target before boot, the rig climbs on its own, and it auto cashes out at that target or melts down first. There is no mid round action and no CASH OUT button on the REVEAL screen. The current copy implies the player acts during the round, which is false.

**Find (top of CONFIG, both screens):**
`> set your cash out multiplier -- cash out before the rig melts down, or lose the stake`

**Replace with:**
`> set your auto cash out target -- the rig climbs on its own and stops there automatically. if it melts down first, you keep only what the checkpoints banked.`

Notes:
- The phrase "auto cash out" is the honest, standard crash game term for a preset target. Use it consistently everywhere the word "cash out" appears as if it were a live action.
- The "cash out at 100.00x" line under the big number is fine as is, because it describes the target, not an action. Leave it.
- On any non checkpoint mode, the second clause changes to `if it melts down first, you lose the stake.` Gate the clause on whether the active mode has checkpoints.

---

## PRIORITY 1: REVEAL screen declutter (this screen is the worst offender)

The same secured checkpoint information is currently printed in three places at once (the SYS LOG confirmations, the right CHECKPOINTS panel, and the center SECURED YIELD box), plus two panels of pure decoration, plus a raw hash dump. Collapse to one source.

### 1.1 Remove the TELEMETRY panel entirely
**Remove** the whole top right block:
`// TELEMETRY`, `FAN 5,065 RPM`, `12V RAIL 12.13 V`, `CORE CLK 2401 MHz`.
Reason: zero gameplay meaning. It renders at the same weight as the actual result.

### 1.2 Remove the CHECKPOINTS ladder panel entirely
**Remove** the whole right column starting at `// CHECKPOINTS` through the full list (`GOLD 250.00x` ... `1.53x 0.39x`).
Reason two ways: it is the full paytable printed on the wall (a sharp player sums probability times multiplier off it to reconstruct the edge), and every reached rung on it is already shown in the center SECURED YIELD box. It is redundant and it leaks expected value.

### 1.3 Strip the SYS LOG down to boot flavor only
**Keep** these lines only:
`> POWER ON -- RIG: MELTDOWN`, `> BIOS OK .. volt rails nominal`, `> hashrate online: 565 MH/s`, `> shutdown temp locked: 25.00x`, `> mining...`
**Remove** every `>> CHECKPOINT x.xx -- y.yy SECURED` confirmation line (all 8).
**Remove** every `sha256: ...` line (all 7).
Reason: the checkpoint confirmations duplicate the SECURED YIELD box; the raw hashes are provably fair data dumped as clutter and belong behind the [FAIRNESS] link, not on the play screen.

### 1.4 Make the SYS LOG ambient
Set the remaining SYS LOG to a dim, small, fixed size block that never competes with the center column. It is atmosphere, not information.

### 1.5 Result: what the REVEAL screen should contain after 1.1 to 1.4
Header, the `RIG: ... | STAKE: ...` line, a dim SYS LOG on the left, and the center column: `CORE TEMP`, the large live multiplier (6.06x), `cash out @ 25.00x`, the progress bar with the target label, and the `SECURED YIELD` box with `next lock @ ...`. Nothing else. The `SECURED YIELD` box is the single source of truth for banked progress.

### 1.6 Trim the RIG line
**Find:** `RIG: MELTDOWN | HASHRATE: 565 MH/s | STAKE: 1.00 MW`
**Replace with:** `RIG: MELTDOWN | STAKE: 1.00 MW`
Reason: hashrate is decoration and has no gameplay meaning. If you want to keep it for flavor, move it into the dim ambient region, not the top line.

---

## PRIORITY 2: Simplify the rank system

Current strip:
`RANK: OVERCLOCKER [progress] 11 runs to HASH BARON | STREAK 1 / BEST 5`

Three specific problems:
1. `OVERCLOCKER` (rank) collides directly with `OVERCLOCK` (a rig tier). Two different ladders using the same words. This is a guaranteed comprehension failure.
2. It introduces a second named progression vocabulary (`HASH BARON`, etc.) on top of the 11 rig tier names the player already has to learn.
3. It adds a full width line of noise above the game.

**Primary fix: remove the rank ladder, keep only the streak.**
**Remove:** `RANK: OVERCLOCKER`, the progress bar, and `11 runs to HASH BARON`.
**Keep and relabel the streak.**
**Find:** `STREAK 1 / BEST 5`
**Replace with:** `STREAK 1 (BEST 5)`
Reason: the live streak is the sticky retention element. The named rank grind is not pulling its weight and it costs the most comprehension. Cut the ladder, keep the streak.

**Fallback if you insist on keeping progression:** drop the named tiers entirely and render a single unlabeled thin progress bar with a plain caption such as `session`. Never name a rank with a word that also names a rig tier.

---

## PRIORITY 3: CONFIG screen remaining clutter

### 3.1 Promote the plain label over the themed one
The `SHUTDOWN TEMP` header now sits above `cash out at Nx`, so the player reads a themed term first and its translation second. Flip the emphasis.
**Change:** render `CASH OUT TARGET` as the primary panel label at full brightness, and demote `SHUTDOWN TEMP` to a small dim subtitle (or remove it). The big number and `cash out at Nx` stay.
Reason: lead with the meaning, keep the theme as a whisper.

### 3.2 Tighten the tick row caption
**Find (PLASMA):** `each tick is a checkpoint -- partial payouts bank as it climbs | rare big locks, big jumps`
**Replace with:** `each tick banks a partial payout as the rig climbs | this mode: rare, big`
**Find (IDLE):** `each tick is a checkpoint -- partial payouts bank as it climbs | many small locks, early`
**Replace with:** `each tick banks a partial payout as the rig climbs | this mode: frequent, small`
Reason: same meaning, fewer words, and it drops the second use of the word "checkpoint" now that the ticks are visually self evident.

### 3.3 Remove the RECENT mini bar sparkline
**Remove** the small green and amber bar chart rendered directly under the RECENT chip row.
Reason: it re encodes the exact data the RECENT chips already show. The chips are the better version. Two encodings of the same series is clutter.

### 3.4 Keep, do not touch
Leave these as they are, they are working: the `HOTTEST / BEST BANK / MODE BEST` peaks line, the reweighted RECENT chips (green wins bright, low reds dim), `pays something: N% of runs`, `stake`, `full send pays`, `max win`, the slider and its safe to spicy gradient, the amber styling on the PLASMA tier number, `[FAIRNESS]`.

---

## PRIORITY 4: Consistency pass on the word "cash out"

After Priority 0, audit every screen for the verb "cash out" used as if it were a live action. It is always a preset target. Acceptable usages describe the target (`cash out at 100.00x`, `auto cash out target`, `cash out @ 25.00x`). Unacceptable usages imply timing or agency during the run (`cash out before ...`, `cash out now`, `hit cash out`). Replace any unacceptable usage with target based phrasing.

---

## Do not cross (unchanged from prior brief)

- Keep every rendered number true. Reweighting attention is fine. Changing a value to something false is not.
- Move the sha256 hashes behind [FAIRNESS]; do not delete provably fair verification, just get it off the play screen.
- Keep any jurisdiction mandated disclosure on screen.

---

## Acceptance checklist

- [ ] Loop line replaced with the auto cash out honest version; checkpoint vs non checkpoint clause gated correctly
- [ ] No copy anywhere implies a mid round cash out action
- [ ] REVEAL: TELEMETRY panel removed
- [ ] REVEAL: CHECKPOINTS ladder panel removed
- [ ] REVEAL: SYS LOG reduced to 5 boot lines, dim and ambient
- [ ] REVEAL: all `>> CHECKPOINT ... SECURED` lines removed
- [ ] REVEAL: all `sha256:` lines removed from the play screen
- [ ] REVEAL: SECURED YIELD box is the only place banked progress is shown
- [ ] REVEAL: RIG line trimmed to `RIG: ... | STAKE: ...`
- [ ] RANK ladder removed; only `STREAK N (BEST M)` remains
- [ ] No rank label reuses a rig tier name
- [ ] CONFIG: `CASH OUT TARGET` is the primary label; `SHUTDOWN TEMP` demoted or removed
- [ ] CONFIG: tick row captions shortened per 3.2
- [ ] CONFIG: RECENT mini bar sparkline removed
- [ ] "cash out" audited everywhere; no live action phrasing remains
