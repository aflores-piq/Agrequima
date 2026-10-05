"""Sincronización nocturna del módulo Financiero: copia COMPLETA de los 10
objetos del servidor del cliente (10.10.0.6,65280) a sus copias fieles en
PIQ_IA (mismo nombre, mismos campos, mismo orden -- ver
17_copias_fieles_financiero.sql). Las pantallas del Financiero leen esas
copias a través de las vistas de 18_vistas_financiero.sql.

  Base CONTACC   (8): vw_piq_balance_saldos, vw_piq_balance_general,
                      vw_catalogo_cuentas, vw_piq_centrosdecosto,
                      vw_piq_presupuestos, vw_piq_asociados_cuota,
                      vw_piq_cheques_circulacion, vw_piq_saldos_bancos
  Base Agrequima (2): SaldoBancario, OtroIngreso

POR QUÉ UN SCRIPT APARTE de sync_piq_ia.py: ese script espeja
Importacion/Nutrientes/catálogos con un mecanismo distinto (refleja el
esquema con SQLAlchemy y lo crea si falta). Acá la estructura es FIJA y
conocida (copias fieles del CSV del cliente), hace falta cargar sin dejar
nunca una tabla vacía o a medias, registrar un log diario con filas por
tabla y devolver un código de salida útil para el Programador de tareas.
Mezclarlo con el otro habría complicado ambos.

CÓMO NUNCA DEJA UNA TABLA A MEDIAS: para cada objeto lee TODO el origen a
una tabla de staging (dbo.stg_sync_<objeto>) de la base de destino; recién
cuando la lectura terminó completa y sin errores, y la cantidad de filas
coincide, hace DELETE + INSERT desde el staging sobre la copia real y COMMIT
-- el reemplazo va en UNA sola transacción. Si algo falla en cualquier punto (conexión caída, error de
estructura, error de inserción), la transacción se revierte y la tabla
conserva los datos del día anterior. Si un objeto falla, los demás siguen.
Si el origen devuelve 0 filas y la copia tenía datos, NO la reemplaza
(casi seguro es un problema del origen, no que realmente no haya datos).

NO TOCA: Importacion, Nutrientes, catálogos de nomenclatura/agrupadores,
CatalogoAgrupadorCuentas, Usuarios, Roles ni nada que se cargue por Excel
(salvo SaldoBancario/OtroIngreso, que SÍ son parte de los 10 objetos --
ver SYNC_FINANCIERO_OMITIR para excluirlas si se prefiere seguir
cargándolas solo por Excel).

Configuración (todo por variables de entorno / archivo .env, nunca en el
código). Busca el .env en: SYNC_ENV_FILE (si está definida), la carpeta
de este script, su carpeta padre y la anterior (en el servidor real, el
.env de la raíz C:\\Pronostiq\\Agrequima-pronostiq\\.env).

  Destino (las MISMAS que ya usa el backend):
    DB_SERVER, DB_NAME, DB_USER, DB_PASSWORD, ODBC_DRIVER
  Origen CONTACC:
    SYNC_CONTACC_DB_SERVER   ej. 10.10.0.6,65280
    SYNC_CONTACC_DB_NAME     (opcional, default CONTACC)
    SYNC_CONTACC_DB_USER
    SYNC_CONTACC_DB_PASSWORD
  Origen Agrequima (todo opcional: si falta, usa el de CONTACC):
    SYNC_AGREQUIMA_DB_SERVER, SYNC_AGREQUIMA_DB_NAME (default Agrequima),
    SYNC_AGREQUIMA_DB_USER, SYNC_AGREQUIMA_DB_PASSWORD
  Opcionales:
    SYNC_FINANCIERO_LOG_DIR       carpeta del log (default: ..\\logs)
    SYNC_FINANCIERO_REINTENTOS    intentos por objeto (default 2)
    SYNC_FINANCIERO_ESPERA_SEG    espera entre intentos (default 60)
    SYNC_FINANCIERO_OMITIR        objetos a NO sincronizar, separados por coma

Uso:
    python sync_financiero.py                  (los 10 objetos)
    python sync_financiero.py --solo SaldoBancario,OtroIngreso
    python sync_financiero.py --probar         (solo prueba la conexión a CONTACC y a Agrequima y que se
                                                puedan leer los 10 objetos; no copia nada)
    python sync_financiero.py --probar-completo  (lo anterior + conexión a PIQ_IA y estructura de las copias)

Código de salida: 0 = todo OK; 1 = falló al menos un objeto;
2 = error de configuración (falta alguna variable).
"""

import datetime
import logging
import os
import sys
import time
import traceback
from pathlib import Path

import pyodbc
from dotenv import load_dotenv

CARPETA_SCRIPT = Path(__file__).resolve().parent

# --- Estructura esperada de los 10 objetos (generada desde ---
# --- docs/legacy/financiero/estructura_vistas_cliente.csv)  ---
# (objeto, base de origen, [(campo, tipo SQL, acepta_nulos), ...]). El destino
# tiene el mismo nombre que el objeto de origen, en el esquema dbo.
OBJETOS = [
    ("vw_piq_balance_saldos", "CONTACC", [
        ("emp_nit", "VARCHAR(20)", False),
        ("Cta_Codigo", "VARCHAR(20)", False),
        ("Cta_Descripcion", "VARCHAR(100)", False),
        ("Sal_Ano", "SMALLINT", False),
        ("Sal_Mes", "SMALLINT", False),
        ("Debitos", "MONEY", True),
        ("Creditos", "MONEY", True),
        ("Saldo", "MONEY", True),
        ("Cod_Centro", "VARCHAR(20)", False),
    ]),
    ("vw_piq_balance_general", "CONTACC", [
        ("emp_nit", "VARCHAR(20)", True),
        ("Cod_n1", "VARCHAR(20)", True),
        ("Nom_n1", "VARCHAR(100)", True),
        ("cod_n5", "VARCHAR(20)", True),
        ("nom_n5", "VARCHAR(100)", True),
        ("Sal_Ano", "SMALLINT", False),
        ("Sal_Mes", "SMALLINT", True),
        ("Debitos", "MONEY", True),
        ("Creditos", "MONEY", True),
        ("Saldo", "MONEY", True),
        ("Inicial", "INT", False),
    ]),
    ("vw_catalogo_cuentas", "CONTACC", [
        ("cta_nivel", "TINYINT", True),
        ("Codigo_N1", "VARCHAR(20)", False),
        ("Nombre_n1", "VARCHAR(100)", False),
        ("Codigo_N5", "VARCHAR(20)", True),
        ("Nombre_N5", "VARCHAR(100)", True),
    ]),
    ("vw_piq_centrosdecosto", "CONTACC", [
        ("emp_nit", "VARCHAR(20)", False),
        ("Cod_centro", "VARCHAR(20)", False),
        ("Des_centro", "VARCHAR(40)", True),
        ("nivel", "TINYINT", True),
        ("CC_Grupo1", "VARCHAR(20)", True),
    ]),
    ("vw_piq_presupuestos", "CONTACC", [
        ("emp_nit", "VARCHAR(20)", False),
        ("par_ano", "SMALLINT", False),
        ("par_mes", "SMALLINT", False),
        ("cta_codigo", "NVARCHAR(20)", False),
        ("pre_presupuesto", "MONEY", True),
        ("cod_centro", "VARCHAR(20)", False),
    ]),
    ("vw_piq_asociados_cuota", "CONTACC", [
        ("emp_nit", "VARCHAR(20)", True),
        ("Sal_Ano", "SMALLINT", False),
        ("cod_n5", "VARCHAR(20)", True),
        ("nom_n5", "VARCHAR(100)", True),
        ("grupo", "VARCHAR(1)", True),
        ("nombre_mostrar", "VARCHAR(25)", True),
        ("cuota", "MONEY", True),
    ]),
    ("vw_piq_cheques_circulacion", "CONTACC", [
        ("ban_codigo", "VARCHAR(10)", False),
        ("cta_numero", "VARCHAR(30)", True),
        ("cta_nombre", "VARCHAR(50)", True),
        ("Cta_Codigo", "VARCHAR(20)", True),
        ("par_ano", "SMALLINT", False),
        ("par_mes", "SMALLINT", False),
        ("doc_numero", "VARCHAR(20)", False),
        ("doc_fecha", "DATETIME", True),
        ("doc_fchcobro", "DATETIME", True),
        ("doc_nombre", "VARCHAR(100)", True),
        ("doc_motivo", "VARCHAR(250)", False),
        ("doc_monto", "MONEY", True),
    ]),
    ("vw_piq_saldos_bancos", "CONTACC", [
        ("ban_codigo", "VARCHAR(10)", False),
        ("Sal_Mes", "INT", False),
        ("Sal_Ano", "INT", False),
        ("InicialL", "MONEY", True),
        ("EntradasL", "MONEY", True),
        ("SalidasL", "MONEY", True),
        ("FinalL", "MONEY", True),
    ]),
    ("SaldoBancario", "Agrequima", [
        ("concepto", "VARCHAR(100)", False),
        ("anio", "INT", False),
        ("mes", "INT", False),
        ("banco", "VARCHAR(100)", False),
        ("valor", "DECIMAL(18,2)", True),
        ("userid", "INT", True),
        ("fechamod", "DATETIME", True),
    ]),
    ("OtroIngreso", "Agrequima", [
        ("tipo", "VARCHAR(100)", False),
        ("concepto", "VARCHAR(150)", False),
        ("anio", "INT", False),
        ("mes", "INT", False),
        ("valor", "DECIMAL(18,2)", True),
        ("userid", "INT", True),
        ("fechamod", "DATETIME", True),
    ]),
]


class ErrorNoReintentable(Exception):
    """Error que repetir no arregla (estructura distinta, origen vacío...)."""


def _cargar_env() -> None:
    candidatos = []
    explicito = os.environ.get("SYNC_ENV_FILE")
    if explicito:
        candidatos.append(Path(explicito))
    for carpeta in (CARPETA_SCRIPT, CARPETA_SCRIPT.parent, CARPETA_SCRIPT.parent.parent):
        candidatos.append(carpeta / ".env")
    for ruta in candidatos:
        if ruta.exists():
            load_dotenv(ruta)  # no pisa variables ya definidas: el primero que la define gana


def _env(nombre: str, defecto: str | None = None) -> str | None:
    valor = os.environ.get(nombre)
    return valor.strip() if valor and valor.strip() else defecto


def _odbc_valor(valor: str) -> str:
    return "{" + valor.replace("}", "}}") + "}"


def _cadena_conexion(server: str, base: str, usuario: str | None, password: str | None) -> str:
    driver = _env("ODBC_DRIVER", "ODBC Driver 17 for SQL Server")
    partes = [f"DRIVER={{{driver}}}", f"SERVER={server}", f"DATABASE={base}", "TrustServerCertificate=yes"]
    if usuario:
        partes += [f"UID={_odbc_valor(usuario)}", f"PWD={_odbc_valor(password or '')}"]
    else:
        partes.append("Trusted_Connection=yes")
    return ";".join(partes)


def _config_destino() -> dict:
    faltan = [v for v in ("DB_SERVER", "DB_NAME") if not _env(v)]
    if faltan:
        raise RuntimeError(f"Faltan variables del destino en el .env: {', '.join(faltan)}")
    return dict(server=_env("DB_SERVER"), base=_env("DB_NAME"), usuario=_env("DB_USER"), password=_env("DB_PASSWORD"))


def _config_origenes() -> dict:
    faltan = [v for v in ("SYNC_CONTACC_DB_SERVER", "SYNC_CONTACC_DB_USER", "SYNC_CONTACC_DB_PASSWORD") if not _env(v)]
    if faltan:
        raise RuntimeError(f"Faltan variables del origen en el .env: {', '.join(faltan)}")
    contacc = dict(
        server=_env("SYNC_CONTACC_DB_SERVER"), base=_env("SYNC_CONTACC_DB_NAME", "CONTACC"),
        usuario=_env("SYNC_CONTACC_DB_USER"), password=_env("SYNC_CONTACC_DB_PASSWORD"),
    )
    agrequima = dict(
        server=_env("SYNC_AGREQUIMA_DB_SERVER", contacc["server"]),
        base=_env("SYNC_AGREQUIMA_DB_NAME", "Agrequima"),
        usuario=_env("SYNC_AGREQUIMA_DB_USER", contacc["usuario"]),
        password=_env("SYNC_AGREQUIMA_DB_PASSWORD", contacc["password"]),
    )
    return {"CONTACC": contacc, "Agrequima": agrequima}


class _ConsolaSegura(logging.StreamHandler):
    """La consola puede no existir o estar cerrada (tarea programada sin sesión, tubería cortada):
    un error al escribir ahí NO debe afectar la sincronización ni el log a archivo."""

    def handleError(self, record):
        pass


def _configurar_log() -> logging.Logger:
    carpeta = Path(_env("SYNC_FINANCIERO_LOG_DIR") or (CARPETA_SCRIPT.parent / "logs"))
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / f"sync_financiero_{datetime.date.today():%Y%m%d}.log"
    logger = logging.getLogger("sync_financiero")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formato = logging.Formatter("%(asctime)s %(levelname)-5s %(message)s", "%Y-%m-%d %H:%M:%S")
    archivo = logging.FileHandler(ruta, encoding="utf-8")
    archivo.setFormatter(formato)
    logger.addHandler(archivo)
    consola = _ConsolaSegura(sys.stdout)
    consola.setFormatter(formato)
    logger.addHandler(consola)
    logger.info("Log: %s", ruta)
    return logger


def _tipo_canonico(data_type, largo, precision, escala) -> str:
    t = data_type.lower()
    if t in ("varchar", "nvarchar", "char", "nchar"):
        return f"{t.upper()}({'MAX' if largo == -1 else largo})"
    if t in ("decimal", "numeric"):
        return f"{t.upper()}({precision},{escala})"
    return t.upper()


def _verificar_estructura_destino(cur, objeto: str, columnas: list) -> None:
    cur.execute(
        "SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, NUMERIC_PRECISION, NUMERIC_SCALE, IS_NULLABLE "
        "FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = ? ORDER BY ORDINAL_POSITION",
        objeto,
    )
    reales = [(r[0], _tipo_canonico(r[1], r[2], r[3], r[4]), r[5] == "YES") for r in cur.fetchall()]
    if not reales:
        raise ErrorNoReintentable(
            f"No existe dbo.{objeto} en PIQ_IA. Falta correr 17_copias_fieles_financiero.sql."
        )
    esperadas = [(c, t, n) for c, t, n in columnas]
    if reales != esperadas:
        detalle = []
        for i in range(max(len(reales), len(esperadas))):
            r = reales[i] if i < len(reales) else None
            e = esperadas[i] if i < len(esperadas) else None
            if r != e:
                detalle.append(f"  posición {i + 1}: en PIQ_IA={r} / esperado={e}")
        raise ErrorNoReintentable(
            f"La estructura de dbo.{objeto} en PIQ_IA no es la esperada (¿se corrió 17_copias_fieles_financiero.sql?):\n"
            + "\n".join(detalle[:10])
        )


def _lista_columnas(columnas: list) -> str:
    return ", ".join(f"[{c}]" for c, _, _ in columnas)


def _intento(objeto: str, base: str, columnas: list, destino: dict, origen: dict, log: logging.Logger):
    """Un intento completo de sincronizar UN objeto. Devuelve (leidas, cargadas).

    Fase 1 (autocommit): lee TODO el origen a una tabla de staging real
    (dbo.stg_sync_<objeto>) en la base de destino. Nadie lee esa tabla; si
    falla acá, la copia real ni se tocó.
    Fase 2 (UNA transacción): DELETE + INSERT desde el staging sobre la copia
    real, verifica la cantidad de filas y recién ahí COMMIT.
    (Se usa una tabla real y no una #temporal porque pyodbc necesita
    "describir" la tabla destino de los INSERT masivos y no ve las #temporales.)"""
    lista = _lista_columnas(columnas)
    stg = f"stg_sync_{objeto}"
    conn_origen = conn_destino = None
    try:
        conn_destino = pyodbc.connect(_cadena_conexion(**destino), timeout=15, autocommit=True)
        conn_destino.timeout = 900
        cur_d = conn_destino.cursor()
        _verificar_estructura_destino(cur_d, objeto, columnas)
        filas_antes = cur_d.execute(f"SELECT COUNT(*) FROM dbo.[{objeto}]").fetchone()[0]

        conn_origen = pyodbc.connect(_cadena_conexion(**origen), timeout=15, autocommit=True)
        conn_origen.timeout = 900
        cur_o = conn_origen.cursor()

        # --- Fase 1: leer TODO el origen al staging ---
        cur_d.execute(f"IF OBJECT_ID('dbo.{stg}', 'U') IS NOT NULL DROP TABLE dbo.[{stg}]")
        cur_d.execute(f"SELECT TOP 0 {lista} INTO dbo.[{stg}] FROM dbo.[{objeto}]")
        insertar = f"INSERT INTO dbo.[{stg}] ({lista}) VALUES ({', '.join('?' for _ in columnas)})"
        cur_d.fast_executemany = True

        cur_o.execute(f"SELECT {lista} FROM dbo.[{objeto}]")
        leidas = 0
        while True:
            bloque = cur_o.fetchmany(5000)
            if not bloque:
                break
            cur_d.executemany(insertar, [tuple(fila) for fila in bloque])
            leidas += len(bloque)
        cur_d.fast_executemany = False

        # La lectura terminó completa: recién ahora se valida.
        en_stg = cur_d.execute(f"SELECT COUNT(*) FROM dbo.[{stg}]").fetchone()[0]
        if en_stg != leidas:
            raise RuntimeError(f"Se leyeron {leidas} filas del origen pero quedaron {en_stg} en el staging.")
        total_origen = cur_o.execute(f"SELECT COUNT(*) FROM dbo.[{objeto}]").fetchone()[0]
        if total_origen != leidas:
            log.warning(
                "[%s] el origen tiene %d filas ahora pero se leyeron %d (el origen cambió durante la lectura).",
                objeto, total_origen, leidas,
            )
        if leidas == 0 and filas_antes > 0:
            raise ErrorNoReintentable(
                f"El origen devolvió 0 filas pero la copia tenía {filas_antes}. No se reemplazó "
                f"(se conservan los datos anteriores); revisar el origen."
            )

        # --- Fase 2: reemplazo en UNA transacción ---
        conn_destino.autocommit = False
        try:
            cur_d.execute("SET XACT_ABORT ON")
            cur_d.execute(f"DELETE FROM dbo.[{objeto}]")
            cur_d.execute(f"INSERT INTO dbo.[{objeto}] ({lista}) SELECT {lista} FROM dbo.[{stg}]")
            cargadas = cur_d.execute(f"SELECT COUNT(*) FROM dbo.[{objeto}]").fetchone()[0]
            if cargadas != leidas:
                raise RuntimeError(f"Tras reemplazar, dbo.{objeto} tiene {cargadas} filas y se esperaban {leidas}.")
            conn_destino.commit()
        except BaseException:
            conn_destino.rollback()
            raise
        return leidas, cargadas
    finally:
        if conn_destino is not None:
            try:
                conn_destino.autocommit = True
                conn_destino.cursor().execute(f"IF OBJECT_ID('dbo.{stg}', 'U') IS NOT NULL DROP TABLE dbo.[{stg}]")
            except Exception:
                pass
        for c in (conn_origen, conn_destino):
            if c is not None:
                try:
                    c.close()
                except Exception:
                    pass


def sincronizar_objeto(objeto, base, columnas, destino, origenes, intentos, espera, log):
    """Devuelve dict con el resultado. Nunca lanza: un objeto que falla no frena a los demás."""
    inicio = time.time()
    ultimo_error = ""
    for n in range(1, intentos + 1):
        try:
            leidas, cargadas = _intento(objeto, base, columnas, destino, origenes[base], log)
            seg = time.time() - inicio
            log.info(
                "[%s] OK  origen=%s  filas leidas=%d  cargadas=%d  (%.1f s)", objeto, base, leidas, cargadas, seg
            )
            return dict(objeto=objeto, base=base, estado="OK", leidas=leidas, cargadas=cargadas, error="")
        except ErrorNoReintentable as exc:
            ultimo_error = str(exc)
            log.error("[%s] ERROR (no se reintenta): %s", objeto, ultimo_error)
            break
        except Exception as exc:
            ultimo_error = f"{type(exc).__name__}: {exc}"
            log.error("[%s] ERROR en el intento %d de %d: %s", objeto, n, intentos, ultimo_error)
            log.error("[%s] detalle técnico:\n%s", objeto, traceback.format_exc().rstrip())
            if n < intentos:
                log.info("[%s] se reintenta en %d s ...", objeto, espera)
                time.sleep(espera)
    log.error("[%s] FALLÓ: la copia en PIQ_IA conserva los datos anteriores (no se modificó).", objeto)
    return dict(objeto=objeto, base=base, estado="ERROR", leidas=None, cargadas=None, error=ultimo_error)


def probar(destino: dict, origenes: dict, log: logging.Logger, completo: bool = False) -> int:
    """Modo --probar: NO copia nada. Verifica que se pueda entrar a los dos orígenes con las
    credenciales del .env y que cada objeto exista y se pueda leer. Con completo=True
    (--probar-completo) además prueba la conexión a PIQ_IA y la estructura de las copias."""
    fallos = 0
    for nombre in ("CONTACC", "Agrequima"):
        cfg = origenes[nombre]
        try:
            conn = pyodbc.connect(_cadena_conexion(**cfg), timeout=15)
        except Exception as exc:
            fallos += 1
            log.error("[ORIGEN %s] ERROR  no se pudo conectar a %s (base %s): %s", nombre, cfg["server"], cfg["base"], exc)
            continue
        log.info("[ORIGEN %s] OK  conexión a %s, base %s", nombre, cfg["server"], cfg["base"])
        cur = conn.cursor()
        for objeto, base, columnas in OBJETOS:
            if base != nombre:
                continue
            try:
                cur.execute(f"SELECT TOP 0 {_lista_columnas(columnas)} FROM dbo.[{objeto}]")
                log.info("      OK     dbo.%s (%d campos)", objeto, len(columnas))
            except Exception as exc:
                fallos += 1
                log.error("      ERROR  dbo.%s: %s", objeto, exc)
        conn.close()
    if not completo:
        log.info("=== Prueba finalizada (resultado=%s) ===", "CON ERRORES" if fallos else "OK")
        return 1 if fallos else 0
    try:
        conn = pyodbc.connect(_cadena_conexion(**destino), timeout=15)
    except Exception as exc:
        fallos += 1
        log.error("[DESTINO] ERROR  no se pudo conectar a %s (base %s): %s", destino["server"], destino["base"], exc)
        return 1
    log.info("[DESTINO] OK  conexión a %s, base %s", destino["server"], destino["base"])
    cur = conn.cursor()
    for objeto, base, columnas in OBJETOS:
        try:
            _verificar_estructura_destino(cur, objeto, columnas)
            log.info("      OK     dbo.%s tiene la estructura esperada", objeto)
        except Exception as exc:
            fallos += 1
            log.error("      ERROR  dbo.%s: %s", objeto, exc)
    conn.close()
    log.info("=== Prueba finalizada (resultado=%s) ===", "CON ERRORES" if fallos else "OK")
    return 1 if fallos else 0


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _cargar_env()
    log = _configurar_log()
    log.info("=== INICIO sincronización Financiero ===")

    try:
        destino = _config_destino()
        origenes = _config_origenes()
    except RuntimeError as exc:
        log.error("Configuración incompleta: %s", exc)
        log.info("=== FIN sincronización Financiero (resultado=ERROR DE CONFIGURACIÓN) ===")
        return 2

    if "--probar" in argv or "--probar-completo" in argv:
        return probar(destino, origenes, log, completo="--probar-completo" in argv)

    omitir = {x.strip().lower() for x in (_env("SYNC_FINANCIERO_OMITIR", "") or "").split(",") if x.strip()}
    solo = None
    if "--solo" in argv:
        solo = {x.strip().lower() for x in argv[argv.index("--solo") + 1].split(",") if x.strip()}
    intentos = max(1, int(_env("SYNC_FINANCIERO_REINTENTOS", "2")))
    espera = max(0, int(_env("SYNC_FINANCIERO_ESPERA_SEG", "60")))

    resultados = []
    for objeto, base, columnas in OBJETOS:
        if (solo is not None and objeto.lower() not in solo) or objeto.lower() in omitir:
            log.info("[%s] omitido (--solo / SYNC_FINANCIERO_OMITIR).", objeto)
            continue
        resultados.append(sincronizar_objeto(objeto, base, columnas, destino, origenes, intentos, espera, log))

    log.info("--- Resumen ---")
    log.info("%-30s %-10s %-7s %10s %10s", "objeto", "origen", "estado", "leidas", "cargadas")
    for r in resultados:
        log.info("%-30s %-10s %-7s %10s %10s", r["objeto"], r["base"], r["estado"], r["leidas"] if r["leidas"] is not None else "-", r["cargadas"] if r["cargadas"] is not None else "-")
    fallidos = [r["objeto"] for r in resultados if r["estado"] != "OK"]
    if fallidos:
        log.error("Fallaron %d objeto(s): %s", len(fallidos), ", ".join(fallidos))
    log.info("=== FIN sincronización Financiero (resultado=%s) ===", "CON ERRORES" if fallidos else "OK")
    return 1 if fallidos else 0


if __name__ == "__main__":
    sys.exit(main())
