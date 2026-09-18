# Puzzles

JSON puzzle files (version 2, see `../docs/PUZZLE_FORMAT.md`).

- `samples/` — a small hand-made test puzzle (`test-small.json`) plus a
  few generated samples at 2 and 4 stars, used for quick manual checks
  and by `generator/tests/`.
- `packs/<lang>/<name>/` — a numbered pack of puzzles for distribution,
  e.g. `packs/nl/4-star-01/` (50 four-star puzzles, seeds 101-150).
  Packs are copied into the plugin's puzzle directory by
  `tools/deploy-kobo.sh`.

Generate a pack with `generator/generate.py`, then check it with
`generator/validate.py`:

```
python3 generator/generate.py --lang nl --stars 4 --count 50 --seed 101 --out puzzles/packs/nl/4-star-01
python3 generator/validate.py puzzles/packs/nl/4-star-01/*.json
```
