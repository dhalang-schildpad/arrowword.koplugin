#!/usr/bin/env python3
"""Generator voor Nederlandstalige Zweedse puzzels (alleen standaardbibliotheek).

Gebruik:
    python3 generator/generate.py --sterren 4 --aantal 3 --seed 1 --uit puzzles/generated/

Werkwijze (PLAN.md §5, hybride):
1. Een ankerwoord wordt geplaatst; daarna groeit het rooster incrementeel met
   woorden die bestaande letters kruisen. Elk woord krijgt de cel ervoor (links
   bij R, erboven bij D) als omschrijvingscel; die cel mag twee omschrijvingen
   dragen (één R, één D). Het rooster blijft na elke plaatsing een geldige
   puzzel: elke letterreeks van >=2 cellen is precies één woord, elke letter
   zit in een woord, woorden eindigen tegen een niet-lettercel of de rand.
2. Kandidaatwoorden komen uit een index per (lengte, positie, letter).
3. Bij vastlopen worden een paar woorden rond lege plekken verwijderd en wordt
   opnieuw gegroeid ("ruin and recreate"); na te veel mislukkingen volgt een
   herstart met een nieuwe seed. Het dichtste rooster binnen de tijd wint.
4. Ongebruikte cellen worden {"t":"X"}; een oplossingswoord wordt gekozen uit
   de letters in het rooster.
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
from woorden import lees_vulwoorden, lees_woordenlijst, split_letters, wrap_omschrijving  # noqa: E402

# Moeilijkheidstabel uit PLAN.md §5. `dichtheid` is het streefpercentage lettercellen.
STERREN = {
    1: dict(w=11, h=13, max_rang=5000, dichtheid=0.55, max_len=6),
    2: dict(w=11, h=13, max_rang=5000, dichtheid=0.55, max_len=7),
    3: dict(w=13, h=15, max_rang=15000, dichtheid=0.62, max_len=8),
    4: dict(w=13, h=18, max_rang=30000, dichtheid=0.68, max_len=9),
    5: dict(w=15, h=20, max_rang=None, dichtheid=0.72, max_len=10),
}

LEEG, LETTER, BLOK = 0, 1, 2
R, D = 0, 1
RICHTING = ("R", "D")


class Woord:
    __slots__ = ("tekst", "cellen", "rang", "oms")

    def __init__(self, tekst, cellen, rang, oms):
        self.tekst, self.cellen, self.rang, self.oms = tekst, cellen, rang, oms


class Woordenboek:
    """Woordenlijst met een index per (lengte, positie, letter)."""

    def __init__(self, max_rang=None, max_len=12, data_dir=None):
        hand = defaultdict(list)
        for r in lees_vulwoorden(os.path.join(data_dir, "vulwoorden.tsv") if data_dir else None):
            hand[r["woord"]].append(r["omschrijving"])
        self.woorden = []
        for tekst, oms in hand.items():
            self.woorden.append(Woord(tekst, tuple(split_letters(tekst)), 0, oms))
        for r in lees_woordenlijst(os.path.join(data_dir, "woorden.tsv") if data_dir else None):
            if r["woord"] in hand or (max_rang and r["rang"] > max_rang):
                continue
            self.woorden.append(Woord(r["woord"], tuple(split_letters(r["woord"])), r["rang"], [r["omschrijving"]]))
        self.per_lengte = defaultdict(list)
        self.index = defaultdict(lambda: defaultdict(set))
        for i, wd in enumerate(self.woorden):
            n = len(wd.cellen)
            if 2 <= n <= max_len:
                self.per_lengte[n].append(i)
                for pos, letter in enumerate(wd.cellen):
                    self.index[n][(pos, letter)].add(i)
        self.alles = {n: set(ids) for n, ids in self.per_lengte.items()}

    def kandidaten(self, patroon, gebruikt):
        """Ids van woorden die passen op patroon (lijst van letters of None)."""
        n = len(patroon)
        sets = []
        for pos, letter in enumerate(patroon):
            if letter is not None:
                s = self.index[n].get((pos, letter))
                if not s:
                    return []
                sets.append(s)
        if not sets:
            result = self.alles.get(n, set())
        else:
            sets.sort(key=len)
            result = sets[0]
            for s in sets[1:]:
                result = result & s
                if not result:
                    return []
        return [i for i in result if self.woorden[i].tekst not in gebruikt]


class Rooster:
    """Roostertoestand. Cellen zijn LEEG, LETTER of BLOK (omschrijving of X)."""

    def __init__(self, w, h, max_len):
        self.w, self.h, self.max_len = w, h, max_len
        n = w * h
        self.type = [LEEG] * n
        self.letter = [None] * n
        self.in_woord = ([None] * n, [None] * n)   # per richting: woord-id
        self.oms = ([None] * n, [None] * n)        # per richting: woord-id van de omschrijving
        self.blok_refs = [0] * n
        self.woorden = {}                           # id -> (sx, sy, d, Woord)
        self.gebruikt = set()
        self.volgende_id = 1
        self.n_letters = 0

    def copy(self):
        k = Rooster.__new__(Rooster)
        k.w, k.h, k.max_len = self.w, self.h, self.max_len
        k.type = self.type[:]
        k.letter = self.letter[:]
        k.in_woord = (self.in_woord[0][:], self.in_woord[1][:])
        k.oms = (self.oms[0][:], self.oms[1][:])
        k.blok_refs = self.blok_refs[:]
        k.woorden = dict(self.woorden)
        k.gebruikt = set(self.gebruikt)
        k.volgende_id = self.volgende_id
        k.n_letters = self.n_letters
        return k

    def dichtheid(self):
        return self.n_letters / (self.w * self.h)

    def slot(self, sx, sy, d, L):
        """Controleer of een woord van lengte L op (sx,sy) in richting d mag.

        Geeft (patroon, aantal_nieuw, voor_idx, na_idx) of None. na_idx is -1 aan de rand.
        """
        w, h = self.w, self.h
        typ = self.type
        if d == R:
            if sx < 1 or sx + L > w:
                return None
            voor = sy * w + sx - 1
            na = sy * w + sx + L if sx + L < w else -1
            stap = 1
        else:
            if sy < 1 or sy + L > h:
                return None
            voor = (sy - 1) * w + sx
            na = (sy + L) * w + sx if sy + L < h else -1
            stap = w
        if typ[voor] == LETTER or self.oms[d][voor] is not None:
            return None
        if na >= 0 and typ[na] == LETTER:
            return None
        in_w = self.in_woord[d]
        patroon = []
        nieuw = 0
        i = sy * w + sx
        for k in range(L):
            t = typ[i]
            if t == BLOK:
                return None
            if t == LETTER:
                if in_w[i] is not None:
                    return None
                patroon.append(self.letter[i])
            else:
                # nieuwe letters mogen geen letterbuur dwars op het woord hebben
                if d == R:
                    if (sy > 0 and typ[i - w] == LETTER) or (sy < h - 1 and typ[i + w] == LETTER):
                        return None
                else:
                    x = i % w
                    if (x > 0 and typ[i - 1] == LETTER) or (x < w - 1 and typ[i + 1] == LETTER):
                        return None
                patroon.append(None)
                nieuw += 1
            i += stap
        if nieuw == 0:
            return None
        return patroon, nieuw, voor, na

    def plaats(self, sx, sy, d, woord):
        info = self.slot(sx, sy, d, len(woord.cellen))
        assert info is not None, "ongeldige plaatsing"
        _, _, voor, na = info
        wid = self.volgende_id
        self.volgende_id += 1
        self.type[voor] = BLOK
        self.oms[d][voor] = wid
        self.blok_refs[voor] += 1
        if na >= 0:
            self.type[na] = BLOK
            self.blok_refs[na] += 1
        stap = 1 if d == R else self.w
        i = sy * self.w + sx
        for cel in woord.cellen:
            if self.type[i] == LEEG:
                self.type[i] = LETTER
                self.letter[i] = cel
                self.n_letters += 1
            self.in_woord[d][i] = wid
            i += stap
        self.woorden[wid] = (sx, sy, d, woord)
        self.gebruikt.add(woord.tekst)
        return wid

    def verwijder(self, wid):
        sx, sy, d, woord = self.woorden.pop(wid)
        L = len(woord.cellen)
        w = self.w
        stap = 1 if d == R else w
        i = sy * w + sx
        for _ in range(L):
            self.in_woord[d][i] = None
            if self.in_woord[1 - d][i] is None:
                self.type[i] = LEEG
                self.letter[i] = None
                self.n_letters -= 1
            i += stap
        voor = sy * w + sx - 1 if d == R else (sy - 1) * w + sx
        self.oms[d][voor] = None
        self._laat_blok_los(voor)
        if d == R:
            na = sy * w + sx + L if sx + L < w else -1
        else:
            na = (sy + L) * w + sx if sy + L < self.h else -1
        if na >= 0:
            self._laat_blok_los(na)
        self.gebruikt.discard(woord.tekst)

    def _laat_blok_los(self, i):
        self.blok_refs[i] -= 1
        if self.blok_refs[i] == 0:
            self.type[i] = LEEG

    def bedekbaar(self, x, y):
        """Kan lege cel (x,y) nog door een woord (structureel) bedekt worden?"""
        for d in (R, D):
            for L in range(2, self.max_len + 1):
                for off in range(L):
                    sx, sy = (x - off, y) if d == R else (x, y - off)
                    if self.slot(sx, sy, d, L) is not None:
                        return True
        return False

    def cellen_bij_woord(self, wid):
        sx, sy, d, woord = self.woorden[wid]
        return [(sx + k, sy) if d == R else (sx, sy + k) for k in range(len(woord.cellen))]


class Generator:
    def __init__(self, wb, w, h, max_len, rng, doel_dichtheid):
        self.wb, self.w, self.h, self.max_len, self.rng = wb, w, h, max_len, rng
        self.doel = doel_dichtheid

    # -- woordkeuze -----------------------------------------------------------
    def kies_woord(self, ids):
        steekproef = ids if len(ids) <= 40 else self.rng.sample(ids, 40)
        gewichten = [1.0 / math.sqrt(self.wb.woorden[i].rang + 50) for i in steekproef]
        return self.wb.woorden[self.rng.choices(steekproef, gewichten)[0]]

    # -- groeien --------------------------------------------------------------
    def slots(self, rooster):
        """Alle structureel geldige slots met een basisscore (zonder woordenboek)."""
        uit = []
        w, h = rooster.w, rooster.h
        typ = rooster.type
        for d in (R, D):
            for sy in range(h):
                for sx in range(w):
                    for L in range(2, self.max_len + 1):
                        info = rooster.slot(sx, sy, d, L)
                        if info is None:
                            continue
                        patroon, nieuw, voor, na = info
                        kruis = L - nieuw
                        kost = (1 if typ[voor] == LEEG else 0) + (1 if na >= 0 and typ[na] == LEEG else 0)
                        score = nieuw + 1.0 * kruis - 0.6 * kost + self.rng.random() * 0.5
                        uit.append((score, sx, sy, d, L, patroon, nieuw, voor, na))
        uit.sort(key=lambda s: -s[0])
        return uit

    def dode_cellen(self, rooster, sx, sy, d, L, voor, na):
        """Aantal lege cellen dat na plaatsing niet meer bedekbaar zou zijn (simulatie)."""
        w = rooster.w
        proef = rooster.copy()
        # plaats een dummy-woord met unieke letters ('?' komt in geen enkel woord voor)
        dummy = Woord("?" * L, tuple("?" * L), 0, [])
        proef.plaats(sx, sy, d, dummy)
        te_checken = set()
        stap = 1 if d == R else w
        i = sy * w + sx
        for _ in range(L):
            x, y = i % w, i // w
            buren = [(x, y - 1), (x, y + 1)] if d == R else [(x - 1, y), (x + 1, y)]
            te_checken.update(buren)
            i += stap
        for b in (voor, na):
            if b >= 0:
                x, y = b % w, b // w
                te_checken.update([(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)])
        dood = 0
        for x, y in te_checken:
            if 0 <= x < w and 0 <= y < rooster.h and proef.type[y * w + x] == LEEG:
                if rooster.bedekbaar(x, y) and not proef.bedekbaar(x, y):
                    dood += 1
        return dood

    def groei(self, rooster, max_stappen=10 ** 6):
        """Plaats gretig woorden tot er geen slot met kandidaten meer is."""
        for _ in range(max_stappen):
            beste = []
            for s in self.slots(rooster):
                score, sx, sy, d, L, patroon, nieuw, voor, na = s
                if beste and score + 2.5 < beste[-1][0]:
                    break  # verder omlaag wint toch niets meer
                ids = self.wb.kandidaten(patroon, rooster.gebruikt)
                if not ids:
                    continue
                dood = self.dode_cellen(rooster, sx, sy, d, L, voor, na)
                beste.append((score - 1.2 * dood, sx, sy, d, L, ids))
                if len(beste) >= 10:
                    break
            if not beste:
                return
            beste.sort(key=lambda s: -s[0])
            top = beste[:3]
            gewichten = [3, 2, 1][:len(top)]
            _, sx, sy, d, L, ids = self.rng.choices(top, gewichten)[0]
            rooster.plaats(sx, sy, d, self.kies_woord(ids))

    def anker(self, rooster):
        L = min(self.max_len, self.w - 3)
        L = self.rng.randint(max(4, L - 2), L)
        sx = self.rng.randint(1, self.w - L - 1)
        info = rooster.slot(sx, 1, R, L)
        ids = self.wb.kandidaten(info[0], rooster.gebruikt)
        rooster.plaats(sx, 1, R, self.kies_woord(ids))

    # -- verbeteren -----------------------------------------------------------
    def lege_cellen(self, rooster):
        return [i for i, t in enumerate(rooster.type) if t == LEEG]

    def woorden_bij_leeg(self, rooster):
        """Woorden die aan lege cellen grenzen (kandidaten om te verwijderen)."""
        w, h = rooster.w, rooster.h
        leeg = set(self.lege_cellen(rooster))
        uit = set()
        for i in leeg:
            x, y = i % w, i // w
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if 0 <= nx < w and 0 <= ny < h:
                    j = ny * w + nx
                    for d in (R, D):
                        if rooster.in_woord[d][j] is not None:
                            uit.add(rooster.in_woord[d][j])
                        if rooster.oms[d][j] is not None:
                            uit.add(rooster.oms[d][j])
        return list(uit)

    def verbeter(self, rooster, iteraties, deadline):
        huidig = rooster
        beste = huidig.copy()
        zonder_winst = 0
        for _ in range(iteraties):
            if time.time() > deadline or beste.dichtheid() >= self.doel:
                break
            kand = huidig.copy()
            weg = self.woorden_bij_leeg(kand) or list(kand.woorden)
            k = min(len(weg), self.rng.choice((1, 1, 2, 2, 3, 4)))
            for wid in self.rng.sample(weg, k):
                if wid in kand.woorden:
                    kand.verwijder(wid)
            self.groei(kand)
            if kand.n_letters >= huidig.n_letters:
                huidig = kand
            if huidig.n_letters > beste.n_letters:
                beste = huidig.copy()
                zonder_winst = 0
            else:
                zonder_winst += 1
                if zonder_winst >= max(20, iteraties // 4):
                    break
        return beste

    def maak(self, tijd_limiet, iteraties):
        deadline = time.time() + tijd_limiet
        beste = None
        while True:
            rooster = Rooster(self.w, self.h, self.max_len)
            self.anker(rooster)
            self.groei(rooster)
            rooster = self.verbeter(rooster, iteraties, deadline)
            if beste is None or rooster.n_letters > beste.n_letters:
                beste = rooster
            if beste.dichtheid() >= self.doel or time.time() > deadline:
                return beste


# -- oplossingswoord en export ---------------------------------------------------

def kies_oplossing(rooster, wb, rng):
    voorraad = Counter(rooster.letter[i] for i in range(rooster.w * rooster.h) if rooster.type[i] == LETTER)
    kandidaten = [wd for wd in wb.woorden
                  if 4 <= len(wd.cellen) <= 8 and 0 < wd.rang <= 4000
                  and wd.tekst not in rooster.gebruikt
                  and not (Counter(wd.cellen) - voorraad)]
    if not kandidaten:
        return None
    woord = rng.choice(kandidaten)
    per_letter = defaultdict(list)
    for i in range(rooster.w * rooster.h):
        if rooster.type[i] == LETTER:
            per_letter[rooster.letter[i]].append(i)
    cellen = []
    for cel in woord.cellen:
        i = rng.choice(per_letter[cel])
        per_letter[cel].remove(i)
        cellen.append([i % rooster.w, i // rooster.w])
    return {"woord": woord.tekst, "cellen": cellen}


def exporteer(rooster, wb, rng, titel, sterren):
    w, h = rooster.w, rooster.h
    oplossing = kies_oplossing(rooster, wb, rng)
    nummers = {}
    if oplossing:
        for n, (x, y) in enumerate(oplossing["cellen"], 1):
            nummers[y * w + x] = n

    # omschrijvingen kiezen en woorden in leesvolgorde (op omschrijvingscel, R eerst)
    def sleutel(item):
        wid, (sx, sy, d, woord) = item
        return ((sy, sx - 1, d) if d == R else (sy - 1, sx, d))
    woorden, oms_per_cel = [], defaultdict(dict)
    for nr, (wid, (sx, sy, d, woord)) in enumerate(sorted(rooster.woorden.items(), key=sleutel), 1):
        regels = None
        for oms in rng.sample(woord.oms, len(woord.oms)):
            regels = wrap_omschrijving(oms)
            if regels:
                break
        txt = "\n".join(regels) if regels else woord.oms[0]
        van = [sx - 1, sy] if d == R else [sx, sy - 1]
        oms_per_cel[van[1] * w + van[0]][RICHTING[d]] = txt
        woorden.append({"id": nr, "antwoord": woord.tekst, "oms": txt, "dir": RICHTING[d],
                        "van": van, "start": [sx, sy]})

    cellen = []
    for y in range(h):
        rij = []
        for x in range(w):
            i = y * w + x
            if rooster.type[i] == LETTER:
                cel = {"t": "L", "s": rooster.letter[i]}
                if i in nummers:
                    cel["n"] = nummers[i]
            elif i in oms_per_cel:
                cel = {"t": "O", "oms": [{"txt": oms_per_cel[i][d], "dir": d} for d in ("R", "D") if d in oms_per_cel[i]]}
            else:
                cel = {"t": "X"}
            rij.append(cel)
        cellen.append(rij)
    puzzel = {"versie": 1, "titel": titel, "sterren": sterren, "w": w, "h": h,
              "cellen": cellen, "woorden": woorden}
    if oplossing:
        puzzel["oplossing"] = oplossing
    return puzzel


def schrijf_json(puzzel, pad):
    """Compact maar leesbaar: één regel per rij cellen en per woord."""
    delen = []
    for k, v in puzzel.items():
        if k in ("cellen", "woorden"):
            regels = ",\n    ".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in v)
            delen.append(f'  "{k}": [\n    {regels}\n  ]')
        else:
            delen.append(f'  "{k}": {json.dumps(v, ensure_ascii=False)}')
    with open(pad, "w", encoding="utf-8") as f:
        f.write("{\n" + ",\n".join(delen) + "\n}\n")


def genereer(sterren=4, seed=1, w=None, h=None, tijd=30.0, iteraties=300, wb=None, data_dir=None):
    """Maak één puzzel; geeft (puzzel-dict, rooster, seconden)."""
    conf = STERREN[sterren]
    w = w or conf["w"]
    h = h or conf["h"]
    wb = wb or Woordenboek(conf["max_rang"], conf["max_len"], data_dir)
    rng = random.Random(seed)
    t0 = time.time()
    gen = Generator(wb, w, h, conf["max_len"], rng, conf["dichtheid"])
    rooster = gen.maak(tijd, iteraties)
    titel = f"Zweeds {sterren}★ #{seed}"
    puzzel = exporteer(rooster, wb, rng, titel, sterren)
    return puzzel, rooster, time.time() - t0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Genereer Zweedse puzzels (JSON, zie puzzles/FORMAT.md).")
    ap.add_argument("--sterren", type=int, default=4, choices=range(1, 6), help="moeilijkheid 1-5 (standaard 4)")
    ap.add_argument("--aantal", type=int, default=1, help="aantal puzzels")
    ap.add_argument("--seed", type=int, default=1, help="seed van de eerste puzzel; volgende puzzels tellen op")
    ap.add_argument("--uit", default="puzzles/generated", help="uitvoermap")
    ap.add_argument("--breedte", type=int, help="roosterbreedte (overschrijft de sterrentabel)")
    ap.add_argument("--hoogte", type=int, help="roosterhoogte (overschrijft de sterrentabel)")
    ap.add_argument("--tijd", type=float, default=30.0, help="maximale seconden per puzzel (standaard 30)")
    ap.add_argument("--iteraties", type=int, default=300, help="verbeterstappen per herstart (standaard 300)")
    args = ap.parse_args(argv)

    conf = STERREN[args.sterren]
    wb = Woordenboek(conf["max_rang"], conf["max_len"])
    os.makedirs(args.uit, exist_ok=True)
    for k in range(args.aantal):
        seed = args.seed + k
        puzzel, rooster, sec = genereer(args.sterren, seed, args.breedte, args.hoogte, args.tijd, args.iteraties, wb)
        pad = os.path.join(args.uit, f"zweeds-{args.sterren}ster-{seed:04d}.json")
        schrijf_json(puzzel, pad)
        n = rooster.w * rooster.h
        print(f"{pad}: {rooster.w}x{rooster.h}, {rooster.n_letters}/{n} letters "
              f"({100 * rooster.n_letters / n:.0f}%), {len(rooster.woorden)} woorden, {sec:.1f} s")


if __name__ == "__main__":
    main()
