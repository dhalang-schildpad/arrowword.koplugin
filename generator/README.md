# Generator

Python-generator voor Nederlandstalige Zweedse puzzels (fase 3 van `../PLAN.md`).
Uitvoer: JSON-bestanden volgens `../puzzles/FORMAT.md`. De generator zelf gebruikt
alleen de standaardbibliotheek (Python 3.10+).

## Gebruik

```
python3 generator/generate.py --sterren 4 --aantal 3 --seed 1 --uit puzzles/generated/
python3 generator/validate.py puzzles/generated/*.json
```

Opties:

| Optie | Betekenis |
|---|---|
| `--sterren 1..5` | moeilijkheid (standaard 4); bepaalt roostermaat, woordfrequentie, maximale woordlengte en streefdichtheid (tabel in PLAN.md §5) |
| `--aantal N` | aantal puzzels; puzzel k krijgt seed `seed + k` |
| `--seed S` | seed van de eerste puzzel (zelfde seed = zelfde puzzel, zolang de tijdslimiet niet ingrijpt) |
| `--uit MAP` | uitvoermap (standaard `puzzles/generated`) |
| `--breedte`, `--hoogte` | roostermaat afwijkend van de sterrentabel |
| `--tijd SEC` | maximale rekentijd per puzzel (standaard 30) |
| `--herstarts N`, `--iteraties N` | zoekbudget: herstarts per puzzel en verbeterstappen per herstart |

Bestandsnaam: `zweeds-<sterren>ster-<seed>.json`, titel `Zweeds 4★ #<seed>`.
Per puzzel wordt de dichtheid (percentage lettercellen), het aantal dubbel
gekruiste letters, het aantal woorden en de rekentijd afgedrukt.

## Werking

1. `Woordenboek` laadt `data/woorden.tsv` (gefilterd op frequentierang per
   sterren) plus `data/vulwoorden.tsv` (handgeschreven korte vulwoorden, altijd
   toegestaan; hun omschrijvingen gaan voor) en bouwt een index per
   (lengte, positie, letter).
2. `Rooster` houdt de toestand bij en garandeert na elke plaatsing een geldige
   puzzel: elk woord krijgt de cel ervoor als omschrijvingscel (max. één R- en
   één D-omschrijving per cel), de cel erna wordt niet-letter, nieuwe letters
   mogen geen letterburen dwars op het woord hebben (behalve bij kruisingen).
3. `Generator.groei` plaatst gretig: alle structureel geldige slots krijgen een
   score (nieuwe letters, kruisingen, hergebruik van blokcellen, straf voor
   cellen die dood komen te liggen en voor tweeletterwoorden); voor de beste
   slots wordt het woordenboek geraadpleegd en een woord gekozen (gewogen naar
   frequentie).
4. `Generator.verbeter` ("ruin and recreate"): verwijder enkele woorden rond een
   lege cel of een enkel gekruiste letter en groei opnieuw; behoud als de
   waarde (letters + dubbel gekruiste letters) niet daalt. Meerdere herstarts;
   het beste rooster wint.
5. `exporteer` kiest omschrijvingen (afgebroken op spaties in max. 2 regels van
   12 tekens, regelscheiding `\n`), nummert een oplossingswoord van 4-8 letters
   en schrijft de JSON.

## Data

Zie `data/BRONNEN.md` voor bronnen en licenties (CC BY-SA 3.0). De woordenlijst
wordt eenmalig gebouwd met `prepare_data.py`; dat script gebruikt het
pip-pakket `wordfreq`:

```
python3 -m venv generator/.venv
generator/.venv/bin/pip install wordfreq
generator/.venv/bin/python generator/prepare_data.py
```

## Tests

```
python3 -m unittest discover -s generator/tests
```

## Bekende beperkingen (fase 3)

- Omschrijvingen zijn automatisch ingekorte Wiktionary-definities: grof en soms
  vreemd. Fase 4 vervangt ze.
- Ongeveer de helft van de letters is maar één keer gekruist en 10-16% van de
  cellen blijft leeg (`X`); een echte Zweedse puzzel is bijna volledig gekruist.
  Dat vraagt een grotere lijst korte vulwoorden (fase 4) en een vuller op een
  vast blokpatroon.
- Woorden van 3 letters zijn oververtegenwoordigd.
