# Puzzelformaat (JSON)

Eén bestand per puzzel, UTF-8, extensie `.json`. Coördinaten zijn `[x, y]`,
0-gebaseerd, `x` naar rechts en `y` omlaag. `cellen[y][x]` is de cel op `(x, y)`.

```json
{
  "versie": 1,
  "titel": "Test klein",
  "sterren": 1,
  "w": 6, "h": 5,
  "cellen": [
    [ {"t":"X"}, {"t":"O","oms":[{"txt":"Venster","dir":"D"}]}, ... ],
    ...
  ],
  "woorden": [
    {"id":1, "antwoord":"REEDS", "oms":"Al", "dir":"R", "van":[0,1], "start":[1,1]}
  ],
  "oplossing": {"woord":"ALS", "cellen":[[2,3],[3,2],[3,3]]}
}
```

## Cellen

| `t` | Betekenis | Extra velden |
|---|---|---|
| `L` | lettercel | `s`: de letter in de oplossing (hoofdletter; `IJ` is één letter in één cel). Optioneel `n`: nummer voor het oplossingswoord. |
| `O` | omschrijvingscel | `oms`: lijst van 1 of 2 `{txt, dir}`. Bij 2 omschrijvingen wordt de cel gesplitst: eerste boven, tweede onder. |
| `X` | lege cel (geen omschrijving) | geen |

`dir` is de pijlrichting vanuit de omschrijvingscel:

| `dir` | Antwoord begint | Loopt |
|---|---|---|
| `R` | direct rechts van de omschrijvingscel | naar rechts |
| `D` | direct onder de omschrijvingscel | omlaag |
| `RD` | direct rechts van de omschrijvingscel | omlaag (geknikte pijl) |
| `DR` | direct onder de omschrijvingscel | naar rechts (geknikte pijl) |

Geknikte pijlen (`RD`, `DR`) zijn gereserveerd; de plugin ondersteunt eerst alleen `R` en `D`.

## Woorden

Elk woord verwijst naar precies één omschrijving: `van` is de
omschrijvingscel, `start` de eerste lettercel, `dir` gelijk aan de `dir` van
de omschrijving. `antwoord` moet letter voor letter overeenkomen met de
lettercellen vanaf `start`. De cel na de laatste letter is een `O`, `X` of de
rand.

## Oplossingswoord

`oplossing.cellen[i]` is de lettercel met nummer `i+1`; de letters vormen
samen `oplossing.woord`. Optioneel; ontbreekt bij kleine testpuzzels.

## Regels (validator)

Fouten:
- afmetingen kloppen met `cellen`;
- elk woord komt overeen met de cellen, begint naast zijn omschrijvingscel en
  eindigt tegen een niet-lettercel of de rand;
- elke omschrijving in een `O`-cel heeft precies één woord en omgekeerd;
- elke reeks van 2 of meer aaneengesloten lettercellen (horizontaal of
  verticaal) is precies één woord; losse lettercellen buiten een woord bestaan niet;
- oplossingswoord klopt met de cellen.

Waarschuwingen (kwaliteit, niet fataal):
- lettercellen die maar in één woord zitten (percentage);
- `X`-cellen (percentage);
- omschrijvingen langer dan 2 regels van 12 tekens;
- omschrijving bevat de stam van het antwoord.
