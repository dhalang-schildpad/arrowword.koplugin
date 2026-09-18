# Puzzle format (JSON, version 2)

One file per puzzle, UTF-8, extension `.json`. Coordinates are `[x, y]`,
zero-based, `x` to the right and `y` downwards. `cells[y][x]` is the cell at `(x, y)`.

```json
{
  "version": 2,
  "lang": "nl",
  "title": "Zweeds 4★ #101",
  "stars": 4,
  "w": 13, "h": 14,
  "cells": [
    [ {"t":"X"}, {"t":"C","clues":[{"text":"Venster","dir":"D"}]}, ... ],
    ...
  ],
  "words": [
    {"id":1, "answer":"REEDS", "clue":"Al", "dir":"R", "from":[0,1], "start":[1,1]}
  ],
  "solution": {"word":"ALS", "cells":[[2,3],[3,2],[3,3]]}
}
```

`lang` is an ISO 639-1 code. It tells the plugin which letter bar to show
(Dutch has an `IJ` key) and lets packs of several languages live side by side.

## Cells

| `t` | Meaning | Extra fields |
|---|---|---|
| `L` | letter cell | `s`: the solution letter (upper case; in Dutch `IJ` is one letter in one cell). Optional `n`: number for the solution word. |
| `C` | clue cell | `clues`: list of 1 or 2 `{text, dir}`. With 2 clues the cell is split: first on top, second below. |
| `X` | empty cell (no clue) | none |

`dir` is the arrow direction out of the clue cell:

| `dir` | Answer starts | Runs |
|---|---|---|
| `R` | directly right of the clue cell | to the right |
| `D` | directly below the clue cell | downwards |
| `RD` | directly right of the clue cell | downwards (bent arrow) |
| `DR` | directly below the clue cell | to the right (bent arrow) |

Bent arrows (`RD`, `DR`) are reserved; the plugin currently supports `R` and `D`.

Clue text may contain `\n` to force a line break inside the cell.

## Words

Each word refers to exactly one clue: `from` is the clue cell, `start` the
first letter cell, `dir` equals the `dir` of the clue. `answer` must match the
letter cells from `start` onwards, letter by letter. The cell after the last
letter is a `C`, an `X` or the border.

## Solution word

`solution.cells[i]` is the letter cell numbered `i+1`; together the letters
spell `solution.word`. Optional.

## Rules checked by the validator

`generator/validate.py` in [arrowword-puzzles](https://github.com/dhalang-schildpad/arrowword-puzzles) checks the following.

Errors:
- dimensions match `cells`;
- every word matches its cells, starts next to its clue cell and ends against
  a non-letter cell or the border;
- every clue in a `C` cell has exactly one word and vice versa;
- every run of 2 or more adjacent letter cells (horizontal or vertical) is
  exactly one word; letter cells outside any word do not exist;
- the solution word matches its cells.

Warnings (quality, not fatal):
- letter cells that belong to only one word (percentage);
- `X` cells (percentage);
- clues that do not fit in 2 lines of 9 characters (a single word may be up
  to 11 characters; the plugin then shrinks the font);
- a clue that contains the stem of its answer.

## Version history

- **2**: English keys, `lang` field. Clue cells are `C` with `clues[].text`.
- **1**: Dutch keys (`cellen`, `woorden`, `oms`, ...). No longer read by the plugin.
