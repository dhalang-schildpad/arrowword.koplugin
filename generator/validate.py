#!/usr/bin/env python3
"""Validate puzzle files against docs/PUZZLE_FORMAT.md (version 2).

Usage: python3 generator/validate.py puzzles/*.json
Exit code 1 on errors; warnings are informational.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from words import MAX_CHARS, MAX_LINES, MAX_SINGLE_WORD, split_letters  # noqa: E402

DIRS = {"R": (1, 0), "D": (0, 1), "RD": (1, 0), "DR": (0, 1)}
STEP = {"R": (1, 0), "D": (0, 1), "RD": (0, 1), "DR": (1, 0)}


def validate_puzzle(path):
    errors, warnings = [], []
    with open(path, encoding="utf-8") as f:
        p = json.load(f)

    lang = p.get("lang", "nl")
    w, h = p["w"], p["h"]
    cells = p["cells"]
    if len(cells) != h or any(len(r) != w for r in cells):
        return [f"dimensions {w}x{h} do not match 'cells'"], []

    def cell(x, y):
        if 0 <= x < w and 0 <= y < h:
            return cells[y][x]
        return None

    def is_letter(x, y):
        c = cell(x, y)
        return c is not None and c["t"] == "L"

    # words vs cells
    used = {}  # (x,y) -> number of words
    clues_seen = {}  # (from, dir) -> number of words
    for wd in p["words"]:
        d = wd["dir"]
        vx, vy = wd["from"]
        sx, sy = wd["start"]
        name = f"word {wd['id']} ({wd['answer']})"
        if d not in DIRS:
            errors.append(f"{name}: unknown direction {d}")
            continue
        ox, oy = DIRS[d]
        if (sx, sy) != (vx + ox, vy + oy):
            errors.append(f"{name}: start {wd['start']} is not next to clue cell {wd['from']}")
        oc = cell(vx, vy)
        if oc is None or oc["t"] != "C":
            errors.append(f"{name}: 'from' {wd['from']} is not a clue cell")
        else:
            fitting = [c for c in oc["clues"] if c["dir"] == d]
            if not fitting:
                errors.append(f"{name}: clue cell {wd['from']} has no clue with direction {d}")
            elif fitting[0]["text"] != wd["clue"]:
                errors.append(f"{name}: clue '{wd['clue']}' differs from the cell ('{fitting[0]['text']}')")
        clues_seen[(vx, vy, d)] = clues_seen.get((vx, vy, d), 0) + 1

        stx, sty = STEP[d]
        letters = split_letters(wd["answer"], lang)
        x, y = sx, sy
        for i, letter in enumerate(letters):
            c = cell(x, y)
            if c is None or c["t"] != "L":
                errors.append(f"{name}: cell ({x},{y}) is not a letter cell")
                break
            if c["s"] != letter:
                errors.append(f"{name}: cell ({x},{y}) contains '{c['s']}', expected '{letter}'")
            used[(x, y)] = used.get((x, y), 0) + 1
            x, y = x + stx, y + sty
        if is_letter(x, y):
            errors.append(f"{name}: runs on past the last letter at ({x},{y})")
        if len(letters) < 2:
            errors.append(f"{name}: shorter than 2 letters")

        # quality
        lines = wd["clue"].split("\n")
        if len(lines) > MAX_LINES or any(len(r) > (MAX_CHARS if " " in r else MAX_SINGLE_WORD) for r in lines):
            warnings.append(f"{name}: clue '{wd['clue']}' may not fit in a cell")
        stem = wd["answer"].lower()[:4]
        if len(stem) >= 4 and stem in wd["clue"].lower():
            warnings.append(f"{name}: clue contains the stem of the answer")

    # clues without a word
    n_x = n_c = n_l = 0
    for y in range(h):
        for x in range(w):
            c = cells[y][x]
            if c["t"] == "X":
                n_x += 1
            elif c["t"] == "C":
                n_c += 1
                if not 1 <= len(c.get("clues", [])) <= 2:
                    errors.append(f"clue cell ({x},{y}) has {len(c.get('clues', []))} clues")
                for cl in c.get("clues", []):
                    if clues_seen.get((x, y, cl["dir"]), 0) != 1:
                        errors.append(f"clue '{cl['text']}' at ({x},{y}) has {clues_seen.get((x, y, cl['dir']), 0)} words")
            elif c["t"] == "L":
                n_l += 1
                if (x, y) not in used:
                    errors.append(f"letter cell ({x},{y}) '{c['s']}' is not part of any word")
                if not re.fullmatch(r"[A-Z]|IJ", c["s"]):
                    errors.append(f"letter cell ({x},{y}) has an invalid letter '{c['s']}'")
            else:
                errors.append(f"cell ({x},{y}) has unknown type '{c['t']}'")

    # runs of >=2 adjacent letters must be exactly one word
    starts_r = {(wd["start"][0], wd["start"][1]) for wd in p["words"] if STEP[wd["dir"]] == (1, 0)}
    starts_d = {(wd["start"][0], wd["start"][1]) for wd in p["words"] if STEP[wd["dir"]] == (0, 1)}
    for y in range(h):
        for x in range(w):
            if is_letter(x, y) and not is_letter(x - 1, y) and is_letter(x + 1, y) and (x, y) not in starts_r:
                errors.append(f"horizontal letter run starting at ({x},{y}) has no clue")
            if is_letter(x, y) and not is_letter(x, y - 1) and is_letter(x, y + 1) and (x, y) not in starts_d:
                errors.append(f"vertical letter run starting at ({x},{y}) has no clue")

    # solution word
    sol = p.get("solution")
    if sol:
        letters = []
        for i, (x, y) in enumerate(sol["cells"]):
            c = cell(x, y)
            if c is None or c["t"] != "L":
                errors.append(f"solution: cell {i + 1} ({x},{y}) is not a letter cell")
                continue
            if c.get("n") != i + 1:
                errors.append(f"solution: cell ({x},{y}) has number {c.get('n')}, expected {i + 1}")
            letters.append(c["s"])
        if "".join(letters) != sol["word"]:
            errors.append(f"solution: cells spell '{''.join(letters)}', expected '{sol['word']}'")

    single = sum(1 for v in used.values() if v == 1)
    total = w * h
    warnings.append(f"quality: {n_l}/{total} letters ({100 * n_l // total}%), {n_c} clue cells, "
                     f"{n_x} empty ({100 * n_x // total}%), {single}/{n_l} letters crossed only once")
    return errors, warnings


def main(paths):
    exit_code = 0
    for path in paths:
        errors, warnings = validate_puzzle(path)
        status = "FAIL" if errors else "OK"
        print(f"{status}  {path}")
        for e in errors:
            print(f"  error: {e}")
        for wa in warnings:
            print(f"  note: {wa}")
        if errors:
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["puzzles/samples/test-small.json"]))
