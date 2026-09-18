#!/usr/bin/env python3
"""One-off data preparation: builds generator/data/<lang>/words.tsv.

Currently only builds the Dutch ('nl') word list; there is no recipe yet for
other languages (see CONTRIBUTING.md for how to add one).

Sources (downloaded to generator/data/raw/, see data/nl/SOURCES.md):
- AriSaadon/NederlandseWoordenboek (CC BY-SA 3.0): OpenTaal words with
  Wiktionary meanings, format "word>meaning1>meaning2>...".
- OpenTaal basiswoorden-gekeurd (BSD / CC BY 3.0): a curated word list.

Requires the pip package `wordfreq` (for the frequency rank):
    python3 -m venv generator/.venv && generator/.venv/bin/pip install wordfreq
    generator/.venv/bin/python generator/prepare_data.py --lang nl

The generator itself (generate.py) only uses the standard library.
"""
import argparse
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from words import DATA_DIR, split_letters, stem_in_clue, wrap_clue  # noqa: E402

RAW_DIR = os.path.join(DATA_DIR, "raw")
SOURCES = {
    "NederlandseWoordenboek-Woordenlijst.txt":
        "https://raw.githubusercontent.com/AriSaadon/NederlandseWoordenboek/main/Woordenlijst.txt",
    "NederlandseWoordenboek-README.md":
        "https://raw.githubusercontent.com/AriSaadon/NederlandseWoordenboek/main/README.md",
    "opentaal-basiswoorden-gekeurd.txt":
        "https://raw.githubusercontent.com/OpenTaal/opentaal-wordlist/master/elements/basiswoorden-gekeurd.txt",
    "opentaal-LICENSE.txt":
        "https://raw.githubusercontent.com/OpenTaal/opentaal-wordlist/master/LICENSE.txt",
}

MIN_CELLS, MAX_CELLS = 2, 12
MAX_WORDS = 40000

# The patterns below match Dutch grammar/spelling, since this script only
# builds the Dutch word list; see the module docstring.
ARTICLES = ("een ", "de ", "het ", "'n ", "'t ", "n ")
# Meanings that describe an inflected/conjugated form: skip these.
INFLECTION = re.compile(
    r"persoon|tegenwoordige tijd|verleden tijd|voltooid deelwoord|meervoud van|"
    r"verkleinwoord|vergrotende trap|overtreffende trap|gebiedende wijs|"
    r"aanvoegende wijs|verbogen vorm|vervoeging|onvoltooid|enkelvoud|"
    r"^zie\b|^variant van|^afkorting|^alternatieve spelling|^oude spelling|"
    r"^verouderde? (spelling|vorm)|^spelfout|^foutieve spelling|^samentrekking",
    re.IGNORECASE)
# Grammatical meta-descriptions that do not yield a usable clue: skip these.
META = re.compile(
    r"^(wordt |word |gebruikt|geeft |verwijst|voorafgaand|duidt|ter aankondiging|"
    r"als aanduiding|aanduiding|zelfstandig gebruikt|ook voor|komt regelmatig|"
    r"(het )?symbool|afkorting|letter van|naam van de letter|in samenstellingen|"
    r"vervangt|eerste deel|achtervoegsel|voorvoegsel|bijvoeglijk|zelfstandig naamwoord|"
    r"werkwoord|drukt |uitdrukking|benaming voor|term voor|woord dat|woord om|"
    r"aanspreekvorm|stopwoord|deel van een)",
    re.IGNORECASE)
# Points where an overly long meaning may be shortened (after the word before the space).
BREAK_POINTS = [" die ", " dat ", " waar", " welke ", " wie ", " om ", " met ", " van ",
                " voor ", " uit ", " in ", " op ", " bij ", " aan ", " door ", " naar ",
                " tot ", " zoals ", " als ", " en ", " of ", " maar ", " tegen ", " over ",
                " onder ", " tussen ", " zonder ", " tijdens ", " volgens ", " per "]
# A shortened clue may not end on one of these words.
BAD_ENDING = {"een", "de", "het", "zeer", "erg", "niet", "heel", "meer", "minder", "zich",
              "te", "en", "of", "is", "zijn", "wordt", "worden", "iets", "iemand", "die", "dat",
              "al", "nog", "ook", "zo", "van", "met", "om", "aan", "op", "in", "uit", "bij",
              "men", "waar", "hoe", "wat", "wie", "voor", "door", "naar", "tot", "over", "onder",
              "tussen", "tegen", "als", "zoals", "per", "zonder", "welke", "geen", "elke", "elk",
              "alle", "andere", "ander", "bepaalde", "bepaald", "zeker", "zekere", "hun", "haar",
              "zijn", "mijn", "je", "jouw", "uw", "ons", "onze", "dit", "deze", "dan", "dus"}
ALLOWED_CHARS = re.compile(r"^[a-zA-ZÀ-ſ' \-]+$")


def download(name, url):
    path = os.path.join(RAW_DIR, name)
    if not os.path.exists(path):
        print(f"downloading {url}")
        urllib.request.urlretrieve(url, path)
    return path


def clean_meaning(meaning):
    """Clean up one Wiktionary meaning; None if unusable."""
    if "'''" in meaning or "|" in meaning or "~" in meaning or "{" in meaning or "=" in meaning:
        return None
    meaning = meaning.replace("''", "")
    meaning = re.sub(r"<[^>]*>", "", meaning)
    for _ in range(3):
        meaning = re.sub(r"\([^()]*\)", "", meaning)
    meaning = re.sub(r"\[[^\]]*\]", "", meaning)
    meaning = re.sub(r"\s+", " ", meaning).strip(" -:")
    if not meaning or INFLECTION.search(meaning) or META.match(meaning):
        return None
    # up to the first punctuation mark
    meaning = re.split(r"[,;.:!?]", meaning, maxsplit=1)[0].strip()
    lower = meaning.lower()
    for art in ARTICLES:
        if lower.startswith(art):
            meaning = meaning[len(art):]
            break
    meaning = meaning.strip(" -")
    if len(meaning) < 3 or not ALLOWED_CHARS.match(meaning):
        return None
    return meaning


def shorten(meaning):
    """Yield candidate clues: the full meaning and increasingly short prefixes."""
    yield meaning
    low = " " + meaning.lower()
    positions = sorted({low.find(k) - 1 for k in BREAK_POINTS if low.find(k) > 0}, reverse=True)
    for p in positions:
        prefix = meaning[:p].strip()
        parts = prefix.split()
        if not parts or parts[-1].lower() in BAD_ENDING:
            continue
        # a single leftover word is often an adjective ("grote"): skip it
        if len(parts) == 1 and (len(parts[0]) < 5 or parts[0].endswith("e")):
            continue
        yield prefix


def choose_clue(word, meanings):
    for meaning in meanings:
        clean = clean_meaning(meaning)
        if not clean:
            continue
        for candidate in shorten(clean):
            if len(candidate) < 3:
                continue
            if stem_in_clue(word.upper(), candidate):
                continue
            if wrap_clue(candidate) is None:
                continue
            return candidate[0].upper() + candidate[1:]
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lang", default="nl", help="language to build the word list for (default nl)")
    ap.add_argument("--max", type=int, default=MAX_WORDS, help="maximum number of words (default 40000)")
    args = ap.parse_args()

    if args.lang != "nl":
        sys.exit(f"prepare_data.py only knows how to build the Dutch ('nl') word list; "
                  f"no recipe for '{args.lang}' yet. See CONTRIBUTING.md.")

    os.makedirs(RAW_DIR, exist_ok=True)
    paths = {name: download(name, url) for name, url in SOURCES.items()}

    try:
        from wordfreq import zipf_frequency
    except ImportError:
        sys.exit("wordfreq is missing: generator/.venv/bin/pip install wordfreq")

    with open(paths["opentaal-basiswoorden-gekeurd.txt"], encoding="utf-8") as f:
        opentaal = {r.strip() for r in f if r.strip()}

    counts = {"lines": 0, "uppercase": 0, "chars": 0, "length": 0, "not_opentaal": 0,
              "no_clue": 0, "usable": 0, "no_frequency": 0}
    candidates = []
    with open(paths["NederlandseWoordenboek-Woordenlijst.txt"], encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if ">" not in line:
                continue
            counts["lines"] += 1
            word, *meanings = line.split(">")
            word = word.strip()
            if word != word.lower():
                counts["uppercase"] += 1
                continue
            if not re.fullmatch(r"[a-z]+", word):
                counts["chars"] += 1
                continue
            cells = split_letters(word.upper(), "nl")
            if not MIN_CELLS <= len(cells) <= MAX_CELLS:
                counts["length"] += 1
                continue
            if word not in opentaal:
                counts["not_opentaal"] += 1
                continue
            clue = choose_clue(word, meanings)
            if not clue:
                counts["no_clue"] += 1
                continue
            zipf = zipf_frequency(word, "nl")
            if zipf == 0:
                counts["no_frequency"] += 1
            counts["usable"] += 1
            candidates.append((-zipf, len(cells), word, clue))

    candidates.sort()
    candidates = candidates[:args.max]
    out_dir = os.path.join(DATA_DIR, args.lang)
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "words.tsv")
    by_length = {}
    with open(out, "w", encoding="utf-8") as f:
        f.write("word\tlength\trank\tclue\tsource\n")
        for rank, (_, length, word, clue) in enumerate(candidates, 1):
            f.write(f"{word.upper()}\t{length}\t{rank}\t{clue}\twiktionary\n")
            by_length[length] = by_length.get(length, 0) + 1

    print(f"lines in dataset:         {counts['lines']}")
    print(f"  skipped uppercase:       {counts['uppercase']}")
    print(f"  skipped characters:      {counts['chars']}")
    print(f"  skipped length:          {counts['length']}")
    print(f"  not in curated OpenTaal: {counts['not_opentaal']}")
    print(f"  no usable clue:          {counts['no_clue']}")
    print(f"usable:                   {counts['usable']} (without wordfreq frequency: {counts['no_frequency']})")
    print(f"written to {out}: {len(candidates)} words ({os.path.getsize(out) // 1024} kB)")
    print("by length: " + ", ".join(f"{k}:{by_length[k]}" for k in sorted(by_length)))


if __name__ == "__main__":
    main()
