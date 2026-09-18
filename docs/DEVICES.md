# Devices

## Tested

| Device | Screen | KOReader | Result |
|---|---|---|---|
| Kobo Forma | 8", 1440 x 1920, 300 ppi | v2026.03 (Kobo firmware 4.38) | Works. 13 x 14 grids are comfortable to read, touch targets are fine, no full-screen flashes while typing. |

That is the whole list. Everything below is expectation, not experience. If
you run the plugin on another device, please open an issue with the model, the
KOReader version, the grid size you used and a photo. That turns a guess into
a row in this table.

## Why resolution and screen size matter

In an arrowword the clues live inside the grid cells, so a cell has to hold two
lines of roughly nine characters. Whether that is legible depends on the
*physical* size of a cell, which follows from three things:

1. **The working area.** The plugin reserves a title bar, a clue bar and a
   three-row letter bar. On the Forma that leaves about 75% of the height and
   98% of the width for the grid. That area is nearly square, which is why our
   grids are nearly square too (13 x 14 rather than the tall 13 x 18 of a
   printed booklet).
2. **The grid size.** Cell size is the smaller of `area width / columns` and
   `area height / rows`.
3. **Pixel density.** `cell size in mm = pixels / ppi x 25.4`.

What we learned on the Forma:

| Grid | Cell on the Forma | Verdict |
|---|---|---|
| 13 x 18 | 83 px, 7.0 mm | clue text just too small |
| 13 x 14 | 103 px, 8.7 mm | good |

Rule of thumb until more people report back: **8.5 mm or more is comfortable,
7.5 to 8.5 mm is acceptable, under 7 mm is too small.** For comparison, a
printed Denksport puzzle has cells of roughly 9 mm.

## Devices we expect to work

The plugin only uses standard KOReader widgets, drawing and touch input, so it
should run on any **touch-screen** device KOReader supports: Kobo, Kindle
(jailbroken), PocketBook, reMarkable, Android. Devices without a touch screen
are not supported; every interaction is a tap or a swipe.

Estimated cell sizes, computed from the layout rules above, **not measured**:

| Screen (examples) | 13 x 14 (4 stars) | 11 x 12 (2 stars) | Advice |
|---|---|---|---|
| 8", 1440 x 1920, 300 ppi (Kobo Forma, Sage) | 103 px, 8.7 mm | 120 px, 10.2 mm | any size |
| 7.8", 1404 x 1872, 300 ppi (Kobo Aura One, PocketBook InkPad 4) | 100 px, 8.5 mm | 117 px, 9.9 mm | any size |
| 10.3", 1404 x 1872, 227 ppi (Kobo Elipsa) | 100 px, 11.2 mm | 117 px, 13.1 mm | any size; 14 x 15 should be fine |
| 7", 1264 x 1680, 300 ppi (Kobo Libra, PocketBook Era) | 90 px, 7.6 mm | 105 px, 8.9 mm | 13 x 14 acceptable, 12 x 13 or smaller is nicer |
| 6.8", 1236 x 1648, 300 ppi (Kindle Paperwhite 5) | 88 px, 7.5 mm | 103 px, 8.7 mm | prefer 12 x 13 or smaller |
| 6", 1072 x 1448, 300 ppi (Kobo Clara, Kindle 2022) | 77 px, 6.5 mm | 90 px, 7.7 mm | use 11 x 12 or 10 x 11 |
| 6", 758 x 1024, 212 ppi (Kobo Nia, older 6" devices) | 55 px, 6.6 mm | 64 px, 7.7 mm | 10 x 11 at most; the low density also makes small text rough |

Two consequences for the project:

- **Packs should say which screens they suit.** Today a pack's grid size is
  tied to its difficulty. The roadmap has an item to separate the two, so a
  six-inch reader can get four-star vocabulary in a 10 x 11 grid.
- **Generate your own size.** The generator in [arrowword-puzzles](https://github.com/dhalang-schildpad/arrowword-puzzles) accepts `--width` and `--height`:

  ```bash
  python3 generator/generate.py --lang nl --stars 4 --width 10 --height 11 --count 20 --seed 1 --out out/
  ```

## Notes for Kobo owners

- Install KOReader with the usual one-click package; the plugin goes in `.adds/koreader/plugins/`.
- Plugins are loaded at start-up. After copying a new version, restart KOReader.
- If something goes wrong, KOReader writes a traceback to `.adds/koreader/crash.log`. Please attach it to your issue.
- Wi-Fi is not needed. Puzzles are plain files copied over USB.
