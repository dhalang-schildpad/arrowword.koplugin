#!/usr/bin/env bash
# Starts the KOReader emulator (sized like a Kobo Forma) with this plugin loaded.
#
# Needs a KOReader checkout next to this repo (../koreader), built with
# `./kodev fetch-thirdparty && ./kodev build` (see CONTRIBUTING.md).
#
# Usage: tools/emulator.sh             start (re-installs the plugin first)
#        tools/emulator.sh --no-build  start without re-installing
#
# Development aids (environment variables read by the plugin):
#   AW_AUTOOPEN=<puzzle.json>|library   open a puzzle or the library at start
#   AW_SCRIPT="cell:1,1;key:R;button:check;shot:/tmp/shot.png"   simulate input
#   AW_SCREENSHOT=/path.png             with AW_AUTOOPEN=library: screenshot after 5 s
set -euo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
KOREADER="${KOREADER_DIR:-$HERE/../koreader}"
BREW="$(brew --prefix)"
export PATH="$BREW/opt/coreutils/libexec/gnubin:$BREW/opt/findutils/libexec/gnubin:$BREW/opt/gnu-getopt/bin:$BREW/opt/make/libexec/gnubin:$BREW/opt/util-linux/bin:$PATH"
export PKG_CONFIG_PATH="$BREW/opt/util-linux/lib/pkgconfig"
# Make KOReader's file browser start in the puzzles folder instead of $HOME,
# otherwise macOS asks for access to Desktop/Documents and blocks the emulator.
export XDG_DOCUMENTS_DIR="$HERE/puzzles"

cd "$KOREADER"
ln -sfn "$HERE/arrowword.koplugin" plugins/arrowword.koplugin
EMU="$(ls -d "$KOREADER"/koreader-emulator-*/koreader | head -1)"
ln -sfn "$HERE/puzzles" "$EMU/arrowwords"
if [[ "${1:-}" != "--no-build" ]]; then
    ./kodev build >/dev/null
fi
# 720x960 points at 300 dpi gives 1440x1920 pixels on a Retina Mac, like the Forma.
NO_BUILD=1 exec ./kodev run -W 720 -H 960 -D 300
