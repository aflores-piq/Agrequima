/* =====================================================================
   PIQ_IA -- Estado de la sincronizacion (script 24)
   =====================================================================
   POR QUE: la pantalla de inicio muestra "Datos actualizados: fecha y hora"
   y esa fecha hay que guardarla en algun lado: sync_financiero.py la deja
   aqui al terminar una corrida EXITOSA (todas las vistas OK). Si la corrida
   falla, NO se toca.

   QUE HACE:
     Crea dbo.SyncEstado (si no existe):
       Proceso            nombre del proceso (hoy solo 'Financiero')  -- clave
       UltimaEjecucionOk  fecha y hora de Guatemala de la ultima corrida exitosa
       Filas              total de filas copiadas en esa corrida (puede ser NULL)
     La tabla queda VACIA: se llena sola con la proxima sincronizacion (hasta
     entonces la pantalla de inicio simplemente no muestra el recuadro).

   Es seguro correrlo las veces que haga falta: solo crea lo que no existe y
   no borra ni modifica ningun dato.

   Consulta de ejemplo:
     SELECT * FROM dbo.SyncEstado;
   ===================================================================== */

USE PIQ_IA;
GO


IF OBJECT_ID('dbo.SyncEstado', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.SyncEstado (
        Proceso            NVARCHAR(50) NOT NULL,
        UltimaEjecucionOk  DATETIME2(0) NOT NULL,
        Filas              INT NULL,
        CONSTRAINT PK_SyncEstado PRIMARY KEY CLUSTERED (Proceso)
    );
    PRINT 'Tabla dbo.SyncEstado creada.';
END
ELSE
    PRINT 'dbo.SyncEstado ya existia -- no se modifico nada.';
GO
