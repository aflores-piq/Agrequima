"""Registro de cargas en dbo.AuditoriaCargas, compartido por los procesos
ETL de plaguicidas y nutrientes."""

from sqlalchemy import text

from app.core.db import engine


def registrar_auditoria(
    tipo_carga: str,
    nombre_archivo: str,
    usuario_id: int,
    filas_procesadas: int | None,
    filas_con_excepcion: int | None,
    estado: str,
    mensaje_error: str | None,
) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO dbo.AuditoriaCargas
                    (TipoCarga, NombreArchivo, UsuarioId, FilasProcesadas,
                     FilasConExcepcion, Estado, MensajeError)
                VALUES
                    (:tipo, :archivo, :usuario_id, :filas_procesadas,
                     :filas_con_excepcion, :estado, :mensaje_error)
                """
            ),
            {
                "tipo": tipo_carga,
                "archivo": nombre_archivo,
                "usuario_id": usuario_id,
                "filas_procesadas": filas_procesadas,
                "filas_con_excepcion": filas_con_excepcion,
                "estado": estado,
                "mensaje_error": mensaje_error[:4000] if mensaje_error else None,
            },
        )
