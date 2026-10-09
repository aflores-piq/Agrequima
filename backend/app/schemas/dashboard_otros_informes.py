"""Schemas del grupo "Otros informes financieros" del dashboard Financiero
(sub-sección hermana de "Estados financieros" en el Sidebar) -- ver
services/dashboard_otros_informes.py para el detalle de cada página."""

from pydantic import BaseModel


# Compartido por todas las páginas de "Otros informes financieros" (y por
# Estados Financieros) -- un par año+mes real, para el selector "hasta el
# mes" que solo ofrece combinaciones que existen de verdad en los datos.
class PeriodoDisponibleGastos(BaseModel):
    anio: int
    mes: int


# --- Cuotas Asociados ---------------------------------------------------


class FilaCuotaAsociado(BaseModel):
    nombre: str
    cuota: float
    cancelado: float
    saldo: float


class TipoCuotaAsociados(BaseModel):
    tipo: str
    filas: list[FilaCuotaAsociado]
    total_cuota: float
    total_cancelado: float
    total_saldo: float


class KpisCuotasAsociados(BaseModel):
    total: float
    cancelado: float
    por_cobrar: float


class CuotasAsociadosResponse(BaseModel):
    anio: int
    mes: int
    periodos_disponibles: list[PeriodoDisponibleGastos]
    kpis: KpisCuotasAsociados
    tipos: list[TipoCuotaAsociados]


# --- Ejecución de gastos (por mes / acumulado) --------------------------
#
# CORREGIDO -- versión anterior (tabla de 22 centros de costo individuales)
# descartada por completo: la estructura real (confirmada por la fórmula
# DAX del .pbix original Y por las capturas de referencia, ambas
# coinciden) agrupa por CATEGORÍA DE GASTO (GroupEgresos), no por centro
# de costo. Ver services/dashboard_otros_informes.py.


class FilaGastoCategoria(BaseModel):
    """Una fila de la tabla principal (una categoría de GroupEgresos), o
    una de las 2 filas de resumen que van debajo con la misma forma
    ("Total ejecutado" ya viene incluido como una fila más de la tabla;
    "Presupuesto" y "Ejecución" son filas aparte, fuera de la tabla)."""

    categoria: str
    administracion: float
    peso_administracion: float
    operacion: float
    peso_operacion: float
    consolidado: float


class TarjetaResumenGasto(BaseModel):
    grupo: str
    presupuesto: float
    ejecutado: float
    porcentaje_ejecucion: float
    diferencia: float


class EjecucionGastosResponse(BaseModel):
    anio: int
    mes: int
    periodos_disponibles: list[PeriodoDisponibleGastos]
    categorias: list[FilaGastoCategoria]
    fila_total_ejecutado: FilaGastoCategoria
    fila_presupuesto: FilaGastoCategoria
    fila_ejecucion: FilaGastoCategoria
    tarjetas: list[TarjetaResumenGasto]


# --- Presupuestos: Ejecución vs presupuesto (mensual / acumulado) --------


class FilaPresupuesto(BaseModel):
    categoria: str
    presupuesto: float
    ejecutado: float
    diferencia: float
    diferencia_pct: float
    negrita: bool = False


class EjecucionVsPresupuestoResponse(BaseModel):
    anio: int
    mes: int
    periodos_disponibles: list[PeriodoDisponibleGastos]
    filas: list[FilaPresupuesto]
    fila_total: FilaPresupuesto


# --- Presupuestos: Comparativo ejecutado (año-1 vs año, acumulado) -------


class FilaComparativoEjecutado(BaseModel):
    categoria: str
    anio_anterior: float
    anio_actual: float
    variacion: float
    variacion_pct: float
    negrita: bool = False


class ComparativoEjecutadoResponse(BaseModel):
    anio: int
    mes: int
    anio_anterior: int
    periodos_disponibles: list[PeriodoDisponibleGastos]
    filas: list[FilaComparativoEjecutado]
    fila_total: FilaComparativoEjecutado


# --- Conciliación bancaria ------------------------------------------------
#
# "Saldo Contabilidad" sale de dbo.SaldosBancos (vw_piq_saldos_bancos.csv
# real). "Saldo Banco" es un estado de cuenta bancario independiente que
# HOY no tenemos cargado en ningún lado (dbo.SaldoBancario existe pero
# vacía, y aunque tuviera datos su esquema actual -- Concepto/Año/Mes/
# Banco/Valor, un solo "Valor" -- no alcanza para las 4 cifras que hacen
# falta por banco/mes) -- ver services/dashboard_otros_informes.py. Los
# campos *_saldo_banco quedan en None salvo "Documentos en Circulación",
# que SÍ es derivable de dbo.ChequesCirculacion.


class FilaConciliacionBanco(BaseModel):
    descripcion: str
    saldo_banco: float | None
    saldo_contabilidad: float | None
    negrita: bool = False


class BancoConciliacion(BaseModel):
    nombre: str
    color: str
    filas: list[FilaConciliacionBanco]


class InversionConciliacion(BaseModel):
    """Una cuenta de inversión (cod_n5 110103...), SIN sumar con otras del mismo banco."""

    banco: str  # nombre del banco como en CatalogoBancos (o el texto de la cuenta si no está)
    color: str
    descripcion: str  # nombre de la cuenta
    valor: float  # saldo al cierre del mes elegido (mismo cálculo que Flujo de caja)


class FilaResumenBanco(BaseModel):
    banco: str
    color: str
    total_banco: float | None  # Saldo Banco (cuenta monetaria) + sus inversiones
    total_contabilidad: float | None  # Saldo Contabilidad + sus inversiones


class ConciliacionBancariaResponse(BaseModel):
    anio: int
    mes: int
    periodos_disponibles: list[PeriodoDisponibleGastos]
    bancos: list[BancoConciliacion]
    # Sección "Inversiones": una fila por cada inversión.
    inversiones: list[InversionConciliacion] = []
    total_inversiones: float = 0.0
    # Sección "Resumen por banco": una fila por banco y la fila de total general.
    resumen_bancos: list[FilaResumenBanco] = []
    total_resumen_banco: float | None = None
    total_resumen_contabilidad: float | None = None


# --- Flujo de caja ---------------------------------------------------------


class FilaFlujoCaja(BaseModel):
    tipo: str
    descripcion: str
    saldos: float | None
    disponibilidad: float | None


class BarraFlujoCaja(BaseModel):
    etiqueta: str
    valor: float
    color: str


class ItemResumenFlujo(BaseModel):
    nombre: str
    valor: float


class InversionResumenFlujo(BaseModel):
    banco: str
    descripcion: str
    valor: float


class ResumenFlujoCaja(BaseModel):
    """Resumen expandible: caja y caja chica, bancos (con el detalle de cada banco),
    inversiones (con el detalle de cada inversión) y total. `total` es el mismo valor de la
    barra "Total disponibilidad" de la gráfica; caja + bancos = barra "Monetarios, Ahorro";
    inversiones = barra "Inversiones"."""

    caja: float
    bancos_total: float
    bancos: list[ItemResumenFlujo]
    inversiones_total: float
    inversiones: list[InversionResumenFlujo]
    total: float


class FlujoCajaResponse(BaseModel):
    anio: int
    mes: int
    periodos_disponibles: list[PeriodoDisponibleGastos]
    filas: list[FilaFlujoCaja]
    grafica: list[BarraFlujoCaja]
    resumen: ResumenFlujoCaja | None = None
