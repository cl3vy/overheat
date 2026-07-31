# OVERHEAT: Production Grade UX Brief

Implementation brief for Cursor. Target: OVERHEAT // MINING RIG THERMAL CONSOLE (Stake Engine crash game, 96.5% RTP, 11 rig tiers, crash mechanic themed as an overheating mining rig).

The game currently passes math validation but fails the only test that matters commercially: a new player cannot understand the loop fast enough to want to play. This brief takes it to production grade with comprehension as the primary objective, and folds the retention and expected value work into the same pass so it all ships together.

Change targets are named by their on screen label and copy, since exact component and file paths are not specified here. Add the file paths for the config screen, the reveal screen, the result screen, and the stats strip at the top of this doc before handing to Cursor so it does not guess.

---

## 0. The one problem

A crash game lives or dies on the player grasping the loop in about two seconds: pick a number, bet, watch it climb, win if it reaches your number before it dies. That sentence appears nowhere on either current screen. Instead the player is handed a private vocabulary (shutdown temp, checkpoints, coins lock in, a fry, DRIP, overdrive, golden, turbo) and asked to decode it before he is allowed to feel anything. The theme is an asset. The vocabulary stacked on top of it is a tax charged at the door, before the player has any reason to pay it.

Everything below serves one goal: make the loop legible instantly and in plain language, put visual weight only on what drives the next action, and let the atmosphere frame the game instead of competing with it.

---

## 1. Design laws (apply everywhere)

1. **The loop is one plain sentence, and it is on screen.** Themed words are allowed, but the plain meaning sits next to them the first time they appear.
2. **Theme is background, mechanics are foreground.** Atmosphere never wins a fight for attention with the action the player needs to take.
3. **Teach vocabulary inline, once.** The first time a themed word appears, its plain meaning appears with it. After that the word can stand alone.
4. **Progressive disclosure.** Advanced mechanics appear at the moment they first matter, not before. A first run needs almost none of them.
5. **One job per screen.** Each screen has a single primary action. Everything else recedes or hides.
6. **Show variance, hide the mean.** Sell the upside and the swing. Never render a figure that lets the player price the game or read his running net score.
7. **Expose fairness, never expected value.** Provably fair proof builds trust and retains. Aggregate loss stats do the losing math for him and send him to another tab.
8. **Every rendered number is true.** Reweighting what the eye lands on is legal and standard. Fabricating wins, streaks, or feeds is not.

---

## 2. Comprehension: the core loop, made legible

Add a persistent plain language statement of the loop, shown prominently for a new player and collapsible once he has played. Draft copy:

> Set your cash out multiplier. Boot the rig. It heats up and climbs. Cash out before it melts down, or lose the stake.

This replaces the current instruction lines, which describe the checkpoint and fry mechanics before the player has any frame to hang them on. Checkpoints are a second layer. They are taught by being watched (see 4, the reveal screen), not by a metaphor paragraph on the boot screen.

Vocabulary translation, applied inline the first time each term shows:

- **shutdown temp** to **cash out at Nx**
- **coins lock in at a checkpoint** to **partial payouts bank as it climbs** (only surfaced once the player is on a checkpoint mode, not on the base boot screen)
- **a fry** to **meltdown, run over**
- **overdrive / golden** to **bonus multiplier on the payout** (surfaced only when one hits, see 5)

---

## 3. Config screen (boot)

Primary action: place a bet. Everything on this screen either helps set the number and stake, or it hides.

**Fix**

- **Translate the target inline.** Under the large multiplier, show the plain meaning once: "cash out at 2.00x." Keep the themed label, remove the translation burden.
- **Cut the metaphor wall.** The block under the slider ("a fry keeps everything banked", "DRIP dense locks loaded to the front") is the single most confusing element on the screen and it explains a mechanic the player does not need to boot his first run. Reduce to one plain line, or reveal it only after the first run.
- **Fix or cut the tick row.** The ticks under the slider read as noise because nothing tells the eye what a tick is. If it does not communicate at a glance, it is clutter. Either make one tick clearly equal one checkpoint (and label it once), or remove it.
- **Move overdrive and golden off the boot screen.** They are upside garnish, not setup. Surface them when one actually lands.
- **Make the boot action unmistakable.** BOOT RIG is the one primary action. It should be the brightest control on the screen. When the power reserve is insufficient, the disabled state and the reason should read clearly without turning the whole screen red.

**Expected value removals on this screen**

- Delete any **profit frequency** string (for example "profit ~1 in N runs"). This is a plain language statement that the player loses most of the time. Nothing on a real floor shows net profit frequency.
- Delete the **full send odds** figure. Odds printed next to a large payout is the exact expected value term for the jackpot leg, served on a plate.
- Never render a **probability and its payout as a pair** for the same outcome. Probability times multiplier summed across the ladder is the RTP. Show one or the other, never the coordinate.
- **locks something** may remain as a standalone mode descriptor ("most runs pay something"). It must never share a line or a card with any profit frequency figure, or the two together rebuild the distribution.

**Keep (sells upside without pricing it):** the temperature dial, the safe to spicy gradient, the flavor line, the max win callout.

---

## 4. Reveal screen (the climb)

This screen is currently implied rather than designed, and it is the most important one, because it is where the player learns the game by feeling it. Spec it explicitly.

- **The climbing multiplier is the hero.** Largest, brightest element on the screen, rising in real time over the roughly five second reveal.
- **The target line is always visible.** Show where his cash out sits so the gap between current and target is legible at a glance. The tension is the distance closing.
- **Checkpoints light up as they are passed.** This is how the checkpoint mechanic is taught: not by a paragraph, but by watching a rung light and a partial payout bank as the number climbs past it. The metaphor wall on the config screen becomes unnecessary because the player now sees the mechanic happen.
- **Banked total ticks up live** as checkpoints lock, so the player sees safety accumulating even before he cash out.
- **The meltdown is the only place red belongs.** Reserve red for the crash moment itself. If red is used for ambient loss tallies elsewhere, it stops reading as danger and starts reading as "losing game."

---

## 5. Result screen (after the crash)

On a loss this screen has exactly one job: make BOOT AGAIN feel like the obvious next move. The current screen does the opposite. It clutters the result with decoration and rubs the loss in.

**Fix**

- **Hero the near miss.** "died 0.07x short of the 1.37x checkpoint" is genuinely good retention copy, because it says "so close, go again." It is currently buried under telemetry and a paytable. Make it, the multiplier it died at, and the target it aimed for, almost the only things on the screen.
- **Cut the telemetry panel.** Fan RPM, 12V rail, core clock have zero gameplay meaning. Remove them, or shrink to a thin ambient strip that never competes with the result. Atmosphere, not information.
- **Collapse the checkpoints ladder.** The full ladder on the right is the paytable printed on the wall. It clutters the result, and it is the exact multiplier ladder a sharp player uses to reconstruct the edge. Show where he landed and the one rung he missed, not all twenty.
- **Trim the sys log and drop the funeral.** Lines like "stake lost", "no checkpoints reached", "brutal" are loss salience turned up to maximum. Keep two or three lines of flavor for atmosphere. Remove the copy that dwells on the loss.
- **BOOT AGAIN is the primary control.** Brightest element after the near miss. RETURN TO RIG SELECT is secondary and quieter.

**On a win,** invert the energy: celebrate loudly, animate the payout, make the win feel bigger than any loss ever felt. The asymmetry is the point.

---

## 6. Stats strip (retention)

The strip currently tallies the player's losses three ways in one eyeline: session net P/L, a wins over attempts count, and a red sparkline that only trends down. Three exits stacked together. Rebuild it to surface peaks he has touched and a streak he is inside, and never show the running score.

**Kill outright**

- **Session net P/L and the red sparkline.** Net P/L is the one number that ends a losing session, which is why no floor machine shows it. If a graph stays in that slot, render multiplier history as upward bars so spikes grab the eye. Never a P/L line.
- **Wins over attempts (for example "2/23").** A win count over an attempt count is a loss rate wearing a costume. Drop the denominator. Never show how many times he pulled.

**Reframe (same data, pointed forward)**

- **Run counter to session progress.** Give the counter a job: a progress bar toward a goal ("4 runs to STANDARD") or session XP. A bare run count next to a loss just measures how long he has been down.
- **Streak to live streak.** Render "streak N / best M", updating as he plays. A streak in progress is sticky, because breaking it feels like a fresh loss. A past record is trivia.

**Amplify (the fuel: big and first)**

- **Personal peaks** (hottest multiplier, best bank, mode best) are the hook: "I did 17x, I can do it again." Promote them to the largest and brightest elements in the strip, ahead of everything else. Right now they are small and dim behind the loss tally.
- **Recent chips.** Stop rendering the recent results at equal weight. Render green wins large and glowing, render low reds small and dim. Same numbers, reweighted so the eye lands on wins.

**Add**

- **Live global win feed.** A ticker of real payouts across the operator ("someone just banked 340 MW on PLASMA"). Crash games retain on other people winning right now, not on the player's own record, which may be red while the feed can always surface a green win. This is the biggest unused lever. Source it from real payout events (see 8).

---

## 7. Visual hierarchy spec

Right now decoration renders at the same weight as the action. Enforce a strict scale so the eye always lands on what drives the next move.

**Type scale (largest to smallest)**

1. The live multiplier during reveal, the result multiplier, the target during config. This tier owns the screen.
2. The plain language translation of the target, the near miss line, the primary action (BOOT RIG, BOOT AGAIN), the cash out control.
3. Stake controls, mode name, banked total.
4. Ambient only, dim and small, never competing: telemetry, flavor text, collapsed checkpoint ladder, sys log.

**Color discipline**

- **Green:** primary, go, climbing, win. The default voice of the game.
- **Amber and gold:** upside garnish. Overdrive, golden, personal peaks, the caution end of the dial.
- **Red:** scarce by design. Reserve it for the meltdown moment itself. Every ambient red loss tally you remove makes the one red that remains hit harder. A screen full of equal weight red reads as a losing game before the player has even played.

**One thing per screen.** Before shipping any screen, name its single primary action. If a second element competes with it for attention, demote the second element.

---

## 8. Progressive disclosure map

| Mechanic | Introduced when | Taught how |
| --- | --- | --- |
| Core loop (bet, climb, cash out, meltdown) | First screen, always | Plain sentence on screen |
| Cash out target (shutdown temp) | First screen, always | Inline translation under the number |
| Checkpoints and banking | First run on a checkpoint mode | Watched live on the reveal screen as rungs light up |
| Overdrive and golden | The first time one lands | A celebratory reveal on the result, not boot copy |
| Turbo | After a few runs, or on hover | A tooltip, not a permanent control label to decode |
| Mode differences (DRIP, SPIKE, tiers) | Rig select, in plain terms | "dense small wins" vs "rare big wins", not jargon |

The base boot screen for a first time player should carry the loop sentence, the target with its translation, the stake control, and the boot button. Nothing else is required to place the first bet.

---

## 9. Known math constraint that is also a UX problem

Per the current model, Expected Tail Liability (ETL 40x) fails on the two top modes (REACTOR, PLASMA) because the distribution is loaded toward the top with almost no wins in the 1x to 40x range. This is a compliance blocker, and it is also a comprehension and retention problem: on those modes the player almost never sees a win in the range he can feel, so the mode reads as dead or broken. Rebalancing to seed more frequent small and mid wins in the 1x to 40x band fixes the compliance failure and makes the top modes feel alive at the same time. Treat this as one fix, not two.

---

## 10. Hard constraints (compliance and integrity)

Everything above is framing, hierarchy, and disclosure discipline, all legal and standard. The following turn it into a real problem, the kind that gets a Stake Engine submission rejected or a licence questioned. Do not cross them.

- **Keep every rendered number true.** Reweight what the eye lands on. Never change a displayed value to something false.
- **No fabricated win feed.** The global feed is sourced from real payout events, not invented players or invented wins.
- **No lying counters.** A live streak or stat counter reflects the actual state.
- **Do not suppress a mandated disclosure.** Where the target jurisdiction requires RTP or other figures on screen, they stay. Removing the aggregate convenience stats is allowed. Hiding a required figure is not.
- **Keep the provably fair verification reachable.** The seed or fairness check stays available. It is a trust asset, not clutter.

---

## 11. Acceptance checklist

Comprehension

- [ ] Plain language loop sentence present on the entry screen
- [ ] Target multiplier carries an inline plain translation on first appearance
- [ ] Config screen reduced to loop sentence, target, stake, boot; advanced copy removed or deferred
- [ ] Metaphor wall under the slider cut or reduced to one plain line
- [ ] Tick row either clearly labelled as checkpoints or removed
- [ ] Reveal screen shows climbing multiplier, target line, live checkpoint lighting, live banked total
- [ ] Checkpoints taught by the reveal, not by boot copy

Result screen

- [ ] Near miss, death multiplier, and target are the hero elements
- [ ] Telemetry panel removed or reduced to ambient strip
- [ ] Checkpoint ladder collapsed to landed rung plus missed rung
- [ ] Sys log trimmed, loss dwelling copy removed
- [ ] BOOT AGAIN is the primary control; win state celebrates loudly

Retention strip

- [ ] Session net P/L removed; any graph is upward multiplier bars
- [ ] Attempt denominator removed from win count
- [ ] Run counter reframed as session progress
- [ ] Streak rendered live
- [ ] Personal peaks promoted to largest and first
- [ ] Recent chips reweighted, wins bright, low reds dim
- [ ] Live global win feed added from real events

Expected value discipline

- [ ] Profit frequency string removed from all modes
- [ ] Full send odds figure removed
- [ ] No probability rendered adjacent to its payout for any outcome
- [ ] locks something never shares a line with a profit frequency figure

Hierarchy and integrity

- [ ] Type scale enforced; each screen has one named primary action
- [ ] Red reserved for the meltdown moment only
- [ ] All rendered numbers verified true; no fabricated feed or counters
- [ ] Provably fair verification reachable; any mandated disclosure retained
- [ ] Top mode distribution rebalanced so ETL passes and 1x to 40x wins appear
