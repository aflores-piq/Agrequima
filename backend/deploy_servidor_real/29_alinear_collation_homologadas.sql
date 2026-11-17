/* =====================================================================
   SCRIPT 29 - ALINEAR LA COLLATION DE LAS COLUMNAS HOMOLOGADAS (arregla el error 446/468 de los dashboards)
   Base: PIQ_IA   |   Idempotente   |   Una sola transaccion

   POR QUE
     En el servidor real las columnas ORIGINALES (Importacion.importador, Importacion.producto, Nutrientes.NombreComercial,
     Nutrientes.EmpresaImportadora, ...) estan en Modern_Spanish_CI_AS, pero las columnas que agregaron los scripts 26 y 27
     (Importacion.EmpresaHomologada, Importacion.NombreComercialHomologado, Nutrientes.EmpresaHomologada) quedaron en la
     collation por defecto de la base PIQ_IA (SQL_Latin1_General_CP1_CI_AS). COALESCE(homologada, original) entre las dos da:
       "Cannot resolve collation conflict between Modern_Spanish_CI_AS and SQL_Latin1_General_CP1_CI_AS in CASE operator ... (446)"
     y los dashboards de Plaguicidas y Nutrientes responden 500. En la base de desarrollo todo estaba en la misma collation y no se vio.

   QUE HACE
     1. DETECTA la collation REAL de cada columna original y alinea con ella la columna homologada correspondiente:
          dbo.Importacion.EmpresaHomologada          -> collation de dbo.Importacion.importador
          dbo.Importacion.NombreComercialHomologado  -> collation de dbo.Importacion.producto
          dbo.Nutrientes.EmpresaHomologada           -> collation de dbo.Nutrientes.EmpresaImportadora
        (ALTER COLUMN ... COLLATE: los datos NO cambian, solo la forma de comparar/agrupar/ordenar; queda igual que antes de homologar.)
        Si una columna ya coincide, no la toca. Si todo coincide (p. ej. la base de desarrollo), NO HACE NADA.
     2. Maneja las dependencias: indices y estadisticas creadas a mano sobre esas columnas se quitan y se vuelven a crear tal cual;
        las vistas que leen las tablas (dbo.vw_NutrientesActivos) se refrescan con sp_refreshview. Si la columna tuviera una
        restriccion, clave foranea, valor por defecto, columna calculada o una vista con SCHEMABINDING, el script se DETIENE y
        deshace todo (no esta previsto: hoy no hay ninguna).
     3. Procedimientos de carga: dbo.usp_ActualizarNomenclatura y dbo.usp_ActualizarAgrupadorNutrientes comparaban (<>) columnas
        del catalogo (Modern_Spanish_CI_AS) contra las tablas dbo.stg_* que la carga recrea con la collation por defecto de la
        base. Si la collation por defecto de la base NO es la de las columnas originales (caso del servidor real) se vuelven a crear
        (CREATE OR ALTER) con COLLATE explicito en esas comparaciones. En una base donde coinciden, no se tocan.

   CATALOGOS (dbo.CatalogoEmpresas, dbo.CatalogoNombresComerciales): NO se alinean. Revisado: sus columnas se comparan solo con
   Latin1_General_BIN2 en ambos lados (sincronizacion), con COLLATE DATABASE_DEFAULT en ambos lados (claves) o contra parametros;
   se asignan a las columnas de las tablas (una asignacion no tiene conflicto de collation). Son PRIMARY KEY (EmpresaKey, NombreKey)
   y alinearlas no aporta nada. La aplicacion (app/core/collation.py) y la prueba de humo usan COLLATE Modern_Spanish_CI_AS explicito
   en toda mezcla de columna homologada con columna original.

   SEGURIDAD
     - @SoloVistaPrevia = 1: solo muestra las collations antes y despues y las dependencias; no cambia nada.
     - Respaldos ZZ_bak29_ (no se pisan): dbo.ZZ_bak29_Importacion_AAAAMMDD, dbo.ZZ_bak29_Nutrientes_AAAAMMDD y
       dbo.ZZ_bak29_Definiciones_AAAAMMDD (texto de la vista y de los dos procedimientos antes del cambio).
     - Si cambia el numero de filas o el CIF de dbo.Importacion o dbo.Nutrientes, o algun dato original o homologado, o si alguna
       columna no queda con la collation esperada, se deshace todo (THROW + XACT_ABORT).
     - Termina con una PRUEBA DE HUMO (solo lectura) de las consultas principales de los dashboards.

   COMO REVERTIR (reemplazar AAAAMMDD por la fecha del respaldo): los datos no cambian, solo la collation. Para volver a la
   situacion anterior: ALTER TABLE dbo.<tabla> ALTER COLUMN <columna> NVARCHAR(400) COLLATE SQL_Latin1_General_CP1_CI_AS NULL; y
   restaurar los procedimientos con SELECT Objeto, Definicion FROM dbo.ZZ_bak29_Definiciones_AAAAMMDD (cambiar CREATE por CREATE OR ALTER).
   ===================================================================== */

USE PIQ_IA;
GO

-- ---------------------------------------------------------------------
-- LOTE 0: parametros, columnas a alinear y totales de control
-- ---------------------------------------------------------------------
SET XACT_ABORT ON;
SET NOCOUNT ON;
SET NOEXEC OFF;

DECLARE @SoloVistaPrevia BIT = 0;   -- 1 = solo muestra la vista previa

IF OBJECT_ID('tempdb..#control29') IS NOT NULL DROP TABLE #control29;
CREATE TABLE #control29 (Clave VARCHAR(40) COLLATE DATABASE_DEFAULT NOT NULL PRIMARY KEY, Texto NVARCHAR(MAX) COLLATE DATABASE_DEFAULT NULL, Numero DECIMAL(19,4) NULL);
INSERT INTO #control29 (Clave, Numero) VALUES ('preview', @SoloVistaPrevia);
INSERT INTO #control29 (Clave, Texto) VALUES ('default', CAST(DATABASEPROPERTYEX(DB_NAME(), 'Collation') AS NVARCHAR(128)));
INSERT INTO #control29 (Clave, Texto) VALUES
    ('col_cat_plag', (SELECT collation_name FROM sys.columns WHERE object_id = OBJECT_ID('dbo.CatalogoNomenclaturaPlaguicidas') AND name = 'Agrupador')),
    ('col_cat_nut',  (SELECT collation_name FROM sys.columns WHERE object_id = OBJECT_ID('dbo.CatalogoAgrupadorNutrientes') AND name = 'ProductoAgrupado'));

IF OBJECT_ID('tempdb..#col29') IS NOT NULL DROP TABLE #col29;
CREATE TABLE #col29 (
    Id INT IDENTITY(1,1) PRIMARY KEY,
    -- COLLATE DATABASE_DEFAULT: las tablas temporales usan la collation de tempdb, que puede ser distinta de la de esta base
    Tabla SYSNAME COLLATE DATABASE_DEFAULT NOT NULL, Columna SYSNAME COLLATE DATABASE_DEFAULT NOT NULL, ColOriginal SYSNAME COLLATE DATABASE_DEFAULT NOT NULL,
    ColAntes SYSNAME COLLATE DATABASE_DEFAULT NULL, ColObjetivo SYSNAME COLLATE DATABASE_DEFAULT NULL, Tipo SYSNAME COLLATE DATABASE_DEFAULT NULL, Largo INT NULL, Nulable BIT NULL);
INSERT INTO #col29 (Tabla, Columna, ColOriginal) VALUES
    ('Importacion', 'EmpresaHomologada',         'importador'),
    ('Importacion', 'NombreComercialHomologado', 'producto'),
    ('Nutrientes',  'EmpresaHomologada',         'EmpresaImportadora');
UPDATE x
SET x.ColAntes = c.collation_name, x.Tipo = t.name, x.Largo = c.max_length, x.Nulable = c.is_nullable, x.ColObjetivo = o.collation_name
FROM #col29 x
LEFT JOIN sys.columns c ON c.object_id = OBJECT_ID('dbo.' + x.Tabla) AND c.name = x.Columna
LEFT JOIN sys.types t ON t.user_type_id = c.user_type_id
LEFT JOIN sys.columns o ON o.object_id = OBJECT_ID('dbo.' + x.Tabla) AND o.name = x.ColOriginal;

-- Totales de control antes de tocar nada
INSERT INTO #control29 (Clave, Numero) VALUES
    ('imp_filas', (SELECT COUNT(*) FROM dbo.Importacion)),
    ('imp_cif',   (SELECT ISNULL(SUM(CAST(cif_USD AS DECIMAL(19,4))), 0) FROM dbo.Importacion)),
    ('nut_filas', (SELECT COUNT(*) FROM dbo.Nutrientes)),
    ('nut_cif',   (SELECT ISNULL(SUM(CAST(CIF_dolares AS DECIMAL(19,4))), 0) FROM dbo.Nutrientes)),
    ('nut_cifq',  (SELECT ISNULL(SUM(CAST(CIF_Q AS DECIMAL(19,4))), 0) FROM dbo.Nutrientes));
GO

-- ---------------------------------------------------------------------
-- LOTE 1: REPORTE (siempre se ejecuta; solo lee): collations antes y despues, dependencias y pendientes
-- ---------------------------------------------------------------------
SET NOCOUNT ON;

SELECT 'collation por defecto de la base ' + DB_NAME() AS dato, (SELECT Texto FROM #control29 WHERE Clave = 'default') AS valor;

SELECT x.Tabla + '.' + x.Columna AS columna_homologada,
       x.ColAntes AS collation_antes,
       x.ColOriginal AS columna_original_de_referencia,
       x.ColObjetivo AS collation_de_la_original,
       CASE WHEN x.ColAntes IS NULL THEN 'la columna no existe (falta aplicar el script 26/27)'
            WHEN x.ColObjetivo IS NULL THEN 'no se encontro la columna original'
            WHEN x.ColAntes = x.ColObjetivo THEN 'ya coincide: no se toca'
            ELSE 'SE ALINEA' END AS accion,
       CASE WHEN x.ColAntes IS NOT NULL AND x.ColObjetivo IS NOT NULL THEN x.ColObjetivo END AS collation_despues
FROM #col29 x
ORDER BY x.Id;

-- Dependencias de las columnas por alinear (los indices y estadisticas se recrean; una restriccion bloquea y deshace todo)
;WITH d AS (
    SELECT x.Tabla, x.Columna, OBJECT_ID('dbo.' + x.Tabla) AS oid, COLUMNPROPERTY(OBJECT_ID('dbo.' + x.Tabla), x.Columna, 'ColumnId') AS cid
    FROM #col29 x WHERE x.ColAntes IS NOT NULL AND x.ColObjetivo IS NOT NULL AND x.ColAntes <> x.ColObjetivo
)
SELECT d.Tabla + '.' + d.Columna AS columna, 'indice' AS tipo, i.name AS objeto,
       CASE WHEN i.is_primary_key = 1 OR i.is_unique_constraint = 1 OR i.type NOT IN (1, 2) THEN 'BLOQUEA' ELSE 'se quita y se recrea igual' END AS tratamiento
FROM d JOIN sys.index_columns ic ON ic.object_id = d.oid AND ic.column_id = d.cid
       JOIN sys.indexes i ON i.object_id = ic.object_id AND i.index_id = ic.index_id
UNION ALL
SELECT d.Tabla + '.' + d.Columna, 'estadistica creada a mano', s.name, 'se quita y se recrea igual'
FROM d JOIN sys.stats_columns sc ON sc.object_id = d.oid AND sc.column_id = d.cid
       JOIN sys.stats s ON s.object_id = sc.object_id AND s.stats_id = sc.stats_id
WHERE s.user_created = 1
UNION ALL
SELECT d.Tabla + '.' + d.Columna, 'vista que lee la tabla', o.name,
       CASE WHEN OBJECTPROPERTY(o.object_id, 'IsSchemaBound') = 1 THEN 'BLOQUEA (SCHEMABINDING)' ELSE 'se refresca (sp_refreshview)' END
FROM d JOIN sys.sql_expression_dependencies e ON e.referenced_id = d.oid
       JOIN sys.objects o ON o.object_id = e.referencing_id AND o.type = 'V'
UNION ALL
SELECT d.Tabla + '.' + d.Columna, 'restriccion / valor por defecto / columna calculada', k.name, 'BLOQUEA'
FROM d JOIN (
         SELECT parent_object_id AS oid, name, parent_column_id AS cid FROM sys.default_constraints
         UNION ALL SELECT parent_object_id, name, parent_column_id FROM sys.check_constraints
         UNION ALL SELECT fk.parent_object_id, fk.name, fc.parent_column_id FROM sys.foreign_keys fk JOIN sys.foreign_key_columns fc ON fc.constraint_object_id = fk.object_id
         UNION ALL SELECT object_id, name, column_id FROM sys.computed_columns
     ) k ON k.oid = d.oid AND k.cid = d.cid;

-- Procedimientos de carga (comparan catalogo contra dbo.stg_*): solo se rehacen si la collation por defecto difiere de la de las originales
DECLARE @colOrig SYSNAME = (SELECT collation_name FROM sys.columns WHERE object_id = OBJECT_ID('dbo.Importacion') AND name = 'importador');
DECLARE @def SYSNAME = (SELECT Texto FROM #control29 WHERE Clave = 'default');
DECLARE @pendCols INT = (SELECT COUNT(*) FROM #col29 WHERE ColAntes IS NOT NULL AND ColObjetivo IS NOT NULL AND ColAntes <> ColObjetivo);
DECLARE @pendProcs INT = 0;
IF @colOrig IS NOT NULL AND @def <> @colOrig
BEGIN
    IF OBJECT_ID('dbo.usp_ActualizarNomenclatura', 'P') IS NOT NULL AND (SELECT Texto FROM #control29 WHERE Clave = 'col_cat_plag') IS NOT NULL
       AND ISNULL(OBJECT_DEFINITION(OBJECT_ID('dbo.usp_ActualizarNomenclatura')), N'') NOT LIKE N'%29: comparaciones con collation explicita%'
        SET @pendProcs = @pendProcs + 1;
    IF OBJECT_ID('dbo.usp_ActualizarAgrupadorNutrientes', 'P') IS NOT NULL AND (SELECT Texto FROM #control29 WHERE Clave = 'col_cat_nut') IS NOT NULL
       AND ISNULL(OBJECT_DEFINITION(OBJECT_ID('dbo.usp_ActualizarAgrupadorNutrientes')), N'') NOT LIKE N'%29: comparaciones con collation explicita%'
        SET @pendProcs = @pendProcs + 1;
END
SELECT 'columnas homologadas por alinear' AS pendiente, @pendCols AS cantidad
UNION ALL SELECT 'procedimientos de carga por rehacer (collation explicita)', @pendProcs;

INSERT INTO #control29 (Clave, Numero) VALUES ('pend_cols', @pendCols), ('pend_procs', @pendProcs),
    ('pendiente', CASE WHEN @pendCols + @pendProcs > 0 THEN 1 ELSE 0 END);
PRINT CASE WHEN @pendCols + @pendProcs > 0 THEN 'Hay cambios por aplicar (columnas y/o procedimientos).' ELSE 'Las collations ya coinciden: no hay nada que cambiar.' END;
GO

-- ---------------------------------------------------------------------
-- LOTE 2: en vista previa o si ya esta todo aplicado, NO se ejecutan los lotes de cambios
-- ---------------------------------------------------------------------
IF (SELECT Numero FROM #control29 WHERE Clave = 'preview') = 1
   OR (SELECT Numero FROM #control29 WHERE Clave = 'pendiente') = 0
    SET NOEXEC ON;
GO

-- ---------------------------------------------------------------------
-- LOTE 3: RESPALDO AUTOMATICO (nunca pisa uno existente)
-- ---------------------------------------------------------------------
DECLARE @sufijo CHAR(8) = CONVERT(CHAR(8), GETDATE(), 112);
DECLARE @bakImp NVARCHAR(200) = N'dbo.ZZ_bak29_Importacion_' + @sufijo;
DECLARE @bakNut NVARCHAR(200) = N'dbo.ZZ_bak29_Nutrientes_' + @sufijo;
DECLARE @bakDef NVARCHAR(200) = N'dbo.ZZ_bak29_Definiciones_' + @sufijo;
IF OBJECT_ID(@bakImp) IS NULL BEGIN EXEC (N'SELECT * INTO ' + @bakImp + N' FROM dbo.Importacion'); PRINT 'Respaldo creado: ' + @bakImp; END
ELSE PRINT 'Respaldo ya existente (no se pisa): ' + @bakImp;
IF OBJECT_ID(@bakNut) IS NULL BEGIN EXEC (N'SELECT * INTO ' + @bakNut + N' FROM dbo.Nutrientes'); PRINT 'Respaldo creado: ' + @bakNut; END
ELSE PRINT 'Respaldo ya existente (no se pisa): ' + @bakNut;
IF OBJECT_ID(@bakDef) IS NULL
BEGIN
    EXEC (N'CREATE TABLE ' + @bakDef + N' (Objeto SYSNAME NOT NULL, Definicion NVARCHAR(MAX) NULL)');
    EXEC (N'INSERT INTO ' + @bakDef + N' (Objeto, Definicion)
            SELECT o.name, OBJECT_DEFINITION(o.object_id) FROM sys.objects o
            WHERE o.object_id IN (OBJECT_ID(''dbo.vw_NutrientesActivos''), OBJECT_ID(''dbo.usp_ActualizarNomenclatura''), OBJECT_ID(''dbo.usp_ActualizarAgrupadorNutrientes''))');
    PRINT 'Respaldo creado: ' + @bakDef;
END
ELSE PRINT 'Respaldo ya existente (no se pisa): ' + @bakDef;
GO

-- ---------------------------------------------------------------------
-- LOTE 4: comienza la transaccion (abarca hasta el COMMIT del lote 6)
-- ---------------------------------------------------------------------
BEGIN TRANSACTION;
GO

-- ---------------------------------------------------------------------
-- LOTE 5: alinear las columnas (con sus dependencias)
-- ---------------------------------------------------------------------
IF @@TRANCOUNT = 0 SET NOEXEC ON;
GO
DECLARE @id INT = 0, @tabla SYSNAME, @col SYSNAME, @colObj SYSNAME, @tipo SYSNAME, @largo INT, @nul BIT, @obj INT, @cid INT;
DECLARE @antes   TABLE (Orden INT IDENTITY(1,1) PRIMARY KEY, Clave NVARCHAR(400) NOT NULL, Texto NVARCHAR(MAX) NOT NULL);
DECLARE @alterar TABLE (Orden INT IDENTITY(1,1) PRIMARY KEY, Texto NVARCHAR(MAX) NOT NULL);
DECLARE @despues TABLE (Orden INT IDENTITY(1,1) PRIMARY KEY, Clave NVARCHAR(400) NOT NULL, Texto NVARCHAR(MAX) NOT NULL);

WHILE 1 = 1
BEGIN
    SELECT TOP 1 @id = Id, @tabla = Tabla, @col = Columna, @colObj = ColObjetivo, @tipo = Tipo, @largo = Largo, @nul = Nulable
    FROM #col29
    WHERE Id > @id AND ColAntes IS NOT NULL AND ColObjetivo IS NOT NULL AND ColAntes <> ColObjetivo
    ORDER BY Id;
    IF @@ROWCOUNT = 0 BREAK;

    SET @obj = OBJECT_ID('dbo.' + @tabla);
    SET @cid = COLUMNPROPERTY(@obj, @col, 'ColumnId');

    IF @tipo NOT IN (N'nvarchar', N'varchar')
        THROW 50030, 'Control fallido: el tipo de la columna no es nvarchar/varchar. Se deshace todo.', 1;

    -- Dependencias que NO se manejan automaticamente: se detiene y se deshace todo
    IF EXISTS (SELECT 1 FROM sys.index_columns ic JOIN sys.indexes i ON i.object_id = ic.object_id AND i.index_id = ic.index_id
               WHERE ic.object_id = @obj AND ic.column_id = @cid AND (i.is_primary_key = 1 OR i.is_unique_constraint = 1 OR i.type NOT IN (1, 2)))
       OR EXISTS (SELECT 1 FROM sys.foreign_key_columns f WHERE (f.parent_object_id = @obj AND f.parent_column_id = @cid) OR (f.referenced_object_id = @obj AND f.referenced_column_id = @cid))
       OR EXISTS (SELECT 1 FROM sys.check_constraints k WHERE k.parent_object_id = @obj AND (k.parent_column_id = @cid OR CHARINDEX(N'[' + @col + N']', k.definition) > 0))
       OR EXISTS (SELECT 1 FROM sys.default_constraints k WHERE k.parent_object_id = @obj AND k.parent_column_id = @cid)
       OR EXISTS (SELECT 1 FROM sys.computed_columns k WHERE k.object_id = @obj AND CHARINDEX(N'[' + @col + N']', k.definition) > 0)
       OR EXISTS (SELECT 1 FROM sys.sql_expression_dependencies d JOIN sys.objects o ON o.object_id = d.referencing_id
                  WHERE d.referenced_id = @obj AND o.type = 'V' AND OBJECTPROPERTY(o.object_id, 'IsSchemaBound') = 1)
        THROW 50031, 'Control fallido: la columna tiene una restriccion, clave foranea, valor por defecto, columna calculada o una vista con SCHEMABINDING que depende de ella; no se alinea automaticamente. Se deshace todo.', 1;

    -- Indices (no restriccion) que contienen la columna: se quitan y se vuelven a crear igual
    INSERT INTO @antes (Clave, Texto)
    SELECT N'IX:' + @tabla + N'.' + i.name, N'DROP INDEX ' + QUOTENAME(i.name) + N' ON dbo.' + QUOTENAME(@tabla)
    FROM sys.indexes i
    WHERE i.object_id = @obj AND i.type IN (1, 2) AND i.is_primary_key = 0 AND i.is_unique_constraint = 0
      AND EXISTS (SELECT 1 FROM sys.index_columns ic WHERE ic.object_id = i.object_id AND ic.index_id = i.index_id AND ic.column_id = @cid)
      AND NOT EXISTS (SELECT 1 FROM @antes a WHERE a.Clave = N'IX:' + @tabla + N'.' + i.name);
    INSERT INTO @despues (Clave, Texto)
    SELECT N'IX:' + @tabla + N'.' + i.name, N'CREATE ' + CASE WHEN i.is_unique = 1 THEN N'UNIQUE ' ELSE N'' END + CASE WHEN i.type = 1 THEN N'CLUSTERED' ELSE N'NONCLUSTERED' END
         + N' INDEX ' + QUOTENAME(i.name) + N' ON dbo.' + QUOTENAME(@tabla) + N' ('
         + (SELECT STRING_AGG(QUOTENAME(c.name) + CASE WHEN ic.is_descending_key = 1 THEN N' DESC' ELSE N'' END, N', ') WITHIN GROUP (ORDER BY ic.key_ordinal)
            FROM sys.index_columns ic JOIN sys.columns c ON c.object_id = ic.object_id AND c.column_id = ic.column_id
            WHERE ic.object_id = i.object_id AND ic.index_id = i.index_id AND ic.is_included_column = 0) + N')'
         + ISNULL(N' INCLUDE (' + (SELECT STRING_AGG(QUOTENAME(c.name), N', ')
            FROM sys.index_columns ic JOIN sys.columns c ON c.object_id = ic.object_id AND c.column_id = ic.column_id
            WHERE ic.object_id = i.object_id AND ic.index_id = i.index_id AND ic.is_included_column = 1) + N')', N'')
         + CASE WHEN i.has_filter = 1 THEN N' WHERE ' + i.filter_definition ELSE N'' END
    FROM sys.indexes i
    WHERE i.object_id = @obj AND i.type IN (1, 2) AND i.is_primary_key = 0 AND i.is_unique_constraint = 0
      AND EXISTS (SELECT 1 FROM sys.index_columns ic WHERE ic.object_id = i.object_id AND ic.index_id = i.index_id AND ic.column_id = @cid)
      AND NOT EXISTS (SELECT 1 FROM @despues d WHERE d.Clave = N'IX:' + @tabla + N'.' + i.name);

    -- Estadisticas creadas a mano que contienen la columna (las automaticas las recrea SQL Server solo)
    INSERT INTO @antes (Clave, Texto)
    SELECT N'ST:' + @tabla + N'.' + s.name, N'DROP STATISTICS dbo.' + QUOTENAME(@tabla) + N'.' + QUOTENAME(s.name)
    FROM sys.stats s
    WHERE s.object_id = @obj AND s.user_created = 1
      AND EXISTS (SELECT 1 FROM sys.stats_columns sc WHERE sc.object_id = s.object_id AND sc.stats_id = s.stats_id AND sc.column_id = @cid)
      AND NOT EXISTS (SELECT 1 FROM @antes a WHERE a.Clave = N'ST:' + @tabla + N'.' + s.name);
    INSERT INTO @despues (Clave, Texto)
    SELECT N'ST:' + @tabla + N'.' + s.name, N'CREATE STATISTICS ' + QUOTENAME(s.name) + N' ON dbo.' + QUOTENAME(@tabla) + N' ('
         + (SELECT STRING_AGG(QUOTENAME(c.name), N', ') WITHIN GROUP (ORDER BY sc.stats_column_id)
            FROM sys.stats_columns sc JOIN sys.columns c ON c.object_id = sc.object_id AND c.column_id = sc.column_id
            WHERE sc.object_id = s.object_id AND sc.stats_id = s.stats_id) + N')'
    FROM sys.stats s
    WHERE s.object_id = @obj AND s.user_created = 1
      AND EXISTS (SELECT 1 FROM sys.stats_columns sc WHERE sc.object_id = s.object_id AND sc.stats_id = s.stats_id AND sc.column_id = @cid)
      AND NOT EXISTS (SELECT 1 FROM @despues d WHERE d.Clave = N'ST:' + @tabla + N'.' + s.name);

    INSERT INTO @alterar (Texto)
    VALUES (N'ALTER TABLE dbo.' + QUOTENAME(@tabla) + N' ALTER COLUMN ' + QUOTENAME(@col) + N' ' + @tipo + N'('
            + CASE WHEN @largo = -1 THEN N'MAX' WHEN @tipo = N'nvarchar' THEN CAST(@largo / 2 AS NVARCHAR(10)) ELSE CAST(@largo AS NVARCHAR(10)) END
            + N') COLLATE ' + @colObj + CASE WHEN @nul = 1 THEN N' NULL' ELSE N' NOT NULL' END);
END

DECLARE @orden INT, @sql NVARCHAR(MAX);
SET @orden = 0;
WHILE 1 = 1
BEGIN
    SELECT TOP 1 @orden = Orden, @sql = Texto FROM @antes WHERE Orden > @orden ORDER BY Orden;
    IF @@ROWCOUNT = 0 BREAK;
    EXEC (@sql);
    PRINT 'Quitado: ' + @sql;
END
SET @orden = 0;
WHILE 1 = 1
BEGIN
    SELECT TOP 1 @orden = Orden, @sql = Texto FROM @alterar WHERE Orden > @orden ORDER BY Orden;
    IF @@ROWCOUNT = 0 BREAK;
    EXEC (@sql);
    PRINT 'Alineada: ' + @sql;
END
SET @orden = 0;
WHILE 1 = 1
BEGIN
    SELECT TOP 1 @orden = Orden, @sql = Texto FROM @despues WHERE Orden > @orden ORDER BY Orden;
    IF @@ROWCOUNT = 0 BREAK;
    EXEC (@sql);
    PRINT 'Recreado: ' + @sql;
END

-- Las vistas que leen las tablas (dbo.vw_NutrientesActivos) se refrescan para que tomen la collation nueva
IF EXISTS (SELECT 1 FROM @alterar)
BEGIN
    DECLARE @vista NVARCHAR(300);
    DECLARE cur_vistas CURSOR LOCAL FAST_FORWARD FOR
        SELECT DISTINCT QUOTENAME(SCHEMA_NAME(o.schema_id)) + N'.' + QUOTENAME(o.name)
        FROM sys.sql_expression_dependencies e JOIN sys.objects o ON o.object_id = e.referencing_id
        WHERE o.type = 'V' AND e.referenced_id IN (OBJECT_ID('dbo.Importacion'), OBJECT_ID('dbo.Nutrientes'));
    OPEN cur_vistas;
    FETCH NEXT FROM cur_vistas INTO @vista;
    WHILE @@FETCH_STATUS = 0
    BEGIN
        EXEC sp_refreshview @vista;
        PRINT 'Vista refrescada: ' + @vista;
        FETCH NEXT FROM cur_vistas INTO @vista;
    END
    CLOSE cur_vistas;
    DEALLOCATE cur_vistas;
END
GO

-- ---------------------------------------------------------------------
-- LOTE 6: procedimientos de carga, controles y COMMIT
-- ---------------------------------------------------------------------
IF @@TRANCOUNT = 0 SET NOEXEC ON;
GO
DECLARE @colPlag SYSNAME = (SELECT Texto FROM #control29 WHERE Clave = 'col_cat_plag');
DECLARE @colNut  SYSNAME = (SELECT Texto FROM #control29 WHERE Clave = 'col_cat_nut');
DECLARE @ddl NVARCHAR(MAX);

IF (SELECT Numero FROM #control29 WHERE Clave = 'pend_procs') > 0
BEGIN
    IF @colPlag IS NOT NULL AND ISNULL(OBJECT_DEFINITION(OBJECT_ID('dbo.usp_ActualizarNomenclatura')), N'') NOT LIKE N'%29: comparaciones con collation explicita%'
    BEGIN
        SET @ddl = N'CREATE OR ALTER PROCEDURE dbo.usp_ActualizarNomenclatura
AS
BEGIN
    SET NOCOUNT ON;
    -- 29: comparaciones con collation explicita (dbo.stg_Nomenclatura la recrea la carga con la collation por defecto de la base;
    -- el catalogo tiene la de las columnas originales)
    MERGE dbo.CatalogoNomenclaturaPlaguicidas AS destino
    USING (
        SELECT DISTINCT IngredienteActivo_Key, Agrupador, Codigo
        FROM dbo.stg_Nomenclatura
        WHERE IngredienteActivo_Key IS NOT NULL
    ) AS origen
    ON destino.IngredienteActivo_Key COLLATE DATABASE_DEFAULT = origen.IngredienteActivo_Key COLLATE DATABASE_DEFAULT
    WHEN MATCHED AND (
            ISNULL(destino.Agrupador, '''') COLLATE ' + @colPlag + N' <> ISNULL(origen.Agrupador, '''') COLLATE ' + @colPlag + N'
         OR ISNULL(destino.Codigo, '''')    COLLATE ' + @colPlag + N' <> ISNULL(origen.Codigo, '''')    COLLATE ' + @colPlag + N'
    ) THEN
        UPDATE SET Agrupador = origen.Agrupador, Codigo = origen.Codigo, FechaMod = GETDATE()
    WHEN NOT MATCHED BY TARGET THEN
        INSERT (IngredienteActivo_Key, Agrupador, Codigo, FechaMod)
        VALUES (origen.IngredienteActivo_Key, origen.Agrupador, origen.Codigo, GETDATE());
END';
        EXEC (@ddl);
        PRINT 'Procedimiento dbo.usp_ActualizarNomenclatura rehecho con COLLATE explicito (' + @colPlag + ').';
    END
    IF @colNut IS NOT NULL AND ISNULL(OBJECT_DEFINITION(OBJECT_ID('dbo.usp_ActualizarAgrupadorNutrientes')), N'') NOT LIKE N'%29: comparaciones con collation explicita%'
    BEGIN
        SET @ddl = N'CREATE OR ALTER PROCEDURE dbo.usp_ActualizarAgrupadorNutrientes
AS
BEGIN
    SET NOCOUNT ON;
    -- 29: comparaciones con collation explicita (dbo.stg_AgrupadorNutrientes la recrea la carga con la collation por defecto de la base;
    -- el catalogo tiene la de las columnas originales)
    MERGE dbo.CatalogoAgrupadorNutrientes AS destino
    USING (
        SELECT DISTINCT NombreComercial_Key, ProductoAgrupado, Codigo
        FROM dbo.stg_AgrupadorNutrientes
        WHERE NombreComercial_Key IS NOT NULL
    ) AS origen
    ON destino.NombreComercial_Key COLLATE DATABASE_DEFAULT = origen.NombreComercial_Key COLLATE DATABASE_DEFAULT
    WHEN MATCHED AND (
            ISNULL(destino.ProductoAgrupado, '''') COLLATE ' + @colNut + N' <> ISNULL(origen.ProductoAgrupado, '''') COLLATE ' + @colNut + N'
         OR ISNULL(destino.Codigo, '''')            COLLATE ' + @colNut + N' <> ISNULL(origen.Codigo, '''')            COLLATE ' + @colNut + N'
    ) THEN
        UPDATE SET ProductoAgrupado = origen.ProductoAgrupado, Codigo = origen.Codigo, FechaMod = GETDATE()
    WHEN NOT MATCHED BY TARGET THEN
        INSERT (NombreComercial_Key, ProductoAgrupado, Codigo, FechaMod)
        VALUES (origen.NombreComercial_Key, origen.ProductoAgrupado, origen.Codigo, GETDATE());
END';
        EXEC (@ddl);
        PRINT 'Procedimiento dbo.usp_ActualizarAgrupadorNutrientes rehecho con COLLATE explicito (' + @colNut + ').';
    END
END

-- Controles: ni una fila ni un centavo de CIF; ninguna columna sin alinear
DECLARE @impFilas INT = (SELECT COUNT(*) FROM dbo.Importacion);
DECLARE @impCif DECIMAL(19,4) = (SELECT ISNULL(SUM(CAST(cif_USD AS DECIMAL(19,4))), 0) FROM dbo.Importacion);
DECLARE @nutFilas INT = (SELECT COUNT(*) FROM dbo.Nutrientes);
DECLARE @nutCif DECIMAL(19,4) = (SELECT ISNULL(SUM(CAST(CIF_dolares AS DECIMAL(19,4))), 0) FROM dbo.Nutrientes);
DECLARE @nutCifQ DECIMAL(19,4) = (SELECT ISNULL(SUM(CAST(CIF_Q AS DECIMAL(19,4))), 0) FROM dbo.Nutrientes);
IF @impFilas <> (SELECT Numero FROM #control29 WHERE Clave = 'imp_filas')
   OR @impCif <> (SELECT Numero FROM #control29 WHERE Clave = 'imp_cif')
   OR @nutFilas <> (SELECT Numero FROM #control29 WHERE Clave = 'nut_filas')
   OR @nutCif <> (SELECT Numero FROM #control29 WHERE Clave = 'nut_cif')
   OR @nutCifQ <> (SELECT Numero FROM #control29 WHERE Clave = 'nut_cifq')
    THROW 50032, 'Control fallido: cambio el numero de filas o el CIF de dbo.Importacion o dbo.Nutrientes. Se deshace todo.', 1;

IF EXISTS (SELECT 1 FROM #col29 x
           JOIN sys.columns c ON c.object_id = OBJECT_ID('dbo.' + x.Tabla) AND c.name = x.Columna
           JOIN sys.columns o ON o.object_id = OBJECT_ID('dbo.' + x.Tabla) AND o.name = x.ColOriginal
           WHERE c.collation_name <> o.collation_name)
    THROW 50033, 'Control fallido: alguna columna homologada no quedo con la collation de su columna original. Se deshace todo.', 1;

-- Los datos (originales y homologados) no cambian: solo cambio la collation
DECLARE @sufijo CHAR(8) = CONVERT(CHAR(8), GETDATE(), 112);
DECLARE @sqlOrig NVARCHAR(MAX) = N'
SELECT @a = (SELECT COUNT(*) FROM dbo.Importacion i JOIN dbo.ZZ_bak29_Importacion_' + @sufijo + N' b ON b.importacionplaguicidaid = i.importacionplaguicidaid
             WHERE ISNULL(i.importador, '''') COLLATE Latin1_General_BIN2 <> ISNULL(b.importador, '''') COLLATE Latin1_General_BIN2
                OR ISNULL(i.producto, '''') COLLATE Latin1_General_BIN2 <> ISNULL(b.producto, '''') COLLATE Latin1_General_BIN2
                OR ISNULL(i.EmpresaHomologada, '''') COLLATE Latin1_General_BIN2 <> ISNULL(b.EmpresaHomologada, '''') COLLATE Latin1_General_BIN2
                OR ISNULL(i.NombreComercialHomologado, '''') COLLATE Latin1_General_BIN2 <> ISNULL(b.NombreComercialHomologado, '''') COLLATE Latin1_General_BIN2),
       @b = (SELECT COUNT(*) FROM dbo.Nutrientes n JOIN dbo.ZZ_bak29_Nutrientes_' + @sufijo + N' b ON b.nutrienteid = n.nutrienteid
             WHERE ISNULL(n.EmpresaImportadora, '''') COLLATE Latin1_General_BIN2 <> ISNULL(b.EmpresaImportadora, '''') COLLATE Latin1_General_BIN2
                OR ISNULL(n.EmpresaHomologada, '''') COLLATE Latin1_General_BIN2 <> ISNULL(b.EmpresaHomologada, '''') COLLATE Latin1_General_BIN2)';
DECLARE @cambioImp INT, @cambioNut INT;
EXEC sp_executesql @sqlOrig, N'@a INT OUTPUT, @b INT OUTPUT', @a = @cambioImp OUTPUT, @b = @cambioNut OUTPUT;
IF @cambioImp <> 0 OR @cambioNut <> 0
    THROW 50034, 'Control fallido: cambiaron datos originales u homologados. Se deshace todo.', 1;

COMMIT TRANSACTION;

PRINT 'dbo.Importacion: ' + CAST(@impFilas AS VARCHAR(20)) + ' filas, CIF USD ' + FORMAT(@impCif, 'N2', 'en-US') + ' (igual que antes).';
PRINT 'dbo.Nutrientes: ' + CAST(@nutFilas AS VARCHAR(20)) + ' filas, CIF USD ' + FORMAT(@nutCif, 'N2', 'en-US') + ' (igual que antes).';
GO

-- ---------------------------------------------------------------------
-- LOTE 7: resultado final: collations despues y prueba de humo
-- ---------------------------------------------------------------------
SET NOEXEC OFF;
SET NOCOUNT ON;
IF (SELECT Numero FROM #control29 WHERE Clave = 'preview') = 1
    PRINT '@SoloVistaPrevia = 1: no se cambio nada.';
ELSE IF (SELECT Numero FROM #control29 WHERE Clave = 'pendiente') = 0
    PRINT 'No habia nada que cambiar (las collations ya coinciden). No se modifico nada.';
ELSE IF @@TRANCOUNT > 0
BEGIN
    ROLLBACK TRANSACTION;
    PRINT 'ATENCION: la transaccion no se cerro; se deshizo todo.';
END
SELECT x.Tabla + '.' + x.Columna AS columna_homologada, c.collation_name AS collation_ahora, o.collation_name AS collation_de_la_original,
       CASE WHEN c.collation_name = o.collation_name THEN 'OK'
            WHEN (SELECT Numero FROM #control29 WHERE Clave = 'preview') = 1 THEN 'vista previa (sin cambios)'
            ELSE 'REVISAR' END AS estado
FROM #col29 x
JOIN sys.columns c ON c.object_id = OBJECT_ID('dbo.' + x.Tabla) AND c.name = x.Columna
JOIN sys.columns o ON o.object_id = OBJECT_ID('dbo.' + x.Tabla) AND o.name = x.ColOriginal
ORDER BY x.Id;
GO

-- ---------------------------------------------------------------------
-- LOTE 8: PRUEBA DE HUMO de los dashboards (solo lectura; si hay conflicto de collation, FALLA aqui)
-- ---------------------------------------------------------------------
-- >>> PRUEBA DE HUMO EMPRESAS
SET NOCOUNT ON;
SELECT p.prueba, p.valor, 'OK' AS estado
FROM (
    SELECT 'Nutrientes - KPI empresas: COUNT(DISTINCT COALESCE(...))' AS prueba,
           CAST(COUNT(DISTINCT COALESCE(EmpresaHomologada COLLATE Modern_Spanish_CI_AS, EmpresaImportadora COLLATE Modern_Spanish_CI_AS)) AS BIGINT) AS valor
    FROM dbo.vw_NutrientesActivos
    UNION ALL
    SELECT 'Nutrientes - Top empresas importadoras: GROUP BY COALESCE(...)', CAST(COUNT(*) AS BIGINT)
    FROM (SELECT TOP 10 COALESCE(EmpresaHomologada COLLATE Modern_Spanish_CI_AS, EmpresaImportadora COLLATE Modern_Spanish_CI_AS) AS empresa, SUM(CIF_dolares) AS cif
          FROM dbo.vw_NutrientesActivos
          WHERE COALESCE(EmpresaHomologada COLLATE Modern_Spanish_CI_AS, EmpresaImportadora COLLATE Modern_Spanish_CI_AS) IS NOT NULL
          GROUP BY COALESCE(EmpresaHomologada COLLATE Modern_Spanish_CI_AS, EmpresaImportadora COLLATE Modern_Spanish_CI_AS)
          ORDER BY SUM(CIF_dolares) DESC) t
    UNION ALL
    SELECT 'Plaguicidas - Top importadores: GROUP BY COALESCE(...)', CAST(COUNT(*) AS BIGINT)
    FROM (SELECT TOP 10 COALESCE(EmpresaHomologada COLLATE Modern_Spanish_CI_AS, importador COLLATE Modern_Spanish_CI_AS) AS empresa, SUM(cif_USD) AS cif
          FROM dbo.Importacion
          WHERE COALESCE(EmpresaHomologada COLLATE Modern_Spanish_CI_AS, importador COLLATE Modern_Spanish_CI_AS) IS NOT NULL
          GROUP BY COALESCE(EmpresaHomologada COLLATE Modern_Spanish_CI_AS, importador COLLATE Modern_Spanish_CI_AS)
          ORDER BY SUM(cif_USD) DESC) t
) p;
-- <<< PRUEBA DE HUMO EMPRESAS

-- >>> PRUEBA DE HUMO NOMBRES
SET NOCOUNT ON;
SELECT p.prueba, p.valor, 'OK' AS estado
FROM (
    SELECT 'Plaguicidas - Nombres comerciales: DISTINCT COALESCE(...)' AS prueba,
           CAST(COUNT(DISTINCT COALESCE(NombreComercialHomologado COLLATE Modern_Spanish_CI_AS, producto COLLATE Modern_Spanish_CI_AS)) AS BIGINT) AS valor
    FROM dbo.Importacion
    UNION ALL
    SELECT 'Plaguicidas - Detalle: ORDER BY COALESCE(...)', CAST(COUNT(*) AS BIGINT)
    FROM (SELECT TOP 20 COALESCE(NombreComercialHomologado COLLATE Modern_Spanish_CI_AS, producto COLLATE Modern_Spanish_CI_AS) AS producto_efectivo
          FROM dbo.Importacion
          ORDER BY COALESCE(NombreComercialHomologado COLLATE Modern_Spanish_CI_AS, producto COLLATE Modern_Spanish_CI_AS)) t
) p;
-- <<< PRUEBA DE HUMO NOMBRES
GO
