from datetime import datetime

from pydantic import BaseModel


class UsuarioOut(BaseModel):
    usuario_id: int
    nombre_usuario: str
    nombre_completo: str | None
    email: str | None
    rol: str
    activo: bool
    puede_exportar: bool
    fecha_creacion: datetime | None
    ultimo_login: datetime | None


class UsuarioCreate(BaseModel):
    nombre_usuario: str
    password: str
    nombre_completo: str | None = None
    email: str | None = None
    rol: str
    puede_exportar: bool = False


class UsuarioUpdate(BaseModel):
    rol: str | None = None
    activo: bool | None = None
    puede_exportar: bool | None = None
