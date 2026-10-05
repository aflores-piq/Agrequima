<#
.SYNOPSIS
  Corre la sincronización de Financiero UNA vez, a mano, con el Python de
  backend\.venv, y muestra el resumen del log al terminar.

.DESCRIPTION
  Es lo mismo que hace la tarea programada de cada noche. Sirve para la
  PRIMERA carga (después de 17_copias_fieles_financiero.sql) y para
  refrescar los datos cuando haga falta.

.PARAMETER Solo
  Opcional: sincronizar solo algunos objetos, separados por coma.
  Ej.: -Solo "SaldoBancario,OtroIngreso"

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\correr_sync_financiero.ps1

.NOTES
  Va en C:\Pronostiq\Agrequima-pronostiq\deploy\ (junto a sync_financiero.py).
  Código de salida: 0 = todo OK; 1 = falló algún objeto (el resto sí se copió y el
  que falló conserva los datos del día anterior); 2 = falta configuración en el .env.
  El log del día queda en ..\logs\sync_financiero_AAAAMMDD.log
#>
param(
    [string]$Solo = "",
    [string]$Raiz = "",
    [string]$Python = ""
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
    exit 2
}
$Script = Join-Path $Deploy "sync_financiero.py"
if (-not (Test-Path $Script)) {
    Write-Host "ERROR: no encuentro $Script (¿se copió sync_financiero.py a esta carpeta?)." -ForegroundColor Red
    exit 2
}

$argumentos = @($Script)
if ($Solo) { $argumentos += @("--solo", $Solo) }

Write-Host ""
Write-Host "=== Sincronización de Financiero (cliente -> PIQ_IA) ===" -ForegroundColor Cyan
Write-Host "Inicio : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Host "Python : $Python"
Write-Host "(la copia de Presupuestos, ~128.000 filas, tarda un par de minutos; es normal)"
Write-Host ""

& $Python @argumentos | ForEach-Object {
    if ($_ -match " ERROR ") { Write-Host $_ -ForegroundColor Red }
    elseif ($_ -match " WARNING ") { Write-Host $_ -ForegroundColor Yellow }
    else { Write-Host $_ }
}
$codigo = $LASTEXITCODE

# --- Resumen del log del día (la última corrida) ---
if ($env:SYNC_FINANCIERO_LOG_DIR) { $CarpetaLog = $env:SYNC_FINANCIERO_LOG_DIR } else { $CarpetaLog = Join-Path (Split-Path -Parent $Deploy) "logs" }
$Log = Join-Path $CarpetaLog ("sync_financiero_{0:yyyyMMdd}.log" -f (Get-Date))
Write-Host ""
Write-Host "=== Resumen de la corrida (del log) ===" -ForegroundColor Cyan
if (Test-Path $Log) {
    $lineas = Get-Content $Log -Encoding UTF8
    $inicio = -1
    for ($i = 0; $i -lt $lineas.Count; $i++) { if ($lineas[$i] -match "--- Resumen ---") { $inicio = $i } }
    if ($inicio -ge 0) { $lineas[$inicio..($lineas.Count - 1)] | ForEach-Object { Write-Host $_ } }
    else { Write-Host "(el log no tiene resumen: la corrida se cortó antes de terminar; ver el log completo)" -ForegroundColor Yellow }
    Write-Host ""
    Write-Host "Log completo: $Log"
}
else {
    Write-Host "No encuentro el log del día ($Log)." -ForegroundColor Yellow
}

Write-Host ""
if ($codigo -eq 0) { if ($Solo) { Write-Host "RESULTADO: OK - quedaron sincronizados los objetos pedidos ($Solo)." -ForegroundColor Green } else { Write-Host "RESULTADO: OK - los 10 objetos quedaron sincronizados." -ForegroundColor Green } }
elseif ($codigo -eq 2) { Write-Host "RESULTADO: ERROR DE CONFIGURACIÓN - falta alguna variable en el .env (LEEME_SYNC.txt, paso 3)." -ForegroundColor Red }
else { Write-Host "RESULTADO: CON ERRORES - revisar las líneas en rojo. Lo que falló conserva los datos anteriores." -ForegroundColor Red }
exit $codigo
