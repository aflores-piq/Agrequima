/* =====================================================================
   PIQ_IA -- Control de acceso por módulo (Importaciones/Financiero/
   Indicadores)
   =====================================================================
   Mismo criterio que dbo.Usuarios.PuedeExportar: permiso individual por
   usuario (no por rol), consultado fresco en cada request (ver
   require_acceso_importaciones/require_acceso_financiero/
   require_acceso_indicadores en backend/app/core/deps.py) -- si un
   administrador se lo da/quita a alguien, aplica de inmediato sin
   esperar a que esa persona vuelva a loguearse.

   AccesoImportaciones arranca en 1 (no en 0 como los otros dos) para no
   romper el acceso de las cuentas que ya existen hoy -- todas seguían
   viendo Plaguicidas/Nutrientes antes de que este control existiera.

   AccesoIndicadores se agrega ahora aunque ese proyecto todavía no
   tiene pantallas propias -- mismo criterio "genérico desde el inicio"
   que ya se usó en sync_piq_ia.py (SYNC_VISTAS_CONTACC), para no tener
   que volver a tocar el esquema ni el JWT cuando Indicadores arranque.

   Es seguro volver a correr este script las veces que haga falta: cada
   ALTER TABLE está protegido con un IF que solo agrega la columna si
   todavía no existe.
   ===================================================================== */

USE PIQ_IA;
GO

IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'Usuarios' AND COLUMN_NAME = 'AccesoImportaciones'
)
BEGIN
    ALTER TABLE dbo.Usuarios ADD AccesoImportaciones BIT NOT NULL DEFAULT 1;
    PRINT 'Columna AccesoImportaciones agregada a dbo.Usuarios.';
END
ELSE
    PRINT 'dbo.Usuarios.AccesoImportaciones ya existía -- no se tocó.';
GO

IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'Usuarios' AND COLUMN_NAME = 'AccesoFinanciero'
)
BEGIN
    ALTER TABLE dbo.Usuarios ADD AccesoFinanciero BIT NOT NULL DEFAULT 0;
    PRINT 'Columna AccesoFinanciero agregada a dbo.Usuarios.';
END
ELSE
    PRINT 'dbo.Usuarios.AccesoFinanciero ya existía -- no se tocó.';
GO

IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'Usuarios' AND COLUMN_NAME = 'AccesoIndicadores'
)
BEGIN
    ALTER TABLE dbo.Usuarios ADD AccesoIndicadores BIT NOT NULL DEFAULT 0;
    PRINT 'Columna AccesoIndicadores agregada a dbo.Usuarios.';
END
ELSE
    PRINT 'dbo.Usuarios.AccesoIndicadores ya existía -- no se tocó.';
GO

SELECT
    'Usuarios con AccesoImportaciones=1' AS metrica, COUNT(*) AS valor FROM dbo.Usuarios WHERE AccesoImportaciones = 1
UNION ALL
SELECT
    'Usuarios con AccesoFinanciero=1', COUNT(*) FROM dbo.Usuarios WHERE AccesoFinanciero = 1
UNION ALL
SELECT
    'Usuarios con AccesoIndicadores=1', COUNT(*) FROM dbo.Usuarios WHERE AccesoIndicadores = 1;
GO

PRINT '=== Control de acceso por módulo aplicado. ===';
GO
