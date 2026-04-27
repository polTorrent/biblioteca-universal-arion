#!/bin/bash
# =============================================================================
# diem-optimizer.sh — Optimitzador de crèdits DIEM diaris
# =============================================================================
# Aprofita els crèdits DIEM que es restableixen cada 00:00 UTC per millorar
# el projecte Biblioteca Universal Arion.
#
# Horari: 22:00 UTC - 23:59 UTC (hores punta abans del reset)
# Estratègia: Utilitza crèdits sobrants per tasques d'optimizció/qualitat
# =============================================================================

set -uo pipefail

# ── Configuració ──────────────────────────────────────────────────────────────
PROJECT="$HOME/biblioteca-universal-arion"
TASKS_DIR="$HOME/.openclaw/workspace/tasks"
LOG="$HOME/diem-optimizer.log"
DISCORD_CHANNEL="1469504522614476953"  # Canal Biblioteca Universal Arion
MIN_BALANCE_FOR_OPTIMIZATION=5.0  # Mínim DIEM per activar optimitzacions
VENICE_BIN="$HOME/.openclaw/workspace/skills/venice-ai/scripts/venice.py"

# ── Helpers ───────────────────────────────────────────────────────────────────
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [DIEM-OPT] $1" | tee -a "$LOG"; }

send_discord() {
    local message="$1"
    # Utilitzar hermes per enviar al canal de Discord
    hermes chat --platform discord --chat-id "$DISCORD_CHANNEL" "$message" 2>/dev/null || true
}

# ── Verificar saldo DIEM ───────────────────────────────────────────────────────
check_diem_balance() {
    if [ ! -f "$VENICE_BIN" ]; then
        log "❌ Venice script no trobat: $VENICE_BIN"
        return 1
    fi
    
    local balance_output
    balance_output=$(python3 "$VENICE_BIN" balance 2>&1)
    
    if [ $? -ne 0 ]; then
        log "❌ Error consultant saldo: $balance_output"
        return 1
    fi
    
    local diem_balance
    diem_balance=$(echo "$balance_output" | grep -oP 'DIEM:\s*\K[\d.]+' | head -1)
    
    if [ -z "$diem_balance" ]; then
        log "⚠️ No s'ha pogut extreure DIEM del output"
        return 1
    fi
    
    echo "$diem_balance"
    return 0
}

# ── Estratègies d'optimització segons saldo ─────────────────────────────────────
plan_optimizations() {
    local balance=$1
    local tasks=""
    
    # Utilitzar model selector intel·ligent
    local budget_report
    budget_report=$(python3 "$PROJECT/sistema/config/model_selector.py" 2>&1)
    
    log "📊 Estat del pressupost:"
    echo "$budget_report" | grep -E "Saldo|Disponible|Recomanacions" >> "$LOG"
    
    # Balance alt (>8 DIEM) → Tasques amb models superiors
    if (( $(echo "$balance > 8.0" | bc -l) )); then
        log "💰 Saldo alt ($balance DIEM) - Utilitzant models superiors per tareas importants"
        tasks="PREMIUM"
    # Balance mitjà (5-8 DIEM) → Tasques amb models equilibrats
    elif (( $(echo "$balance >= 5.0" | bc -l) )); then
        log "📊 Saldo mitjà ($balance DIEM) - Utilitzant models equilibrats"
        tasks="BALANCED"
    # Balance baix (3-5 DIEM) → Tasques rutinàries amb models econòmics
    elif (( $(echo "$balance >= 3.0" | bc -l) )); then
        log "⚠️ Saldo baix ($balance DIEM) - Només tasques rutinàries"
        tasks="ECONOMIC"
    # Balance crític (<3 DIEM) → Preservar
    else
        log "🚨 Saldo crític ($balance DIEM) - Preservant per emergències"
        tasks="SKIP"
    fi
    
    echo "$tasks"
}

# ── Crear tasques d'optimització ───────────────────────────────────────────────
create_optimization_tasks() {
    local level=$1
    local count=0
    
    case "$level" in
        PREMIUM)
            # Models superiors per a traduccions importants
            log "💎 Creant tasques PREMIUM amb models superiors"
            
            create_task "Traducció: Obra filosòfica complexa" \
                "Usant model_selector.py per seleccionar claude-opus-4-7. Tradueix obra filosòfica sense .validated. Protocol anti-al·lucinació obligatori. Crea .validated si qualitat >= 8." && ((count++))
            
            create_task "Supervisió: Revisió final d'alta qualitat" \
                "Usant openai-gpt-55-pro per detectar al·lucinacions. Revisa traduccions amb puntuació 7-8. Aplica protocol anti-al·lucinació. Crea .validated si qualitat >= 8." && ((count++))
            
            create_task "Qualitat: Glossari i notes d'obra complexa" \
                "Usant claude-opus-4-7. Obra amb .validated però sense glossari complet. Extreu termes filosòfics/lingüístics i crea glossari.yml amb definicions contextuales." && ((count++))
            ;;
            
        BALANCED)
            # Models equilibrats per a tasques mitjanes
            log "⚖️ Creant tasques BALANCED amb models equilibrats"
            
            create_task "Traducció: Obra narrativa estàndard" \
                "Usant claude-sonnet-4-6. Tradueix obra narrativa sense .validated. Qualitat mínim 7/10. Crea .validated si >= 7." && ((count++))
            
            create_task "Supervisió: Revisió bàsica" \
                "Usant qwen3-6-27b. Revisa obres noves (últims 7 dies). Puntuació >= 6. Aplica protocol anti-al·lucinació bàsic." && ((count++))
            
            create_task "Metadata: Completar metadades" \
                "Usant qwen3-6-27b. Obres sense metadata.yml o incomplet. Crea metadata complet amb títol, autor, llengua, categoria, data, estat." && ((count++))
            ;;
            
        ECONOMIC)
            # Models econòmics per a tasques rutinàries
            log "💡 Creant tasques ECONOMIC amb models econòmics"
            
            create_task "Web: Regenerar docs si cal" \
                "Usant glm-5. Comprova si obres/ té modificacions més recents que docs/. Si sí, executa: python3 sistema/web/build.py. Commit i push." && ((count++))
            
            create_task "Tests: Executar testos bàsics" \
                "Usant glm-5. Executa: python3 -m pytest tests/ -v --tb=short. Si hi ha errors simples, arregla'ls. Ignora errors complexos." && ((count++))
            
            create_task "Fetch: Obtenir texts fonts" \
                "Usant deepseek-v3.2. Obres sense original.md. Cercador fonts, descarrega text i guarda comoriginal.md. Commit." && ((count++))
            ;;
            
        SKIP)
            log "⏭️ No es creen tasques d'optimització - Preservant saldo"
            return 0
            ;;
    esac
    
    log "✅ $count tasques d'optimització creades amb nivell $level"
    return $count
}

create_task() {
    local title="$1"
    local instruction="$2"
    
    # No crear tasques si ja n'hi ha moltes pendents
    local pending
    pending=$(ls -1 "$TASKS_DIR/pending/"*.json 2>/dev/null | wc -l)
    
    if [ "$pending" -ge 5 ]; then
        log "⚠️ Massa tasques pendents ($pending). No es creen més."
        return 1
    fi
    
    # Crear tasca via task-manager
    bash "$PROJECT/sistema/automatitzacio/task-manager.sh" add "optimize" "$instruction" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        log "   ➕ $title"
        return 0
    else
        log "   ❌ Error creant: $title"
        return 1
    fi
}

# ── Main ───────────────────────────────────────────────────────────────────────
main() {
    log "🚀 Iniciant optimitzador DIEM"
    
    # Verificar que estem en l'horari correcte (opcional, es pot executar sempre)
    local hour
    hour=$(date -u +%H)
    
    if [ "$hour" -ge 22 ] || [ "$hour" -lt 2 ]; then
        send_discord "🔄 **DIEM Optimizer iniciat** - Verificant saldo disponible..."
    fi
    
    # Consultar saldo
    local balance
    balance=$(check_diem_balance)
    
    if [ $? -ne 0 ]; then
        log "❌ No s'ha pogut obtenir el saldo DIEM"
        send_discord "❌ **Error DIEM Optimizer**: No s'ha pogut consultar el saldo"
        exit 1
    fi
    
    log "💰 Saldo DIEM: $balance"
    
    # Decidir estratègia
    local strategy
    strategy=$(plan_optimizations "$balance")
    
    if [ "$strategy" = "SKIP" ]; then
        log "⏭️ Saldo insuficient per optimitzacions"
        send_discord "⏭️ **DIEM Optimizer**: Saldo insuficient ($balance DIEM) - Preservant crèdits"
        exit 0
    fi
    
    # Crear tasques
    create_optimization_tasks "$strategy"
    
    # Notificar
    send_discord "✅ **DIEM Optimizer completat** - $balance DIEM disponibles, tasques d'optimització creades"
    
    log "✅ Optimitzador completat"
}

# Executar si s'invoca directament
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi