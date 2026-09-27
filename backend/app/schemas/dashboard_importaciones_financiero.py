"""Schemas de "Importaciones" DENTRO del módulo Financiero (sub-sección
hermana de "Presupuestos" en el Sidebar) -- ver
services/dashboard_importaciones_financiero.py para el detalle de cada
página. Distinto del dashboard "Importaciones" (Plaguicidas/Nutrientes,
dbo.Importacion visto desde ESE ángulo) -- acá se lee la MISMA tabla
dbo.Importacion pero agrupada por institucion (Agrequima/Gremiagro),
fuente real de ingresos de la gremial, confirmada con pbixray."""

from pydantic import BaseModel

from app.schemas.dashboard_otros_informes import PeriodoDisponibleGastos


# --- Compartido ----------------------------------------------------------


class FilaCIFMes(BaseModel):
    """Una fila de la tabla CIF por mes (o la fila de resumen "Total
    año"), tanto en "Ingresos por importación" como en cada bloque de
    "Ingresos por importación comparativo". Las columnas de año anterior/
    VAR/VAR% son None cuando ese año no tiene NINGÚN dato (el frontend
    muestra "—" en vez de $0/0.00% engañoso)."""

    mes: str
    cif_anio_anterior: float | None
    pct_anio_anterior: float | None
    cif_anio_actual: float
    pct_anio_actual: float
    variacion: float | None
    variacion_pct: float | None
    negrita: bool = False


class PuntoCIFMes(BaseModel):
    """Un punto de la gráfica Deneb de líneas CIF por mes (año-1 vs año).
    cif_anio_anterior es None cuando ese año no tiene ningún dato -- el
    frontend no dibuja esa serie en absoluto."""

    mes: str
    cif_anio_anterior: float | None
    cif_anio_actual: float


class PuntoPrecioMes(BaseModel):
    """Un punto de la gráfica de precio acumulado por kilolitro (3 líneas:
    Agrequima/Gremiagro/Total), del año seleccionado únicamente."""

    mes: str
    agrequima: float
    gremiagro: float
    total: float


# --- 1. Ingresos por importación ------------------------------------------


class IngresosImportacionResponse(BaseModel):
    anio: int
    anio_anterior: int
    anio_anterior_sin_datos: bool = False
    anios_disponibles: list[int]
    ultimo_mes_con_datos: int
    filas: list[FilaCIFMes]
    fila_total: FilaCIFMes
    grafico_cif: list[PuntoCIFMes]
    grafico_precio: list[PuntoPrecioMes]


# --- 2. Ingresos por importación comparativo ------------------------------


class BloqueComparativoInstitucion(BaseModel):
    institucion: str
    titulo: str
    anio_anterior_sin_datos: bool = False
    filas: list[FilaCIFMes]
    fila_total: FilaCIFMes
    grafico: list[PuntoCIFMes]


class ImportacionComparativoResponse(BaseModel):
    anio: int
    anio_anterior: int
    anios_disponibles: list[int]
    bloques: list[BloqueComparativoInstitucion]


# --- 3. Comparación importaciones Kilolitros ------------------------------


class TarjetaCambioCantidad(BaseModel):
    etiqueta: str
    mensaje: str


class FilaPrecioKilolitro(BaseModel):
    etiqueta: str
    precio_anio_anterior: float | None
    precio_anio_actual: float | None
    variacion_pct: float | None
    negrita: bool = False


class KilolitrosResponse(BaseModel):
    anio: int
    mes: int
    anio_anterior: int
    periodos_disponibles: list[PeriodoDisponibleGastos]
    tarjetas: list[TarjetaCambioCantidad]
    filas_precio: list[FilaPrecioKilolitro]


# --- 4. Ingresos por contribución 4.5 por millar --------------------------


class PuntoContribucionMes(BaseModel):
    mes: str
    anio_anterior: float
    presupuesto: float
    anio_actual: float


class TarjetaResumenContribucion(BaseModel):
    presupuesto: float
    realizado: float
    porcentaje_ejecucion: float | None  # None -> "Sin presupuesto"


class ContribucionMillarResponse(BaseModel):
    anio: int
    mes: int
    periodos_disponibles: list[PeriodoDisponibleGastos]
    grafico: list[PuntoContribucionMes]
    tarjeta_mes: TarjetaResumenContribucion
    tarjeta_acumulada: TarjetaResumenContribucion
