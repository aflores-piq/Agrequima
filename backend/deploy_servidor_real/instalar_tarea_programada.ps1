<#
.SYNOPSIS
  Crea la tarea programada de Windows "PIQ_IA_Sync_Financiero": corre la
  sincronización de Financiero todos los días a las 2:00 a. m., AUNQUE NO HAYA
  NINGUNA SESIÓN INICIADA en el servidor.

.DESCRIPTION
  La tarea corre como la cuenta SYSTEM (no necesita contraseña de usuario) y llama
  directamente a python.exe de backend\.venv con sync_financiero.py. Las
  credenciales de SQL salen del .env, no de la tarea.
  Si la tarea ya existe, la reemplaza (se puede correr de nuevo sin problema).

.PARAMETER SoloMostrar
  No crea nada: solo muestra qué crearía (para revisar antes).

.PARAMETER Desinstalar
  Borra la tarea.

.EXAMPLE
  # PowerShell abierto "Como administrador":
  powershell -ExecutionPolicy Bypass -File .\instalar_tarea_programada.ps1

.NOTES
  Va en C:\Pronostiq\Agrequima-pronostiq\deploy\ (junto a sync_financiero.py).
  REQUIERE PowerShell como Administrador (salvo con -SoloMostrar).
#>
param(
    [string]$NombreTarea = "PIQ_IA_Sync_Financiero",
    [string]$Hora = "02:00",
    [string]$Raiz = "",
    [string]$Python = "",
    [switch]$SoloMostrar,
    [switch]$Desinstalar
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$Deploy = $PSScriptRoot
if (-not $Raiz) { $Raiz = Split-Path -Parent $Deploy }

function Mostrar-Comandos {
    Write-Host ""
    Write-Host "Cómo manejar la tarea (en un PowerShell, algunos requieren 'Como administrador'):" -ForegroundColor Cyan
    Write-Host "  Ver estado y último resultado :  Get-ScheduledTask -TaskName $NombreTarea | Get-ScheduledTaskInfo"
    Write-Host "      (LastTaskResult = 0 significa que la última corrida salió OK; 1 = falló alguna vista)"
    Write-Host "  Correrla a mano ahora         :  Start-ScheduledTask -TaskName $NombreTarea"
    Write-Host "  Desactivarla (sin borrarla)   :  Disable-ScheduledTask -TaskName $NombreTarea"
    Write-Host "  Volver a activarla            :  Enable-ScheduledTask -TaskName $NombreTarea"
    Write-Host "  Borrarla                      :  powershell -ExecutionPolicy Bypass -File .\instalar_tarea_programada.ps1 -Desinstalar"
    Write-Host "  También se ve en 'Programador de tareas' (taskschd.msc), en la raíz de la Biblioteca."
    Write-Host "  El log de cada día está en: $(Join-Path $Raiz 'logs')\sync_financiero_AAAAMMDD.log"
}

if ($Desinstalar) {
    $tarea = Get-ScheduledTask -TaskName $NombreTarea -ErrorAction SilentlyContinue
    if ($tarea) {
        Unregister-ScheduledTask -TaskName $NombreTarea -Confirm:$false
        Write-Host "Tarea '$NombreTarea' borrada." -ForegroundColor Green
    }
    else {
        Write-Host "La tarea '$NombreTarea' no existe; no hay nada que borrar."
    }
    exit 0
}

if (-not $Python) {
    foreach ($candidato in @("$Raiz\backend\.venv\Scripts\python.exe", "$Deploy\..\.venv\Scripts\python.exe")) {
        if (Test-Path $candidato) { $Python = (Resolve-Path $candidato).Path; break }
    }
}
if (-not $Python -or -not (Test-Path $Python)) {
    Write-Host "ERROR: no encuentro python.exe. Esperaba $Raiz\backend\.venv\Scripts\python.exe" -ForegroundColor Red
    exit 2
}
$Script = Join-Path $Deploy "sync_financiero.py"
if (-not (Test-Path $Script)) {
    Write-Host "ERROR: no encuentro $Script" -ForegroundColor Red
    exit 2
}
try { $cuando = [datetime]::ParseExact($Hora, "HH:mm", $null) }
catch { Write-Host "ERROR: -Hora debe tener formato HH:mm (ej. 02:00)." -ForegroundColor Red; exit 2 }

$accion = New-ScheduledTaskAction -Execute $Python -Argument ('"{0}"' -f $Script) -WorkingDirectory $Deploy
$disparador = New-ScheduledTaskTrigger -Daily -At $cuando
$configuracion = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 3) `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

Write-Host ""
Write-Host "=== Tarea programada de la sincronización de Financiero ===" -ForegroundColor Cyan
Write-Host "Nombre        : $NombreTarea"
Write-Host "Se ejecuta    : todos los días a las $Hora (aunque no haya sesión iniciada)"
Write-Host "Cuenta        : SYSTEM (privilegios más altos)"
Write-Host "Programa      : $Python"
Write-Host "Argumentos    : `"$Script`""
Write-Host "Si el servidor estaba apagado a esa hora: corre apenas arranque (StartWhenAvailable)."
Write-Host "Si ya hay una corrida en curso: no lanza otra (IgnoreNew). Límite de duración: 3 horas."

if ($SoloMostrar) {
    Write-Host ""
    Write-Host "(-SoloMostrar: NO se creó nada.)" -ForegroundColor Yellow
    Mostrar-Comandos
    exit 0
}

$esAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $esAdmin) {
    Write-Host ""
    Write-Host "ERROR: hay que abrir PowerShell con 'Ejecutar como administrador' para crear la tarea." -ForegroundColor Red
    exit 3
}

$existia = [bool](Get-ScheduledTask -TaskName $NombreTarea -ErrorAction SilentlyContinue)
Register-ScheduledTask -TaskName $NombreTarea -Action $accion -Trigger $disparador -Settings $configuracion `
    -Principal $principal -Description "PIQ_IA: copia cada noche las 8 vistas de CONTACC de Financiero (sync_financiero.py). Ver LEEME_SYNC.txt." -Force | Out-Null

$info = Get-ScheduledTask -TaskName $NombreTarea
Write-Host ""
if ($existia) { Write-Host "Tarea '$NombreTarea' REEMPLAZADA. Estado: $($info.State)" -ForegroundColor Green }
else { Write-Host "Tarea '$NombreTarea' CREADA. Estado: $($info.State)" -ForegroundColor Green }
Mostrar-Comandos
exit 0
