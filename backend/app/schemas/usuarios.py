from datetime import datetime

from pydantic import BaseModel, Field


class UsuarioOut(BaseModel):
    usuario_id: int
    nombre_usuario: str
    nombre_completo: str | None
    email: str | None
    empresa: str | None
    rol: str
    activo: bool
    puede_exportar: bool
    fecha_creacion: datetime | None
    ultimo_login: datetime | None
    acceso_importaciones: bool
    acceso_financiero: bool
    acceso_indicadores: bool


class UsuarioCreate(BaseModel):
    nombre_usuario: str
    password: str
    nombre_completo: str | None = None
    email: str | None = None
    empresa: str | None = Field(default=None, max_length=150)
    rol: str
    puede_exportar: bool = False
    acceso_importaciones: bool = True
    acceso_financiero: bool = False
    acceso_indicadores: bool = False


class UsuarioUpdate(BaseModel):
    rol: str | None = None
    # Vacío o solo espacios deja la empresa sin valor (NULL).
    empresa: str | None = Field(default=None, max_length=150)
    activo: bool | None = None
    puede_exportar: bool | None = None
    acceso_importaciones: bool | None = None
    acceso_financiero: bool | None = None
    acceso_indicadores: bool | None = None


class CambiarPasswordRequest(BaseModel):
    password: str
