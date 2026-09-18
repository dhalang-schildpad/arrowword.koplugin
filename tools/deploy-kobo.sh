#!/usr/bin/env bash
# Copies the plugin (and puzzle packs, if found) to a Kobo with KOReader, mounted over USB.
#
# Usage: tools/deploy-kobo.sh [/Volumes/KOBOeReader]
# Packs are taken from ../arrowword-puzzles/packs, or from $ARROWWORD_PACKS.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
KOBO="${1:-/Volumes/KOBOeReader}"
KOREADER="$KOBO/.adds/koreader"
PACKS="${ARROWWORD_PACKS:-$HERE/../arrowword-puzzles/packs}"

if [[ ! -d "$KOREADER" ]]; then
    echo "No KOReader found at $KOREADER. Is the Kobo connected and KOReader installed?" >&2
    exit 1
fi

# remove the plugin under its previous (Dutch) name, if present
rm -rf "$KOREADER/plugins/zweedsepuzzel.koplugin" "$KOREADER/zweedsepuzzels"

DEST="$KOREADER/plugins/arrowword.koplugin"
echo "Plugin -> $DEST"
rm -rf "$DEST"
mkdir -p "$DEST"
cp "$HERE"/*.lua "$DEST/"
cp -R "$HERE/puzzles" "$DEST/"
cp "$HERE/LICENSE" "$HERE/README.md" "$DEST/"

if [[ -d "$PACKS" ]]; then
    echo "Packs  -> $KOREADER/arrowwords/"
    mkdir -p "$KOREADER/arrowwords"
    cp -R "$PACKS/." "$KOREADER/arrowwords/"
fi

# macOS writes ._ files (resource forks) on FAT volumes; clean them up
if command -v dot_clean >/dev/null; then
    dot_clean -m "$DEST"
    [[ -d "$KOREADER/arrowwords" ]] && dot_clean -m "$KOREADER/arrowwords"
fi
sync
echo "Done. Eject the Kobo safely and restart KOReader."
