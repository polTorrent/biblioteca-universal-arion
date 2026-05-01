#!/bin/bash
# =============================================================================
# claude-tasks-adapter.sh — Converteix tasques OpenClaw a prompts Claude Code
# =============================================================================

TASKS_DIR="$HOME/.openclaw/workspace/tasks"
BACKUP_DIR="$TASKS_DIR/openclaw-format-backup"
NEW_DIR="$TASKS_DIR/claude-ready"

mkdir -p "$NEW_DIR"

# Extreu el path de l'obra de la instrucció
extract_obra_path() {
    local instruction="$1"# Busca patrons com: obres/*/autor/obra o obres/categoria/autor/obra
    echo "$instruction" | grep -oP 'obres/[^/]+/[^/]+/[^/]+' | head -1
}

# Extreu autor i obra del path
parse_obra_info() {
    local path="$1"
    # obres/categoria/autor/obra -> categoria, autor, obra
    local parts=$(echo "$path" | tr '/' ' ')
    echo "$parts"
}

# Iterar sobre tasques del backup (format original)
for task_file in "$BACKUP_DIR"/*.json; do
    [ ! -f "$task_file" ] && continue
    
    task_id=$(basename "$task_file" .json)
    
    # Extreu informació amb Python
    task_type=$(python3 -c "import json; d=json.load(open('$task_file')); print(d.get('type','unknown'))" 2>/dev/null)
    instruction=$(python3 -c "import json; d=json.load(open('$task_file')); print(d.get('instruction',''))" 2>/dev/null)
    priority=$(python3 -c "import json; d=json.load(open('$task_file')); print(d.get('priority',2))" 2>/dev/null)
    
    # Extreu el path de l'obra de la instrucció
    obra_path=$(extract_obra_path "$instruction")
    
    # Si no troba el path, intenta extreure'l del ID
    if [ -z "$obra_path" ]; then
        # fix-translate-autor-obra-timestamp -> autor/obra
        obra_info=$(echo "$task_id" | sed 's/fix-translate-//' | sed 's/fix-fetch-//' | sed 's/-[0-9]*$//' | tr '-' '/')
        if [ -n "$obra_info" ]; then
            obra_path="obres/filosofia/$obra_info"
        fi
    fi
    
    # Determina la categoria basant-se en el path o tipus
    categoria="filosofia"
    if [[ "$obra_path" == *"/narrativa/"* ]] || [[ "$task_id" == *"akutagawa"* ]] || [[ "$task_id" == *"kafka"* ]] || [[ "$task_id" == *"tolstoi"* ]]; then
        categoria="narrativa"
    elif [[ "$obra_path" == *"/poesia/"* ]] || [[ "$task_id" == *"petrarca"* ]] || [[ "$task_id" == *"rumi"* ]]; then
        categoria="poesia"
    elif [[ "$obra_path" == *"/teatre/"* ]] || [[ "$task_id" == *"strindberg"* ]]; then
        categoria="teatre"
    fi
    
    # Construeix el path complet si no el tenim
    if [ -z "$obra_path" ]; then
        # Extreu autor i obra del ID
        autor=$(echo "$task_id" | sed 's/fix-translate-//' | sed 's/fix-fetch-//' | sed 's/-[0-9]*$//' | cut -d'-' -f1)
        obra=$(echo "$task_id" | sed 's/fix-translate-//' | sed 's/fix-fetch-//' | sed 's/-[0-9]*$//' | cut -d'-' -f2-)
        obra_path="obres/$categoria/$autor/$obra"
    fi
    
    # Generar prompt adequat per a Claude Code
    case "$task_type" in
        fetch|fix-fetch)
            prompt="Treballa en l'obra a '$obra_path'. Busca i descarrega l'original des de fonts fiables (Internet Archive, Wikisource, Project Gutenberg). Guarda'l a 'original.md' dins el directori de l'obra. Després fes commit i push dels canvis."
            ;;
        translate)
            prompt="Tradueix l'obra a '$obra_path'. 1) Llegeix l'original.md, 2) Tradueix al català seguint el protocol anti-al·lucinació del CLAUDE.md, 3) Guarda a traduccio.md, 4) Commit i push."
            ;;
        fix-translate)
            prompt="Repara la traducció a '$obra_path'. Revisa el fitxer traduccio.md, corregeix errors de normativa catalana, completa les parts incompletes seguint el protocol anti-al·lucinació. Assegura't que la traducció és fidel a l'original. Commit i push."
            ;;
        *)
            prompt="Processa la tasca '$task_type' per a l'obra a '$obra_path'. Segueix les instruccions del CLAUDE.md i les millors pràctiques del projecte."
            ;;
    esac
    
    # Crear nova tasca amb format Claude Code
    cat > "$NEW_DIR/$task_id.json" << EOF
{
    "id": "$task_id",
    "type": "$task_type",
    "priority": $priority,
    "max_minutes": 60,
    "obra_path": "$obra_path",
    "instruction": "$prompt",
    "created_at": "$(date -Iseconds)",
    "claude_ready": true
}
EOF
    
    echo "✅ $task_id -> $obra_path"
done

echo ""
echo "📊 Tasques convertides: $(ls -1 "$NEW_DIR"/*.json 2>/dev/null | wc -l)"
echo "📁 Ubicació: $NEW_DIR"