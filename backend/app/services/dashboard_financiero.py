"""Cálculos del dashboard Financiero (grupo "Estados Financieros", 4
páginas), sobre las tablas reales cargadas una sola vez desde CONTACC:

    dbo.BalanceSaldos(emp_nit, Cta_Codigo, Cta_Descripcion, Sal_Ano,
        Sal_Mes, Debitos, Creditos, Saldo, Cod_Centro)
    dbo.BalanceGeneral(emp_nit, Cod_n1, Nom_n1, cod_n5, nom_n5, Sal_Ano,
        Sal_Mes, Debitos, Creditos, Saldo, Inicial)

(ver services/cargar_datos_financiero_inicial.py -- carga real, no el
sync nocturno, que todavía no toca estas tablas).

Semántica CONFIRMADA contra los datos reales (validado cruzando cada
fórmula de acá contra los números exactos de las 4 capturas reales del
reporte viejo, ver docs/legacy/Financiero_capturas/ -- no asumida):

  - BalanceSaldos: cada fila es el MOVIMIENTO de una cuenta en un mes
    puntual (Debitos/Creditos/Saldo no acumulados). "Este mes" = SUM
    filtrando Sal_Ano/Sal_Mes exactos. "Acumulado del año" = SUM con
    Sal_Mes <= mes, dentro del MISMO Sal_Ano (reinicia cada enero).

  - BalanceGeneral: A PESAR del nombre ("balance general" sugiere saldo
    de punto en el tiempo), cada fila TAMBIÉN es un movimiento/
    transacción puntual, no un saldo corrido -- confirmado con datos
    reales: una cuenta con una sola transacción en enero no tiene fila
    en los meses siguientes, y sumar solo el mes exacto da un total muy
    por debajo del esperado. El saldo real de una cuenta a una fecha de
    corte se reconstruye SUMANDO Saldo desde enero hasta el mes filtrado
    DENTRO DEL MISMO AÑO (mismo patrón "acumulado" que BalanceSaldos,
    reinicia cada enero) -- validado exacto contra Activo/Patrimonio de
    2025 y 2026 en las capturas reales.

  - Clasificación contable (BalanceGeneral), confirmada contra los
    Cod_n1/cod_n5 reales (no los asumidos originalmente -- Cod_n1 acá
    son códigos de 4 dígitos tipo '1101', no '1'):
        Fondos por aplicar: cod_n5 = '210105001' (Cod_n1 viene NULL en
            los datos reales para esta cuenta puntual -- hay que
            revisarla ANTES que Cod_n1, no con un filtro de Cod_n1).
        Excluir: Cod_n1 = '3201' ("RESULTADOS AGREQUIMA" -- cuentas de
            memoria de resultado por ejercicio/año, NO forman parte del
            balance; los totales de Activo/Pasivo/Patrimonio cuadran
            exacto sin incluirlas).
        Activo: LEFT(Cod_n1, 1) = '1'.
        Patrimonio: Cod_n1 = '3101' ("PATRIMONIO AGREQUIMA" -- incluye
            más de una cuenta cod_n5, no solo la puntual '310101001').
        Pasivo (TOTAL, para KPI/tabla/banda/gráfico): LEFT(Cod_n1, 1) =
            '2' O Fondos por aplicar -- confirmado que el KPI "Pasivo"
            real (Q7,736,878 al cierre de junio 2026) es Cuentas por
            Pagar + Fondos por aplicar juntos, no por separado.
        Pasivo SOLO PARA LA DONA (página 3): LEFT(Cod_n1, 1) = '2' pero
            EXCLUYENDO Fondos por aplicar -- la dona necesita 3
            porciones (Pasivo/Patrimonio/Fondos) que sumen exactamente
            Activo=100%; si Pasivo incluyera Fondos ahí, sumaría más
            del doble de Activo.

"Grupo" (todas las tablas de detalle) sale de dbo.CatalogoAgrupadorCuentas
vía emparejamiento jerárquico por código (ver agrupador_cuentas.py) --
las filas de detalle se agregan POR GRUPO (no por cuenta individual):
las 4 capturas reales muestran la matriz de Power BI ya colapsada a
nivel de Grupo (sin desglose de cuenta individual visible), así que esa
es la granularidad que se replica acá.
"""

from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.dashboard_financiero import (
    BalanceGeneralComparativo,
    BalanceGeneralMensual,
    BarraTresCategorias,
    DashboardFinancieroResponse,
    DistribucionBalanceItem,
    FilaCuentaBalanceComparativa,
    FilaCuentaBalanceMensual,
    FilaCuentaComparativa,
    FilaCuentaMensual,
    FilaGrupoBalanceComparativa,
    FilaGrupoBalanceMensual,
    FilaGrupoComparativa,
    FilaGrupoMensual,
    IngresosDesembolsosAcumulado,
    IngresosDesembolsosMensual,
    KpiComparativoActivoPasivoPatrimonio,
    KpisBalanceGeneralComparativo,
    KpisBalanceGeneralMensual,
    KpisIngresosDesembolsosAcumulado,
    KpisIngresosDesembolsosMensual,
    PeriodoDisponible,
    SerieAnioBalance,
    SerieAnioTresCategorias,
    TotalBalanceComparativo,
    TotalBalanceMensual,
    TotalComparativo,
    TotalMensual,
)
from app.services.agrupador_cuentas import MapasAgrupador, cargar_mapas_agrupador, grupo_de_cuenta

MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]

# CASE compartido por las consultas de BalanceGeneral -- ver semántica
# confirmada en el docstring de arriba.
_CLASIFICACION_BALANCE_SQL = """
    CASE
        WHEN cod_n5 = '210105001' THEN 'FondosPorAplicar'
        WHEN Cod_n1 = '3201' THEN 'Excluir'
        WHEN LEFT(Cod_n1, 1) = '1' THEN 'Activo'
        WHEN Cod_n1 = '3101' THEN 'Patrimonio'
        WHEN LEFT(Cod_n1, 1) = '2' THEN 'Pasivo'
        ELSE 'Otro'
    END
"""


def _num(valor) -> float:
    return float(valor) if valor is not None else 0.0


def _periodo_anterior(anio: int, mes: int) -> tuple[int, int]:
    return (anio - 1, 12) if mes == 1 else (anio, mes - 1)


def _etiqueta_mes(anio_ref: int, anio: int, mes: int) -> str:
    """Nombre del mes, con el año agregado si es distinto del año
    filtrado (ej. "Diciembre 2025" al filtrar Enero 2026)."""
    nombre = MESES[mes - 1]
    return nombre if anio == anio_ref else f"{nombre} {anio}"


def _periodos_disponibles(db: Session) -> list[PeriodoDisponible]:
    filas = db.execute(
        text(
            """
            SELECT DISTINCT Sal_Ano, Sal_Mes FROM dbo.BalanceSaldos
            UNION
            SELECT DISTINCT Sal_Ano, Sal_Mes FROM dbo.BalanceGeneral
            ORDER BY Sal_Ano, Sal_Mes
            """
        )
    ).all()
    return [PeriodoDisponible(anio=int(a), mes=int(m)) for a, m in filas if a is not None and m is not None]


def _anio_mes_default(db: Session, anio: int | None, mes: int | None, periodos: list[PeriodoDisponible]) -> tuple[int, int]:
    if not periodos:
        hoy = date.today()
        return anio or hoy.year, mes or hoy.month
    if anio is not None and mes is not None:
        return anio, mes
    ultimo = periodos[-1]
    return anio or ultimo.anio, mes or ultimo.mes


# --- Página 1: Estado de ingresos y desembolsos mensual ---------------


def _detalle_grupo_mensual(
    db: Session, anio: int, mes: int, anio_ant: int, mes_ant: int, columna: str, mapas: MapasAgrupador
) -> tuple[list[FilaGrupoMensual], TotalMensual]:
    filas = db.execute(
        text(
            f"""
            SELECT
                Cta_Codigo AS codigo,
                MAX(Cta_Descripcion) AS nombre,
                SUM(CASE WHEN Sal_Ano = :anio_ant AND Sal_Mes = :mes_ant THEN {columna} ELSE 0 END) AS mes_anterior,
                SUM(CASE WHEN Sal_Ano = :anio AND Sal_Mes = :mes THEN {columna} ELSE 0 END) AS mes_actual,
                SUM(CASE WHEN Sal_Ano = :anio AND Sal_Mes <= :mes THEN {columna} ELSE 0 END) AS acumulado_anio
            FROM dbo.BalanceSaldos
            WHERE (Sal_Ano = :anio_ant AND Sal_Mes = :mes_ant) OR (Sal_Ano = :anio AND Sal_Mes <= :mes)
            GROUP BY Cta_Codigo
            HAVING SUM(CASE WHEN Sal_Ano = :anio_ant AND Sal_Mes = :mes_ant THEN {columna} ELSE 0 END) <> 0
                OR SUM(CASE WHEN Sal_Ano = :anio AND Sal_Mes <= :mes THEN {columna} ELSE 0 END) <> 0
            """
        ),
        {"anio": anio, "mes": mes, "anio_ant": anio_ant, "mes_ant": mes_ant},
    ).mappings().all()

    por_grupo: dict[str, dict] = {}
    for f in filas:
        grupo = grupo_de_cuenta(mapas, f["codigo"]) or "Sin clasificar"
        acc = por_grupo.setdefault(grupo, {"totales": [0.0, 0.0, 0.0], "cuentas": []})
        mes_anterior, mes_actual, acumulado_anio = _num(f["mes_anterior"]), _num(f["mes_actual"]), _num(f["acumulado_anio"])
        acc["totales"][0] += mes_anterior
        acc["totales"][1] += mes_actual
        acc["totales"][2] += acumulado_anio
        acc["cuentas"].append(
            FilaCuentaMensual(cuenta=f["nombre"] or f["codigo"], mes_anterior=mes_anterior, mes_actual=mes_actual, acumulado_anio=acumulado_anio)
        )

    detalle = [
        FilaGrupoMensual(
            grupo=g,
            mes_anterior=v["totales"][0],
            mes_actual=v["totales"][1],
            acumulado_anio=v["totales"][2],
            cuentas=sorted(v["cuentas"], key=lambda c: -c.acumulado_anio),
        )
        for g, v in por_grupo.items()
    ]
    detalle.sort(key=lambda f: -f.acumulado_anio)
    total = TotalMensual(
        mes_anterior=sum(f.mes_anterior for f in detalle),
        mes_actual=sum(f.mes_actual for f in detalle),
        acumulado_anio=sum(f.acumulado_anio for f in detalle),
    )
    return detalle, total


def _pagina_ingresos_desembolsos_mensual(db: Session, anio: int, mes: int) -> IngresosDesembolsosMensual:
    anio_ant, mes_ant = _periodo_anterior(anio, mes)
    mapas_ingresos, _ = cargar_mapas_agrupador(db, "Ingresos")
    mapas_egresos, _ = cargar_mapas_agrupador(db, "Egresos")

    detalle_ingresos, total_ingresos = _detalle_grupo_mensual(db, anio, mes, anio_ant, mes_ant, "Creditos", mapas_ingresos)
    detalle_egresos, total_egresos = _detalle_grupo_mensual(db, anio, mes, anio_ant, mes_ant, "Debitos", mapas_egresos)

    kpis = KpisIngresosDesembolsosMensual(
        ingresos=total_ingresos.mes_actual,
        egresos=total_egresos.mes_actual,
        resultado=total_ingresos.mes_actual - total_egresos.mes_actual,
    )
    resultado_del_ejercicio = TotalMensual(
        mes_anterior=total_ingresos.mes_anterior - total_egresos.mes_anterior,
        mes_actual=total_ingresos.mes_actual - total_egresos.mes_actual,
        acumulado_anio=total_ingresos.acumulado_anio - total_egresos.acumulado_anio,
    )

    etiqueta_mes_actual = _etiqueta_mes(anio, anio, mes)
    etiqueta_mes_anterior = _etiqueta_mes(anio, anio_ant, mes_ant)

    return IngresosDesembolsosMensual(
        kpis=kpis,
        etiqueta_mes_anterior=etiqueta_mes_anterior,
        etiqueta_mes_actual=etiqueta_mes_actual,
        etiqueta_acumulado=f"Acumulado Año {anio}",
        titulo_grafico_mes=f"Estado de Ingresos y Desembolsos {etiqueta_mes_actual} {anio}",
        titulo_grafico_acumulado=f"Acumulado al mes de {etiqueta_mes_actual} de {anio}",
        grafico_mes=BarraTresCategorias(
            ingresos=total_ingresos.mes_actual, egresos=total_egresos.mes_actual,
            resultado=total_ingresos.mes_actual - total_egresos.mes_actual,
        ),
        grafico_acumulado=BarraTresCategorias(
            ingresos=total_ingresos.acumulado_anio, egresos=total_egresos.acumulado_anio,
            resultado=total_ingresos.acumulado_anio - total_egresos.acumulado_anio,
        ),
        detalle_ingresos=detalle_ingresos,
        total_ingresos=total_ingresos,
        detalle_egresos=detalle_egresos,
        total_egresos=total_egresos,
        resultado_del_ejercicio=resultado_del_ejercicio,
    )


# --- Página 2: Estado de ingresos y desembolsos acumulado -------------


def _detalle_grupo_comparativo(
    db: Session, anio: int, anio_ant: int, mes: int, columna: str, mapas: MapasAgrupador
) -> tuple[list[FilaGrupoComparativa], TotalComparativo]:
    filas = db.execute(
        text(
            f"""
            SELECT
                Cta_Codigo AS codigo,
                MAX(Cta_Descripcion) AS nombre,
                SUM(CASE WHEN Sal_Ano = :anio_ant AND Sal_Mes <= :mes THEN {columna} ELSE 0 END) AS anio_anterior,
                SUM(CASE WHEN Sal_Ano = :anio AND Sal_Mes <= :mes THEN {columna} ELSE 0 END) AS anio_actual
            FROM dbo.BalanceSaldos
            WHERE (Sal_Ano = :anio_ant OR Sal_Ano = :anio) AND Sal_Mes <= :mes
            GROUP BY Cta_Codigo
            HAVING SUM(CASE WHEN Sal_Ano = :anio_ant AND Sal_Mes <= :mes THEN {columna} ELSE 0 END) <> 0
                OR SUM(CASE WHEN Sal_Ano = :anio AND Sal_Mes <= :mes THEN {columna} ELSE 0 END) <> 0
            """
        ),
        {"anio": anio, "anio_ant": anio_ant, "mes": mes},
    ).mappings().all()

    por_grupo: dict[str, dict] = {}
    for f in filas:
        grupo = grupo_de_cuenta(mapas, f["codigo"]) or "Sin clasificar"
        acc = por_grupo.setdefault(grupo, {"totales": [0.0, 0.0], "cuentas": []})
        anio_anterior, anio_actual = _num(f["anio_anterior"]), _num(f["anio_actual"])
        acc["totales"][0] += anio_anterior
        acc["totales"][1] += anio_actual
        acc["cuentas"].append(
            FilaCuentaComparativa(cuenta=f["nombre"] or f["codigo"], anio_anterior=anio_anterior, anio_actual=anio_actual, variacion=anio_actual - anio_anterior)
        )

    detalle = [
        FilaGrupoComparativa(
            grupo=g,
            anio_anterior=v["totales"][0],
            anio_actual=v["totales"][1],
            variacion=v["totales"][1] - v["totales"][0],
            cuentas=sorted(v["cuentas"], key=lambda c: -c.anio_actual),
        )
        for g, v in por_grupo.items()
    ]
    detalle.sort(key=lambda f: -f.anio_actual)
    total = TotalComparativo(
        anio_anterior=sum(f.anio_anterior for f in detalle),
        anio_actual=sum(f.anio_actual for f in detalle),
        variacion=sum(f.variacion for f in detalle),
    )
    return detalle, total


def _pagina_ingresos_desembolsos_acumulado(db: Session, anio: int, mes: int) -> IngresosDesembolsosAcumulado:
    anio_ant = anio - 1
    mapas_ingresos, _ = cargar_mapas_agrupador(db, "Ingresos")
    mapas_egresos, _ = cargar_mapas_agrupador(db, "Egresos")

    detalle_ingresos, total_ingresos = _detalle_grupo_comparativo(db, anio, anio_ant, mes, "Creditos", mapas_ingresos)
    detalle_egresos, total_egresos = _detalle_grupo_comparativo(db, anio, anio_ant, mes, "Debitos", mapas_egresos)

    kpis = KpisIngresosDesembolsosAcumulado(
        ingresos=total_ingresos.anio_actual,
        egresos=total_egresos.anio_actual,
        saldo=total_ingresos.anio_actual - total_egresos.anio_actual,
    )
    resultado_del_ejercicio = TotalComparativo(
        anio_anterior=total_ingresos.anio_anterior - total_egresos.anio_anterior,
        anio_actual=total_ingresos.anio_actual - total_egresos.anio_actual,
        variacion=(total_ingresos.anio_actual - total_egresos.anio_actual)
        - (total_ingresos.anio_anterior - total_egresos.anio_anterior),
    )

    etiqueta_mes = MESES[mes - 1]
    grafico = [
        SerieAnioTresCategorias(
            anio=anio_ant, ingresos=total_ingresos.anio_anterior, egresos=total_egresos.anio_anterior,
            resultado=total_ingresos.anio_anterior - total_egresos.anio_anterior,
        ),
        SerieAnioTresCategorias(
            anio=anio, ingresos=total_ingresos.anio_actual, egresos=total_egresos.anio_actual,
            resultado=total_ingresos.anio_actual - total_egresos.anio_actual,
        ),
    ]

    return IngresosDesembolsosAcumulado(
        kpis=kpis,
        etiqueta_anio_anterior=str(anio_ant),
        etiqueta_anio_actual=str(anio),
        titulo_grafico=f"Comparativo al mes de {etiqueta_mes} {anio_ant} vs. {anio}",
        grafico=grafico,
        detalle_ingresos=detalle_ingresos,
        total_ingresos=total_ingresos,
        detalle_egresos=detalle_egresos,
        total_egresos=total_egresos,
        resultado_del_ejercicio=resultado_del_ejercicio,
    )


# --- Páginas 3 y 4: Balance general -------------------------------------


def _totales_balance(db: Session, anio: int, mes: int) -> dict:
    """YTD dentro del año (Sal_Mes <= mes) -- ver semántica en el
    docstring del módulo: BalanceGeneral también son movimientos, no
    saldos corridos."""
    fila = db.execute(
        text(
            f"""
            SELECT
                SUM(CASE WHEN clasif = 'Activo' THEN Saldo ELSE 0 END) AS activo,
                SUM(CASE WHEN clasif IN ('Pasivo', 'FondosPorAplicar') THEN Saldo ELSE 0 END) AS pasivo,
                SUM(CASE WHEN clasif = 'Pasivo' THEN Saldo ELSE 0 END) AS pasivo_sin_fondos,
                SUM(CASE WHEN clasif = 'FondosPorAplicar' THEN Saldo ELSE 0 END) AS fondos,
                SUM(CASE WHEN clasif = 'Patrimonio' THEN Saldo ELSE 0 END) AS patrimonio
            FROM (
                SELECT Saldo, {_CLASIFICACION_BALANCE_SQL} AS clasif
                FROM dbo.BalanceGeneral
                WHERE Sal_Ano = :anio AND Sal_Mes <= :mes
            ) t
            """
        ),
        {"anio": anio, "mes": mes},
    ).mappings().first()
    return {
        "activo": _num(fila["activo"]),
        "pasivo": _num(fila["pasivo"]),
        "pasivo_sin_fondos": _num(fila["pasivo_sin_fondos"]),
        "fondos": _num(fila["fondos"]),
        "patrimonio": _num(fila["patrimonio"]),
    }


def _detalle_grupo_balance_mensual(
    db: Session, anio: int, mes: int, anio_ant: int, mes_ant: int, clasificaciones: tuple[str, ...], mapas: MapasAgrupador
) -> tuple[list[FilaGrupoBalanceMensual], TotalBalanceMensual]:
    placeholders = ", ".join(f":clasif{i}" for i in range(len(clasificaciones)))
    params = {f"clasif{i}": c for i, c in enumerate(clasificaciones)}
    filas = db.execute(
        text(
            f"""
            SELECT
                cod_n5 AS codigo,
                MAX(nom_n5) AS nombre,
                SUM(CASE WHEN Sal_Ano = :anio_ant AND Sal_Mes <= :mes_ant THEN Saldo ELSE 0 END) AS mes_anterior,
                SUM(CASE WHEN Sal_Ano = :anio AND Sal_Mes <= :mes THEN Saldo ELSE 0 END) AS mes_actual
            FROM (
                SELECT cod_n5, nom_n5, Saldo, Sal_Ano, Sal_Mes, {_CLASIFICACION_BALANCE_SQL} AS clasif
                FROM dbo.BalanceGeneral
                WHERE (Sal_Ano = :anio_ant AND Sal_Mes <= :mes_ant) OR (Sal_Ano = :anio AND Sal_Mes <= :mes)
            ) t
            WHERE clasif IN ({placeholders})
            GROUP BY cod_n5
            """
        ),
        {"anio": anio, "mes": mes, "anio_ant": anio_ant, "mes_ant": mes_ant, **params},
    ).mappings().all()

    por_grupo: dict[str, dict] = {}
    for f in filas:
        grupo = grupo_de_cuenta(mapas, f["codigo"]) or "Sin clasificar"
        acc = por_grupo.setdefault(grupo, {"totales": [0.0, 0.0], "cuentas": []})
        mes_anterior, mes_actual = _num(f["mes_anterior"]), _num(f["mes_actual"])
        acc["totales"][0] += mes_anterior
        acc["totales"][1] += mes_actual
        acc["cuentas"].append(
            FilaCuentaBalanceMensual(cuenta=f["nombre"] or f["codigo"], mes_anterior=mes_anterior, mes_actual=mes_actual, diferencia=mes_actual - mes_anterior)
        )

    detalle = [
        FilaGrupoBalanceMensual(
            grupo=g,
            mes_anterior=v["totales"][0],
            mes_actual=v["totales"][1],
            diferencia=v["totales"][1] - v["totales"][0],
            cuentas=sorted(v["cuentas"], key=lambda c: -c.mes_actual),
        )
        for g, v in por_grupo.items()
        if v["totales"][0] != 0 or v["totales"][1] != 0
    ]
    detalle.sort(key=lambda f: -f.mes_actual)
    total = TotalBalanceMensual(
        mes_anterior=sum(f.mes_anterior for f in detalle),
        mes_actual=sum(f.mes_actual for f in detalle),
        diferencia=sum(f.diferencia for f in detalle),
    )
    return detalle, total


def _pagina_balance_general_mensual(db: Session, anio: int, mes: int) -> BalanceGeneralMensual:
    anio_ant, mes_ant = _periodo_anterior(anio, mes)
    actual = _totales_balance(db, anio, mes)

    kpis = KpisBalanceGeneralMensual(activo=actual["activo"], pasivo=actual["pasivo"], patrimonio=actual["patrimonio"])

    activo_para_pct = actual["activo"] or 1.0
    distribucion = [
        DistribucionBalanceItem(etiqueta="Pasivo", monto=actual["pasivo_sin_fondos"], porcentaje=actual["pasivo_sin_fondos"] / activo_para_pct * 100),
        DistribucionBalanceItem(etiqueta="Patrimonio", monto=actual["patrimonio"], porcentaje=actual["patrimonio"] / activo_para_pct * 100),
        DistribucionBalanceItem(etiqueta="Fondos por aplicar", monto=actual["fondos"], porcentaje=actual["fondos"] / activo_para_pct * 100),
    ]

    mapas_activo, _ = cargar_mapas_agrupador(db, "Activo")
    mapas_pasivo, _ = cargar_mapas_agrupador(db, "Pasivo")
    mapas_patrimonio, _ = cargar_mapas_agrupador(db, "Patrimonio")

    detalle_activo, total_activo = _detalle_grupo_balance_mensual(db, anio, mes, anio_ant, mes_ant, ("Activo",), mapas_activo)
    detalle_pasivo, total_pasivo = _detalle_grupo_balance_mensual(db, anio, mes, anio_ant, mes_ant, ("Pasivo", "FondosPorAplicar"), mapas_pasivo)
    detalle_patrimonio, total_patrimonio = _detalle_grupo_balance_mensual(db, anio, mes, anio_ant, mes_ant, ("Patrimonio",), mapas_patrimonio)

    total_pasivo_y_patrimonio = TotalBalanceMensual(
        mes_anterior=total_pasivo.mes_anterior + total_patrimonio.mes_anterior,
        mes_actual=total_pasivo.mes_actual + total_patrimonio.mes_actual,
        diferencia=total_pasivo.diferencia + total_patrimonio.diferencia,
    )

    return BalanceGeneralMensual(
        kpis=kpis,
        etiqueta_mes_anterior=_etiqueta_mes(anio, anio_ant, mes_ant),
        etiqueta_mes_actual=_etiqueta_mes(anio, anio, mes),
        distribucion_balance=distribucion,
        activo_referencia=actual["activo"],
        detalle_activo=detalle_activo,
        total_activo=total_activo,
        detalle_pasivo=detalle_pasivo,
        total_pasivo=total_pasivo,
        detalle_patrimonio=detalle_patrimonio,
        total_patrimonio=total_patrimonio,
        total_pasivo_y_patrimonio=total_pasivo_y_patrimonio,
    )


def _detalle_grupo_balance_comparativo(
    db: Session, anio: int, anio_ant: int, mes: int, clasificaciones: tuple[str, ...], mapas: MapasAgrupador
) -> tuple[list[FilaGrupoBalanceComparativa], TotalBalanceComparativo]:
    placeholders = ", ".join(f":clasif{i}" for i in range(len(clasificaciones)))
    params = {f"clasif{i}": c for i, c in enumerate(clasificaciones)}
    filas = db.execute(
        text(
            f"""
            SELECT
                cod_n5 AS codigo,
                MAX(nom_n5) AS nombre,
                SUM(CASE WHEN Sal_Ano = :anio_ant AND Sal_Mes <= :mes THEN Saldo ELSE 0 END) AS anio_anterior,
                SUM(CASE WHEN Sal_Ano = :anio AND Sal_Mes <= :mes THEN Saldo ELSE 0 END) AS anio_actual
            FROM (
                SELECT cod_n5, nom_n5, Saldo, Sal_Ano, Sal_Mes, {_CLASIFICACION_BALANCE_SQL} AS clasif
                FROM dbo.BalanceGeneral
                WHERE (Sal_Ano = :anio_ant OR Sal_Ano = :anio) AND Sal_Mes <= :mes
            ) t
            WHERE clasif IN ({placeholders})
            GROUP BY cod_n5
            """
        ),
        {"anio": anio, "anio_ant": anio_ant, "mes": mes, **params},
    ).mappings().all()

    por_grupo: dict[str, dict] = {}
    for f in filas:
        grupo = grupo_de_cuenta(mapas, f["codigo"]) or "Sin clasificar"
        acc = por_grupo.setdefault(grupo, {"totales": [0.0, 0.0], "cuentas": []})
        anio_anterior, anio_actual = _num(f["anio_anterior"]), _num(f["anio_actual"])
        acc["totales"][0] += anio_anterior
        acc["totales"][1] += anio_actual
        acc["cuentas"].append(
            FilaCuentaBalanceComparativa(cuenta=f["nombre"] or f["codigo"], anio_anterior=anio_anterior, anio_actual=anio_actual, variacion=anio_actual - anio_anterior)
        )

    detalle = [
        FilaGrupoBalanceComparativa(
            grupo=g,
            anio_anterior=v["totales"][0],
            anio_actual=v["totales"][1],
            variacion=v["totales"][1] - v["totales"][0],
            cuentas=sorted(v["cuentas"], key=lambda c: -c.anio_actual),
        )
        for g, v in por_grupo.items()
        if v["totales"][0] != 0 or v["totales"][1] != 0
    ]
    detalle.sort(key=lambda f: -f.anio_actual)
    total = TotalBalanceComparativo(
        anio_anterior=sum(f.anio_anterior for f in detalle),
        anio_actual=sum(f.anio_actual for f in detalle),
        variacion=sum(f.variacion for f in detalle),
    )
    return detalle, total


def _pagina_balance_general_comparativo(db: Session, anio: int, mes: int) -> BalanceGeneralComparativo:
    anio_ant = anio - 1
    actual = _totales_balance(db, anio, mes)
    anterior = _totales_balance(db, anio_ant, mes)

    def _kpi(actual_v: float, anterior_v: float) -> KpiComparativoActivoPasivoPatrimonio:
        pct = ((actual_v - anterior_v) / anterior_v * 100) if anterior_v else 0.0
        return KpiComparativoActivoPasivoPatrimonio(diferencia_porcentaje=pct, variacion_q=actual_v - anterior_v)

    kpis = KpisBalanceGeneralComparativo(
        activo=_kpi(actual["activo"], anterior["activo"]),
        pasivo=_kpi(actual["pasivo"], anterior["pasivo"]),
        patrimonio=_kpi(actual["patrimonio"], anterior["patrimonio"]),
    )

    mapas_activo, _ = cargar_mapas_agrupador(db, "Activo")
    mapas_pasivo, _ = cargar_mapas_agrupador(db, "Pasivo")
    mapas_patrimonio, _ = cargar_mapas_agrupador(db, "Patrimonio")

    detalle_activo, total_activo = _detalle_grupo_balance_comparativo(db, anio, anio_ant, mes, ("Activo",), mapas_activo)
    detalle_pasivo, total_pasivo = _detalle_grupo_balance_comparativo(db, anio, anio_ant, mes, ("Pasivo", "FondosPorAplicar"), mapas_pasivo)
    detalle_patrimonio, total_patrimonio = _detalle_grupo_balance_comparativo(db, anio, anio_ant, mes, ("Patrimonio",), mapas_patrimonio)

    total_pasivo_y_patrimonio = TotalBalanceComparativo(
        anio_anterior=total_pasivo.anio_anterior + total_patrimonio.anio_anterior,
        anio_actual=total_pasivo.anio_actual + total_patrimonio.anio_actual,
        variacion=total_pasivo.variacion + total_patrimonio.variacion,
    )

    etiqueta_mes = MESES[mes - 1]
    grafico = [
        SerieAnioBalance(anio=anio_ant, activo=anterior["activo"], pasivo=anterior["pasivo"], patrimonio=anterior["patrimonio"]),
        SerieAnioBalance(anio=anio, activo=actual["activo"], pasivo=actual["pasivo"], patrimonio=actual["patrimonio"]),
    ]

    return BalanceGeneralComparativo(
        kpis=kpis,
        etiqueta_anio_anterior=str(anio_ant),
        etiqueta_anio_actual=str(anio),
        titulo_grafico=f"Comparativo Balance General al mes de {etiqueta_mes} {anio} vs {anio_ant}",
        grafico=grafico,
        detalle_activo=detalle_activo,
        total_activo=total_activo,
        detalle_pasivo=detalle_pasivo,
        total_pasivo=total_pasivo,
        detalle_patrimonio=detalle_patrimonio,
        total_patrimonio=total_patrimonio,
        total_pasivo_y_patrimonio=total_pasivo_y_patrimonio,
    )


def obtener_dashboard_financiero(
    db: Session, anio: int | None, mes: int | None
) -> DashboardFinancieroResponse:
    periodos = _periodos_disponibles(db)
    anio_resuelto, mes_resuelto = _anio_mes_default(db, anio, mes, periodos)

    pagina1 = _pagina_ingresos_desembolsos_mensual(db, anio_resuelto, mes_resuelto)
    pagina2 = _pagina_ingresos_desembolsos_acumulado(db, anio_resuelto, mes_resuelto)
    pagina3 = _pagina_balance_general_mensual(db, anio_resuelto, mes_resuelto)
    pagina4 = _pagina_balance_general_comparativo(db, anio_resuelto, mes_resuelto)

    return DashboardFinancieroResponse(
        anio=anio_resuelto,
        mes=mes_resuelto,
        periodos_disponibles=periodos,
        ingresos_desembolsos_mensual=pagina1,
        ingresos_desembolsos_acumulado=pagina2,
        balance_general_mensual=pagina3,
        balance_general_comparativo=pagina4,
    )
