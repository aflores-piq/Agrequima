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
