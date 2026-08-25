from datetime import datetime

from pydantic import BaseModel


class ResumenCargaPlaguicidas(BaseModel):
    filas_cargadas: int
    anios: list[int]
    meses_nuevos: list[int]
    filas_ya_cargadas: int
    filas_descartadas: int
    filas_truncadas: int
    combos_porcentaje: int
    porcentajes_no_parseables: int
    filas_sin_agrupador: int
    nomenclatura_actualizada: bool
    claves_nomenclatura_nuevas: int | None = None
    estado: str


class ResumenCargaNutrientes(BaseModel):
    filas_cargadas: int
    anios: list[int]
    meses_nuevos: list[int]
    filas_ya_cargadas: int
    filas_truncadas: int
    filas_sin_agrupador: int
    agrupador_actualizado: bool
    claves_agrupador_nuevas: int | None = None
    estado: str


class AuditoriaCargaItem(BaseModel):
    carga_id: int
    tipo_carga: str
    nombre_archivo: str | None
    usuario: str | None
    fecha_carga: datetime
    filas_procesadas: int | None
    filas_con_excepcion: int | None
    estado: str
    mensaje_error: str | None


class PaginaAuditoriaCargas(BaseModel):
    total: int
    pagina: int
    tamano_pagina: int
    filas: list[AuditoriaCargaItem]
