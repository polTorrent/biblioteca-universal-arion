#!/bin/bash
# iniciar-gateway-tmux.sh - Inicia el gateway i dashboard amb tmux
# Executar a l'inici de WSL
#
# 8-10-2026 — dues correccions després de veure que cada arrencada deia
# «✗ Error iniciant hermes-gateway» sense que hi hagués cap error:
#  1) El gateway NO viu a tmux: l'engega `hermes-ensure.sh` amb `nohup` a
#     l'arrencada. Obrir-hi una sessió tmux amb `hermes gateway run` feia que
#     el procés sortís de seguida («ja n'hi ha un de corrent»), la sessió
#     morís i el resum digués «✗ Error». Ara es mira el PROCÉS abans de res.
#  2) Fora `set -e`: aquest script s'executa amb `source` des del `.bashrc`,
#     i un `set -e` en una shell interactiva la fa sortir a la primera ordre
#     que falli. Les ordres que poden fallar ja porten el seu `||`.

# Funció per iniciar servei en tmux
start_in_tmux() {
    local name="$1"
    local command="$2"
    
    if tmux has-session -t "$name" 2>/dev/null; then
        echo "✓ $name ja està corrent (tmux session: $name)"
    else
        echo "Iniciant $name..."
        tmux new-session -d -s "$name" -x 120 -y 40 "$command"
        sleep 2
        if tmux has-session -t "$name" 2>/dev/null; then
            echo "✓ $name iniciat correctament"
        else
            echo "✗ Error iniciant $name"
        fi
    fi
}

echo "=== Iniciant serveis Hermes ==="
echo ""

# Iniciar dashboard
start_in_tmux "hermes-dashboard" "hermes dashboard --host 0.0.0.0 --port 9119 --no-open --insecure --tui"

# Iniciar gateway — només si no hi ha cap procés corrent
if pgrep -f "[h]ermes gateway" > /dev/null; then
    echo "✓ hermes-gateway ja està corrent (pid $(pgrep -f '[h]ermes gateway' | head -1))"
else
    start_in_tmux "hermes-gateway" "hermes gateway run"
fi

echo ""
echo "=== Estat dels serveis ==="
echo ""
echo "Dashboard:"
tmux capture-pane -t hermes-dashboard -p 2>/dev/null | tail -5 || echo "  (output no disponible)"
echo ""
echo "Gateway:"
if pgrep -f "[h]ermes gateway" > /dev/null; then
    echo "  corrent (pid $(pgrep -f '[h]ermes gateway' | head -1))"
else
    tmux capture-pane -t hermes-gateway -p 2>/dev/null | tail -5 || echo "  (no hi ha cap gateway corrent)"
fi

echo ""
echo "=== Sessions tmux actives ==="
tmux list-sessions 2>/dev/null || echo "Cap sessió activa"

echo ""
echo "=== Comandes útils ==="
echo "  tmux attach -t hermes-dashboard  # Veure dashboard"
echo "  tmux attach -t hermes-gateway     # Veure gateway"
echo "  tmux list-sessions                # Llistar sessions"
echo "  Ctrl+b d                          # Desconnectar sense aturar"
echo "  Ctrl+c                            # Aturar servei"
echo ""
echo "Per aturar tots els serveis: ./aturar-serveis-hermes.sh"