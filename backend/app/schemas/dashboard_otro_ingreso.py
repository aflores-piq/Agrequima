"""Schemas de "Otros ingresos generados" (sub-sección "Otros ingresos" del
Financiero, ver services/dashboard_otro_ingreso.py para el detalle de
fuente y fórmulas). Fuente: dbo.OtroIngreso -- export real de
Agrequima.dbo.OtroIngreso del servidor 10.10.0.6 (columnas Tipo,
Concepto, Anio, Mes, Valor), cargado desde docs/legacy/financiero/
OtroIngreso.csv con el mismo patrón que el resto del módulo."""

from pydantic import BaseModel


class FilaOtroIngreso(BaseModel):
    concepto: str
    ejecutado_anio_anterior: float
    presupuesto_anio: float
    ejecutado_anio: float
    porcentaje_ejecucion: float  # 0.0 si presupuesto_anio es 0


class OtroIngresoResponse(BaseModel):
    anio: int
    anio_anterior: int
    anios_disponibles: list[int]
    # Orden FIJO (ver ORDEN_CONCEPTOS en el service); conceptos nuevos no
    # listados van al final en orden alfabético.
    filas: list[FilaOtroIngreso]
    total: FilaOtroIngreso
