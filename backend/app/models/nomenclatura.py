from sqlalchemy import Column, DateTime, String

from app.core.db import Base


class CatalogoNomenclaturaPlaguicidas(Base):
    __tablename__ = "CatalogoNomenclaturaPlaguicidas"

    IngredienteActivo_Key = Column(String(400), primary_key=True)
    Agrupador = Column(String(350))
    Codigo = Column(String(20))
    FechaMod = Column(DateTime)


class CatalogoAgrupadorNutrientes(Base):
    __tablename__ = "CatalogoAgrupadorNutrientes"

    NombreComercial_Key = Column(String(400), primary_key=True)
    ProductoAgrupado = Column(String(150))
    Codigo = Column(String(20))
    FechaMod = Column(DateTime)
