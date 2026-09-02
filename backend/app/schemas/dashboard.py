from pydantic import BaseModel


class RankingItem(BaseModel):
    etiqueta: str
    cif_usd: float


class ResumenItem(BaseModel):
    etiqueta: str
    transacciones: int
    cif_usd: float
    porcentaje_del_total: float


class ComparacionMensual(BaseModel):
    mes: int
    cif_usd_actual: float
    cif_usd_anterior: float


class ComparacionAcumuladaMensual(BaseModel):
    mes: int
    cif_usd_actual_acumulado: float
    cif_usd_anterior_acumulado: float


class PuntoAcumuladoAnual(BaseModel):
    mes: int
    cif_usd_acumulado: float


class SerieAcumuladoAnual(BaseModel):
    anio: int
    puntos: list[PuntoAcumuladoAnual]


# --- Plaguicidas ---


class KpisPlaguicidas(BaseModel):
    cif_total_usd: float
    cif_total_q: float
    registros: int
    ingredientes_activos: int


class DetalleTransaccionPlaguicida(BaseModel):
    # Todas las columnas reales de dbo.Importacion / el archivo fuente
    # (sección 7 de la guía: "y más columnas al hacer scroll horizontal"),
    # salvo fechamod/userid (metadata interna de auditoría de carga, no
    # es un dato de la transacción en sí — no se muestra en ninguna otra
    # tabla/exportación de la app tampoco).
    anio: int | None
    fecha: str | None
    recibointerno: str | None
    serie_sat: str | None
    numero_recibo_sat: str | None
    aplicacion: str | None
    importador: str | None
    producto: str | None
    ingrediente_act: str | None
    exportador: str | None
    origen: str | None
    porcentaje: float | None
    cantidad: float | None
    unidad_medida: str | None
    cif_usd: float | None
    cif_q: float | None
    tipo_cambio: str | None
    institucion: str | None
    umsp: float | None
    grupo: str | None
    codigo_agrupador: str | None


class PaginaDetallePlaguicidas(BaseModel):
    total: int
    pagina: int
    tamano_pagina: int
    filas: list[DetalleTransaccionPlaguicida]


class NombreComercialItem(BaseModel):
    producto: str
    grupo: str | None
    aplicacion: str | None
    importador: str | None
    origen: str | None
    cantidad: float
    unidad_medida: str | None
    cif_usd: float
    cif_q: float
    categoria_aplicacion: str


class GrupoItem(BaseModel):
    grupo: str
    porcentaje_del_total: float
    aplicacion_principal: str | None
    cantidad: float
    unidad_medida: str | None
    cif_usd: float
    cif_q: float
    categoria_aplicacion: str


class DashboardPlaguicidasResponse(BaseModel):
    anio_actual: int
    anio_anterior: int
    mes_seleccionado: int
    mes_maximo: int
    kpis: KpisPlaguicidas
    comparacion_acumulada_mensual: list[ComparacionAcumuladaMensual]
    comparacion_mensual: list[ComparacionMensual]
    comparativo_acumulado_multianual: list[SerieAcumuladoAnual]
    diversificacion_aplicacion: list[RankingItem]
    top_ingredientes: list[RankingItem]
    top_importadores: list[RankingItem]
    top_origenes: list[ResumenItem]
    tabla_nombres_comerciales: list[NombreComercialItem]
    tabla_grupos: list[GrupoItem]
    detalle: PaginaDetallePlaguicidas


# --- Nutrientes ---


class KpisNutrientes(BaseModel):
    cif_total_usd: float
    cif_total_q: float
    registros: int
    empresas: int


class DetalleLicenciaNutriente(BaseModel):
    aduana: str | None
    no_licencia: str | None
    no_registro: str | None
    nombre_comercial: str | None
    empresa_importadora: str | None
    fecha_emision: str | None
    unidad: str | None


class PaginaDetalleNutrientes(BaseModel):
    total: int
    pagina: int
    tamano_pagina: int
    filas: list[DetalleLicenciaNutriente]


class FormulaComponenteItem(BaseModel):
    componente: str
    porcentaje_del_total: float
    concentracion_principal: str | None
    cantidad: float
    unidad: str | None
    cif_usd: float
    cif_q: float


class DashboardNutrientesResponse(BaseModel):
    anio_actual: int
    anio_anterior: int
    mes_seleccionado: int
    mes_maximo: int
    kpis: KpisNutrientes
    comparacion_acumulada_mensual: list[ComparacionAcumuladaMensual]
    comparacion_mensual: list[ComparacionMensual]
    comparativo_acumulado_multianual: list[SerieAcumuladoAnual]
    top_formulas: list[RankingItem]
    top_paises_origen: list[ResumenItem]
    top_aduanas: list[RankingItem]
    tabla_formulas_componentes: list[FormulaComponenteItem]
    detalle: PaginaDetalleNutrientes


# --- Opciones de filtro (para poblar dropdowns/autocompletado con valores reales) ---


class OpcionesFiltroPlaguicidas(BaseModel):
    anios: list[int]
    origenes: list[str]
    aplicaciones: list[str]
    ingredientes_activos: list[str]
    productos: list[str]


class OpcionesFiltroNutrientes(BaseModel):
    anios: list[int]
    paises_origen: list[str]
    componentes: list[str]
    nombres_comerciales: list[str]
    nombres_comerciales_raw: list[str]
