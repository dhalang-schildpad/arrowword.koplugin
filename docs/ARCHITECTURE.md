# Architecture

## The main decision: generate on a computer, solve on the device

Filling a dense arrowword grid is a search problem. On a laptop a 13 x 14 grid
takes about ten seconds in plain Python; on an e-reader (the Kobo Forma has a
single 1 GHz core and 512 MB of memory) it would block the UI and could take
minutes on an unlucky seed. Generation also needs the word list and clue
database, and the results deserve a quality check before anyone solves them.

So the device only renders and solves. Puzzles are plain JSON files copied
over USB, and the plugin stays small.

```
generator/ (Python)                      arrowword.koplugin/ (Lua, on the device)
  data/<lang>/words.tsv, fillers.tsv,      main.lua      library, progress
              clues.tsv                    puzzle.lua    model, no KOReader deps
  generate.py  -> puzzle JSON  ---USB--->  gameview.lua  painting and input
  validate.py  quality gate                i18n.lua      UI strings
  clues.py     clue batches
```

## Generator

1. **Words.** `WordList` loads the language's words with a frequency rank. Up to four stars only words with a hand-written clue are used. An index per (length, position, letter) makes pattern look-ups cheap.
2. **Growing.** Anchor words are placed, then the grid grows with crossing words. The cell before a word (left of it, or above it) becomes its clue cell; one cell may hold two clues. After every step the grid is a valid puzzle.
3. **Repair.** A ruin-and-recreate loop removes words around holes and singly crossed letters and refills, keeping improvements. Several restarts, best result wins.
4. **Finish.** A solution word is picked from the letters in the grid, clues are chosen and wrapped, and the puzzle is exported.

Everything is driven by one seeded random generator, so a seed reproduces a puzzle exactly.

Difficulty (`STARS` in `generate.py`) sets grid size, the frequency limit for
words, the target letter density and the maximum word length. Hand-clued words
get a strong preference when a slot is filled.

## Plugin

- `puzzle.lua` is a pure model: selection, input, checking, hints, progress. It is tested outside KOReader with LuaJIT.
- `gameview.lua` is one full-screen `InputContainer` that paints everything itself on the Blitbuffer (grid, clue cells with arrows, clue bar, letter bar). Painting directly is much faster on a slow CPU than a widget per cell.
- Clue text picks the largest font that fits without hyphenation, then falls back to hyphenation.
- Refreshes are limited to the region that changed and use the non-flashing "ui" mode, so typing does not flash the screen.
- Progress is stored per puzzle (key: path relative to the puzzle folder) together with a fingerprint of the answers, so progress is ignored if a file is replaced by a different puzzle.

## Things we tried and dropped

- **Tall grids like the printed booklets (13 x 18).** Cells became too small; grids now follow the screen's working area.
- **Automatic clues from Wiktionary definitions.** Too often wrong or unreadable once shortened to fit a cell. They remain only for five-star puzzles, until hand-written clues cover those words too.
- **Ordering clue work by how often a word is placed.** Long words are almost never placed twice, so frequency rank is the better order.
