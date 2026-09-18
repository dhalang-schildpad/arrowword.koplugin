"""Shared helpers for words and clues (stdlib only).

Used by prepare_data.py (one-off), clues.py and generate.py (runtime).
"""
import csv
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
MAX_LINES, MAX_CHARS = 2, 9
MAX_SINGLE_WORD = 11  # a single word that may still stay whole on one line (smaller font)

# Language-specific bits used by the generator and CLIs. `digraphs` lists
# letter pairs that count as one cell (e.g. Dutch "IJ"). `title` is the
# puzzle title template, formatted with `stars` and `seed`.
LANGUAGES = {
    "nl": {"digraphs": ["IJ"], "title": "Zweeds {stars}★ #{seed}"},
    "en": {"digraphs": [], "title": "Arrowword {stars}★ #{seed}"},
}


def split_letters(answer, lang="nl"):
    """Split an answer (upper case) into cells; a digraph of the language is one cell."""
    digraphs = LANGUAGES.get(lang, LANGUAGES["nl"])["digraphs"]
    out, i = [], 0
    while i < len(answer):
        for dg in digraphs:
            if answer[i:i + len(dg)] == dg:
                out.append(dg)
                i += len(dg)
                break
        else:
            out.append(answer[i])
            i += 1
    return out


def wrap_clue(text, max_lines=MAX_LINES, max_chars=MAX_CHARS):
    """Wrap a clue on spaces into lines of at most `max_chars` characters.

    Returns the lines, or None if it does not fit in `max_lines` lines.
    """
    lines, current = [], ""
    for word in text.split():
        # a single word up to MAX_SINGLE_WORD characters stays whole: the plugin
        # then picks a smaller font instead of breaking it
        if max_chars < len(word) <= MAX_SINGLE_WORD:
            if current:
                lines.append(current)
                current = ""
            lines.append(word)
            continue
        # break even longer words with a hyphen, the way the plugin does too
        while len(word) > max_chars:
            if current:
                lines.append(current)
                current = ""
            lines.append(word[:max_chars - 1] + "-")
            word = word[max_chars - 1:]
        if not current:
            current = word
        elif len(current) + 1 + len(word) <= max_chars:
            current += " " + word
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    if not lines or len(lines) > max_lines:
        return None
    return lines


def fix_clue_capitalization(text, lang="nl"):
    """Fix naive capitalization of a leading digraph, e.g. 'Ijsvogel' -> 'IJsvogel'.

    Clue text is capitalized by taking the first character upper case; for a
    language with a digraph (Dutch "IJ") that under-capitalizes the second
    letter, so fix it up here based on the language's digraph list.
    """
    for dg in LANGUAGES.get(lang, LANGUAGES["nl"])["digraphs"]:
        naive = dg[0] + dg[1:].lower()
        if text.startswith(naive):
            return dg + text[len(dg):]
    return text


def stem_in_clue(answer, clue):
    """True if the clue contains the stem (first 4 letters, or the whole short
    word) of the answer; same rule as validate.py."""
    stem = answer.lower()[:4]
    return stem in clue.lower()


def read_words(path=None, lang="nl"):
    """Read words.tsv: list of dicts with word, length, rank, clue, source."""
    path = path or os.path.join(DATA_DIR, lang, "words.tsv")
    rows = []
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE):
            row["length"] = int(row["length"])
            row["rank"] = int(row["rank"])
            rows.append(row)
    return rows


def read_clue_file(path):
    """Read a simple word/clue/source TSV (fillers.tsv or clues.tsv): list of dicts."""
    rows = []
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE):
            rows.append(row)
    return rows


def require_word_list(lang):
    """Raise SystemExit with a helpful message if data/<lang>/words.tsv is missing."""
    path = os.path.join(DATA_DIR, lang, "words.tsv")
    if not os.path.exists(path):
        raise SystemExit(
            f"no word list for '{lang}' yet: {path} does not exist. "
            "See CONTRIBUTING.md for how to add one."
        )
