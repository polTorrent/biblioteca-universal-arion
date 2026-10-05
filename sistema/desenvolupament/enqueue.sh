#!/usr/bin/env bash
# enqueue.sh — Afegeix tasques al backlog del worker de desenvolupament.
#
# Ús:
#   bash enqueue.sh <fitxer.md> [prioritat]   # copia una tasca al backlog
#   bash enqueue.sh --new "Títol de la tasca" # crea una plantilla
#   bash enqueue.sh --list                    # llista el backlog
set -uo pipefail

DEV_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BL="$DEV_DIR/backlog"

mkdir -p "$BL/pending" "$BL/running" "$BL/done" "$BL/failed"

slugify() {
    echo "$1" | tr '[:upper:]' '[:lower:]' \
        | sed 's/[^a-z0-9]\+/-/g; s/^-//; s/-$//' | cut -c1-60
}

case "${1:-}" in
    --new)
        shift
        TITLE="${*:-Tasca sense títol}"
        SLUG="$(slugify "$TITLE")"
        FILE="$BL/pending/$(date +%Y%m%d%H%M)-$SLUG.md"
        cat > "$FILE" <<EOF
---
títol: $TITLE
prioritat: 5
estat: pending
---
# $TITLE

## Objectiu
<què s'ha d'aconseguir, en una frase>

## Context
<estat actual, fitxers rellevants, per què cal>

## Passos
1. ...
2. ...

## Fitxers
- ...

## Validació
<com es comprova que està fet: ordres exactes + resultat esperat>
EOF
        echo "✅ Plantilla creada: $FILE"
        ;;
    --list)
        echo "═══ BACKLOG ═══"
        for d in pending running done failed; do
            n=$(ls "$BL/$d" 2>/dev/null | grep -c '\.md$' || true)
            echo "  $d: $n"
        done
        echo
        echo "── PENDING ──"
        ls "$BL/pending" 2>/dev/null | grep '\.md$' | sort || echo "  (buit)"
        ;;
    *)
        SRC="${1:-}"
        [ -z "$SRC" ] && { echo "Ús: enqueue.sh <fitxer.md> [prioritat]"; exit 1; }
        [ -f "$SRC" ] || { echo "No existeix: $SRC"; exit 1; }
        PRIO="${2:-5}"
        BASE="$(basename "$SRC")"
        DEST="$BL/pending/$(date +%Y%m%d%H%M)-$BASE"
        cp "$SRC" "$DEST"
        echo "✅ Encuada: $DEST (prioritat $PRIO)"
        ;;
esac
