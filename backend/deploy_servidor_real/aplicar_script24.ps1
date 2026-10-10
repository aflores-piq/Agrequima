<#
  Aplica en el servidor el script 24 (tabla dbo.SyncEstado) y verifica.
  Es seguro correrlo mas de una vez (solo crea la tabla si no existe y no modifica datos).
  Uso (PowerShell como administrador o con un usuario con permiso sobre PIQ_IA):
      powershell -ExecutionPolicy Bypass -File .\aplicar_script24.ps1
#>
param(
    [string]$Servidor = ".\SQLEXPRESS",
    [string]$Base     = "PIQ_IA",
    [string]$Ruta     = ""
)

# El script SQL va en la subcarpeta "sql" (paquete de publicacion) o junto a este archivo (carpeta deploy_servidor_real).
if (-not $Ruta) {
    $Ruta = Join-Path $PSScriptRoot "sql\24_sync_estado.sql"
    if (-not (Test-Path -LiteralPath $Ruta)) { $Ruta = Join-Path $PSScriptRoot "24_sync_estado.sql" }
}

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Data

function Invoke-SqlScript {
    param([System.Data.SqlClient.SqlConnection]$Conexion, [string]$Sql, [string]$Titulo)
    Write-Host ""
    Write-Host ("=" * 90) -ForegroundColor Cyan
    Write-Host (" " + $Titulo) -ForegroundColor Cyan
    Write-Host ("=" * 90) -ForegroundColor Cyan
    $handler = [System.Data.SqlClient.SqlInfoMessageEventHandler] {
        param($sender, $e)
        foreach ($m in $e.Errors) { Write-Host ("  " + $m.Message) -ForegroundColor Yellow }
    }
    $Conexion.add_InfoMessage($handler)
    try {
        $lotes = [regex]::Split($Sql, "(?im)^\s*GO\s*$") | Where-Object { $_.Trim() -ne "" }
        foreach ($lote in $lotes) {
            $cmd = $Conexion.CreateCommand()
            $cmd.CommandText = $lote
            $cmd.CommandTimeout = 0
            $da = New-Object System.Data.SqlClient.SqlDataAdapter($cmd)
            $ds = New-Object System.Data.DataSet
            [void]$da.Fill($ds)
            foreach ($tabla in $ds.Tables) {
                if ($tabla.Rows.Count -gt 0) {
                    ($tabla | Format-Table -AutoSize -Wrap | Out-String -Width 250).TrimEnd() | Write-Host
                }
            }
        }
    }
    finally { $Conexion.remove_InfoMessage($handler) }
}

$sqlVerificacion = @'
SET NOCOUNT ON;
SELECT CASE WHEN OBJECT_ID('dbo.SyncEstado', 'U') IS NOT NULL THEN 'OK' ELSE 'FALTA' END AS tabla_SyncEstado,
       (SELECT COUNT(*) FROM dbo.SyncEstado) AS procesos_registrados;
GO
'@

$codigoSalida = 0
try {
    if (-not (Test-Path -LiteralPath $Ruta)) { throw "No encuentro el script: $Ruta" }
    $sqlScript = [System.IO.File]::ReadAllText($Ruta, [System.Text.Encoding]::UTF8)

    $cs = New-Object System.Data.SqlClient.SqlConnectionStringBuilder
    $cs["Data Source"] = $Servidor; $cs["Initial Catalog"] = $Base; $cs["Integrated Security"] = $true
    $cs["Connect Timeout"] = 30; $cs["TrustServerCertificate"] = $true; $cs["Application Name"] = "aplicar_script24"
    $conexion = New-Object System.Data.SqlClient.SqlConnection($cs.ConnectionString)
    $conexion.Open()
    Write-Host ("Conectado a {0} / {1}. Aplicando {2}" -f $Servidor, $Base, $Ruta) -ForegroundColor Green

    Invoke-SqlScript -Conexion $conexion -Sql $sqlScript -Titulo "APLICANDO 24_sync_estado.sql"
    Invoke-SqlScript -Conexion $conexion -Sql $sqlVerificacion -Titulo "VERIFICACION"
    Write-Host ""
    Write-Host "LISTO: si dice OK en tabla_SyncEstado, ya se puede publicar la aplicacion (carpetas app y frontend) y copiar sync_financiero.py a la carpeta deploy." -ForegroundColor Green
}
catch {
    Write-Host ""
    Write-Host ("ERROR: " + $_.Exception.Message) -ForegroundColor Red
    $codigoSalida = 2
}
finally {
    if ($conexion) { $conexion.Close() }
}
exit $codigoSalida
