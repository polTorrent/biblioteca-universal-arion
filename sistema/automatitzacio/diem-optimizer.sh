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
    
    # Balance alt (>10 DIEM) → Tasques intensives
    if (( $(echo "$balance > 10.0" | bc -l) )); then
        log "📊 Saldo alt ($balance DIEM) - Planificant tasques intensives"
        tasks="INTENSIVE"
    # Balance mitjà (5-10 DIEM) → Tasques mitjanes
    elif (( $(echo "$balance >= 5.0" | bc -l) )); then
        log "📊 Saldo mitjà ($balance DIEM) - Planificant tasques mitjanes"
        tasks="MODERATE"
    # Balance baix (<5 DIEM) → No activar
    else
        log "📊 Saldo baix ($balance DIEM) - Millor preservar"
        tasks="SKIP"
    fi
    
    echo "$tasks"
}

# ── Crear tasques d'optimització ───────────────────────────────────────────────
create_optimization_tasks() {
    local level=$1
    local count=0
    
    case "$level" in
        INTENSIVE)
            # Revisar traduccions amb qualitat mitjana
            create_task "Qualitat: Revisar traduccions amb puntuació 6-7" \
                "Busca obres amb .needs_fix que tinguin puntuació entre 6-7. Revisa i millora la traducció. Elimina .needs_fix si la qualitat final >= 8." && ((count++))
            
            # Actualitzar glossaris
            create_task "Glossari: Actualitzar glossaris d'obres completades" \
                "Busca obres amb .validated i sense glossari.yml (o glossari incomplet). Extreu termes del text i crea glossari complet." && ((count++))
            
            # Revisar metadata
            create_task "Metadata: Completar metadata.yml d'obres sense metadata" \
                "Busca obres sense metadata.yml o amb metadata incomplet. Crea metadata.yml amb: title, author, source_language, category, date, status, translator." && ((count++))
            
            # Testejant scripts
            create_task "Tests: Executar tests del projecte" \
                "Executa: python3 -m pytest tests/ -v. Si hi ha errors, arregla'ls. Commit amb: 'test: corregeix errors'." && ((count++))
            ;;
            
        MODERATE)
            # Revisar traduccions recents
            create_task "Qualitat: Supervisar traduccions noves" \
                "Busca obres traduïdes els últims 7 dies sense .validated. Revisa 5-10 unitats aleatòries. Crea .validated o .needs_fix segons qualitat." && ((count++))
            
            # Actualitzar web
            create_task "Web: Regenerar docs si cal" \
                "Comprova si obres/ té modificacions més recents que docs/. Si sí, executa: python3 sistema/web/build.py. Commit i push." && ((count++))
            ;;
            
        SKIP)
            log "⏭️ No es creen tasques d'optimització"
            return 0
            ;;
    esac
    
    log "✅ $count tasques d'optimització creades"
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