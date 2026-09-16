"""Gedeelde hulpfuncties voor woorden en omschrijvingen (alleen stdlib).

Gebruikt door prepare_data.py (eenmalig) en generate.py (runtime).
"""
import csv
import os
import re

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
MAX_REGELS, MAX_TEKENS = 2, 12


def split_letters(antwoord):
    """Splits een antwoord (hoofdletters) in cellen; IJ is één cel."""
    out, i = [], 0
    while i < len(antwoord):
        if antwoord[i:i + 2] == "IJ":
            out.append("IJ")
            i += 2
        else:
            out.append(antwoord[i])
            i += 1
    return out


def wrap_omschrijving(tekst, max_regels=MAX_REGELS, max_tekens=MAX_TEKENS):
    """Breek een omschrijving op spaties in regels van max `max_tekens` tekens.

    Geeft de regels terug, of None als het niet in `max_regels` regels past.
    """
    regels, huidige = [], ""
    for woord in tekst.split():
        if len(woord) > max_tekens:
            return None
        if not huidige:
            huidige = woord
        elif len(huidige) + 1 + len(woord) <= max_tekens:
            huidige += " " + woord
        else:
            regels.append(huidige)
            huidige = woord
    if huidige:
        regels.append(huidige)
    if not regels or len(regels) > max_regels:
        return None
    return regels


def stam_in_omschrijving(antwoord, omschrijving):
    """True als de omschrijving de stam (eerste 4 letters, of het hele korte
    woord) van het antwoord bevat; zelfde regel als validate.py."""
    stam = antwoord.lower()[:4]
    return stam in omschrijving.lower()


def lees_woordenlijst(pad=None):
    """Lees woorden.tsv: lijst van dicts met woord, lengte, rang, omschrijving, bron."""
    pad = pad or os.path.join(DATA_DIR, "woorden.tsv")
    rijen = []
    with open(pad, encoding="utf-8", newline="") as f:
        for rij in csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE):
            rij["lengte"] = int(rij["lengte"])
            rij["rang"] = int(rij["rang"])
            rijen.append(rij)
    return rijen


def lees_vulwoorden(pad=None):
    """Lees vulwoorden.tsv: lijst van dicts met woord, omschrijving, bron."""
    pad = pad or os.path.join(DATA_DIR, "vulwoorden.tsv")
    rijen = []
    with open(pad, encoding="utf-8", newline="") as f:
        for rij in csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE):
            rijen.append(rij)
    return rijen
