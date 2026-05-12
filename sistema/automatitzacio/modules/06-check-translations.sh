#!/bin/bash
# 06-check-translations.sh — Obres pendents de traducció
MODULE_NAME="check-translations"
source "${BASH_SOURCE[0]%/*}/common.sh"

check_translations() {
    log "📚 Analitzant obres pendents..."
    log_json "info" "checking_translations"
    
    # Buscar obres amb original.md però sense traduccio.md (o buida)
    for obra_dir in "$PROJECT/obres"/*/; do
        [ "$(count_pending)" -ge "$MAX_PENDING" ] && break
        [ ! -d "$obra_dir" ] && continue
        
        # Iterar autors
        for autor_dir in "$obra_dir"*/; do
            [ ! -d "$autor_dir" ] && continue
            [ "$(count_pending)" -ge "$MAX_PENDING" ] && break
            
            # Iterar obres
            for obra_path in "$autor_dir"*/; do
                [ ! -d "$obra_path" ] && continue
                [ "$(count_pending)" -ge "$MAX_PENDING" ] && break
                
                local original="$obra_path/original.md"
                local traduccio="$obra_path/traduccio.md"
                local validated="$obra_path/.validated"
                
                # Si no hi ha original, skip
                [ ! -f "$original" ] && continue
                # Si l'original és buit, skip
                [ ! -s "$original" ] && continue
                # Si ja està validada, skip
                [ -f "$validated" ] && continue
                # Si ja hi ha tasca pending/running per aquesta obra, skip
                local obra_name=$(basename "$obra_path")
                if task_exists "$obra_name" > /dev/null 2>&1; then
                    continue
                fi
                
                # Determinar tipus: traduir nova o continuar
                local tipus="translate"
                local accio="Tradueix"
                if [ -f "$traduccio" ] && [ -s "$traduccio" ]; then
                    tipus="translate"
                    accio="Continua la traducció de"
                fi
                
                # Calcular ruta relativa
                local rel_path="${obra_path#$PROJECT/}"
                rel_path="${rel_path%/}"  # Treure / final
                
                # Detectar gènere per a la ruta
                local genere=$(echo "$rel_path" | cut -d'/' -f1)
                
                # Seleccionar model segons gènere
                local model="claude-sonnet-4-6"
                case "$genere" in
                    filosofia|poesia|teatre) model="claude-opus-4-7" ;;
                    narrativa|assaig) model="claude-sonnet-4-6" ;;
                    oriental) model="qwen3-235b-a22b-instruct-2507" ;;
                esac
                
                # Crear tasca amb format correcte per al worker
                add_task "$tipus" "$accio l'obra al català literari. Ruta: $rel_path"
                
                # Actualitzar el model de la darrera tasca creada
                local latest_task=$(ls -t "$TASKS_DIR/pending/"*.json 2>/dev/null | head -1)
                if [ -n "$latest_task" ]; then
                    python3 -c "
import json
with open('$latest_task') as f: d = json.load(f)
d['model'] = '$model'
json.dump(d, open('$latest_task', 'w'), indent=2, ensure_ascii=False)
" 2>/dev/null
                    log "   📝 $accio: $rel_path (model=$model)"
                fi
            done
        done
    done
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    PROJECT="${PROJECT:-$HOME/biblioteca-universal-arion}"
    TASKS_DIR="$PROJECT/sistema/tasks"; LOG="$PROJECT/sistema/logs/heartbeat.log"
    MAX_PENDING=5; MIN_DIEM_RESERVE=3; TASK_MANAGER="$PROJECT/sistema/automatitzacio/task-manager.sh"
    check_translations
fi
