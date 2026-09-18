# Contributing

Thanks for wanting to help. The goal of this project is simple: **good
arrowword puzzles on e-readers.** "Good" mostly means good clues and good
grids, so that is where help counts most. You do not need an e-reader, and for
most of the work you do not need to write code.

## Where help is most valuable

1. **Clue quality.** Fix a clue that is wrong, clumsy, too hard or too easy. Add a second or third clue to a word so puzzles repeat less.
2. **Word lists.** Remove words nobody knows, add everyday words that are missing, fix frequency ranks that put an obscure word in an easy puzzle.
3. **Grid quality.** Fewer empty cells, more letters that are crossed twice, fewer three-letter words. This is generator work (Python).
4. **A new language.** English is first in line. See "Adding a language".
5. **Device reports.** Run the plugin on your e-reader and tell us how it reads. See [docs/DEVICES.md](docs/DEVICES.md).
6. **Plugin polish.** Lua, KOReader widgets. See [docs/ROADMAP.md](docs/ROADMAP.md).

Found a bad clue while solving? Open an issue with the "Bad clue" template:
the puzzle title, the answer, the clue, and what is wrong. That alone helps.

## Getting started

```bash
git clone https://github.com/dhalang-schildpad/KORreaderSP.git
cd KORreaderSP
python3 -m unittest discover -s generator/tests        # generator tests
python3 generator/generate.py --lang nl --stars 4 --count 1 --seed 42 --out /tmp/aw
python3 generator/validate.py /tmp/aw/*.json
```

Python 3.10+ is all you need for the generator; it uses only the standard
library. (`prepare_data.py`, which rebuilds the word list from OpenTaal and
Wiktionary, needs `wordfreq` in a virtual environment. You rarely need it.)

For plugin work, see "Working on the plugin" below.

## How clues work

Per language there are three files in `generator/data/<lang>/`:

| File | What | Source column |
|---|---|---|
| `words.tsv` | all candidate words with a frequency rank and an automatic Wiktionary clue | `wiktionary` |
| `fillers.tsv` | short, curated filler words that are always allowed | `hand` |
| `clues.tsv` | hand-written clues, **generated** by merging the batch files | `claude` |

Hand-written clues win over the automatic ones, and up to four stars the
generator uses *only* words that have a hand-written clue. The automatic
Wiktionary clues turned out to be unreliable, so a word effectively joins the
game when somebody writes it a clue.

**Do not edit `clues.tsv` directly.** Edit the batch files in
`generator/data/<lang>/clue-batches/` and rebuild:

```bash
# fix or add clues: one line per word, WORD<TAB>clue1<TAB>clue2[<TAB>clue3]
$EDITOR generator/data/nl/clue-batches/batch-003.tsv

python3 generator/clues.py check generator/data/nl/clue-batches/batch-003.tsv
python3 generator/clues.py merge
```

To write clues for words that have none yet, make a new batch. It lists the
next words by frequency together with their automatic clue as a hint:

```bash
python3 generator/clues.py batch 11 --prefix lang --min 5 --max 12 --size 300
# writes clue-batches/lang-011-in.tsv; put your clues in lang-011.tsv
```

### Clue style guide

These rules come from the conventions of printed Dutch arrowwords and from
what fits in a cell. `clues.py check` enforces the mechanical ones.

- **Short.** One or two words if you can. At most two lines of nine characters; a single word may be up to eleven.
- **Prefer a synonym**, otherwise a short definition or a category ("Boom", "Rivier in Italië", "Muzieknoot").
- **Match the grammar.** Plural clue for a plural answer, past tense for past tense, infinitive for infinitive. An inflected answer gets an inflected clue: LIEP -> "Wandelde".
- **Abbreviations** are clued with "(afk.)" or with another abbreviation.
- **Function words** get a grammatical clue: DE -> "Lidwoord".
- **Use different senses** for a word's different clues: BANK -> "Zitmeubel", "Geldinstelling".
- **Never put the stem of the answer in the clue.** No article in front. Start with a capital, no full stop.
- Standard language first; a regional sense may be a second clue, never the only one.
- A pun is fine now and then. Mark it with "?".

The full prompt we use when drafting clues with a language model is in
`clue-batches/PROMPT.md`. **AI-drafted clues are welcome**, on two conditions:
they pass `clues.py check`, and a person who speaks the language has read
them. Say in your pull request which batches were drafted that way.

## Working on the generator

`generator/README.md` describes the scripts. Things to know:

- **Determinism matters.** The same seed must give the same puzzle, so packs can be regenerated. Do not iterate over sets or rely on dict order from external input; the tests pin a known seed.
- **Every puzzle must pass `validate.py`** with zero errors. The warnings line reports quality (letter density, empty cells, singly crossed letters); quote it before and after in your pull request when you change the algorithm.
- Difficulty lives in the `STARS` table in `generate.py`: grid size, frequency limit, target density, maximum word length.

## Adding a language

The format, the plugin and the tools carry a language code, so a language is
mostly data:

1. Add the language to `LANGUAGES` in `generator/words.py` (digraphs that take one cell, such as Dutch `IJ`; the title template).
2. Create `generator/data/<lang>/words.tsv` with `word, length, rank, clue, source`. `prepare_data.py` shows how we built the Dutch list from an open word list, Wiktionary glosses and `wordfreq` ranks. Check the licences and record them in `SOURCES.md`.
3. Write a curated `fillers.tsv` of two- and three-letter words. They carry the grid.
4. Write clues in batches, shortest and most frequent words first. About 2,500 short words plus 3,000 common longer ones gave Dutch full coverage up to four stars.
5. Translate `clue-batches/PROMPT.md`: the conventions differ per country (English arrowwords are usually called "arrowwords" or "arrow crosswords").
6. If the language needs extra keys, add them to `EXTRA_KEYS` in `arrowword.koplugin/gameview.lua`, and add UI strings to `i18n.lua`.

## Working on the plugin

You can develop without a device, using KOReader's desktop emulator.

- Build KOReader next to this repository (`../koreader`) following its
  [build guide](https://github.com/koreader/koreader/blob/master/doc/Building.md).
  On macOS you also need `wget`, and a full clone (not `--depth 1`), otherwise the version string breaks start-up.
- `tools/emulator.sh` links the plugin and the puzzles into the emulator and starts it at Kobo Forma size.
- `tools/test.sh` runs the puzzle model tests (`tools/test_puzzle.lua`) with the emulator's LuaJIT.
- `luacheck arrowword.koplugin` must be clean. Note that `_` is the translation function: use `__` for unused loop variables, never `_`. That mistake crashed the plugin on a real device once.
- The plugin reads a few environment variables that open a puzzle at start-up, replay taps and keys, and save screenshots; they are documented at the top of `tools/emulator.sh`. Use them to attach before/after screenshots to a pull request.
- E-ink rules of thumb: refresh only the region that changed (`UIManager:setDirty(self, function() return "ui", rect end)`), never flash on a key press, keep fills light.

## Pull requests

- Branch from `main`, keep a pull request to one subject, and describe what you checked.
- Run what applies: `python3 -m unittest discover -s generator/tests`, `python3 generator/validate.py <puzzles>`, `python3 generator/clues.py check <batches>`, `luacheck arrowword.koplugin`, `tools/test.sh`.
- Documentation, code and commit messages are in English. Clue data is in the language of the puzzle.
- Commit messages: a short imperative summary line, then why.

## Licensing of contributions

Code contributions are licensed under AGPL-3.0, data contributions (words and
clues) under CC BY-SA 4.0, matching the rest of the project. Only contribute
clues you wrote or drafted yourself; do not copy from puzzle dictionaries or
published puzzles, whose databases are protected.
