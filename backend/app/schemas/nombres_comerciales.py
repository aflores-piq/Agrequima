from datetime import datetime

from pydantic import BaseModel, Field, field_validator


def _nombre_limpio(v: str) -> str:
    v = " ".join(v.split())
    if not v:
        raise ValueError("El nombre estándar no puede estar vacío.")
    if len(v) > 400:
        raise ValueError("El nombre es demasiado largo (máximo 400 caracteres).")
    return v


class VarianteNombre(BaseModel):
    clave: str
    nombre_original: str
    filas: int
    cif_usd: float


class GrupoNombre(BaseModel):
    nombre_homologado: str
    confirmada: bool
    claves: list[str]
    filas: int
    cif_usd: float
    puede_separar: bool
    fecha_mod: datetime | None = None
    usuario_mod: str | None = None
    variantes: list[VarianteNombre]


class PaginaGruposNombres(BaseModel):
    total: int
    pagina: int
    tamano_pagina: int
    pendientes_en_filtro: int
    total_pendientes: int
    total_confirmadas: int
    grupos: list[GrupoNombre]


class NombreNuevo(BaseModel):
    clave: str
    nombre_ejemplo: str
    filas: int
    cif_usd: float
    variantes: list[VarianteNombre]


class NuevosSinHomologarNombres(BaseModel):
    total: int
    pagina: int
    tamano_pagina: int
    nombres: list[NombreNuevo]


class UnirNombresPayload(BaseModel):
    claves: list[str] = Field(min_length=2)
    nombre_oficial: str

    @field_validator("nombre_oficial")
    @classmethod
    def _nombre(cls, v: str) -> str:
        return _nombre_limpio(v)


class RenombrarNombrePayload(BaseModel):
    nombre_actual: str
    nombre_nuevo: str

    @field_validator("nombre_nuevo")
    @classmethod
    def _nombre(cls, v: str) -> str:
        return _nombre_limpio(v)


class SepararNombrePayload(BaseModel):
    clave: str


class ConfirmarNombresPayload(BaseModel):
    nombres: list[str] = Field(min_length=1)


class ConfirmarPendientesNombresPayload(BaseModel):
    busqueda: str | None = None


class AsignarNombresPayload(BaseModel):
    claves: list[str] = Field(min_length=1)
    nombre_grupo: str
    grupo_nuevo: bool = False

    @field_validator("nombre_grupo")
    @classmethod
    def _nombre(cls, v: str) -> str:
        return _nombre_limpio(v)


class ResultadoNombres(BaseModel):
    mensaje: str
    nombre_oficial: str | None = None
    claves_afectadas: int = 0
    grupos_afectados: int = 0
    filas_sincronizadas: int = 0


class FilaExcelNombres(BaseModel):
    fila: int
    nombre: str
    nombre_estandar: str
    clave: str | None = None
    estado: str
    motivo: str | None = None
    nombre_actual: str | None = None


class ResultadoExcelNombres(BaseModel):
    aplicado: bool
    mensaje: str
    filas_leidas: int
    se_uniran: int
    nuevos: int
    sin_cambio: int
    conflictos: int
    repetidas: int
    filas_sincronizadas: int
    detalle: list[FilaExcelNombres]
