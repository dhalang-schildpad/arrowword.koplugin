#!/usr/bin/env bash
# Runs the puzzle model tests with the luajit from the emulator build (../koreader).
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
KOREADER="${KOREADER_DIR:-$HERE/../koreader}"
EMU="$(ls -d "$KOREADER"/koreader-emulator-*/koreader | head -1)"
cd "$HERE"
"$EMU/luajit" -e "package.cpath='$EMU/common/?.so;'..package.cpath; package.path='$EMU/common/?.lua;$HERE/arrowword.koplugin/?.lua;'..package.path" tools/test_puzzle.lua "$@"
