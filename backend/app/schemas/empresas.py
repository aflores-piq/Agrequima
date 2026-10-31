from datetime import datetime

from pydantic import BaseModel, Field, field_validator


def _limpiar(valor: str) -> str:
    return " ".join(valor.split())


class OrigenMonto(BaseModel):
    filas: int = 0
    cif_usd: float = 0.0


class VarianteEmpresa(BaseModel):
    """Una forma en que la empresa viene escrita en los datos (nombre original) con su clave normalizada. Varios nombres
    pueden compartir la clave (solo difieren en mayúsculas, puntuación o "S.A."): se unen siempre."""

    clave: str
    nombre_original: str
    plaguicidas: OrigenMonto
    nutrientes: OrigenMonto
    cif_total_usd: float


class GrupoEmpresa(BaseModel):
    nombre_homologado: str
    confirmada: bool
    # "P" = solo Plaguicidas, "N" = solo Nutrientes, "ambas", "" = sin movimientos actuales
    origen: str
    claves: list[str]
    plaguicidas: OrigenMonto
    nutrientes: OrigenMonto
    cif_total_usd: float
    puede_separar: bool
    fecha_mod: datetime | None = None
    usuario_mod: str | None = None
    variantes: list[VarianteEmpresa]


class PaginaGruposEmpresas(BaseModel):
    total: int
    pagina: int
    tamano_pagina: int
    # Grupos pendientes que cumplen busqueda + origen (ignora el filtro de estado): es lo que confirmaría
    # "Confirmar todos los pendientes" con el filtro actual
    pendientes_en_filtro: int
    total_pendientes: int
    total_confirmadas: int
    grupos: list[GrupoEmpresa]


class EmpresaNueva(BaseModel):
    clave: str
    nombre_ejemplo: str
    origenes: list[str]
    plaguicidas: OrigenMonto
    nutrientes: OrigenMonto
    cif_total_usd: float
    ultima_carga: datetime | None = None


class NuevasSinHomologarResponse(BaseModel):
    total: int
    empresas: list[EmpresaNueva]


class UnirPayload(BaseModel):
    claves: list[str] = Field(min_length=2)
    nombre_oficial: str

    @field_validator("nombre_oficial")
    @classmethod
    def _nombre(cls, v: str) -> str:
        v = _limpiar(v)
        if not v:
            raise ValueError("El nombre oficial no puede estar vacío.")
        if len(v) > 400:
            raise ValueError("El nombre oficial es demasiado largo (máximo 400 caracteres).")
        return v


class RenombrarPayload(BaseModel):
    nombre_actual: str
    nombre_nuevo: str

    @field_validator("nombre_nuevo")
    @classmethod
    def _nombre(cls, v: str) -> str:
        v = _limpiar(v)
        if not v:
            raise ValueError("El nombre oficial no puede estar vacío.")
        if len(v) > 400:
            raise ValueError("El nombre oficial es demasiado largo (máximo 400 caracteres).")
        return v


class SepararPayload(BaseModel):
    clave: str


class ConfirmarPayload(BaseModel):
    nombres: list[str] = Field(min_length=1)


class ConfirmarPendientesPayload(BaseModel):
    """Mismo filtro de la lista (busqueda + origen): confirma los grupos pendientes que lo cumplen."""

    busqueda: str | None = None
    origen: str = "todas"


class AsignarNuevasPayload(BaseModel):
    claves: list[str] = Field(min_length=1)
    nombre_grupo: str
    # True: crea un grupo con ese nombre (no debe existir). False: se agregan al grupo existente con ese nombre.
    grupo_nuevo: bool = False

    @field_validator("nombre_grupo")
    @classmethod
    def _nombre(cls, v: str) -> str:
        v = _limpiar(v)
        if not v:
            raise ValueError("El nombre oficial no puede estar vacío.")
        if len(v) > 400:
            raise ValueError("El nombre oficial es demasiado largo (máximo 400 caracteres).")
        return v


class ResultadoHomologacion(BaseModel):
    mensaje: str
    nombre_oficial: str | None = None
    claves_afectadas: int = 0
    grupos_afectados: int = 0
    filas_sincronizadas: int = 0
