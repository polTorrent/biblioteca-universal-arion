#!/bin/bash
# =============================================================================
# fix-structure.sh — Auto-correcció d'estructura d'obres
# =============================================================================
# Detecta obres mal ubicades a obres/ i les mou a la categoria correcta.
# Cridat pel heartbeat o manualment.
# Ús: bash sistema/automatitzacio/fix-structure.sh [--dry-run]
# =============================================================================

set -uo pipefail

PROJECT="$HOME/biblioteca-universal-arion"
OBRES_DIR="$PROJECT/obres"
LOG="$HOME/claude-worker.log"
DRY_RUN=false

[ "${1:-}" = "--dry-run" ] && DRY_RUN=true

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [FIX-STRUCTURE] $1" | tee -a "$LOG"; }

# Categories vàlides
VALID_CATEGORIES="filosofia narrativa poesia teatre oriental assaig"

# Mapa d'autors → categoria (els més comuns)
declare -A AUTOR_CATEGORIA=(
    # Filosofia
    ["epictetus"]="filosofia"
    ["seneca"]="filosofia"
    ["plato"]="filosofia"
    ["aristotil"]="filosofia"
    ["marc-aureli"]="filosofia"
    ["heraclit"]="filosofia"
    ["schopenhauer"]="filosofia"
    ["nietzsche"]="filosofia"
    ["montaigne"]="filosofia"
    ["descartes"]="filosofia"
    ["kant"]="filosofia"
    ["spinoza"]="filosofia"
    ["hume"]="filosofia"
    ["locke"]="filosofia"
    ["marx"]="filosofia"
    ["confuci"]="filosofia"
    ["laozi"]="filosofia"
    # Narrativa
    ["kafka"]="narrativa"
    ["dostoievski"]="narrativa"
    ["txekhov"]="narrativa"
    ["tolstoi"]="narrativa"
    ["poe"]="narrativa"
    ["edgar-allan-poe"]="narrativa"
    ["herman-melville"]="narrativa"
    ["akutagawa"]="narrativa"
    ["garxin"]="narrativa"
    ["sade"]="narrativa"
    ["gogol"]="narrativa"
    ["dickens"]="narrativa"
    ["twain"]="narrativa"
    ["wilde"]="narrativa"
    ["stevenson"]="narrativa"
    ["shelley"]="narrativa"
    ["stoker"]="narrativa"
    ["lovecraft"]="narrativa"
    ["maupassant"]="narrativa"
    # Poesia
    ["baudelaire"]="poesia"
    ["shakespeare"]="poesia"
    ["rimbaud"]="poesia"
    ["rilke"]="poesia"
    ["homer"]="poesia"
    ["virgili"]="poesia"
    ["ovidi"]="poesia"
    ["dante"]="poesia"
    ["petrarca"]="poesia"
    # Teatre
    ["sofocles"]="teatre"
    ["euripides"]="teatre"
    ["aristofanes"]="teatre"
    ["moliere"]="teatre"
    ["ibsen"]="teatre"
    # Oriental
    ["sanscrit"]="oriental"
    ["murasaki"]="oriental"
    ["basho"]="oriental"
    ["sun-tzu"]="oriental"
)

# ── Detectar carpetes mal ubicades ────────────────────────────────────────────
fix_count=0

for entry in "$OBRES_DIR"/*/; do
    [ -d "$entry" ] || continue
    
    dirname=$(basename "$entry")
    
    # Si ja és una categoria vàlida, skip
    if echo "$VALID_CATEGORIES" | grep -qw "$dirname"; then
        continue
    fi
    
    # És un autor directament a obres/ (hauria d'estar dins una categoria)
    log "⚠️ Trobat '$dirname' directament a obres/ (falta categoria)"
    
    # Buscar categoria al mapa
    categoria="${AUTOR_CATEGORIA[$dirname]:-}"
    
    # Si no és al mapa, intentar detectar per metadata.yml
    if [ -z "$categoria" ]; then
        for obra_subdir in "$entry"/*/; do
            [ -d "$obra_subdir" ] || continue
            if [ -f "$obra_subdir/metadata.yml" ]; then
                detected=$(grep -i "^category\|^categoria" "$obra_subdir/metadata.yml" 2>/dev/null | head -1 | sed 's/.*: *//' | tr -d '"' | tr -d "'" | tr '[:upper:]' '[:lower:]')
                if [ -n "$detected" ] && echo "$VALID_CATEGORIES" | grep -qw "$detected"; then
                    categoria="$detected"
                    break
                fi
            fi
        done
    fi
    
    # Si encara no sabem la categoria, posar a filosofia per defecte (la més comuna)
    if [ -z "$categoria" ]; then
        log "   ❓ No puc determinar categoria per '$dirname'. Usant 'filosofia' per defecte."
        categoria="filosofia"
    fi
    
    target="$OBRES_DIR/$categoria/$dirname"
    
    if [ -d "$target" ]; then
        # Ja existeix la carpeta destí — merge (moure subcarpetes que no existeixin)
        log "   📁 Ja existeix $categoria/$dirname — fent merge..."
        
        for obra_subdir in "$entry"/*/; do
            [ -d "$obra_subdir" ] || continue
            obra_name=$(basename "$obra_subdir")
            
            if [ -d "$target/$obra_name" ]; then
                # Ja existeix — comparar contingut
                local_files=$(ls "$obra_subdir" 2>/dev/null | wc -l)
                target_files=$(ls "$target/$obra_name" 2>/dev/null | wc -l)
                
                if [ "$local_files" -gt "$target_files" ]; then
                    log "   🔄 Duplicat '$obra_name': versió a obres/$dirname/ té més fitxers ($local_files vs $target_files). Substituint."
                    if ! $DRY_RUN; then
                        rm -rf "$target/$obra_name"
                        mv "$obra_subdir" "$target/"
                        fix_count=$((fix_count + 1))
                    fi
                else
                    log "   🗑️ Duplicat '$obra_name': versió a $categoria/ és millor o igual. Eliminant duplicat."
                    if ! $DRY_RUN; then
                        rm -rf "$obra_subdir"
                        fix_count=$((fix_count + 1))
                    fi
                fi
            else
                log "   📦 Movent '$obra_name' → $categoria/$dirname/"
                if ! $DRY_RUN; then
                    mv "$obra_subdir" "$target/"
                    fix_count=$((fix_count + 1))
                fi
            fi
        done
        
        # Netejar carpeta buida
        if ! $DRY_RUN; then
            rmdir "$entry" 2>/dev/null && log "   🧹 Carpeta buida '$dirname' eliminada"
        fi
    else
        # No existeix — moure sencer
        log "   📦 Movent '$dirname' → $categoria/$dirname/"
        if ! $DRY_RUN; then
            mkdir -p "$OBRES_DIR/$categoria"
            mv "$entry" "$target"
            fix_count=$((fix_count + 1))
        fi
    fi
done

if [ $fix_count -gt 0 ]; then
    log "✅ Estructura corregida: $fix_count canvis"
    
    if ! $DRY_RUN; then
        # Rebuild web
        cd "$PROJECT"
        python3 sistema/web/build.py > /dev/null 2>&1
        git add -A 2>/dev/null
        git commit -m "fix: auto-correcció estructura obres ($fix_count canvis)" 2>/dev/null
        git push origin main 2>/dev/null
        log "📤 Commit + push amb estructura corregida"
    else
        log "🔍 (dry-run — cap canvi aplicat)"
    fi
else
    log "✅ Estructura correcta — res a corregir"
fi
