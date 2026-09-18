"""Test: generate a small puzzle and have validate.py check it (stdlib unittest).

Run: python3 -m unittest discover -s generator/tests
"""
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import generate  # noqa: E402
import validate  # noqa: E402
from words import split_letters  # noqa: E402

# Captured once from `generate.generate(stars=1, seed=42, w=9, h=9, time_limit=20,
# iterations=300, restarts=2)`; see test_known_seed_matches_expected_answers below.
# A refactor that changes this (with the algorithm otherwise unchanged) usually
# means a dict/set iteration order or a sort key changed somewhere.
EXPECTED_SEED_42_ANSWERS = [
    "ALE", "BENT", "CHILI", "DAGEN", "DEKKER", "ECHT", "EEND", "ENIGE", "ER",
    "IK", "KAN", "KRING", "NES", "ROTS", "STRENG", "TIN", "ZEE", "ZET",
]


class TestGenerate(unittest.TestCase):
    def test_small_puzzle_validates(self):
        puzzle, grid, _ = generate.generate(stars=1, seed=7, w=9, h=9, time_limit=20, iterations=300, restarts=2)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "test.json")
            generate.write_json(puzzle, path)
            errors, warnings = validate.validate_puzzle(path)
        self.assertEqual(errors, [], "validator reports errors: " + "; ".join(errors))
        self.assertEqual(puzzle["w"], 9)
        self.assertEqual(puzzle["h"], 9)
        self.assertGreaterEqual(grid.density(), 0.45)
        self.assertEqual(len({wd["answer"] for wd in puzzle["words"]}), len(puzzle["words"]), "duplicate answers")
        for wd in puzzle["words"]:
            for line in wd["clue"].split("\n"):
                limit = generate.MAX_CHARS if " " in line else generate.MAX_SINGLE_WORD
                self.assertLessEqual(len(line), limit)
            self.assertLessEqual(wd["clue"].count("\n"), generate.MAX_LINES - 1)
        self.assertIn("solution", puzzle)
        self.assertTrue(4 <= len(split_letters(puzzle["solution"]["word"])) <= 8)

    def test_deterministic(self):
        a, _, _ = generate.generate(stars=1, seed=3, w=8, h=8, time_limit=20, iterations=100, restarts=1)
        b, _, _ = generate.generate(stars=1, seed=3, w=8, h=8, time_limit=20, iterations=100, restarts=1)
        self.assertEqual(a["cells"], b["cells"])

    def test_known_seed_matches_expected_answers(self):
        """Regression guard: a fixed seed on a small grid should keep producing
        the same words. See EXPECTED_SEED_42_ANSWERS above."""
        puzzle, _, _ = generate.generate(stars=1, seed=42, w=9, h=9, time_limit=20, iterations=300, restarts=2)
        answers = sorted(wd["answer"] for wd in puzzle["words"])
        self.assertEqual(answers, EXPECTED_SEED_42_ANSWERS)


if __name__ == "__main__":
    unittest.main()
