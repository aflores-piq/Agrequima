from datetime import datetime

from pydantic import BaseModel


class NomenclaturaPlaguicidaItem(BaseModel):
    ingrediente_key: str
    agrupador: str | None
    codigo: str | None
    fecha_mod: datetime | None


class NomenclaturaPlaguicidaUpdate(BaseModel):
    agrupador: str
    codigo: str | None = None


class PaginaNomenclaturaPlaguicidas(BaseModel):
    total: int
    pagina: int
    tamano_pagina: int
    filas: list[NomenclaturaPlaguicidaItem]


class AgrupadorNutrienteItem(BaseModel):
    nombre_key: str
    producto_agrupado: str | None
    codigo: str | None
    fecha_mod: datetime | None


class AgrupadorNutrienteUpdate(BaseModel):
    producto_agrupado: str
    codigo: str | None = None


class PaginaAgrupadorNutrientes(BaseModel):
    total: int
    pagina: int
    tamano_pagina: int
    filas: list[AgrupadorNutrienteItem]


# --- Sección "sin agrupador" (ex pantalla de Excepciones, consolidada
# dentro de Nomenclatura — ver admin_nomenclatura.py) ---


class ResumenSinAgrupadorPlaguicida(BaseModel):
    ingrediente_key: str
    ingrediente_ejemplo: str | None
    transacciones: int
    cantidad_total: float
    cif_usd_total: float
    posible_error_captura: bool


class DetalleSinAgrupadorPlaguicida(BaseModel):
    recibointerno: str | None
    ingrediente_act: str | None
    ingrediente_key: str | None
    producto: str | None


class PaginaDetalleSinAgrupadorPlaguicidas(BaseModel):
    total: int
    pagina: int
    tamano_pagina: int
    filas: list[DetalleSinAgrupadorPlaguicida]


class SinAgrupadorPlaguicidasResponse(BaseModel):
    resumen: list[ResumenSinAgrupadorPlaguicida]
    detalle: PaginaDetalleSinAgrupadorPlaguicidas


class ResumenSinAgrupadorNutriente(BaseModel):
    nombre_key: str
    nombre_ejemplo: str | None
    transacciones: int
    cif_dolares_total: float
    posible_error_captura: bool


class DetalleSinAgrupadorNutriente(BaseModel):
    no_licencia: str | None
    nombre_comercial: str | None
    nombre_key: str | None


class PaginaDetalleSinAgrupadorNutrientes(BaseModel):
    total: int
    pagina: int
    tamano_pagina: int
    filas: list[DetalleSinAgrupadorNutriente]


class SinAgrupadorNutrientesResponse(BaseModel):
    resumen: list[ResumenSinAgrupadorNutriente]
    detalle: PaginaDetalleSinAgrupadorNutrientes
