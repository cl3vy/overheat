# OVERHEAT: Final Declutter Pass

Change order for Cursor. The honest loop copy, the peaks line, the streak simplification, the CASH OUT TARGET relabel, and the telemetry removal all landed. This pass is only about what is still on screen that the player does not need. Each item says exactly what to remove or fix.

Add the component file paths for CONFIG, the REVEAL/result screen, and the win variant before running.

---

## PRIORITY 0: CONFIG no longer fits on screen (fix first)

In the BOOST config screenshot there is a scrollbar on the right and the BOOT RIG button is cut off at the bottom fold. The single most important control in the game is below the fold. Nothing else on this list matters if the player cannot see the boot button.

- **Make the CONFIG screen fit in the viewport with BOOT RIG fully visible, no scroll.** The removals in Priority 1 below claw back the vertical space to do this. If it still overflows after those, tighten vertical spacing between the number, the slider, and the stake row rather than shrinking BOOT RIG.

---

## PRIORITY 1: Remove dead weight on CONFIG

### 1.1 Remove the vestigial `shutdown temp` subtitle
`CASH OUT TARGET` is now the primary label, which is correct. The small dim `shutdown temp` line under it is now pure vestige and just adds a line.
**Remove** the `shutdown temp` subtitle entirely. The theme survives in RIG names and flavor lines; it does not need to sit under the primary label too.

### 1.2 Remove the dashed rectangle around the slider
There is a dashed box drawn around the slider track. It communicates nothing and reads as a selection artifact.
**Remove** the dashed border. The handle already shows the position.

### 1.3 Remove the ASCII decoration around the TURBO button
When TURBO is on, stray sparkle glyphs render around the button. It is noise next to the primary action.
**Remove** the decorative glyphs. A simple `TURBO [ON]` state, styled distinctly, is enough.

### 1.4 Collapse the two payout lines into one (optional, saves a line)
`full send pays: 3.00 MW` and `max win 30.00 MW` are two lines saying related things. On modes where they differ only by the overdrive multiplier, one line carries it:
**Replace** the two lines with a single line: `full send pays 3.00 MW, up to 30.00 MW on overdrive`.
Skip this if the layout already fits after 1.1 to 1.3.

---

## PRIORITY 2: The CHECKPOINTS ladder is still on the result screens

Round 2 called for removing this and it is still there on both the meltdown and the clean win result screens (the `// CHECKPOINTS` column listing `3.00x FULL 3.00x` down to `1.19x 0.47x`).

- **Remove the entire `// CHECKPOINTS` ladder panel from both result screens.**
- Two reasons, both still true: it is the full paytable printed on the wall, which a sharp player sums to reconstruct the edge, and it is redundant with the summary already shown in the center (`CHECKPOINTS HELD +0.99 MW secured` on a loss, `CLEAN BANK +3.00 MW` on a win). The center summary is the only place this belongs.
- Removing it also frees the right third of the result screen, which currently competes with the outcome.

---

## PRIORITY 3: Clean up the win screen

The clean win screen is the emotional peak of the whole game and it is currently the messiest. Scattered glyphs (`0`, `1`, `Ð`, `Ξ`, `¤`, and similar) float at random positions across the screen, overlapping the result.

- **Remove the scattered floating glyphs from the result screen.** If you want ambient digital rain for atmosphere, confine it to a low opacity background layer that sits behind a solid panel and never overlaps the `CLEAN BANK` box or the text.
- The win moment should be the cleanest screen in the game, not the busiest. After the glyphs and the ladder (Priority 2) are gone, what remains is the multiplier, `CLEAN BANK +3.00 MW`, the one line tease, `NEW PERSONAL BEST`, and BOOT AGAIN. That is the whole screen.

### 3.1 Deduplicate the win labels (optional)
`SHUTDOWN CLEAN` and `CLEAN BANK` both say clean. Keep `CLEAN BANK +3.00 MW` as the headline and cut `SHUTDOWN CLEAN`, or vice versa. One clean is enough.

### 3.2 Keep the crash point tease
`silicon had 3.38x in it` is worth keeping. Telling the winner how far it would have gone creates a small go again pull. Leave it.

---

## PRIORITY 4: Trim result screen stats to the essentials

On the meltdown screen there are several stat fragments competing: `aimed for 3.00x`, `your BOOST best: 0.99x`, `CHECKPOINTS HELD: +0.99 MW secured (0.99x stake, 7 locks)`, and `NEW PERSONAL BEST RUN`.

- **Cut `your BOOST best: 0.99x`.** The `NEW PERSONAL BEST RUN` banner already tells him this run was his best. The inline per mode best is a second copy of the same idea.
- **Trim the parenthetical.** Change `CHECKPOINTS HELD: +0.99 MW secured (0.99x stake, 7 locks)` to `CHECKPOINTS HELD: +0.99 MW secured`. The `7 locks` and `0.99x stake` detail is math the player does not need at the moment of a result.
- **Keep** `aimed for 3.00x`, the meltdown line, and the secured total. Those three are the result.

---

## One thing to sanity check, not a fix

On the meltdown screen the run banked 0.99 MW on a 1.00 MW stake and is labeled `NEW PERSONAL BEST RUN`. That is a net losing run wearing a best run badge. It is true (best banked on BOOST so far) and it is good retention framing, so keep it, but make sure the badge triggers on genuine banked improvement and not on every near miss, or it stops meaning anything and the player learns to ignore it.

---

## Acceptance checklist

- [ ] CONFIG fits the viewport; BOOT RIG fully visible with no scroll
- [ ] `shutdown temp` subtitle removed from CONFIG
- [ ] Dashed rectangle around the slider removed
- [ ] TURBO decorative glyphs removed
- [ ] Payout lines collapsed to one (if needed for fit)
- [ ] `// CHECKPOINTS` ladder removed from both result screens
- [ ] Floating glyphs removed from the win screen; any rain confined to a background layer
- [ ] Win screen deduped to one clean headline
- [ ] `silicon had ...x in it` tease kept
- [ ] `your BOOST best` inline stat removed from the meltdown screen
- [ ] Checkpoints held parenthetical trimmed to the secured total
- [ ] Personal best badge gated on real banked improvement, not every run
