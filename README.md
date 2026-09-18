# arrowword.koplugin

**Arrowword puzzles (Swedish-style crosswords) for e-readers running [KOReader](https://koreader.rocks).**
Known as *Zweedse puzzels* in Dutch, *Schwedenrätsel* in German and *mots fléchés* in French.

An arrowword is a crossword where the clues are written inside the grid, with
an arrow pointing at the answer. They suit an e-ink screen well: one page, no
scrolling, no time pressure.

<p align="center">
  <img src="docs/img/screenshot-nl-4star.png" alt="A four-star Dutch puzzle in the plugin (emulator screenshot)" width="420">
</p>

<!-- Photo of the puzzle on a Kobo Forma: save it as docs/img/photo-kobo-forma.jpg and
     uncomment the block below.
<p align="center">
  <img src="docs/img/photo-kobo-forma.jpg" alt="The same puzzle on a Kobo Forma" width="420">
</p>
-->

This repository is the plugin. The puzzles, the generator that makes them and
the clue database live in
**[arrowword-puzzles](https://github.com/dhalang-schildpad/arrowword-puzzles)**.

## Features

- Grid with clue cells and arrows, sized to make the cells as large as your screen allows
- Tap a cell or a clue to select a word; tap again to switch between across and down
- The current clue is shown large under the grid
- QWERTY letter bar, with extra keys per puzzle language (`IJ` for Dutch)
- Check marks wrong letters, Hint fills in one letter
- Progress is saved per puzzle; folders show up as packs with a done counter
- No full-screen flashes while typing
- English and Dutch interface, following KOReader's language
- Comes with a small Dutch starter pack; more packs in [arrowword-puzzles](https://github.com/dhalang-schildpad/arrowword-puzzles)

Puzzles are Dutch for now. English is planned; the format and the plugin are language-aware.

## Tested device, and why your screen matters

Everything has been tested on a **Kobo Forma** (8 inch, 1440 x 1920 pixels,
300 ppi, Kobo firmware 4.38, KOReader v2026.03). That is the only device we
can vouch for.

An arrowword puts its clues *inside* the cells, so cell size decides whether
the puzzle is readable. The plugin makes the cells as large as the screen
allows, which means the same puzzle has smaller cells on a smaller screen:

- On the Forma a 13 x 14 grid gives cells of about 103 px, or 8.7 mm. That reads comfortably.
- Our first attempt, 13 x 18, gave 83 px (7 mm) cells on the same screen. The tester's verdict: just too small.

So grids are shaped like the screen's working area, and smaller screens need
smaller grids. [docs/DEVICES.md](docs/DEVICES.md) explains the layout, lists
the devices we expect to work with estimated cell sizes, and says which grid
size to pick. If you try another device, please tell us how it went.

## Install

You need a touch-screen e-reader with KOReader installed.

1. Download this repository (green **Code** button, *Download ZIP*) and unpack it, or clone it.
2. Copy the folder to KOReader's `plugins/` folder and make sure it is called `arrowword.koplugin`
   (on a Kobo: `.adds/koreader/plugins/arrowword.koplugin/`).
3. Restart KOReader. Open the top menu, tap the tools icon and choose **Arrowword puzzles**.

The starter pack works right away. For more puzzles, copy pack folders from
[arrowword-puzzles](https://github.com/dhalang-schildpad/arrowword-puzzles) to
`arrowwords/` in the KOReader folder (on a Kobo: `.adds/koreader/arrowwords/`).

On macOS with a Kobo connected over USB, `tools/deploy-kobo.sh` copies the plugin and, if
`arrowword-puzzles` is checked out next to this repository, the packs too.

## Documentation

- [docs/DEVICES.md](docs/DEVICES.md): tested and expected devices, and why screen size matters
- [docs/PUZZLE_FORMAT.md](docs/PUZZLE_FORMAT.md): the JSON puzzle format
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): how the parts fit and why
- [docs/ROADMAP.md](docs/ROADMAP.md): what is next
- [CONTRIBUTING.md](CONTRIBUTING.md): working on the plugin, reporting a device

Want to help with the puzzles themselves (clues, words, grids, a new
language)? That happens in [arrowword-puzzles](https://github.com/dhalang-schildpad/arrowword-puzzles).

## Licence and credits

- Plugin code: [AGPL-3.0](LICENSE), like KOReader itself.
- The starter pack in `puzzles/` is CC BY-SA 4.0; it comes from arrowword-puzzles, which has the attribution.
- Thanks to the [KOReader](https://github.com/koreader/koreader) project, and to
  [roygbyte/crossword.koplugin](https://github.com/roygbyte/crossword.koplugin) for showing the way.
