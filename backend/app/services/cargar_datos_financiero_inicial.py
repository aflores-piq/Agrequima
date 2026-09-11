"""Carga inicial (UNA SOLA VEZ) de los 7 CSV reales exportados de
CONTACC hacia las tablas del módulo Financiero: BalanceSaldos,
BalanceGeneral, CatalogoCuentas, CentrosDeCosto, Presupuestos,
AsociadosCuota, ChequesCirculacion.

Esto NO es el sync nocturno (sync_piq_ia.py no toca estas tablas
todavía, a propósito) -- es carga manual, pensada para tener datos
reales con los que construir y probar los dashboards de Financiero
antes de que el sync contra CONTACC esté disponible.

Mismo patrón que el resto de la app (pandas + SQLAlchemy) y mismo
concepto que 03_cargar_datos_iniciales.sql: cada CSV crudo (sin
encabezado) sube tal cual a su stg_ correspondiente
(`if_exists="replace"`, igual que etl_plaguicidas.py/etl_nutrientes.py
-- pandas es dueño del esquema real de cada stg_, la definición de
db/agrequima_schema_sql_server.sql es solo la forma inicial/vacía), y
de ahí un TRUNCATE + INSERT hacia la tabla final con los tipos ya
convertidos.

Los 7 CSV viven en docs/legacy/financiero/ (nombre real de la vista de
origen), columnas en el mismo orden que las tablas finales -- ver cada
función _cargar_* de acá abajo para el orden exacto, confirmado
contra los datos reales antes de escribir esto (conteos de filas y
longitud máxima de texto por columna, sin truncamientos).

Uso:
    python -m app.services.cargar_datos_financiero_inicial
"""

import logging
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from app.core.db import engine

logger = logging.getLogger(__name__)

CARPETA_CSV = Path(__file__).resolve().parents[3] / "docs" / "legacy" / "financiero"


def _leer_csv(nombre_archivo: str, columnas: list[str]) -> pd.DataFrame:
    return pd.read_csv(
        CARPETA_CSV / nombre_archivo, header=None, names=columnas, encoding="utf-8-sig", dtype=str
    )


def _a_numerico(df: pd.DataFrame, columnas: list[str]) -> None:
    for col in columnas:
        df[col] = pd.to_numeric(df[col], errors="coerce")


def _nan_a_none(df: pd.DataFrame) -> pd.DataFrame:
    return df.where(pd.notnull(df), None)


def _cargar_balance_saldos() -> int:
    columnas = [
        "emp_nit", "Cta_Codigo", "Cta_Descripcion", "Sal_Ano", "Sal_Mes",
        "Debitos", "Creditos", "Saldo", "Cod_Centro",
    ]
    df = _leer_csv("vw_piq_balance_saldos.csv", columnas)
    _a_numerico(df, ["Sal_Ano", "Sal_Mes", "Debitos", "Creditos", "Saldo"])
    df = _nan_a_none(df)
    df.to_sql("stg_BalanceSaldos", engine, if_exists="replace", index=False)

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE dbo.BalanceSaldos"))
        conn.execute(text(
            """
            INSERT INTO dbo.BalanceSaldos
                (emp_nit, Cta_Codigo, Cta_Descripcion, Sal_Ano, Sal_Mes, Debitos, Creditos, Saldo, Cod_Centro, fechamod)
            SELECT emp_nit, Cta_Codigo, Cta_Descripcion,
                   CAST(Sal_Ano AS INT), CAST(Sal_Mes AS INT),
                   CAST(Debitos AS DECIMAL(18,2)), CAST(Creditos AS DECIMAL(18,2)), CAST(Saldo AS DECIMAL(18,2)),
                   Cod_Centro, GETDATE()
            FROM dbo.stg_BalanceSaldos
            """
        ))
    return len(df)


def _cargar_balance_general() -> int:
    columnas = [
        "emp_nit", "Cod_n1", "Nom_n1", "cod_n5", "nom_n5", "Sal_Ano", "Sal_Mes",
        "Debitos", "Creditos", "Saldo", "Inicial",
    ]
    df = _leer_csv("vw_piq_balance_general.csv", columnas)
    _a_numerico(df, ["Sal_Ano", "Sal_Mes", "Debitos", "Creditos", "Saldo", "Inicial"])
    df = _nan_a_none(df)
    df.to_sql("stg_BalanceGeneral", engine, if_exists="replace", index=False)

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE dbo.BalanceGeneral"))
        conn.execute(text(
            """
            INSERT INTO dbo.BalanceGeneral
                (emp_nit, Cod_n1, Nom_n1, cod_n5, nom_n5, Sal_Ano, Sal_Mes, Debitos, Creditos, Saldo, Inicial, fechamod)
            SELECT emp_nit, Cod_n1, Nom_n1, cod_n5, nom_n5,
                   CAST(Sal_Ano AS INT), CAST(Sal_Mes AS INT),
                   CAST(Debitos AS DECIMAL(18,2)), CAST(Creditos AS DECIMAL(18,2)), CAST(Saldo AS DECIMAL(18,2)), CAST(Inicial AS DECIMAL(18,2)),
                   GETDATE()
            FROM dbo.stg_BalanceGeneral
            """
        ))
    return len(df)


def _cargar_catalogo_cuentas() -> int:
    columnas = ["cta_nivel", "Codigo_N1", "Nombre_n1", "Codigo_N5", "Nombre_N5"]
    df = _leer_csv("vw_catalogo_cuentas.csv", columnas)
    _a_numerico(df, ["cta_nivel"])
    df = _nan_a_none(df)
    df.to_sql("stg_CatalogoCuentas", engine, if_exists="replace", index=False)

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE dbo.CatalogoCuentas"))
        conn.execute(text(
            """
            INSERT INTO dbo.CatalogoCuentas
                (cta_nivel, Codigo_N1, Nombre_n1, Codigo_N5, Nombre_N5, fechamod)
            SELECT CAST(cta_nivel AS INT), Codigo_N1, Nombre_n1, Codigo_N5, Nombre_N5, GETDATE()
            FROM dbo.stg_CatalogoCuentas
            """
        ))
    return len(df)


def _cargar_centros_de_costo() -> int:
    columnas = ["emp_nit", "Cod_centro", "Des_centro", "nivel", "CC_Grupo1"]
    df = _leer_csv("vw_piq_centrosdecosto.csv", columnas)
    _a_numerico(df, ["nivel"])
    df = _nan_a_none(df)
    df.to_sql("stg_CentrosDeCosto", engine, if_exists="replace", index=False)

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE dbo.CentrosDeCosto"))
        conn.execute(text(
            """
            INSERT INTO dbo.CentrosDeCosto
                (emp_nit, Cod_centro, Des_centro, nivel, CC_Grupo1, fechamod)
            SELECT emp_nit, Cod_centro, Des_centro, CAST(nivel AS INT), CC_Grupo1, GETDATE()
            FROM dbo.stg_CentrosDeCosto
            """
        ))
    return len(df)


def _cargar_presupuestos() -> int:
    columnas = ["emp_nit", "par_ano", "par_mes", "cta_codigo", "pre_presupuesto", "cod_centro"]
    df = _leer_csv("vw_piq_presupuestos.csv", columnas)
    _a_numerico(df, ["par_ano", "par_mes", "pre_presupuesto"])
    df = _nan_a_none(df)
    df.to_sql("stg_Presupuestos", engine, if_exists="replace", index=False)

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE dbo.Presupuestos"))
        conn.execute(text(
            """
            INSERT INTO dbo.Presupuestos
                (emp_nit, par_ano, par_mes, cta_codigo, pre_presupuesto, cod_centro, fechamod)
            SELECT emp_nit, CAST(par_ano AS INT), CAST(par_mes AS INT), cta_codigo,
                   CAST(pre_presupuesto AS DECIMAL(18,2)), cod_centro, GETDATE()
            FROM dbo.stg_Presupuestos
            """
        ))
    return len(df)


def _cargar_asociados_cuota() -> int:
    columnas = ["emp_nit", "Sal_Ano", "cod_n5", "nom_n5", "grupo", "nombre_mostrar", "cuota"]
    df = _leer_csv("vw_piq_asociados_cuota.csv", columnas)
    _a_numerico(df, ["Sal_Ano", "cuota"])
    df = _nan_a_none(df)
    df.to_sql("stg_AsociadosCuota", engine, if_exists="replace", index=False)

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE dbo.AsociadosCuota"))
        conn.execute(text(
            """
            INSERT INTO dbo.AsociadosCuota
                (emp_nit, Sal_Ano, cod_n5, nom_n5, grupo, nombre_mostrar, cuota, fechamod)
            SELECT emp_nit, CAST(Sal_Ano AS INT), cod_n5, nom_n5, grupo, nombre_mostrar,
                   CAST(cuota AS DECIMAL(18,2)), GETDATE()
            FROM dbo.stg_AsociadosCuota
            """
        ))
    return len(df)


def _cargar_cheques_circulacion() -> int:
    columnas = [
        "ban_codigo", "cta_numero", "cta_nombre", "Cta_Codigo", "par_ano", "par_mes",
        "doc_numero", "doc_fecha", "doc_fchcobro", "doc_nombre", "doc_motivo", "doc_monto",
    ]
    df = _leer_csv("vw_piq_cheques_circulacion.csv", columnas)
    _a_numerico(df, ["par_ano", "par_mes", "doc_monto"])
    df["doc_fecha"] = pd.to_datetime(df["doc_fecha"], errors="coerce")
    df["doc_fchcobro"] = pd.to_datetime(df["doc_fchcobro"], errors="coerce")
    df = _nan_a_none(df)
    df.to_sql("stg_ChequesCirculacion", engine, if_exists="replace", index=False)

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE dbo.ChequesCirculacion"))
        conn.execute(text(
            """
            INSERT INTO dbo.ChequesCirculacion
                (ban_codigo, cta_numero, cta_nombre, Cta_Codigo, par_ano, par_mes,
                 doc_numero, doc_fecha, doc_fchcobro, doc_nombre, doc_motivo, doc_monto, fechamod)
            SELECT ban_codigo, cta_numero, cta_nombre, Cta_Codigo,
                   CAST(par_ano AS INT), CAST(par_mes AS INT),
                   doc_numero, doc_fecha, doc_fchcobro, doc_nombre, doc_motivo,
                   CAST(doc_monto AS DECIMAL(18,2)), GETDATE()
            FROM dbo.stg_ChequesCirculacion
            """
        ))
    return len(df)


CARGAS = [
    ("BalanceSaldos", _cargar_balance_saldos),
    ("BalanceGeneral", _cargar_balance_general),
    ("CatalogoCuentas", _cargar_catalogo_cuentas),
    ("CentrosDeCosto", _cargar_centros_de_costo),
    ("Presupuestos", _cargar_presupuestos),
    ("AsociadosCuota", _cargar_asociados_cuota),
    ("ChequesCirculacion", _cargar_cheques_circulacion),
]


def main() -> int:
    hubo_error = False
    for nombre_tabla, funcion in CARGAS:
        try:
            filas = funcion()
            logger.info("OK   %-20s %d filas", nombre_tabla, filas)
            print(f"OK   {nombre_tabla:<20} {filas} filas")
        except Exception:
            hubo_error = True
            logger.exception("ERROR al cargar %s", nombre_tabla)
            print(f"ERROR al cargar {nombre_tabla}")
    return 1 if hubo_error else 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(main())
