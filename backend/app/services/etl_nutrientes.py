"""ETL de licencias de importación de nutrientes.

Mismo patrón que etl_plaguicidas.py: recibe los archivos ya en memoria
(bytes) desde un UploadFile, sin rutas de disco fijas. A diferencia de
plaguicidas, el cruce de agrupación es por NOMBRE COMERCIAL normalizado,
no por ingrediente activo, según el diccionario "Agrupador de
Fertilizantes Importaciones.xlsx" (hoja "Diccionario Productos").
"""

import datetime
import logging
from io import BytesIO

import pandas as pd
from sqlalchemy import bindparam, text

from app.core.db import engine
from app.schemas.cargas import ResumenCargaNutrientes
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

HOJA_AGRUPADOR = "Diccionario Productos"

# Límites reales de las columnas NVARCHAR en dbo.Nutrientes. Mismo
# propósito que LIMITES_COLUMNAS en etl_plaguicidas.py.
LIMITES_COLUMNAS = {
    "Tipo": 50,
    "No_Licencia": 50,
    "No_Registro": 50,
    "NombreComercial": 200,
    "EmpresaImportadora": 200,
    "UMedida": 50,
    "PaisProcedencia": 100,
    "PaisOrigen": 100,
    "AduanadeIngreso": 100,
    "Exportador": 150,
    "Concentraciones": 150,
    "Componentes": 500,
    "VENTANILLA": 50,
}

_COLUMNAS_ESPERADAS = [
    "Tipo", "No_Licencia", "No_Registro", "NombreComercial", "EmpresaImportadora",
    "FechaEmision", "UMedida", "Cantidad", "PaisProcedencia", "PaisOrigen",
    "AduanadeIngreso", "CIF_dolares", "CIF_Q", "TimbresQ", "Exportador",
    "Concentraciones", "Componentes", "VENTANILLA",
]

_COLUMNAS_TEXTO = [
    "Tipo", "NombreComercial", "EmpresaImportadora",
    "UMedida", "PaisProcedencia", "PaisOrigen", "AduanadeIngreso", "Exportador",
    "Concentraciones", "Componentes", "VENTANILLA",
]


def _cargar_agrupador_nutrientes(contenido: bytes) -> pd.DataFrame:
    df = pd.read_excel(BytesIO(contenido), sheet_name=HOJA_AGRUPADOR)
    df = df.rename(columns={"Nombre Comercial (MAGA)": "NombreComercialRaw"})

    if "NombreComercialRaw" not in df.columns or "Producto Agrupado" not in df.columns:
        raise ValueError(
            "El archivo de agrupador de fertilizantes no tiene las columnas "
            "esperadas 'Nombre Comercial (MAGA)' y 'Producto Agrupado' en la "
            f"hoja '{HOJA_AGRUPADOR}'."
        )

    tiene_codigo = "Codigo" in df.columns
    filas = []
    for _, fila in df.iterrows():
        if es_vacio(fila["NombreComercialRaw"]):
            continue
        producto_agrupado = limpiar_texto(fila["Producto Agrupado"])
        codigo = limpiar_texto(fila["Codigo"]) if tiene_codigo else None
        # Algunas celdas combinan varias variantes de nombre separadas por
        # "/" (ej. "FORMULA 12-24-12 / FORMULA QUIMICA 12-24-12") que
        # apuntan al mismo Producto Agrupado: se separan en alias
        # independientes antes de normalizar, para no perder coincidencias.
        for alias in str(fila["NombreComercialRaw"]).split("/"):
            clave = normalizar(alias)
            if clave is None:
                continue
            filas.append({
                "NombreComercial_Key": clave,
                "ProductoAgrupado": producto_agrupado,
                "Codigo": codigo,
            })

    resultado = (
        pd.DataFrame(filas, columns=["NombreComercial_Key", "ProductoAgrupado", "Codigo"])
        .dropna(subset=["NombreComercial_Key", "ProductoAgrupado"])
        .drop_duplicates(subset=["NombreComercial_Key"])
    )

    resultado.to_sql("stg_AgrupadorNutrientes", engine, if_exists="replace", index=False)
    return resultado


def _leer_crudo_nutrientes(contenido: bytes, es_csv: bool) -> pd.DataFrame:
    # Algunos archivos traen una fila de título (y/o filas en blanco)
    # arriba de los encabezados reales (ej. "Consolidado Licencias de
    # Importación 2023 al mes de diciembre") — no se puede asumir que la
    # fila 0 siempre sea el encabezado real.
    if es_csv:
        # Viene en UTF-8 con BOM y algunos encabezados con espacios extra
        # (ej. " CIF_dolares "), de ahí encoding="utf-8-sig".
        crudo_sin_encabezado = pd.read_csv(
            BytesIO(contenido), sep=";", encoding="utf-8-sig", dtype=str, header=None, nrows=10
        )
        fila_encabezado = detectar_fila_encabezado(crudo_sin_encabezado, _COLUMNAS_ESPERADAS)
        df = pd.read_csv(
            BytesIO(contenido), sep=";", encoding="utf-8-sig", dtype=str, header=fila_encabezado
        )
        df.columns = [c.strip() for c in df.columns]

        faltantes = set(_COLUMNAS_ESPERADAS) - set(df.columns)
        if faltantes:
            raise ValueError(
                f"El archivo de nutrientes no tiene las columnas esperadas: "
                f"{sorted(faltantes)}. Encabezados encontrados: {list(df.columns)}"
            )
        return df

    # Un .xlsx real puede traer los encabezados en español legible
    # ("Número de Licencia", "Valor CIF $"...) en vez de los nombres
    # internos del .csv — el ORDEN de columnas sí es estable (verificado
    # contra un archivo real), así que una vez ubicada la fila de
    # encabezado se asignan los nombres internos por posición, igual que
    # ya hace etl_plaguicidas.py, en vez de exigir coincidencia exacta de
    # texto.
    excel_file = pd.ExcelFile(BytesIO(contenido))
    crudo_sin_encabezado = excel_file.parse(header=None, nrows=10)
    fila_encabezado = detectar_fila_encabezado(crudo_sin_encabezado, _COLUMNAS_ESPERADAS)
    df = excel_file.parse(header=fila_encabezado)

    if df.shape[1] < len(_COLUMNAS_ESPERADAS):
        raise ValueError(
            f"El archivo de nutrientes tiene {df.shape[1]} columnas, se esperaban al "
            f"menos {len(_COLUMNAS_ESPERADAS)}. Encabezados encontrados: {list(df.columns)}"
        )
    df = df.iloc[:, : len(_COLUMNAS_ESPERADAS)].copy()
    df.columns = _COLUMNAS_ESPERADAS
    return df


def _mapear_tipo_nutriente(valor: str | None) -> str | None:
    """"." (o vacío) en la columna Tipo del archivo de nutrientes
    significa "Licencias" -- confirmado por el cliente, ya no es un
    valor ambiguo. `valor` ya pasó por limpiar_texto() acá arriba, así
    que "vacío" llega como None."""
    if valor is None or valor == ".":
        return "Licencias"
    return valor


def _filtrar_solo_con_f_en_no_registro(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Filtro permanente: solo se cargan filas cuyo No_Registro contiene
    la letra "F" (case-insensitive) -- las demás (ej. "..._ENMIENDA_...",
    IDs puramente numéricos) se descartan en silencio, sin error, en
    TODO archivo consolidado de ahora en adelante. Se aplica acá (no en
    el archivo de origen) para que quede visible cuántas filas se
    descartaron en el resumen de la carga."""
    contiene_f = df["No_Registro"].apply(
        lambda v: isinstance(v, str) and "F" in v.upper()
    )
    descartadas = int((~contiene_f).sum())
    return df[contiene_f].copy(), descartadas


def _cargar_nutrientes(contenido: bytes, es_csv: bool = True) -> tuple[pd.DataFrame, list[dict], int]:
    df = _leer_crudo_nutrientes(contenido, es_csv)

    for col in _COLUMNAS_TEXTO:
        df[col] = df[col].apply(limpiar_texto)

    if es_csv:
        # DD/MM/YYYY en texto plano, como llega en el CSV.
        fecha_emision = pd.to_datetime(df["FechaEmision"], format="%d/%m/%Y", errors="coerce")
    else:
        # En un .xlsx la celda de fecha normalmente ya llega tipada
        # (datetime nativo). Pero se confirmó en producción (carga del
        # 2026-08-27, 260 filas con día/mes invertido) que un mismo
        # archivo puede traer un bloque de filas con la celda en TEXTO
        # "DD/MM/YYYY" aunque la columna se vea formateada como Fecha en
        # Excel — el formato de celda y el tipo de valor real son cosas
        # independientes en el .xlsx (confirmado con ISNUMERO=FALSO sobre
        # la celda real). Si se deja pd.to_datetime() adivinar el formato
        # de ese texto, asume MM/DD/YYYY e invierte día/mes. Por eso se
        # resuelve celda por celda: la que ya es datetime se deja tal
        # cual (no se reinterpreta), la que es texto se parsea con
        # day-first explícito, igual que el CSV.
        def _fecha_celda_excel(valor):
            if pd.isna(valor):
                return pd.NaT
            if isinstance(valor, datetime.date):
                return pd.Timestamp(valor)
            return pd.to_datetime(valor, format="%d/%m/%Y", errors="coerce")

        fecha_emision = pd.to_datetime(df["FechaEmision"].apply(_fecha_celda_excel))

    salida = pd.DataFrame({
        "Tipo": df["Tipo"].apply(_mapear_tipo_nutriente),
        # a_texto_id (no limpiar_texto): en un Excel, una licencia/registro
        # puramente numérico llega como float (ej. 123.0) y hay que quitar
        # el ".0", igual que RECIBO en etl_plaguicidas.py.
        "No_Licencia": df["No_Licencia"].apply(a_texto_id),
        "No_Registro": df["No_Registro"].apply(a_texto_id),
        "NombreComercial": df["NombreComercial"],
        "NombreComercial_Key": df["NombreComercial"].apply(normalizar),
        "EmpresaImportadora": df["EmpresaImportadora"],
        "FechaEmision": fecha_emision.dt.strftime("%Y-%m-%d"),
        "anio": fecha_emision.dt.year,
        "UMedida": df["UMedida"],
        "Cantidad": pd.to_numeric(df["Cantidad"], errors="coerce"),
        "PaisProcedencia": df["PaisProcedencia"],
        "PaisOrigen": df["PaisOrigen"],
        "AduanadeIngreso": df["AduanadeIngreso"],
        "CIF_dolares": df["CIF_dolares"].apply(limpiar_moneda),
        "CIF_Q": df["CIF_Q"].apply(limpiar_moneda),
        "TimbresQ": df["TimbresQ"].apply(limpiar_moneda),
        "Exportador": df["Exportador"],
        "Concentraciones": df["Concentraciones"],
        "Componentes": df["Componentes"],
        "VENTANILLA": df["VENTANILLA"],
    })

    salida, filas_descartadas_sin_f = _filtrar_solo_con_f_en_no_registro(salida)
    salida, advertencias_truncado = truncar_columnas(salida, LIMITES_COLUMNAS)

    return salida, advertencias_truncado, filas_descartadas_sin_f


def _mes_maximo_cargado_por_anio(anios: list[int]) -> dict[int, int]:
    """Último mes ya guardado en dbo.Nutrientes, por año (0 si ese año
    todavía no tiene ningún dato) — usado para solo cargar el mes nuevo."""
    if not anios:
        return {}
    consulta = text(
        "SELECT anio, MAX(MONTH(FechaEmision)) AS mes_max "
        "FROM dbo.Nutrientes WHERE anio IN :anios GROUP BY anio"
    ).bindparams(bindparam("anios", expanding=True))
    with engine.connect() as conn:
        filas = conn.execute(consulta, {"anios": anios}).all()
    return {int(a): int(m) for a, m in filas}


def _filtrar_solo_mes_nuevo(df: pd.DataFrame) -> tuple[pd.DataFrame, int, list[int]]:
    """Deja únicamente las filas de meses posteriores al último mes ya
    cargado en dbo.Nutrientes para el año de cada fila — mismo criterio
    que _filtrar_solo_mes_nuevo en etl_plaguicidas.py."""
    if df.empty:
        return df, 0, []

    anios_presentes = sorted({int(a) for a in df["anio"].dropna().unique()})
    mes_maximo_por_anio = _mes_maximo_cargado_por_anio(anios_presentes)

    # FechaEmision ya viene "YYYY-MM-DD"; una fila con fecha no parseable
    # (NaN) no tiene mes que comparar, así que se trata como "nueva" (se
    # deja pasar tal cual se comportaba antes de este filtro).
    mes_de_la_fila = pd.to_numeric(df["FechaEmision"].str.slice(5, 7), errors="coerce")
    tope_de_la_fila = df["anio"].map(lambda a: mes_maximo_por_anio.get(int(a), 0) if pd.notna(a) else -1)
    es_mes_nuevo = mes_de_la_fila.isna() | (mes_de_la_fila > tope_de_la_fila)

    filas_ya_cargadas = int((~es_mes_nuevo).sum())
    meses_nuevos = sorted({int(m) for m in mes_de_la_fila[es_mes_nuevo].dropna().unique()})
    return df[es_mes_nuevo].copy(), filas_ya_cargadas, meses_nuevos


def procesar_carga_nutrientes(
    contenido_nutrientes: bytes,
    nombre_archivo_nutrientes: str,
    contenido_agrupador: bytes | None,
    usuario_id: int,
) -> ResumenCargaNutrientes:
    logger.info(
        "Iniciando carga de nutrientes: archivo=%s usuario_id=%s agrupador=%s",
        nombre_archivo_nutrientes, usuario_id, contenido_agrupador is not None,
    )
    try:
        agrupador_actualizado = False
        claves_agrupador_nuevas = None

        if contenido_agrupador is not None:
            df_agrupador = _cargar_agrupador_nutrientes(contenido_agrupador)
            claves_agrupador_nuevas = len(df_agrupador)
            with engine.begin() as conn:
                conn.execute(text("EXEC dbo.usp_ActualizarAgrupadorNutrientes;"))
            agrupador_actualizado = True

        es_csv = nombre_archivo_nutrientes.lower().endswith(".csv")
        df_nutrientes, advertencias_trunc, filas_descartadas_sin_f = _cargar_nutrientes(
            contenido_nutrientes, es_csv
        )
        df_nutrientes, filas_ya_cargadas, meses_nuevos = _filtrar_solo_mes_nuevo(df_nutrientes)
        df_nutrientes.to_sql("stg_Nutrientes", engine, if_exists="replace", index=False)

        with engine.connect() as conn:
            max_log_id_antes = conn.execute(
                text("SELECT ISNULL(MAX(LogId), 0) FROM dbo.log_ExcepcionesAgrupadorNutrientes")
            ).scalar()

        with engine.begin() as conn:
            conn.execute(
                text("EXEC dbo.usp_CargarNutrientes @UserId = :userid;"),
                {"userid": usuario_id},
            )

        with engine.connect() as conn:
            filas_sin_agrupador = conn.execute(
                text(
                    "SELECT COUNT(*) FROM dbo.log_ExcepcionesAgrupadorNutrientes "
                    "WHERE LogId > :max_id"
                ),
                {"max_id": max_log_id_antes},
            ).scalar()
    except Exception as exc:
        logger.exception("Falló la carga de nutrientes (archivo=%s)", nombre_archivo_nutrientes)
        registrar_auditoria(
            "Nutrientes", nombre_archivo_nutrientes, usuario_id, None, None, "Error", str(exc)
        )
        raise

    estado = "ConExcepciones" if filas_sin_agrupador else "OK"

    resumen = ResumenCargaNutrientes(
        filas_cargadas=len(df_nutrientes),
        anios=sorted({int(a) for a in df_nutrientes["anio"].dropna().unique()}),
        meses_nuevos=meses_nuevos,
        filas_ya_cargadas=filas_ya_cargadas,
        filas_truncadas=len(advertencias_trunc),
        filas_descartadas_sin_f=filas_descartadas_sin_f,
        filas_sin_agrupador=int(filas_sin_agrupador),
        agrupador_actualizado=agrupador_actualizado,
        claves_agrupador_nuevas=claves_agrupador_nuevas,
        estado=estado,
    )

    registrar_auditoria(
        "Nutrientes",
        nombre_archivo_nutrientes,
        usuario_id,
        resumen.filas_cargadas,
        resumen.filas_sin_agrupador,
        estado,
        None,
    )
    logger.info(
        "Carga de nutrientes finalizada: archivo=%s estado=%s filas=%s sin_agrupador=%s",
        nombre_archivo_nutrientes, estado, resumen.filas_cargadas, resumen.filas_sin_agrupador,
    )
    return resumen
