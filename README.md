# OVERHEAT — Mining Rig Crash Game (Stake Engine)

A crash-style game themed as an overheating crypto mining rig, rendered as a
green-on-black terminal. Six "rigs" are Stake Engine bet modes with fixed
shutdown temperatures (payout multipliers); one heavy-tailed crash
distribution gives every rig an exact 97% RTP. Built per
`overheat_rig_build_brief.md`.

## Layout

| Path | What it is |
| --- | --- |
| `tools/gen_overheat_math.py` | Standalone math generator (no slot SDK scaffolding) |
| `tools/verify_overheat_math.py` | Verification: book structure, CSV/book match, exact RTP |
| `math-out/publish_files/` | Publishable math: `index.json`, 6x `books_<rig>.jsonl.zst`, 6x `lookUpTable_<rig>_0.csv` |
| `math-out/configs/` | `config.json` (sha256 hashes, `autoEndRoundDisabled: true`) + frontend config |
| `web-sdk/apps/overheat-rig/` | The game frontend (SvelteKit, DOM-rendered terminal, no Pixi) |
| `build/` | Production frontend bundle ready for upload |
| `math-sdk/`, `web-sdk/` | Cloned SDKs (gitignored); `games/fifty_fifty` was the output-format reference |

## Math pipeline

```bash
python3 -m venv env && ./env/bin/pip install -r tools/requirements.txt

# full run: six rigs x 100k sims, compressed
./env/bin/python tools/gen_overheat_math.py --out math-out

# verify (must print ALL CHECKS PASSED)
cd tools && ../env/bin/python verify_overheat_math.py --out ../math-out
```

Key properties (all machine-verified):

- `payoutMultiplier` is an integer, multiplier x 100 (5x win → `500`), identical
  in books and the lookup-table third column.
- Crash temperature: instant bust mass `e = 0.03` at `C = 1.00`, else `C = 1/V`
  (uniform `V`), cosmetically capped at 5000x. Win iff `C >= T`.
- Lookup weights use two exact integer weight classes (win rows / bust rows) so
  weighted RTP is exactly `0.97` per mode — not just approximately.
- `crashTemp` lives only inside `events`; wallet maths never touch it.
- `config.json` sets `autoEndRoundDisabled: true` per mode: the frontend calls
  `/wallet/end-round` at the visual shutdown moment, so a mid-animation
  disconnect resumes via `/wallet/authenticate` + the `/bet/event` progress index.

## Frontend

```bash
cd web-sdk            # Node 22.16.0, pnpm 10.5.0
pnpm install

# storybook with fixture books (bust-far, near-miss, wins, turbo)
cd apps/overheat-rig && pnpm run storybook   # http://localhost:6001

# production build (output lands in apps/overheat-rig/build/)
pnpm run build
```

Pacing is derived from `crashTemp` vs `targetTemp` (display-only): far busts fry
in under a second, near misses crawl and hold just below target, wins climb on
a duration scaled by the rig target. Turbo (hidden when the jurisdiction sets
`disabledTurbo`) skips the reveal entirely.

To test against the live RGS: open a Developer session on engine.stake.com for
the uploaded game, copy the launch query string
(`?sessionID=...&rgs_url=...&lang=en&device=desktop`) onto a local
`pnpm run dev` URL.

## Publishing (requires your Stake Engine ACP access)

1. In the Admin Control Panel, create/select the game and upload the **math
   files** from `math-out/publish_files/` (`index.json`, all `books_*.jsonl.zst`,
   all `lookUpTable_*_0.csv`) plus `math-out/configs/config.json`.
2. Upload the **frontend**: the entire contents of `build/` (`index.html` at the
   root, `_app/`, gifs, favicon).
3. Publish, then verify the full loop in a Developer session:
   - authenticate shows balance and the six rigs with bet levels,
   - boot a rig and watch a bust and a win settle,
   - confirm the balance only changes after the on-screen shutdown/meltdown
     (end-round is called at the shutdown moment),
   - kill the tab mid-climb and relaunch: the round must resume and settle.
