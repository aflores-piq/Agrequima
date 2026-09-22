"""Schemas del grupo "Otros informes financieros" del dashboard Financiero
(sub-sección hermana de "Estados financieros" en el Sidebar) -- ver
services/dashboard_otros_informes.py para el detalle de cada página."""

from pydantic import BaseModel


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
    periodos_disponibles: list[int]
    kpis: KpisCuotasAsociados
    tipos: list[TipoCuotaAsociados]


# --- Ejecución de gastos (por mes / acumulado) --------------------------
#
# CORREGIDO -- versión anterior (tabla de 22 centros de costo individuales)
# descartada por completo: la estructura real (confirmada por la fórmula
# DAX del .pbix original Y por las capturas de referencia, ambas
# coinciden) agrupa por CATEGORÍA DE GASTO (GroupEgresos), no por centro
# de costo. Ver services/dashboard_otros_informes.py.


class PeriodoDisponibleGastos(BaseModel):
    anio: int
    mes: int


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
