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


class NutrienteActivo(Base):
    """Espejo de solo lectura de dbo.Nutrientes vía la vista
    dbo.vw_NutrientesActivos (WHERE Excluido = 0) -- ver
    04_migracion_nutrientes_tipo_exclusion.sql /
    07_vista_nutrientes_activos.sql para la definición de la vista.

    USAR SIEMPRE este modelo (nunca `Nutriente`) en cualquier pantalla,
    dashboard, export o cálculo: la vista ya excluye los productos
    marcados Excluido=1 por definición, así que ningún código que lea
    de acá puede "olvidarse" del filtro -- no depende de que cada
    función se acuerde de agregar `.filter(Excluido == False)`.

    `Nutriente` (la tabla real, con TODAS las filas) queda reservado
    exclusivamente para lo que necesita ver también las excluidas:
    el proceso de carga (etl_nutrientes.py / usp_CargarNutrientes,
    que necesita el total real cargado para el filtro de "solo mes
    nuevo") y la sincronización del catálogo
    (sincronizacion_agrupador.py), que escribe Excluido/ProductoAgrupado
    sobre la tabla real -- una vista no es escribible con MERGE/UPDATE
    multi-columna, así que esos dos casos siguen apuntando a Nutriente
    a propósito."""

    __tablename__ = "vw_NutrientesActivos"

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
    Excluido = Column(Boolean, nullable=False)
    fechamod = Column(DateTime)
    userid = Column(Integer)
