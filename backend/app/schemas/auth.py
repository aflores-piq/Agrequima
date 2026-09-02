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


class ActualizarPreferenciasRequest(BaseModel):
    tema: Tema


class PreferenciasResponse(BaseModel):
    tema: Tema


class CambiarMiPasswordRequest(BaseModel):
    password_actual: str
    password_nueva: str
