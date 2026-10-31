/* =====================================================================
   PIQ_IA -- Homologacion de empresas (Plaguicidas y Nutrientes)
   (script 26_homologacion_empresas)
   =====================================================================
   POR QUE: la misma empresa viene escrita de varias formas en los archivos
   del cliente ("DISAGRO DE GUATEMALA, S.A" / "DISAGRO DE GUATEMALA, SOCIEDAD
   ANONIMA", "Grupo Fert, S. A." / "GRUPO FERT, S.A", "TRIBO SA" / "TRIBO, S.A.").
   En los tableros salen como empresas distintas (Top de importadores, KPI de
   Empresas, tablas de detalle). Este script deja la BASE DE DATOS lista para
   homologarlas, con el mismo patron de Grupo / ProductoAgrupado: un catalogo y
   una columna sincronizada. (La pantalla para editar el catalogo es el paso 1b.)

   QUE CREA / CAMBIA
     1. dbo.fn_ClaveEmpresa(texto): la clave normalizada de una empresa.
        Mayusculas, sin tildes, sin puntos ni comas, espacios colapsados, y las
        variantes de sociedad anonima (S.A., S. A., SA, S A, SOCIEDAD ANONIMA,
        SOCIEDAD ANÓNIMA) unificadas en un solo sufijo "SA". NO une errores de
        tipeo ni quita otras palabras. Es la UNICA definicion de la clave: la usan
        este script, los procedimientos de carga y la sincronizacion.
     2. dbo.CatalogoEmpresas (EmpresaKey PK normalizada, EmpresaHomologada,
        Confirmada BIT = 0, FechaMod, UsuarioMod): UN catalogo compartido por
        Plaguicidas y Nutrientes. Un nombre homologado vale para las dos.
     3. Columna EmpresaHomologada en dbo.Importacion y dbo.Nutrientes (y en la
        vista dbo.vw_NutrientesActivos), sincronizada desde el catalogo. Los
        datos ORIGINALES (importador, EmpresaImportadora) NO se modifican nunca;
        los tableros usan COALESCE(EmpresaHomologada, original).
     4. dbo.log_ExcepcionesEmpresas: las empresas cuya clave NO esta en el
        catalogo al cargar (mismo patron que log_ExcepcionesAgrupador).
     5. usp_CargarImportacion y usp_CargarNutrientes: rellenan EmpresaHomologada
        cruzando con el catalogo y registran en el log las empresas nuevas (esas
        quedan con EmpresaHomologada NULL).
     6. SEMILLA: inserta en el catalogo TODAS las empresas distintas actuales de
        ambas tablas. Las variantes que normalizan igual se unen bajo el nombre
        de la variante de mayor CIF USD total (entre las dos tablas). Todo lo
        sembrado queda con Confirmada = 0: el cliente lo confirmara luego.
        Si una clave ya esta en el catalogo NO se toca (conserva lo que el
        cliente haya editado).

   NO TOCA importes, cantidades ni los datos originales. Al final verifica que el
   numero de filas y el CIF de dbo.Importacion y dbo.Nutrientes son EXACTAMENTE los
   de antes, y que importador / EmpresaImportadora no cambiaron; si no, ROLLBACK.

   COMO FUNCIONA (importante para leerlo): todo corre en UNA transaccion que
   abarca varios lotes (GO). SET XACT_ABORT ON deshace todo ante cualquier error. En
   la vista previa (@SoloVistaPrevia = 1) se muestran los reportes y NO se ejecuta
   ningun lote de cambios (SET NOEXEC ON). Si ya esta todo aplicado, tampoco se
   ejecuta nada (0 cambios).

   QUE MUESTRA: empresas distintas hoy y despues de normalizar en cada tabla, la
   lista de TODOS los grupos que se unirian (con sus variantes y el nombre
   elegido), y el KPI de Empresas de Nutrientes 2026 enero a julio antes y
   despues (misma base del dashboard).

   RESPALDO AUTOMATICO (solo si hay algo que cambiar; nunca pisa uno existente):
   dbo.ZZ_bak26_Importacion_AAAAMMDD, dbo.ZZ_bak26_Nutrientes_AAAAMMDD y
   dbo.ZZ_bak26_Definiciones_AAAAMMDD (texto de la vista y de los dos
   procedimientos antes del cambio).

   COLLATE DATABASE_DEFAULT en las comparaciones texto-contra-texto (evita el
   error 468). Seguro de repetir: una segunda corrida no cambia nada.

   COMO USARLO
     - Vista previa SIN cambiar nada: poner @SoloVistaPrevia = 1 abajo.
     - Aplicar: @SoloVistaPrevia = 0 (valor por defecto).

   COMO REVERTIR (reemplazar AAAAMMDD por la fecha del respaldo): como los datos
   originales no cambian, basta quitar lo nuevo y restaurar los objetos viejos:
       -- 1) restaurar vista y procedimientos con el texto guardado:
       SELECT Objeto, Definicion FROM dbo.ZZ_bak26_Definiciones_AAAAMMDD;
       --    (ejecutar cada Definicion; empiezan con CREATE, cambiar por CREATE OR ALTER)
       -- 2) ALTER TABLE dbo.Importacion DROP COLUMN EmpresaHomologada;
       --    ALTER TABLE dbo.Nutrientes   DROP COLUMN EmpresaHomologada;
       -- 3) DROP TABLE dbo.CatalogoEmpresas; DROP TABLE dbo.log_ExcepcionesEmpresas;
       --    DROP FUNCTION dbo.fn_ClaveEmpresa;
   (la vista y los procedimientos se restauran ANTES de borrar las columnas).
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

IF OBJECT_ID('tempdb..#control26') IS NOT NULL DROP TABLE #control26;
CREATE TABLE #control26 (Clave VARCHAR(40) NOT NULL PRIMARY KEY, Texto NVARCHAR(MAX) NULL, Numero DECIMAL(19,4) NULL);
INSERT INTO #control26 (Clave, Numero) VALUES ('preview', @SoloVistaPrevia);

-- Plantilla de la clave de empresa ({X} = la columna o variable de texto)
DECLARE @e NVARCHAR(MAX) = N'UPPER(LTRIM(RTRIM(CAST({X} AS NVARCHAR(400)))))';
DECLARE @mapa TABLE (Id INT IDENTITY(1,1) PRIMARY KEY, Desde INT NOT NULL, Hasta NCHAR(1) NOT NULL);
INSERT INTO @mapa (Desde, Hasta) VALUES   -- tildes y diéresis -> letra simple (codigos Unicode, en mayuscula)
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
-- variantes de sociedad anonima -> " SA " (con espacios alrededor para respetar palabras completas)
SET @e = N'REPLACE(REPLACE(N'' '' + ' + @e + N' + N'' '', N'' SOCIEDAD ANONIMA '', N'' SA ''), N'' S A '', N'' SA '')';
SET @e = N'(NULLIF(LTRIM(RTRIM(' + @e + N')), N'''') COLLATE DATABASE_DEFAULT)';
INSERT INTO #control26 (Clave, Texto) VALUES ('plantilla', @e);

-- Totales de control antes de tocar nada
INSERT INTO #control26 (Clave, Numero) VALUES
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

CREATE TABLE #emp26 (
    Origen   VARCHAR(20)   NOT NULL,
    Original NVARCHAR(400) COLLATE Latin1_General_BIN2 NOT NULL,
    Clave    NVARCHAR(400) COLLATE DATABASE_DEFAULT NULL,
    Activa   BIT           NOT NULL,
    Filas    INT           NOT NULL,
    Cif      DECIMAL(19,4) NOT NULL);

DECLARE @plantilla NVARCHAR(MAX) = (SELECT Texto FROM #control26 WHERE Clave = 'plantilla');
DECLARE @sqlEmp NVARCHAR(MAX) = N'
INSERT INTO #emp26 (Origen, Original, Clave, Activa, Filas, Cif)
SELECT ''Plaguicidas'', g.Original, ' + REPLACE(@plantilla, N'{X}', N'g.Original') + N', 1, g.Filas, g.Cif
FROM (SELECT CAST(importador AS NVARCHAR(400)) COLLATE Latin1_General_BIN2 AS Original, COUNT(*) AS Filas,
             ISNULL(SUM(CAST(cif_USD AS DECIMAL(19,4))), 0) AS Cif
      FROM dbo.Importacion WHERE importador IS NOT NULL AND LTRIM(RTRIM(importador)) <> ''''
      GROUP BY CAST(importador AS NVARCHAR(400)) COLLATE Latin1_General_BIN2) g
UNION ALL
SELECT ''Nutrientes'', g.Original, ' + REPLACE(@plantilla, N'{X}', N'g.Original') + N', g.Activa, g.Filas, g.Cif
FROM (SELECT CAST(EmpresaImportadora AS NVARCHAR(400)) COLLATE Latin1_General_BIN2 AS Original,
             CASE WHEN Excluido = 0 THEN 1 ELSE 0 END AS Activa, COUNT(*) AS Filas,
             ISNULL(SUM(CAST(CIF_dolares AS DECIMAL(19,4))), 0) AS Cif
      FROM dbo.Nutrientes WHERE EmpresaImportadora IS NOT NULL AND LTRIM(RTRIM(EmpresaImportadora)) <> ''''
      GROUP BY CAST(EmpresaImportadora AS NVARCHAR(400)) COLLATE Latin1_General_BIN2,
               CASE WHEN Excluido = 0 THEN 1 ELSE 0 END) g';
EXEC sp_executesql @sqlEmp;

-- Empresas distintas hoy y despues de normalizar
SELECT Tabla AS tabla, COUNT(DISTINCT Original) AS distintas_hoy, COUNT(DISTINCT Clave) AS distintas_normalizadas,
       COUNT(DISTINCT Original) - COUNT(DISTINCT Clave) AS se_unen
FROM (
    SELECT 'Plaguicidas (dbo.Importacion.importador)' AS Tabla, Original, Clave FROM #emp26 WHERE Origen = 'Plaguicidas'
    UNION ALL SELECT 'Nutrientes, vista activa (Excluido = 0)', Original, Clave FROM #emp26 WHERE Origen = 'Nutrientes' AND Activa = 1
    UNION ALL SELECT 'Nutrientes, todas las filas', Original, Clave FROM #emp26 WHERE Origen = 'Nutrientes'
    UNION ALL SELECT 'Las dos tablas juntas', Original, Clave FROM #emp26
) t
GROUP BY Tabla
ORDER BY CASE Tabla WHEN 'Las dos tablas juntas' THEN 4 WHEN 'Nutrientes, todas las filas' THEN 3 WHEN 'Plaguicidas (dbo.Importacion.importador)' THEN 1 ELSE 2 END;

-- TODOS los grupos que se unirian (varias formas de escribir la misma empresa)
;WITH v AS (
    SELECT Clave, Original, SUM(Cif) AS Cif, SUM(Filas) AS Filas,
           MAX(CASE WHEN Origen = 'Plaguicidas' THEN 1 ELSE 0 END) AS EnPlaguicidas,
           MAX(CASE WHEN Origen = 'Nutrientes' THEN 1 ELSE 0 END) AS EnNutrientes
    FROM #emp26 GROUP BY Clave, Original
), r AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY Clave ORDER BY Cif DESC, Original) AS rn,
              COUNT(*) OVER (PARTITION BY Clave) AS nvar
    FROM v
)
SELECT r.Clave AS clave,
       MAX(CASE WHEN r.rn = 1 THEN r.Original END) AS nombre_homologado_elegido,
       STRING_AGG(r.Original, '  ||  ') WITHIN GROUP (ORDER BY r.Cif DESC, r.Original) AS variantes,
       MAX(r.nvar) AS variantes_n,
       SUM(r.Filas) AS filas,
       CAST(SUM(r.Cif) AS DECIMAL(19,2)) AS cif_usd,
       CASE WHEN MAX(r.EnPlaguicidas) = 1 AND MAX(r.EnNutrientes) = 1 THEN 'Plaguicidas y Nutrientes'
            WHEN MAX(r.EnPlaguicidas) = 1 THEN 'Plaguicidas' ELSE 'Nutrientes' END AS tabla
FROM r
GROUP BY r.Clave
HAVING MAX(r.nvar) > 1
ORDER BY SUM(r.Cif) DESC;

-- KPI de Empresas de Nutrientes (2026, enero a julio; misma base del dashboard) antes y despues
DECLARE @kpiAntes INT, @kpiDespues INT;
SELECT @kpiAntes = COUNT(DISTINCT n.EmpresaImportadora),
       @kpiDespues = COUNT(DISTINCT e.Clave)
FROM dbo.vw_NutrientesActivos n
LEFT JOIN (SELECT DISTINCT Original, Clave FROM #emp26 WHERE Origen = 'Nutrientes') e
       ON e.Original = CAST(n.EmpresaImportadora AS NVARCHAR(400)) COLLATE Latin1_General_BIN2
WHERE n.anio = 2026 AND n.FechaEmision >= '2026-01-01' AND n.FechaEmision < '2026-08-01' AND n.Tipo NOT IN ('PLAGUICIDA')
  AND NOT EXISTS (
      SELECT 1 FROM dbo.vw_NutrientesActivos o
      WHERE o.anio = n.anio AND o.nutrienteid < n.nutrienteid
        AND (o.No_Licencia = n.No_Licencia OR (o.No_Licencia IS NULL AND n.No_Licencia IS NULL))
        AND (o.No_Registro = n.No_Registro OR (o.No_Registro IS NULL AND n.No_Registro IS NULL))
        AND (o.FechaEmision = n.FechaEmision OR (o.FechaEmision IS NULL AND n.FechaEmision IS NULL))
        AND (o.EmpresaImportadora = n.EmpresaImportadora OR (o.EmpresaImportadora IS NULL AND n.EmpresaImportadora IS NULL))
        AND (o.NombreComercial = n.NombreComercial OR (o.NombreComercial IS NULL AND n.NombreComercial IS NULL))
        AND (o.CIF_dolares = n.CIF_dolares OR (o.CIF_dolares IS NULL AND n.CIF_dolares IS NULL)));
SELECT 'KPI Empresas de Nutrientes, 2026 enero a julio' AS indicador, @kpiAntes AS antes, @kpiDespues AS despues_esperado;

-- Hay algo que cambiar? (estructura incompleta, claves sin sembrar o filas sin sincronizar)
DECLARE @pendiente BIT = CASE WHEN
       OBJECT_ID('dbo.CatalogoEmpresas', 'U') IS NULL OR OBJECT_ID('dbo.log_ExcepcionesEmpresas', 'U') IS NULL
    OR OBJECT_ID('dbo.fn_ClaveEmpresa') IS NULL
    OR COL_LENGTH('dbo.Importacion', 'EmpresaHomologada') IS NULL OR COL_LENGTH('dbo.Nutrientes', 'EmpresaHomologada') IS NULL
    OR ISNULL(OBJECT_DEFINITION(OBJECT_ID('dbo.vw_NutrientesActivos')), '') NOT LIKE '%EmpresaHomologada%'
    OR ISNULL(OBJECT_DEFINITION(OBJECT_ID('dbo.usp_CargarImportacion')), '') NOT LIKE '%EmpresaHomologada%'
    OR ISNULL(OBJECT_DEFINITION(OBJECT_ID('dbo.usp_CargarNutrientes')), '') NOT LIKE '%EmpresaHomologada%'
    THEN 1 ELSE 0 END;
IF @pendiente = 0
BEGIN
    -- Estructura completa: revisar si faltan claves en el catalogo o filas por sincronizar
    DECLARE @sqlPend NVARCHAR(MAX) = N'
    SELECT @p = CASE WHEN
         EXISTS (SELECT 1 FROM #emp26 e WHERE NOT EXISTS (SELECT 1 FROM dbo.CatalogoEmpresas c WHERE c.EmpresaKey COLLATE DATABASE_DEFAULT = e.Clave COLLATE DATABASE_DEFAULT))
      OR EXISTS (SELECT 1 FROM dbo.Importacion i JOIN dbo.CatalogoEmpresas c ON c.EmpresaKey COLLATE DATABASE_DEFAULT = dbo.fn_ClaveEmpresa(i.importador) COLLATE DATABASE_DEFAULT
                 WHERE ISNULL(i.EmpresaHomologada, N'''') COLLATE Latin1_General_BIN2 <> c.EmpresaHomologada COLLATE Latin1_General_BIN2)
      OR EXISTS (SELECT 1 FROM dbo.Nutrientes n JOIN dbo.CatalogoEmpresas c ON c.EmpresaKey COLLATE DATABASE_DEFAULT = dbo.fn_ClaveEmpresa(n.EmpresaImportadora) COLLATE DATABASE_DEFAULT
                 WHERE ISNULL(n.EmpresaHomologada, N'''') COLLATE Latin1_General_BIN2 <> c.EmpresaHomologada COLLATE Latin1_General_BIN2)
      THEN 1 ELSE 0 END';
    EXEC sp_executesql @sqlPend, N'@p BIT OUTPUT', @p = @pendiente OUTPUT;
END
INSERT INTO #control26 (Clave, Numero) VALUES ('pendiente', @pendiente);
PRINT CASE WHEN @pendiente = 1 THEN 'Hay cambios por aplicar (estructura, semilla o sincronizacion).' ELSE 'Ya esta todo aplicado: no hay nada que cambiar.' END;
GO

-- ---------------------------------------------------------------------
-- LOTE 2: en vista previa o si ya esta todo aplicado, NO se ejecutan los lotes de cambios
-- ---------------------------------------------------------------------
IF (SELECT Numero FROM #control26 WHERE Clave = 'preview') = 1
   OR (SELECT Numero FROM #control26 WHERE Clave = 'pendiente') = 0
    SET NOEXEC ON;
GO

-- ---------------------------------------------------------------------
-- LOTE 3: RESPALDO AUTOMATICO (nunca pisa uno existente)
-- ---------------------------------------------------------------------
DECLARE @sufijo CHAR(8) = CONVERT(CHAR(8), GETDATE(), 112);
DECLARE @bakImp NVARCHAR(200) = N'dbo.ZZ_bak26_Importacion_' + @sufijo;
DECLARE @bakNut NVARCHAR(200) = N'dbo.ZZ_bak26_Nutrientes_' + @sufijo;
DECLARE @bakDef NVARCHAR(200) = N'dbo.ZZ_bak26_Definiciones_' + @sufijo;
IF OBJECT_ID(@bakImp) IS NULL BEGIN EXEC (N'SELECT * INTO ' + @bakImp + N' FROM dbo.Importacion'); PRINT 'Respaldo creado: ' + @bakImp; END
ELSE PRINT 'Respaldo ya existente (no se pisa): ' + @bakImp;
IF OBJECT_ID(@bakNut) IS NULL BEGIN EXEC (N'SELECT * INTO ' + @bakNut + N' FROM dbo.Nutrientes'); PRINT 'Respaldo creado: ' + @bakNut; END
ELSE PRINT 'Respaldo ya existente (no se pisa): ' + @bakNut;
IF OBJECT_ID(@bakDef) IS NULL
BEGIN
    EXEC (N'SELECT CAST(o.Objeto AS NVARCHAR(200)) AS Objeto, OBJECT_DEFINITION(OBJECT_ID(o.Objeto)) AS Definicion INTO ' + @bakDef + N'
            FROM (VALUES (N''dbo.vw_NutrientesActivos''), (N''dbo.usp_CargarImportacion''), (N''dbo.usp_CargarNutrientes'')) o (Objeto)');
    PRINT 'Respaldo creado: ' + @bakDef;
END
ELSE PRINT 'Respaldo ya existente (no se pisa): ' + @bakDef;
GO

-- ---------------------------------------------------------------------
-- LOTE 4: comienza la transaccion (abarca hasta el COMMIT del lote 9)
-- ---------------------------------------------------------------------
BEGIN TRANSACTION;
GO

-- ---------------------------------------------------------------------
-- LOTE 5: funcion de la clave, tablas nuevas y columnas
-- ---------------------------------------------------------------------
IF @@TRANCOUNT = 0 SET NOEXEC ON;
GO
DECLARE @plantilla NVARCHAR(MAX) = (SELECT Texto FROM #control26 WHERE Clave = 'plantilla');
DECLARE @ddl NVARCHAR(MAX) = N'CREATE OR ALTER FUNCTION dbo.fn_ClaveEmpresa (@t NVARCHAR(400)) RETURNS NVARCHAR(400) AS BEGIN RETURN '
                           + REPLACE(@plantilla, N'{X}', N'@t') + N'; END';
EXEC (@ddl);
PRINT 'Funcion dbo.fn_ClaveEmpresa creada/actualizada.';

IF OBJECT_ID('dbo.CatalogoEmpresas', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.CatalogoEmpresas (
        EmpresaKey        NVARCHAR(400) NOT NULL PRIMARY KEY,
        EmpresaHomologada NVARCHAR(400) NOT NULL,
        Confirmada        BIT           NOT NULL CONSTRAINT DF_CatalogoEmpresas_Confirmada DEFAULT 0,
        FechaMod          DATETIME      NOT NULL CONSTRAINT DF_CatalogoEmpresas_FechaMod DEFAULT GETDATE(),
        UsuarioMod        INT           NULL
    );
    PRINT 'Tabla dbo.CatalogoEmpresas creada.';
END
IF OBJECT_ID('dbo.log_ExcepcionesEmpresas', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.log_ExcepcionesEmpresas (
        LogId        INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        FechaCorrida DATETIME      NOT NULL CONSTRAINT DF_log_ExcepcionesEmpresas_Fecha DEFAULT SYSDATETIME(),
        Origen       VARCHAR(20)   NOT NULL,
        Empresa      NVARCHAR(400) NULL,
        EmpresaKey   NVARCHAR(400) NULL,
        Filas        INT           NULL,
        CifUsd       DECIMAL(19,2) NULL
    );
    PRINT 'Tabla dbo.log_ExcepcionesEmpresas creada.';
END
IF COL_LENGTH('dbo.Importacion', 'EmpresaHomologada') IS NULL
BEGIN
    ALTER TABLE dbo.Importacion ADD EmpresaHomologada NVARCHAR(400) NULL;
    PRINT 'Columna dbo.Importacion.EmpresaHomologada agregada.';
END
IF COL_LENGTH('dbo.Nutrientes', 'EmpresaHomologada') IS NULL
BEGIN
    ALTER TABLE dbo.Nutrientes ADD EmpresaHomologada NVARCHAR(400) NULL;
    PRINT 'Columna dbo.Nutrientes.EmpresaHomologada agregada.';
END
GO

-- ---------------------------------------------------------------------
-- LOTE 6: vista de nutrientes activos, con la columna nueva al final
-- ---------------------------------------------------------------------
IF @@TRANCOUNT = 0 SET NOEXEC ON;
GO
-- (como texto: en la vista previa la columna nueva todavia no existe y el lote no debe compilarse)
EXEC (N'CREATE OR ALTER VIEW dbo.vw_NutrientesActivos AS
SELECT
    nutrienteid, anio, Tipo, No_Licencia, No_Registro, NombreComercial,
    EmpresaImportadora, FechaEmision, UMedida, Cantidad, PaisProcedencia,
    PaisOrigen, AduanadeIngreso, CIF_dolares, CIF_Q, TimbresQ, Exportador,
    Concentraciones, Componentes, VENTANILLA, ProductoAgrupado,
    CodigoAgrupador, Excluido, fechamod, userid, EmpresaHomologada
FROM dbo.Nutrientes
WHERE Excluido = 0');
PRINT 'Vista dbo.vw_NutrientesActivos actualizada (con EmpresaHomologada).';
GO

-- ---------------------------------------------------------------------
-- LOTE 7: usp_CargarImportacion (Plaguicidas): ahora rellena EmpresaHomologada y registra las empresas nuevas
-- ---------------------------------------------------------------------
IF @@TRANCOUNT = 0 SET NOEXEC ON;
GO
CREATE OR ALTER PROCEDURE dbo.usp_CargarImportacion
    @UserId INT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        BEGIN TRANSACTION;

        -- A partir de la validación de "solo cargar el mes nuevo" en el
        -- ETL (Python), dbo.stg_Importacion YA viene filtrada para
        -- contener únicamente meses que todavía no existen en
        -- dbo.Importacion para su año -- por eso ya NO se borra nada
        -- antes de insertar.
        INSERT INTO dbo.Importacion (
            anio, recibointerno, serie_sat, numero_recibo_sat, aplicacion, fecha,
            importador, producto, ingrediente_act, exportador, origen, porcentaje,
            cantidad, unidad_medida, cif_USD, cif_Q, tipo_cambio, institucion, umsp,
            fechamod, userid, Grupo, CodigoAgrupador, EmpresaHomologada
        )
        SELECT
            CAST(s.anio AS INT), s.recibointerno, s.serie_sat, s.numero_recibo_sat,
            s.aplicacion, s.fecha, s.importador, s.producto, s.ingrediente_act,
            s.exportador, s.origen, CAST(s.porcentaje AS DECIMAL(18,2)),
            CAST(s.cantidad AS DECIMAL(18,2)), s.unidad_medida,
            CAST(s.cif_USD AS DECIMAL(18,2)), CAST(s.cif_Q AS DECIMAL(18,2)),
            s.tipo_cambio, s.institucion, CAST(s.umsp AS DECIMAL(18,2)),
            GETDATE(), @UserId, c.Agrupador, c.Codigo, e.EmpresaHomologada
        FROM dbo.stg_Importacion s
        LEFT JOIN dbo.CatalogoNomenclaturaPlaguicidas c
               -- Fix collation: DATABASE_DEFAULT en los dos lados (ver
               -- encabezado de este archivo).
               ON c.IngredienteActivo_Key COLLATE DATABASE_DEFAULT = s.ingrediente_key COLLATE DATABASE_DEFAULT
        LEFT JOIN dbo.CatalogoEmpresas e
               -- Homologacion de empresas: misma clave (dbo.fn_ClaveEmpresa) que usa todo el sistema.
               ON e.EmpresaKey COLLATE DATABASE_DEFAULT = dbo.fn_ClaveEmpresa(s.importador) COLLATE DATABASE_DEFAULT;

        INSERT INTO dbo.log_ExcepcionesAgrupador
            (recibointerno, ingrediente_act, ingrediente_key, producto, cantidad, cif_USD)
        SELECT s.recibointerno, s.ingrediente_act, s.ingrediente_key, s.producto,
               CAST(s.cantidad AS DECIMAL(18,2)), CAST(s.cif_USD AS DECIMAL(18,2))
        FROM dbo.stg_Importacion s
        LEFT JOIN dbo.CatalogoNomenclaturaPlaguicidas c
               ON c.IngredienteActivo_Key COLLATE DATABASE_DEFAULT = s.ingrediente_key COLLATE DATABASE_DEFAULT
        WHERE c.IngredienteActivo_Key IS NULL AND s.ingrediente_key IS NOT NULL;

        -- Empresas nuevas: su clave no esta en el catalogo (quedan con EmpresaHomologada NULL). Una fila por empresa.
        INSERT INTO dbo.log_ExcepcionesEmpresas (Origen, Empresa, EmpresaKey, Filas, CifUsd)
        SELECT 'Plaguicidas', MIN(s.importador), k.Clave, COUNT(*), SUM(CAST(s.cif_USD AS DECIMAL(19,2)))
        FROM dbo.stg_Importacion s
        CROSS APPLY (SELECT dbo.fn_ClaveEmpresa(s.importador) AS Clave) k
        LEFT JOIN dbo.CatalogoEmpresas e
               ON e.EmpresaKey COLLATE DATABASE_DEFAULT = k.Clave COLLATE DATABASE_DEFAULT
        WHERE k.Clave IS NOT NULL AND e.EmpresaKey IS NULL
        GROUP BY k.Clave;

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END
GO

-- ---------------------------------------------------------------------
-- LOTE 8: usp_CargarNutrientes: ahora rellena EmpresaHomologada y registra las empresas nuevas
-- ---------------------------------------------------------------------
IF @@TRANCOUNT = 0 SET NOEXEC ON;
GO
CREATE OR ALTER PROCEDURE dbo.usp_CargarNutrientes
    @UserId INT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        BEGIN TRANSACTION;

        INSERT INTO dbo.Nutrientes (
            anio, Tipo, No_Licencia, No_Registro, NombreComercial, EmpresaImportadora,
            FechaEmision, UMedida, Cantidad, PaisProcedencia, PaisOrigen, AduanadeIngreso,
            CIF_dolares, CIF_Q, TimbresQ, Exportador, Concentraciones, Componentes,
            VENTANILLA, ProductoAgrupado, CodigoAgrupador, Excluido, fechamod, userid, EmpresaHomologada
        )
        SELECT
            CAST(s.anio AS INT), s.Tipo, s.No_Licencia, s.No_Registro, s.NombreComercial,
            s.EmpresaImportadora, TRY_CAST(s.FechaEmision AS DATE), s.UMedida,
            s.Cantidad, s.PaisProcedencia, s.PaisOrigen, s.AduanadeIngreso,
            s.CIF_dolares, s.CIF_Q, s.TimbresQ, s.Exportador, s.Concentraciones,
            s.Componentes, s.VENTANILLA, c.ProductoAgrupado, c.Codigo,
            CASE
                WHEN s.Componentes LIKE '%Mancozeb%'
                  OR s.Componentes LIKE '%Propamocarbhydrocloride%'
                  OR s.Componentes LIKE '%paraq%'
                THEN 1
                ELSE ISNULL(c.Excluido, 0)
            END,
            GETDATE(), @UserId, e.EmpresaHomologada
        FROM dbo.stg_Nutrientes s
        LEFT JOIN dbo.CatalogoAgrupadorNutrientes c
               ON c.NombreComercial_Key COLLATE DATABASE_DEFAULT = s.NombreComercial_Key COLLATE DATABASE_DEFAULT
        LEFT JOIN dbo.CatalogoEmpresas e
               -- Homologacion de empresas: misma clave (dbo.fn_ClaveEmpresa) que usa todo el sistema.
               ON e.EmpresaKey COLLATE DATABASE_DEFAULT = dbo.fn_ClaveEmpresa(s.EmpresaImportadora) COLLATE DATABASE_DEFAULT;

        INSERT INTO dbo.log_ExcepcionesAgrupadorNutrientes
            (No_Licencia, NombreComercial, NombreComercial_Key, Cantidad, CIF_dolares)
        SELECT s.No_Licencia, s.NombreComercial, s.NombreComercial_Key, s.Cantidad, s.CIF_dolares
        FROM dbo.stg_Nutrientes s
        LEFT JOIN dbo.CatalogoAgrupadorNutrientes c
               ON c.NombreComercial_Key COLLATE DATABASE_DEFAULT = s.NombreComercial_Key COLLATE DATABASE_DEFAULT
        WHERE c.NombreComercial_Key IS NULL AND s.NombreComercial_Key IS NOT NULL;

        -- Empresas nuevas: su clave no esta en el catalogo (quedan con EmpresaHomologada NULL). Una fila por empresa.
        INSERT INTO dbo.log_ExcepcionesEmpresas (Origen, Empresa, EmpresaKey, Filas, CifUsd)
        SELECT 'Nutrientes', MIN(s.EmpresaImportadora), k.Clave, COUNT(*), SUM(CAST(s.CIF_dolares AS DECIMAL(19,2)))
        FROM dbo.stg_Nutrientes s
        CROSS APPLY (SELECT dbo.fn_ClaveEmpresa(s.EmpresaImportadora) AS Clave) k
        LEFT JOIN dbo.CatalogoEmpresas e
               ON e.EmpresaKey COLLATE DATABASE_DEFAULT = k.Clave COLLATE DATABASE_DEFAULT
        WHERE k.Clave IS NOT NULL AND e.EmpresaKey IS NULL
        GROUP BY k.Clave;

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END
GO

-- ---------------------------------------------------------------------
-- LOTE 9: semilla del catalogo, sincronizacion, controles y COMMIT
-- ---------------------------------------------------------------------
IF @@TRANCOUNT = 0 SET NOEXEC ON;
GO
-- Semilla: una fila por clave, con el nombre de la variante de mayor CIF USD total (entre las dos tablas)
;WITH v AS (
    SELECT Clave, Original, SUM(Cif) AS Cif FROM #emp26 WHERE Clave IS NOT NULL GROUP BY Clave, Original
), r AS (
    SELECT Clave, Original, ROW_NUMBER() OVER (PARTITION BY Clave ORDER BY Cif DESC, Original) AS rn FROM v
)
INSERT INTO dbo.CatalogoEmpresas (EmpresaKey, EmpresaHomologada, Confirmada, FechaMod, UsuarioMod)
SELECT r.Clave, r.Original, 0, GETDATE(), NULL
FROM r
WHERE r.rn = 1
  AND NOT EXISTS (SELECT 1 FROM dbo.CatalogoEmpresas c WHERE c.EmpresaKey COLLATE DATABASE_DEFAULT = r.Clave COLLATE DATABASE_DEFAULT);
DECLARE @sembradas INT = @@ROWCOUNT;

-- Sincronizacion: EmpresaHomologada de cada fila = la del catalogo para su clave
UPDATE i
SET i.EmpresaHomologada = c.EmpresaHomologada
FROM dbo.Importacion i
JOIN dbo.CatalogoEmpresas c ON c.EmpresaKey COLLATE DATABASE_DEFAULT = dbo.fn_ClaveEmpresa(i.importador) COLLATE DATABASE_DEFAULT
WHERE ISNULL(i.EmpresaHomologada, N'') COLLATE Latin1_General_BIN2 <> c.EmpresaHomologada COLLATE Latin1_General_BIN2;
DECLARE @syncImp INT = @@ROWCOUNT;
UPDATE n
SET n.EmpresaHomologada = c.EmpresaHomologada
FROM dbo.Nutrientes n
JOIN dbo.CatalogoEmpresas c ON c.EmpresaKey COLLATE DATABASE_DEFAULT = dbo.fn_ClaveEmpresa(n.EmpresaImportadora) COLLATE DATABASE_DEFAULT
WHERE ISNULL(n.EmpresaHomologada, N'') COLLATE Latin1_General_BIN2 <> c.EmpresaHomologada COLLATE Latin1_General_BIN2;
DECLARE @syncNut INT = @@ROWCOUNT;

-- Controles: ni una fila ni un centavo de CIF; los datos originales no cambian
DECLARE @impFilas INT = (SELECT COUNT(*) FROM dbo.Importacion);
DECLARE @impCif DECIMAL(19,4) = (SELECT ISNULL(SUM(CAST(cif_USD AS DECIMAL(19,4))), 0) FROM dbo.Importacion);
DECLARE @nutFilas INT = (SELECT COUNT(*) FROM dbo.Nutrientes);
DECLARE @nutCif DECIMAL(19,4) = (SELECT ISNULL(SUM(CAST(CIF_dolares AS DECIMAL(19,4))), 0) FROM dbo.Nutrientes);
DECLARE @nutCifQ DECIMAL(19,4) = (SELECT ISNULL(SUM(CAST(CIF_Q AS DECIMAL(19,4))), 0) FROM dbo.Nutrientes);
IF @impFilas <> (SELECT Numero FROM #control26 WHERE Clave = 'imp_filas')
   OR @impCif <> (SELECT Numero FROM #control26 WHERE Clave = 'imp_cif')
   OR @nutFilas <> (SELECT Numero FROM #control26 WHERE Clave = 'nut_filas')
   OR @nutCif <> (SELECT Numero FROM #control26 WHERE Clave = 'nut_cif')
   OR @nutCifQ <> (SELECT Numero FROM #control26 WHERE Clave = 'nut_cifq')
    THROW 50026, 'Control fallido: cambio el numero de filas o el CIF de dbo.Importacion o dbo.Nutrientes. Se deshace todo.', 1;

DECLARE @sufijo CHAR(8) = CONVERT(CHAR(8), GETDATE(), 112);
DECLARE @sqlOrig NVARCHAR(MAX) = N'
SELECT @a = (SELECT COUNT(*) FROM dbo.Importacion i JOIN dbo.ZZ_bak26_Importacion_' + @sufijo + N' b ON b.importacionplaguicidaid = i.importacionplaguicidaid
             WHERE ISNULL(i.importador, '''') COLLATE Latin1_General_BIN2 <> ISNULL(b.importador, '''') COLLATE Latin1_General_BIN2),
       @b = (SELECT COUNT(*) FROM dbo.Nutrientes n JOIN dbo.ZZ_bak26_Nutrientes_' + @sufijo + N' b ON b.nutrienteid = n.nutrienteid
             WHERE ISNULL(n.EmpresaImportadora, '''') COLLATE Latin1_General_BIN2 <> ISNULL(b.EmpresaImportadora, '''') COLLATE Latin1_General_BIN2)';
DECLARE @cambioImp INT, @cambioNut INT;
EXEC sp_executesql @sqlOrig, N'@a INT OUTPUT, @b INT OUTPUT', @a = @cambioImp OUTPUT, @b = @cambioNut OUTPUT;
IF @cambioImp <> 0 OR @cambioNut <> 0
    THROW 50027, 'Control fallido: cambiaron datos originales de empresa (importador / EmpresaImportadora). Se deshace todo.', 1;

COMMIT TRANSACTION;

PRINT 'Claves sembradas en dbo.CatalogoEmpresas: ' + CAST(@sembradas AS VARCHAR(10));
PRINT 'Filas de dbo.Importacion con EmpresaHomologada asignada: ' + CAST(@syncImp AS VARCHAR(10));
PRINT 'Filas de dbo.Nutrientes con EmpresaHomologada asignada: ' + CAST(@syncNut AS VARCHAR(10));
PRINT 'dbo.Importacion: ' + CAST(@impFilas AS VARCHAR(20)) + ' filas, CIF USD ' + FORMAT(@impCif, 'N2', 'en-US') + ' (igual que antes).';
PRINT 'dbo.Nutrientes: ' + CAST(@nutFilas AS VARCHAR(20)) + ' filas, CIF USD ' + FORMAT(@nutCif, 'N2', 'en-US') + ' (igual que antes).';
GO

-- ---------------------------------------------------------------------
-- LOTE 10: resultado final
-- ---------------------------------------------------------------------
SET NOEXEC OFF;
SET NOCOUNT ON;
IF (SELECT Numero FROM #control26 WHERE Clave = 'preview') = 1
    PRINT '@SoloVistaPrevia = 1: no se cambio nada.';
ELSE IF (SELECT Numero FROM #control26 WHERE Clave = 'pendiente') = 0
    PRINT 'No habia nada que cambiar (ya estaba aplicado). No se modifico nada.';
ELSE IF @@TRANCOUNT > 0
BEGIN
    ROLLBACK TRANSACTION;
    PRINT 'ATENCION: la transaccion no se cerro; se deshizo todo.';
END
ELSE IF OBJECT_ID('dbo.CatalogoEmpresas', 'U') IS NOT NULL
BEGIN
    EXEC (N'
    SELECT ''Plaguicidas'' AS tabla,
           (SELECT COUNT(DISTINCT CAST(importador AS NVARCHAR(400)) COLLATE Latin1_General_BIN2) FROM dbo.Importacion WHERE importador IS NOT NULL) AS empresas_distintas_original,
           (SELECT COUNT(DISTINCT COALESCE(EmpresaHomologada, CAST(importador AS NVARCHAR(400))) COLLATE Latin1_General_BIN2) FROM dbo.Importacion WHERE importador IS NOT NULL) AS empresas_distintas_homologadas
    UNION ALL
    SELECT ''Nutrientes (vista activa)'',
           (SELECT COUNT(DISTINCT CAST(EmpresaImportadora AS NVARCHAR(400)) COLLATE Latin1_General_BIN2) FROM dbo.vw_NutrientesActivos WHERE EmpresaImportadora IS NOT NULL),
           (SELECT COUNT(DISTINCT COALESCE(EmpresaHomologada, CAST(EmpresaImportadora AS NVARCHAR(400))) COLLATE Latin1_General_BIN2) FROM dbo.vw_NutrientesActivos WHERE EmpresaImportadora IS NOT NULL)');
    SELECT COUNT(*) AS claves_en_catalogo, SUM(CAST(Confirmada AS INT)) AS confirmadas FROM dbo.CatalogoEmpresas;
END
GO
