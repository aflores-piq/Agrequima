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
