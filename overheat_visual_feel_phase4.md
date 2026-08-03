# OVERHEAT: Visual and Feel Polish (Phase 4)

Purely visual and motion direction for Cursor. No compliance, no copy, no structure. The goal is to make the game feel like a physical machine that has been obsessively worked on, and to fix the "dark and uninviting" read without abandoning the CRT aesthetic.

The core diagnosis: the darkness is not the problem, a terminal should be dark. The problem is the black is dead flat and every element sits on the same plane. The fix is depth, light, and reactive motion, not raw brightness.

Add file paths for CONFIG, REVEAL, and RESULT before running.

---

## 1. Give the black life (fixes "uninviting")

The background is currently uniform near-black, which reads as empty rather than atmospheric. Add depth to the void itself:

- **Vignette and center glow.** Darken the corners slightly and lift the center with a very subtle radial glow behind the panel, so the panel feels lit from within rather than pasted onto flat black. This alone kills most of the "dead" feeling.
- **Ambient CRT texture.** A faint scanline overlay and a slow, low-amplitude flicker on the whole frame (respecting the existing photosensitivity toggle, keep it subtle and off if flicker is disabled). Barely perceptible is the goal; it should read as "this is a screen" subliminally.
- **Drifting particle haze.** Very sparse, very slow embers or dust motes drifting upward in the background, tinted to the current tier color (green when safe, amber/red when spicy). Low count, low opacity. This adds life and reinforces the heat theme without competing with the UI.
- **Background reacts to tier.** The ambient glow and particle tint should shift with the selected risk, cool green haze on safe tiers, warm red haze on SUPERNOVA. The whole environment runs hotter as the player dials up, not just the slider.

## 2. The 2.5D panel

Make the CASH OUT TARGET panel feel like a physical screen recessed into a housing, not a flat outlined rectangle.

- **Recessed screen treatment.** Give the panel an inner bevel: a subtle darker inset shadow on the top and left inner edges, a faint lit edge on the bottom and right, so it reads as a screen sitting inside a machined bezel. This is the 2.5D effect, and it is mostly one inset box-shadow plus a highlight edge.
- **Screen curvature.** A very slight barrel distortion or a soft highlight gradient across the panel glass (brighter toward the top center, falling off at the edges) sells the CRT curve. Keep it subtle, a hint of a curved glass surface catching light.
- **Parallax on pointer.** On desktop, a small parallax: the panel contents shift a few pixels against the bezel as the pointer moves across the screen, so the "screen inside a housing" reads as having actual depth. Two or three layers (bezel, glass, content) moving at slightly different rates is enough. Disable on touch.
- **Corner hardware.** Replace the plain rounded rectangle border with HUD corner brackets or small machined corner details (screws, ticks, or `[ ]` brackets at the corners), so the frame reads as built hardware rather than a CSS border.
- **Header strip.** Give "CASH OUT TARGET" a filled or underlined header bar treatment instead of plain text on the border line, like a labeled panel on a real device.

## 3. The multiplier as the centerpiece

The number is the whole game. It should feel like a live seven-segment or CRT readout, not static text.

- **2.5D readout.** Give the big multiplier depth: a subtle extrusion or layered shadow so it sits proud of the screen, plus a soft bloom/glow in the tier color (green safe, amber mid, red hot) that intensifies as the value climbs during a run.
- **Live tick-up motion.** During the reveal the number counts up continuously with easing, never snapping. Add a faint motion blur or trailing ghost on fast climbs (turbo) so speed is felt.
- **Digit flicker on change.** Each digit briefly flickers or rolls as it changes, like a mechanical counter or an unstable CRT segment. Small, fast, satisfying.
- **Heat shimmer as it climbs.** As the multiplier approaches the target, a rising visual tension: the glow pulses faster, a subtle heat-haze distortion builds around the number, the color creeps warmer. The screen should feel like it is straining. This is the tension engine of the whole game, spend real effort here.
- **Impact on resolve.** On a clean cash out, a bright green flash and a satisfying settle/bounce on the number. On meltdown, the number snaps red, a sharp screen judder, the glow blows out then dies, and the CRT flicker spikes for a frame. The two outcomes should feel physically different, not just differently colored.

## 4. The slider and controls, with feel

- **Weighted handle.** The slider handle settles with a slight overshoot and spring on release, not a flat teleport. It should feel like it has mass.
- **Handle glow tracks heat.** The handle itself glows in the current zone color and pulses subtly faster as it moves into the red, so the control feels dangerous at the top end.
- **Track fill animation.** When the handle moves, the gradient fill animates to catch up rather than jumping, a quick liquid or charge-up sweep.
- **Button press physicality.** BOOT RIG and the steppers depress on press (scale down slightly, inner shadow deepens, glow spikes) so clicks feel tactile. BOOT RIG specifically should feel like slamming a physical switch: a brief charge-up glow, then a flash on release as the rig boots.
- **Hover life.** Every interactive element gets a subtle hover state, a glow bloom, a border brighten, a faint scanline sweep across it, so the UI feels responsive to the pointer even before clicking.
- **TURBO as a distinct switch.** Keep the amber treatment (it already reads well as ON), but make it look like a toggle switch or a lit indicator, not a sibling of the plus/minus steppers. When ON, a steady amber glow; a satisfying flip animation on toggle.

## 5. The boot transition

The moment between config and reveal is currently likely a hard cut. Make it an event:

- On BOOT, a brief "powering up" beat: the panel glow surges, scanlines roll, a quick flicker, maybe a one-line boot readout, then the reveal screen resolves in. Half a second of ceremony makes the whole thing feel built. Turbo shortens this rather than skipping it entirely.

## 6. Checkpoint locks as events (reveal screen)

Each checkpoint banking should be a small hit of reward, not a silent number change:

- A flash and a brief scale pulse on the SECURED total when a checkpoint locks, plus a tick of particle burst in the tier color. The player should feel each lock land. Stagger nicely so a dense run of locks feels like a satisfying rhythm rather than noise.

## 7. Result screen richness

The meltdown screen is currently strong (committed red, good hierarchy). Push the feel:

- **Meltdown aftermath.** After the red snap, let the screen "cool down": the red glow fades to embers, a few particles drift up and die, the CRT settles. It should feel like the aftermath of a burnout, not just a red screen.
- **The CHECKPOINTS HELD line** currently reads as a consolation. Give it a warmer amber glow and a small settle animation so banking something on a loss still feels like a minor win, not a footnote.
- **NEW PERSONAL BEST** deserves a celebratory beat, a brief gold shimmer or particle burst, since it is a retention hook. Right now it is static amber text.
- **Clean win screen** (the good outcome) should be the most alive screen in the game: green bloom, upward particle celebration, the banked number settling with a bounce, a bright but not obnoxious flash on arrival.

## 8. Color depth beyond the three roles

The green/amber/red system works. Add tonal range within it so it does not read as three flat colors:

- Use darker shades of each role for fills and lighter shades for glows and highlights, so each color has depth. A tier is not just "red", it is deep red fills, bright red edges, an orange-red glow.
- Introduce a cool accent (a cyan or electric blue) sparingly, for UI chrome and non-risk information only (the [SPACE] hint, secondary labels), so the warm risk colors have something cool to pop against. Right now everything is on the warm-to-green axis, and a single cool accent will make the whole palette feel richer and more intentional. Use it very sparingly, it is seasoning, not a fourth role.

---

## Priority order for feel-per-effort

1. Background depth (section 1): vignette, center glow, tier-reactive haze. Biggest fix for "uninviting," low risk.
2. Multiplier centerpiece (section 3): the live tick-up, heat shimmer, and outcome impact. This is the game's core sensation.
3. 2.5D panel (section 2): recessed bevel and corner hardware. Highest "worked on for months" payoff.
4. Boot transition and checkpoint locks (sections 5, 6): cheap ceremony, big feel.
5. Control physicality (section 4): press states, weighted handle.
6. Result richness and color depth (sections 7, 8): polish on the polish.

Reduced-motion note: gate the heavier motion (parallax, shimmer, judder, particles) behind the prefers-reduced-motion setting and the existing photosensitivity toggle, with a calmer fallback, so the game stays comfortable and compliant while feeling rich by default.
