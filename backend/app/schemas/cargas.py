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
    # Empresas (distintas) de esta carga cuya clave no estaba en dbo.CatalogoEmpresas: quedan sin homologar
    empresas_sin_homologar: int = 0
    # Nombres comerciales (distintos) de esta carga que no estaban en dbo.CatalogoNombresComerciales
    nombres_sin_homologar: int = 0
    estado: str


class ResumenCargaNutrientes(BaseModel):
    filas_cargadas: int
    anios: list[int]
    meses_nuevos: list[int]
    filas_ya_cargadas: int
    filas_truncadas: int
    filas_descartadas_sin_f: int
    filas_sin_agrupador: int
    agrupador_actualizado: bool
    claves_agrupador_nuevas: int | None = None
    # Empresas (distintas) de esta carga cuya clave no estaba en dbo.CatalogoEmpresas: quedan sin homologar
    empresas_sin_homologar: int = 0
    estado: str


class PeriodoCubierto(BaseModel):
    anio: int
    mes: int


class ResumenCargaFinanciero(BaseModel):
    """Compartido por Saldos Bancarios y Otros Ingresos -- cargas
    directas (sin cruce de catálogo), estrategia DELETE + INSERT por
    cada período (año/mes) presente en el archivo."""

    filas_cargadas: int
    periodos: list[PeriodoCubierto]
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
