# Overheat Math v4

Implements `Overheat_Math_v4_Redesign_Spec.md`.

## Layout

| Path | Role |
|---|---|
| `config_v4.py` | Mode configs + RTP band budgets (§4) |
| `grid.py` | Outcome grid builder (§6) |
| `generate_books.py` | Weight generator (§7) → `books/<mode>_v4.csv` |
| `validate_books.py` | Harness (§8) → `reports/v4_validation.md` |
| `emit_stake.py` | Weight tables → Stake `math-out/publish_files/` |
| `tests/` | Grid / generator / invariants / v3 regression |

## Commands

```bash
cd math
python3 generate_books.py          # write books/*_v4.csv + manifest.json
python3 validate_books.py          # assert §4/§8; write reports/v4_validation.md
../env/bin/python emit_stake.py    # stage math-out/ (needs zstandard)
python3 tests/test_grid.py
python3 tests/test_invariants.py
python3 tests/test_regression.py   # needs existing v3 LUTs in math-out/
```

Use `--idle-fallback` on `generate_books.py` only if Stake's Base Mode STD check fails.

## Note on §7.3 vs §4.2

Hitting the mandated hit rates on entry tiers requires packing RTP mass near 1.00x
inside the dominant band. That conflicts with the “no outcome > 8% of non-zero
probability” smoothness rule. The generator prioritizes RTP / hit / zero / std /
ladder invariants; `validate_books.py` still asserts the 8% rule so the tension
stays visible (§11).
