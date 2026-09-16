# Bronnen van de woordenlijsten

De bestanden in deze map zijn afgeleid van open datasets. Ze vallen onder
**CC BY-SA 3.0** (de omschrijvingen komen uit Wiktionary via de dataset
hieronder); dat staat los van de AGPL-licentie van de code in deze repo.

| Bestand | Inhoud | Afgeleid van | Licentie |
|---|---|---|---|
| `woorden.tsv` | ~40k woorden (2-12 cellen) met frequentierang en één korte omschrijving | NederlandseWoordenboek + OpenTaal + wordfreq | CC BY-SA 3.0 |
| `vulwoorden.tsv` | ~130 korte vulwoorden (2-5 letters) met handgeschreven omschrijvingen | eigen werk (dit project) | CC BY-SA 3.0 |
| `raw/` (niet in git) | onbewerkte downloads | zie hieronder | zie hieronder |

## Gebruikte bronnen

- **AriSaadon/NederlandseWoordenboek** — https://github.com/AriSaadon/NederlandseWoordenboek
  OpenTaal-woorden met betekenissen uit de Nederlandse Wiktionary
  (dump `nlwiktionary-20211001`). Licentie: CC BY-SA 3.0
  (https://creativecommons.org/licenses/by-sa/3.0/). De omschrijvingen in
  `woorden.tsv` zijn automatisch ingekorte Wiktionary-definities; de
  Wiktionary-auteurs zijn de oorspronkelijke makers.
- **OpenTaal woordenlijst** — https://github.com/OpenTaal/opentaal-wordlist
  bestand `elements/basiswoorden-gekeurd.txt`, gebruikt als filter
  (alleen door OpenTaal gekeurde woorden). Licentie: BSD (revised) en/of
  CC BY 3.0; zie `raw/opentaal-LICENSE.txt` na het draaien van
  `prepare_data.py`. Bronvermelding: "OpenTaal, https://opentaal.org".
- **wordfreq** (Robyn Speer) — https://github.com/rspeer/wordfreq
  Python-pakket, gebruikt om de frequentierang (`rang`) te bepalen via
  `zipf_frequency(woord, "nl")`. Code MIT; de frequentiedata is
  CC BY-SA 4.0 en bevat o.a. SUBTLEX-NL, OpenSubtitles en Wikipedia.
  Alleen de rangorde (een getal per woord) is overgenomen.

## Opnieuw genereren

```
python3 -m venv generator/.venv
generator/.venv/bin/pip install wordfreq
generator/.venv/bin/python generator/prepare_data.py
```

`prepare_data.py` downloadt de ruwe bestanden naar `raw/` (staat in
`.gitignore`) en schrijft `woorden.tsv`. `vulwoorden.tsv` is handwerk.
