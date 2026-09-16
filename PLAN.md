# Plan: Zweedse puzzels op de Kobo Forma (KOReader-plugin)

Doel: een KOReader-plugin waarmee je op een Kobo Forma Zweedse puzzels
(Nederlandstalig) interactief kunt oplossen, plus een manier om steeds
nieuwe puzzels te krijgen.

Status: plan, nog niets gebouwd. Datum: 2026-09-16.

Besluiten (2026-09-16):
- Puzzels in het Nederlands, Denksport-achtige standaardmaat, moeilijkheid 4 van 5 sterren.
- Geen betaalde LLM-batch voor omschrijvingen; zie §4.
- Overzetten via USB als basis, Wi-Fi (WebDAV/FTP/SSH in KOReader) als extra.
- Licentie: AGPL-3.0.
- Moeilijkheid is een instelbare parameter van de generator (§5).
- Puzzels worden als **packs** uitgebracht (GitHub Releases), zodat ze later openbaar kunnen (§5a).

## 1. Kernbeslissing: genereren op de Mac, oplossen op het apparaat

**Advies: puzzels offline genereren (Python op de Mac) en als bestanden op
de Kobo zetten. De plugin doet alleen weergeven en oplossen.**

Waarom:

- Genereren is een zoekprobleem (NP-compleet). Een dichte 13x18 Zweedse
  puzzel vraagt duizenden tot honderdduizenden zoekstappen plus herhaalde
  pogingen met een ander rooster als het vastloopt. Op de Forma
  (1 GHz single-core Cortex-A9, 512 MB) blokkeert dat de UI en kan het bij
  pech minuten duren. Op de Mac zijn het seconden.
- Kwaliteitscontrole hoort offline: dubbele antwoorden weghalen, obscure
  woorden weigeren, controleren dat elke letter gekruist wordt, het
  oplossingswoord kiezen. Dat wil je kunnen bekijken voordat de puzzel
  naar het apparaat gaat.
- De woordenlijst met omschrijvingen (tientallen MB) hoeft dan niet op
  het apparaat.
- Er bestaat geen enkele Lua-generator; de plugin blijft klein (renderen,
  invoer, opslaan van voortgang).

Later kan een "oneindig"-modus met generatie op het apparaat alsnog, het
algoritme is porteerbaar naar LuaJIT. Nu niet.

## 2. Architectuur

```
KORreaderSP/
  generator/                Python: woordenlijst -> rooster -> vulling -> puzzelbestand
    data/                   woordenlijst + omschrijvingen (gegenereerd, zie §4)
    layout.py               plaatsen van omschrijvingscellen
    fill.py                 backtracking-vuller met (lengte, positie, letter)-index
    validate.py             kwaliteitsregels
    export.py               eigen JSON + ipuz-export
  zweedsepuzzel.koplugin/   Lua: KOReader-plugin
    _meta.lua
    main.lua                menu-registratie, puzzelbibliotheek
    puzzle.lua              JSON inlezen, model
    gridwidget.lua          rooster tekenen (direct op Blitbuffer)
    keyboard.lua            letterbalk
    progress.lua            voortgang opslaan
  puzzles/                  voorbeeldpuzzels (JSON)
  PLAN.md
```

Puzzels komen op de Kobo via USB of de Wi-Fi-bestandsoverdracht van
KOReader, in een map zoals `.adds/koreader/puzzles/`.

## 3. Puzzelformaat

Intern een eigen JSON dat expliciet is over pijlen. Export naar **ipuz**
(soort `http://ipuz.org/crossword/arrowword#1`), het enige open formaat
dat Zweedse puzzels ondersteunt. `.puz` kan het niet.

```json
{
  "w": 13, "h": 18, "titel": "Zweeds 2026-09-16 #1", "sterren": 3,
  "cellen": [[{"t":"L","s":"E"}, {"t":"O","oms":[{"txt":"Hoofdstad","dir":"R"},{"txt":"Sier","dir":"D"}]}]],
  "woorden": [{"id":1,"oms":"Hoofdstad","antwoord":"EDAM","start":[1,0],"dir":"R","van":[0,0]}],
  "oplossing": {"cellen":[[3,4],[7,2]], "woord":"KOBO"}
}
```

- `t`: `L` = lettercel, `O` = omschrijvingscel (1 of 2 omschrijvingen).
- `dir`: `R` (rechts), `D` (omlaag), later ook geknikte pijlen `RD`/`DR`.
- **IJ telt als één letter en één cel.** Dat moet in de woordenlijst, de
  vuller en de letterbalk consequent zo zijn.

## 4. Woorden en omschrijvingen

Er is **geen legaal herbruikbare Nederlandse omschrijvingendatabase**.
Puzzelwoordenboek-sites (mijnwoordenboek, woorden.org, Van Dale) verbieden
hergebruik en scrapen; het databankenrecht beschermt ze extra.
Omschrijvingen moeten we dus zelf maken.

Pijplijn (zonder extra kosten):

1. **Woorden**: OpenTaal `basiswoorden-gekeurd` (~200k, BSD/CC-BY)
   gefilterd op frequentie met SUBTLEX-NL of `wordfreq` naar ~10-15k
   gangbare woorden van 2-12 letters. Zelfstandige naamwoorden,
   bijvoeglijke naamwoorden, werkwoorden; meervouden toegestaan, andere
   verbuigingen niet.
2. **Korte vulwoorden**: aparte handgemaakte lijst van ~500 woorden van
   2-3 letters (ara, eer, els, ei, os, ra, ...) met meerdere omschrijvingen
   elk, plus gangbare afkortingen (enz., r.-k., a.s.). Die dragen het rooster.
3. **Omschrijvingen, drie gratis bronnen gecombineerd**:
   a. Claude schrijft ze in de ontwikkelsessies zelf, in batches naar
      `generator/data/omschrijvingen.tsv` (2-3 per woord, synoniem of
      korte definitie, max ~12 tekens per regel, max 2 regels). Eerst de
      vulwoorden en de meest frequente woorden.
   b. Open Dutch WordNet (CC BY-SA 4.0): synoniemgroepen als
      synoniem-omschrijvingen.
   c. AriSaadon/NederlandseWoordenboek (OpenTaal + Wiktionary, CC BY-SA
      3.0): definities automatisch ingekort tot het deel voor de eerste
      komma. Grof, maar meteen bruikbaar om de generator te testen.
   Optie voor later: lokaal model via Ollama op de Mac.
4. **Validatie**: lengte past in een cel, omschrijving bevat niet de stam
   van het antwoord, meervoud/enkelvoud klopt, afkorting bij afkorting.
5. Omdat b en c CC BY-SA zijn, is de omschrijvingendataset zelf
   CC BY-SA; dat staat los van de licentie van de code.

## 5. Generator (Python)

Hybride "vullen en dan omschrijvingscellen plaatsen", zoals de
open-source Zweedse generator eoq746/SwedishCrossword doet:

1. Kies roostermaat en doel-dichtheid (65-70% lettercellen, dus ~30%
   omschrijvingscellen; makkelijk = kleiner rooster, kortere woorden).
2. Plaats ankerwoorden, groei incrementeel met woorden die kruisen.
   Voor elk woord wordt de cel ervoor (links of erboven) een
   omschrijvingscel; een cel mag twee omschrijvingen dragen.
3. Vul gaten met backtracking: index per (lengte, positie, letter),
   kies eerst de slot met de minste kandidaten (MRV).
4. Bij vastlopen: verplaats een omschrijvingscel en probeer opnieuw met
   een nieuwe seed.
5. Kies oplossingswoord: genummerde cellen die samen een woord vormen.
6. Valideer, exporteer JSON + ipuz.

Referenties: Ginsberg 1990 (arc consistency, backjumping),
paulgb/crossword-composer (MIT, Rust, herbruikbare indexeringsaanpak).

**Instelbare moeilijkheid (1-5 sterren).** De generator krijgt een
sterrenparameter die tegelijk stuurt:

| Sterren | Rooster | Woordfrequentie | Dichtheid lettercellen | Omschrijvingen |
|---|---|---|---|---|
| 1-2 | 11x13 | alleen top-5k woorden | ~55% | letterlijk synoniem |
| 3 | 13x15 | top-15k | ~62% | synoniem of definitie |
| 4 | 13x18 | top-30k | ~68% | ook omschrijvende/indirecte |
| 5 | 15x20 | volledige lijst | ~72% | indirect, met "?"-woordspelingen |

Elk woord krijgt daarvoor een frequentierang en elke omschrijving een
moeilijkheidsniveau; de generator kiest per ster uit de passende laag.
Standaard voor dit project: 4 sterren.

### 5a. Puzzelpacks

De generator maakt packs: een map (of zip) met N puzzels van één niveau,
bijvoorbeeld `pack-4ster-2026-10.zip` met 50 puzzels als JSON plus de
ipuz-export. Packs komen als GitHub Release in deze repo; de plugin toont
elke pack als eigen map in de bibliotheek. Zodra de repo openbaar gaat
kunnen anderen de packs downloaden zonder de generator te hoeven draaien.
Een kleine losse app om zelf packs te maken (webpagina of CLI met
sterrenkeuze) is een mogelijke latere stap; de CLI van de generator is
daar de basis voor.

## 6. KOReader-plugin (Lua)

- Eigen code schrijven. Als structuurreferentie roygbyte/crossword.koplugin
  (AGPL-3.0, 2024, alleen ipuz/NYT). omer-faruq/crossword.koplugin heeft
  **geen licentie**, daar geen code van overnemen.
- Rooster direct tekenen op de Blitbuffer (`paintRect` + `RenderText`) in
  een `InputContainer`; sneller dan een widget per cel op deze CPU.
  Omschrijvingscellen krijgen kleinere tekst en een pijltje.
- Invoer: tap op cel selecteert woord (tweede tap wisselt richting),
  letterbalk onderin gebouwd op `VirtualKey` (met IJ als eigen toets),
  swipe voor volgende/vorige woord.
- E-ink: per-cel refresh met `UIManager:setDirty(self, function() return
  "ui", cel_geom end)`; alleen `flashui` bij openen/sluiten. Voorkomt
  flitsen bij elke letter.
- Voortgang per puzzel opslaan in de instellingenmap; knop
  "controleer" (fouten markeren) en "hint" (één letter).
- Bibliotheek: lijst van puzzels in `puzzles/`, met status (nieuw, bezig,
  klaar).
- Installatie op de Kobo: `.adds/koreader/plugins/zweedsepuzzel.koplugin/`.

## 7. Ontwikkelomgeving

- KOReader-emulator op de Mac: `brew install` van de bouwtools, dan
  `./kodev fetch-thirdparty && ./kodev build && ./kodev run -w=1440 -h=1920 -d=300`
  om de Forma na te bootsen. Plugin symlinken in `koreader/plugins/`.
  Geen hot reload: herstarten na wijzigingen.
- Op het apparaat: SSH-server in KOReader (poort 2222, root), bestanden
  overzetten met `cat | ssh`. Logs in `.adds/koreader/crash.log` via
  `logger.dbg`.
- KOReader op de Forma: firmware 4.38 is de 4.x-lijn, dus de standaard
  One-Click-installer (KOReader + KFMon + NickelMenu) werkt. Let op dat
  macOS zip-bestanden automatisch uitpakt; de zip moet intact naar het
  apparaat.

## 8. Fasen

| Fase | Resultaat | Klaar als |
|---|---|---|
| 0 Opzet | Repo-structuur, emulator draait, KOReader op de Forma, "hello"-plugin zichtbaar | plugin verschijnt in het menu op het apparaat |
| 1 Formaat | JSON-schema + 2 handgemaakte testpuzzels | validator accepteert ze |
| 2 Plugin MVP | Rooster tonen, letters invoeren, voortgang opslaan, controleren | een testpuzzel is op de Forma op te lossen |
| 3 Generator MVP | Woordenlijst + vuller + export, met de tijdelijke Wiktionary-omschrijvingen | 10 puzzels van 11x15 die de validator halen |
| 4 Omschrijvingen | LLM-batch, validatie, vulwoordenlijst | generator maakt puzzels die "als Denksport" lezen |
| 5 Afwerking | Oplossingswoord, sterren, bibliotheek, hints, geknikte pijlen | vriendin-test geslaagd |

Fase 2 en 3 kunnen parallel; fase 2 heeft alleen fase 1 nodig.

## 9. Open vragen

1. Licentie van de repo. Advies AGPL-3.0: kost niets, past bij
   KOReader (zelf AGPL), en laat toe om stukken uit roygbyte en Sudoku+
   over te nemen. Verwacht letterlijk hergebruik van roygbyte: 0-5%,
   het dient vooral als voorbeeld van welke KOReader-API's nodig zijn.
   MIT alleen als hergebruik in gesloten software gewenst is.
2. Of de Kobo op Wi-Fi zit blijkt bij de installatie van KOReader.

## 10. Bronnen

- KOReader plugin-loader en hello-plugin: https://github.com/koreader/koreader/tree/master/plugins/hello.koplugin
- KOReader bouwen: https://github.com/koreader/koreader/blob/master/doc/Building.md
- KOReader SSH: https://github.com/koreader/koreader/wiki/SSH
- Installatie op Kobo: https://github.com/koreader/koreader/wiki/Installation-on-Kobo-devices
- roygbyte/crossword.koplugin (AGPL): https://github.com/roygbyte/crossword.koplugin
- Borisvl/sudokuplus.koplugin (per-cel refresh, AGPL): https://github.com/Borisvl/sudokuplus.koplugin
- ipuz-specificatie (arrowword): https://libipuz.org/ipuz-spec.html
- eoq746/SwedishCrossword (algoritmereferentie): https://github.com/eoq746/SwedishCrossword
- paulgb/crossword-composer (MIT): https://github.com/paulgb/crossword-composer/
- Ginsberg 1990: https://cdn.aaai.org/AAAI/1990/AAAI90-032.pdf
- OpenTaal: https://github.com/OpenTaal/opentaal-wordlist
- AriSaadon/NederlandseWoordenboek: https://github.com/AriSaadon/NederlandseWoordenboek
- Open Dutch WordNet: https://github.com/cltl/OpenDutchWordnet
- SUBTLEX-NL: https://link.springer.com/article/10.3758/BRM.42.3.643
- Conventies Zweedse puzzel: https://nl.wikipedia.org/wiki/Zweedse_puzzel
- Puzzel Samen (ipuz/puz in NL): https://puzzelsamen.nl/
