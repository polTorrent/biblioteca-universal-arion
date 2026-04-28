# Configurar Port Forwarding per Hermes Dashboard (WSL -> Tailscale)
# Executar com a Administrador al Windows PowerShell

param(
    [string]$WSLIP = "",
    [int]$Port = 9119
)

Write-Host "=== Hermes Dashboard Port Forwarding ===" -ForegroundColor Cyan
Write-Host ""

# Si no s'ha passat IP, intentar detectar-la des de WSL
if ([string]::IsNullOrEmpty($WSLIP)) {
    Write-Host "Detectant IP de WSL..." -ForegroundColor Yellow
    $WSLIP = wsl hostname -I 2>$null
    if ($WSLIP) {
        # WSL retorna múltiples IPs, agafar la primera
        $WSLIP = $WSLIP.Split()[0].Trim()
        Write-Host "IP detectada: $WSLIP" -ForegroundColor Green
    } else {
        Write-Host "ERROR: No s'ha pogut detectar la IP de WSL" -ForegroundColor Red
        Write-Host "Passa la IP manualment: .\configurar-port-forwarding.ps1 -WSLIP 172.27.xxx.xxx" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host ""
Write-Host "Configurant port forwarding..." -ForegroundColor Yellow
Write-Host "  IP WSL: $WSLIP" -ForegroundColor Gray
Write-Host "  Port: $Port" -ForegroundColor Gray
Write-Host ""

# Eliminar configuració antiga
Write-Host "Eliminant configuracio antiga..." -ForegroundColor Gray
netsh interface portproxy delete v4tov4 listenport=$Port listenaddress=0.0.0.0 2>$null
netsh interface portproxy delete v4tov4 listenport=$Port listenaddress=127.0.0.1 2>$null

# Afegir nova configuracio
Write-Host "Afegint nova configuracio..." -ForegroundColor Gray
netsh interface portproxy add v4tov4 listenport=$Port listenaddress=0.0.0.0 connectport=$Port connectaddress=$WSLIP

if ($LASTEXITCODE -eq 0) {
    Write-Host "OK: Port forwarding configurat correctament" -ForegroundColor Green
} else {
    Write-Host "ERROR: No s'ha pogut configurar el port forwarding" -ForegroundColor Red
    exit 1
}

# Configurar firewall
Write-Host ""
Write-Host "Configurant firewall..." -ForegroundColor Yellow

$ruleName = "Hermes Dashboard WSL"
$existingRule = Get-NetFireWallRule -DisplayName $ruleName -ErrorAction SilentlyContinue

if ($existingRule) {
    Write-Host "Regla existent trobada, actualitzant..." -ForegroundColor Gray
    Remove-NetFireWallRule -DisplayName $ruleName
}

New-NetFireWallRule -Profile Private,Public -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Port | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host "OK: Firewall configurat correctament" -ForegroundColor Green
} else {
    Write-Host "WARNING: No s'ha pogut configurar el firewall" -ForegroundColor Yellow
}

# Mostrar configuracio actual
Write-Host ""
Write-Host "=== Configuracio actual ===" -ForegroundColor Cyan
netsh interface portproxy show all

Write-Host ""
Write-Host "=== Verificant connectivitat ===" -ForegroundColor Cyan

# Test local
$localTest = Test-NetConnection -ComputerName localhost -Port $Port -InformationLevel Quiet
if ($localTest) {
    Write-Host "OK: Localhost:$Port accessible" -ForegroundColor Green
} else {
    Write-Host "WARNING: Localhost:$Port no accessible (potser el dashboard no esta corrent)" -ForegroundColor Yellow
}

# Test WSL
$wslTest = Test-NetConnection -ComputerName $WSLIP -Port $Port -InformationLevel Quiet
if ($wslTest) {
    Write-Host "OK: $WSLIP:$Port accessible" -ForegroundColor Green
} else {
    Write-Host "WARNING: $WSLIP:$Port no accessible" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== IP de Tailscale ===" -ForegroundColor Cyan
$tailscaleIP = tailscale ip 2>$null
if ($tailscaleIP) {
    Write-Host "IP Tailscale: $tailscaleIP" -ForegroundColor Green
    Write-Host "Dashboard accessible via: http://$tailscaleIP:$Port" -ForegroundColor Cyan
} else {
    Write-Host "Tailscale no detectat o no corrent" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Finalitzat!" -ForegroundColor Green