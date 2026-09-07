from sqlalchemy import Boolean, Column, Date, DateTime, Float, Integer, Numeric, String

from app.core.db import Base


class Nutriente(Base):
    __tablename__ = "Nutrientes"

    nutrienteid = Column(Integer, primary_key=True)
    anio = Column(Integer)
    Tipo = Column(String(50))
    No_Licencia = Column(String(50))
    No_Registro = Column(String(50))
    NombreComercial = Column(String(200))
    EmpresaImportadora = Column(String(200))
    FechaEmision = Column(Date)
    UMedida = Column(String(50))
    Cantidad = Column(Float)
    PaisProcedencia = Column(String(100))
    PaisOrigen = Column(String(100))
    AduanadeIngreso = Column(String(100))
    CIF_dolares = Column(Numeric(19, 4))
    CIF_Q = Column(Numeric(19, 4))
    TimbresQ = Column(Numeric(19, 4))
    Exportador = Column(String(150))
    Concentraciones = Column(String(150))
    Componentes = Column(String(500))
    VENTANILLA = Column(String(50))
    ProductoAgrupado = Column(String(150))
    CodigoAgrupador = Column(String(20))
    # Copiado desde CatalogoAgrupadorNutrientes.Excluido al cargar (mismo
    # JOIN que ya llena ProductoAgrupado/CodigoAgrupador, ver
    # usp_CargarNutrientes) y vuelto a sincronizar cada vez que se edita
    # el catálogo (sincronizar_agrupador_nutrientes) -- así una fila
    # excluida deja de mostrarse en dashboards/exports sin depender de
    # un JOIN en tiempo real ni de repetir la carga.
    Excluido = Column(Boolean, nullable=False, default=False)
    fechamod = Column(DateTime)
    userid = Column(Integer)
