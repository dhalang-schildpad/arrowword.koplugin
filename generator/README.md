# Generator

Python generator for arrowword ("Zweedse puzzel") puzzles. Output: JSON files
according to `../docs/PUZZLE_FORMAT.md` (version 2). The generator itself only
uses the standard library (Python 3.10+).

## Usage

```
python3 generator/generate.py --lang nl --stars 4 --count 3 --seed 1 --out puzzles/generated/
python3 generator/validate.py puzzles/generated/*.json
```

Options:

| Option | Meaning |
|---|---|
| `--lang CODE` | language, selects `generator/data/<lang>/` (default `nl`) |
| `--stars 1..5` | difficulty (default 4); sets grid size, word frequency cutoff, maximum word length and target density (table in `docs/history/PLAN.nl.md` §5) |
| `--count N` | number of puzzles; puzzle k gets seed `seed + k` |
| `--seed S` | seed of the first puzzle (same seed = same puzzle, as long as the time limit does not cut in) |
| `--out DIR` | output directory (default `puzzles/generated`) |
| `--width`, `--height` | grid size, overriding the stars table |
| `--time SEC` | maximum compute time per puzzle (default 30) |
| `--restarts N`, `--iterations N` | search budget: restarts per puzzle and improve steps per restart |

File name: `<lang>-<stars>star-<seed>.json`, title from
`words.LANGUAGES[lang]["title"]` (e.g. `Zweeds 4★ #101` for `nl`). Per puzzle
it prints the density (percentage of letter cells), the number of
double-crossed letters, the number of words and the compute time.

## How it works

1. `WordList` loads `data/<lang>/words.tsv` (filtered by frequency rank per
   the stars level) plus `data/<lang>/fillers.tsv` (hand-written short filler
   words, always allowed; their clues take priority) and `data/<lang>/clues.tsv`
   (hand-written clues for other words), and builds an index per
   (length, position, letter).
2. `Grid` holds the state and guarantees a valid puzzle after every placement:
   every word gets the cell before it as its clue cell (at most one R and one
   D clue per cell), the cell after becomes non-letter, new letters may not
   have letter neighbours across the word (except at crossings).
3. `Generator.grow` places greedily: every structurally valid slot gets a
   score (new letters, crossings, block-cell reuse, a penalty for cells that
   would become dead and for two-letter words); the word list is consulted
   for the best slots and a word is chosen (weighted by frequency).
4. `Generator.improve` ("ruin and recreate"): remove a few words around an
   empty cell or a singly-crossed letter and grow again; keep the result if
   the value (letters + double-crossed letters) does not drop. Several
   restarts; the best grid wins.
5. `export` picks clues (wrapped on spaces into at most 2 lines of 9
   characters, line break `\n`), numbers a solution word of 4-8 letters and
   writes the JSON.

## Data

`generator/data/<lang>/`:

| File | Contents |
|---|---|
| `words.tsv` | word, length, rank, clue, source |
| `fillers.tsv` | hand-written short filler words: word, clue, source |
| `clues.tsv` | merged hand-written clues (from `clue-batches/`): word, clue, source |
| `clue-batches/` | per-batch clue files (see below) and the LLM prompt |
| `placements.tsv` | how often each word gets placed, from `clues.py count` |

See `data/nl/SOURCES.md` for sources and licenses. The Dutch word list is
built once with `prepare_data.py`, which uses the pip package `wordfreq`:

```
python3 -m venv generator/.venv
generator/.venv/bin/pip install wordfreq
generator/.venv/bin/python generator/prepare_data.py --lang nl
```

`generator/data/raw/` (downloads, git-ignored) is shared across languages.

## Clue batches

Words below the hand-clue frequency cutoff only have an automatic,
often-poor Wiktionary clue. `clues.py` drives writing better clues with an
LLM, in batches of `--size` words:

```
python3 generator/clues.py batch 1 --size 200 --min 2 --max 4
# paste data/nl/clue-batches/batch-001-in.tsv into the prompt in data/nl/clue-batches/PROMPT.md,
# save the reply as data/nl/clue-batches/batch-001.tsv
python3 generator/clues.py check generator/data/nl/clue-batches/batch-001.tsv
python3 generator/clues.py merge   # writes data/nl/clues.tsv
```

`clues.py count` generates a batch of puzzles and counts how often each word
gets placed, so `clues.py batch --order placement` can prioritize the words
that matter most for future batches.

## Tests

```
python3 -m unittest discover -s generator/tests
```

`generator/tests/test_generate.py` generates a small puzzle, validates it,
and checks a fixed seed against a stored list of expected answers so future
refactors that accidentally change generation order are caught.

## Known limitations

- Wiktionary-derived clues (words without a hand-written clue) are blunt and
  sometimes odd.
- About half of the letters are crossed only once and 10-16% of the cells
  stay empty (`X`); a real arrowword puzzle is almost fully crossed. That
  needs a larger short-filler-word list and a filler pass on a fixed block
  pattern.
- Three-letter words are over-represented.
