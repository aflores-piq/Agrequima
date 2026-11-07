/* =====================================================================
   SCRIPT 28 - AVISOS (campanita)
   Base: PIQ_IA   |   Idempotente   |   Una sola transaccion

   QUE HACE
     1. dbo.Avisos (AvisoId, Tipo, Mensaje, Referencia, FechaCreacion, Destino 'Todos' | 'Administrador').
        Indice unico filtrado (Tipo, Referencia): el mismo aviso no se crea dos veces.
     2. dbo.AvisosLeidos (AvisoId, UsuarioId, FechaLectura): cada usuario marca LEIDO por su cuenta.
        Se borra solo si se borra el aviso o el usuario (ON DELETE CASCADE).

   NO TOCA ninguna tabla existente. Al final verifica que filas y CIF de dbo.Importacion y
   dbo.Nutrientes sean los mismos que al empezar; si no, deshace todo.

   SEGURIDAD
     - @SoloVistaPrevia = 1: solo informa, no cambia nada.
     - Si las tablas ya existen, se respaldan como ZZ_bak28_ antes de cualquier cambio (no se pisan).
     - Si ya esta todo creado, no hace nada (idempotente).
   ===================================================================== */

USE PIQ_IA;
GO

-- ---------------------------------------------------------------------
-- LOTE 0: parametros y totales de control
-- ---------------------------------------------------------------------
SET XACT_ABORT ON;
SET NOCOUNT ON;
SET NOEXEC OFF;

DECLARE @SoloVistaPrevia BIT = 0;   -- 1 = solo muestra la vista previa

IF OBJECT_ID('tempdb..#control28') IS NOT NULL DROP TABLE #control28;
CREATE TABLE #control28 (Clave VARCHAR(40) NOT NULL PRIMARY KEY, Numero DECIMAL(19,4) NULL);
INSERT INTO #control28 (Clave, Numero) VALUES
    ('preview',   @SoloVistaPrevia),
    ('imp_filas', (SELECT COUNT(*) FROM dbo.Importacion)),
    ('imp_cif',   (SELECT ISNULL(SUM(CAST(cif_USD AS DECIMAL(19,4))), 0) FROM dbo.Importacion)),
    ('nut_filas', (SELECT COUNT(*) FROM dbo.Nutrientes)),
    ('nut_cif',   (SELECT ISNULL(SUM(CAST(CIF_dolares AS DECIMAL(19,4))), 0) FROM dbo.Nutrientes)),
    ('nut_cifq',  (SELECT ISNULL(SUM(CAST(CIF_Q AS DECIMAL(19,4))), 0) FROM dbo.Nutrientes));
GO

-- ---------------------------------------------------------------------
-- LOTE 1: REPORTE (siempre se ejecuta; solo lee)
-- ---------------------------------------------------------------------
SET NOCOUNT ON;

DECLARE @pendiente BIT = CASE WHEN
       OBJECT_ID('dbo.Avisos', 'U') IS NULL OR OBJECT_ID('dbo.AvisosLeidos', 'U') IS NULL
    OR NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'UX_Avisos_Tipo_Referencia' AND object_id = OBJECT_ID('dbo.Avisos'))
    THEN 1 ELSE 0 END;
INSERT INTO #control28 (Clave, Numero) VALUES ('pendiente', @pendiente);

SELECT CASE WHEN OBJECT_ID('dbo.Avisos', 'U') IS NULL THEN 'por crear' ELSE 'ya existe' END AS tabla_avisos,
       CASE WHEN OBJECT_ID('dbo.AvisosLeidos', 'U') IS NULL THEN 'por crear' ELSE 'ya existe' END AS tabla_avisos_leidos;
PRINT CASE WHEN @pendiente = 1 THEN 'Hay cambios por aplicar (tablas de avisos).' ELSE 'Ya esta todo aplicado: no hay nada que cambiar.' END;
GO

-- ---------------------------------------------------------------------
-- LOTE 2: en vista previa o si ya esta todo aplicado, NO se ejecutan los lotes de cambios
-- ---------------------------------------------------------------------
IF (SELECT Numero FROM #control28 WHERE Clave = 'preview') = 1
   OR (SELECT Numero FROM #control28 WHERE Clave = 'pendiente') = 0
    SET NOEXEC ON;
GO

-- ---------------------------------------------------------------------
-- LOTE 3: RESPALDO AUTOMATICO (solo si las tablas ya existen; nunca pisa uno existente)
-- ---------------------------------------------------------------------
DECLARE @sufijo CHAR(8) = CONVERT(CHAR(8), GETDATE(), 112);
DECLARE @bakA NVARCHAR(200) = N'dbo.ZZ_bak28_Avisos_' + @sufijo;
DECLARE @bakL NVARCHAR(200) = N'dbo.ZZ_bak28_AvisosLeidos_' + @sufijo;
IF OBJECT_ID('dbo.Avisos', 'U') IS NOT NULL AND OBJECT_ID(@bakA) IS NULL
BEGIN EXEC (N'SELECT * INTO ' + @bakA + N' FROM dbo.Avisos'); PRINT 'Respaldo creado: ' + @bakA; END
IF OBJECT_ID('dbo.AvisosLeidos', 'U') IS NOT NULL AND OBJECT_ID(@bakL) IS NULL
BEGIN EXEC (N'SELECT * INTO ' + @bakL + N' FROM dbo.AvisosLeidos'); PRINT 'Respaldo creado: ' + @bakL; END
IF OBJECT_ID('dbo.Avisos', 'U') IS NULL AND OBJECT_ID('dbo.AvisosLeidos', 'U') IS NULL
    PRINT 'Las tablas de avisos no existen todavia: no hay nada que respaldar.';
GO

-- ---------------------------------------------------------------------
-- LOTE 4: comienza la transaccion (abarca hasta el COMMIT del lote 6)
-- ---------------------------------------------------------------------
BEGIN TRANSACTION;
GO

-- ---------------------------------------------------------------------
-- LOTE 5: tablas e indice
-- ---------------------------------------------------------------------
SET QUOTED_IDENTIFIER ON;   -- necesario para el indice unico filtrado
IF @@TRANCOUNT = 0 SET NOEXEC ON;
GO
IF OBJECT_ID('dbo.Avisos', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.Avisos (
        AvisoId       INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_Avisos PRIMARY KEY,
        Tipo          VARCHAR(60)   NOT NULL,
        Mensaje       NVARCHAR(500) NOT NULL,
        Referencia    NVARCHAR(200) NULL,
        FechaCreacion DATETIME      NOT NULL CONSTRAINT DF_Avisos_FechaCreacion DEFAULT GETDATE(),
        Destino       VARCHAR(20)   NOT NULL CONSTRAINT DF_Avisos_Destino DEFAULT 'Todos',
        CONSTRAINT CK_Avisos_Destino CHECK (Destino IN ('Todos', 'Administrador'))
    );
    PRINT 'Tabla dbo.Avisos creada.';
END
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'UX_Avisos_Tipo_Referencia' AND object_id = OBJECT_ID('dbo.Avisos'))
BEGIN
    CREATE UNIQUE INDEX UX_Avisos_Tipo_Referencia ON dbo.Avisos (Tipo, Referencia) WHERE Referencia IS NOT NULL;
    PRINT 'Indice unico UX_Avisos_Tipo_Referencia creado.';
END
IF OBJECT_ID('dbo.AvisosLeidos', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.AvisosLeidos (
        AvisoId      INT      NOT NULL,
        UsuarioId    INT      NOT NULL,
        FechaLectura DATETIME NOT NULL CONSTRAINT DF_AvisosLeidos_FechaLectura DEFAULT GETDATE(),
        CONSTRAINT PK_AvisosLeidos PRIMARY KEY (AvisoId, UsuarioId),
        CONSTRAINT FK_AvisosLeidos_Avisos   FOREIGN KEY (AvisoId)   REFERENCES dbo.Avisos (AvisoId)      ON DELETE CASCADE,
        CONSTRAINT FK_AvisosLeidos_Usuarios FOREIGN KEY (UsuarioId) REFERENCES dbo.Usuarios (UsuarioId) ON DELETE CASCADE
    );
    PRINT 'Tabla dbo.AvisosLeidos creada.';
END
GO

-- ---------------------------------------------------------------------
-- LOTE 6: controles y COMMIT
-- ---------------------------------------------------------------------
IF @@TRANCOUNT = 0 SET NOEXEC ON;
GO
DECLARE @impFilas INT = (SELECT COUNT(*) FROM dbo.Importacion);
DECLARE @impCif DECIMAL(19,4) = (SELECT ISNULL(SUM(CAST(cif_USD AS DECIMAL(19,4))), 0) FROM dbo.Importacion);
DECLARE @nutFilas INT = (SELECT COUNT(*) FROM dbo.Nutrientes);
DECLARE @nutCif DECIMAL(19,4) = (SELECT ISNULL(SUM(CAST(CIF_dolares AS DECIMAL(19,4))), 0) FROM dbo.Nutrientes);
DECLARE @nutCifQ DECIMAL(19,4) = (SELECT ISNULL(SUM(CAST(CIF_Q AS DECIMAL(19,4))), 0) FROM dbo.Nutrientes);
IF @impFilas <> (SELECT Numero FROM #control28 WHERE Clave = 'imp_filas')
   OR @impCif <> (SELECT Numero FROM #control28 WHERE Clave = 'imp_cif')
   OR @nutFilas <> (SELECT Numero FROM #control28 WHERE Clave = 'nut_filas')
   OR @nutCif <> (SELECT Numero FROM #control28 WHERE Clave = 'nut_cif')
   OR @nutCifQ <> (SELECT Numero FROM #control28 WHERE Clave = 'nut_cifq')
    THROW 50030, 'Control fallido: cambio el numero de filas o el CIF de dbo.Importacion o dbo.Nutrientes. Se deshace todo.', 1;

COMMIT TRANSACTION;

PRINT 'dbo.Importacion: ' + CAST(@impFilas AS VARCHAR(20)) + ' filas, CIF USD ' + FORMAT(@impCif, 'N2', 'en-US') + ' (igual que antes).';
PRINT 'dbo.Nutrientes: ' + CAST(@nutFilas AS VARCHAR(20)) + ' filas, CIF USD ' + FORMAT(@nutCif, 'N2', 'en-US') + ' (igual que antes).';
GO

-- ---------------------------------------------------------------------
-- LOTE 7: resultado final
-- ---------------------------------------------------------------------
SET NOEXEC OFF;
SET NOCOUNT ON;
IF (SELECT Numero FROM #control28 WHERE Clave = 'preview') = 1
    PRINT '@SoloVistaPrevia = 1: no se cambio nada.';
ELSE IF (SELECT Numero FROM #control28 WHERE Clave = 'pendiente') = 0
    PRINT 'No habia nada que cambiar (ya estaba aplicado). No se modifico nada.';
ELSE IF @@TRANCOUNT > 0
BEGIN
    ROLLBACK TRANSACTION;
    PRINT 'ATENCION: la transaccion no se cerro; se deshizo todo.';
END
ELSE
    SELECT (SELECT COUNT(*) FROM dbo.Avisos) AS avisos, (SELECT COUNT(*) FROM dbo.AvisosLeidos) AS avisos_leidos;
GO
