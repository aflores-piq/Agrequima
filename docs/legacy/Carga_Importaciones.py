"""
Proceso de carga: Importaciones de Plaguicidas + Nomenclatura Agrupada
------------------------------------------------------------------------
1. Lee el archivo crudo de importaciones y el de nomenclatura agrupada.
2. Normaliza el ingrediente activo (TRIM + UPPER + espacios colapsados)
   para poder cruzarlo de forma confiable.
3. Sube ambos a tablas de staging en SQL Server (dbo.stg_Nomenclatura,
   dbo.stg_Importacion), ya con los nombres/tipos alineados a la tabla
   final dbo.Importacion.
4. Ejecuta los stored procedures: actualizan el catálogo de nomenclatura
   e integran las importaciones a dbo.Importacion (estrategia DELETE +
   INSERT por año, ver 01_sql_ddl_procedimientos.sql).
5. Exporta un reporte Excel con las transacciones sin agrupador
   encontrado.

Requisitos:
    pip install pandas sqlalchemy pyodbc openpyxl
"""

import glob
import os
import re
import sys
from datetime import date

import pandas as pd
from sqlalchemy import create_engine, text

# =====================================================================
# CONFIGURACIÓN — ajustar antes de ejecutar
# =====================================================================
SERVER   = r"10.10.0.6,65280"
DATABASE = "Agrequima"
DRIVER   = "ODBC Driver 17 for SQL Server"
USUARIO  = "admindatos"
PASSWORD = "Basededatos2024"

CONN_STR = (
    f"mssql+pyodbc://{USUARIO}:{PASSWORD}@{SERVER}/{DATABASE}"
    f"?driver={DRIVER.replace(' ', '+')}"
)
# Nota de seguridad: para producción, mueve USUARIO/PASSWORD a variables
# de entorno o a un almacén de secretos en vez de dejarlos en el script.

# Id de usuario que se registra en la columna userid de dbo.Importacion
# para las cargas automáticas. Ajusta al id real que usa la aplicación
# para procesos de sistema (o dejar en None si la columna acepta NULL).
USERID_CARGA_AUTOMATICA = None

# Formato de texto para la columna dbo.Importacion.fecha (varchar(15)).
FORMATO_FECHA = "%Y/%m/%d"

# Límites reales de las columnas VARCHAR en dbo.Importacion. Se usan para
# truncar de forma segura ANTES de insertar (en vez de dejar que SQL
# Server rechace todo el lote con "String or binary data would be
# truncated"). Cualquier truncamiento se reporta en consola y en el
# reporte de excepciones para que puedas revisarlo.
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

RUTA_BASE = r"C:\Pronostiq\Importacionesdata"

RUTA_NOMENCLATURA  = RUTA_BASE + r"\Nomenclatura_agrupador.xlsx"
HOJA_NOMENCLATURA  = "Nomenclatura agrupada"

RUTA_IMPORTACIONES_FORZADA = None  # si quieres forzar una ruta específica, escríbela aquí como r"C:\...\archivo.xlsx"

# Nombre estándar: coloca siempre el archivo del mes con este nombre
# exacto en RUTA_BASE. Si no lo encuentra, el script cae de respaldo a
# buscar automáticamente el .xlsx más reciente en la carpeta (por si
# algún mes se te olvida renombrarlo).
NOMBRE_ARCHIVO_IMPORTACIONES_ESTANDAR = "importaciones_del_mes.xlsx"

# Patrones de archivos que NUNCA son el archivo crudo de importaciones
# (para no confundirlos al buscar automáticamente el archivo del mes)
_PATRONES_EXCLUIDOS = [
    "Nomenclatura_agrupador*.xlsx",
    "Reporte_*.xlsx",
    "Revision_*.xlsx",
]


def detectar_archivo_importaciones():
    """Encuentra el archivo crudo de importaciones del mes. Primero
    busca el nombre estándar (NOMBRE_ARCHIVO_IMPORTACIONES_ESTANDAR);
    si no existe, cae de respaldo a detectar automáticamente el .xlsx
    modificado más recientemente en RUTA_BASE que no sea la
    nomenclatura ni ninguno de los reportes que genera este proceso."""
    if RUTA_IMPORTACIONES_FORZADA:
        return RUTA_IMPORTACIONES_FORZADA

    ruta_estandar = os.path.join(RUTA_BASE, NOMBRE_ARCHIVO_IMPORTACIONES_ESTANDAR)
    if os.path.isfile(ruta_estandar):
        return ruta_estandar

    print(f"  (no se encontró '{NOMBRE_ARCHIVO_IMPORTACIONES_ESTANDAR}'; "
          f"buscando el archivo más reciente como respaldo...)")

    todos = glob.glob(os.path.join(RUTA_BASE, "*.xlsx"))
    excluidos = set()
    for patron in _PATRONES_EXCLUIDOS:
        excluidos.update(glob.glob(os.path.join(RUTA_BASE, patron)))

    # También ignora archivos temporales de Excel (cuando el archivo
    # está abierto, Excel crea uno que empieza con "~$")
    candidatos = [
        f for f in todos
        if f not in excluidos and not os.path.basename(f).startswith("~$")
    ]

    if not candidatos:
        raise FileNotFoundError(
            f"No se encontró ningún archivo de importaciones en {RUTA_BASE}. "
            f"Coloca el archivo crudo del mes ahí (con cualquier nombre) y "
            f"vuelve a correr el proceso."
        )

    candidatos.sort(key=os.path.getmtime, reverse=True)
    elegido = candidatos[0]

    print(f"Archivo de importaciones detectado: {os.path.basename(elegido)}")
    if len(candidatos) > 1:
        otros = ", ".join(os.path.basename(c) for c in candidatos[1:])
        print(f"  (se usó el más reciente; también hay en la carpeta: {otros})")
        print(f"  Si no es el correcto, borra/mueve los archivos viejos, o fija "
              f"RUTA_IMPORTACIONES_FORZADA al inicio del script.")

    return elegido


def detectar_hoja_importaciones(ruta):
    """Encuentra la hoja de datos dentro del archivo (el nombre cambia
    cada año, ej. 'ImpPlag2026' -> 'ImpPlag2027')."""
    hojas = pd.ExcelFile(ruta).sheet_names
    if len(hojas) == 1:
        return hojas[0]
    candidatas = [h for h in hojas if h.upper().startswith("IMPPLAG")]
    if len(candidatas) == 1:
        return candidatas[0]
    raise ValueError(
        f"No se pudo determinar automáticamente la hoja de datos en "
        f"'{os.path.basename(ruta)}'. Hojas disponibles: {hojas}. "
        f"Edita HOJA_IMPORTACIONES manualmente si hace falta."
    )

RUTA_REPORTE_EXCEPCIONES = RUTA_BASE + r"\Reporte_Excepciones_Agrupador.xlsx"
RUTA_REPORTE_TRUNCADOS   = RUTA_BASE + r"\Reporte_Valores_Truncados.xlsx"


# =====================================================================
# UTILIDADES
# =====================================================================
# Algunos archivos traen celdas con el texto literal "nan" (no vacías
# de verdad, sino con esa palabra escrita) en vez de estar en blanco --
# probablemente de un proceso previo que exportó valores faltantes como
# texto. Se tratan igual que un valor realmente vacío.
_TEXTOS_VACIOS = {"nan", "none", "null", "n/a", "na", ""}


def _es_vacio(valor):
    if pd.isna(valor):
        return True
    if isinstance(valor, str) and valor.strip().lower() in _TEXTOS_VACIOS:
        return True
    return False


def normalizar(texto):
    """TRIM + UPPER + colapsar espacios múltiples. Usar como clave de cruce."""
    if _es_vacio(texto):
        return None
    return re.sub(r"\s+", " ", str(texto).strip().upper())


def a_texto_id(valor):
    """Convierte un identificador a texto de forma segura.
    Si es un número entero (o un float que representa un entero, ej.
    66698.0 leído de Excel), lo devuelve sin decimales. Si es texto no
    numérico (se detectaron casos como 'RDON-REVAI-12094-15.pdf' en el
    archivo real), lo deja tal cual, solo recortando espacios."""
    if _es_vacio(valor):
        return None
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor).strip()


def limpiar_texto(texto):
    """TRIM + colapsar espacios, sin cambiar mayúsculas."""
    if _es_vacio(texto):
        return None
    return re.sub(r"\s+", " ", str(texto).strip())


_ADVERTENCIAS_PORCENTAJE = {"combos": 0, "no_parseables": 0}


def parsear_porcentaje(valor):
    """Convierte el campo de porcentaje a fracción decimal (ej. '50%'
    -> 0.50), consistente con cómo se guardaba históricamente (como
    fracción, no como número entero de 0-100).

    Algunos meses este campo llega como texto en vez de número, y en
    productos con varios ingredientes puede venir como un combo
    ('10% + 40%'). Un combo no se puede representar en una sola columna
    decimal(18,2) sin perder información -- se deja NULL y se cuenta
    para avisar en consola (no es un campo usado en el cruce de
    nomenclatura, así que no afecta la clasificación)."""
    if _es_vacio(valor):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)

    texto = str(valor).strip()
    if "+" in texto:
        _ADVERTENCIAS_PORCENTAJE["combos"] += 1
        return None

    texto = texto.replace("%", "").strip()
    try:
        return float(texto) / 100.0
    except ValueError:
        _ADVERTENCIAS_PORCENTAJE["no_parseables"] += 1
        return None


_ADVERTENCIAS_TRUNCADO = []  # se llena durante truncar_columnas(), se reporta al final


def truncar_columnas(df):
    """Corta cualquier valor de texto que exceda el límite de su columna
    destino en dbo.Importacion, para evitar que SQL Server rechace todo
    el lote con 'String or binary data would be truncated'. Registra
    cada caso truncado para poder revisarlo después."""
    _ADVERTENCIAS_TRUNCADO.clear()
    for columna, limite in LIMITES_COLUMNAS.items():
        if columna not in df.columns:
            continue

        def _recortar(valor, _limite=limite, _columna=columna):
            if valor is None:
                return None
            texto = str(valor)
            if len(texto) > _limite:
                _ADVERTENCIAS_TRUNCADO.append({
                    "columna": _columna,
                    "longitud_original": len(texto),
                    "limite": _limite,
                    "valor_original": texto,
                    "valor_truncado": texto[:_limite],
                })
                return texto[:_limite]
            return texto

        df[columna] = df[columna].apply(_recortar)
    return df


# =====================================================================
# PASO 1: Cargar y normalizar nomenclatura
# =====================================================================
def cargar_nomenclatura(engine):
    print("Leyendo nomenclatura agrupada...")
    df = pd.read_excel(RUTA_NOMENCLATURA, sheet_name=HOJA_NOMENCLATURA)
    df = df.rename(columns={
        "INGREDIENTE ACT.": "IngredienteRaw",
        "Agrupación estandarizada_Nomenclatura": "Agrupador",
        "Codigo": "Codigo",  # ya viene con este nombre; se deja explícito por claridad
    })

    df["IngredienteActivo_Key"] = df["IngredienteRaw"].apply(normalizar)
    df["Agrupador"] = df["Agrupador"].apply(limpiar_texto)
    df["Codigo"] = df["Codigo"].apply(limpiar_texto) if "Codigo" in df.columns else None

    df = (
        df[["IngredienteActivo_Key", "Agrupador", "Codigo"]]
        .dropna(subset=["IngredienteActivo_Key", "Agrupador"])
        .drop_duplicates(subset=["IngredienteActivo_Key"])
    )

    sin_codigo = df["Codigo"].isna().sum()
    if sin_codigo:
        print(f"  AVISO: {sin_codigo} ingredientes en la nomenclatura no traen 'Codigo' "
              f"asignado todavía (quedarán con CodigoAgrupador NULL en Importacion).")

    print(f"  {len(df)} claves de ingrediente únicas en la nomenclatura.")
    df.to_sql("stg_Nomenclatura", engine, if_exists="replace", index=False)
    return df


# =====================================================================
# PASO 2: Cargar, mapear y normalizar importaciones
#   Mapeo archivo crudo -> dbo.Importacion:
#     RECIBO            -> recibointerno
#     SerieSAT          -> serie_sat
#     RECIBOSAT/RecSAT  -> numero_recibo_sat (mismos valores en el
#                          crudo; se usa RECIBOSAT y si viene vacío
#                          se completa con RecSAT)
#     APLICACIoN        -> aplicacion
#     FECHA             -> fecha (formateada a texto) + anio (derivado)
#     IMPORTADOR        -> importador
#     PRODUCTO          -> producto
#     INGREDIENTEACT    -> ingrediente_act (+ ingrediente_key normalizado)
#     EXPORTADOR        -> exportador
#     ORIGEN            -> origen
#     pct               -> porcentaje  (OJO: la tabla es decimal(18,2);
#                          valores como 0.001 se redondean a 0.00,
#                          es una limitación del esquema existente)
#     CANTIDAD          -> cantidad
#     UNMEDIDA          -> unidad_medida
#     CIFusd            -> cif_USD
#     CIFQ              -> cif_Q
#     CAMBIO            -> tipo_cambio (se guarda como texto)
#     Empresa           -> institucion
#     UMSP              -> umsp
# =====================================================================
def cargar_importaciones(engine):
    ruta_importaciones = detectar_archivo_importaciones()
    hoja_importaciones = detectar_hoja_importaciones(ruta_importaciones)
    print(f"Leyendo archivo crudo de importaciones "
          f"({os.path.basename(ruta_importaciones)}, hoja '{hoja_importaciones}')...")
    df_crudo = pd.read_excel(ruta_importaciones, sheet_name=hoja_importaciones)

    # Los encabezados cambian de nombre entre archivos (ej. "RECIBO" un
    # mes, "RECIBO INTERNO VAI-MAGA" otro mes), pero el ORDEN de las
    # columnas se mantiene. Por eso se leen por posición, no por nombre.
    NOMBRES_INTERNOS = [
        "RECIBO", "SerieSAT", "RecSAT", "APLICACIoN", "RECIBOSAT", "FECHA",
        "IMPORTADOR", "PRODUCTO", "INGREDIENTEACT", "EXPORTADOR", "ORIGEN",
        "pct", "CANTIDAD", "UNMEDIDA", "CIFusd", "CIFQ", "CAMBIO", "Empresa", "UMSP",
    ]
    if df_crudo.shape[1] < len(NOMBRES_INTERNOS):
        raise ValueError(
            f"El archivo tiene {df_crudo.shape[1]} columnas, se esperaban al menos "
            f"{len(NOMBRES_INTERNOS)}. Encabezados encontrados: {list(df_crudo.columns)}"
        )

    encabezados_originales = list(df_crudo.columns[:len(NOMBRES_INTERNOS)])
    print("  Mapeo de columnas por posición (verifica que el orden tenga sentido):")
    for i, (nombre_interno, encabezado) in enumerate(zip(NOMBRES_INTERNOS, encabezados_originales), start=1):
        print(f"    columna {i:>2}: '{encabezado}' -> {nombre_interno}")

    df = df_crudo.iloc[:, :len(NOMBRES_INTERNOS)].copy()
    df.columns = NOMBRES_INTERNOS

    columnas_texto = ["IMPORTADOR", "PRODUCTO", "EXPORTADOR", "ORIGEN", "Empresa",
                       "APLICACIoN", "SerieSAT", "UNMEDIDA"]
    for col in columnas_texto:
        df[col] = df[col].apply(limpiar_texto)

    df["INGREDIENTEACT"] = df["INGREDIENTEACT"].apply(limpiar_texto)

    numero_recibo_sat = df["RECIBOSAT"]
    numero_recibo_sat = numero_recibo_sat.where(numero_recibo_sat.notna(), df["RecSAT"])

    salida = pd.DataFrame({
        "anio": pd.to_datetime(df["FECHA"]).dt.year,
        "recibointerno": df["RECIBO"].apply(a_texto_id),
        "serie_sat": df["SerieSAT"],
        "numero_recibo_sat": numero_recibo_sat.apply(a_texto_id),
        "aplicacion": df["APLICACIoN"],
        "fecha": pd.to_datetime(df["FECHA"]).dt.strftime(FORMATO_FECHA),
        "importador": df["IMPORTADOR"],
        "producto": df["PRODUCTO"],
        "ingrediente_act": df["INGREDIENTEACT"],
        "ingrediente_key": df["INGREDIENTEACT"].apply(normalizar),
        "exportador": df["EXPORTADOR"],
        "origen": df["ORIGEN"],
        "porcentaje": df["pct"].apply(parsear_porcentaje),
        "cantidad": df["CANTIDAD"],
        "unidad_medida": df["UNMEDIDA"],
        "cif_USD": df["CIFusd"],
        "cif_Q": df["CIFQ"],
        "tipo_cambio": df["CAMBIO"].apply(lambda x: None if _es_vacio(x) else str(x)),
        "institucion": df["Empresa"],
        "umsp": df["UMSP"],
    })

    # Descarta filas basura de la hoja (sin ningún dato real de
    # transacción) -- se detectaron filas al final de algunos archivos
    # con "nan" en todas las columnas, que no son transacciones reales
    # y no deben llegar a la base de datos.
    antes = len(salida)
    salida = salida[
        salida["ingrediente_act"].notna()
        | salida["producto"].notna()
        | salida["importador"].notna()
    ].copy()
    descartadas = antes - len(salida)
    if descartadas:
        print(f"  AVISO: {descartadas} fila(s) completamente vacías descartadas "
              f"(sin ingrediente, producto ni importador -- basura de la hoja, no "
              f"son transacciones reales).")

    if _ADVERTENCIAS_PORCENTAJE["combos"] or _ADVERTENCIAS_PORCENTAJE["no_parseables"]:
        print(f"  AVISO: columna 'pct' con formato inesperado -> "
              f"{_ADVERTENCIAS_PORCENTAJE['combos']} combo(s) tipo '10% + 40%' "
              f"y {_ADVERTENCIAS_PORCENTAJE['no_parseables']} valor(es) no reconocido(s); "
              f"se dejaron en NULL (no afecta el cruce de nomenclatura, solo el dato informativo).")

    salida = truncar_columnas(salida)

    print(f"  {len(salida)} transacciones leídas, años presentes: "
          f"{sorted(salida['anio'].dropna().unique().tolist())}")

    if _ADVERTENCIAS_TRUNCADO:
        print(f"  AVISO: {len(_ADVERTENCIAS_TRUNCADO)} valores excedían el límite "
              f"de su columna y fueron truncados antes de cargar (ver reporte).")
        for w in _ADVERTENCIAS_TRUNCADO[:5]:
            print(f"    - columna '{w['columna']}' ({w['longitud_original']} > "
                  f"{w['limite']} caracteres): {w['valor_original'][:60]}...")
        if len(_ADVERTENCIAS_TRUNCADO) > 5:
            print(f"    ... y {len(_ADVERTENCIAS_TRUNCADO) - 5} más "
                  f"(ver {RUTA_REPORTE_TRUNCADOS}).")
        pd.DataFrame(_ADVERTENCIAS_TRUNCADO).to_excel(RUTA_REPORTE_TRUNCADOS, index=False)

    salida.to_sql("stg_Importacion", engine, if_exists="replace", index=False)
    return salida


# =====================================================================
# PASO 3: Ejecutar procedimientos en SQL Server
# =====================================================================
def ejecutar_integracion(engine):
    print("Actualizando catálogo de nomenclatura en la base de datos...")
    with engine.begin() as conn:
        conn.execute(text("EXEC dbo.usp_ActualizarNomenclatura;"))

    print("Integrando transacciones a dbo.Importacion (DELETE + INSERT por año)...")
    with engine.begin() as conn:
        conn.execute(
            text("EXEC dbo.usp_CargarImportacion @UserId = :userid;"),
            {"userid": USERID_CARGA_AUTOMATICA},
        )


# =====================================================================
# PASO 4: Validación de excepciones (transacciones sin agrupador)
#   - Reporte Excel con 2 pestañas: Resumen (por ingrediente) y Detalle
#     (transacción por transacción), sobrescrito cada corrida.
#   - Log de texto acumulado (una línea por corrida), para llevar
#     historial mes a mes sin depender de abrir el Excel.
#   - Devuelve True si hubo excepciones, False si todo cruzó bien.
# =====================================================================
RUTA_LOG_HISTORICO = RUTA_BASE + r"\log_excepciones_historico.txt"


def _parece_error_captura(texto):
    """Heurística simple para separar 'ingredientes' que en realidad son
    basura de captura (números sueltos, nombres de archivo, códigos) de
    ingredientes activos reales sin agrupador todavía. No es perfecta:
    es solo una ayuda para priorizar la revisión manual."""
    if not texto:
        return False
    t = texto.strip()
    # Solo dígitos/puntos/comas (ej. "113.74")
    if re.fullmatch(r"[\d.,]+", t):
        return True
    # Termina en extensión de archivo (ej. "RDON-REVAI-12094-15.pdf")
    if re.search(r"\.(pdf|xlsx?|docx?|jpg|png)$", t, re.IGNORECASE):
        return True
    return False


def exportar_excepciones(engine):
    query_detalle = """
        SELECT recibointerno, ingrediente_act, ingrediente_key, producto, cantidad, cif_USD
        FROM dbo.log_ExcepcionesAgrupador
        WHERE CAST(FechaCorrida AS DATE) = CAST(SYSDATETIME() AS DATE)
        ORDER BY ingrediente_key
    """
    df_detalle = pd.read_sql(query_detalle, engine)

    ahora = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")

    if df_detalle.empty:
        print("Todas las transacciones encontraron agrupador. No hay excepciones.")
        with open(RUTA_LOG_HISTORICO, "a", encoding="utf-8") as f:
            f.write(f"{ahora}\tOK\ttransacciones_sin_agrupador=0\n")
        return False

    # --- Resumen agrupado por ingrediente (equivalente a la vista SQL) ---
    df_resumen = (
        df_detalle.groupby("ingrediente_key", as_index=False)
        .agg(
            ingrediente_act_ejemplo=("ingrediente_act", "first"),
            transacciones=("recibointerno", "count"),
            cantidad_total=("cantidad", "sum"),
            cif_usd_total=("cif_USD", "sum"),
        )
        .sort_values("transacciones", ascending=False)
    )
    df_resumen["posible_error_captura"] = df_resumen["ingrediente_act_ejemplo"].apply(
        _parece_error_captura
    )

    # --- Pestaña lista para copiar/pegar a Nomenclatura_agrupador.xlsx ---
    # Solo las 2 columnas que el proceso realmente usa de ese archivo
    # (INGREDIENTE ACT. y Agrupación estandarizada_Nomenclatura; la
    # columna GRUPO del archivo original no la lee el proceso, así que
    # no se incluye aquí para no confundir).
    df_para_agregar = df_resumen.sort_values(
        ["posible_error_captura", "transacciones"], ascending=[True, False]
    )[["ingrediente_act_ejemplo", "posible_error_captura", "transacciones", "cif_usd_total"]].rename(
        columns={"ingrediente_act_ejemplo": "INGREDIENTE ACT."}
    )
    df_para_agregar["Agrupación estandarizada_Nomenclatura"] = ""
    df_para_agregar = df_para_agregar[
        ["INGREDIENTE ACT.", "Agrupación estandarizada_Nomenclatura",
         "posible_error_captura", "transacciones", "cif_usd_total"]
    ]

    with pd.ExcelWriter(RUTA_REPORTE_EXCEPCIONES, engine="openpyxl") as writer:
        df_para_agregar.to_excel(writer, sheet_name="Nomenclatura_Por_Agregar", index=False)
        df_resumen.to_excel(writer, sheet_name="Resumen", index=False)
        df_detalle.to_excel(writer, sheet_name="Detalle", index=False)

    n_error_captura = int(df_resumen["posible_error_captura"].sum())
    ingredientes_unicos = df_detalle["ingrediente_key"].nunique()
    print(
        f"ATENCIÓN: {len(df_detalle)} transacciones ({ingredientes_unicos} ingredientes "
        f"distintos) sin agrupador encontrado "
        f"({n_error_captura} parecen errores de captura, no ingredientes reales)."
    )
    print(f"Reporte exportado a: {RUTA_REPORTE_EXCEPCIONES}")
    print("  -> Pestaña 'Nomenclatura_Por_Agregar': llena "
          "'Agrupación estandarizada_Nomenclatura' y pega esas filas "
          "(solo esas 2 columnas) en Nomenclatura_agrupador.xlsx.")

    with open(RUTA_LOG_HISTORICO, "a", encoding="utf-8") as f:
        f.write(
            f"{ahora}\tEXCEPCIONES\ttransacciones_sin_agrupador={len(df_detalle)}\t"
            f"ingredientes_distintos={ingredientes_unicos}\t"
            f"posibles_errores_captura={n_error_captura}\n"
        )
    return True


# =====================================================================
# MAIN
# Códigos de salida (útiles si programas esto en el servidor):
#   0 = corrió bien, sin excepciones
#   1 = error real (no se pudo conectar/cargar)
#   2 = corrió bien, PERO hay transacciones sin agrupador (revisar reporte)
# =====================================================================
def main():
    print(f"=== Proceso de carga — {date.today().isoformat()} ===")
    try:
        engine = create_engine(CONN_STR, fast_executemany=True)
    except Exception as e:
        print(f"ERROR al conectar a la base de datos: {e}")
        sys.exit(1)

    cargar_nomenclatura(engine)
    cargar_importaciones(engine)
    ejecutar_integracion(engine)
    hubo_excepciones = exportar_excepciones(engine)

    print("=== Proceso finalizado ===")
    sys.exit(2 if hubo_excepciones else 0)


if __name__ == "__main__":
    main()
