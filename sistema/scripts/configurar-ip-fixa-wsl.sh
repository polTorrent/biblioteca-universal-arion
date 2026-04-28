#!/bin/bash
# configurar-ip-fixa-wsl.sh - Configura una IP fixa per a WSL
# Així evita que canviï cada copque es reinicia

set -e

echo "=== Configurar IP Fixa per WSL ==="
echo ""

# Detectar la xarxa actual deWSL
CURRENT_IP=$(ip addr show eth0 | grep 'inet ' | awk '{print $2}' | cut -d/ -f1)
GATEWAY=$(ip route | grep default | awk '{print $3}')
DNS=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}' | head -1)

echo "Configuracio actual:"
echo "  IP: $CURRENT_IP"
echo "  Gateway: $GATEWAY"
echo "  DNS: $DNS"
echo ""

# Calcular una IP fixa (agafem la mateixa que tenim ara)
FIXED_IP="$CURRENT_IP"

echo "IP fixa proposta: $FIXED_IP"
echo ""

# Crear backup de wsl.conf si existeix
if [ -f /etc/wsl.conf ]; then
    echo "Copiadeseguretat de /etc/wsl.conf"
    sudo cp /etc/wsl.conf /etc/wsl.conf.backup
fi

# Crear/modificar wsl.conf
echo "Configurant /etc/wsl.conf..."
sudo tee/etc/wsl.conf > /dev/null << EOF
[network]
generateResolvConf = false

[boot]
systemd = true
EOF

echo "OK: wsl.conf configurat"
echo ""

# Ara cal configurar la IP manualment
# NOTA: Per una IP realment fixa, caldria configurar el switch de Hyper-V al Windows

echo "=== PROPER PAS : Configurar al Windows ==="
echo ""
echo "Per tenir una IP realment fixa, executa a PowerShell (Admin):"
echo ""
echo "# Veure adaptadors WSL"
echo "Get-NetAdapter -Name 'vEthernet (WSL)' -ErrorAction SilentlyContinue"
echo ""
echo "# Si vols IP fixa constant, considera usar Windows Terminal"
echo "# i executar WSL siempre con la misma configuracion."
echo ""
echo "=== ALTERNATIVA: Script d'inici automatizat ==="
echo ""
echo "Pots crear una tasca al Windows que executi aquest script"
echo "a l'inici per actualitzar automaticament el port forwarding:"
echo ""
echo "1. Obre 'Task Scheduler' al Windows"
echo "2. Crea una nova tasca: 'Hermes Port Forward'"
echo "3. Trigger: 'At startup' o 'On workstation unlock'"
echo "4. Action: Start a program"
echo "   Program: powershell.exe"
echo "   Arguments: -ExecutionPolicy Bypass -File \"\\\\wsl\$\\$(cat /etc/os-release | grep ID | cut -d= -f2)\\home\\$(whoami)\\biblioteca-universal-arion\\sistema\\scripts\\configurar-port-forwarding.ps1\""
echo ""

# Creu script per actualitzar la IP al fitxer de configuració
echo "$FIXED_IP" > ~/.hermes/wsl_ip_fixed 2>/dev/null || true

echo "=== Resum ==="
echo ""
echo "Scripts creats:"
echo "  1. obtenir-ip-wsl.sh - Mostra comandes perconfigurar port forwarding"
echo "  2. configurar-port-forwarding.ps1 - Script PowerShell per al Windows"
echo ""
echo "Per configurar ara:"
echo "  1. Obre PowerShell com a Administrador al Windows"
echo "  2. Executa: netsh interface portproxy add v4tov4 listenport=9119 listenaddress=0.0.0.0 connectport=9119 connectaddress=$FIXED_IP"
echo "  3. Afegeix la regla del firewall"
echo ""
echo "Després d'això, el dashboard sera accessible via:"
echo "  http://100.93.26.104:9119"