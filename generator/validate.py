#!/usr/bin/env python3
"""Valideer puzzelbestanden volgens puzzles/FORMAT.md.

Gebruik: python3 generator/validate.py puzzles/*.json
Exitcode 1 bij fouten; waarschuwingen zijn informatief.
"""
import json
import re
import sys

DIRS = {"R": (1, 0), "D": (0, 1), "RD": (1, 0), "DR": (0, 1)}
STEP = {"R": (1, 0), "D": (0, 1), "RD": (0, 1), "DR": (1, 0)}
MAX_REGELS, MAX_TEKENS = 2, 9
MAX_LOS_WOORD = 11  # een los woord mag langer zijn; de plugin verkleint dan het lettertype


def split_letters(antwoord):
    """Splits een antwoord in cellen; IJ is één cel."""
    out, i = [], 0
    while i < len(antwoord):
        if antwoord[i:i + 2] == "IJ":
            out.append("IJ")
            i += 2
        else:
            out.append(antwoord[i])
            i += 1
    return out


def valideer(pad):
    fouten, waarsch = [], []
    with open(pad, encoding="utf-8") as f:
        p = json.load(f)

    w, h = p["w"], p["h"]
    cellen = p["cellen"]
    if len(cellen) != h or any(len(r) != w for r in cellen):
        return [f"afmetingen {w}x{h} kloppen niet met 'cellen'"], []

    def cel(x, y):
        if 0 <= x < w and 0 <= y < h:
            return cellen[y][x]
        return None

    def is_letter(x, y):
        c = cel(x, y)
        return c is not None and c["t"] == "L"

    # woorden vs cellen
    gebruikt = {}  # (x,y) -> aantal woorden
    oms_gezien = {}  # (van, dir) -> aantal woorden
    for wd in p["woorden"]:
        d = wd["dir"]
        vx, vy = wd["van"]
        sx, sy = wd["start"]
        naam = f"woord {wd['id']} ({wd['antwoord']})"
        if d not in DIRS:
            fouten.append(f"{naam}: onbekende richting {d}")
            continue
        ox, oy = DIRS[d]
        if (sx, sy) != (vx + ox, vy + oy):
            fouten.append(f"{naam}: start {wd['start']} ligt niet naast omschrijvingscel {wd['van']}")
        oc = cel(vx, vy)
        if oc is None or oc["t"] != "O":
            fouten.append(f"{naam}: 'van' {wd['van']} is geen omschrijvingscel")
        else:
            past = [o for o in oc["oms"] if o["dir"] == d]
            if not past:
                fouten.append(f"{naam}: omschrijvingscel {wd['van']} heeft geen omschrijving met richting {d}")
            elif past[0]["txt"] != wd["oms"]:
                fouten.append(f"{naam}: omschrijving '{wd['oms']}' wijkt af van cel ('{past[0]['txt']}')")
        oms_gezien[(vx, vy, d)] = oms_gezien.get((vx, vy, d), 0) + 1

        stx, sty = STEP[d]
        letters = split_letters(wd["antwoord"])
        x, y = sx, sy
        for i, letter in enumerate(letters):
            c = cel(x, y)
            if c is None or c["t"] != "L":
                fouten.append(f"{naam}: cel ({x},{y}) is geen lettercel")
                break
            if c["s"] != letter:
                fouten.append(f"{naam}: cel ({x},{y}) bevat '{c['s']}', verwacht '{letter}'")
            gebruikt[(x, y)] = gebruikt.get((x, y), 0) + 1
            x, y = x + stx, y + sty
        if is_letter(x, y):
            fouten.append(f"{naam}: loopt door na de laatste letter op ({x},{y})")
        if len(letters) < 2:
            fouten.append(f"{naam}: korter dan 2 letters")

        # kwaliteit
        regels = wd["oms"].split("\n")
        if len(regels) > MAX_REGELS or any(len(r) > (MAX_TEKENS if " " in r else MAX_LOS_WOORD) for r in regels):
            waarsch.append(f"{naam}: omschrijving '{wd['oms']}' past mogelijk niet in een cel")
        stam = wd["antwoord"].lower()[:4]
        if len(stam) >= 4 and stam in wd["oms"].lower():
            waarsch.append(f"{naam}: omschrijving bevat de stam van het antwoord")

    # omschrijvingen zonder woord
    n_x = n_o = n_l = 0
    for y in range(h):
        for x in range(w):
            c = cellen[y][x]
            if c["t"] == "X":
                n_x += 1
            elif c["t"] == "O":
                n_o += 1
                if not 1 <= len(c.get("oms", [])) <= 2:
                    fouten.append(f"omschrijvingscel ({x},{y}) heeft {len(c.get('oms', []))} omschrijvingen")
                for o in c.get("oms", []):
                    if oms_gezien.get((x, y, o["dir"]), 0) != 1:
                        fouten.append(f"omschrijving '{o['txt']}' op ({x},{y}) heeft {oms_gezien.get((x, y, o['dir']), 0)} woorden")
            elif c["t"] == "L":
                n_l += 1
                if (x, y) not in gebruikt:
                    fouten.append(f"lettercel ({x},{y}) '{c['s']}' zit in geen enkel woord")
                if not re.fullmatch(r"[A-Z]|IJ", c["s"]):
                    fouten.append(f"lettercel ({x},{y}) heeft ongeldige letter '{c['s']}'")
            else:
                fouten.append(f"cel ({x},{y}) heeft onbekend type '{c['t']}'")

    # aaneengesloten reeksen van >=2 letters moeten precies één woord zijn
    starts_r = {(wd["start"][0], wd["start"][1]) for wd in p["woorden"] if STEP[wd["dir"]] == (1, 0)}
    starts_d = {(wd["start"][0], wd["start"][1]) for wd in p["woorden"] if STEP[wd["dir"]] == (0, 1)}
    for y in range(h):
        for x in range(w):
            if is_letter(x, y) and not is_letter(x - 1, y) and is_letter(x + 1, y) and (x, y) not in starts_r:
                fouten.append(f"horizontale letterreeks vanaf ({x},{y}) zonder omschrijving")
            if is_letter(x, y) and not is_letter(x, y - 1) and is_letter(x, y + 1) and (x, y) not in starts_d:
                fouten.append(f"verticale letterreeks vanaf ({x},{y}) zonder omschrijving")

    # oplossingswoord
    opl = p.get("oplossing")
    if opl:
        letters = []
        for i, (x, y) in enumerate(opl["cellen"]):
            c = cel(x, y)
            if c is None or c["t"] != "L":
                fouten.append(f"oplossing: cel {i + 1} ({x},{y}) is geen lettercel")
                continue
            if c.get("n") != i + 1:
                fouten.append(f"oplossing: cel ({x},{y}) heeft nummer {c.get('n')}, verwacht {i + 1}")
            letters.append(c["s"])
        if "".join(letters) != opl["woord"]:
            fouten.append(f"oplossing: cellen vormen '{''.join(letters)}', verwacht '{opl['woord']}'")

    enkel = sum(1 for v in gebruikt.values() if v == 1)
    tot = w * h
    waarsch.append(f"kwaliteit: {n_l}/{tot} letters ({100 * n_l // tot}%), {n_o} omschrijvingscellen, "
                   f"{n_x} leeg ({100 * n_x // tot}%), {enkel}/{n_l} letters maar één keer gekruist")
    return fouten, waarsch


def main(paden):
    exit_code = 0
    for pad in paden:
        fouten, waarsch = valideer(pad)
        status = "FOUT" if fouten else "OK"
        print(f"{status}  {pad}")
        for f in fouten:
            print(f"  fout: {f}")
        for wa in waarsch:
            print(f"  let op: {wa}")
        if fouten:
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["puzzles/test-klein.json"]))
