#!/usr/bin/env bash
# Kopieert de plugin en de puzzels naar een via USB aangesloten Kobo met KOReader.
#
# Gebruik: tools/deploy-kobo.sh [/Volumes/KOBOeReader]
set -euo pipefail
HIER="$(cd "$(dirname "$0")/.." && pwd)"
KOBO="${1:-/Volumes/KOBOeReader}"
KOREADER="$KOBO/.adds/koreader"

if [[ ! -d "$KOREADER" ]]; then
    echo "Geen KOReader gevonden op $KOREADER. Is de Kobo aangesloten en KOReader geïnstalleerd?" >&2
    exit 1
fi

echo "Plugin -> $KOREADER/plugins/zweedsepuzzel.koplugin"
mkdir -p "$KOREADER/plugins"
rm -rf "$KOREADER/plugins/zweedsepuzzel.koplugin"
cp -R "$HIER/zweedsepuzzel.koplugin" "$KOREADER/plugins/"

echo "Puzzels -> $KOREADER/zweedsepuzzels/"
mkdir -p "$KOREADER/zweedsepuzzels"
cp "$HIER"/puzzles/*.json "$KOREADER/zweedsepuzzels/" 2>/dev/null || true
if [[ -d "$HIER/puzzles/generated" ]]; then
    cp "$HIER"/puzzles/generated/*.json "$KOREADER/zweedsepuzzels/" 2>/dev/null || true
fi

sync
echo "Klaar. Werp de Kobo veilig uit en herstart KOReader."
