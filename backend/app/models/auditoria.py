from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from app.core.db import Base


class AuditoriaCarga(Base):
    __tablename__ = "AuditoriaCargas"

    CargaId = Column(Integer, primary_key=True)
    TipoCarga = Column(String(20), nullable=False)
    NombreArchivo = Column(String(300))
    UsuarioId = Column(Integer, ForeignKey("Usuarios.UsuarioId"))
    FechaCarga = Column(DateTime)
    FilasProcesadas = Column(Integer)
    FilasConExcepcion = Column(Integer)
    Estado = Column(String(20))
    MensajeError = Column(String)
