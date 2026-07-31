# OVERHEAT — Mining Rig Crash Game (Stake Engine)

A crash-style game themed as an overheating crypto mining rig, rendered as a
green-on-black terminal. Eleven "rigs" (1.2x–100x) are Stake Engine bet modes
with fixed shutdown temperatures; a **checkpoint-banking** payout distribution
gives every rig an exact **96.5% RTP**: coins lock in rung by rung on the way
up, and a fry keeps everything already banked. Built per
`docs/overheat_rig_build_brief.md`.

## Layout

| Path | What it is |
| --- | --- |
| `tools/gen_overheat_math.py` | Standalone math generator (no slot SDK scaffolding) |
| `tools/verify_overheat_math.py` | Verifier: book structure, CSV/book match, exact RTP + all ACP gates |
| `tools/package_acp.sh` | Assembles `acp-upload/` from the canonical sources below |
| `math-out/publish_files/` | Canonical math package: `index.json`, 11x `books_<rig>.jsonl.zst`, 11x `lookUpTable_<rig>_0.csv` |
| `math-out/configs/` | `config.json` (sha256 hashes, `autoEndRoundDisabled: true`) + frontend config |
| `web-sdk/apps/overheat-rig/` | The game frontend (SvelteKit, DOM-rendered terminal, no Pixi) |
| `web-sdk/apps/overheat-rig/build/` | Production frontend bundle (gitignored; `pnpm run build`) |
| `acp-upload/` | Upload staging (gitignored; regenerate with `tools/package_acp.sh`) |
| `docs/` | The build brief |
| `math-sdk/`, rest of `web-sdk/` | Cloned SDKs (gitignored); `games/fifty_fifty` was the output-format reference |
| `env/` | Python venv for the math tools (gitignored) |

## The math (checkpoint banking)

Per rig with target `T`, a round is a crash temperature `C` under the
hyperbolic crash law `P(C >= x) = r/x`. A per-rig ladder of 12–14 checkpoint
rungs `c_i` (geometric temps below `T`) banks a cumulative amount `B_i` when
crossed; frying keeps the last banked amount. Reaching `T` pays the full
target, split into rare tiers: CLEAN `T` (90% of target hits), OVERDRIVE
`1.5·T` (6%), CRITICAL `3·T` (3%), GOLDEN `10·T` (1%). The reach-law scale `r`
is solved in closed form per rig so the expected payout is exactly `193/200`.

Rigs differ in ladder *shape*, not just cap:

| Profile | Rigs | Character |
| --- | --- | --- |
| DRIP | IDLE / ECO / STANDARD | dense rungs, front-loaded banking — frequent small locks |
| BALANCED | BOOST – FURNACE | steady ladder, classic crash feel |
| SPIKE | INFERNO – PLASMA | sparse back-loaded rungs, long droughts, jackpot tail |

Key properties (all machine-verified by `verify_overheat_math.py`):

- `payoutMultiplier` is an integer, multiplier x 100 (5x win → `500`), identical
  in books and the lookup-table third column.
- Exact class probabilities are quantized to integer weights summing to `10^12`
  with a bounded weight-transfer correction, so weighted RTP is exactly `0.965`
  per mode — not approximately (asserted, and re-verified from the published
  CSVs).
- ACP gates asserted locally before any upload: RTP inside 90.0–96.70%,
  non-zero win rate ≥ 5% per mode (actual: 19–72%), payout std ≥ 0.6
  (actual: 1.1–9.5), max win = `10·T` (1,000x on PLASMA), nothing at or above
  the 5,000x tail threshold.
- Texture gates pinned as regressions: ≥ 12 distinct payouts per rig
  (actual 16–18), no empty payout band between 1x and the target, and a
  profitable (≥ 1x) outcome at least every 15 spins on average
  (actual: every 1.6–12.3 spins by rig).
- Books carry explicit `bank` events per rung crossed and `meltdown` carries
  the kept amount, so resume fast-forward reconstructs the secured state
  exactly. `tools/gen_overheat_math.py` also emits the ladder tables to
  `web-sdk/apps/overheat-rig/src/game/ladders.json`, which the frontend
  imports — the UI odds/ladders can never drift from the published math.
- `crashTemp` lives only inside `events`; wallet maths never touch it.
- `config.json` sets `autoEndRoundDisabled: true` per mode: the frontend calls
  `/wallet/end-round` at the visual shutdown moment, so a mid-animation
  disconnect resumes via `/wallet/authenticate` + the `/bet/event` progress index.

## Math pipeline

```bash
python3 -m venv env && ./env/bin/pip install -r tools/requirements.txt

# full run: eleven rigs x 100k sims, compressed
./env/bin/python tools/gen_overheat_math.py --out math-out

# verify (must print ALL CHECKS PASSED)
cd tools && ../env/bin/python verify_overheat_math.py --out ../math-out
```

## Frontend

```bash
cd web-sdk            # Node 22.16.0, pnpm 10.5.0
pnpm install

# storybook with fixture books (busts, partial banks, near-miss, overdrive, golden, turbo)
cd apps/overheat-rig && pnpm run storybook   # http://localhost:6001

# headless smoke test against a running storybook
node smoke.mjs mode-rigs-book--win-eco-15-x

# production build (output lands in apps/overheat-rig/build/)
pnpm run build
```

Pacing is decorrelated from the outcome (display-only): every round follows
the same time-at-temperature law with a hesitation stall at each checkpoint
rung, so a bust is the win path truncated at the fry point — the first N
seconds of a dud are indistinguishable from a jackpot. Near misses crawl and
hold just below the next rung or the target, and overdrive wins surge past
the BANK rung with their own sting. Turbo (hidden when the jurisdiction sets
`disabledTurbo`) skips the reveal entirely.

To test against the live RGS: open a Developer session on engine.stake.com for
the uploaded game, copy the launch query string
(`?sessionID=...&rgs_url=...&lang=en&device=desktop`) onto a local
`pnpm run dev` URL.

## Publishing (requires your Stake Engine ACP access)

```bash
# verifies the math, then assembles acp-upload/math + acp-upload/frontend
./tools/package_acp.sh
```

1. In the Admin Control Panel, upload the **math files** from
   `acp-upload/math/` (`index.json`, all `books_*.jsonl.zst`, all
   `lookUpTable_*_0.csv`, `config.json`).
2. Upload the **frontend**: the entire contents of `acp-upload/frontend/`
   (`index.html` at the root, `_app/`, gifs, favicon).
3. Publish, then verify the full loop in a Developer session:
   - authenticate shows balance and the eleven rigs with bet levels,
   - boot a rig and watch a bust and a win settle,
   - confirm the balance only changes after the on-screen shutdown/meltdown
     (end-round is called at the shutdown moment),
   - kill the tab mid-climb and relaunch: the round must resume and settle.
