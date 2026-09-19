/* =====================================================================
   PIQ_IA -- Migracion: columnas de aceptacion del aviso legal en
   dbo.Usuarios
   =====================================================================
   Correr esto DESPUES de 01_crear_base_piq_ia.sql y 02_seed_roles_y_admin.sql
   (necesita que dbo.Usuarios ya exista).

   Agrega 2 columnas a dbo.Usuarios para registrar la aceptacion del
   aviso legal y condiciones de uso que ahora se muestra una sola vez
   por usuario, al primer login, quedando como respaldo ante cualquier
   reclamo:

     - AvisoLegalAceptado         BIT NOT NULL DEFAULT 0
     - AvisoLegalFechaAceptacion  DATETIME NULL (fecha/hora real del
       SERVIDOR -- GETDATE() -- nunca la del navegador del usuario, para
       que el timestamp sea confiable como respaldo)

   Es seguro volver a correr este script las veces que haga falta: los
   ALTER TABLE verifican que la columna no exista todavia antes de
   agregarla (mismo patron que 04_migracion_nutrientes_tipo_exclusion.sql).
   ===================================================================== */

USE PIQ_IA;
GO


/* ---------------------------------------------------------------------
   1. COLUMNA AvisoLegalAceptado (si no existe todavía)
   --------------------------------------------------------------------- */

IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'Usuarios' AND COLUMN_NAME = 'AvisoLegalAceptado'
)
BEGIN
    ALTER TABLE dbo.Usuarios ADD AvisoLegalAceptado BIT NOT NULL DEFAULT 0;
    PRINT 'Columna AvisoLegalAceptado agregada a dbo.Usuarios.';
END
ELSE
    PRINT 'dbo.Usuarios.AvisoLegalAceptado ya existía -- no se tocó.';
GO


/* ---------------------------------------------------------------------
   2. COLUMNA AvisoLegalFechaAceptacion (si no existe todavía)
   --------------------------------------------------------------------- */

IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'Usuarios' AND COLUMN_NAME = 'AvisoLegalFechaAceptacion'
)
BEGIN
    ALTER TABLE dbo.Usuarios ADD AvisoLegalFechaAceptacion DATETIME NULL;
    PRINT 'Columna AvisoLegalFechaAceptacion agregada a dbo.Usuarios.';
END
ELSE
    PRINT 'dbo.Usuarios.AvisoLegalFechaAceptacion ya existía -- no se tocó.';
GO


/* ---------------------------------------------------------------------
   3. VERIFICACIÓN
   --------------------------------------------------------------------- */

SELECT
    'Usuarios con AvisoLegalAceptado=1'  AS metrica, COUNT(*) AS valor FROM dbo.Usuarios WHERE AvisoLegalAceptado = 1
UNION ALL
SELECT
    'Total de usuarios (referencia de tamaño)', COUNT(*) FROM dbo.Usuarios;
GO

PRINT '=== Migración de aviso legal en Usuarios finalizada. ===';
PRINT 'Recién creadas, ambas columnas deben quedar en AvisoLegalAceptado=0 para todos los usuarios existentes (nadie lo aceptó todavía bajo el nuevo esquema).';
GO
