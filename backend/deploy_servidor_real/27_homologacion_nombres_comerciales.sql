/* =====================================================================
   SCRIPT 27 - HOMOLOGACION DE NOMBRES COMERCIALES (Plaguicidas y Nutrientes)
   Base: PIQ_IA   |   Idempotente   |   Una sola transaccion

   QUE HACE
     1. dbo.fn_ClaveNombreComercial: clave normalizada de un nombre comercial
        (mayusculas, sin tildes, puntos y comas -> espacio, espacios colapsados).
        NO une por orden de palabras ni por errores de tipeo.
     2. PLAGUICIDAS: dbo.CatalogoNombresComerciales (NombreKey -> NombreHomologado,
        Confirmada, FechaMod, UsuarioMod), dbo.log_ExcepcionesNombresComerciales y
        la columna dbo.Importacion.NombreComercialHomologado (se sincroniza desde el
        catalogo; dbo.Importacion.producto NO se modifica nunca).
     3. NUTRIENTES: se reutiliza dbo.CatalogoAgrupadorNutrientes (ProductoAgrupado) como
        estandar; solo se le agregan Confirmada (lo ya existente queda Confirmada = 1) y
        UsuarioMod. No se toca ni la regla de duplicados ni la de la letra F.
     4. SEMILLA (Plaguicidas): todos los nombres comerciales distintos de dbo.Importacion.
        Las variantes que normalizan igual se unen bajo el nombre de mayor CIF USD.
        Todo lo sembrado queda Confirmada = 0 (el cliente lo revisa en la pantalla).
        Si una clave ya esta en el catalogo NO se toca.

   SEGURIDAD
     - @SoloVistaPrevia = 1: solo informa, no cambia nada.
     - Respaldos ZZ_bak27_ (no se pisan). Si cambia el numero de filas o el CIF de
       dbo.Importacion o dbo.Nutrientes, o algun dato original (producto), se
       deshace todo (THROW + XACT_ABORT).
     - Los procedimientos de carga NO se modifican: las cargas de Python rellenan
       NombreComercialHomologado y registran los nombres nuevos (services/nombres_comerciales.py).
   ===================================================================== */

USE PIQ_IA;
GO

-- ---------------------------------------------------------------------
-- LOTE 0: parametros, plantilla de la clave y totales de control
-- ---------------------------------------------------------------------
SET XACT_ABORT ON;
SET NOCOUNT ON;
SET NOEXEC OFF;

DECLARE @SoloVistaPrevia BIT = 0;   -- 1 = solo muestra la vista previa

IF OBJECT_ID('tempdb..#control27') IS NOT NULL DROP TABLE #control27;
CREATE TABLE #control27 (Clave VARCHAR(40) NOT NULL PRIMARY KEY, Texto NVARCHAR(MAX) NULL, Numero DECIMAL(19,4) NULL);
INSERT INTO #control27 (Clave, Numero) VALUES ('preview', @SoloVistaPrevia);

-- Plantilla de la clave ({X} = la columna o variable de texto)
DECLARE @e NVARCHAR(MAX) = N'UPPER(LTRIM(RTRIM(CAST({X} AS NVARCHAR(400)))))';
DECLARE @mapa TABLE (Id INT IDENTITY(1,1) PRIMARY KEY, Desde INT NOT NULL, Hasta NCHAR(1) NOT NULL);
INSERT INTO @mapa (Desde, Hasta) VALUES   -- tildes y dieresis -> letra simple (codigos Unicode, en mayuscula)
    (193, N'A'), (192, N'A'), (194, N'A'), (196, N'A'), (195, N'A'),
    (201, N'E'), (200, N'E'), (202, N'E'), (203, N'E'),
    (205, N'I'), (204, N'I'), (206, N'I'), (207, N'I'),
    (211, N'O'), (210, N'O'), (212, N'O'), (214, N'O'), (213, N'O'),
    (218, N'U'), (217, N'U'), (219, N'U'), (220, N'U'),
    (209, N'N'), (199, N'C');
DECLARE @i INT = 1, @n INT = (SELECT COUNT(*) FROM @mapa);
WHILE @i <= @n
BEGIN
    SELECT @e = N'REPLACE(' + @e + N' COLLATE Latin1_General_BIN2, NCHAR(' + CAST(Desde AS NVARCHAR(10)) + N'), N''' + Hasta + N''')'
    FROM @mapa WHERE Id = @i;
    SET @i += 1;
END
-- puntos y comas -> espacio, y colapsar espacios multiples
SET @e = N'REPLACE(REPLACE(' + @e + N', N''.'', N'' ''), N'','', N'' '')';
SET @i = 1;
WHILE @i <= 5
BEGIN
    SET @e = N'REPLACE(' + @e + N', N''  '', N'' '')';
    SET @i += 1;
END
SET @e = N'(NULLIF(LTRIM(RTRIM(' + @e + N')), N'''') COLLATE DATABASE_DEFAULT)';
INSERT INTO #control27 (Clave, Texto) VALUES ('plantilla', @e);

-- Totales de control antes de tocar nada
INSERT INTO #control27 (Clave, Numero) VALUES
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

CREATE TABLE #pn27 (
    Original NVARCHAR(400) COLLATE Latin1_General_BIN2 NOT NULL,
    Clave    NVARCHAR(400) COLLATE DATABASE_DEFAULT NULL,
    Filas    INT           NOT NULL,
    Cif      DECIMAL(19,4) NOT NULL);

DECLARE @plantilla NVARCHAR(MAX) = (SELECT Texto FROM #control27 WHERE Clave = 'plantilla');
DECLARE @sqlPn NVARCHAR(MAX) = N'
INSERT INTO #pn27 (Original, Clave, Filas, Cif)
SELECT g.Original, ' + REPLACE(@plantilla, N'{X}', N'g.Original') + N', g.Filas, g.Cif
FROM (SELECT CAST(producto AS NVARCHAR(400)) COLLATE Latin1_General_BIN2 AS Original, COUNT(*) AS Filas,
             ISNULL(SUM(CAST(cif_USD AS DECIMAL(19,4))), 0) AS Cif
      FROM dbo.Importacion WHERE producto IS NOT NULL AND LTRIM(RTRIM(producto)) <> ''''
      GROUP BY CAST(producto AS NVARCHAR(400)) COLLATE Latin1_General_BIN2) g';
EXEC sp_executesql @sqlPn;

-- PLAGUICIDAS: nombres comerciales distintos hoy y despues de normalizar
SELECT 'Plaguicidas (dbo.Importacion.producto)' AS tabla, COUNT(DISTINCT Original) AS distintos_hoy,
       COUNT(DISTINCT Clave) AS distintos_normalizados, COUNT(DISTINCT Original) - COUNT(DISTINCT Clave) AS se_unen
FROM #pn27;

-- TODOS los grupos que se unirian (varias formas de escribir el mismo nombre)
;WITH r AS (
    SELECT Clave, Original, Cif, Filas, ROW_NUMBER() OVER (PARTITION BY Clave ORDER BY Cif DESC, Original) AS rn,
           COUNT(*) OVER (PARTITION BY Clave) AS nvar
    FROM #pn27
)
SELECT r.Clave AS clave,
       MAX(CASE WHEN r.rn = 1 THEN r.Original END) AS nombre_homologado_elegido,
       STRING_AGG(r.Original, '  ||  ') WITHIN GROUP (ORDER BY r.Cif DESC, r.Original) AS variantes,
       MAX(r.nvar) AS variantes_n, SUM(r.Filas) AS filas, CAST(SUM(r.Cif) AS DECIMAL(19,2)) AS cif_usd
FROM r
GROUP BY r.Clave
HAVING MAX(r.nvar) > 1
ORDER BY SUM(r.Cif) DESC;

-- NUTRIENTES (solo lectura): catalogo estandar existente y nombres comerciales de la vista activa
SELECT (SELECT COUNT(*) FROM dbo.CatalogoAgrupadorNutrientes) AS catalogo_entradas,
       (SELECT COUNT(DISTINCT ProductoAgrupado) FROM dbo.CatalogoAgrupadorNutrientes) AS productos_agrupados_distintos,
       (SELECT COUNT(DISTINCT NombreComercial) FROM dbo.vw_NutrientesActivos WHERE NombreComercial IS NOT NULL) AS nombres_activos_distintos,
       (SELECT COUNT(DISTINCT n.NombreComercial) FROM dbo.vw_NutrientesActivos n WHERE n.ProductoAgrupado IS NOT NULL) AS nombres_activos_con_entrada,
       (SELECT COUNT(DISTINCT n.NombreComercial) FROM dbo.vw_NutrientesActivos n WHERE n.NombreComercial IS NOT NULL AND n.ProductoAgrupado IS NULL) AS nombres_activos_sin_entrada;

-- Hay algo que cambiar?
DECLARE @pendiente BIT = CASE WHEN
       OBJECT_ID('dbo.CatalogoNombresComerciales', 'U') IS NULL OR OBJECT_ID('dbo.log_ExcepcionesNombresComerciales', 'U') IS NULL
    OR OBJECT_ID('dbo.fn_ClaveNombreComercial') IS NULL
    OR COL_LENGTH('dbo.Importacion', 'NombreComercialHomologado') IS NULL
    OR COL_LENGTH('dbo.CatalogoAgrupadorNutrientes', 'Confirmada') IS NULL OR COL_LENGTH('dbo.CatalogoAgrupadorNutrientes', 'UsuarioMod') IS NULL
    THEN 1 ELSE 0 END;
IF @pendiente = 0
BEGIN
    DECLARE @sqlPend NVARCHAR(MAX) = N'
    SELECT @p = CASE WHEN
         EXISTS (SELECT 1 FROM #pn27 e WHERE NOT EXISTS (SELECT 1 FROM dbo.CatalogoNombresComerciales c WHERE c.NombreKey COLLATE DATABASE_DEFAULT = e.Clave COLLATE DATABASE_DEFAULT))
      OR EXISTS (SELECT 1 FROM dbo.Importacion i JOIN dbo.CatalogoNombresComerciales c ON c.NombreKey COLLATE DATABASE_DEFAULT = dbo.fn_ClaveNombreComercial(i.producto) COLLATE DATABASE_DEFAULT
                 WHERE ISNULL(i.NombreComercialHomologado, N'''') COLLATE Latin1_General_BIN2 <> c.NombreHomologado COLLATE Latin1_General_BIN2)
      THEN 1 ELSE 0 END';
    EXEC sp_executesql @sqlPend, N'@p BIT OUTPUT', @p = @pendiente OUTPUT;
END
INSERT INTO #control27 (Clave, Numero) VALUES ('pendiente', @pendiente);
PRINT CASE WHEN @pendiente = 1 THEN 'Hay cambios por aplicar (estructura, semilla o sincronizacion).' ELSE 'Ya esta todo aplicado: no hay nada que cambiar.' END;
GO

-- ---------------------------------------------------------------------
-- LOTE 2: en vista previa o si ya esta todo aplicado, NO se ejecutan los lotes de cambios
-- ---------------------------------------------------------------------
IF (SELECT Numero FROM #control27 WHERE Clave = 'preview') = 1
   OR (SELECT Numero FROM #control27 WHERE Clave = 'pendiente') = 0
    SET NOEXEC ON;
GO

-- ---------------------------------------------------------------------
-- LOTE 3: RESPALDO AUTOMATICO (nunca pisa uno existente)
-- ---------------------------------------------------------------------
DECLARE @sufijo CHAR(8) = CONVERT(CHAR(8), GETDATE(), 112);
DECLARE @bakImp NVARCHAR(200) = N'dbo.ZZ_bak27_Importacion_' + @sufijo;
DECLARE @bakCat NVARCHAR(200) = N'dbo.ZZ_bak27_CatalogoAgrupadorNutrientes_' + @sufijo;
IF OBJECT_ID(@bakImp) IS NULL BEGIN EXEC (N'SELECT * INTO ' + @bakImp + N' FROM dbo.Importacion'); PRINT 'Respaldo creado: ' + @bakImp; END
ELSE PRINT 'Respaldo ya existente (no se pisa): ' + @bakImp;
IF OBJECT_ID(@bakCat) IS NULL BEGIN EXEC (N'SELECT * INTO ' + @bakCat + N' FROM dbo.CatalogoAgrupadorNutrientes'); PRINT 'Respaldo creado: ' + @bakCat; END
ELSE PRINT 'Respaldo ya existente (no se pisa): ' + @bakCat;
GO

-- ---------------------------------------------------------------------
-- LOTE 4: comienza la transaccion (abarca hasta el COMMIT del lote 6)
-- ---------------------------------------------------------------------
BEGIN TRANSACTION;
GO

-- ---------------------------------------------------------------------
-- LOTE 5: funcion de la clave, tablas nuevas y columnas
-- ---------------------------------------------------------------------
IF @@TRANCOUNT = 0 SET NOEXEC ON;
GO
DECLARE @plantilla NVARCHAR(MAX) = (SELECT Texto FROM #control27 WHERE Clave = 'plantilla');
DECLARE @ddl NVARCHAR(MAX) = N'CREATE OR ALTER FUNCTION dbo.fn_ClaveNombreComercial (@t NVARCHAR(400)) RETURNS NVARCHAR(400) AS BEGIN RETURN '
                           + REPLACE(@plantilla, N'{X}', N'@t') + N'; END';
EXEC (@ddl);
PRINT 'Funcion dbo.fn_ClaveNombreComercial creada/actualizada.';

IF OBJECT_ID('dbo.CatalogoNombresComerciales', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.CatalogoNombresComerciales (
        NombreKey        NVARCHAR(400) NOT NULL PRIMARY KEY,
        NombreHomologado NVARCHAR(400) NOT NULL,
        Confirmada       BIT           NOT NULL CONSTRAINT DF_CatalogoNombresComerciales_Confirmada DEFAULT 0,
        FechaMod         DATETIME      NOT NULL CONSTRAINT DF_CatalogoNombresComerciales_FechaMod DEFAULT GETDATE(),
        UsuarioMod       INT           NULL
    );
    PRINT 'Tabla dbo.CatalogoNombresComerciales creada.';
END
IF OBJECT_ID('dbo.log_ExcepcionesNombresComerciales', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.log_ExcepcionesNombresComerciales (
        LogId        INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        FechaCorrida DATETIME      NOT NULL CONSTRAINT DF_log_ExcepcionesNombresComerciales_Fecha DEFAULT SYSDATETIME(),
        Origen       VARCHAR(20)   NOT NULL,
        Nombre       NVARCHAR(400) NULL,
        NombreKey    NVARCHAR(400) NULL,
        Filas        INT           NULL,
        CifUsd       DECIMAL(19,2) NULL
    );
    PRINT 'Tabla dbo.log_ExcepcionesNombresComerciales creada.';
END
IF COL_LENGTH('dbo.Importacion', 'NombreComercialHomologado') IS NULL
BEGIN
    ALTER TABLE dbo.Importacion ADD NombreComercialHomologado NVARCHAR(400) NULL;
    PRINT 'Columna dbo.Importacion.NombreComercialHomologado agregada.';
END
IF COL_LENGTH('dbo.CatalogoAgrupadorNutrientes', 'Confirmada') IS NULL
BEGIN
    -- Lo que ya estaba en el catalogo (agrupador del cliente) queda Confirmada = 1
    ALTER TABLE dbo.CatalogoAgrupadorNutrientes ADD Confirmada BIT NOT NULL CONSTRAINT DF_CatalogoAgrupadorNutrientes_Confirmada DEFAULT 1;
    PRINT 'Columna dbo.CatalogoAgrupadorNutrientes.Confirmada agregada (existentes = 1).';
END
IF COL_LENGTH('dbo.CatalogoAgrupadorNutrientes', 'UsuarioMod') IS NULL
BEGIN
    ALTER TABLE dbo.CatalogoAgrupadorNutrientes ADD UsuarioMod INT NULL;
    PRINT 'Columna dbo.CatalogoAgrupadorNutrientes.UsuarioMod agregada.';
END
GO

-- ---------------------------------------------------------------------
-- LOTE 6: semilla, sincronizacion, controles y COMMIT
-- ---------------------------------------------------------------------
IF @@TRANCOUNT = 0 SET NOEXEC ON;
GO
-- Semilla: una fila por clave, con el nombre de la variante de mayor CIF USD
;WITH r AS (
    SELECT Clave, Original, ROW_NUMBER() OVER (PARTITION BY Clave ORDER BY Cif DESC, Original) AS rn FROM #pn27 WHERE Clave IS NOT NULL
)
INSERT INTO dbo.CatalogoNombresComerciales (NombreKey, NombreHomologado, Confirmada, FechaMod, UsuarioMod)
SELECT r.Clave, r.Original, 0, GETDATE(), NULL
FROM r
WHERE r.rn = 1
  AND NOT EXISTS (SELECT 1 FROM dbo.CatalogoNombresComerciales c WHERE c.NombreKey COLLATE DATABASE_DEFAULT = r.Clave COLLATE DATABASE_DEFAULT);
DECLARE @sembradas INT = @@ROWCOUNT;

-- Sincronizacion: NombreComercialHomologado de cada fila = el del catalogo para su clave
UPDATE i
SET i.NombreComercialHomologado = c.NombreHomologado
FROM dbo.Importacion i
JOIN dbo.CatalogoNombresComerciales c ON c.NombreKey COLLATE DATABASE_DEFAULT = dbo.fn_ClaveNombreComercial(i.producto) COLLATE DATABASE_DEFAULT
WHERE ISNULL(i.NombreComercialHomologado, N'') COLLATE Latin1_General_BIN2 <> c.NombreHomologado COLLATE Latin1_General_BIN2;
DECLARE @syncImp INT = @@ROWCOUNT;

-- Controles: ni una fila ni un centavo de CIF; los datos originales no cambian
DECLARE @impFilas INT = (SELECT COUNT(*) FROM dbo.Importacion);
DECLARE @impCif DECIMAL(19,4) = (SELECT ISNULL(SUM(CAST(cif_USD AS DECIMAL(19,4))), 0) FROM dbo.Importacion);
DECLARE @nutFilas INT = (SELECT COUNT(*) FROM dbo.Nutrientes);
DECLARE @nutCif DECIMAL(19,4) = (SELECT ISNULL(SUM(CAST(CIF_dolares AS DECIMAL(19,4))), 0) FROM dbo.Nutrientes);
DECLARE @nutCifQ DECIMAL(19,4) = (SELECT ISNULL(SUM(CAST(CIF_Q AS DECIMAL(19,4))), 0) FROM dbo.Nutrientes);
IF @impFilas <> (SELECT Numero FROM #control27 WHERE Clave = 'imp_filas')
   OR @impCif <> (SELECT Numero FROM #control27 WHERE Clave = 'imp_cif')
   OR @nutFilas <> (SELECT Numero FROM #control27 WHERE Clave = 'nut_filas')
   OR @nutCif <> (SELECT Numero FROM #control27 WHERE Clave = 'nut_cif')
   OR @nutCifQ <> (SELECT Numero FROM #control27 WHERE Clave = 'nut_cifq')
    THROW 50028, 'Control fallido: cambio el numero de filas o el CIF de dbo.Importacion o dbo.Nutrientes. Se deshace todo.', 1;

DECLARE @sufijo CHAR(8) = CONVERT(CHAR(8), GETDATE(), 112);
DECLARE @sqlOrig NVARCHAR(MAX) = N'
SELECT @a = (SELECT COUNT(*) FROM dbo.Importacion i JOIN dbo.ZZ_bak27_Importacion_' + @sufijo + N' b ON b.importacionplaguicidaid = i.importacionplaguicidaid
             WHERE ISNULL(i.producto, '''') COLLATE Latin1_General_BIN2 <> ISNULL(b.producto, '''') COLLATE Latin1_General_BIN2),
       @b = (SELECT COUNT(*) FROM dbo.CatalogoAgrupadorNutrientes c JOIN dbo.ZZ_bak27_CatalogoAgrupadorNutrientes_' + @sufijo + N' b ON b.NombreComercial_Key = c.NombreComercial_Key
             WHERE ISNULL(c.ProductoAgrupado, '''') COLLATE Latin1_General_BIN2 <> ISNULL(b.ProductoAgrupado, '''') COLLATE Latin1_General_BIN2
                OR ISNULL(c.Codigo, '''') <> ISNULL(b.Codigo, '''') OR c.Excluido <> b.Excluido)';
DECLARE @cambioImp INT, @cambioCat INT;
EXEC sp_executesql @sqlOrig, N'@a INT OUTPUT, @b INT OUTPUT', @a = @cambioImp OUTPUT, @b = @cambioCat OUTPUT;
IF @cambioImp <> 0 OR @cambioCat <> 0
    THROW 50029, 'Control fallido: cambiaron datos originales (producto) o el catalogo de nutrientes. Se deshace todo.', 1;

COMMIT TRANSACTION;

PRINT 'Claves sembradas en dbo.CatalogoNombresComerciales: ' + CAST(@sembradas AS VARCHAR(10));
PRINT 'Filas de dbo.Importacion con NombreComercialHomologado asignado: ' + CAST(@syncImp AS VARCHAR(10));
PRINT 'dbo.Importacion: ' + CAST(@impFilas AS VARCHAR(20)) + ' filas, CIF USD ' + FORMAT(@impCif, 'N2', 'en-US') + ' (igual que antes).';
PRINT 'dbo.Nutrientes: ' + CAST(@nutFilas AS VARCHAR(20)) + ' filas, CIF USD ' + FORMAT(@nutCif, 'N2', 'en-US') + ' (igual que antes).';
GO

-- ---------------------------------------------------------------------
-- LOTE 7: resultado final
-- ---------------------------------------------------------------------
SET NOEXEC OFF;
SET NOCOUNT ON;
IF (SELECT Numero FROM #control27 WHERE Clave = 'preview') = 1
    PRINT '@SoloVistaPrevia = 1: no se cambio nada.';
ELSE IF (SELECT Numero FROM #control27 WHERE Clave = 'pendiente') = 0
    PRINT 'No habia nada que cambiar (ya estaba aplicado). No se modifico nada.';
ELSE IF @@TRANCOUNT > 0
BEGIN
    ROLLBACK TRANSACTION;
    PRINT 'ATENCION: la transaccion no se cerro; se deshizo todo.';
END
ELSE IF OBJECT_ID('dbo.CatalogoNombresComerciales', 'U') IS NOT NULL
BEGIN
    EXEC (N'
    SELECT COUNT(DISTINCT CAST(producto AS NVARCHAR(400)) COLLATE Latin1_General_BIN2) AS nombres_distintos_original,
           COUNT(DISTINCT COALESCE(NombreComercialHomologado, CAST(producto AS NVARCHAR(400))) COLLATE Latin1_General_BIN2) AS nombres_distintos_homologados
    FROM dbo.Importacion WHERE producto IS NOT NULL');
    SELECT COUNT(*) AS claves_en_catalogo, SUM(CAST(Confirmada AS INT)) AS confirmadas FROM dbo.CatalogoNombresComerciales;
END
GO
