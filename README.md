# KORreaderSP

Zweedse puzzels (Nederlandstalig) oplossen op een Kobo e-reader met
[KOReader](https://koreader.rocks).

- `zweedsepuzzel.koplugin/` KOReader-plugin (Lua): puzzels tonen en oplossen.
- `generator/` Python-generator die puzzels en packs maakt (met instelbare moeilijkheid).
- `puzzles/` voorbeeldpuzzels.
- `PLAN.md` het plan en de onderzoeksresultaten.

Installatie op de Kobo: kopieer `zweedsepuzzel.koplugin/` naar
`.adds/koreader/plugins/` en herstart KOReader.

Licentie: AGPL-3.0.

## Ontwikkelen

- Emulator: `tools/emulator.sh` start KOReader als Kobo Forma met de plugin geladen
  (eenmalig KOReader bouwen, zie `PLAN.md` §7).
- Lua-controle: `luacheck zweedsepuzzel.koplugin`.
- Modeltests: `tools/test.sh` (draait `tools/test_puzzle.lua` met de luajit uit de emulatorbuild).
- Puzzels controleren: `python3 generator/validate.py puzzles/*.json`.
- Naar de Kobo (USB): `tools/deploy-kobo.sh`.
- Emulator met gesimuleerde invoer: zet `ZP_AUTOOPEN=<puzzel.json>` (of `library`) en
  `ZP_SCRIPT="cell:1,1;key:R;button:check;shot:/pad.png"` als omgevingsvariabelen.
