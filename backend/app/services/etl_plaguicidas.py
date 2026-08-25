"""ETL de importaciones de plaguicidas.

Puerto del script Carga_Importaciones.py a un servicio invocable desde un
endpoint HTTP: en vez de leer archivos fijos del disco, recibe el
contenido del Excel crudo de importaciones y, opcionalmente, el de
nomenclatura, ya en memoria (bytes) desde un UploadFile. Conserva la
lógica de normalización, truncado seguro por columna, manejo de combos de
porcentaje y detección de filas basura del script original.
"""

import logging
from io import BytesIO

import pandas as pd
from sqlalchemy import bindparam, text

from app.core.db import engine
from app.schemas.cargas import ResumenCargaPlaguicidas
from app.services.auditoria import registrar_auditoria
from app.services.text_utils import (
    a_texto_id,
    detectar_fila_encabezado,
    es_vacio,
    limpiar_moneda,
    limpiar_texto,
    normalizar,
    truncar_columnas,
)

logger = logging.getLogger(__name__)

HOJA_NOMENCLATURA = "Nomenclatura agrupada"

# Mapeo posicional del archivo crudo -> nombres internos. Los encabezados
# originales cambian de nombre entre archivos (ej. "RECIBO" un mes,
# "RECIBO INTERNO VAI-MAGA" otro mes), pero el ORDEN de las columnas se
# mantiene, así que se leen por posición, no por nombre.
NOMBRES_INTERNOS = [
    "RECIBO", "SerieSAT", "RecSAT", "APLICACIoN", "RECIBOSAT", "FECHA",
    "IMPORTADOR", "PRODUCTO", "INGREDIENTEACT", "EXPORTADOR", "ORIGEN",
    "pct", "CANTIDAD", "UNMEDIDA", "CIFusd", "CIFQ", "CAMBIO", "Empresa", "UMSP",
]

FORMATO_FECHA = "%Y/%m/%d"

# Límites reales de las columnas VARCHAR en dbo.Importacion. Se usan para
# truncar de forma segura ANTES de insertar, en vez de dejar que SQL
# Server rechace todo el lote con "String or binary data would be
# truncated".
LIMITES_COLUMNAS = {
    "recibointerno": 80,
    "serie_sat": 70,
    "numero_recibo_sat": 80,
    "aplicacion": 150,
    "fecha": 15,
    "importador": 250,
    "producto": 250,
    "ingrediente_act": 350,
    "exportador": 350,
    "origen": 50,
    "unidad_medida": 50,
    "tipo_cambio": 50,
    "institucion": 150,
}


def parsear_porcentaje(valor, advertencias: dict) -> float | None:
    """Convierte el campo de porcentaje a fracción decimal (ej. '50%' ->
    0.50). Los combos ('10% + 40%') no se pueden representar en una sola
    columna decimal(18,2) sin perder información: se dejan en NULL y se
    cuentan en `advertencias`."""
    if es_vacio(valor):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)

    texto = str(valor).strip()
    if "+" in texto:
        advertencias["combos"] += 1
        return None

    texto = texto.replace("%", "").strip()
    try:
        return float(texto) / 100.0
    except ValueError:
        advertencias["no_parseables"] += 1
        return None


def _detectar_hoja_importaciones(excel_file: pd.ExcelFile) -> str:
    """Encuentra la hoja de datos dentro del archivo (el nombre cambia
    cada año, ej. 'ImpPlag2026' -> 'ImpPlag2027')."""
    hojas = excel_file.sheet_names
    if len(hojas) == 1:
        return hojas[0]
    candidatas = [h for h in hojas if h.upper().startswith("IMPPLAG")]
    if len(candidatas) == 1:
        return candidatas[0]
    raise ValueError(
        f"No se pudo determinar automáticamente la hoja de datos del archivo "
        f"de importaciones. Hojas disponibles: {hojas}."
    )


def _cargar_nomenclatura(contenido: bytes) -> pd.DataFrame:
    df = pd.read_excel(BytesIO(contenido), sheet_name=HOJA_NOMENCLATURA)
    df = df.rename(columns={
        "INGREDIENTE ACT.": "IngredienteRaw",
        "Agrupación estandarizada_Nomenclatura": "Agrupador",
    })

    if "IngredienteRaw" not in df.columns or "Agrupador" not in df.columns:
        raise ValueError(
            "El archivo de nomenclatura no tiene las columnas esperadas "
            "'INGREDIENTE ACT.' y 'Agrupación estandarizada_Nomenclatura' "
            f"en la hoja '{HOJA_NOMENCLATURA}'."
        )

    df["IngredienteActivo_Key"] = df["IngredienteRaw"].apply(normalizar)
    df["Agrupador"] = df["Agrupador"].apply(limpiar_texto)
    df["Codigo"] = df["Codigo"].apply(limpiar_texto) if "Codigo" in df.columns else None

    df = (
        df[["IngredienteActivo_Key", "Agrupador", "Codigo"]]
        .dropna(subset=["IngredienteActivo_Key", "Agrupador"])
        .drop_duplicates(subset=["IngredienteActivo_Key"])
    )

    df.to_sql("stg_Nomenclatura", engine, if_exists="replace", index=False)
    return df


def _leer_crudo_importaciones(contenido: bytes, es_csv: bool) -> pd.DataFrame:
    # Algunos archivos traen una fila de título (y/o filas en blanco)
    # arriba de los encabezados reales — no se puede asumir que la fila
    # 0 siempre sea el encabezado. Se leen las primeras filas sin
    # encabezado para ubicar la fila real antes de leer el archivo
    # completo (NOMBRES_INTERNOS son los encabezados históricamente
    # vistos en archivos reales, ver mapeo de columnas más abajo).
    if es_csv:
        # Mismas columnas y mismo orden que el Excel crudo (se leen por
        # posición más abajo, no por nombre). Separador ';', igual que el
        # CSV de licencias de nutrientes; encoding utf-8-sig por el BOM
        # que traen estos archivos.
        crudo_sin_encabezado = pd.read_csv(
            BytesIO(contenido), sep=";", encoding="utf-8-sig", dtype=str, header=None, nrows=10
        )
        fila_encabezado = detectar_fila_encabezado(crudo_sin_encabezado, NOMBRES_INTERNOS)
        return pd.read_csv(
            BytesIO(contenido), sep=";", encoding="utf-8-sig", dtype=str, header=fila_encabezado
        )

    excel_file = pd.ExcelFile(BytesIO(contenido))
    hoja = _detectar_hoja_importaciones(excel_file)
    crudo_sin_encabezado = excel_file.parse(sheet_name=hoja, header=None, nrows=10)
    fila_encabezado = detectar_fila_encabezado(crudo_sin_encabezado, NOMBRES_INTERNOS)
    return excel_file.parse(sheet_name=hoja, header=fila_encabezado)


def _cargar_importaciones(
    contenido: bytes, es_csv: bool = False
) -> tuple[pd.DataFrame, dict, list[dict], int]:
    df_crudo = _leer_crudo_importaciones(contenido, es_csv)

    if df_crudo.shape[1] < len(NOMBRES_INTERNOS):
        raise ValueError(
            f"El archivo tiene {df_crudo.shape[1]} columnas, se esperaban al "
            f"menos {len(NOMBRES_INTERNOS)}. Encabezados encontrados: "
            f"{list(df_crudo.columns)}"
        )

    df = df_crudo.iloc[:, :len(NOMBRES_INTERNOS)].copy()
    df.columns = NOMBRES_INTERNOS

    columnas_texto = [
        "IMPORTADOR", "PRODUCTO", "EXPORTADOR", "ORIGEN", "Empresa",
        "APLICACIoN", "SerieSAT", "UNMEDIDA",
    ]
    for col in columnas_texto:
        df[col] = df[col].apply(limpiar_texto)

    df["INGREDIENTEACT"] = df["INGREDIENTEACT"].apply(limpiar_texto)

    numero_recibo_sat = df["RECIBOSAT"]
    numero_recibo_sat = numero_recibo_sat.where(numero_recibo_sat.notna(), df["RecSAT"])

    advertencias_pct = {"combos": 0, "no_parseables": 0}

    if es_csv:
        # En un Excel estas celdas ya llegan tipadas (float/datetime); en
        # un CSV todo llega como texto ("6/01/2026", "$97,612.50"), así
        # que hay que parsear la fecha con dayfirst (formato guatemalteco
        # DD/MM/YYYY) y limpiar los montos antes de usarlos.
        fecha = pd.to_datetime(df["FECHA"], dayfirst=True, errors="coerce")
        cantidad = df["CANTIDAD"].apply(limpiar_moneda)
        cif_usd = df["CIFusd"].apply(limpiar_moneda)
        cif_q = df["CIFQ"].apply(limpiar_moneda)
        umsp = df["UMSP"].apply(limpiar_moneda)
    else:
        fecha = pd.to_datetime(df["FECHA"])
        cantidad = df["CANTIDAD"]
        cif_usd = df["CIFusd"]
        cif_q = df["CIFQ"]
        umsp = df["UMSP"]

    salida = pd.DataFrame({
        "anio": fecha.dt.year,
        "recibointerno": df["RECIBO"].apply(a_texto_id),
        "serie_sat": df["SerieSAT"],
        "numero_recibo_sat": numero_recibo_sat.apply(a_texto_id),
        "aplicacion": df["APLICACIoN"],
        "fecha": fecha.dt.strftime(FORMATO_FECHA),
        "importador": df["IMPORTADOR"],
        "producto": df["PRODUCTO"],
        "ingrediente_act": df["INGREDIENTEACT"],
        "ingrediente_key": df["INGREDIENTEACT"].apply(normalizar),
        "exportador": df["EXPORTADOR"],
        "origen": df["ORIGEN"],
        "porcentaje": df["pct"].apply(lambda v: parsear_porcentaje(v, advertencias_pct)),
        "cantidad": cantidad,
        "unidad_medida": df["UNMEDIDA"],
        "cif_USD": cif_usd,
        "cif_Q": cif_q,
        "tipo_cambio": df["CAMBIO"].apply(lambda x: None if es_vacio(x) else str(x)),
        "institucion": df["Empresa"],
        "umsp": umsp,
    })

    # Descarta filas basura de la hoja (sin ningún dato real de
    # transacción), ej. filas finales con "nan" en todas las columnas.
    antes = len(salida)
    salida = salida[
        salida["ingrediente_act"].notna()
        | salida["producto"].notna()
        | salida["importador"].notna()
    ].copy()
    filas_descartadas = antes - len(salida)

    salida, advertencias_truncado = truncar_columnas(salida, LIMITES_COLUMNAS)

    return salida, advertencias_pct, advertencias_truncado, filas_descartadas


def _mes_maximo_cargado_por_anio(anios: list[int]) -> dict[int, int]:
    """Último mes ya guardado en dbo.Importacion, por año (0 si ese año
    todavía no tiene ningún dato) — usado para solo cargar el mes nuevo."""
    if not anios:
        return {}
    consulta = text(
        "SELECT anio, MAX(CAST(SUBSTRING(fecha, 6, 2) AS INT)) AS mes_max "
        "FROM dbo.Importacion WHERE anio IN :anios GROUP BY anio"
    ).bindparams(bindparam("anios", expanding=True))
    with engine.connect() as conn:
        filas = conn.execute(consulta, {"anios": anios}).all()
    return {int(a): int(m) for a, m in filas}


def _filtrar_solo_mes_nuevo(df: pd.DataFrame) -> tuple[pd.DataFrame, int, list[int]]:
    """Deja únicamente las filas de meses posteriores al último mes ya
    cargado en dbo.Importacion para el año de cada fila — así una carga
    acumulada que repite meses ya guardados no los duplica (los ignora
    sin error), y solo se insertan los meses realmente nuevos."""
    if df.empty:
        return df, 0, []

    anios_presentes = sorted({int(a) for a in df["anio"].dropna().unique()})
    mes_maximo_por_anio = _mes_maximo_cargado_por_anio(anios_presentes)

    # fecha ya viene "YYYY/MM/DD"; una fila con fecha no parseable (NaN)
    # no tiene mes que comparar, así que se trata como "nueva" (se deja
    # pasar tal cual se comportaba antes de este filtro).
    mes_de_la_fila = pd.to_numeric(df["fecha"].str.slice(5, 7), errors="coerce")
    tope_de_la_fila = df["anio"].map(lambda a: mes_maximo_por_anio.get(int(a), 0) if pd.notna(a) else -1)
    es_mes_nuevo = mes_de_la_fila.isna() | (mes_de_la_fila > tope_de_la_fila)

    filas_ya_cargadas = int((~es_mes_nuevo).sum())
    meses_nuevos = sorted({int(m) for m in mes_de_la_fila[es_mes_nuevo].dropna().unique()})
    return df[es_mes_nuevo].copy(), filas_ya_cargadas, meses_nuevos


def procesar_carga_plaguicidas(
    contenido_importaciones: bytes,
    nombre_archivo_importaciones: str,
    contenido_nomenclatura: bytes | None,
    usuario_id: int,
) -> ResumenCargaPlaguicidas:
    logger.info(
        "Iniciando carga de plaguicidas: archivo=%s usuario_id=%s nomenclatura=%s",
        nombre_archivo_importaciones, usuario_id, contenido_nomenclatura is not None,
    )
    try:
        nomenclatura_actualizada = False
        claves_nomenclatura_nuevas = None

        if contenido_nomenclatura is not None:
            df_nomenclatura = _cargar_nomenclatura(contenido_nomenclatura)
            claves_nomenclatura_nuevas = len(df_nomenclatura)
            with engine.begin() as conn:
                conn.execute(text("EXEC dbo.usp_ActualizarNomenclatura;"))
            nomenclatura_actualizada = True

        es_csv = nombre_archivo_importaciones.lower().endswith(".csv")
        df_importaciones, advertencias_pct, advertencias_trunc, filas_descartadas = (
            _cargar_importaciones(contenido_importaciones, es_csv)
        )
        df_importaciones, filas_ya_cargadas, meses_nuevos = _filtrar_solo_mes_nuevo(df_importaciones)
        df_importaciones.to_sql("stg_Importacion", engine, if_exists="replace", index=False)

        with engine.connect() as conn:
            max_log_id_antes = conn.execute(
                text("SELECT ISNULL(MAX(LogId), 0) FROM dbo.log_ExcepcionesAgrupador")
            ).scalar()

        with engine.begin() as conn:
            conn.execute(
                text("EXEC dbo.usp_CargarImportacion @UserId = :userid;"),
                {"userid": usuario_id},
            )

        with engine.connect() as conn:
            filas_sin_agrupador = conn.execute(
                text(
                    "SELECT COUNT(*) FROM dbo.log_ExcepcionesAgrupador WHERE LogId > :max_id"
                ),
                {"max_id": max_log_id_antes},
            ).scalar()
    except Exception as exc:
        logger.exception("Falló la carga de plaguicidas (archivo=%s)", nombre_archivo_importaciones)
        registrar_auditoria(
            "Plaguicidas", nombre_archivo_importaciones, usuario_id, None, None, "Error", str(exc)
        )
        raise

    estado = "ConExcepciones" if filas_sin_agrupador else "OK"

    resumen = ResumenCargaPlaguicidas(
        filas_cargadas=len(df_importaciones),
        anios=sorted({int(a) for a in df_importaciones["anio"].dropna().unique()}),
        meses_nuevos=meses_nuevos,
        filas_ya_cargadas=filas_ya_cargadas,
        filas_descartadas=filas_descartadas,
        filas_truncadas=len(advertencias_trunc),
        combos_porcentaje=advertencias_pct["combos"],
        porcentajes_no_parseables=advertencias_pct["no_parseables"],
        filas_sin_agrupador=int(filas_sin_agrupador),
        nomenclatura_actualizada=nomenclatura_actualizada,
        claves_nomenclatura_nuevas=claves_nomenclatura_nuevas,
        estado=estado,
    )

    registrar_auditoria(
        "Plaguicidas",
        nombre_archivo_importaciones,
        usuario_id,
        resumen.filas_cargadas,
        resumen.filas_sin_agrupador,
        estado,
        None,
    )
    logger.info(
        "Carga de plaguicidas finalizada: archivo=%s estado=%s filas=%s sin_agrupador=%s",
        nombre_archivo_importaciones, estado, resumen.filas_cargadas, resumen.filas_sin_agrupador,
    )
    return resumen
