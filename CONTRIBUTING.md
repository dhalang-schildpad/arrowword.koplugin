# Contributing

This repository is the KOReader plugin. **Puzzle work (clues, word lists, grid
quality, new languages) happens in
[arrowword-puzzles](https://github.com/dhalang-schildpad/arrowword-puzzles)**,
and that is where help counts most.

Here you can help in two ways.

## 1. Tell us how it works on your device

We have tested one device, a Kobo Forma. A report from any other e-reader is
valuable: open an issue with the "Device report" template. Model, KOReader
version, the grid size you tried, whether the clue text is readable, and a
photo. See [docs/DEVICES.md](docs/DEVICES.md) for what we expect and why.

## 2. Work on the plugin

You can develop without a device, using KOReader's desktop emulator.

- Build KOReader next to this repository (`../koreader`) following its
  [build guide](https://github.com/koreader/koreader/blob/master/doc/Building.md).
  On macOS you also need `wget`, and a full clone (not `--depth 1`), otherwise the version string breaks start-up.
- `tools/emulator.sh` links this repository into the emulator as `arrowword.koplugin` and starts it at
  Kobo Forma size. If `../arrowword-puzzles` exists, its packs are linked in too.
- `tools/test.sh` runs the puzzle model tests (`tools/test_puzzle.lua`) with the emulator's LuaJIT.
- `luacheck *.lua` must be clean. Note that `_` is the translation function: use `__` for unused loop
  variables, never `_`. That mistake crashed the plugin on a real device once.
- The plugin reads a few environment variables that open a puzzle at start-up, replay taps and keys, and
  save screenshots; they are documented at the top of `tools/emulator.sh`. Use them to attach before/after
  screenshots to a pull request.

### Code map

| File | Role |
|---|---|
| `main.lua` | menu entry, puzzle library (folders are packs), progress storage |
| `puzzle.lua` | model: selection, input, check, hints, progress. No KOReader dependencies, so it is unit-tested |
| `gameview.lua` | one full-screen widget that paints grid, clue cells, clue bar and letter bar, and handles input |
| `i18n.lua` | the plugin's own UI strings; add a table per language |
| `puzzles/` | starter pack shipped with the plugin |

### E-ink rules of thumb

- Refresh only the region that changed: `UIManager:setDirty(self, function() return "ui", rect end)`.
- Never flash on a key press; flash only when opening and closing the game.
- Paint directly on the Blitbuffer rather than building a widget per cell; the CPU is slow.
- Keep fills light and borders crisp. Test text sizes at real cell sizes (see DEVICES.md).

### Ideas

See [docs/ROADMAP.md](docs/ROADMAP.md): a solution-word bar, confirmation before a hint, page-turn buttons
for previous and next word, bent arrows, downloading packs on the device.

If a change touches the puzzle format, update [docs/PUZZLE_FORMAT.md](docs/PUZZLE_FORMAT.md) here first and
bump the version; the generator in arrowword-puzzles follows.

## Pull requests

- Branch from `main`, keep a pull request to one subject, and describe what you checked.
- Run `luacheck *.lua` and `tools/test.sh`.
- Documentation, code and commit messages are in English.
- Commit messages: a short imperative summary line, then why.

Contributions are licensed under AGPL-3.0, like the rest of the plugin.
