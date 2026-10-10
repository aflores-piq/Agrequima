from datetime import datetime

from pydantic import BaseModel


class FilaBitacoraIngreso(BaseModel):
    usuario: str
    nombre: str | None
    empresa: str | None
    # Hora de Guatemala (sin zona), tal como la registró la aplicación.
    fecha_hora: datetime


class BitacoraIngresosResponse(BaseModel):
    total: int
    filas: list[FilaBitacoraIngreso]
    empresas: list[str]
    usuarios: list[str]
