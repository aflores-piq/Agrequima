from sqlalchemy import DECIMAL, Column, DateTime, Integer, String

from app.core.db import Base


class Importacion(Base):
    __tablename__ = "Importacion"

    importacionplaguicidaid = Column(Integer, primary_key=True)
    anio = Column(Integer)
    recibointerno = Column(String(80))
    serie_sat = Column(String(70))
    numero_recibo_sat = Column(String(80))
    aplicacion = Column(String(150))
    fecha = Column(String(15))
    importador = Column(String(250))
    producto = Column(String(250))
    ingrediente_act = Column(String(350))
    exportador = Column(String(350))
    origen = Column(String(50))
    porcentaje = Column(DECIMAL(18, 2))
    cantidad = Column(DECIMAL(18, 2))
    unidad_medida = Column(String(50))
    cif_USD = Column(DECIMAL(18, 2))
    cif_Q = Column(DECIMAL(18, 2))
    tipo_cambio = Column(String(50))
    institucion = Column(String(150))
    umsp = Column(DECIMAL(18, 2))
    fechamod = Column(DateTime)
    userid = Column(Integer)
    Grupo = Column(String(350))
    CodigoAgrupador = Column(String(20))
