"""Utilidades compartidas por los servicios que arman DataFrames de
pandas a partir de filas de SQLAlchemy."""

import pandas as pd

from app.schemas.dashboard import PuntoAcumuladoAnual, SerieAcumuladoAnual


def sin_nan(df: pd.DataFrame) -> pd.DataFrame:
    """pandas convierte una columna con solo valores None (o texto
    mezclado con None) en NaN (float) al inferir su dtype, lo que rompe
    la validación de Pydantic para campos `str | None` (llega `nan` en
    vez de `None`) y se ve mal en el Excel exportado. Se normaliza antes
    de convertir el DataFrame a registros."""
    return df.astype(object).where(pd.notnull(df), None)


def normalizar_rango_meses(mes_desde: int | None, mes_hasta: int) -> tuple[int, int]:
    """Rango de meses (Desde, Hasta) de los selectores de mes. `mes_hasta`
    es el mes de corte de siempre; `mes_desde` es opcional (por defecto 1,
    enero, o sea el acumulado enero→mes de antes). Un Desde posterior al
    Hasta nunca es un estado válido: el Desde se ajusta al Hasta."""
    desde = mes_desde or 1
    return min(desde, mes_hasta), mes_hasta


def meses_del_rango(mes_desde: int, mes_hasta: int) -> range:
    """Meses (1-12) incluidos en el rango, ambos extremos incluidos."""
    return range(mes_desde, mes_hasta + 1)


def filtrar_rango_meses(query, mes_expr, mes_desde: int, mes_hasta: int):
    """Acota la query al rango de meses Desde..Hasta (ambos incluidos).
    Con Desde=1 (enero) no se agrega la cota inferior: la consulta queda
    exactamente igual que el acumulado enero→mes de siempre."""
    if mes_desde > 1:
        query = query.filter(mes_expr >= mes_desde)
    return query.filter(mes_expr <= mes_hasta)


def series_multianual_desde_df(df: pd.DataFrame) -> list[SerieAcumuladoAnual]:
    """Convierte un DataFrame en formato largo (columnas anio, mes,
    cif_usd_acumulado) al formato anidado que espera el JSON del
    dashboard: una serie por año, en el mismo orden en que aparecen en
    el DataFrame (año seleccionado primero, luego los anteriores)."""
    return [
        SerieAcumuladoAnual(
            anio=int(anio),
            puntos=[
                PuntoAcumuladoAnual(mes=int(fila.mes), cif_usd_acumulado=float(fila.cif_usd_acumulado))
                for fila in grupo.itertuples()
            ],
        )
        for anio, grupo in df.groupby("anio", sort=False)
    ]
