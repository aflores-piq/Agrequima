<#
.SYNOPSIS
  Revisión exhaustiva (SOLO LECTURA) de los datos del módulo Financiero en PIQ_IA.

.DESCRIPTION
  Hace 4 revisiones y muestra todo en pantalla (y lo guarda en un archivo):
    1. ORIGEN vs COPIA   : CONTACC (cliente) contra las 8 copias fieles de PIQ_IA.
    2. COPIA vs VISTA    : cada copia fiel contra la vista que lee la web.
    3. RESPALDO vs VISTA : los datos verificados de la semana pasada (tablas *_respaldo)
                           contra la vista que lee la web  (la revisión más importante).
    4. EXCEL             : SaldoBancario y OtroIngreso (solo informativo).

  NO MODIFICA NADA: solo ejecuta consultas SELECT. Cada consulta pasa por una guarda
  que se niega a ejecutar cualquier cosa que no empiece con SELECT/WITH o que contenga
  INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, MERGE, EXEC, INTO, etc.
  Lo único que escribe es el archivo de reporte en la carpeta de logs.

.PARAMETER ServidorPIQ
  Servidor SQL de PIQ_IA. Por defecto DB_SERVER del .env (si no está: <esta PC>\SQLEXPRESS).
.PARAMETER BasePIQ
  Base de datos. Por defecto DB_NAME del .env (si no está: PIQ_IA).
.PARAMETER AutenticacionSql
  Por defecto se conecta a PIQ_IA con Integrated Security (la cuenta de Windows con la que
  se corre el script). Con este interruptor usa DB_USER/DB_PASSWORD del .env.
.PARAMETER EnvFile
  Ruta del .env (default: ..\.env, o sea C:\Pronostiq\Agrequima-pronostiq\.env).
.PARAMETER CarpetaLog
  Dónde guardar el reporte (default: ..\logs).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\verificar_datos_financiero.ps1

.NOTES
  Va en C:\Pronostiq\Agrequima-pronostiq\deploy\ . Código de salida: 0 = OK, 1 = REVISAR,
  2 = no pudo conectarse o falta configuración.
#>
param(
    [string]$Raiz = "",
    [string]$EnvFile = "",
    [string]$ServidorPIQ = "",
    [string]$BasePIQ = "",
    [switch]$AutenticacionSql,
    [string]$CarpetaLog = ""
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Data

$Deploy = $PSScriptRoot
if (-not $Raiz) { $Raiz = Split-Path -Parent $Deploy }
if (-not $EnvFile) { $EnvFile = Join-Path $Raiz ".env" }
if (-not $CarpetaLog) { $CarpetaLog = Join-Path $Raiz "logs" }
$Inicio = Get-Date
$inv = [Globalization.CultureInfo]::InvariantCulture

# ----------------------------------------------------------------------------
# Salida: pantalla + archivo
# ----------------------------------------------------------------------------
$script:Reporte = New-Object System.Collections.ArrayList
function W([string]$texto = "", [string]$color = "") {
    [void]$script:Reporte.Add($texto)
    if ($color) { Write-Host $texto -ForegroundColor $color } else { Write-Host $texto }
}
function Titulo([string]$texto) {
    W ""; W ("=" * 100) "Cyan"; W (" " + $texto) "Cyan"; W ("=" * 100) "Cyan"
}
function Subtitulo([string]$texto) { W ""; W ("--- " + $texto + " ---") "Yellow" }
function Tabla($objetos) {
    $filas = @($objetos)
    if ($filas.Count -eq 0) { W "  (sin filas)"; return }
    $txt = ($filas | Format-Table -AutoSize | Out-String -Width 250).TrimEnd()
    foreach ($l in ($txt -split "`r?`n")) { W $l }
}
function N0($x) { if ($null -eq $x -or $x -is [DBNull]) { return "-" }; return [string]::Format($inv, "{0:N0}", [decimal]$x) }
function N2($x) { if ($null -eq $x -or $x -is [DBNull]) { return "-" }; return [string]::Format($inv, "{0:N2}", [decimal]$x) }
function Dec($x) { if ($null -eq $x -or $x -is [DBNull]) { return [decimal]0 }; return [decimal]$x }
function Txt($x) {
    if ($null -eq $x -or $x -is [DBNull]) { return "NULL" }
    if ($x -is [datetime]) { return $x.ToString("yyyy-MM-dd HH:mm:ss") }
    if ($x -is [decimal] -or $x -is [double]) { return (N2 $x) }
    return [string]$x
}

# ----------------------------------------------------------------------------
# .env (sin mostrar nunca la contraseña)
# ----------------------------------------------------------------------------
function Leer-Env([string]$ruta) {
    $d = @{}
    foreach ($l in Get-Content -LiteralPath $ruta -Encoding UTF8) {
        $t = $l.Trim()
        if (-not $t -or $t.StartsWith("#")) { continue }
        $i = $t.IndexOf("=")
        if ($i -lt 1) { continue }
        $k = $t.Substring(0, $i).Trim(); $v = $t.Substring($i + 1).Trim()
        if ($v.StartsWith("'") -or $v.StartsWith('"')) {
            $q = $v[0]; $f = $v.IndexOf($q, 1)
            if ($f -gt 0) { $v = $v.Substring(1, $f - 1) }
        }
        else {
            $c = $v.IndexOf(" #")
            if ($c -ge 0) { $v = $v.Substring(0, $c).Trim() }
        }
        $d[$k] = $v
    }
    return $d
}

# ----------------------------------------------------------------------------
# Conexión y GUARDA DE SOLO LECTURA
# ----------------------------------------------------------------------------
$script:Consultas = New-Object System.Collections.ArrayList

function Abrir-Conexion([string]$servidor, [string]$base, [bool]$integrada, [string]$usuario, [string]$clave) {
    $b = New-Object System.Data.SqlClient.SqlConnectionStringBuilder
    $b["Data Source"] = $servidor
    $b["Initial Catalog"] = $base
    $b["Connect Timeout"] = 20
    $b["Application Name"] = "verificar_datos_financiero (solo lectura)"
    $b["TrustServerCertificate"] = $true
    if ($integrada) { $b["Integrated Security"] = $true } else { $b["User ID"] = $usuario; $b["Password"] = $clave }
    $c = New-Object System.Data.SqlClient.SqlConnection($b.ConnectionString)
    $c.Open()
    return $c
}

function Invoke-Consulta($conn, [string]$sql, [hashtable]$p = @{}) {
    $limpio = ($sql -replace "(?s)/\*.*?\*/", "" -replace "--[^\r\n]*", "").Trim()
    if ($limpio -notmatch "^(?i)(SELECT|WITH)\b") {
        throw "BLOQUEADO (solo lectura): esta consulta no empieza con SELECT/WITH: $limpio"
    }
    if ($limpio -match "(?i)\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|MERGE|EXEC|EXECUTE|GRANT|REVOKE|DENY|BACKUP|RESTORE|DBCC|SHUTDOWN|INTO|SET|USE)\b") {
        throw "BLOQUEADO (solo lectura): la consulta contiene una palabra de modificación ($($Matches[1])): $limpio"
    }
    $cmd = $conn.CreateCommand()
    $cmd.CommandText = $sql
    $cmd.CommandTimeout = 900
    foreach ($k in $p.Keys) {
        $v = $p[$k]
        if ($null -eq $v) { $v = [DBNull]::Value }
        [void]$cmd.Parameters.AddWithValue("@$k", $v)
    }
    $dt = New-Object System.Data.DataTable
    $da = New-Object System.Data.SqlClient.SqlDataAdapter($cmd)
    [void]$da.Fill($dt)
    [void]$script:Consultas.Add($limpio)
    return , $dt
}

function Columnas($conn, [string]$tabla) {
    $dt = Invoke-Consulta $conn "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = @t ORDER BY ORDINAL_POSITION" @{ t = $tabla }
    $res = @()
    foreach ($r in $dt.Rows) { $res += , @($r["COLUMN_NAME"], $r["DATA_TYPE"]) }
    return , $res
}

function Es-Texto([string]$tipo) { return (@("varchar", "nvarchar", "char", "nchar") -contains $tipo.ToLower()) }
function Expr-Col([string]$col, [string]$tipo, [string]$alias = "") {
    $e = "[$col]"
    if (Es-Texto $tipo) { $e = "[$col] COLLATE Latin1_General_BIN2" }
    return $e
}

# ----------------------------------------------------------------------------
# Definición de las 8 tablas
# ----------------------------------------------------------------------------
$Tablas = @(
    @{ Vista = "BalanceSaldos"; Copia = "vw_piq_balance_saldos"; Respaldo = "BalanceSaldos_respaldo"
       Importes = @("Debitos", "Creditos", "Saldo"); Anio = "Sal_Ano"; Mes = "Sal_Mes"
       Clave = @("emp_nit", "Cta_Codigo", "Sal_Ano", "Sal_Mes", "Cod_Centro"); Agrupada = $false },
    @{ Vista = "BalanceGeneral"; Copia = "vw_piq_balance_general"; Respaldo = "BalanceGeneral_respaldo"
       Importes = @("Debitos", "Creditos", "Saldo", "Inicial"); Anio = "Sal_Ano"; Mes = "Sal_Mes"
       Clave = @("emp_nit", "cod_n5", "Sal_Ano", "Sal_Mes"); Agrupada = $false },
    @{ Vista = "CatalogoCuentas"; Copia = "vw_catalogo_cuentas"; Respaldo = "CatalogoCuentas_respaldo"
       Importes = @(); Anio = ""; Mes = ""
       Clave = @("Codigo_N1", "Codigo_N5"); Agrupada = $false },
    @{ Vista = "CentrosDeCosto"; Copia = "vw_piq_centrosdecosto"; Respaldo = "CentrosDeCosto_respaldo"
       Importes = @(); Anio = ""; Mes = ""
       Clave = @("emp_nit", "Cod_centro"); Agrupada = $false },
    @{ Vista = "Presupuestos"; Copia = "vw_piq_presupuestos"; Respaldo = "Presupuestos_respaldo"
       Importes = @("pre_presupuesto"); Anio = "par_ano"; Mes = "par_mes"
       Clave = @("emp_nit", "par_ano", "par_mes", "cta_codigo", "cod_centro"); Agrupada = $false },
    @{ Vista = "AsociadosCuota"; Copia = "vw_piq_asociados_cuota"; Respaldo = "AsociadosCuota_respaldo"
       Importes = @("cuota"); Anio = "Sal_Ano"; Mes = ""
       Clave = @("emp_nit", "Sal_Ano", "cod_n5"); Agrupada = $false },
    @{ Vista = "ChequesCirculacion"; Copia = "vw_piq_cheques_circulacion"; Respaldo = "ChequesCirculacion_respaldo"
       Importes = @("doc_monto"); Anio = "par_ano"; Mes = "par_mes"
       Clave = @("ban_codigo", "cta_numero", "par_ano", "par_mes", "doc_numero"); Agrupada = $false },
    @{ Vista = "SaldosBancos"; Copia = "vw_piq_saldos_bancos"; Respaldo = "SaldosBancos_respaldo"
       Importes = @("InicialL", "EntradasL", "SalidasL", "FinalL"); Anio = "Sal_Ano"; Mes = "Sal_Mes"
       Clave = @("ban_codigo", "Sal_Mes", "Sal_Ano"); Agrupada = $true }
)

function Periodo-Texto($num) {
    $a = [int][math]::Floor($num / 100); $m = [int]($num % 100)
    if ($m -eq 0) { return "$a" }
    return ("{0}-{1:00}" -f $a, $m)
}

function Guardar-Reporte {
    try {
        if (-not (Test-Path -LiteralPath $CarpetaLog)) { New-Item -ItemType Directory -Path $CarpetaLog -Force | Out-Null }
        $archivo = Join-Path $CarpetaLog ("verificacion_financiero_{0:yyyyMMdd_HHmm}.txt" -f $Inicio)
        [System.IO.File]::WriteAllLines($archivo, [string[]]$script:Reporte.ToArray(), (New-Object System.Text.UTF8Encoding($true)))
        Write-Host ""
        Write-Host "Reporte guardado en: $archivo"
    }
    catch { Write-Host "No se pudo guardar el reporte: $($_.Exception.Message)" -ForegroundColor Yellow }
}

# Cualquier error inesperado que no se haya atrapado más abajo: se informa, se guarda el reporte y se sale con código 2.
trap {
    W ""
    W "ERROR INESPERADO: $($_.Exception.Message)" "Red"
    W "El reporte quedó incompleto. Copiar este mensaje y el archivo del reporte para revisarlo." "Red"
    Guardar-Reporte
    exit 2
}

# ----------------------------------------------------------------------------
# Resultados (para el resumen final)
# ----------------------------------------------------------------------------
$Res1 = @{}; $Res2 = @{}; $Res3 = @{}
$Notas1 = @{}; $Notas2 = @{}; $Notas3 = @{}
$Pendientes = New-Object System.Collections.ArrayList

# ============================================================================
#  ENCABEZADO Y CONEXIONES
# ============================================================================
W ("=" * 100) "Cyan"
W " VERIFICACIÓN DE DATOS DEL MÓDULO FINANCIERO (solo lectura)" "Cyan"
W ("=" * 100) "Cyan"
W ("Fecha y hora   : " + $Inicio.ToString("yyyy-MM-dd HH:mm:ss"))
W ("Equipo / cuenta: " + $env:COMPUTERNAME + " / " + $env:USERDOMAIN + "\" + $env:USERNAME)

if (-not (Test-Path -LiteralPath $EnvFile)) {
    W "ERROR: no encuentro el archivo .env en $EnvFile (usar -EnvFile para indicar otra ruta)." "Red"
    exit 2
}
$envv = Leer-Env $EnvFile
foreach ($v in @("SYNC_CONTACC_DB_SERVER", "SYNC_CONTACC_DB_USER", "SYNC_CONTACC_DB_PASSWORD")) {
    if (-not $envv[$v]) { W "ERROR: falta $v en $EnvFile (ver LEEME_SYNC.txt, paso 3)." "Red"; exit 2 }
}
if (-not $ServidorPIQ) { if ($envv["DB_SERVER"]) { $ServidorPIQ = $envv["DB_SERVER"] } else { $ServidorPIQ = "$($env:COMPUTERNAME)\SQLEXPRESS" } }
if (-not $BasePIQ) { if ($envv["DB_NAME"]) { $BasePIQ = $envv["DB_NAME"] } else { $BasePIQ = "PIQ_IA" } }
$srvOrigen = $envv["SYNC_CONTACC_DB_SERVER"]
$dbOrigen = if ($envv["SYNC_CONTACC_DB_NAME"]) { $envv["SYNC_CONTACC_DB_NAME"] } else { "CONTACC" }

W ("Destino (PIQ_IA): " + $ServidorPIQ + " / base " + $BasePIQ + $(if ($AutenticacionSql) { "  [usuario SQL del .env]" } else { "  [Integrated Security]" }))
W ("Origen (cliente): " + $srvOrigen + " / base " + $dbOrigen + "  [usuario " + $envv["SYNC_CONTACC_DB_USER"] + ", contraseña no se muestra]")
W ".env            : $EnvFile"

try {
    if ($AutenticacionSql) {
        if (-not $envv["DB_USER"]) { W "ERROR: -AutenticacionSql pide DB_USER/DB_PASSWORD en el .env." "Red"; exit 2 }
        $piq = Abrir-Conexion $ServidorPIQ $BasePIQ $false $envv["DB_USER"] $envv["DB_PASSWORD"]
    }
    else { $piq = Abrir-Conexion $ServidorPIQ $BasePIQ $true "" "" }
}
catch {
    W "ERROR: no se pudo conectar a PIQ_IA ($ServidorPIQ / $BasePIQ): $($_.Exception.Message)" "Red"
    W "       Si la cuenta de Windows no tiene permiso, probar con -AutenticacionSql (usa DB_USER/DB_PASSWORD del .env)." "Red"
    exit 2
}
try { $cx = Abrir-Conexion $srvOrigen $dbOrigen $false $envv["SYNC_CONTACC_DB_USER"] $envv["SYNC_CONTACC_DB_PASSWORD"] }
catch {
    W "ERROR: no se pudo conectar a CONTACC ($srvOrigen / $dbOrigen): $($_.Exception.Message)" "Red"
    W "       Sin esa conexión solo se pueden hacer las revisiones 2, 3 y 4 (todo dentro de PIQ_IA); la revisión 1 se omite." "Red"
    $cx = $null
}

# Última sincronización registrada en los logs
$ultimaSync = "no se encontró ningún log de sincronización en $CarpetaLog"
try {
    $logs = Get-ChildItem -LiteralPath $CarpetaLog -Filter "sync_financiero_*.log" -ErrorAction Stop | Sort-Object Name -Descending
    foreach ($lg in $logs) {
        $fin = Get-Content -LiteralPath $lg.FullName -Encoding UTF8 | Where-Object { $_ -match "=== FIN sincronización Financiero" } | Select-Object -Last 1
        if ($fin) { $ultimaSync = "$($lg.Name): $fin"; break }
    }
}
catch { }
W ("Última sincronización registrada: " + $ultimaSync)

# ============================================================================
#  REVISIÓN 1: ORIGEN (CONTACC) vs COPIA (PIQ_IA)
# ============================================================================
Titulo "REVISIÓN 1 de 4 - ORIGEN (CONTACC, cliente) contra COPIA FIEL (PIQ_IA)"
W "Qué se compara: filas, suma de los importes, tamaño total en bytes del contenido y un checksum de TODO el"
W "contenido (CHECKSUM_AGG de BINARY_CHECKSUM por fila). Si coinciden, la copia es idéntica al origen."

if ($null -eq $cx) {
    W "No hay conexión a CONTACC: esta revisión se omite." "Red"
    foreach ($t in $Tablas) { $Res1[$t.Vista] = "REVISAR"; $Notas1[$t.Vista] = "sin conexión a CONTACC" ; [void]$Pendientes.Add("1 · $($t.Vista): no se pudo conectar a CONTACC") }
}
else {
    $tabResumen = @(); $tabImportes = @(); $tabPeriodos = @()
    foreach ($t in $Tablas) {
      try {
        $cols = Columnas $piq $t.Copia
        if ($cols.Count -eq 0) { $Res1[$t.Vista] = "REVISAR"; $Notas1[$t.Vista] = "no existe dbo.$($t.Copia) en PIQ_IA"; [void]$Pendientes.Add("1 · $($t.Vista): no existe la copia dbo.$($t.Copia)"); continue }
        $bytes = ($cols | ForEach-Object { "ISNULL(CAST(DATALENGTH([$($_[0])]) AS BIGINT), -1)" }) -join " + "
        $sumas = @($t.Importes | ForEach-Object { "SUM(CAST([$_] AS DECIMAL(38,4))) AS [s_$_]" })
        $listaTot = @("COUNT_BIG(*) AS filas") + $sumas + @("SUM($bytes) AS bytes", "CHECKSUM_AGG(BINARY_CHECKSUM(*)) AS ck")
        $sqlTot = "SELECT " + ($listaTot -join ", ") + " FROM dbo.[$($t.Copia)]"
        $tieneP = [bool]$t.Anio
        $o = (Invoke-Consulta $cx $sqlTot).Rows[0]
        $c = (Invoke-Consulta $piq $sqlTot).Rows[0]
        $iguales = ($o["filas"] -eq $c["filas"]) -and ([string]$o["ck"] -eq [string]$c["ck"]) -and ([string]$o["bytes"] -eq [string]$c["bytes"])
        foreach ($imp in $t.Importes) { if ((Dec $o["s_$imp"]) -ne (Dec $c["s_$imp"])) { $iguales = $false } }

        $nota = ""
        $estado = "OK"
        if (-not $iguales) {
            $estado = "REVISAR"
            $nota = "origen y copia NO coinciden"
            # Análisis fila por fila: BINARY_CHECKSUM de cada fila, contado por período, en ambos lados
            $anioSel = "0"; $mesSel2 = "0"
            if ($tieneP) { $anioSel = "[$($t.Anio)]"; if ($t.Mes) { $mesSel2 = "[$($t.Mes)]" } }
            $sqlH = "SELECT h, anio, mes, COUNT_BIG(*) AS n FROM (SELECT BINARY_CHECKSUM(*) AS h, $anioSel AS anio, $mesSel2 AS mes FROM dbo.[$($t.Copia)]) x GROUP BY h, anio, mes"
            $ho = Invoke-Consulta $cx $sqlH; $hc = Invoke-Consulta $piq $sqlH
            $dO = @{}; $dC = @{}
            foreach ($r in $ho.Rows) { $dO["$($r['h'])|$($r['anio'])|$($r['mes'])"] = [int64]$r["n"] }
            foreach ($r in $hc.Rows) { $dC["$($r['h'])|$($r['anio'])|$($r['mes'])"] = [int64]$r["n"] }
            $maxCopia = 0
            foreach ($k in $dC.Keys) { $pp = $k.Split("|"); $num = [int]$pp[1] * 100 + [int]$pp[2]; if ($num -gt $maxCopia) { $maxCopia = $num } }
            $soloOrigen = @{}; $soloCopia = @{}
            foreach ($k in (@($dO.Keys) + @($dC.Keys) | Sort-Object -Unique)) {
                $a = 0; $b = 0
                if ($dO.ContainsKey($k)) { $a = $dO[$k] }
                if ($dC.ContainsKey($k)) { $b = $dC[$k] }
                $pp = $k.Split("|"); $num = [int]$pp[1] * 100 + [int]$pp[2]
                if ($a -gt $b) { $soloOrigen[$num] = [int64]$soloOrigen[$num] + ($a - $b) }
                elseif ($b -gt $a) { $soloCopia[$num] = [int64]$soloCopia[$num] + ($b - $a) }
            }
            $totOrigen = 0; foreach ($v in $soloOrigen.Values) { $totOrigen += $v }
            $totCopia = 0; foreach ($v in $soloCopia.Values) { $totCopia += $v }
            $periodos = @(@($soloOrigen.Keys) + @($soloCopia.Keys) | Sort-Object -Unique)
            foreach ($k in $periodos) {
                $etq = "(toda la tabla)"
                if ($tieneP) { $etq = Periodo-Texto $k }
                $pos = "-"
                if ($tieneP) { if ($k -ge $maxCopia) { $pos = "reciente (>= último período de la copia)" } else { $pos = "ANTERIOR al último período de la copia" } }
                $tabPeriodos += [pscustomobject][ordered]@{ Tabla = $t.Vista; Período = $etq; "Filas solo en CONTACC" = (N0 $soloOrigen[$k]); "Filas solo en la copia" = (N0 $soloCopia[$k]); Posición = $pos }
            }
            $listaPer = ($periodos | ForEach-Object { if ($tieneP) { Periodo-Texto $_ } else { "toda la tabla" } }) -join ", "
            $copiaAntiguas = @($soloCopia.Keys | Where-Object { $tieneP -and $_ -lt $maxCopia })
            if ($totOrigen -eq 0 -and $totCopia -eq 0) {
                $nota = "los totales difieren pero no se pudo ubicar la diferencia fila por fila (revisar a mano)"
            }
            elseif ($totCopia -eq 0) {
                $estado = "OK"
                $nota = "AVISO: la contabilidad AGREGÓ $(N0 $totOrigen) filas después de la última sincronización (períodos: $listaPer). La copia no tiene nada de más ni cambiado. Se incorporan en la próxima corrida de las 2:00 a. m."
            }
            elseif ($tieneP -and $copiaAntiguas.Count -eq 0) {
                $estado = "OK"
                $nota = "AVISO: la contabilidad cambió datos del período más reciente después de la última sincronización (períodos: $listaPer). Se actualizan en la próxima corrida de las 2:00 a. m."
            }
            else {
                $nota = "la copia tiene $(N0 $totCopia) filas que ya no están así en CONTACC (períodos: $listaPer). O la contabilidad cambió datos cerrados, o la copia está dañada: correr la sincronización a mano y repetir esta verificación."
            }
        }
        $Res1[$t.Vista] = $estado; $Notas1[$t.Vista] = $nota
        if ($estado -eq "REVISAR") { [void]$Pendientes.Add("1 · $($t.Vista): $nota") }

        $tabResumen += [pscustomobject][ordered]@{
            Tabla = $t.Vista; "Filas CONTACC" = (N0 $o["filas"]); "Filas copia" = (N0 $c["filas"])
            "Bytes CONTACC" = (N0 $o["bytes"]); "Bytes copia" = (N0 $c["bytes"])
            "Checksum CONTACC" = [string]$o["ck"]; "Checksum copia" = [string]$c["ck"]; Estado = $estado
        }
        foreach ($imp in $t.Importes) {
            $do = Dec $o["s_$imp"]; $dc = Dec $c["s_$imp"]
            $tabImportes += [pscustomobject][ordered]@{ Tabla = $t.Vista; Importe = $imp; "Suma CONTACC" = (N2 $do); "Suma copia" = (N2 $dc); Diferencia = (N2 ($do - $dc)) }
        }
      }
      catch {
        $msg = "error al revisar: $($_.Exception.Message)"
        $Res1[$t.Vista] = "REVISAR"; $Notas1[$t.Vista] = $msg
        [void]$Pendientes.Add("1 · $($t.Vista): $msg")
        W "  ERROR en $($t.Vista): $msg" "Red"
      }
    }
    Subtitulo "Filas, contenido y checksum (CONTACC contra la copia en PIQ_IA)"
    Tabla $tabResumen
    Subtitulo "Suma de los importes principales"
    Tabla $tabImportes
    if ($tabPeriodos.Count -gt 0) {
        Subtitulo "Dónde difieren origen y copia (filas que están en un lado y no en el otro)"
        Tabla $tabPeriodos
    }
    foreach ($t in $Tablas) { if ($Notas1[$t.Vista]) { W ("  * " + $t.Vista + ": " + $Notas1[$t.Vista]) $(if ($Res1[$t.Vista] -eq "REVISAR") { "Red" } else { "Yellow" }) } }
}

# ============================================================================
#  REVISIÓN 2: COPIA vs VISTA QUE LEE LA WEB
# ============================================================================
Titulo "REVISIÓN 2 de 4 - COPIA FIEL contra la VISTA que lee la web (dentro de PIQ_IA)"
W "La vista debe devolver las mismas filas que su copia y los mismos totales. Los importes de la vista van"
W "redondeados a 2 decimales (igual que la carga manual anterior), así que el total esperado es el de la copia"
W "redondeado fila por fila a 2 decimales; la diferencia contra ese total tiene que ser exactamente 0.00."
$tab2 = @(); $tab2i = @()
foreach ($t in $Tablas) {
  try {
    $nota = ""; $estado = "OK"
    try {
        $fc = [int64](Invoke-Consulta $piq "SELECT COUNT_BIG(*) AS n FROM dbo.[$($t.Copia)]").Rows[0]["n"]
        $fv = [int64](Invoke-Consulta $piq "SELECT COUNT_BIG(*) AS n FROM dbo.[$($t.Vista)]").Rows[0]["n"]
    }
    catch { $Res2[$t.Vista] = "REVISAR"; $Notas2[$t.Vista] = "no se pudo leer la vista o la copia: $($_.Exception.Message)"; [void]$Pendientes.Add("2 · $($t.Vista): $($Notas2[$t.Vista])"); continue }
    $esperadas = $fc
    if ($t.Agrupada) {
        $esperadas = [int64](Invoke-Consulta $piq "SELECT COUNT_BIG(*) AS n FROM (SELECT [ban_codigo], [Sal_Mes], [Sal_Ano] FROM dbo.[$($t.Copia)] GROUP BY [ban_codigo], [Sal_Mes], [Sal_Ano]) g").Rows[0]["n"]
    }
    if ($fv -ne $esperadas) { $estado = "REVISAR"; $nota = "la vista tiene $fv filas y se esperaban $esperadas" }
    $tab2 += [pscustomobject][ordered]@{ Tabla = $t.Vista; "Filas copia" = (N0 $fc); "Filas esperadas en la vista" = (N0 $esperadas); "Filas vista" = (N0 $fv); Estado = $estado }
    foreach ($imp in $t.Importes) {
        $sc = Dec (Invoke-Consulta $piq "SELECT SUM(CAST([$imp] AS DECIMAL(38,4))) AS s FROM dbo.[$($t.Copia)]").Rows[0]["s"]
        if ($t.Agrupada) {
            $sqlEsp = "SELECT SUM(CAST(g.s AS DECIMAL(38,4))) AS s FROM (SELECT CAST(SUM(ISNULL([$imp], 0)) AS DECIMAL(18,2)) AS s FROM dbo.[$($t.Copia)] GROUP BY [ban_codigo], [Sal_Mes], [Sal_Ano]) g"
        }
        else { $sqlEsp = "SELECT SUM(CAST(CAST([$imp] AS DECIMAL(18,2)) AS DECIMAL(38,4))) AS s FROM dbo.[$($t.Copia)]" }
        $se = Dec (Invoke-Consulta $piq $sqlEsp).Rows[0]["s"]
        $sv = Dec (Invoke-Consulta $piq "SELECT SUM(CAST([$imp] AS DECIMAL(38,4))) AS s FROM dbo.[$($t.Vista)]").Rows[0]["s"]
        $dif = $sv - $se
        $ok = ($dif -eq 0)
        if (-not $ok) { $estado = "REVISAR"; $nota = "el total de $imp en la vista no coincide con el de su copia (diferencia $(N2 $dif))" }
        $tab2i += [pscustomobject][ordered]@{ Tabla = $t.Vista; Importe = $imp; "Suma copia (exacta)" = (N2 $sc); "Esperado (copia a 2 dec.)" = (N2 $se); "Suma vista" = (N2 $sv); "Diferencia vs esperado" = (N2 $dif); "Redondeo (copia - esperado)" = (N2 ($sc - $se)); Estado = $(if ($ok) { "OK" } else { "REVISAR" }) }
    }
    $Res2[$t.Vista] = $estado; $Notas2[$t.Vista] = $nota
    if ($estado -eq "REVISAR") { [void]$Pendientes.Add("2 · $($t.Vista): $nota") }
  }
  catch {
    $msg = "error al revisar: $($_.Exception.Message)"
    $Res2[$t.Vista] = "REVISAR"; $Notas2[$t.Vista] = $msg
    [void]$Pendientes.Add("2 · $($t.Vista): $msg")
    W "  ERROR en $($t.Vista): $msg" "Red"
  }
}
Subtitulo "Filas"
Tabla $tab2
Subtitulo "Totales de importes"
Tabla $tab2i
$sb = $Tablas | Where-Object { $_.Agrupada }
$repetidas = Invoke-Consulta $piq "SELECT [ban_codigo] AS Banco, COUNT_BIG(*) AS [Períodos con filas repetidas], SUM(n) AS [Filas que se suman] FROM (SELECT [ban_codigo], [Sal_Mes], [Sal_Ano], COUNT_BIG(*) AS n FROM dbo.[$($sb.Copia)] GROUP BY [ban_codigo], [Sal_Mes], [Sal_Ano] HAVING COUNT_BIG(*) > 1) g GROUP BY [ban_codigo]"
$totalCopiaSB = [int64](Invoke-Consulta $piq "SELECT COUNT_BIG(*) AS n FROM dbo.[$($sb.Copia)]").Rows[0]["n"]
$totalVistaSB = [int64](Invoke-Consulta $piq "SELECT COUNT_BIG(*) AS n FROM dbo.[$($sb.Vista)]").Rows[0]["n"]
Subtitulo "Por qué SaldosBancos tiene menos filas que su copia"
W "  La copia fiel (vw_piq_saldos_bancos) trae $(N0 $totalCopiaSB) filas y la vista SaldosBancos da $(N0 $totalVistaSB):"
W "  la vista suma en una sola fila las filas repetidas de un mismo banco/mes/año (ej. BANRURAL trae 3 por período),"
W "  igual que hacía la carga manual anterior. Se suman $(N0 ($totalCopiaSB - $totalVistaSB)) filas sobrantes; los totales no cambian."
if ($repetidas.Rows.Count -gt 0) { Tabla ($repetidas.Rows | ForEach-Object { [pscustomobject][ordered]@{ Banco = $_["Banco"]; "Períodos con filas repetidas" = $_["Períodos con filas repetidas"]; "Filas que se suman" = $_["Filas que se suman"] } }) }
foreach ($t in $Tablas) { if ($Notas2[$t.Vista]) { W ("  * " + $t.Vista + ": " + $Notas2[$t.Vista]) "Red" } }

# ============================================================================
#  REVISIÓN 3: RESPALDO vs VISTA
# ============================================================================
Titulo "REVISIÓN 3 de 4 - RESPALDO (datos verificados de la semana pasada) contra la VISTA que lee la web"
W "Esta es la revisión más importante: todo lo que estaba en el respaldo debe seguir EXACTAMENTE igual en la vista."
W "Se comparan solo las columnas de datos (sin id autonumérico, fechamod, userid ni columnas técnicas) y los textos"
W "se comparan letra por letra (sin ignorar mayúsculas/minúsculas ni acentos)."

foreach ($t in $Tablas) {
  try {
    Subtitulo ("{0}:  respaldo dbo.{1}  contra  vista dbo.{0}" -f $t.Vista, $t.Respaldo)
    $colsV = Columnas $piq $t.Vista
    $colsR = Columnas $piq $t.Respaldo
    if ($colsR.Count -eq 0) {
        $Res3[$t.Vista] = "REVISAR"; $Notas3[$t.Vista] = "no existe dbo.$($t.Respaldo)"; [void]$Pendientes.Add("3 · $($t.Vista): no existe dbo.$($t.Respaldo)"); W "  No existe dbo.$($t.Respaldo): no se puede comparar." "Red"; continue
    }
    $nombresR = @($colsR | ForEach-Object { $_[0].ToLower() })
    $faltan = @($colsV | Where-Object { $nombresR -notcontains $_[0].ToLower() } | ForEach-Object { $_[0] })
    $excluidas = @($colsR | Where-Object { -not (@($colsV | ForEach-Object { $_[0].ToLower() }) -contains $_[0].ToLower()) } | ForEach-Object { $_[0] })
    if ($faltan.Count -gt 0) {
        $Res3[$t.Vista] = "REVISAR"; $Notas3[$t.Vista] = "el respaldo no tiene las columnas: $($faltan -join ', ')"; [void]$Pendientes.Add("3 · $($t.Vista): $($Notas3[$t.Vista])"); W "  El respaldo no tiene las columnas: $($faltan -join ', ')" "Red"; continue
    }
    W ("  Columnas comparadas ({0}): {1}" -f $colsV.Count, (($colsV | ForEach-Object { $_[0] }) -join ", "))
    W ("  Columnas del respaldo EXCLUIDAS (técnicas): " + $(if ($excluidas.Count) { $excluidas -join ", " } else { "ninguna" }))

    # lista de columnas con alias c1..cn
    $exprs = @(); $alias = @{}
    for ($i = 0; $i -lt $colsV.Count; $i++) { $exprs += (Expr-Col $colsV[$i][0] $colsV[$i][1]); $alias[$colsV[$i][0].ToLower()] = "c$($i + 1)" }
    $listaSel = ((0..($colsV.Count - 1)) | ForEach-Object { "$($exprs[$_]) AS c$($_ + 1)" }) -join ", "
    $listaGrp = $exprs -join ", "
    $selR = "SELECT $listaSel, COUNT_BIG(*) AS n FROM dbo.[$($t.Respaldo)] GROUP BY $listaGrp"
    $selV = "SELECT $listaSel, COUNT_BIG(*) AS n FROM dbo.[$($t.Vista)] GROUP BY $listaGrp"
    $cr = [int64](Invoke-Consulta $piq "SELECT COUNT_BIG(*) AS n FROM dbo.[$($t.Respaldo)]").Rows[0]["n"]
    $cv = [int64](Invoke-Consulta $piq "SELECT COUNT_BIG(*) AS n FROM dbo.[$($t.Vista)]").Rows[0]["n"]
    $soloR = [int64](Invoke-Consulta $piq "WITH dr AS ($selR EXCEPT $selV) SELECT ISNULL(SUM(n), 0) AS n FROM dr").Rows[0]["n"]
    $soloV = [int64](Invoke-Consulta $piq "WITH dv AS ($selV EXCEPT $selR) SELECT ISNULL(SUM(n), 0) AS n FROM dv").Rows[0]["n"]

    # condiciones de clave (NULL-seguras) hacia la otra tabla
    function Cond-Clave([string]$otraAlias, [string]$mia) {
        $conds = @()
        foreach ($k in $t.Clave) {
            $tipoK = ($colsV | Where-Object { $_[0].ToLower() -eq $k.ToLower() } | Select-Object -First 1)[1]
            $izq = "$otraAlias.[$k]"; if (Es-Texto $tipoK) { $izq = "$otraAlias.[$k] COLLATE Latin1_General_BIN2" }
            $der = "$mia.$($alias[$k.ToLower()])"
            $conds += "($izq = $der OR ($otraAlias.[$k] IS NULL AND $der IS NULL))"
        }
        return ($conds -join " AND ")
    }
    $condV = Cond-Clave "x" "d"   # la fila d (de respaldo) existe en la vista con la misma clave?
    $tieneP = [bool]$t.Anio
    $cA = if ($tieneP) { "d." + $alias[$t.Anio.ToLower()] } else { "" }
    $cM = if ($t.Mes) { "d." + $alias[$t.Mes.ToLower()] } else { "0" }

    $estado = "OK"; $nota = ""
    $modif = 0; $desap = 0; $nuevas = 0; $modifV = 0
    if ($soloR -gt 0) {
        $estado = "REVISAR"
        # clasificación por período: ¿modificadas (misma clave, otros valores) o desaparecidas?
        if ($tieneP) {
            $selA = "$cA AS anio, $cM AS mes,"
            $selO = "z.anio, z.mes,"
            $grpA = "GROUP BY z.anio, z.mes ORDER BY z.anio, z.mes"
        }
        else { $selA = ""; $selO = ""; $grpA = "" }
        $sqlR = "WITH dr AS ($selR EXCEPT $selV) SELECT $selO SUM(z.modificadas) AS modificadas, SUM(z.desaparecidas) AS desaparecidas FROM (SELECT $selA CASE WHEN EXISTS (SELECT 1 FROM dbo.[$($t.Vista)] x WHERE $condV) THEN d.n ELSE 0 END AS modificadas, CASE WHEN EXISTS (SELECT 1 FROM dbo.[$($t.Vista)] x WHERE $condV) THEN 0 ELSE d.n END AS desaparecidas FROM dr d) z $grpA"
        $porP = Invoke-Consulta $piq $sqlR
        foreach ($r in $porP.Rows) { $modif += [int64]$r["modificadas"]; $desap += [int64]$r["desaparecidas"] }
        Subtitulo "FILAS DEL RESPALDO QUE YA NO ESTÁN IGUAL EN LA VISTA: $(N0 $soloR)  (deben ser 0)"
        W ("  De ellas: {0} modificadas (la clave existe en la vista con otros valores) y {1} que desaparecieron (la clave ya no existe)." -f (N0 $modif), (N0 $desap)) "Red"
        if ($tieneP) {
            Tabla ($porP.Rows | ForEach-Object { [pscustomobject][ordered]@{ "Año" = $_["anio"]; Mes = $(if ($t.Mes) { $_["mes"] } else { "-" }); "Modificadas" = (N0 $_["modificadas"]); "Desaparecidas" = (N0 $_["desaparecidas"]) } })
            $anios = @($porP.Rows | ForEach-Object { [int]$_["anio"] } | Sort-Object -Unique)
            W ("  Períodos afectados: " + (($porP.Rows | ForEach-Object { if ($t.Mes) { "{0}-{1:00}" -f $_["anio"], $_["mes"] } else { "{0}" -f $_["anio"] } }) -join ", ") + ". Si son meses anteriores, es un cambio de la contabilidad en meses ya cerrados.") "Yellow"
        }
        # ejemplos (hasta 10) con valor anterior y nuevo
        $orden = if ($tieneP) { "ORDER BY $cA" + $(if ($t.Mes) { ", $cM" } else { "" }) } else { "ORDER BY d.c1" }
        $cols_d = ((1..$colsV.Count) | ForEach-Object { "d.c$_" }) -join ", "
        $ej = Invoke-Consulta $piq "WITH dr AS ($selR EXCEPT $selV) SELECT TOP 10 $cols_d, d.n FROM dr d $orden"
        W ""
        W "  Ejemplos (hasta 10) - valor ANTERIOR (respaldo) y valor NUEVO (vista):" "Yellow"
        $num = 0
        foreach ($fila in $ej.Rows) {
            $num++
            $claveTxt = (($t.Clave | ForEach-Object { "$_=" + (Txt $fila[$alias[$_.ToLower()]]) }) -join ", ")
            W ("  {0,2}. {1}" -f $num, $claveTxt)
            # buscar la fila de la vista con la misma clave
            $conds = @(); $pars = @{}; $j = 0
            foreach ($k in $t.Clave) {
                $j++; $val = $fila[$alias[$k.ToLower()]]
                if ($val -is [DBNull]) { $conds += "([$k] IS NULL)" } else { $conds += "([$k] = @p$j)"; $pars["p$j"] = $val }
            }
            $listaV = ($colsV | ForEach-Object { "[$($_[0])]" }) -join ", "
            $cand = Invoke-Consulta $piq "SELECT TOP 5 $listaV FROM dbo.[$($t.Vista)] WHERE $($conds -join ' AND ')" $pars
            if ($cand.Rows.Count -eq 0) {
                W "      ANTERIOR: $((($colsV | ForEach-Object { $_[0] + '=' + (Txt $fila[$alias[$_[0].ToLower()]]) }) -join '; '))"
                W "      NUEVO   : (la fila ya no existe en la vista)" "Red"
            }
            else {
                $mejor = $null; $mejorDif = 9999
                foreach ($cr2 in $cand.Rows) {
                    $d2 = @($colsV | Where-Object { (Txt $fila[$alias[$_[0].ToLower()]]) -cne (Txt $cr2[$_[0]]) })
                    if ($d2.Count -lt $mejorDif) { $mejorDif = $d2.Count; $mejor = $cr2 }
                }
                foreach ($cc in $colsV) {
                    $va = Txt $fila[$alias[$cc[0].ToLower()]]; $vn = Txt $mejor[$cc[0]]
                    if ($va -cne $vn) { W ("      {0}: ANTERIOR {1}  ->  NUEVO {2}" -f $cc[0], $va, $vn) "Red" }
                }
            }
        }
        $nota = "$(N0 $soloR) filas del respaldo ya no están iguales en la vista ($(N0 $modif) modificadas, $(N0 $desap) desaparecidas)"
    }
    if ($soloV -gt 0) {
        $condR = Cond-Clave "y" "d"
        if ($tieneP) {
            $selB = "$cA AS anio, $cM AS mes,"
            $selO2 = "z.anio, z.mes,"
            $grpB = "GROUP BY z.anio, z.mes ORDER BY z.anio, z.mes"
        }
        else { $selB = ""; $selO2 = ""; $grpB = "" }
        $sqlV = "WITH dv AS ($selV EXCEPT $selR) SELECT $selO2 SUM(z.nuevas) AS nuevas, SUM(z.modificadas) AS modificadas FROM (SELECT $selB CASE WHEN EXISTS (SELECT 1 FROM dbo.[$($t.Respaldo)] y WHERE $condR) THEN 0 ELSE d.n END AS nuevas, CASE WHEN EXISTS (SELECT 1 FROM dbo.[$($t.Respaldo)] y WHERE $condR) THEN d.n ELSE 0 END AS modificadas FROM dv d) z $grpB"
        $porV = Invoke-Consulta $piq $sqlV
        foreach ($r in $porV.Rows) { $nuevas += [int64]$r["nuevas"]; $modifV += [int64]$r["modificadas"] }
        Subtitulo "FILAS NUEVAS EN LA VISTA (no estaban en el respaldo): $(N0 $nuevas)   (+ $(N0 $modifV) que son la versión nueva de filas modificadas)"
        if ($tieneP) {
            Tabla ($porV.Rows | Where-Object { [int64]$_["nuevas"] -gt 0 } | ForEach-Object { [pscustomobject][ordered]@{ "Año" = $_["anio"]; Mes = $(if ($t.Mes) { $_["mes"] } else { "-" }); "Filas nuevas" = (N0 $_["nuevas"]) } })
        }
        else { W ("  Filas nuevas: " + (N0 $nuevas) + " (esta tabla no tiene período para agrupar).") }
        W "  Las filas nuevas son normales: son datos de la contabilidad posteriores a la exportación del 2026-10-01." "Green"
    }
    if ($soloR -eq 0 -and $soloV -eq 0) { W "  Todas las filas del respaldo están EXACTAMENTE igual en la vista, y la vista no tiene filas de más." "Green" }
    elseif ($soloR -eq 0) { W "  Todas las filas del respaldo están EXACTAMENTE igual en la vista (la vista solo tiene filas nuevas)." "Green" }

    # totales por año
    if ($tieneP -and $t.Importes.Count -gt 0) {
        $sumasY = ($t.Importes | ForEach-Object { "SUM(CAST([$_] AS DECIMAL(38,2))) AS [s_$_]" }) -join ", "
        $sqlY = "SELECT [$($t.Anio)] AS anio, COUNT_BIG(*) AS filas, $sumasY FROM dbo.[%T%] GROUP BY [$($t.Anio)]"
        $yr = Invoke-Consulta $piq ($sqlY -replace "%T%", $t.Respaldo)
        $yv = Invoke-Consulta $piq ($sqlY -replace "%T%", $t.Vista)
        $mr = @{}; $mv = @{}
        foreach ($r in $yr.Rows) { $mr[[int]$r["anio"]] = $r }
        foreach ($r in $yv.Rows) { $mv[[int]$r["anio"]] = $r }
        $anios = @($mr.Keys) + @($mv.Keys) | Sort-Object -Unique
        $tabY = @()
        foreach ($a in $anios) {
            foreach ($imp in $t.Importes) {
                $vr = if ($mr[$a]) { Dec $mr[$a]["s_$imp"] } else { [decimal]0 }
                $vv = if ($mv[$a]) { Dec $mv[$a]["s_$imp"] } else { [decimal]0 }
                $tabY += [pscustomobject][ordered]@{ "Año" = $a; Importe = $imp; "Filas respaldo" = $(if ($mr[$a]) { N0 $mr[$a]["filas"] } else { "0" }); "Filas vista" = $(if ($mv[$a]) { N0 $mv[$a]["filas"] } else { "0" }); "Total respaldo" = (N2 $vr); "Total vista" = (N2 $vv); Diferencia = (N2 ($vv - $vr)) }
            }
        }
        W ""; W "  Totales por año, respaldo contra vista (la diferencia solo debería aparecer en años con filas nuevas):"
        Tabla $tabY
    }
    elseif (-not $tieneP) { W "" ; W "  (Esta tabla no tiene años ni importes: solo se comparan filas y contenido.)" }

    $tabFilas = [pscustomobject][ordered]@{ "Filas respaldo" = (N0 $cr); "Filas vista" = (N0 $cv); "Respaldo sin igual en la vista" = (N0 $soloR); "Vista sin igual en el respaldo" = (N0 $soloV) }
    W ""; Tabla $tabFilas
    $Res3[$t.Vista] = $estado
    $Notas3[$t.Vista] = $(if ($nota) { $nota } elseif ($nuevas -gt 0) { "$(N0 $nuevas) filas nuevas respecto del respaldo (normal)" } else { "" })
    if ($estado -eq "REVISAR") { [void]$Pendientes.Add("3 · $($t.Vista): $nota") }
  }
  catch {
    $msg = "error al revisar: $($_.Exception.Message)"
    $Res3[$t.Vista] = "REVISAR"; $Notas3[$t.Vista] = $msg
    [void]$Pendientes.Add("3 · $($t.Vista): $msg")
    W "  ERROR en $($t.Vista): $msg" "Red"
  }
}

# ============================================================================
#  REVISIÓN 4: TABLAS QUE SE CARGAN POR EXCEL
# ============================================================================
Titulo "REVISIÓN 4 de 4 - TABLAS QUE SE CARGAN POR EXCEL (solo informativo)"
W "SaldoBancario y OtroIngreso las carga una persona desde la pantalla de cargas; la sincronización no las toca."
foreach ($nombre in @("SaldoBancario", "OtroIngreso")) {
    Subtitulo "dbo.$nombre"
    try {
        $tot = (Invoke-Consulta $piq "SELECT COUNT_BIG(*) AS filas, MAX([Anio] * 100 + [Mes]) AS ultimo FROM dbo.[$nombre]").Rows[0]
        W ("  Filas totales: {0}    Último año/mes cargado: {1}" -f (N0 $tot["filas"]), $(if ($tot["ultimo"] -is [DBNull]) { "-" } else { Periodo-Texto ([int]$tot["ultimo"]) }))
        if ($nombre -eq "SaldoBancario") { $sqlA = "SELECT [Anio] AS anio, COUNT_BIG(*) AS filas, SUM(CAST([Valor] AS DECIMAL(38,2))) AS total FROM dbo.[SaldoBancario] GROUP BY [Anio] ORDER BY [Anio]" }
        else { $sqlA = "SELECT [Anio] AS anio, [Tipo] AS tipo, COUNT_BIG(*) AS filas, SUM(CAST([Valor] AS DECIMAL(38,2))) AS total FROM dbo.[OtroIngreso] GROUP BY [Anio], [Tipo] ORDER BY [Anio], [Tipo]" }
        $pa = Invoke-Consulta $piq $sqlA
        if ($nombre -eq "SaldoBancario") { Tabla ($pa.Rows | ForEach-Object { [pscustomobject][ordered]@{ "Año" = $_["anio"]; Filas = (N0 $_["filas"]); "Suma de Valor" = (N2 $_["total"]) } }) }
        else { Tabla ($pa.Rows | ForEach-Object { [pscustomobject][ordered]@{ "Año" = $_["anio"]; Tipo = $_["tipo"]; Filas = (N0 $_["filas"]); "Suma de Valor" = (N2 $_["total"]) } }); W "  (Los valores de OtroIngreso son acumulados por mes: la suma por año es solo una referencia.)" }
    }
    catch { W "  No se pudo leer dbo.$nombre`: $($_.Exception.Message)" "Yellow" }
}

# ============================================================================
#  RESUMEN
# ============================================================================
Titulo "RESUMEN"
$resumen = @()
foreach ($t in $Tablas) {
    $resumen += [pscustomobject][ordered]@{
        Tabla = $t.Vista
        "1 Origen vs copia" = $Res1[$t.Vista]
        "2 Copia vs vista" = $Res2[$t.Vista]
        "3 Respaldo vs vista" = $Res3[$t.Vista]
    }
}
Tabla $resumen
W "4 Tablas por Excel (SaldoBancario, OtroIngreso): informativo, ver arriba."
W ""
$hayRevisar = ($Pendientes.Count -gt 0)
if ($hayRevisar) {
    W "RESULTADO: REVISAR" "Red"
    W "Lo que hay que mirar:" "Red"
    foreach ($p in $Pendientes) { W ("  - " + $p) "Red" }
}
else {
    W "RESULTADO: OK, los datos cuadran" "Green"
    $avisos = @($Tablas | Where-Object { $Notas1[$_.Vista] -like "AVISO*" })
    foreach ($t in $avisos) { W ("  (aviso) " + $t.Vista + ": " + $Notas1[$t.Vista]) "Yellow" }
}
$noSelect = @($script:Consultas | Where-Object { $_ -notmatch "^(?i)(SELECT|WITH)\b" })
W ""
W ("Consultas ejecutadas: {0}, todas de solo lectura (SELECT/WITH); consultas que no eran SELECT: {1}." -f $script:Consultas.Count, $noSelect.Count)
W ("Duración: {0:N0} segundos." -f ((Get-Date) - $Inicio).TotalSeconds)

Guardar-Reporte

$piq.Close(); if ($cx) { $cx.Close() }
if ($hayRevisar) { exit 1 } else { exit 0 }
