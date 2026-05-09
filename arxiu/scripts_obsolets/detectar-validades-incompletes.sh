#!/bin/bash
# Comprova obres .validated però amb traducció incompleta

PROJECT="$HOME/biblioteca-universal-arion"
TASKS_DIR="$PROJECT/sistema/tasks"
MIN_RATIO=0.6  # Obres validades haurien de tenir almenys 60%

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [VALIDADES-INC] $1"; }

count_words() {
    local file="$1"
    grep -v "^---\|^#\|^$" "$file" 2>/dev/null | wc -w
}

# Cercar obres validades però incompletes
find "$PROJECT/obres" -name ".validated" -type f | while read val; do
    obra_dir=$(dirname "$val")
    if [ -f "$obra_dir/original.md" ] && [ -f "$obra_dir/traduccio.md" ]; then
        orig_words=$(count_words "$obra_dir/original.md")
        trad_words=$(count_words "$obra_dir/traduccio.md")
        
        if [ "$orig_words" -gt 0 ]; then
            ratio=$(python3 -c "print(f'{$trad_words / $orig_words * 100:.1f}')")
            
            # Si validada però incompleta
            if [ "$(python3 -c "print($trad_words / $orig_words < $MIN_RATIO)")" = "True" ]; then
                slug=$(basename "$obra_dir")
                
                # Eliminar .validated per re-obrir l'obra
                log "⚠️  $slug: validada però només ${ratio}% completa"
                log "   Eliminant .validated per permetre correcció..."
                rm -f "$val"
                
                # Marcar per a revisió
                echo "Revisar: traduït ${trad_words}/${orig_words} paraules (${ratio}%)" > "$obra_dir/.needs_fix"
            fi
        fi
    fi
done
