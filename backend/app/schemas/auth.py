from datetime import datetime
from typing import Literal

from pydantic import BaseModel

Tema = Literal["Claro", "Oscuro"]


class LoginRequest(BaseModel):
    nombre_usuario: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    rol: str
    puede_exportar: bool
    tema: Tema
    acceso_importaciones: bool
    acceso_financiero: bool
    acceso_indicadores: bool
    # Si es False, el frontend muestra el aviso legal bloqueando el
    # dashboard hasta que el usuario acepte (ver POST /auth/aviso-legal).
    aviso_legal_aceptado: bool


class ActualizarPreferenciasRequest(BaseModel):
    tema: Tema


class PreferenciasResponse(BaseModel):
    tema: Tema


class CambiarMiPasswordRequest(BaseModel):
    password_actual: str
    password_nueva: str


class AvisoLegalResponse(BaseModel):
    aceptado: bool
    fecha_aceptacion: datetime | None
