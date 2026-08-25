from datetime import datetime

from pydantic import BaseModel


class NomenclaturaPlaguicidaItem(BaseModel):
    ingrediente_key: str
    agrupador: str | None
    codigo: str | None
    fecha_mod: datetime | None


class NomenclaturaPlaguicidaUpdate(BaseModel):
    agrupador: str
    codigo: str | None = None


class PaginaNomenclaturaPlaguicidas(BaseModel):
    total: int
    pagina: int
    tamano_pagina: int
    filas: list[NomenclaturaPlaguicidaItem]


class AgrupadorNutrienteItem(BaseModel):
    nombre_key: str
    producto_agrupado: str | None
    codigo: str | None
    fecha_mod: datetime | None


class AgrupadorNutrienteUpdate(BaseModel):
    producto_agrupado: str
    codigo: str | None = None


class PaginaAgrupadorNutrientes(BaseModel):
    total: int
    pagina: int
    tamano_pagina: int
    filas: list[AgrupadorNutrienteItem]
