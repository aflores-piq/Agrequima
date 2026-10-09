/* =====================================================================
   PIQ_IA -- Registro de CADA aceptación del aviso legal (script 22)
   =====================================================================
   POR QUÉ: el aviso legal ahora aparece SIEMPRE que un usuario inicia
   sesión (antes solo la primera vez) y hay que dejar constancia de cada
   aceptación: qué usuario y a qué hora (hora de Guatemala). Las columnas
   dbo.Usuarios.AvisoLegalAceptado / AvisoLegalFechaAceptacion (script 11)
   solo guardan UNA vez (la primera aceptación): se quedan como están, y
   esta tabla guarda una fila por CADA aceptación.

   QUÉ HACE:
     Crea dbo.AvisoLegalAceptaciones (si no existe):
       AceptacionId        número consecutivo
       UsuarioId           usuario que aceptó (FK a dbo.Usuarios)
       NombreUsuario       el nombre de usuario en ese momento (por si luego se renombra la cuenta)
       FechaHoraGuatemala  fecha y hora de la aceptación en hora de Guatemala (UTC-6, sin horario de verano);
                           la calcula la aplicación al registrar, no el navegador del usuario
       FechaHoraUtc        la misma fecha y hora en UTC (la pone el servidor de base de datos)
     Más un índice para consultar rápido por usuario y fecha.

   Es seguro correrlo las veces que haga falta: solo crea lo que no existe
   y no borra ni modifica ningún dato.

   Consulta de ejemplo (últimas aceptaciones):
     SELECT TOP 50 * FROM dbo.AvisoLegalAceptaciones ORDER BY AceptacionId DESC;
   ===================================================================== */

USE PIQ_IA;
GO


/* ---------------------------------------------------------------------
   1. TABLA dbo.AvisoLegalAceptaciones (si no existe todavía)
   --------------------------------------------------------------------- */

IF OBJECT_ID('dbo.AvisoLegalAceptaciones', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.AvisoLegalAceptaciones (
        AceptacionId        INT IDENTITY(1,1) NOT NULL,
        UsuarioId           INT NOT NULL,
        NombreUsuario       VARCHAR(100) NOT NULL,
        FechaHoraGuatemala  DATETIME2(0) NOT NULL,
        FechaHoraUtc        DATETIME2(0) NOT NULL
            CONSTRAINT DF_AvisoLegalAceptaciones_FechaHoraUtc DEFAULT (SYSUTCDATETIME()),
        CONSTRAINT PK_AvisoLegalAceptaciones PRIMARY KEY CLUSTERED (AceptacionId),
        CONSTRAINT FK_AvisoLegalAceptaciones_Usuarios FOREIGN KEY (UsuarioId) REFERENCES dbo.Usuarios (UsuarioId)
    );
    PRINT 'Tabla dbo.AvisoLegalAceptaciones creada.';
END
ELSE
    PRINT 'dbo.AvisoLegalAceptaciones ya existía -- no se tocó.';
GO


/* ---------------------------------------------------------------------
   2. ÍNDICE por usuario y fecha (si no existe todavía)
   --------------------------------------------------------------------- */

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_AvisoLegalAceptaciones_Usuario_Fecha'
      AND object_id = OBJECT_ID('dbo.AvisoLegalAceptaciones')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_AvisoLegalAceptaciones_Usuario_Fecha
        ON dbo.AvisoLegalAceptaciones (UsuarioId, FechaHoraGuatemala);
    PRINT 'Índice IX_AvisoLegalAceptaciones_Usuario_Fecha creado.';
END
ELSE
    PRINT 'IX_AvisoLegalAceptaciones_Usuario_Fecha ya existía -- no se tocó.';
GO


/* ---------------------------------------------------------------------
   3. VERIFICACIÓN
   --------------------------------------------------------------------- */

SELECT 'Aceptaciones registradas' AS metrica, COUNT(*) AS valor FROM dbo.AvisoLegalAceptaciones;
GO

PRINT '=== Registro de aceptaciones del aviso legal listo. ===';
GO
