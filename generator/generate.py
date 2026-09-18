#!/usr/bin/env python3
"""Generator for arrowword ("Zweedse puzzel") puzzles (standard library only).

Usage:
    python3 generator/generate.py --lang nl --stars 4 --count 3 --seed 1 --out puzzles/generated/

Approach (docs/history/PLAN.nl.md §5, hybrid):
1. An anchor word is placed; the grid then grows incrementally with words
   that cross existing letters. Each word gets the cell before it (to the
   left for R, above for D) as its clue cell; that cell may carry two clues
   (one R, one D). The grid stays a valid puzzle after every placement: every
   run of >=2 letter cells is exactly one word, every letter is in a word,
   words end against a non-letter cell or the border.
2. Candidate words come from an index per (length, position, letter).
3. When stuck, a few words around empty spots are removed and the grid grows
   again ("ruin and recreate"); after too many failures a restart follows
   with a new seed. The densest grid within the time budget wins.
4. Unused cells become {"t":"X"}; a solution word is picked from the letters
   in the grid.
"""
import argparse
import json
import math
import os
import random
import sys
import time
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from words import (  # noqa: E402
    DATA_DIR, LANGUAGES, MAX_CHARS, MAX_LINES, MAX_SINGLE_WORD,
    fix_clue_capitalization, read_clue_file, read_words, require_word_list, split_letters, wrap_clue,
)

# Difficulty table from docs/history/PLAN.nl.md §5. `density` is the target
# percentage of letter cells. Grid sizes follow the shape of the work area on
# a Kobo Forma (nearly square: 1440 wide, ~1450 high after the title bar,
# clue bar and keyboard), so cells are as large as possible.
STARS = {
    1: dict(w=10, h=11, max_rank=5000, density=0.55, max_len=6),
    2: dict(w=11, h=12, max_rank=5000, density=0.55, max_len=7),
    3: dict(w=12, h=13, max_rank=15000, density=0.62, max_len=8),
    4: dict(w=13, h=14, max_rank=30000, density=0.68, max_len=9),
    5: dict(w=14, h=15, max_rank=None, density=0.72, max_len=10),
}

EMPTY, LETTER, BLOCK = 0, 1, 2
R, D = 0, 1
DIRS = ("R", "D")


class Word:
    __slots__ = ("text", "cells", "rank", "clues", "hand")

    def __init__(self, text, cells, rank, clues, hand=False):
        self.text, self.cells, self.rank, self.clues, self.hand = text, cells, rank, clues, hand


class WordList:
    """Word list with an index per (length, position, letter)."""

    def __init__(self, max_rank=None, max_len=12, lang="nl", data_dir=None, hand_only=False):
        self.lang = lang
        data_dir = os.path.join(data_dir or DATA_DIR, lang)
        # frequency rank and Wiktionary clue per word
        by_text = {r["word"]: r for r in read_words(os.path.join(data_dir, "words.tsv"), lang=lang)}
        # hand-written clues: fillers.tsv (curated, always allowed) and
        # clues.tsv (Claude batches; subject to the frequency cutoff)
        hand, curated = defaultdict(list), set()
        for name in ("fillers.tsv", "clues.tsv"):
            path = os.path.join(data_dir, name)
            if os.path.exists(path):
                for r in read_clue_file(path):
                    if r["clue"] not in hand[r["word"]]:
                        hand[r["word"]].append(r["clue"])
                    if name == "fillers.tsv":
                        curated.add(r["word"])
        self.words = []
        # only clues that fit in a cell; words without a fitting clue drop out
        for text, clues in hand.items():
            clues = [c for c in clues if wrap_clue(c)]
            rank = by_text[text]["rank"] if text in by_text else 0
            if text not in curated and max_rank and rank > max_rank:
                continue
            if clues:
                self.words.append(Word(text, tuple(split_letters(text, lang)), rank, clues, hand=True))
        for text, r in by_text.items():
            if hand_only or text in hand or (max_rank and r["rank"] > max_rank):
                continue
            if not wrap_clue(r["clue"]):
                continue
            self.words.append(Word(text, tuple(split_letters(text, lang)), r["rank"], [r["clue"]]))
        self.by_length = defaultdict(list)
        self.index = defaultdict(lambda: defaultdict(set))
        for i, wd in enumerate(self.words):
            n = len(wd.cells)
            if 2 <= n <= max_len:
                self.by_length[n].append(i)
                for pos, letter in enumerate(wd.cells):
                    self.index[n][(pos, letter)].add(i)
        self.all_by_length = {n: set(ids) for n, ids in self.by_length.items()}

    def candidates(self, pattern, used):
        """Ids of words that fit `pattern` (list of letters or None)."""
        n = len(pattern)
        sets = []
        for pos, letter in enumerate(pattern):
            if letter is not None:
                s = self.index[n].get((pos, letter))
                if not s:
                    return []
                sets.append(s)
        if not sets:
            result = self.all_by_length.get(n, set())
        else:
            sets.sort(key=len)
            result = sets[0]
            for s in sets[1:]:
                result = result & s
                if not result:
                    return []
        return [i for i in result if self.words[i].text not in used]


class Grid:
    """Grid state. Cells are EMPTY, LETTER or BLOCK (clue or X)."""

    def __init__(self, w, h, max_len):
        self.w, self.h, self.max_len = w, h, max_len
        n = w * h
        self.type = [EMPTY] * n
        self.letter = [None] * n
        self.in_word = ([None] * n, [None] * n)   # per direction: word id
        self.clue_id = ([None] * n, [None] * n)   # per direction: word id whose clue lives here
        self.block_refs = [0] * n
        self.words = {}                             # id -> (sx, sy, d, Word)
        self.used = set()
        self.next_id = 1
        self.n_letters = 0
        self.n_double = 0                            # letters that belong to two words

    def copy(self):
        k = Grid.__new__(Grid)
        k.w, k.h, k.max_len = self.w, self.h, self.max_len
        k.type = self.type[:]
        k.letter = self.letter[:]
        k.in_word = (self.in_word[0][:], self.in_word[1][:])
        k.clue_id = (self.clue_id[0][:], self.clue_id[1][:])
        k.block_refs = self.block_refs[:]
        k.words = dict(self.words)
        k.used = set(self.used)
        k.next_id = self.next_id
        k.n_letters = self.n_letters
        k.n_double = self.n_double
        return k

    def density(self):
        return self.n_letters / (self.w * self.h)

    def value(self):
        """Objective function for improving: many letters, ideally double-crossed."""
        return self.n_letters + self.n_double

    def walk(self, sx, sy, d):
        """Walk from (sx,sy) in direction d and yield every valid slot.

        Yields (L, pattern, new, before, after, fixed_single) per valid length L:
        pattern is a list of letters/None, new the number of empty cells, before
        the index of the clue cell, after the cell after the word (-1 at the
        border) and fixed_single the number of new letters that could never be
        crossed again.
        """
        w, h = self.w, self.h
        typ = self.type
        if d == R:
            if sx < 1:
                return
            before, step, max_l = sy * w + sx - 1, 1, min(self.max_len, w - sx)
        else:
            if sy < 1:
                return
            before, step, max_l = (sy - 1) * w + sx, w, min(self.max_len, h - sy)
        if typ[before] == LETTER or self.clue_id[d][before] is not None:
            return
        in_w = self.in_word[d]
        pattern, new, fixed_single = [], 0, 0
        i = sy * w + sx
        for L in range(1, max_l + 1):
            t = typ[i]
            if t == BLOCK:
                return
            if t == LETTER:
                if in_w[i] is not None:
                    return
                pattern.append(self.letter[i])
            else:
                # new letters may not have a letter neighbour across the word
                if d == R:
                    b1 = typ[i - w] if sy > 0 else BLOCK
                    b2 = typ[i + w] if sy < h - 1 else BLOCK
                else:
                    x = i % w
                    b1 = typ[i - 1] if x > 0 else BLOCK
                    b2 = typ[i + 1] if x < w - 1 else BLOCK
                if b1 == LETTER or b2 == LETTER:
                    return
                if b1 == BLOCK and b2 == BLOCK:
                    fixed_single += 1
                pattern.append(None)
                new += 1
            i += step
            if L >= 2 and new:
                after = i if L < max_l or (w - sx if d == R else h - sy) > L else -1
                if after < 0 or typ[after] != LETTER:
                    yield L, pattern[:], new, before, after, fixed_single

    def slot(self, sx, sy, d, L):
        """(pattern, new, before, after) for a word of length L at (sx,sy), or None."""
        for length, pattern, new, before, after, _ in self.walk(sx, sy, d):
            if length == L:
                return pattern, new, before, after
            if length > L:
                break
        return None

    def place(self, sx, sy, d, word):
        info = self.slot(sx, sy, d, len(word.cells))
        assert info is not None, "invalid placement"
        _, _, before, after = info
        wid = self.next_id
        self.next_id += 1
        self.type[before] = BLOCK
        self.clue_id[d][before] = wid
        self.block_refs[before] += 1
        if after >= 0:
            self.type[after] = BLOCK
            self.block_refs[after] += 1
        step = 1 if d == R else self.w
        i = sy * self.w + sx
        for cell in word.cells:
            if self.type[i] == EMPTY:
                self.type[i] = LETTER
                self.letter[i] = cell
                self.n_letters += 1
            else:
                self.n_double += 1
            self.in_word[d][i] = wid
            i += step
        self.words[wid] = (sx, sy, d, word)
        self.used.add(word.text)
        return wid

    def remove(self, wid):
        """Remove a word, plus (cascade) crossing words whose letters would
        otherwise remain as loose adjacent letters without a word."""
        queue = [wid]
        while queue:
            w0 = queue.pop()
            if w0 not in self.words:
                continue
            for cells in self._remove_one(w0):
                # cells: consecutive remaining letters of the removed word
                for i in cells[1:]:
                    for d in (R, D):
                        if self.in_word[d][i] is not None:
                            queue.append(self.in_word[d][i])

    def _remove_one(self, wid):
        """Remove one word; returns runs (>=2) of remaining letters."""
        sx, sy, d, word = self.words.pop(wid)
        L = len(word.cells)
        w = self.w
        step = 1 if d == R else w
        i = sy * w + sx
        runs, run = [], []
        for _ in range(L):
            self.in_word[d][i] = None
            if self.in_word[1 - d][i] is None:
                self.type[i] = EMPTY
                self.letter[i] = None
                self.n_letters -= 1
                if len(run) >= 2:
                    runs.append(run)
                run = []
            else:
                self.n_double -= 1
                run.append(i)
            i += step
        if len(run) >= 2:
            runs.append(run)
        before = sy * w + sx - 1 if d == R else (sy - 1) * w + sx
        self.clue_id[d][before] = None
        self._release_block(before)
        if d == R:
            after = sy * w + sx + L if sx + L < w else -1
        else:
            after = (sy + L) * w + sx if sy + L < self.h else -1
        if after >= 0:
            self._release_block(after)
        self.used.discard(word.text)
        return runs

    def _release_block(self, i):
        self.block_refs[i] -= 1
        if self.block_refs[i] == 0:
            self.type[i] = EMPTY

    def coverable(self, x, y):
        """Can empty cell (x,y) still be (structurally) covered by a word?"""
        for d in (R, D):
            for off in range(self.max_len):
                sx, sy = (x - off, y) if d == R else (x, y - off)
                if sx < 0 or sy < 0:
                    break
                for L, *_ in self.walk(sx, sy, d):
                    if L > off:
                        return True
        return False


# Weights for the slot score while growing (see Generator.slots).
WEIGHTS = dict(cross=2.0, cost=0.6, fixed_single=0.7, dead=1.5, two=2.0, three=0.0, long=0.3, mid=0.0)


class Generator:
    def __init__(self, wl, w, h, max_len, rng, target_density, weights=None):
        self.wl, self.w, self.h, self.max_len, self.rng = wl, w, h, max_len, rng
        self.target = target_density
        self.g = dict(WEIGHTS, **(weights or {}))

    # -- word choice ------------------------------------------------------
    def choose_word(self, ids):
        sample = ids if len(ids) <= 40 else self.rng.sample(ids, 40)
        # words with a hand-written clue get a strong preference
        weights = [(4.0 if self.wl.words[i].hand else 1.0) / math.sqrt(self.wl.words[i].rank + 50) for i in sample]
        return self.wl.words[self.rng.choices(sample, weights)[0]]

    # -- growing ------------------------------------------------------------
    def slots(self, grid):
        """All structurally valid slots with a base score (without the word list)."""
        out = []
        w, h = grid.w, grid.h
        typ = grid.type
        rand = self.rng.random
        g = self.g
        for d in (R, D):
            for sy in range(1 if d == D else 0, h):
                for sx in range(1 if d == R else 0, w):
                    for L, pattern, new, before, after, fixed_single in grid.walk(sx, sy, d):
                        cross = L - new
                        cost = (typ[before] == EMPTY) + (after >= 0 and typ[after] == EMPTY)
                        score = new + g["cross"] * cross - g["cost"] * cost - g["fixed_single"] * fixed_single + rand() * 0.5
                        if L == 2:
                            score -= g["two"]
                        elif L == 3:
                            score -= g["three"]
                        elif L >= 8:
                            score -= g["long"] * (L - 7)
                        elif 5 <= L <= 7:
                            score += g["mid"]
                        out.append((score, sx, sy, d, L, pattern, new, before, after))
        out.sort(key=lambda s: -s[0])
        return out

    def dead_cells(self, grid, sx, sy, d, L, before, after):
        """Number of empty cells that would no longer be coverable after
        placement (simulation)."""
        w = grid.w
        trial = grid.copy()
        # place a dummy word with unique letters ('?' occurs in no real word)
        dummy = Word("?" * L, tuple("?" * L), 0, [])
        trial.place(sx, sy, d, dummy)
        to_check = set()
        step = 1 if d == R else w
        i = sy * w + sx
        for _ in range(L):
            x, y = i % w, i // w
            neighbours = [(x, y - 1), (x, y + 1)] if d == R else [(x - 1, y), (x + 1, y)]
            to_check.update(neighbours)
            i += step
        for b in (before, after):
            if b >= 0:
                x, y = b % w, b // w
                to_check.update([(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)])
        dead = 0
        for x, y in to_check:
            if 0 <= x < w and 0 <= y < grid.h and trial.type[y * w + x] == EMPTY:
                if grid.coverable(x, y) and not trial.coverable(x, y):
                    dead += 1
        return dead

    def grow(self, grid, max_steps=10 ** 6):
        """Greedily place words until no slot with candidates remains."""
        max_two = max(2, grid.w * grid.h // 60)   # two-letter words are emergency filler
        for _ in range(max_steps):
            n_two = sum(1 for _, _, _, wd in grid.words.values() if len(wd.cells) == 2)
            best = []
            for s in self.slots(grid):
                score, sx, sy, d, L, pattern, new, before, after = s
                if best and score + 2.5 < best[-1][0]:
                    break  # nothing further down can win anyway
                if L == 2 and n_two >= max_two:
                    continue
                ids = self.wl.candidates(pattern, grid.used)
                if not ids:
                    continue
                dead = self.dead_cells(grid, sx, sy, d, L, before, after)
                best.append((score - self.g["dead"] * dead, sx, sy, d, L, ids))
                if len(best) >= 10:
                    break
            if not best:
                return
            best.sort(key=lambda s: -s[0])
            top = best[:3]
            weights = [3, 2, 1][:len(top)]
            _, sx, sy, d, L, ids = self.rng.choices(top, weights)[0]
            grid.place(sx, sy, d, self.choose_word(ids))

    def anchor(self, grid):
        L = min(self.max_len, self.w - 3)
        L = self.rng.randint(max(4, L - 2), L)
        sx = self.rng.randint(1, self.w - L - 1)
        info = grid.slot(sx, 1, R, L)
        ids = self.wl.candidates(info[0], grid.used)
        grid.place(sx, 1, R, self.choose_word(ids))

    # -- improving -----------------------------------------------------------
    def target_words(self, grid):
        """Choose words to remove: around an empty cell or a singly-crossed letter."""
        w, h = grid.w, grid.h
        rng = self.rng
        empty = [i for i, t in enumerate(grid.type) if t == EMPTY]
        single = [i for i, t in enumerate(grid.type)
                  if t == LETTER and (grid.in_word[R][i] is None or grid.in_word[D][i] is None)]
        if empty and (not single or rng.random() < 0.5):
            middle = rng.choice(empty)
        elif single:
            middle = rng.choice(single)
        else:
            return rng.sample(list(grid.words), min(2, len(grid.words)))
        x, y = middle % w, middle // w
        radius = rng.choice((1, 1, 2))
        area = set()
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h:
                    j = ny * w + nx
                    for d in (R, D):
                        if grid.in_word[d][j] is not None:
                            area.add(grid.in_word[d][j])
                        if grid.clue_id[d][j] is not None:
                            area.add(grid.clue_id[d][j])
        area = list(area)
        k = min(len(area), rng.choice((1, 2, 2, 3)))
        return rng.sample(area, k) if area else []

    def improve(self, grid, iterations, deadline, stale=500):
        """Ruin and recreate: remove a few words around a weak spot and grow again."""
        current = grid
        best = current.copy()
        no_gain = 0
        for _ in range(iterations):
            if time.time() > deadline:
                break
            candidate = current.copy()
            for wid in self.target_words(candidate):
                if wid in candidate.words:
                    candidate.remove(wid)
            self.grow(candidate)
            if candidate.value() >= current.value():
                current = candidate
            if current.value() > best.value():
                best = current.copy()
                no_gain = 0
            else:
                no_gain += 1
                if no_gain >= stale:
                    break
        return best

    def build(self, time_limit, iterations, restarts=6):
        """Grow + improve, with restarts; the best grid within the time wins."""
        deadline = time.time() + time_limit
        best = None
        for _ in range(restarts):
            grid = Grid(self.w, self.h, self.max_len)
            self.anchor(grid)
            self.grow(grid)
            grid = self.improve(grid, iterations, deadline)
            if best is None or grid.value() > best.value():
                best = grid
            if best.density() >= self.target or time.time() > deadline:
                break
        return best


# -- solution word and export ---------------------------------------------------

def pick_solution(grid, wl, rng):
    stock = Counter(grid.letter[i] for i in range(grid.w * grid.h) if grid.type[i] == LETTER)
    candidates = [wd for wd in wl.words
                  if 4 <= len(wd.cells) <= 8 and 0 < wd.rank <= 4000
                  and wd.text not in grid.used
                  and not (Counter(wd.cells) - stock)]
    if not candidates:
        return None
    word = rng.choice(candidates)
    by_letter = defaultdict(list)
    for i in range(grid.w * grid.h):
        if grid.type[i] == LETTER:
            by_letter[grid.letter[i]].append(i)
    cells = []
    for cell in word.cells:
        i = rng.choice(by_letter[cell])
        by_letter[cell].remove(i)
        cells.append([i % grid.w, i // grid.w])
    return {"word": word.text, "cells": cells}


def export(grid, wl, rng, title, stars, lang):
    w, h = grid.w, grid.h
    solution = pick_solution(grid, wl, rng)
    numbers = {}
    if solution:
        for n, (x, y) in enumerate(solution["cells"], 1):
            numbers[y * w + x] = n

    # pick clues and words in reading order (by clue cell, R first)
    def key(item):
        wid, (sx, sy, d, word) = item
        return ((sy, sx - 1, d) if d == R else (sy - 1, sx, d))
    words, clues_per_cell = [], defaultdict(dict)
    for nr, (wid, (sx, sy, d, word)) in enumerate(sorted(grid.words.items(), key=key), 1):
        txt = "\n".join(wrap_clue(rng.choice(word.clues)))
        txt = fix_clue_capitalization(txt, lang)
        clue_from = [sx - 1, sy] if d == R else [sx, sy - 1]
        clues_per_cell[clue_from[1] * w + clue_from[0]][DIRS[d]] = txt
        words.append({"id": nr, "answer": word.text, "clue": txt, "dir": DIRS[d],
                      "from": clue_from, "start": [sx, sy]})

    cells = []
    for y in range(h):
        row = []
        for x in range(w):
            i = y * w + x
            if grid.type[i] == LETTER:
                cell = {"t": "L", "s": grid.letter[i]}
                if i in numbers:
                    cell["n"] = numbers[i]
            elif i in clues_per_cell:
                cell = {"t": "C", "clues": [{"text": clues_per_cell[i][d], "dir": d} for d in ("R", "D") if d in clues_per_cell[i]]}
            else:
                cell = {"t": "X"}
            row.append(cell)
        cells.append(row)
    puzzle = {"version": 2, "lang": lang, "title": title, "stars": stars, "w": w, "h": h,
              "cells": cells, "words": words}
    if solution:
        puzzle["solution"] = solution
    return puzzle


def write_json(puzzle, path):
    """Compact but readable: one line per cell row and per word."""
    parts = []
    for k, v in puzzle.items():
        if k in ("cells", "words"):
            lines = ",\n    ".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in v)
            parts.append(f'  "{k}": [\n    {lines}\n  ]')
        else:
            parts.append(f'  "{k}": {json.dumps(v, ensure_ascii=False)}')
    with open(path, "w", encoding="utf-8") as f:
        f.write("{\n" + ",\n".join(parts) + "\n}\n")


def generate(stars=4, seed=1, w=None, h=None, lang="nl", time_limit=30.0, iterations=3000, wl=None, data_dir=None,
             weights=None, restarts=6):
    """Build one puzzle; returns (puzzle dict, grid, seconds)."""
    conf = STARS[stars]
    w = w or conf["w"]
    h = h or conf["h"]
    # up to 4 stars only words with a hand-written clue (the Wiktionary clues
    # are too often unusable); 5 stars allows everything
    wl = wl or WordList(conf["max_rank"], conf["max_len"], lang, data_dir, hand_only=stars <= 4)
    rng = random.Random(seed)
    t0 = time.time()
    gen = Generator(wl, w, h, conf["max_len"], rng, conf["density"], weights)
    grid = gen.build(time_limit, iterations, restarts)
    title = LANGUAGES[lang]["title"].format(stars=stars, seed=seed)
    puzzle = export(grid, wl, rng, title, stars, lang)
    return puzzle, grid, time.time() - t0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Generate arrowword puzzles (JSON, see docs/PUZZLE_FORMAT.md).")
    ap.add_argument("--lang", default="nl", help="language code, selects generator/data/<lang>/ (default nl)")
    ap.add_argument("--stars", type=int, default=4, choices=range(1, 6), help="difficulty 1-5 (default 4)")
    ap.add_argument("--count", type=int, default=1, help="number of puzzles")
    ap.add_argument("--seed", type=int, default=1, help="seed of the first puzzle; later puzzles count up")
    ap.add_argument("--out", default="puzzles/generated", help="output directory")
    ap.add_argument("--width", type=int, help="grid width (overrides the stars table)")
    ap.add_argument("--height", type=int, help="grid height (overrides the stars table)")
    ap.add_argument("--time", type=float, default=30.0, help="maximum seconds per puzzle (default 30)")
    ap.add_argument("--iterations", type=int, default=3000, help="improve steps per restart (default 3000)")
    ap.add_argument("--restarts", type=int, default=6, help="number of restarts per puzzle (default 6)")
    args = ap.parse_args(argv)

    require_word_list(args.lang)
    conf = STARS[args.stars]
    wl = WordList(conf["max_rank"], conf["max_len"], args.lang, hand_only=args.stars <= 4)
    os.makedirs(args.out, exist_ok=True)
    for k in range(args.count):
        seed = args.seed + k
        puzzle, grid, sec = generate(args.stars, seed, args.width, args.height, args.lang, args.time, args.iterations,
                                      wl, restarts=args.restarts)
        path = os.path.join(args.out, f"{args.lang}-{args.stars}star-{seed:04d}.json")
        write_json(puzzle, path)
        n = grid.w * grid.h
        print(f"{path}: {grid.w}x{grid.h}, {grid.n_letters}/{n} letters "
              f"({100 * grid.n_letters / n:.0f}%), {grid.n_double} double-crossed, "
              f"{len(grid.words)} words, {sec:.1f} s")


if __name__ == "__main__":
    main()
