from pydantic import BaseModel


class ActualizarAgrupadorPlaguicidasRequest(BaseModel):
    ingrediente_key: str
    agrupador: str


class ActualizarAgrupadorNutrientesRequest(BaseModel):
    nombre_key: str
    agrupador: str


class ActualizarAgrupadorResponse(BaseModel):
    filas_actualizadas: int


class ResumenExcepcionPlaguicida(BaseModel):
    ingrediente_key: str
    ingrediente_ejemplo: str | None
    transacciones: int
    cantidad_total: float
    cif_usd_total: float
    posible_error_captura: bool


class DetalleExcepcionPlaguicida(BaseModel):
    recibointerno: str | None
    ingrediente_act: str | None
    ingrediente_key: str | None
    producto: str | None


class PaginaDetalleExcepcionesPlaguicidas(BaseModel):
    total: int
    pagina: int
    tamano_pagina: int
    filas: list[DetalleExcepcionPlaguicida]


class ExcepcionesPlaguicidasResponse(BaseModel):
    resumen: list[ResumenExcepcionPlaguicida]
    detalle: PaginaDetalleExcepcionesPlaguicidas


class ResumenExcepcionNutriente(BaseModel):
    nombre_key: str
    nombre_ejemplo: str | None
    transacciones: int
    cif_dolares_total: float
    posible_error_captura: bool


class DetalleExcepcionNutriente(BaseModel):
    no_licencia: str | None
    nombre_comercial: str | None
    nombre_key: str | None


class PaginaDetalleExcepcionesNutrientes(BaseModel):
    total: int
    pagina: int
    tamano_pagina: int
    filas: list[DetalleExcepcionNutriente]


class ExcepcionesNutrientesResponse(BaseModel):
    resumen: list[ResumenExcepcionNutriente]
    detalle: PaginaDetalleExcepcionesNutrientes
