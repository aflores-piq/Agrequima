from sqlalchemy import Boolean, Column, DateTime, String

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
    # Productos que el cliente confirmó que NO corresponden a Nutrientes
    # (ej. plaguicidas que se colaron en el diccionario) -- sus filas en
    # dbo.Nutrientes se siguen cargando (no se pierde el dato crudo) pero
    # se excluyen de dashboards y exports. Ver Excluido en Nutriente
    # (models/nutriente.py) y sincronizar_agrupador_nutrientes(), que
    # propaga este valor hacia las filas ya cargadas.
    Excluido = Column(Boolean, nullable=False, default=False)
