# OVERHEAT: Mining Rig Crash Game — Build Brief

You are building a crash style casino game for **Stake Engine**, themed as an overheating crypto mining rig rendered in a green on black terminal. This document is the full specification. Follow it precisely. Where it says a value is configurable, expose it as a constant; do not invent gameplay rules that are not written here.

---

## 0. Mental model (read this first, it prevents the most common mistakes)

Stake Engine is a Remote Gaming Server (RGS). The core rule that governs the whole architecture:

> **The round outcome is sealed the moment the `/play` API returns.** The math is precomputed offline into "books". At runtime the RGS samples one precomputed book and returns its event list. Nothing the player does after `/play` can change the payout.

Consequences you must respect everywhere:

1. The player's temperature limit (their cashout target) is chosen **before** `/play`. It is not a live decision. It is expressed as the **bet mode** (which rig they boot). There is no live "cash out now" button that affects money.
2. The frontend is a **dumb replayer**. It animates the events returned by the RGS. It never computes, decides, or influences the payout.
3. Money is authoritative server side only. The frontend displays balances returned by the RGS.

Two repositories are involved:

- **`math-sdk`** (Python, >= 3.12, plus Rust/Cargo for the optimizer): defines game rules, simulates outcomes, produces the publishable math files. Clone: `git@github.com:StakeEngine/math-sdk.git`.
- **`web-sdk`** (TypeScript, Svelte 5, Vite, pnpm 10.5, Node 18.18): the game frontend, developed and previewed in Storybook.

---

## 1. Money and units (hard rules, do not deviate)

- Monetary values are **integers with six decimal places of precision**. `1000000` = 1.0 unit, `100000` = 0.1 unit. **Never use floats for money.** Use integers everywhere on the wire.
- Currency and the "MW" (megawatt) label are **display layer only**. Underneath, a bet is a normal integer amount. Show the stake and payouts labelled as MW; store and transmit them as integer amounts.
- Bet levels come from `/wallet/authenticate`: the bet must satisfy `minBet <= bet <= maxBet` and be divisible by `stepBet`. Use the returned `betLevels` array to build the stake selector.

---

## 2. The game

### 2.1 Fiction

The player boots a mining rig. It heats up as it mines. Coins accumulate as the temperature climbs. The player picks **which rig to run**, and each rig has a fixed **shutdown temperature** (their cashout multiplier). If the rig reaches its shutdown temperature, it powers down safely and the player banks the coins at that multiplier. If the rig's silicon fails before reaching the shutdown temperature, it **melts down** and the player loses the stake.

The rig the player chooses **is** their temperature limit. A hotter target rig pays more but is far more likely to fry first.

### 2.2 Rigs (bet modes)

Ship six rigs. Each is a bet mode in `index.json`, all at cost multiplier `1.0` (same stake, different target). At an RTP of 97 percent:

| Rig id      | Display name | Shutdown temp (payout multiplier) | Survive probability |
| ----------- | ------------ | --------------------------------- | ------------------- |
| `eco`       | Eco          | 1.5x                              | 64.7%               |
| `standard`  | Standard     | 2x                                | 48.5%               |
| `overclock` | Overclock    | 5x                                | 19.4%               |
| `furnace`   | Furnace      | 10x                               | 9.7%                |
| `meltdown`  | Meltdown     | 25x                               | 3.9%                |
| `plasma`    | Plasma       | 100x                              | 0.97%               |

The survive probabilities are derived, not hand tuned. See section 3.

---

## 3. The math (implement exactly)

### 3.1 Core distribution

Let `e` be the house edge and `R = 1 - e` the RTP. Default `e = 0.03`, so `R = 0.97`. Make `e` a single configurable constant.

Each round draws a rig **crash temperature** `C`, the multiplier at which the rig fails, using the standard crash construction:

```
draw U ~ Uniform(0, 1)
if U >= R:                 # probability (1 - R) = e  -> instant bust at boot
    C = 1.00
else:                      # probability R
    draw V ~ Uniform(0, 1)  # exclude 0
    C = 1.0 / V             # heavy tail: P(C >= x | survived boot) = 1/x
C_display = min(C, DISPLAY_CAP)   # DISPLAY_CAP default 5000, cosmetic only
```

This gives the survival function `P(C >= x) = R / x` for all `x >= 1`, with an instant bust mass of `e` (the rig fries on boot before producing anything).

### 3.2 Why this is correct and self balancing

For a rig with shutdown temperature `T`, the player wins if `C >= T` and is paid `T`. Expected return is:

```
RTP(T) = T * P(C >= T) = T * (R / T) = R
```

The `T` cancels. **Every rig returns exactly R.** Do not attempt to balance rigs individually; the distribution handles it. This is the reason a single crash distribution serves all six rigs.

Survive probability per rig is simply `R / T`:

- Eco: 0.97 / 1.5 = 0.647
- Standard: 0.97 / 2 = 0.485
- Overclock: 0.97 / 5 = 0.194
- Furnace: 0.97 / 10 = 0.097
- Meltdown: 0.97 / 25 = 0.0388
- Plasma: 0.97 / 100 = 0.0097

### 3.3 Per rig outcome and payout

For a given rig with shutdown temperature `T`, for each simulated round:

- Draw `C` per 3.1.
- If `C >= T`: **win**. `payoutMultiplier = T`. `criteria = "win"`.
- Else: **bust**. `payoutMultiplier = 0`. `criteria = "bust"`.

Realized maximum win is the top rig, 100x. The `DISPLAY_CAP` on `C` is purely for the on screen fry temperature reveal and never affects `payoutMultiplier`.

### 3.4 Book structure

Every book must contain the three required keys `id`, `events`, `payoutMultiplier`. Put the crash temperature into the **events** as cosmetic reveal data. It must never appear in `payoutMultiplier`.

Bust example (rig `overclock`, target 5x, fried at 4.7x):

```json
{
  "id": 1247,
  "payoutMultiplier": 0,
  "events": [
    { "index": 0, "type": "boot",    "rigTier": "overclock", "targetTemp": 5.0, "hashrate": 420 },
    { "index": 1, "type": "heat",    "crashTemp": 4.7 },
    { "index": 2, "type": "meltdown","crashTemp": 4.7 },
    { "index": 3, "type": "setTotalWin", "amount": 0 },
    { "index": 4, "type": "finalWin",    "amount": 0 }
  ],
  "criteria": "bust"
}
```

Win example (rig `overclock`, banked at 5x, rig could have survived to 8.3x):

```json
{
  "id": 883,
  "payoutMultiplier": 5,
  "events": [
    { "index": 0, "type": "boot",     "rigTier": "overclock", "targetTemp": 5.0, "hashrate": 420 },
    { "index": 1, "type": "heat",     "crashTemp": 5.0 },
    { "index": 2, "type": "shutdown", "bankedAt": 5.0, "couldHaveReached": 8.3 },
    { "index": 3, "type": "setTotalWin", "amount": 5 },
    { "index": 4, "type": "finalWin",    "amount": 5 }
  ],
  "criteria": "win"
}
```

Event conventions: `setTotalWin` and `finalWin` are the platform money events and must reflect `payoutMultiplier`. `boot`, `heat`, `meltdown`, `shutdown` are game specific events (the equivalents of the sample games' `reveal` and `winInfo`). `couldHaveReached` is the capped crash temperature `C_display` on a win and is optional flavor; include it, it drives retention.

---

## 4. Math generation

### 4.0 Important: do not fight the slot SDK

The Stake Engine Math SDK is built around **reel based slot games**. Its `GameConfig` requires a `win_type` of `lines`, `ways`, `cluster`, or `scatter`, plus reels, symbols, and a paytable, and it raises at startup if these are missing. A crash game has none of those. That is fine, because two facts make it a non issue:

1. The **RGS is game agnostic**. It validates only the published file format (`index.json`, per mode lookup CSV, and `.jsonl.zst` books with `id`, `events`, `payoutMultiplier`). It does not care how the files were produced. The SDK is explicitly an optional package.
2. Non slot games already ship on the platform. Stake has a live **Burst Games** category built on Stake Engine, and the SDK's own `fifty_fifty` sample is a non slot binary game.

**Primary path: generate the three publishable files directly with a standalone Python script.** Do not model reels, symbols, or a paytable. This is cleaner than bending the slot `GameConfig` to a game that has no board. Use the `fifty_fifty` sample only as a reference for the exact output format, not as a scaffold to inherit.

### 4.1 The generator

Write `tools/gen_overheat_math.py` that, for each of the six rigs, produces:

- `books_<rig>.jsonl.zst`: one book per simulation, each with `id`, `events`, `payoutMultiplier`, per section 3.4. Compress with Zstandard.
- `lookUpTable_<rig>.csv`: rows of `id, probability, payoutMultiplier` as `uint64`. The third column must exactly match each book's `payoutMultiplier`.
- After all rigs, one `index.json` listing all six modes (section 4.4).

Constants at the top of the script: `HOUSE_EDGE = 0.03`, `DISPLAY_CAP = 5000`, `SIMS_PER_MODE = 100000`, and the rig table mapping each rig id to its target `T`.

Core logic, target independent, one function:

```python
def draw_crash_temp(rng, house_edge, display_cap):
    R = 1.0 - house_edge
    u = rng.random()
    if u >= R:                    # probability house_edge: instant bust at boot
        return 1.00
    v = rng.random()              # in (0, 1)
    c = 1.0 / v                   # heavy tail: P(C >= x | survived) = 1/x
    return min(c, display_cap)
```

Per rig with target `T`, per simulation: draw `C`; if `C >= T` then `payoutMultiplier = T`, `criteria = "win"`, else `payoutMultiplier = 0`, `criteria = "bust"`; build the event list; write the book and the CSV row.

The `probability` column can be a uniform integer weight (every row equal) since the crash draw already encodes the odds; the platform derives statistics from the payout and weight columns. Verify empirically (section 4.3) that realized RTP per rig is about 97 percent before publishing.

### 4.2 Optional: run it through the SDK instead

If you prefer the SDK's tooling (multithreaded simulation, the PAR sheet, the Rust optimizer), fork `fifty_fifty` into `games/overheat_rig/` and set the six rigs as bet modes, keeping any reel or symbol fields as minimal dummy values the coin flip sample already uses. This works but adds slot scaffolding the game does not need. Prefer 4.1 unless you specifically want the analytics. Either way the deliverable is identical: the files in section 4.4.

### 4.3 Debug run first, then scale

First pass, force human readable output to verify structure:

```python
num_threads = 1
compression = False
num_sim_args = { "eco": 100, "standard": 100, "overclock": 100,
                 "furnace": 100, "meltdown": 100, "plasma": 100 }
run_conditions = { "run_sims": True, "run_optimization": False, "run_analysis": False }
```

Run `make run GAME=overheat_rig`. Open `library/books/books_overclock.jsonl` and confirm the event structure matches 3.4, and that `payoutMultiplier` is always exactly `0` or the rig's `T`. Cross check a few ids against `library/lookup_tables/lookUpTable_overclock.csv`.

Second pass, production scale:

```python
num_threads = 20
compression = True
num_sim_args = { mode: int(1e5) for mode in modes }   # 100k per mode
run_conditions = { "run_sims": True, "run_optimization": True, "run_analysis": True, "upload_data": False }
```

`run_analysis: True` produces a PAR sheet. Confirm the measured RTP for each mode is approximately 97 percent. Because the payout is binary, optimization is light; its role here is to lock each mode's win hit rate to `R / T`. If you prefer, you may set simulation weights directly to enforce the exact hit rate rather than relying on the optimizer, but keep the pipeline able to verify RTP.

### 4.4 Output files

Publishable files land in `library/publish_files/`:

- `index.json` listing all six modes, each pointing at its `books_<mode>.jsonl.zst` and `lookUpTable_<mode>_0.csv`, with `cost: 1.0`.
- One lookup table CSV per mode: rows of `id, probability, payoutMultiplier` as `uint64`.
- One compressed books file per mode.

`index.json` shape:

```json
{
  "modes": [
    { "name": "eco",       "cost": 1.0, "events": "books_eco.jsonl.zst",       "weights": "lookUpTable_eco_0.csv" },
    { "name": "standard",  "cost": 1.0, "events": "books_standard.jsonl.zst",  "weights": "lookUpTable_standard_0.csv" },
    { "name": "overclock", "cost": 1.0, "events": "books_overclock.jsonl.zst", "weights": "lookUpTable_overclock_0.csv" },
    { "name": "furnace",   "cost": 1.0, "events": "books_furnace.jsonl.zst",   "weights": "lookUpTable_furnace_0.csv" },
    { "name": "meltdown",  "cost": 1.0, "events": "books_meltdown.jsonl.zst",  "weights": "lookUpTable_meltdown_0.csv" },
    { "name": "plasma",    "cost": 1.0, "events": "books_plasma.jsonl.zst",    "weights": "lookUpTable_plasma_0.csv" }
  ]
}
```

The third column of each CSV must exactly match the `payoutMultiplier` values in the corresponding books file. The RGS hashes them to verify. A mismatch fails publication.

---

## 5. Frontend implementation (web-sdk)

### 5.1 Stack and preview

Svelte 5 + Vite, developed in Storybook via TurboRepo. Node 18.18, pnpm 10.5. Create the app module under `apps/overheat_rig/` mirroring an existing sample app. Preview with `pnpm run storybook --filter=overheat_rig`. Drive test rounds from Storybook's book actions before wiring the live RGS.

### 5.2 Launch parameters

The game is loaded with URL query params. Read and use them; **never hardcode `rgs_url`**:

- `sessionID` (required on every request)
- `lang` (ISO 639-1)
- `device` (`mobile` or `desktop`)
- `rgs_url` (base URL for all API calls, dynamic)

### 5.3 Aesthetic

Green on black terminal. Monospace throughout. Suggested palette: background near black (`#0a0e0a`), primary phosphor green (`#00ff41`), amber warning (`#ffb000`), red fault (`#ff2b2b`). Blinking block cursor. Optional subtle scanline overlay and CRT flicker, kept tasteful and toggleable. All game state is communicated as terminal output: boot logs, scrolling hash lines, an ASCII temperature gauge, a coin counter.

### 5.4 Screens and flow

1. **Rig select + stake.** List the six rigs with their shutdown temperature and a short flavor line. Stake input in MW, constrained to `minBet`, `maxBet`, `stepBet`, seeded from `betLevels`. Show balance.
2. **Run.** On confirm, call `/wallet/play` with the selected rig as `mode` and the stake as `amount`. Then replay the returned events.
3. **Reveal.** Boot sequence, then temperature climbs. The gauge color shifts green to amber to red as it approaches `targetTemp`. The coin counter rises with temperature. Terminate in either `shutdown` (bank) or `meltdown` (fry).
4. **Settle.** If `payoutMultiplier > 0`, call `/wallet/end-round` to finalize the win and update the balance. Then return to rig select.

**Round closing behavior (decide this per bet mode).** Each bet mode has an `auto_close_disabled` flag. With the default (`False`), the RGS auto closes the round for efficiency, but the player cannot resume it. With `True`, the frontend must call `/wallet/end-round` itself, which lets a disconnected player resume an unsettled round. For this game the outcome is sealed and the reveal is purely cosmetic, so either works. Recommended: set `auto_close_disabled = True` so the win banks at the visual `shutdown` moment (the manual "END ROUND to collect" beat, as in the `fifty_fifty` sample) and a mid animation disconnect resumes cleanly via `/wallet/authenticate` returning the active round. Use `/bet/event` to persist reveal progress for that resume.

### 5.5 Pacing (critical, this makes or breaks it)

Do not use a fixed round duration. Scale the suspense to the outcome, reading `crashTemp` and `targetTemp` from the events:

- **Bust far below target** (`crashTemp` well under `targetTemp`): fry fast, roughly 1 second. Sharp fault, smoke ASCII, done.
- **Near miss** (`crashTemp` just under `targetTemp`): milk it. Climb slowly, hold agonizingly close to the target, then fry. This is the signature moment.
- **Win**: climb to `targetTemp` and bank, with the climb duration scaling to the rig so a Plasma win earns a longer, tenser crawl. On a win, optionally flash `couldHaveReached` afterward as a "you could have pushed to X" tease.

### 5.6 Turbo

Honor the jurisdiction flag `disabledTurbo` from `/wallet/authenticate`. When turbo is allowed and enabled by the player, skip the animation and jump straight to the settled result. Grinders will play hundreds of rounds; a flat multi second animation every time is unacceptable.

### 5.7 API surface

- `POST {rgs_url}/wallet/authenticate` with `{ sessionID }`. Returns balance, config (`minBet`, `maxBet`, `stepBet`, `betLevels`, jurisdiction flags), and any active round. If a round is still active, continue it.
- `POST {rgs_url}/wallet/balance` with `{ sessionID }` for periodic refresh.
- `POST {rgs_url}/wallet/play` with `{ sessionID, amount, mode }` where `mode` is the rig id. Returns the round to replay.
- `POST {rgs_url}/wallet/end-round` with `{ sessionID }` to settle a win.
- `POST {rgs_url}/bet/event` with `{ sessionID, event }` to record in progress state for disconnect recovery. Use it to persist reveal progress so a refresh mid animation resumes cleanly. It does not change the outcome.

Handle error codes and surface them in terminal style: `ERR_VAL`, `ERR_IPB` (insufficient balance), `ERR_IS` (invalid or expired session), `ERR_ATE`, `ERR_GLE`, `ERR_LOC`, and 500s `ERR_GEN`, `ERR_MAINTENANCE`.

---

## 6. Publishing

1. Run the generator (section 4.1) to produce the per rig books, lookup tables, and `index.json`.
2. Build the frontend: produce the static `dist/` (ensure `vite.config.ts` sets `base: "./"`).
3. Upload the math files and the frontend `dist/` to Stake Engine through the Admin Control Panel.
4. Launch and walk the full loop: authenticate, boot a rig, watch a bust and a win, confirm balances settle through `end-round`.

---

## 7. Constraints and gotchas checklist

- [ ] Money is integer, six decimal places. No floats on the wire. `1000000` = 1.0.
- [ ] The outcome is sealed at `/play`. The frontend never computes or influences payout.
- [ ] The temperature limit is the bet **mode**, chosen before `/play`. There is no live cashout that affects money.
- [ ] `payoutMultiplier` is the final realized payout (`0` or `T`) and must match the CSV third column exactly (hash verified).
- [ ] `crashTemp` lives only inside `events` for animation. It is never in `payoutMultiplier`.
- [ ] Every book has `id`, `events`, `payoutMultiplier`.
- [ ] Books are `.jsonl.zst`. Lookup CSV rows are `uint64` `id, probability, payout`.
- [ ] `rgs_url` is read from URL params, never hardcoded.
- [ ] RTP is invariant across rigs by construction. Do not balance rigs separately.
- [ ] Pacing scales to the outcome. Turbo is honored.
- [ ] Do not force the game into the slot `GameConfig`. Generate the publishable files directly (section 4).
- [ ] Round closing behavior is chosen deliberately via `auto_close_disabled` (section 5.4).

---

## 8. Resolved: discrete rigs, not a slider

The documented `/wallet/play` request is `{ sessionID, amount, mode }` with no free numeric parameter, so a continuous temperature slider is **not** natively supported. Ship the six discrete rigs, with the target expressed as the bet mode. This is confirmed, not an open question, and the rig framing is the stronger product anyway. Do not build a slider UI. If a future SDK version adds a play time parameter, the math already supports a slider for free because RTP is invariant to the chosen target, but do not design for it now.

---

## 9. Definition of done, by phase

- **Phase 0 — Environment.** `math-sdk` set up (`make setup`), `web-sdk` installed (`pnpm install`), a sample game runs in Storybook.
- **Phase 1 — One rig, math only.** The generator produces the `overclock` books, lookup table, and `index.json`. Uncompressed 100 sim output inspected and matches section 3.4, with `payoutMultiplier` always `0` or `5`.
- **Phase 2 — All rigs.** All six rigs generated from one target independent crash draw. 100k sims per rig. Realized RTP per rig verified at about 97 percent.
- **Phase 3 — Frontend replay.** Terminal renders boot, climb, meltdown, and shutdown from replayed events for one rig in Storybook, with outcome scaled pacing.
- **Phase 4 — Live loop.** authenticate, play, end-round wired against the RGS. Stake constraints, error handling, turbo, and disconnect resume all working.
- **Phase 5 — Publish.** Math and `dist/` uploaded to the ACP, live launch walks a bust and a win end to end.
