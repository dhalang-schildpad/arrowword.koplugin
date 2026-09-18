# Word list sources

The files in this directory are derived from open datasets. They are
**CC BY-SA 3.0** (the clues come from Wiktionary via the dataset below);
that is independent of the AGPL license of the code in this repo.

| File | Contents | Derived from | License |
|---|---|---|---|
| `words.tsv` | ~40k words (2-12 cells) with frequency rank and one short clue | NederlandseWoordenboek + OpenTaal + wordfreq | CC BY-SA 3.0 |
| `fillers.tsv` | ~130 short filler words (2-5 letters) with hand-written clues | own work (this project) | CC BY-SA 3.0 |
| `raw/` (not in git) | raw downloads | see below | see below |

## Sources used

- **AriSaadon/NederlandseWoordenboek** — https://github.com/AriSaadon/NederlandseWoordenboek
  OpenTaal words with meanings from the Dutch Wiktionary
  (dump `nlwiktionary-20211001`). License: CC BY-SA 3.0
  (https://creativecommons.org/licenses/by-sa/3.0/). The clues in
  `words.tsv` are automatically shortened Wiktionary definitions; the
  Wiktionary authors are the original creators.
- **OpenTaal word list** — https://github.com/OpenTaal/opentaal-wordlist
  file `elements/basiswoorden-gekeurd.txt`, used as a filter
  (only words approved by OpenTaal). License: BSD (revised) and/or
  CC BY 3.0; see `raw/opentaal-LICENSE.txt` after running
  `prepare_data.py`. Attribution: "OpenTaal, https://opentaal.org".
- **wordfreq** (Robyn Speer) — https://github.com/rspeer/wordfreq
  Python package, used to determine the frequency rank (`rank`) via
  `zipf_frequency(word, "nl")`. Code MIT; the frequency data is
  CC BY-SA 4.0 and includes SUBTLEX-NL, OpenSubtitles and Wikipedia,
  among others. Only the ranking (a number per word) is used.

## Regenerating

```
python3 -m venv generator/.venv
generator/.venv/bin/pip install wordfreq
generator/.venv/bin/python generator/prepare_data.py --lang nl
```

`prepare_data.py` downloads the raw files to `raw/` (in `.gitignore`)
and writes `words.tsv`. `fillers.tsv` is hand-written.
