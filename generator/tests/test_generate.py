"""Test: een kleine puzzel genereren en door validate.py laten keuren (stdlib unittest).

Draaien: python3 -m unittest discover -s generator/tests
"""
import os
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HIER))

import generate  # noqa: E402
import validate  # noqa: E402


class TestGenerate(unittest.TestCase):
    def test_kleine_puzzel_valideert(self):
        puzzel, rooster, _ = generate.genereer(sterren=1, seed=7, w=9, h=9, tijd=20, iteraties=300, herstarts=2)
        with tempfile.TemporaryDirectory() as map_:
            pad = os.path.join(map_, "test.json")
            generate.schrijf_json(puzzel, pad)
            fouten, waarsch = validate.valideer(pad)
        self.assertEqual(fouten, [], "validator meldt fouten: " + "; ".join(fouten))
        self.assertEqual(puzzel["w"], 9)
        self.assertEqual(puzzel["h"], 9)
        self.assertGreaterEqual(rooster.dichtheid(), 0.45)
        self.assertEqual(len({wd["antwoord"] for wd in puzzel["woorden"]}), len(puzzel["woorden"]), "dubbele antwoorden")
        for wd in puzzel["woorden"]:
            for regel in wd["oms"].split("\n"):
                self.assertLessEqual(len(regel), generate.MAX_TEKENS)
            self.assertLessEqual(wd["oms"].count("\n"), generate.MAX_REGELS - 1)
        self.assertIn("oplossing", puzzel)
        self.assertTrue(4 <= len(generate.split_letters(puzzel["oplossing"]["woord"])) <= 8)

    def test_deterministisch(self):
        a, _, _ = generate.genereer(sterren=1, seed=3, w=8, h=8, tijd=20, iteraties=100, herstarts=1)
        b, _, _ = generate.genereer(sterren=1, seed=3, w=8, h=8, tijd=20, iteraties=100, herstarts=1)
        self.assertEqual(a["cellen"], b["cellen"])


if __name__ == "__main__":
    unittest.main()
