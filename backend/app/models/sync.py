from sqlalchemy import Column, DateTime, Integer, String

from app.core.db import Base


class SyncEstado(Base):
    """Última ejecución EXITOSA de cada proceso de sincronización (script 24). Hoy solo
    'Financiero': lo escribe sync_financiero.py al terminar con todas las vistas OK."""

    __tablename__ = "SyncEstado"

    Proceso = Column(String(50), primary_key=True)
    # Hora de Guatemala (UTC-6), calculada por el sincronizador.
    UltimaEjecucionOk = Column(DateTime, nullable=False)
    Filas = Column(Integer)
