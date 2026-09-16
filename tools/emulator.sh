#!/usr/bin/env bash
# Start de KOReader-emulator (als Kobo Forma) met deze plugin erin.
#
# Vereist een KOReader-checkout naast deze repo (../koreader), gebouwd met
# `./kodev fetch-thirdparty && ./kodev build` (zie PLAN.md §7), en een symlink
# ../koreader/plugins/zweedsepuzzel.koplugin -> zweedsepuzzel.koplugin.
#
# Gebruik: tools/emulator.sh            start (herinstalleert de plugin eerst)
#          tools/emulator.sh --no-build  start zonder herinstalleren
set -euo pipefail

HIER="$(cd "$(dirname "$0")/.." && pwd)"
KOREADER="${KOREADER_DIR:-$HIER/../koreader}"
BREW="$(brew --prefix)"
export PATH="$BREW/opt/coreutils/libexec/gnubin:$BREW/opt/findutils/libexec/gnubin:$BREW/opt/gnu-getopt/bin:$BREW/opt/make/libexec/gnubin:$BREW/opt/util-linux/bin:$PATH"
export PKG_CONFIG_PATH="$BREW/opt/util-linux/lib/pkgconfig"

cd "$KOREADER"
if [[ ! -L plugins/zweedsepuzzel.koplugin ]]; then
    ln -s "$HIER/zweedsepuzzel.koplugin" plugins/zweedsepuzzel.koplugin
fi
if [[ "${1:-}" == "--no-build" ]]; then
    NO_BUILD=1 exec ./kodev run -s kobo-forma
else
    ./kodev build >/dev/null
    NO_BUILD=1 exec ./kodev run -s kobo-forma
fi
