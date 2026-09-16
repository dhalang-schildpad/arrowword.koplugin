#!/usr/bin/env python3
"""Eenmalige datavoorbereiding: bouwt generator/data/woorden.tsv.

Bronnen (worden gedownload naar generator/data/raw/, zie data/BRONNEN.md):
- AriSaadon/NederlandseWoordenboek (CC BY-SA 3.0): OpenTaal-woorden met
  Wiktionary-betekenissen, formaat "woord>betekenis1>betekenis2>...".
- OpenTaal basiswoorden-gekeurd (BSD / CC BY 3.0): gekeurde woordenlijst.

Vereist het pip-pakket `wordfreq` (voor de frequentierang):
    python3 -m venv generator/.venv && generator/.venv/bin/pip install wordfreq
    generator/.venv/bin/python generator/prepare_data.py

De generator zelf (generate.py) gebruikt alleen de standaardbibliotheek.
"""
import argparse
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from woorden import DATA_DIR, split_letters, stam_in_omschrijving, wrap_omschrijving  # noqa: E402

RAW_DIR = os.path.join(DATA_DIR, "raw")
BRONNEN = {
    "NederlandseWoordenboek-Woordenlijst.txt":
        "https://raw.githubusercontent.com/AriSaadon/NederlandseWoordenboek/main/Woordenlijst.txt",
    "NederlandseWoordenboek-README.md":
        "https://raw.githubusercontent.com/AriSaadon/NederlandseWoordenboek/main/README.md",
    "opentaal-basiswoorden-gekeurd.txt":
        "https://raw.githubusercontent.com/OpenTaal/opentaal-wordlist/master/elements/basiswoorden-gekeurd.txt",
    "opentaal-LICENSE.txt":
        "https://raw.githubusercontent.com/OpenTaal/opentaal-wordlist/master/LICENSE.txt",
}

MIN_CELLEN, MAX_CELLEN = 2, 12
MAX_WOORDEN = 40000

LIDWOORDEN = ("een ", "de ", "het ", "'n ", "'t ", "n ")
# Betekenissen die een verbuiging/vervoeging beschrijven: overslaan.
VERBUIGING = re.compile(
    r"persoon|tegenwoordige tijd|verleden tijd|voltooid deelwoord|meervoud van|"
    r"verkleinwoord|vergrotende trap|overtreffende trap|gebiedende wijs|"
    r"aanvoegende wijs|verbogen vorm|vervoeging|onvoltooid|enkelvoud|"
    r"^zie\b|^variant van|^afkorting|^alternatieve spelling|^oude spelling|"
    r"^verouderde? (spelling|vorm)|^spelfout|^foutieve spelling|^samentrekking",
    re.IGNORECASE)
# Grammaticale meta-beschrijvingen die geen omschrijving opleveren: overslaan.
META = re.compile(
    r"^(wordt |word |gebruikt|geeft |verwijst|voorafgaand|duidt|ter aankondiging|"
    r"als aanduiding|aanduiding|zelfstandig gebruikt|ook voor|komt regelmatig|"
    r"(het )?symbool|afkorting|letter van|naam van de letter|in samenstellingen|"
    r"vervangt|eerste deel|achtervoegsel|voorvoegsel|bijvoeglijk|zelfstandig naamwoord|"
    r"werkwoord|drukt |uitdrukking|benaming voor|term voor|woord dat|woord om|"
    r"aanspreekvorm|stopwoord|deel van een)",
    re.IGNORECASE)
# Punten waarop een te lange betekenis mag worden ingekort (na het woord vóór de spatie).
KNIPPUNTEN = [" die ", " dat ", " waar", " welke ", " wie ", " om ", " met ", " van ",
              " voor ", " uit ", " in ", " op ", " bij ", " aan ", " door ", " naar ",
              " tot ", " zoals ", " als ", " en ", " of ", " maar ", " tegen ", " over ",
              " onder ", " tussen ", " zonder ", " tijdens ", " volgens ", " per "]
# Een ingekorte omschrijving mag niet eindigen op deze woorden.
SLECHT_EIND = {"een", "de", "het", "zeer", "erg", "niet", "heel", "meer", "minder", "zich",
               "te", "en", "of", "is", "zijn", "wordt", "worden", "iets", "iemand", "die", "dat",
               "al", "nog", "ook", "zo", "van", "met", "om", "aan", "op", "in", "uit", "bij",
               "men", "waar", "hoe", "wat", "wie", "voor", "door", "naar", "tot", "over", "onder",
               "tussen", "tegen", "als", "zoals", "per", "zonder", "welke", "geen", "elke", "elk",
               "alle", "andere", "ander", "bepaalde", "bepaald", "zeker", "zekere", "hun", "haar",
               "zijn", "mijn", "je", "jouw", "uw", "ons", "onze", "dit", "deze", "dan", "dus"}
TOEGESTANE_TEKENS = re.compile(r"^[a-zA-ZÀ-ſ' \-]+$")


def download(naam, url):
    pad = os.path.join(RAW_DIR, naam)
    if not os.path.exists(pad):
        print(f"download {url}")
        urllib.request.urlretrieve(url, pad)
    return pad


def schoon_betekenis(bet):
    """Maak één Wiktionary-betekenis schoon; None als onbruikbaar."""
    if "'''" in bet or "|" in bet or "~" in bet or "{" in bet or "=" in bet:
        return None
    bet = bet.replace("''", "")
    bet = re.sub(r"<[^>]*>", "", bet)
    for _ in range(3):
        bet = re.sub(r"\([^()]*\)", "", bet)
    bet = re.sub(r"\[[^\]]*\]", "", bet)
    bet = re.sub(r"\s+", " ", bet).strip(" -:")
    if not bet or VERBUIGING.search(bet) or META.match(bet):
        return None
    # tot het eerste leesteken
    bet = re.split(r"[,;.:!?]", bet, maxsplit=1)[0].strip()
    lower = bet.lower()
    for lid in LIDWOORDEN:
        if lower.startswith(lid):
            bet = bet[len(lid):]
            break
    bet = bet.strip(" -")
    if len(bet) < 3 or not TOEGESTANE_TEKENS.match(bet):
        return None
    return bet


def kort_in(bet):
    """Geef kandidaat-omschrijvingen: de hele betekenis en steeds kortere prefixen."""
    yield bet
    low = " " + bet.lower()
    posities = sorted({low.find(k) - 1 for k in KNIPPUNTEN if low.find(k) > 0}, reverse=True)
    for p in posities:
        prefix = bet[:p].strip()
        delen = prefix.split()
        if not delen or delen[-1].lower() in SLECHT_EIND:
            continue
        # een los overgebleven woord is vaak een bijvoeglijk naamwoord ("grote"): overslaan
        if len(delen) == 1 and (len(delen[0]) < 5 or delen[0].endswith("e")):
            continue
        yield prefix


def kies_omschrijving(woord, betekenissen):
    for bet in betekenissen:
        schoon = schoon_betekenis(bet)
        if not schoon:
            continue
        for kandidaat in kort_in(schoon):
            if len(kandidaat) < 3:
                continue
            if stam_in_omschrijving(woord.upper(), kandidaat):
                continue
            if wrap_omschrijving(kandidaat) is None:
                continue
            return kandidaat[0].upper() + kandidaat[1:]
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--max", type=int, default=MAX_WOORDEN, help="maximaal aantal woorden (standaard 40000)")
    args = ap.parse_args()

    os.makedirs(RAW_DIR, exist_ok=True)
    paden = {naam: download(naam, url) for naam, url in BRONNEN.items()}

    try:
        from wordfreq import zipf_frequency
    except ImportError:
        sys.exit("wordfreq ontbreekt: generator/.venv/bin/pip install wordfreq")

    with open(paden["opentaal-basiswoorden-gekeurd.txt"], encoding="utf-8") as f:
        opentaal = {r.strip() for r in f if r.strip()}

    tellingen = {"regels": 0, "hoofdletter": 0, "tekens": 0, "lengte": 0, "niet_opentaal": 0,
                 "geen_omschrijving": 0, "bruikbaar": 0, "zonder_frequentie": 0}
    kandidaten = []
    with open(paden["NederlandseWoordenboek-Woordenlijst.txt"], encoding="utf-8") as f:
        for regel in f:
            regel = regel.rstrip("\n")
            if ">" not in regel:
                continue
            tellingen["regels"] += 1
            woord, *betekenissen = regel.split(">")
            woord = woord.strip()
            if woord != woord.lower():
                tellingen["hoofdletter"] += 1
                continue
            if not re.fullmatch(r"[a-z]+", woord):
                tellingen["tekens"] += 1
                continue
            cellen = split_letters(woord.upper())
            if not MIN_CELLEN <= len(cellen) <= MAX_CELLEN:
                tellingen["lengte"] += 1
                continue
            if woord not in opentaal:
                tellingen["niet_opentaal"] += 1
                continue
            oms = kies_omschrijving(woord, betekenissen)
            if not oms:
                tellingen["geen_omschrijving"] += 1
                continue
            zipf = zipf_frequency(woord, "nl")
            if zipf == 0:
                tellingen["zonder_frequentie"] += 1
            tellingen["bruikbaar"] += 1
            kandidaten.append((-zipf, len(cellen), woord, oms))

    kandidaten.sort()
    kandidaten = kandidaten[:args.max]
    uit = os.path.join(DATA_DIR, "woorden.tsv")
    per_lengte = {}
    with open(uit, "w", encoding="utf-8") as f:
        f.write("woord\tlengte\trang\tomschrijving\tbron\n")
        for rang, (_, lengte, woord, oms) in enumerate(kandidaten, 1):
            f.write(f"{woord.upper()}\t{lengte}\t{rang}\t{oms}\twiktionary\n")
            per_lengte[lengte] = per_lengte.get(lengte, 0) + 1

    print(f"regels in dataset:        {tellingen['regels']}")
    print(f"  overgeslagen hoofdletter: {tellingen['hoofdletter']}")
    print(f"  overgeslagen tekens:      {tellingen['tekens']}")
    print(f"  overgeslagen lengte:      {tellingen['lengte']}")
    print(f"  niet in OpenTaal gekeurd: {tellingen['niet_opentaal']}")
    print(f"  geen bruikbare omschr.:   {tellingen['geen_omschrijving']}")
    print(f"bruikbaar:                {tellingen['bruikbaar']} (zonder wordfreq-frequentie: {tellingen['zonder_frequentie']})")
    print(f"geschreven naar {uit}: {len(kandidaten)} woorden ({os.path.getsize(uit) // 1024} kB)")
    print("per lengte: " + ", ".join(f"{k}:{per_lengte[k]}" for k in sorted(per_lengte)))


if __name__ == "__main__":
    main()
