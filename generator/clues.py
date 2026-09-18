#!/usr/bin/env python3
"""Tool for hand-written clues (phase 4).

  python3 generator/clues.py batch 1 [--size 200] [--min 2 --max 4] [--lang nl]
      writes data/<lang>/clue-batches/batch-001-in.tsv (word, current clue)
  python3 generator/clues.py check data/nl/clue-batches/batch-001.tsv
      checks a filled-in batch (word<TAB>clue1<TAB>clue2[<TAB>clue3])
  python3 generator/clues.py merge
      merges all approved batches into data/nl/clues.tsv
  python3 generator/clues.py count [--count 40]
      generates puzzles and counts how often each word gets placed, for
      --order placement in `batch`
"""
import argparse
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from words import read_words, split_letters, wrap_clue  # noqa: E402

DATA = os.path.join(HERE, "data")
DEFAULT_LANG = "nl"


def candidates(min_len, max_len, order="rank", lang="nl"):
    rows = [r for r in read_words(os.path.join(DATA, lang, "words.tsv"), lang=lang)
            if min_len <= len(split_letters(r["word"], lang)) <= max_len]
    if order == "placement":
        # most frequently placed words first (see cmd_count), then by frequency
        counts = {}
        path = os.path.join(DATA, lang, "placements.tsv")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                for line in f:
                    w, n = line.rstrip("\n").split("\t")
                    counts[w] = int(n)
        rows.sort(key=lambda r: (-counts.get(r["word"], 0), r["rank"]))
    else:
        rows.sort(key=lambda r: r["rank"])
    return rows


def cmd_count(args):
    """Generate puzzles and count how often each word gets placed."""
    import generate
    from collections import Counter
    counts = Counter()
    n = 0
    for stars, count in ((4, args.count), (3, args.count // 2), (5, args.count // 2)):
        wl = generate.WordList(generate.STARS[stars]["max_rank"], generate.STARS[stars]["max_len"], DEFAULT_LANG)
        for seed in range(1, count + 1):
            puzzle = generate.generate(stars, seed, lang=DEFAULT_LANG, wl=wl)[0]
            counts.update(w["answer"] for w in puzzle["words"])
            n += 1
            print(f"\r{n} puzzles", end="", flush=True)
    print()
    path = os.path.join(DATA, DEFAULT_LANG, "placements.tsv")
    with open(path, "w", encoding="utf-8") as f:
        for w, c in counts.most_common():
            f.write(f"{w}\t{c}\n")
    print(f"{path}: {len(counts)} distinct words in {n} puzzles")


def cmd_batch(args):
    rows = candidates(args.min, args.max, args.order, args.lang)
    start = (args.number - 1) * args.size
    part = rows[start:start + args.size]
    if not part:
        sys.exit(f"no words for batch {args.number} ({len(rows)} candidates)")
    batch_dir = os.path.join(DATA, args.lang, "clue-batches")
    os.makedirs(batch_dir, exist_ok=True)
    path = os.path.join(batch_dir, f"{args.prefix}-{args.number:03d}-in.tsv")
    with open(path, "w", encoding="utf-8") as f:
        f.write("word\tcurrent_clue\n")
        for r in part:
            f.write(f"{r['word']}\t{r['clue']}\n")
    print(f"{path}: {len(part)} words (of {len(rows)} candidates of {args.min}-{args.max} letters)")


def split_line(line):
    """Split a line on tabs, or on '|' if it has none (chat output)."""
    sep = "\t" if "\t" in line else "|"
    return [d.strip() for d in line.split(sep)]


def word_stem(word):
    w = word.lower()
    return w if len(w) < 4 else w[:4]


def check_batch(path, known):
    errors, n_words, n_clues = [], 0, 0
    seen = set()
    with open(path, encoding="utf-8") as f:
        for nr, line in enumerate(f, 1):
            line = line.rstrip("\n")
            if not line.strip() or line.startswith("#") or line.startswith("word\t") or line.startswith("```"):
                continue
            parts = split_line(line)
            word, clues = parts[0].upper(), [d for d in parts[1:] if d]
            if word not in known:
                errors.append(f"line {nr}: {word} is not in the word list")
                continue
            if word in seen:
                errors.append(f"line {nr}: {word} appears twice")
            seen.add(word)
            if not 1 <= len(clues) <= 3:
                errors.append(f"line {nr}: {word} has {len(clues)} clues (1-3 expected)")
            n_words += 1
            for c in clues:
                n_clues += 1
                if not wrap_clue(c):
                    errors.append(f"line {nr}: {word}: '{c}' does not fit in 2 lines of 9 characters")
                if word_stem(word) in c.lower().replace("-", ""):
                    errors.append(f"line {nr}: {word}: '{c}' contains the stem of the answer")
                if c[0].islower():
                    errors.append(f"line {nr}: {word}: '{c}' starts with a lower-case letter")
                if c.endswith("."):
                    errors.append(f"line {nr}: {word}: '{c}' ends with a period")
            if len(set(c.lower() for c in clues)) != len(clues):
                errors.append(f"line {nr}: {word}: duplicate clue")
    return errors, n_words, n_clues


def cmd_check(args):
    known = {r["word"] for r in read_words(os.path.join(DATA, DEFAULT_LANG, "words.tsv"), lang=DEFAULT_LANG)}
    exit_code = 0
    for path in args.files:
        errors, n_w, n_c = check_batch(path, known)
        print(f"{'FAIL' if errors else 'OK'}  {path}: {n_w} words, {n_c} clues")
        for e in errors:
            print("  " + e)
        if errors:
            exit_code = 1
    return exit_code


def cmd_merge(args):
    known = {r["word"] for r in read_words(os.path.join(DATA, DEFAULT_LANG, "words.tsv"), lang=DEFAULT_LANG)}
    batch_dir = os.path.join(DATA, DEFAULT_LANG, "clue-batches")
    out = os.path.join(DATA, DEFAULT_LANG, "clues.tsv")
    n = 0
    with open(out, "w", encoding="utf-8") as f:
        f.write("word\tclue\tsource\n")
        for path in sorted(glob.glob(os.path.join(batch_dir, "batch-*.tsv")) + glob.glob(os.path.join(batch_dir, "lang-*.tsv"))):
            if path.endswith("-in.tsv"):
                continue
            errors, _, _ = check_batch(path, known)
            if errors:
                print(f"skipped (errors): {path}")
                continue
            with open(path, encoding="utf-8") as g:
                for line in g:
                    line = line.rstrip("\n")
                    if not line.strip() or line.startswith("#") or line.startswith("word\t") or line.startswith("```"):
                        continue
                    parts = split_line(line)
                    for c in parts[1:]:
                        if c:
                            f.write(f"{parts[0].upper()}\t{c}\tclaude\n")
                            n += 1
    print(f"{out}: {n} clues")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("batch"); b.add_argument("number", type=int); b.add_argument("--size", type=int, default=200)
    b.add_argument("--min", type=int, default=2); b.add_argument("--max", type=int, default=4)
    b.add_argument("--prefix", default="batch"); b.add_argument("--order", choices=("rank", "placement"), default="rank")
    b.add_argument("--lang", default="nl")
    b.set_defaults(fn=cmd_batch)
    t = sub.add_parser("count"); t.add_argument("--count", type=int, default=40); t.set_defaults(fn=cmd_count)
    c = sub.add_parser("check"); c.add_argument("files", nargs="+"); c.set_defaults(fn=cmd_check)
    m = sub.add_parser("merge"); m.set_defaults(fn=cmd_merge)
    args = ap.parse_args()
    sys.exit(args.fn(args) or 0)


if __name__ == "__main__":
    main()
