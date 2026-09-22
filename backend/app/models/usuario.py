from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.core.db import Base


class Rol(Base):
    __tablename__ = "Roles"

    RolId = Column(Integer, primary_key=True)
    NombreRol = Column(String(50), nullable=False, unique=True)


class Usuario(Base):
    __tablename__ = "Usuarios"

    UsuarioId = Column(Integer, primary_key=True)
    NombreUsuario = Column(String(100), nullable=False, unique=True)
    NombreCompleto = Column(String(200))
    Email = Column(String(200))
    PasswordHash = Column(String(255), nullable=False)
    RolId = Column(Integer, ForeignKey("Roles.RolId"), nullable=False)
    Activo = Column(Boolean, nullable=False, default=True)
    PuedeExportar = Column(Boolean, nullable=False, default=False)
    FechaCreacion = Column(DateTime, server_default=func.getdate())
    UltimoLogin = Column(DateTime)
    Tema = Column(String(10), nullable=False, default="Claro")
    AccesoImportaciones = Column(Boolean, nullable=False, default=True)
    AccesoFinanciero = Column(Boolean, nullable=False, default=False)
    AccesoIndicadores = Column(Boolean, nullable=False, default=False)
    # Aviso legal y condiciones de uso -- se pide una sola vez por
    # usuario, al primer login (ver LoginPage.tsx / endpoint
    # /auth/aceptar-aviso-legal). FechaAceptacion se llena con la hora
    # del SERVIDOR (func.getdate() del lado del backend), nunca con una
    # fecha que mande el navegador, para que sirva de respaldo confiable
    # ante un reclamo.
    AvisoLegalAceptado = Column(Boolean, nullable=False, default=False)
    AvisoLegalFechaAceptacion = Column(DateTime)
