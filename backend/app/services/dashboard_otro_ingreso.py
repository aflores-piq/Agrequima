"""Cálculos de "Otros ingresos generados" (sub-sección "Otros ingresos"
del Financiero). SQL crudo vía text(), sin ORM, mismo patrón que el
resto del módulo.

--- Fuente -----------------------------------------------------------

dbo.OtroIngreso: Tipo ('Ejecutado' | 'Presupuesto'), Concepto, Anio,
Mes, Valor. Export real de Agrequima.dbo.OtroIngreso del servidor
10.10.0.6, cargado desde docs/legacy/financiero/OtroIngreso.csv (ver
cargar_datos_financiero_inicial.py, función _cargar_otro_ingreso). En
desarrollo: años 2025 (12 meses completos) y 2026 (Enero-Agosto), 12
conceptos, cada uno con fila para TODOS los meses de ambos años (sin
huecos).

--- Fórmulas (DAX real, confirmado con pbixray) -----------------------

Los valores guardados en dbo.OtroIngreso son ACUMULADOS -- NO se suman
meses entre sí, se toma el valor del ÚLTIMO MES CON DATOS de cada año
(por concepto y tipo), igual que hace el DAX real
(Ejecutado_año_actual/Ejecutado_año_anterior/Presupuesto_año_actual):
    Ejecutado {Año} = valor con Tipo="Ejecutado" del año seleccionado,
        en el último mes con datos de ESE año (por concepto).
    Presupuesto {Año} = ídem con Tipo="Presupuesto".
    Ejecutado {Año-1} = ídem con Tipo="Ejecutado", año-1, último mes con
        datos de año-1 (0 si ese año no tiene ninguna fila para el
        concepto -- el DAX real usa IF(ISBLANK(...), 0, ...)).
    % ejecutado = Ejecutado{Año} / Presupuesto{Año} (0 si el presupuesto
        es 0 -- DAX real usa DIVIDE(...,...,0)).
    Total = suma de los conceptos; % total = total ejecutado / total
        presupuesto (mismo criterio, 0 si el total de presupuesto es 0).

Donde el DAX real usa YEAR(TODAY()) (medida TituloOtrosIngresos), acá se
usa el AÑO SELECCIONADO por el filtro.

--- Números de control (Año 2026), validados exactos ------------------

CropLife - Proyecto SPMF: Q837,981 / Q637,500 / Q626,528 / 98%
Gremiagro: Q300,000 / Q300,000 / Q100,000 / 33%
Venta de Material Reciclable(...): Q354,690 / Q275,000 / Q255,115 / 93%
Aporte Industria Fertilizantes: Q0 / Q0 / Q0 / 0%
Aporte Fundación Hanns R. Neumann Stiftung: Q152,875 / Q78,000 / Q36,250 / 46%
Intereses Bancarios e Inversión: Q176,472 / Q229,950 / Q131,301 / 57%
Carnet Aplicadores...: Q144,449 / Q125,000 / Q96,799 / 77%
Venta de Sellos: Q42,896 / Q40,000 / Q34,640 / 87%
Venta Minicentros de Plástico Reciclado: Q24,554 / Q20,000 / Q4,464 / 22%
Proyecto ATRACSI: Q0 / Q0 / Q0 / 0%
Localg.a.p. Guatemala: Q0 / Q0 / Q0 / 0%
Venta de Vehículos: Q15,000 / Q225,000 / Q0 / 0%
TOTAL: Q2,048,918 / Q1,930,450 / Q1,285,097 / 67%
"""

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.dashboard_otro_ingreso import FilaOtroIngreso, FilaResumenIngresos, OtroIngresoResponse, ResumenIngresos
from app.services.agrupador_cuentas import cargar_mapas_agrupador
from app.services.dashboard_financiero import _detalle_grupo_mensual, _periodo_anterior


def _num(valor) -> float:
    return float(valor) if valor is not None else 0.0


# Orden fijo pedido por el usuario -- los conceptos que no estén acá (de
# aparecer en el futuro) van al final, en orden alfabético.
ORDEN_CONCEPTOS = [
    "CropLife - Proyecto SPMF",
    "Gremiagro",
    "Venta de Material Reciclable(Chatarra, cartón, metal, plástico)",
    "Aporte Industria Fertilizantes",
    "Aporte Fundación Hanns R. Neumann Stiftung",
    "Intereses Bancarios e Inversión",
    "Carnet Aplicadores y Certificados, Cursos, Capacitaciones y Talleres y otras donaciones",
    "Venta de Sellos",
    "Venta Minicentros de Plástico Reciclado",
    "Proyecto ATRACSI",
    "Localg.a.p. Guatemala",
    "Venta de Vehículos",
]


def _ordenar_conceptos(conceptos: list[str]) -> list[str]:
    indice = {c: i for i, c in enumerate(ORDEN_CONCEPTOS)}
    conocidos = sorted((c for c in conceptos if c in indice), key=lambda c: indice[c])
    nuevos = sorted(c for c in conceptos if c not in indice)
    return conocidos + nuevos


def _anios_disponibles(db: Session) -> list[int]:
    filas = db.execute(text("SELECT DISTINCT Anio FROM dbo.OtroIngreso ORDER BY Anio")).all()
    return [int(a) for (a,) in filas if a is not None]


def _conceptos_disponibles(db: Session) -> list[str]:
    filas = db.execute(text("SELECT DISTINCT Concepto FROM dbo.OtroIngreso")).all()
    return [c for (c,) in filas if c is not None]


def _valores_por_concepto(db: Session, anio: int, tipo: str) -> dict[str, float]:
    """Valor del ÚLTIMO MES CON DATOS de ese año, por concepto (acumulado,
    no se suman meses) -- una sola consulta para todos los conceptos."""
    filas = db.execute(
        text(
            """
            SELECT o.Concepto, o.Valor
            FROM dbo.OtroIngreso o
            INNER JOIN (
                SELECT Concepto, MAX(Mes) AS UltimoMes
                FROM dbo.OtroIngreso
                WHERE Anio = :anio AND Tipo = :tipo
                GROUP BY Concepto
            ) u ON u.Concepto = o.Concepto AND u.UltimoMes = o.Mes
            WHERE o.Anio = :anio AND o.Tipo = :tipo
            """
        ),
        {"anio": anio, "tipo": tipo},
    ).all()
    return {c: _num(v) for c, v in filas}


def _porcentaje_ejecucion(ejecutado: float, presupuesto: float) -> float:
    return (ejecutado / presupuesto * 100) if presupuesto else 0.0


def _mes_corte(db: Session, anio: int) -> int | None:
    """Último mes con datos "Ejecutado" del año en dbo.OtroIngreso: el mismo mes del que
    salen los totales de esta pantalla (valores acumulados al último mes con datos)."""
    mes = db.execute(
        text("SELECT MAX(Mes) FROM dbo.OtroIngreso WHERE Anio = :anio AND Tipo = 'Ejecutado'"),
        {"anio": anio},
    ).scalar()
    return int(mes) if mes is not None else None


def _normalizar(nombre: str) -> str:
    return " ".join((nombre or "").lower().split())


def _resumen_ingresos(db: Session, anio: int, otros_ingresos: float) -> ResumenIngresos | None:
    """Cuadro de composición del total de ingresos del año, al mismo corte que los totales
    de la pantalla. Cuotas de asociados y 4.5 por millar salen de la MISMA función que arma
    el Estado de ingresos y desembolsos (columna "Acumulado Año" del grupo de ingresos), así
    que los montos son idénticos a los de esa pantalla para ese mes."""
    mes = _mes_corte(db, anio)
    if mes is None:
        return None
    anio_ant, mes_ant = _periodo_anterior(anio, mes)
    mapas_ingresos, _ = cargar_mapas_agrupador(db, "Ingresos")
    detalle, _total = _detalle_grupo_mensual(
        db, anio, mes, anio_ant, mes_ant, "Creditos", "Creditos", "Creditos - Debitos", mapas_ingresos, "4"
    )
    por_grupo = {_normalizar(f.grupo): f.acumulado_anio for f in detalle}
    cuotas_asociados = por_grupo.get("cuotas asociados", 0.0)
    cuotas_millar = por_grupo.get("cuotas 4.5 por millar", 0.0)
    total = cuotas_asociados + cuotas_millar + otros_ingresos

    def fila(concepto: str, monto: float) -> FilaResumenIngresos:
        return FilaResumenIngresos(concepto=concepto, monto=monto, porcentaje=(monto / total * 100) if total else 0.0)

    return ResumenIngresos(
        anio=anio,
        mes_corte=mes,
        filas=[
            fila("Cuotas de asociados", cuotas_asociados),
            fila("Cuotas 4.5 por millar", cuotas_millar),
            fila("Otros ingresos", otros_ingresos),
        ],
        total=fila("Total ingresos", total),
    )


def obtener_otro_ingreso(db: Session, anio: int | None) -> OtroIngresoResponse:
    anios_disponibles = _anios_disponibles(db)
    anio_resuelto = anio if anio is not None else (anios_disponibles[-1] if anios_disponibles else 0)
    anio_anterior = anio_resuelto - 1

    conceptos = _ordenar_conceptos(_conceptos_disponibles(db))

    ejecutado_actual = _valores_por_concepto(db, anio_resuelto, "Ejecutado")
    presupuesto_actual = _valores_por_concepto(db, anio_resuelto, "Presupuesto")
    ejecutado_anterior = _valores_por_concepto(db, anio_anterior, "Ejecutado")

    filas: list[FilaOtroIngreso] = []
    for concepto in conceptos:
        ej_act = ejecutado_actual.get(concepto, 0.0)
        pre_act = presupuesto_actual.get(concepto, 0.0)
        ej_ant = ejecutado_anterior.get(concepto, 0.0)
        filas.append(
            FilaOtroIngreso(
                concepto=concepto,
                ejecutado_anio_anterior=ej_ant,
                presupuesto_anio=pre_act,
                ejecutado_anio=ej_act,
                porcentaje_ejecucion=_porcentaje_ejecucion(ej_act, pre_act),
            )
        )

    total_ej_ant = sum(f.ejecutado_anio_anterior for f in filas)
    total_pre = sum(f.presupuesto_anio for f in filas)
    total_ej = sum(f.ejecutado_anio for f in filas)
    total = FilaOtroIngreso(
        concepto="Total",
        ejecutado_anio_anterior=total_ej_ant,
        presupuesto_anio=total_pre,
        ejecutado_anio=total_ej,
        porcentaje_ejecucion=_porcentaje_ejecucion(total_ej, total_pre),
    )

    return OtroIngresoResponse(
        anio=anio_resuelto,
        anio_anterior=anio_anterior,
        anio_anterior_sin_datos=anio_anterior not in anios_disponibles,
        anios_disponibles=anios_disponibles,
        filas=filas,
        total=total,
        resumen_ingresos=_resumen_ingresos(db, anio_resuelto, total_ej) if anio_resuelto else None,
    )
