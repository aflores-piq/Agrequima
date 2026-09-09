"""Cálculos del dashboard Financiero (grupo "Estados Financieros", 4
páginas), sobre las vistas espejadas desde CONTACC:

    vw_piq_balance_saldos(emp_nit, Cta_Codigo, Cta_Descripcion, Sal_Ano,
        Sal_Mes, Debitos, Creditos, Saldo, Cod_Centro)
    vw_piq_balance_general(emp_nit, Cod_n1, Nom_n1, cod_n5, nom_n5,
        Sal_Ano, Sal_Mes, Debitos, Creditos, Saldo, Inicial)

más dbo.CatalogoAgrupadorCuentas (tabla propia de la app, no espejada
desde CONTACC -- ver agrupador_cuentas.py), que es la fuente real de la
columna "Grupo" en las 4 páginas. vw_catalogo_cuentas (otra vista
espejada, con Nombre_n1/Codigo_N5) YA NO se usa para esto -- se probó
y esa columna quedaba mal; CatalogoAgrupadorCuentas es el agrupador de
cuentas contables real que dio el cliente, con emparejamiento
jerárquico por código (Nivel 3 exacto -> Nivel 2 primeros 6 dígitos ->
Nivel 1 primeros 4 dígitos).

vw_piq_balance_saldos/vw_piq_balance_general no son modelos de la app
(no viven en app/models/): son espejos de solo lectura que crea
sync_piq_ia.py reflejando el esquema real de CONTACC -- por eso las
consultas de acá son SQL crudo (SQLAlchemy text()) en vez de ORM, igual
que dashboard_plaguicidas.py hace con dbo.Importacion pero sin un
modelo declarado para estas.

Semántica asumida (confirmada por el cliente para la clasificación
Activo/Pasivo/Patrimonio -- sacada del DAX real del .pbix original; el
resto son la interpretación más estándar dado el nombre de las columnas,
sin poder contrastarla contra datos reales todavía porque el sync a
CONTACC no ha corrido en producción):
  - vw_piq_balance_saldos: Debitos/Creditos son el MOVIMIENTO de ese
    mes puntual (no acumulado); Saldo es el resultado neto de ESE mes
    (no un saldo corrido) -- "acumulado" se arma sumando Saldo de
    varios meses (Sal_Mes <= mes seleccionado).
  - vw_piq_balance_general: Saldo SÍ es el saldo contable acumulado/
    vigente a esa fecha de corte (Sal_Ano, Sal_Mes) -- normal en
    cuentas de balance (Activo/Pasivo/Patrimonio), a diferencia de
    cuentas de resultado.
  - Clasificación (confirmada, del DAX real de _Balance_General):
        Activo:      LEFT(Cod_n1, 1) = '1'
        Patrimonio:  cod_n5 = '310101001' (cuenta puntual)
        Fondos por aplicar: cod_n5 = '210105001' (cuenta puntual)
        Pasivo:      LEFT(cod_n5, 1) = '2' Y cod_n5 <> '210105001'
"""

from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.dashboard_financiero import (
    BalanceGeneralComparativo,
    BalanceGeneralMensual,
    DashboardFinancieroResponse,
    DetalleCuentaBalance,
    DetalleCuentaBalanceComparativo,
    DetalleCuentaComparativoMovimiento,
    DetalleCuentaMovimiento,
    DistribucionBalanceItem,
    GrupoMontoItem,
    IngresosDesembolsosAcumulado,
    IngresosDesembolsosMensual,
    KpisBalanceGeneralComparativo,
    KpisBalanceGeneralMensual,
    KpisIngresosDesembolsosAcumulado,
    KpisIngresosDesembolsosMensual,
)
from app.services.agrupador_cuentas import MapasAgrupador, cargar_mapas_agrupador, grupo_de_cuenta

# CASE compartido por todas las consultas de vw_piq_balance_general que
# necesitan la clasificación contable -- ver semántica en el docstring.
_CLASIFICACION_BALANCE_SQL = """
    CASE
        WHEN LEFT(Cod_n1, 1) = '1' THEN 'Activo'
        WHEN cod_n5 = '310101001' THEN 'Patrimonio'
        WHEN cod_n5 = '210105001' THEN 'FondosPorAplicar'
        WHEN LEFT(cod_n5, 1) = '2' THEN 'Pasivo'
        ELSE 'Otro'
    END
"""


def _num(valor) -> float:
    return float(valor) if valor is not None else 0.0


def _periodo_anterior(anio: int, mes: int) -> tuple[int, int]:
    return (anio - 1, 12) if mes == 1 else (anio, mes - 1)


def _anio_mes_default(db: Session, anio: int | None, mes: int | None) -> tuple[int, int]:
    if anio is None:
        anio = db.execute(
            text("SELECT MAX(Sal_Ano) FROM dbo.vw_piq_balance_saldos")
        ).scalar()
        if anio is None:
            hoy = date.today()
            return hoy.year, hoy.month
    if mes is None:
        mes = db.execute(
            text("SELECT MAX(Sal_Mes) FROM dbo.vw_piq_balance_saldos WHERE Sal_Ano = :anio"),
            {"anio": anio},
        ).scalar()
        if mes is None:
            mes = 1
    return int(anio), int(mes)


# --- Página 1: Estado de ingresos y desembolsos mensual ---------------


def _totales_saldos_periodo(db: Session, anio: int, mes: int) -> dict:
    fila = db.execute(
        text(
            "SELECT SUM(Creditos) AS creditos, SUM(Debitos) AS debitos, SUM(Saldo) AS saldo "
            "FROM dbo.vw_piq_balance_saldos WHERE Sal_Ano = :anio AND Sal_Mes = :mes"
        ),
        {"anio": anio, "mes": mes},
    ).mappings().first()
    return {"creditos": _num(fila["creditos"]), "debitos": _num(fila["debitos"]), "saldo": _num(fila["saldo"])}


def _saldo_acumulado_ytd(db: Session, anio: int, mes: int) -> float:
    valor = db.execute(
        text(
            "SELECT SUM(Saldo) FROM dbo.vw_piq_balance_saldos "
            "WHERE Sal_Ano = :anio AND Sal_Mes <= :mes"
        ),
        {"anio": anio, "mes": mes},
    ).scalar()
    return _num(valor)


def _cascada_por_grupo(
    db: Session, anio: int, mes: int, columna: str, mapas: MapasAgrupador, ordenes: dict[str, int]
) -> list[GrupoMontoItem]:
    """Por cuenta (Cta_Codigo), el grupo lo da dbo.CatalogoAgrupadorCuentas
    (emparejamiento jerárquico, ver agrupador_cuentas.py) -- ya no
    vw_catalogo_cuentas/Nombre_n1. Se agrega en Python porque el
    emparejamiento en sí es Python, y el orden final de la cascada sigue
    el Orden real del catálogo (pensado como secuencia de "cascada"), no
    la magnitud del monto."""
    filas = db.execute(
        text(
            f"""
            SELECT Cta_Codigo AS codigo, SUM({columna}) AS monto
            FROM dbo.vw_piq_balance_saldos
            WHERE Sal_Ano = :anio AND Sal_Mes = :mes
            GROUP BY Cta_Codigo
            HAVING SUM({columna}) <> 0
            """
        ),
        {"anio": anio, "mes": mes},
    ).mappings().all()

    acumulado_por_grupo: dict[str, float] = {}
    for f in filas:
        grupo = grupo_de_cuenta(mapas, f["codigo"]) or "Sin clasificar"
        acumulado_por_grupo[grupo] = acumulado_por_grupo.get(grupo, 0.0) + _num(f["monto"])

    items = [GrupoMontoItem(grupo=g, monto=m) for g, m in acumulado_por_grupo.items()]
    items.sort(key=lambda it: ordenes.get(it.grupo, 999))
    return items


def _detalle_movimiento_por_cuenta(
    db: Session,
    anio: int,
    mes: int,
    anio_ant: int,
    mes_ant: int,
    columna_movimiento: str,
    mapas: MapasAgrupador,
) -> list[DetalleCuentaMovimiento]:
    """columna_movimiento: 'Debitos' (Egresos) o 'Creditos' (Ingresos).
    Por cuenta: valor de esa columna en el mes ANTERIOR + Saldo
    acumulado (YTD) en el período seleccionado. El grupo lo da
    dbo.CatalogoAgrupadorCuentas (ver agrupador_cuentas.py), no
    vw_catalogo_cuentas."""
    filas = db.execute(
        text(
            f"""
            SELECT
                b.Cta_Codigo AS codigo,
                MAX(b.Cta_Descripcion) AS nombre_cuenta_n5,
                SUM(CASE WHEN b.Sal_Ano = :anio_ant AND b.Sal_Mes = :mes_ant THEN b.{columna_movimiento} ELSE 0 END) AS mes_anterior,
                SUM(CASE WHEN b.Sal_Ano = :anio AND b.Sal_Mes <= :mes THEN b.Saldo ELSE 0 END) AS saldo_acumulado
            FROM dbo.vw_piq_balance_saldos b
            WHERE (b.Sal_Ano = :anio_ant AND b.Sal_Mes = :mes_ant)
               OR (b.Sal_Ano = :anio AND b.Sal_Mes <= :mes)
            GROUP BY b.Cta_Codigo
            -- Filtra por movimiento total de ESTA columna (Debitos para
            -- Egresos, Creditos para Ingresos) en la ventana consultada,
            -- no por Saldo -- una cuenta de Ingresos con Debitos=0 no
            -- debe aparecer en la tabla de Egresos solo porque su saldo
            -- acumulado no sea cero.
            HAVING SUM(b.{columna_movimiento}) <> 0
            ORDER BY saldo_acumulado DESC
            """
        ),
        {"anio": anio, "mes": mes, "anio_ant": anio_ant, "mes_ant": mes_ant},
    ).mappings().all()
    return [
        DetalleCuentaMovimiento(
            grupo=grupo_de_cuenta(mapas, f["codigo"]),
            nombre_cuenta_n5=f["nombre_cuenta_n5"],
            mes_anterior=_num(f["mes_anterior"]),
            saldo_acumulado=_num(f["saldo_acumulado"]),
        )
        for f in filas
    ]


def _pagina_ingresos_desembolsos_mensual(db: Session, anio: int, mes: int) -> IngresosDesembolsosMensual:
    anio_ant, mes_ant = _periodo_anterior(anio, mes)

    actual = _totales_saldos_periodo(db, anio, mes)
    anterior = _totales_saldos_periodo(db, anio_ant, mes_ant)
    acumulado = _saldo_acumulado_ytd(db, anio, mes)

    kpis = KpisIngresosDesembolsosMensual(
        ingresos=actual["creditos"],
        egresos=actual["debitos"],
        resultado=actual["creditos"] - actual["debitos"],
        saldo_mes_corriente=actual["saldo"],
        acumulado_saldo_mes_corriente=acumulado,
        saldo_mes_anterior=anterior["saldo"],
    )

    mapas_ingresos, ordenes_ingresos = cargar_mapas_agrupador(db, "Ingresos")
    mapas_egresos, ordenes_egresos = cargar_mapas_agrupador(db, "Egresos")

    return IngresosDesembolsosMensual(
        kpis=kpis,
        cascada_ingresos_por_grupo=_cascada_por_grupo(db, anio, mes, "Creditos", mapas_ingresos, ordenes_ingresos),
        cascada_egresos_por_grupo=_cascada_por_grupo(db, anio, mes, "Debitos", mapas_egresos, ordenes_egresos),
        detalle_egresos=_detalle_movimiento_por_cuenta(db, anio, mes, anio_ant, mes_ant, "Debitos", mapas_egresos),
        detalle_ingresos=_detalle_movimiento_por_cuenta(db, anio, mes, anio_ant, mes_ant, "Creditos", mapas_ingresos),
    )


# --- Página 2: Estado de ingresos y desembolsos acumulado -------------


def _totales_saldos_ytd(db: Session, anio: int, mes: int) -> dict:
    fila = db.execute(
        text(
            "SELECT SUM(Creditos) AS creditos, SUM(Debitos) AS debitos, SUM(Saldo) AS saldo "
            "FROM dbo.vw_piq_balance_saldos WHERE Sal_Ano = :anio AND Sal_Mes <= :mes"
        ),
        {"anio": anio, "mes": mes},
    ).mappings().first()
    return {"creditos": _num(fila["creditos"]), "debitos": _num(fila["debitos"]), "saldo": _num(fila["saldo"])}


def _detalle_comparativo_por_cuenta(
    db: Session, anio: int, anio_ant: int, mes: int, columna_movimiento: str, mapas: MapasAgrupador
) -> list[DetalleCuentaComparativoMovimiento]:
    """Por cuenta: la columna (Debitos=Egresos, Creditos=Ingresos)
    acumulada (YTD, Sal_Mes<=mes) del año anterior vs. del año actual.
    El grupo lo da dbo.CatalogoAgrupadorCuentas."""
    filas = db.execute(
        text(
            f"""
            SELECT
                b.Cta_Codigo AS codigo,
                MAX(b.Cta_Descripcion) AS cuenta,
                SUM(CASE WHEN b.Sal_Ano = :anio_ant AND b.Sal_Mes <= :mes THEN b.{columna_movimiento} ELSE 0 END) AS anio_anterior,
                SUM(CASE WHEN b.Sal_Ano = :anio AND b.Sal_Mes <= :mes THEN b.{columna_movimiento} ELSE 0 END) AS anio_actual
            FROM dbo.vw_piq_balance_saldos b
            WHERE (b.Sal_Ano = :anio_ant OR b.Sal_Ano = :anio) AND b.Sal_Mes <= :mes
            GROUP BY b.Cta_Codigo
            HAVING SUM(CASE WHEN b.Sal_Ano = :anio_ant AND b.Sal_Mes <= :mes THEN b.{columna_movimiento} ELSE 0 END) <> 0
                OR SUM(CASE WHEN b.Sal_Ano = :anio AND b.Sal_Mes <= :mes THEN b.{columna_movimiento} ELSE 0 END) <> 0
            ORDER BY anio_actual DESC
            """
        ),
        {"anio": anio, "anio_ant": anio_ant, "mes": mes},
    ).mappings().all()
    return [
        DetalleCuentaComparativoMovimiento(
            cuenta=f["cuenta"],
            grupo=grupo_de_cuenta(mapas, f["codigo"]),
            monto_anio_anterior=_num(f["anio_anterior"]),
            variacion=_num(f["anio_actual"]) - _num(f["anio_anterior"]),
            monto_anio_actual=_num(f["anio_actual"]),
        )
        for f in filas
    ]


def _pagina_ingresos_desembolsos_acumulado(
    db: Session, anio: int, mes: int, kpis_pagina1: KpisIngresosDesembolsosMensual
) -> IngresosDesembolsosAcumulado:
    anio_ant = anio - 1

    ytd_actual = _totales_saldos_ytd(db, anio, mes)
    ytd_anterior = _totales_saldos_ytd(db, anio_ant, mes)

    resultado_actual = ytd_actual["creditos"] - ytd_actual["debitos"]
    er_anio_anterior = ytd_anterior["creditos"] - ytd_anterior["debitos"]

    kpis = KpisIngresosDesembolsosAcumulado(
        ingresos=ytd_actual["creditos"],
        egresos=ytd_actual["debitos"],
        saldo_acumulado=ytd_actual["saldo"],
        resultado_anio_actual=resultado_actual,
        variacion_resultado=resultado_actual - er_anio_anterior,
        er_anio_anterior=er_anio_anterior,
        er_anio_actual=resultado_actual,
        er_mensual=kpis_pagina1.resultado,
        acumulado_saldo_anio_anterior=ytd_anterior["saldo"],
    )

    mapas_ingresos, _ = cargar_mapas_agrupador(db, "Ingresos")
    mapas_egresos, _ = cargar_mapas_agrupador(db, "Egresos")

    return IngresosDesembolsosAcumulado(
        kpis=kpis,
        detalle_egresos=_detalle_comparativo_por_cuenta(db, anio, anio_ant, mes, "Debitos", mapas_egresos),
        detalle_ingresos=_detalle_comparativo_por_cuenta(db, anio, anio_ant, mes, "Creditos", mapas_ingresos),
    )


# --- Páginas 3 y 4: Balance general -------------------------------------


def _totales_balance_general(db: Session, anio: int, mes: int) -> dict:
    fila = db.execute(
        text(
            f"""
            SELECT
                SUM(CASE WHEN {_CLASIFICACION_BALANCE_SQL} = 'Activo' THEN Saldo ELSE 0 END) AS activo,
                SUM(CASE WHEN {_CLASIFICACION_BALANCE_SQL} = 'Pasivo' THEN Saldo ELSE 0 END) AS pasivo,
                SUM(CASE WHEN {_CLASIFICACION_BALANCE_SQL} = 'Patrimonio' THEN Saldo ELSE 0 END) AS patrimonio,
                SUM(CASE WHEN {_CLASIFICACION_BALANCE_SQL} = 'FondosPorAplicar' THEN Saldo ELSE 0 END) AS fondos_por_aplicar
            FROM dbo.vw_piq_balance_general
            WHERE Sal_Ano = :anio AND Sal_Mes = :mes
            """
        ),
        {"anio": anio, "mes": mes},
    ).mappings().first()
    return {
        "activo": _num(fila["activo"]),
        "pasivo": _num(fila["pasivo"]),
        "patrimonio": _num(fila["patrimonio"]),
        "fondos_por_aplicar": _num(fila["fondos_por_aplicar"]),
    }


def _detalle_balance_periodo_a_vs_b(
    db: Session, clasificacion: str, anio_a: int, mes_a: int, anio_b: int, mes_b: int, mapas: MapasAgrupador
) -> list[tuple]:
    """Fila por cuenta de esa clasificación: (nombre_n5, grupo, monto_a,
    monto_b) -- monto_a es el período "más nuevo" (mes/año seleccionado),
    monto_b el de comparación (mes anterior en pág. 3, año anterior en
    pág. 4). El grupo lo da dbo.CatalogoAgrupadorCuentas (clasificacion
    coincide exactamente con TipoAgrupador: 'Activo'/'Pasivo'/
    'Patrimonio'), no Nom_n1."""
    filas = db.execute(
        text(
            f"""
            SELECT
                cod_n5 AS codigo,
                MAX(nom_n5) AS nombre_n5,
                SUM(CASE WHEN Sal_Ano = :anio_a AND Sal_Mes = :mes_a THEN Saldo ELSE 0 END) AS monto_a,
                SUM(CASE WHEN Sal_Ano = :anio_b AND Sal_Mes = :mes_b THEN Saldo ELSE 0 END) AS monto_b
            FROM dbo.vw_piq_balance_general
            WHERE {_CLASIFICACION_BALANCE_SQL} = :clasificacion
              AND ((Sal_Ano = :anio_a AND Sal_Mes = :mes_a) OR (Sal_Ano = :anio_b AND Sal_Mes = :mes_b))
            GROUP BY cod_n5
            HAVING SUM(CASE WHEN Sal_Ano = :anio_a AND Sal_Mes = :mes_a THEN Saldo ELSE 0 END) <> 0
                OR SUM(CASE WHEN Sal_Ano = :anio_b AND Sal_Mes = :mes_b THEN Saldo ELSE 0 END) <> 0
            ORDER BY monto_a DESC
            """
        ),
        {"anio_a": anio_a, "mes_a": mes_a, "anio_b": anio_b, "mes_b": mes_b, "clasificacion": clasificacion},
    ).mappings().all()
    return [
        (f["nombre_n5"], grupo_de_cuenta(mapas, f["codigo"]), _num(f["monto_a"]), _num(f["monto_b"]))
        for f in filas
    ]


def _pagina_balance_general_mensual(db: Session, anio: int, mes: int) -> BalanceGeneralMensual:
    anio_ant, mes_ant = _periodo_anterior(anio, mes)
    totales = _totales_balance_general(db, anio, mes)
    total_para_porcentajes = totales["activo"] or 1.0  # evita división por cero sin datos

    kpis = KpisBalanceGeneralMensual(
        activo=totales["activo"],
        pasivo=totales["pasivo"],
        patrimonio=totales["patrimonio"],
        porcentaje_activo=totales["activo"] / total_para_porcentajes * 100,
        porcentaje_pasivo=totales["pasivo"] / total_para_porcentajes * 100,
        porcentaje_patrimonio=totales["patrimonio"] / total_para_porcentajes * 100,
        porcentaje_fondos_por_aplicar=totales["fondos_por_aplicar"] / total_para_porcentajes * 100,
        balance_mensual=totales["activo"] - (totales["pasivo"] + totales["patrimonio"] + totales["fondos_por_aplicar"]),
    )

    distribucion = [
        DistribucionBalanceItem(etiqueta="Activo", monto=totales["activo"]),
        DistribucionBalanceItem(etiqueta="Pasivo", monto=totales["pasivo"]),
        DistribucionBalanceItem(etiqueta="Patrimonio", monto=totales["patrimonio"]),
        DistribucionBalanceItem(etiqueta="Fondos por aplicar", monto=totales["fondos_por_aplicar"]),
    ]

    def _detalle(clasificacion: str) -> list[DetalleCuentaBalance]:
        mapas, _ = cargar_mapas_agrupador(db, clasificacion)
        filas = _detalle_balance_periodo_a_vs_b(db, clasificacion, anio, mes, anio_ant, mes_ant, mapas)
        return [
            DetalleCuentaBalance(
                nombre_n5=nombre_n5,
                grupo=grupo,
                saldo_mes_anterior=monto_b,
                saldo_acumulado_actual=monto_a,
                variacion=monto_a - monto_b,
            )
            for nombre_n5, grupo, monto_a, monto_b in filas
        ]

    return BalanceGeneralMensual(
        kpis=kpis,
        distribucion_balance=distribucion,
        detalle_activo=_detalle("Activo"),
        detalle_pasivo=_detalle("Pasivo"),
        detalle_patrimonio=_detalle("Patrimonio"),
    )


def _pagina_balance_general_comparativo(db: Session, anio: int, mes: int) -> BalanceGeneralComparativo:
    anio_ant = anio - 1
    actual = _totales_balance_general(db, anio, mes)
    anterior = _totales_balance_general(db, anio_ant, mes)

    def _diferencia_pct(actual_v: float, anterior_v: float) -> float:
        return ((actual_v - anterior_v) / anterior_v * 100) if anterior_v else 0.0

    total_actual = actual["activo"]
    total_anterior = anterior["activo"]

    kpis = KpisBalanceGeneralComparativo(
        diferencia_porcentaje_activo=_diferencia_pct(actual["activo"], anterior["activo"]),
        variacion_q_activo=actual["activo"] - anterior["activo"],
        diferencia_porcentaje_pasivo=_diferencia_pct(actual["pasivo"], anterior["pasivo"]),
        variacion_q_pasivo=actual["pasivo"] - anterior["pasivo"],
        diferencia_porcentaje_patrimonio=_diferencia_pct(actual["patrimonio"], anterior["patrimonio"]),
        variacion_q_patrimonio=actual["patrimonio"] - anterior["patrimonio"],
        total_acumulado_anterior=total_anterior,
        total_acumulado_actual=total_actual,
        total_variacion=total_actual - total_anterior,
        balance_acumulado=actual["activo"] - (actual["pasivo"] + actual["patrimonio"] + actual["fondos_por_aplicar"]),
    )

    def _detalle(clasificacion: str) -> list[DetalleCuentaBalanceComparativo]:
        mapas, _ = cargar_mapas_agrupador(db, clasificacion)
        filas = _detalle_balance_periodo_a_vs_b(db, clasificacion, anio, mes, anio_ant, mes, mapas)
        return [
            DetalleCuentaBalanceComparativo(
                nombre_n5=nombre_n5,
                grupo=grupo,
                saldo_acumulado_actual=monto_a,
                saldo_acumulado_anterior=monto_b,
                variacion=monto_a - monto_b,
            )
            for nombre_n5, grupo, monto_a, monto_b in filas
        ]

    return BalanceGeneralComparativo(
        kpis=kpis,
        detalle_activo=_detalle("Activo"),
        detalle_pasivo=_detalle("Pasivo"),
        detalle_patrimonio=_detalle("Patrimonio"),
    )


def obtener_dashboard_financiero(
    db: Session, anio: int | None, mes: int | None
) -> DashboardFinancieroResponse:
    anio_resuelto, mes_resuelto = _anio_mes_default(db, anio, mes)

    pagina1 = _pagina_ingresos_desembolsos_mensual(db, anio_resuelto, mes_resuelto)
    pagina2 = _pagina_ingresos_desembolsos_acumulado(db, anio_resuelto, mes_resuelto, pagina1.kpis)
    pagina3 = _pagina_balance_general_mensual(db, anio_resuelto, mes_resuelto)
    pagina4 = _pagina_balance_general_comparativo(db, anio_resuelto, mes_resuelto)

    return DashboardFinancieroResponse(
        anio=anio_resuelto,
        mes=mes_resuelto,
        ingresos_desembolsos_mensual=pagina1,
        ingresos_desembolsos_acumulado=pagina2,
        balance_general_mensual=pagina3,
        balance_general_comparativo=pagina4,
    )
