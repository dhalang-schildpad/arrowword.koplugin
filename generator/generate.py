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
from woorden import DATA_DIR, MAX_REGELS, MAX_TEKENS, lees_vulwoorden, lees_woordenlijst, split_letters, wrap_omschrijving  # noqa: E402

# Moeilijkheidstabel uit PLAN.md §5. `dichtheid` is het streefpercentage lettercellen.
# Roostermaten volgen de vorm van het werkvlak op een Kobo Forma (bijna
# vierkant: 1440 breed, ~1450 hoog na titelbalk, omschrijvingsbalk en
# toetsenbord), zodat de cellen zo groot mogelijk worden.
STERREN = {
    1: dict(w=10, h=11, max_rang=5000, dichtheid=0.55, max_len=6),
    2: dict(w=11, h=12, max_rang=5000, dichtheid=0.55, max_len=7),
    3: dict(w=12, h=13, max_rang=15000, dichtheid=0.62, max_len=8),
    4: dict(w=13, h=14, max_rang=30000, dichtheid=0.68, max_len=9),
    5: dict(w=14, h=15, max_rang=None, dichtheid=0.72, max_len=10),
}

LEEG, LETTER, BLOK = 0, 1, 2
R, D = 0, 1
RICHTING = ("R", "D")


class Woord:
    __slots__ = ("tekst", "cellen", "rang", "oms", "hand")

    def __init__(self, tekst, cellen, rang, oms, hand=False):
        self.tekst, self.cellen, self.rang, self.oms, self.hand = tekst, cellen, rang, oms, hand


class Woordenboek:
    """Woordenlijst met een index per (lengte, positie, letter)."""

    def __init__(self, max_rang=None, max_len=12, data_dir=None):
        data_dir = data_dir or DATA_DIR
        # frequentierang en Wiktionary-omschrijving per woord
        lijst = {r["woord"]: r for r in lees_woordenlijst(os.path.join(data_dir, "woorden.tsv"))}
        # handgeschreven omschrijvingen: vulwoorden.tsv (gecureerd, altijd toegestaan)
        # en omschrijvingen.tsv (Claude-batches; onderhevig aan de frequentiegrens)
        hand, gecureerd = defaultdict(list), set()
        for naam in ("vulwoorden.tsv", "omschrijvingen.tsv"):
            pad = os.path.join(data_dir, naam)
            if os.path.exists(pad):
                for r in lees_vulwoorden(pad):
                    if r["omschrijving"] not in hand[r["woord"]]:
                        hand[r["woord"]].append(r["omschrijving"])
                    if naam == "vulwoorden.tsv":
                        gecureerd.add(r["woord"])
        self.woorden = []
        # alleen omschrijvingen die in een cel passen; woorden zonder passende omschrijving vallen af
        for tekst, oms in hand.items():
            oms = [o for o in oms if wrap_omschrijving(o)]
            rang = lijst[tekst]["rang"] if tekst in lijst else 0
            if tekst not in gecureerd and max_rang and rang > max_rang:
                continue
            if oms:
                self.woorden.append(Woord(tekst, tuple(split_letters(tekst)), rang, oms, hand=True))
        for tekst, r in lijst.items():
            if tekst in hand or (max_rang and r["rang"] > max_rang):
                continue
            if not wrap_omschrijving(r["omschrijving"]):
                continue
            self.woorden.append(Woord(tekst, tuple(split_letters(tekst)), r["rang"], [r["omschrijving"]]))
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
        self.n_dubbel = 0                           # letters die in twee woorden zitten

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
        k.n_dubbel = self.n_dubbel
        return k

    def dichtheid(self):
        return self.n_letters / (self.w * self.h)

    def waarde(self):
        """Doelfunctie voor het verbeteren: veel letters, liefst dubbel gekruist."""
        return self.n_letters + self.n_dubbel

    def loop(self, sx, sy, d):
        """Loop vanaf (sx,sy) in richting d en geef elk geldig slot.

        Yields (L, patroon, nieuw, voor, na, vast_enkel) per geldige lengte L:
        patroon is een lijst letters/None, nieuw het aantal lege cellen, voor de
        index van de omschrijvingscel, na de cel na het woord (-1 aan de rand) en
        vast_enkel het aantal nieuwe letters dat nooit meer gekruist kan worden.
        """
        w, h = self.w, self.h
        typ = self.type
        if d == R:
            if sx < 1:
                return
            voor, stap, max_l = sy * w + sx - 1, 1, min(self.max_len, w - sx)
        else:
            if sy < 1:
                return
            voor, stap, max_l = (sy - 1) * w + sx, w, min(self.max_len, h - sy)
        if typ[voor] == LETTER or self.oms[d][voor] is not None:
            return
        in_w = self.in_woord[d]
        patroon, nieuw, vast_enkel = [], 0, 0
        i = sy * w + sx
        for L in range(1, max_l + 1):
            t = typ[i]
            if t == BLOK:
                return
            if t == LETTER:
                if in_w[i] is not None:
                    return
                patroon.append(self.letter[i])
            else:
                # nieuwe letters mogen geen letterbuur dwars op het woord hebben
                if d == R:
                    b1 = typ[i - w] if sy > 0 else BLOK
                    b2 = typ[i + w] if sy < h - 1 else BLOK
                else:
                    x = i % w
                    b1 = typ[i - 1] if x > 0 else BLOK
                    b2 = typ[i + 1] if x < w - 1 else BLOK
                if b1 == LETTER or b2 == LETTER:
                    return
                if b1 == BLOK and b2 == BLOK:
                    vast_enkel += 1
                patroon.append(None)
                nieuw += 1
            i += stap
            if L >= 2 and nieuw:
                na = i if L < max_l or (w - sx if d == R else h - sy) > L else -1
                if na < 0 or typ[na] != LETTER:
                    yield L, patroon[:], nieuw, voor, na, vast_enkel

    def slot(self, sx, sy, d, L):
        """(patroon, nieuw, voor, na) voor een woord van lengte L op (sx,sy), of None."""
        for lengte, patroon, nieuw, voor, na, _ in self.loop(sx, sy, d):
            if lengte == L:
                return patroon, nieuw, voor, na
            if lengte > L:
                break
        return None

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
            else:
                self.n_dubbel += 1
            self.in_woord[d][i] = wid
            i += stap
        self.woorden[wid] = (sx, sy, d, woord)
        self.gebruikt.add(woord.tekst)
        return wid

    def verwijder(self, wid):
        """Verwijder een woord, plus (cascade) kruisende woorden waarvan de letters
        anders als losse aangrenzende letters zonder woord zouden overblijven."""
        wachtrij = [wid]
        while wachtrij:
            w0 = wachtrij.pop()
            if w0 not in self.woorden:
                continue
            for cellen in self._verwijder_een(w0):
                # cellen: opeenvolgende overgebleven letters van het verwijderde woord
                for i in cellen[1:]:
                    for d in (R, D):
                        if self.in_woord[d][i] is not None:
                            wachtrij.append(self.in_woord[d][i])

    def _verwijder_een(self, wid):
        """Verwijder één woord; geeft reeksen (>=2) van overgebleven letters terug."""
        sx, sy, d, woord = self.woorden.pop(wid)
        L = len(woord.cellen)
        w = self.w
        stap = 1 if d == R else w
        i = sy * w + sx
        reeksen, reeks = [], []
        for _ in range(L):
            self.in_woord[d][i] = None
            if self.in_woord[1 - d][i] is None:
                self.type[i] = LEEG
                self.letter[i] = None
                self.n_letters -= 1
                if len(reeks) >= 2:
                    reeksen.append(reeks)
                reeks = []
            else:
                self.n_dubbel -= 1
                reeks.append(i)
            i += stap
        if len(reeks) >= 2:
            reeksen.append(reeks)
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
        return reeksen

    def _laat_blok_los(self, i):
        self.blok_refs[i] -= 1
        if self.blok_refs[i] == 0:
            self.type[i] = LEEG

    def bedekbaar(self, x, y):
        """Kan lege cel (x,y) nog door een woord (structureel) bedekt worden?"""
        for d in (R, D):
            for off in range(self.max_len):
                sx, sy = (x - off, y) if d == R else (x, y - off)
                if sx < 0 or sy < 0:
                    break
                for L, *_ in self.loop(sx, sy, d):
                    if L > off:
                        return True
        return False


# Gewichten voor de slotscore bij het groeien (zie Generator.slots).
GEWICHTEN = dict(kruis=2.0, kost=0.6, vast_enkel=0.7, dood=1.5, twee=2.0, drie=0.0, lang=0.3, midden=0.0)


class Generator:
    def __init__(self, wb, w, h, max_len, rng, doel_dichtheid, gewichten=None):
        self.wb, self.w, self.h, self.max_len, self.rng = wb, w, h, max_len, rng
        self.doel = doel_dichtheid
        self.g = dict(GEWICHTEN, **(gewichten or {}))

    # -- woordkeuze -----------------------------------------------------------
    def kies_woord(self, ids):
        steekproef = ids if len(ids) <= 40 else self.rng.sample(ids, 40)
        # woorden met een handgeschreven omschrijving krijgen sterke voorkeur
        gewichten = [(4.0 if self.wb.woorden[i].hand else 1.0) / math.sqrt(self.wb.woorden[i].rang + 50) for i in steekproef]
        return self.wb.woorden[self.rng.choices(steekproef, gewichten)[0]]

    # -- groeien --------------------------------------------------------------
    def slots(self, rooster):
        """Alle structureel geldige slots met een basisscore (zonder woordenboek)."""
        uit = []
        w, h = rooster.w, rooster.h
        typ = rooster.type
        rand = self.rng.random
        g = self.g
        for d in (R, D):
            for sy in range(1 if d == D else 0, h):
                for sx in range(1 if d == R else 0, w):
                    for L, patroon, nieuw, voor, na, vast_enkel in rooster.loop(sx, sy, d):
                        kruis = L - nieuw
                        kost = (typ[voor] == LEEG) + (na >= 0 and typ[na] == LEEG)
                        score = nieuw + g["kruis"] * kruis - g["kost"] * kost - g["vast_enkel"] * vast_enkel + rand() * 0.5
                        if L == 2:
                            score -= g["twee"]
                        elif L == 3:
                            score -= g["drie"]
                        elif L >= 8:
                            score -= g["lang"] * (L - 7)
                        elif 5 <= L <= 7:
                            score += g["midden"]
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
        max_twee = max(2, rooster.w * rooster.h // 60)   # tweeletterwoorden zijn noodvulling
        for _ in range(max_stappen):
            n_twee = sum(1 for _, _, _, wd in rooster.woorden.values() if len(wd.cellen) == 2)
            beste = []
            for s in self.slots(rooster):
                score, sx, sy, d, L, patroon, nieuw, voor, na = s
                if beste and score + 2.5 < beste[-1][0]:
                    break  # verder omlaag wint toch niets meer
                if L == 2 and n_twee >= max_twee:
                    continue
                ids = self.wb.kandidaten(patroon, rooster.gebruikt)
                if not ids:
                    continue
                dood = self.dode_cellen(rooster, sx, sy, d, L, voor, na)
                beste.append((score - self.g["dood"] * dood, sx, sy, d, L, ids))
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
    def doelwit(self, rooster):
        """Kies woorden om te verwijderen: rond een lege cel of een enkel gekruiste letter."""
        w, h = rooster.w, rooster.h
        rng = self.rng
        leeg = [i for i, t in enumerate(rooster.type) if t == LEEG]
        enkel = [i for i, t in enumerate(rooster.type)
                 if t == LETTER and (rooster.in_woord[R][i] is None or rooster.in_woord[D][i] is None)]
        if leeg and (not enkel or rng.random() < 0.5):
            middel = rng.choice(leeg)
        elif enkel:
            middel = rng.choice(enkel)
        else:
            return rng.sample(list(rooster.woorden), min(2, len(rooster.woorden)))
        x, y = middel % w, middel // w
        straal = rng.choice((1, 1, 2))
        buurt = set()
        for dy in range(-straal, straal + 1):
            for dx in range(-straal, straal + 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h:
                    j = ny * w + nx
                    for d in (R, D):
                        if rooster.in_woord[d][j] is not None:
                            buurt.add(rooster.in_woord[d][j])
                        if rooster.oms[d][j] is not None:
                            buurt.add(rooster.oms[d][j])
        buurt = list(buurt)
        k = min(len(buurt), rng.choice((1, 2, 2, 3)))
        return rng.sample(buurt, k) if buurt else []

    def verbeter(self, rooster, iteraties, deadline, stil=500):
        """Ruin and recreate: verwijder enkele woorden rond een zwakke plek en groei opnieuw."""
        huidig = rooster
        beste = huidig.copy()
        zonder_winst = 0
        for _ in range(iteraties):
            if time.time() > deadline:
                break
            kand = huidig.copy()
            for wid in self.doelwit(kand):
                if wid in kand.woorden:
                    kand.verwijder(wid)
            self.groei(kand)
            if kand.waarde() >= huidig.waarde():
                huidig = kand
            if huidig.waarde() > beste.waarde():
                beste = huidig.copy()
                zonder_winst = 0
            else:
                zonder_winst += 1
                if zonder_winst >= stil:
                    break
        return beste

    def maak(self, tijd_limiet, iteraties, herstarts=6):
        """Groei + verbeter, met herstarts; het beste rooster binnen de tijd wint."""
        deadline = time.time() + tijd_limiet
        beste = None
        for _ in range(herstarts):
            rooster = Rooster(self.w, self.h, self.max_len)
            self.anker(rooster)
            self.groei(rooster)
            rooster = self.verbeter(rooster, iteraties, deadline)
            if beste is None or rooster.waarde() > beste.waarde():
                beste = rooster
            if beste.dichtheid() >= self.doel or time.time() > deadline:
                break
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
        txt = "\n".join(wrap_omschrijving(rng.choice(woord.oms)))
        if txt.startswith("Ij"):  # IJ is één letter, dus ook als hoofdletter
            txt = "IJ" + txt[2:]
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


def genereer(sterren=4, seed=1, w=None, h=None, tijd=30.0, iteraties=3000, wb=None, data_dir=None,
             gewichten=None, herstarts=6):
    """Maak één puzzel; geeft (puzzel-dict, rooster, seconden)."""
    conf = STERREN[sterren]
    w = w or conf["w"]
    h = h or conf["h"]
    wb = wb or Woordenboek(conf["max_rang"], conf["max_len"], data_dir)
    rng = random.Random(seed)
    t0 = time.time()
    gen = Generator(wb, w, h, conf["max_len"], rng, conf["dichtheid"], gewichten)
    rooster = gen.maak(tijd, iteraties, herstarts)
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
    ap.add_argument("--iteraties", type=int, default=3000, help="verbeterstappen per herstart (standaard 3000)")
    ap.add_argument("--herstarts", type=int, default=6, help="aantal herstarts per puzzel (standaard 6)")
    args = ap.parse_args(argv)

    conf = STERREN[args.sterren]
    wb = Woordenboek(conf["max_rang"], conf["max_len"])
    os.makedirs(args.uit, exist_ok=True)
    for k in range(args.aantal):
        seed = args.seed + k
        puzzel, rooster, sec = genereer(args.sterren, seed, args.breedte, args.hoogte, args.tijd, args.iteraties, wb,
                                        herstarts=args.herstarts)
        pad = os.path.join(args.uit, f"zweeds-{args.sterren}ster-{seed:04d}.json")
        schrijf_json(puzzel, pad)
        n = rooster.w * rooster.h
        print(f"{pad}: {rooster.w}x{rooster.h}, {rooster.n_letters}/{n} letters "
              f"({100 * rooster.n_letters / n:.0f}%), {rooster.n_dubbel} dubbel gekruist, "
              f"{len(rooster.woorden)} woorden, {sec:.1f} s")


if __name__ == "__main__":
    main()
