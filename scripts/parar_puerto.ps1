# Detiene el proceso que escucha en un puerto (por defecto la copia aislada, 8001).
#   powershell -File scripts/parar_puerto.ps1 8001
param([int]$Puerto = 8001)
$conexiones = Get-NetTCPConnection -LocalPort $Puerto -State Listen -ErrorAction SilentlyContinue
foreach ($c in $conexiones) {
    try { Stop-Process -Id $c.OwningProcess -Force -ErrorAction Stop; Write-Output "Detenido PID $($c.OwningProcess) en :$Puerto" } catch {}
}
