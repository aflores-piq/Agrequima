"""Indicadores > Viáticos > «Resumen General» (copia fiel de la página del PBIX
PIQ_AGRAQUIMA_VIATICOS.pbix, con la DAX de docs/legacy/indicadores/inventario_pbix.md).

Fuente: dbo.vw_piq_viaticos (script 30_copias_fieles_indicadores.sql). Solo SELECT.

Equivalencias con la DAX del PBIX:
  Calculos_Viaticos[TotalGastos]        = SUM(vw_piq_viaticos[monto])
  Calculos_Viaticos[TotalColaboradores] = DISTINCTCOUNT(nombre_completo)
  Calculos_Viaticos[TotalDocumentos]    = DISTINCTCOUNT(documento)
  Calculos_Viaticos[TotalProveedores]   = DISTINCTCOUNT(proveedor)
  Calculos_Viaticos[Gastos Acumulados Hasta Mes] = suma del año elegido hasta el mes elegido
El filtro «Año y Mes» actúa sobre fecha_documento (a través de MiCalendario en el PBIX): las filas sin
fecha_documento no entran en ningún mes.

DISTINCTCOUNT de DAX cuenta el valor vacío (BLANK) como un valor más; COUNT(DISTINCT) de SQL lo ignora.
Por eso cada conteo suma 1 si hay NULL en la columna (igual que consultas_resumen_general.sql).
"""

from __future__ import annotations

import calendar
from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

MESES_ABREVIADOS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
MESES_LETRAS = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]
SIN_VALOR = "(En blanco)"


def etiqueta_mes(anio: int, mes: int) -> str:
    """«Nov. 2026» (como el filtro «Año y Mes» de la imagen del nuevo diseño)."""
    return f"{MESES_ABREVIADOS[mes - 1]}. {anio}"


def _periodo(anio: int, mes: int) -> tuple[date, date]:
    ultimo = calendar.monthrange(anio, mes)[1]
    return date(anio, mes, 1), date(anio, mes, ultimo)


def titulo_dinamico(anio: int, mes: int) -> str:
    """Calculos_Viaticos[TituloGeneral_1]: «Resumen General de Viáticos del 01 al 30 de Noviembre de 2026».
    En el PBIX MiCalendario llega hasta el fin del mes actual, así que con un solo mes elegido las fechas
    van siempre del día 1 al último día del mes."""
    desde, hasta = _periodo(anio, mes)
    return (
        f"Resumen General de Viáticos del {desde.day:02d} al {hasta.day:02d} "
        f"de {MESES_LETRAS[mes - 1]} de {anio}"
    )


def _mes_atras(anio: int, mes: int, meses: int) -> tuple[int, int]:
    indice = anio * 12 + (mes - 1) - meses
    return indice // 12, indice % 12 + 1


def _num(valor) -> float:
    return float(valor) if valor is not None else 0.0


def meses_disponibles(db: Session) -> dict:
    """Meses con datos (más reciente primero) y el mes por defecto (el último con datos)."""
    filas = db.execute(
        text(
            """
            SELECT YEAR(fecha_documento) AS anio, MONTH(fecha_documento) AS mes, COUNT(*) AS filas
            FROM dbo.vw_piq_viaticos
            WHERE fecha_documento IS NOT NULL
            GROUP BY YEAR(fecha_documento), MONTH(fecha_documento)
            ORDER BY anio DESC, mes DESC
            """
        )
    ).all()
    meses = [
        {"anio": int(f.anio), "mes": int(f.mes), "etiqueta": etiqueta_mes(int(f.anio), int(f.mes)), "filas": int(f.filas)}
        for f in filas
    ]
    por_defecto = {"anio": meses[0]["anio"], "mes": meses[0]["mes"]} if meses else None
    return {"meses": meses, "por_defecto": por_defecto}


def tarjetas(db: Session, anio: int, mes: int) -> dict:
    """Las 4 tarjetas KPI: valor del mes, últimos 12 meses (hasta el mes elegido, incluido) y % contra el
    mismo mes del año anterior (None si ese mes no tiene datos).

    Si el mes elegido está incompleto (su último día con datos es anterior al fin de mes), el % se calcula contra
    el mismo mes del año anterior SOLO del día 1 hasta ese mismo día («vs. mismo período año ant.»); si está
    completo, contra el mes completo («vs. año ant.»). La mini gráfica de 12 meses sigue usando meses completos."""
    anio_ini, mes_ini = _mes_atras(anio, mes, 12)  # el mismo mes del año anterior es el primero de la ventana
    desde = date(anio_ini, mes_ini, 1)
    _, hasta = _periodo(anio, mes)
    filas = db.execute(
        text(
            """
            SELECT YEAR(fecha_documento) AS anio, MONTH(fecha_documento) AS mes,
                   SUM(monto) AS total_viaticos,
                   COUNT(DISTINCT nombre_completo) + MAX(CASE WHEN nombre_completo IS NULL THEN 1 ELSE 0 END) AS tecnicos,
                   COUNT(DISTINCT documento)       + MAX(CASE WHEN documento       IS NULL THEN 1 ELSE 0 END) AS documentos,
                   COUNT(DISTINCT proveedor)       + MAX(CASE WHEN proveedor       IS NULL THEN 1 ELSE 0 END) AS proveedores,
                   COUNT(*) AS filas
            FROM dbo.vw_piq_viaticos
            WHERE fecha_documento >= :desde AND fecha_documento <= :hasta
            GROUP BY YEAR(fecha_documento), MONTH(fecha_documento)
            """
        ),
        {"desde": desde, "hasta": hasta},
    ).all()
    por_mes = {(int(f.anio), int(f.mes)): f for f in filas}

    anio_ant, mes_ant = _mes_atras(anio, mes, 12)
    ultimo_dia_mes = calendar.monthrange(anio, mes)[1]
    ultimo_dia_con_datos = db.execute(
        text("SELECT MAX(fecha_documento) FROM dbo.vw_piq_viaticos WHERE fecha_documento >= :desde AND fecha_documento <= :hasta"),
        {"desde": date(anio, mes, 1), "hasta": date(anio, mes, ultimo_dia_mes)},
    ).scalar()
    parcial = ultimo_dia_con_datos is not None and ultimo_dia_con_datos.day < ultimo_dia_mes
    dia_corte = ultimo_dia_con_datos.day if parcial else None
    fila_comparacion = por_mes.get((anio_ant, mes_ant))
    if parcial:
        # mismo período del año anterior: día 1 hasta el mismo día (29 de febrero -> último día de febrero)
        corte_ant = min(dia_corte, calendar.monthrange(anio_ant, mes_ant)[1])
        fila_comparacion = db.execute(
            text(
                """
                SELECT SUM(monto) AS total_viaticos,
                       COUNT(DISTINCT nombre_completo) + MAX(CASE WHEN nombre_completo IS NULL THEN 1 ELSE 0 END) AS tecnicos,
                       COUNT(DISTINCT documento)       + MAX(CASE WHEN documento       IS NULL THEN 1 ELSE 0 END) AS documentos,
                       COUNT(DISTINCT proveedor)       + MAX(CASE WHEN proveedor       IS NULL THEN 1 ELSE 0 END) AS proveedores,
                       COUNT(*) AS filas
                FROM dbo.vw_piq_viaticos
                WHERE fecha_documento >= :desde AND fecha_documento <= :hasta
                """
            ),
            {"desde": date(anio_ant, mes_ant, 1), "hasta": date(anio_ant, mes_ant, corte_ant)},
        ).first()
        if fila_comparacion is not None and not fila_comparacion.filas:
            fila_comparacion = None  # ese período del año anterior no tiene datos

    definicion = [
        ("total_viaticos", "Total Viáticos", "total_viaticos", "moneda"),
        ("tecnicos_conductores", "Técnicos/Conductores", "tecnicos", "entero"),
        ("total_documentos", "Total Documentos", "documentos", "entero"),
        ("total_proveedores", "Total Proveedores", "proveedores", "entero"),
    ]
    resultado = []
    for clave, etiqueta, columna, formato in definicion:
        serie = []
        for atras in range(11, -1, -1):
            a, m = _mes_atras(anio, mes, atras)
            fila = por_mes.get((a, m))
            serie.append({"anio": a, "mes": m, "valor": _num(getattr(fila, columna)) if fila else 0.0})
        valor = serie[-1]["valor"]
        valor_ant = _num(getattr(fila_comparacion, columna)) if fila_comparacion else None
        variacion = None
        if valor_ant:  # None (mes sin datos) o 0 -> sin porcentaje
            variacion = round((valor - valor_ant) / valor_ant * 100, 1)
        resultado.append(
            {
                "clave": clave,
                "etiqueta": etiqueta,
                "formato": formato,
                "valor": valor,
                "valor_anio_anterior": valor_ant,
                "variacion_pct": variacion,
                "ultimos_12_meses": serie,
            }
        )
    return {
        "anio": anio,
        "mes": mes,
        "etiqueta_mes": etiqueta_mes(anio, mes),
        "titulo": titulo_dinamico(anio, mes),
        "periodo_parcial": parcial,
        "dia_corte": dia_corte,
        "texto_comparacion": "vs. mismo período año ant." if parcial else "vs. año ant.",
        "tarjetas": resultado,
    }


def acumulado(db: Session, anio: int, mes: int) -> dict:
    """«Gastos Acumulados Hasta Mes» para el año elegido y el anterior: por cada mes 1..12, la suma de los meses
    1..m del año. El año elegido solo llega hasta el mes elegido (después queda en None); el anterior llega a 12."""
    filas = db.execute(
        text(
            """
            SELECT YEAR(fecha_documento) AS anio, MONTH(fecha_documento) AS mes, SUM(monto) AS total
            FROM dbo.vw_piq_viaticos
            WHERE fecha_documento >= :desde AND fecha_documento <= :hasta
            GROUP BY YEAR(fecha_documento), MONTH(fecha_documento)
            """
        ),
        {"desde": date(anio - 1, 1, 1), "hasta": date(anio, 12, 31)},
    ).all()
    por_mes = {(int(f.anio), int(f.mes)): _num(f.total) for f in filas}

    def serie(a: int, hasta_mes: int) -> list[dict]:
        acum = 0.0
        salida = []
        for m in range(1, 13):
            acum += por_mes.get((a, m), 0.0)
            salida.append({"mes": m, "etiqueta": MESES_ABREVIADOS[m - 1], "acumulado": round(acum, 2) if m <= hasta_mes else None})
        return salida

    return {
        "anio": anio,
        "anio_anterior": anio - 1,
        "mes": mes,
        "serie_actual": serie(anio, mes),
        "serie_anterior": serie(anio - 1, 12),
    }


def _agrupado(db: Session, columna: str, anio: int, mes: int) -> list[dict]:
    desde, hasta = _periodo(anio, mes)
    filas = db.execute(
        text(
            f"""
            SELECT {columna} AS nombre, SUM(monto) AS total_gastos
            FROM dbo.vw_piq_viaticos
            WHERE fecha_documento >= :desde AND fecha_documento <= :hasta
            GROUP BY {columna}
            ORDER BY SUM(monto) DESC, {columna}
            """
        ),
        {"desde": desde, "hasta": hasta},
    ).all()
    return [{"nombre": f.nombre if f.nombre is not None else SIN_VALOR, "total_gastos": _num(f.total_gastos)} for f in filas]


def tipos_gasto(db: Session, anio: int, mes: int) -> dict:
    """Dona «Distribución de Viáticos por Tipo de Gasto» (orden: TotalGastos descendente)."""
    datos = _agrupado(db, "Tipo_gasto", anio, mes)
    return {"anio": anio, "mes": mes, "total": round(sum(d["total_gastos"] for d in datos), 2), "datos": datos}


def colaboradores(db: Session, anio: int, mes: int) -> dict:
    """Barras «Viáticos Totales por Colaborador» (orden: TotalGastos descendente)."""
    datos = _agrupado(db, "nombre_completo", anio, mes)
    return {"anio": anio, "mes": mes, "total": round(sum(d["total_gastos"] for d in datos), 2), "datos": datos}


def detalle(db: Session, anio: int, mes: int) -> dict:
    """Tabla: una fila por combinación distinta de las 7 columnas, con Total Factura = SUM(monto). El PBIX no guarda un
    orden para la tabla: se ordena por la primera columna (igual que consultas_resumen_general.sql)."""
    desde, hasta = _periodo(anio, mes)
    filas = db.execute(
        text(
            """
            SELECT fecha_documento, fechainicial, fechafinal, nombre_completo AS tecnico, Tipo_gasto AS tipo_gasto,
                   motivo, SUM(monto) AS total_factura, proveedor
            FROM dbo.vw_piq_viaticos
            WHERE fecha_documento >= :desde AND fecha_documento <= :hasta
            GROUP BY fecha_documento, fechainicial, fechafinal, nombre_completo, Tipo_gasto, motivo, proveedor
            ORDER BY fecha_documento, fechainicial, fechafinal, nombre_completo, Tipo_gasto, motivo, proveedor
            """
        ),
        {"desde": desde, "hasta": hasta},
    ).all()
    total = db.execute(
        text("SELECT SUM(monto) FROM dbo.vw_piq_viaticos WHERE fecha_documento >= :desde AND fecha_documento <= :hasta"),
        {"desde": desde, "hasta": hasta},
    ).scalar()

    def fecha(valor) -> str | None:
        return valor.isoformat() if valor is not None else None

    return {
        "anio": anio,
        "mes": mes,
        "total_factura": _num(total),
        "filas": [
            {
                "fecha_documento": fecha(f.fecha_documento),
                "fecha_inicial": fecha(f.fechainicial),
                "fecha_final": fecha(f.fechafinal),
                "tecnico": f.tecnico,
                "tipo_gasto": f.tipo_gasto,
                "motivo": f.motivo,
                "total_factura": _num(f.total_factura),
                "proveedor": f.proveedor,
            }
            for f in filas
        ],
    }
