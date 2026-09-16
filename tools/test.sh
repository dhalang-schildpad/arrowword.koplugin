#!/usr/bin/env bash
# Draait de modeltests met de luajit uit de emulatorbuild (../koreader).
set -euo pipefail
HIER="$(cd "$(dirname "$0")/.." && pwd)"
KOREADER="${KOREADER_DIR:-$HIER/../koreader}"
EMU="$(ls -d "$KOREADER"/koreader-emulator-*/koreader | head -1)"
cd "$HIER"
"$EMU/luajit" -e "package.cpath='$EMU/common/?.so;'..package.cpath; package.path='$EMU/common/?.lua;$HIER/zweedsepuzzel.koplugin/?.lua;'..package.path" tools/test_puzzle.lua "$@"
