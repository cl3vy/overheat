# OVERHEAT: QA Remediation Plan (submission readiness)

Implementation plan for Cursor, built from the full QA audit and cross-checked against the official Stake Engine RGS documentation (stakeengine.github.io/math-sdk/rgs_docs/RGS/) and web-sdk (github.com/StakeEngine/web-sdk). Work the phases in order. Phase 1 and 2 account for most of the failed checklist items.

Verified against docs before planning:
- Bets must fall between minBet and maxBet from /wallet/authenticate and be divisible by stepBet. The current stake field (free text, clamps only to balance) can therefore produce RGS-rejectable bets. This is a hard fix, not polish.
- Currency is display-layer only and comes from the authenticate response (balance.currency). The web-sdk exposes numberToCurrencyString for formatting. MW-always rendering is non-compliant.
- The authenticate round object may be an active round, and the frontend is required to continue it. Mid-round refresh restoration is a documented requirement.
- The authenticate config carries jurisdiction flags (socialCasino, disabledFullscreen, disabledTurbo). The game currently reads none of them.

What the audit confirmed is healthy and must not be regressed: settlement math correct in every audited round, 96.50% RTP flat across all 11 modes, insufficient-balance path, invalid-language fallback, load time, turbo timing.

---

## PHASE 1: Rules screen (largest cluster of checklist failures)

One missing screen currently fails five or more checklist items: RTP in rules, max win stated, payout information, mode descriptions with cost info, general disclaimer, interaction guide.

Build a RULES overlay, opened from a persistent `[RULES]` control next to `[FAIRNESS]`, containing these sections:

1. **How to play.** The honest loop copy already written: set an auto cash out target, the rig climbs on its own and stops there automatically; on checkpoint modes a meltdown keeps what the checkpoints banked, otherwise the stake is lost. Include the keyboard and touch interaction guide (set target, set stake, boot; SPACE to boot on desktop).
2. **Modes table.** All eleven rigs: name, target multiplier, hit rate ("pays something" %), checkpoint pattern (frequent-small vs rare-big), and cost basis. This is also where OVERDRIVE gets documented (see Phase 6.3).
3. **Payouts.** How checkpoint banking works, what a full send pays, OVERDRIVE multipliers (1.5x / 3x / 10x golden), and max win 1000x stated explicitly.
4. **RTP.** 96.50%, all modes.
5. **Disclaimer.** Standard general disclaimer text (malfunction voids plays and pays, etc.).

Constraints: the overlay must be scrollable internally while the game frame itself stays fixed (see Phase 2), readable at every supported viewport, and reachable from config, result, and replay states.

---

## PHASE 2: Frame overflow, spacebar, and responsive

These are one cluster. The scrollable frame is an explicit checklist failure and it is also the direct cause of the spacebar bug.

### 2.1 Kill frame scroll at the root
- Set the game root to exactly the viewport (100dvh/100dvw, overflow hidden). No native scrollbars in any state, on any screen size, including after the HOTTEST / RECENT stats row populates post-round-one. That row appearing must not change the layout height: reserve its space at load (render it empty or dim) so round one does not reflow the page.
- With frame scroll gone, retest SPACE: the current failure (focus on slider or stake field makes SPACE scroll instead of boot) should disappear. Additionally, add an explicit keydown handler at the document level that intercepts Space when the game is in a bootable state, calls preventDefault, and triggers BOOT, regardless of which control holds focus. Enter in the stake field should blur and commit.

### 2.2 Responsive layouts (mobile is most of Stake traffic)
Define three explicit layout tiers instead of letting the desktop layout squeeze:
- **Desktop / tablet:** current layout.
- **Mobile (<= 480px wide):** single column. Order: multiplier target (large), slider full width with labels ABOVE the track at reduced size ("1.20x" left, "100x" right, drop "safe"/"spicy" at this width), stake row as one line (minus, input, plus, never wrapping; fix with flex-nowrap and a min-width on the input), BOOT RIG full width and always above the fold, TURBO as a small toggle beside or below it. Stats strip collapses to one line: peaks only, RECENT chips horizontally scrollable within their own row (inner scroll on a row is fine; frame scroll is not).
- **Popout / mini (<= ~450x260):** a dedicated compact state: multiplier, stake, BOOT. Nothing else. If a surface cannot fit those three, it is not a supported surface, but the checklist requires the frame not to scroll, so the compact state must fit.
- Specific bugs to verify fixed at 375x667 and 320x568: stake "+" wrapping to its own line, slider labels colliding into "1.20xsafespicy100.00x", BOOT RIG text wrapping to three lines, intro paragraph clipping mid-word, slider "+" pushed off the right edge.
- Hide "[SPACE] to boot" when the device has no keyboard (pointer: coarse / device=mobile param).
- Disable double-tap-to-zoom (touch-action: manipulation on interactive elements) — flagged as unverified in the audit; make it verifiable.

---

## PHASE 3: Replay mode compliance

The replay requirements are a named section of the official approval guidelines. Fix all of these:
- **BOOT AGAIN in replay replays the same event.** It is currently disabled, which is a named checklist failure. In replay context, relabel it `REPLAY AGAIN` and have it re-run the same round playback.
- **Hide the balance line in replay.** "PWR RESERVE: 0.00 MW" plus "insufficient power reserve" inside a read-only replay is nonsense output. Replay renders the round's stake and result only; no wallet UI, no insufficient-balance messaging.
- **Remove RETURN TO RIG SELECT in replay** (or make it inert). It currently drops the viewer into a live betting UI with a zero balance inside a read-only window.
- Replay must work in the compact layout (Phase 2.2), since replay at Popout S is currently unusable.

---

## PHASE 4: Currency, amounts, and bet levels

### 4.1 Currency from authenticate
- Read balance.currency from the authenticate response. Format all money (balance, stake, wins, banked) with locale-aware currency formatting (the web-sdk's numberToCurrencyString pattern), including zero-decimal currencies like JPY. Test with currency=JPY: no ".00" anywhere.
- Keep MW as flavor, not as the money unit. Recommended rendering: real currency is primary ("STAKE: ¥100"), MW as themed garnish where wanted ("100 MW" as a subtitle), never the other way around. The real currency must be unambiguous on config, run, result, and rules screens.

### 4.2 Integer math for display
- The RGS deals in integer micro-units (1.00 = 1000000). Keep all amounts as integers end to end and format only at render. This kills both observed rounding bugs: the sub-cent boundary case (0.75x and 1.20x on a 0.01 stake both showing +0.01) and the header mismatch (859.79 credited vs BEST BANK 859.78). One shared formatting function everywhere; no parallel floor-in-one-place round-in-another paths.

### 4.3 Stake input snaps to bet levels
- Replace free-text clamping with the bet template from authenticate: minBet, maxBet, stepBet, betLevels, defaultBetLevel. The minus/plus buttons step through betLevels; typed input snaps to the nearest valid level on blur; anything outside min/max clamps to the boundary level. Never send an amount the RGS could reject as not divisible by stepBet.

### 4.4 Jurisdiction flags
- Respect the jurisdiction object from authenticate: hide TURBO when disabledTurbo, honor disabledFullscreen, and check whether socialCasino requires any copy changes for that market.

---

## PHASE 5: Functional bugs

- **5.1 Stale first frame on boot.** Repro: run INFERNO 1.00/15x, return to rig select, switch to PLASMA 5.00/100x, BOOT. The run screen shows the previous rig, stake, target, and full checkpoint ladder for ~0.5-1s before snapping. Fix: clear/reset the run-screen state atomically when a new round starts, and do not render the run screen until the new round's play response has populated it. Render a boot spinner or a one-beat "POWER ON" frame instead of stale state. A reviewer will screenshot this as "game displays wrong bet amount"; treat it as a blocker.
- **5.2 Fairness LAST ROUND ID never populates.** Wire it to round.roundID from the play/end-round response. Every settled round must display its ID, and the ID must persist until the next round settles. The panel copy tells players to quote this ID; an em-dash there is worse than no field.
- **5.3 Slider thumb overlaps the "+" button at the 100x end.** Constrain the track so the thumb at max stops short of the button, or move the +/- outside the track's bounding box.
- **5.4 First-run state hygiene.** On a fresh player the stats strip must be a clean slate (no leftover "STANDARD BEST 3.00x", "STREAK 0 (BEST 7)"). Namespace persisted display stats per player session and per currency. Keep all of it display-only: no persisted state may alter gameplay, cost, or outcomes (statelessness is a platform rule; cosmetic stats are fine, progression that changes the game is not).
- **5.5 Mid-round refresh restore.** On authenticate, if the returned round is active, resume it: restore stake, target, rig, and continue or settle the round. Documented requirement, currently unverified.
- **5.6 Ship a real loader.** The harness's "Add Your Loader" placeholder appeared on replay launch. The checklist explicitly forbids shipping the Stake Engine loader. Build a branded loading screen (the CRT boot aesthetic is a gift here: BIOS-style boot lines over the logo).
- **5.7 Thumbnail.** Produce and upload the required thumbnail asset. Pre-submission checklist is red on it.

---

## PHASE 6: Design and math items from the audit

- **6.1 Rename the MELTDOWN collision.** MELTDOWN is both a rig tier (250x) and the bust announcement on every losing round. Keep "** MELTDOWN @ x.xx **" as the bust word (it is the theme's best word) and rename the rig tier. Suggested: CRITICAL or SUPERNOVA. Update the modes table in the rules screen (Phase 1) to match.
- **6.2 Fix risk monotonicity or the UI claim of it.** The slider is a continuous safe-to-spicy gradient, but hit rates are not monotonic: INFERNO (150x) pays something 31.33% vs FURNACE (100x) 29.72%; REACTOR (500x) 27.77% vs MELTDOWN (250x) 27.20%. Preferred fix: retune those four modes in the math so hit rate strictly decreases as target rises, then re-run the validator. Alternative if retuning is off the table: replace the continuous gradient with an explicit eleven-stop ladder showing each stop's own stats, so the UI stops implying a monotonic curve the math does not have. Do one or the other; shipping the contradiction invites both player confusion and reviewer notes.
- **6.3 Document OVERDRIVE.** It is advertised on every rig-select screen and explained nowhere, and it never fired in ~20 audited rounds. Add it to the rules screen (what it is, the 1.5x/3x/10x golden multipliers, that it applies on shutdown), and give it a distinct win presentation when it does hit so the payout is legible as an overdrive.
- **6.4 Soften the on-win regret line only.** Keep the crash-point reveal (it is honest and distinctive), but change the winner's framing. Current: "silicon had 8.16x in it" immediately after banking 1.20x reads as "you left 7x on the table." Replace on wins with neutral phrasing: "ran clean — peaked at 8.16x". Keep the loss-side near miss ("died 0.16x short") as is; that framing is standard. Leave HOTTEST tracking as is.
- **6.5 Flicker off by default.** Make the CRT flicker an opt-in toggle in settings for photosensitivity. Scanlines can stay; flicker defaults off.
- **6.6 Tick strip contrast.** Raise the checkpoint tick strip contrast so it is clearly visible, and align its scale with the slider track above it so tick positions map to multiplier positions.

---

## PHASE 7: Optional, after everything above is green

- **Autoplay.** Not required, but with 1-3s rounds it is the most obvious retention gap. If added: a confirmation step before autoplay starts, and a second confirmation when activating it on high-cost modes; a visible stop control; respects turbo and jurisdiction flags. Do not start this phase until Phases 1-5 pass.

---

## Regression guard (retest after every phase)

- Settlement reconciliation on 10 rounds across 3 modes (stake debit, checkpoint value, balance to the cent)
- Insufficient-balance path still blocks BOOT with the message, still never fires a doomed request
- Invalid language falls back to English
- Turbo still ~1s vs ~3-4s
- No console errors introduced

## Submission checklist mapping

- [ ] Rules screen: RTP, max win, payouts, mode descriptions and costs, disclaimer, interaction guide
- [ ] Game frame does not scroll on any surface or state
- [ ] SPACE boots from any focus state; hint hidden on touch
- [ ] Mobile M, Mobile S, Popout S all usable per Phase 2.2
- [ ] Replay: replayable again, no wallet UI, no live betting entry, works in compact layout
- [ ] Currency from authenticate, zero-decimal correct, integer-math display, one formatter
- [ ] Stake snaps to betLevels/stepBet; never RGS-rejectable
- [ ] Jurisdiction flags respected (turbo, fullscreen, social)
- [ ] Stale boot frame eliminated
- [ ] LAST ROUND ID populates every settled round
- [ ] BEST BANK matches credited amount exactly
- [ ] Fresh player gets a clean slate; stats namespaced, display-only
- [ ] Active round resumes on refresh
- [ ] Custom loader shipped; no Stake Engine loader
- [ ] Thumbnail uploaded
- [ ] MELTDOWN naming collision resolved
- [ ] Hit rates monotonic across the ladder, or UI switched to explicit stops
- [ ] OVERDRIVE documented and given a win presentation
- [ ] On-win crash reveal reworded neutrally
- [ ] Flicker defaults off
- [ ] Double-tap zoom disabled; old-device performance spot-checked
