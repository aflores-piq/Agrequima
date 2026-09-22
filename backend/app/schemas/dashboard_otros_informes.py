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
