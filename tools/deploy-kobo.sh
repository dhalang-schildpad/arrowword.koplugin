#!/usr/bin/env bash
# Copies the plugin and the puzzles to a Kobo with KOReader, mounted over USB.
#
# Usage: tools/deploy-kobo.sh [/Volumes/KOBOeReader]
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
KOBO="${1:-/Volumes/KOBOeReader}"
KOREADER="$KOBO/.adds/koreader"

if [[ ! -d "$KOREADER" ]]; then
    echo "No KOReader found at $KOREADER. Is the Kobo connected and KOReader installed?" >&2
    exit 1
fi

# remove the plugin under its previous (Dutch) name, if present
rm -rf "$KOREADER/plugins/zweedsepuzzel.koplugin" "$KOREADER/zweedsepuzzels"

echo "Plugin  -> $KOREADER/plugins/arrowword.koplugin"
mkdir -p "$KOREADER/plugins"
rm -rf "$KOREADER/plugins/arrowword.koplugin"
cp -R "$HERE/arrowword.koplugin" "$KOREADER/plugins/"

echo "Puzzles -> $KOREADER/arrowwords/"
mkdir -p "$KOREADER/arrowwords"
for dir in samples packs; do
    [[ -d "$HERE/puzzles/$dir" ]] || continue
    # packs/<lang>/<pack>/ becomes arrowwords/<lang>/<pack>/
    if [[ "$dir" == "packs" ]]; then
        cp -R "$HERE/puzzles/packs/." "$KOREADER/arrowwords/"
    else
        mkdir -p "$KOREADER/arrowwords/samples"
        cp "$HERE"/puzzles/samples/*.json "$KOREADER/arrowwords/samples/"
    fi
done

# macOS writes ._ files (resource forks) on FAT volumes; clean them up
if command -v dot_clean >/dev/null; then
    dot_clean -m "$KOREADER/plugins/arrowword.koplugin" "$KOREADER/arrowwords"
fi
sync
echo "Done. Eject the Kobo safely and restart KOReader."
