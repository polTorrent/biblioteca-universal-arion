#!/bin/bash
# obtenir-ip-wsl.sh - Obté la IP de WSL i genera comandes per configurar port forwarding
# Executar des de WSL

set -e

echo "=== Hermes Dashboard - Configuracio Port Forwarding ==="
echo ""

# Obtenir IP de WSL
WSL_IP=$(ip addr show eth0 | grep 'inet ' | awk '{print $2}' | cut -d/ -f1)

if [ -z "$WSL_IP" ]; then
    echo "ERROR: No s'ha pogut obtenir la IP de WSL"
    exit 1
fi

echo "IP de WSL detectada: $WSL_IP"
echo ""

# Obtenir IP de Tailscale del Windows (siaccessible)
echo "Intentant obtenir IP de Tailscale del Windows..."
TAILSCALE_IP="100.93.26.104"  # Valor per defecte de la memoria

echo ""
echo "=== EXECUTA AQUESTES COMANDES AL WINDOWS (PowerShell Admin) ==="
echo ""
echo "# 1. Eliminar configuracio antiga"
echo "netsh interface portproxy delete v4tov4 listenport=9119 listenaddress=0.0.0.0"
echo ""
echo "# 2. Afegir nova configuracio"
echo "netsh interface portproxy add v4tov4 listenport=9119 listenaddress=0.0.0.0 connectport=9119 connectaddress=$WSL_IP"
echo ""
echo "# 3. Configurar firewall"
echo "New-NetFireWallRule -Profile Private,Public -DisplayName 'Hermes Dashboard WSL' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 9119"
echo ""
echo "# 4. Verificar configuracio"
echo "netsh interface portproxy show all"
echo ""
echo "=== DADES D'ACCÉS ==="
echo ""
echo "Dashboard accessible via:"
echo "  - Local WSL: http://localhost:9119"
echo "  - Local Windows: http://localhost:9119"
echo "  - Tailscale: http://$TAILSCALE_IP:9119"
echo ""
echo "Si la IP de WSL canvia (reinici), torna a executar aquest script"
echo "i actualitza el port forwarding amb la nova IP."
echo ""

# Opcional: guardar la IP actual per comparar després
echo "$WSL_IP" > ~/.cache/wsl_ip_last 2>/dev/null || true

# Verificar que el dashboard està corrent
echo "=== Estat del Dashboard ==="
if ss -tlnp 2>/dev/null | grep -q ":9119" || netstat -tlnp 2>/dev/null | grep -q ":9119"; then
    echo "✓ Dashboard escoltant al port 9119"
else
    echo "⚠ Dashboard NO està escoltant al port 9119"
    echo "  Inicia'l amb: hermes dashboard --host 0.0.0.0 --port 9119 --no-open --insecure --tui &"
fi

# Verificar que el gateway està corrent
echo ""
echo "=== Estat del Gateway ==="
if hermes gateway status 2>/dev/null | grep -q "running"; then
    echo "✓ Gateway funcionant"
else
    echo "⚠ Gateway NO està funcionant"
    echo "  Inicia'l amb: hermes gateway run &"
fi