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

   AccesoFinanciero arranca en 0 para todos, EXCEPTO las cuentas con rol
   "Administrador" -- quedan con AccesoFinanciero=1 (además del rol, que
   ya les da acceso a /admin) para que, apenas corrido este script, al
   menos un usuario pueda entrar a verificar el módulo recién publicado
   sin depender de que alguien más active el checkbox a mano primero
   desde la pantalla de Usuarios. El resto de las cuentas (rol "Usuario"
   o "Administrador de Usuarios") queda en 0 -- se activa por cuenta,
   como siempre, desde esa misma pantalla.

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

-- Excepción explícita: las cuentas con rol "Administrador" quedan con
-- AccesoFinanciero=1 (ver comentario del encabezado). UPDATE
-- incondicional -- es seguro volver a correrlo, siempre deja el mismo
-- resultado sin importar el valor que tuviera antes.
UPDATE u
SET u.AccesoFinanciero = 1
FROM dbo.Usuarios u
INNER JOIN dbo.Roles r ON r.RolId = u.RolId
WHERE r.NombreRol = 'Administrador';
PRINT 'AccesoFinanciero=1 aplicado a las cuentas con rol Administrador.';
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
