from sqlalchemy import DECIMAL, Column, DateTime, Integer, String
from sqlalchemy.ext.hybrid import hybrid_property

from app.core.collation import coalesce_homologado
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
    # Nombre homologado de la empresa (dbo.CatalogoEmpresas, ver script 26): se rellena al cargar y al editar el
    # catalogo. NULL = empresa todavia sin homologar. El dato original (importador) NO se modifica nunca.
    EmpresaHomologada = Column(String(400))
    # Nombre comercial homologado (dbo.CatalogoNombresComerciales, ver script 27). NULL = todavia sin homologar.
    # El dato original (producto) NO se modifica nunca.
    NombreComercialHomologado = Column(String(400))

    @hybrid_property
    def producto_efectivo(self):
        """Nombre comercial que ven los tableros: el homologado y, si no hay, el original."""
        return self.NombreComercialHomologado if self.NombreComercialHomologado is not None else self.producto

    @producto_efectivo.expression
    def producto_efectivo(cls):
        return coalesce_homologado(cls.NombreComercialHomologado, cls.producto)

    @hybrid_property
    def importador_efectivo(self):
        """Empresa que ven los tableros: la homologada y, si no hay, la original."""
        return self.EmpresaHomologada if self.EmpresaHomologada is not None else self.importador

    @importador_efectivo.expression
    def importador_efectivo(cls):
        return coalesce_homologado(cls.EmpresaHomologada, cls.importador)
