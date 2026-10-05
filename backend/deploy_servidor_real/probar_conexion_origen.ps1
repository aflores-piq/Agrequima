<#
.SYNOPSIS
  Prueba, desde ESTE servidor, la conexión a CONTACC y a Agrequima (servidor del
  cliente) con las credenciales del .env y que se puedan leer los 10 objetos.
  NO copia ni modifica nada. Muestra OK o ERROR por cada cosa.
  Con -Completo prueba además la conexión a PIQ_IA y que las copias fieles tengan
  la estructura correcta (sirve después de correr 17_copias_fieles_financiero.sql).

.DESCRIPTION
  Usa el mismo código de sync_financiero.py (modo --probar), así que lee el .env
  exactamente igual que la sincronización real.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\probar_conexion_origen.ps1

.NOTES
  Va en C:\Pronostiq\Agrequima-pronostiq\deploy\ (junto a sync_financiero.py).
  Parámetros opcionales: -Raiz (carpeta de la app) y -Python (ruta de python.exe),
  solo si el servidor tiene otra distribución de carpetas.
#>
param(
    [string]$Raiz = "",
    [string]$Python = "",
    [switch]$Completo
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$Deploy = $PSScriptRoot
if (-not $Raiz) { $Raiz = Split-Path -Parent $Deploy }
if (-not $Python) {
    foreach ($candidato in @("$Raiz\backend\.venv\Scripts\python.exe", "$Deploy\..\.venv\Scripts\python.exe")) {
        if (Test-Path $candidato) { $Python = (Resolve-Path $candidato).Path; break }
    }
}
if (-not $Python) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { $Python = $cmd.Source }
}
if (-not $Python -or -not (Test-Path $Python)) {
    Write-Host "ERROR: no encuentro python.exe. Esperaba $Raiz\backend\.venv\Scripts\python.exe" -ForegroundColor Red
    Write-Host "       Pasar la ruta con -Python 'C:\ruta\python.exe'." -ForegroundColor Red
    exit 2
}
$Script = Join-Path $Deploy "sync_financiero.py"
if (-not (Test-Path $Script)) {
    Write-Host "ERROR: no encuentro $Script (¿se copió sync_financiero.py a esta carpeta?)." -ForegroundColor Red
    exit 2
}

Write-Host ""
if ($Completo) { $modo = "--probar-completo"; Write-Host "=== Probando conexión al origen (cliente) y al destino (PIQ_IA) ===" -ForegroundColor Cyan }
else { $modo = "--probar"; Write-Host "=== Probando conexión al origen (servidor del cliente) ===" -ForegroundColor Cyan }
Write-Host "Python : $Python"
Write-Host "Script : $Script"
Write-Host ""

& $Python $Script $modo | ForEach-Object {
    if ($_ -match " ERROR ") { Write-Host $_ -ForegroundColor Red }
    elseif ($_ -match " OK ") { Write-Host $_ -ForegroundColor Green }
    else { Write-Host $_ }
}
$codigo = $LASTEXITCODE

Write-Host ""
if ($codigo -eq 0) {
    if ($Completo) { Write-Host "RESULTADO: OK - se puede conectar al cliente y las copias de PIQ_IA están bien." -ForegroundColor Green }
    else { Write-Host "RESULTADO: OK - este servidor puede conectarse a CONTACC y a Agrequima y leer los 10 objetos." -ForegroundColor Green }
}
elseif ($codigo -eq 2) {
    Write-Host "RESULTADO: ERROR DE CONFIGURACIÓN - falta alguna variable en el .env (ver LEEME_SYNC.txt, paso 3)." -ForegroundColor Red
}
else {
    Write-Host "RESULTADO: ERROR - revisar las líneas en rojo de arriba." -ForegroundColor Red
    Write-Host "  - 'Login failed' / 'Error de inicio de sesión'  -> usuario o contraseña incorrectos en el .env."
    Write-Host "  - 'timeout' / 'no se encontró el servidor' / 'TCP Provider'  -> este servidor no llega a 10.10.0.6,65280 (VPN o firewall)."
    Write-Host "  - (solo con -Completo) 'No existe dbo.<tabla> en PIQ_IA' / 'estructura ... no es la esperada'  -> falta correr 17_copias_fieles_financiero.sql."
    Write-Host "  - 'Invalid object name' en el origen  -> el cliente cambió o renombró esa vista; avisar."
}
exit $codigo
