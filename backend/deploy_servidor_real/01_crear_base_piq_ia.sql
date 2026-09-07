/* =====================================================================
   PIQ_IA -- Creacion completa de la base de datos (estructura)
   =====================================================================
   Que hace este script:
     1. Crea la base de datos PIQ_IA si no existe (no toca nada si ya existe).
     2. Crea las 13 tablas reales (datos + propias de la app + Carga),
        con exactamente los mismos tipos de columna, largos, PRIMARY KEY
        e IDENTITY que la base de origen (Desarrollo-2), generado
        automaticamente a partir de la estructura real -- no escrito a mano.
     3. Crea los 4 stored procedures de carga.

   Que NO hace:
     - No carga ningun dato (las tablas quedan vacias). Los datos los trae
       el script de sincronizacion (sync_piq_ia.py), que hay que correr
       aparte -- ver LEEME.txt en esta misma carpeta.
     - Es seguro volver a correrlo mas de una vez: cada CREATE TABLE/
       PROCEDURE esta protegido con un IF (no falla ni borra nada si el
       objeto ya existe). Si un stored procedure ya existe, se reemplaza
       por la version de este script (DROP + CREATE), nunca las tablas.

   Como correrlo:
     1. Abrir SQL Server Management Studio (SSMS) en este servidor.
     2. Conectarse a la instancia de SQL Server correspondiente.
     3. Abrir este archivo (Archivo > Abrir > Archivo... o arrastrarlo a SSMS).
     4. Presionar F5 (o el boton "Ejecutar") con la conexion activa.
     5. Revisar el panel de "Mensajes" abajo -- no debe haber ningun error
        en rojo. Al final hay una consulta de verificacion que muestra el
        conteo de filas por tabla (deberian ser todas 0, recien creadas).
   ===================================================================== */

IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'PIQ_IA')
BEGIN
    CREATE DATABASE PIQ_IA;
END
GO

USE PIQ_IA;
GO

/* ---------------------------------------------------------------------
   TABLAS
   Orden: las tablas referenciadas por una FK van primero (Roles antes
   que Usuarios, Usuarios antes que AuditoriaCargas) para que las
   restricciones de clave foranea se puedan crear sin error.
   --------------------------------------------------------------------- */

IF OBJECT_ID('dbo.Roles', 'U') IS NULL
BEGIN
CREATE TABLE dbo.[Roles] (
	[RolId] INTEGER NOT NULL IDENTITY(1,1), 
	[NombreRol] VARCHAR(50) COLLATE Modern_Spanish_CI_AS NOT NULL, 
	CONSTRAINT [PK__Roles__F92302F1A1197D1F] PRIMARY KEY CLUSTERED ([RolId])
);
END
GO

IF OBJECT_ID('dbo.Usuarios', 'U') IS NULL
BEGIN
CREATE TABLE dbo.[Usuarios] (
	[UsuarioId] INTEGER NOT NULL IDENTITY(1,1), 
	[NombreUsuario] VARCHAR(100) COLLATE Modern_Spanish_CI_AS NOT NULL, 
	[NombreCompleto] VARCHAR(200) COLLATE Modern_Spanish_CI_AS NULL, 
	[Email] VARCHAR(200) COLLATE Modern_Spanish_CI_AS NULL, 
	[PasswordHash] VARCHAR(255) COLLATE Modern_Spanish_CI_AS NOT NULL, 
	[RolId] INTEGER NOT NULL, 
	[Activo] BIT NOT NULL DEFAULT ((1)), 
	[FechaCreacion] DATETIME NOT NULL DEFAULT (getdate()), 
	[UltimoLogin] DATETIME NULL, 
	[PuedeExportar] BIT NOT NULL DEFAULT ((0)), 
	[Tema] VARCHAR(10) COLLATE Modern_Spanish_CI_AS NOT NULL DEFAULT ('Claro'), 
	CONSTRAINT [PK__Usuarios__2B3DE7B817C4236F] PRIMARY KEY CLUSTERED ([UsuarioId]), 
	CONSTRAINT [FK_Usuarios_Roles] FOREIGN KEY([RolId]) REFERENCES dbo.[Roles] ([RolId])
);
END
GO

IF OBJECT_ID('dbo.AuditoriaCargas', 'U') IS NULL
BEGIN
CREATE TABLE dbo.[AuditoriaCargas] (
	[CargaId] INTEGER NOT NULL IDENTITY(1,1), 
	[TipoCarga] VARCHAR(20) COLLATE Modern_Spanish_CI_AS NOT NULL, 
	[NombreArchivo] VARCHAR(300) COLLATE Modern_Spanish_CI_AS NULL, 
	[UsuarioId] INTEGER NULL, 
	[FechaCarga] DATETIME NOT NULL DEFAULT (getdate()), 
	[FilasProcesadas] INTEGER NULL, 
	[FilasConExcepcion] INTEGER NULL, 
	[Estado] VARCHAR(20) COLLATE Modern_Spanish_CI_AS NULL, 
	[MensajeError] VARCHAR(max) COLLATE Modern_Spanish_CI_AS NULL, 
	CONSTRAINT [PK__Auditori__B3699DE8FABC43B1] PRIMARY KEY CLUSTERED ([CargaId]), 
	CONSTRAINT [FK_AuditoriaCargas_Usuarios] FOREIGN KEY([UsuarioId]) REFERENCES dbo.[Usuarios] ([UsuarioId])
);
END
GO

IF OBJECT_ID('dbo.Importacion', 'U') IS NULL
BEGIN
CREATE TABLE dbo.[Importacion] (
	importacionplaguicidaid INTEGER NOT NULL IDENTITY(1,1), 
	anio INTEGER NULL, 
	recibointerno VARCHAR(80) COLLATE Modern_Spanish_CI_AS NULL, 
	serie_sat VARCHAR(70) COLLATE Modern_Spanish_CI_AS NULL, 
	numero_recibo_sat VARCHAR(80) COLLATE Modern_Spanish_CI_AS NULL, 
	aplicacion VARCHAR(150) COLLATE Modern_Spanish_CI_AS NULL, 
	fecha VARCHAR(15) COLLATE Modern_Spanish_CI_AS NULL, 
	importador VARCHAR(250) COLLATE Modern_Spanish_CI_AS NULL, 
	producto VARCHAR(250) COLLATE Modern_Spanish_CI_AS NULL, 
	ingrediente_act VARCHAR(350) COLLATE Modern_Spanish_CI_AS NULL, 
	exportador VARCHAR(350) COLLATE Modern_Spanish_CI_AS NULL, 
	origen VARCHAR(50) COLLATE Modern_Spanish_CI_AS NULL, 
	porcentaje DECIMAL(18, 2) NULL, 
	cantidad DECIMAL(18, 2) NULL, 
	unidad_medida VARCHAR(50) COLLATE Modern_Spanish_CI_AS NULL, 
	[cif_USD] DECIMAL(18, 2) NULL, 
	[cif_Q] DECIMAL(18, 2) NULL, 
	tipo_cambio VARCHAR(50) COLLATE Modern_Spanish_CI_AS NULL, 
	institucion VARCHAR(150) COLLATE Modern_Spanish_CI_AS NULL, 
	umsp DECIMAL(18, 2) NULL, 
	fechamod DATETIME NULL, 
	userid INTEGER NULL, 
	[Grupo] VARCHAR(350) COLLATE Modern_Spanish_CI_AS NULL, 
	[CodigoAgrupador] VARCHAR(20) COLLATE Modern_Spanish_CI_AS NULL, 
	CONSTRAINT [PK_Importacion] PRIMARY KEY CLUSTERED (importacionplaguicidaid)
);
END
GO

IF OBJECT_ID('dbo.Nutrientes', 'U') IS NULL
BEGIN
CREATE TABLE dbo.[Nutrientes] (
	nutrienteid INTEGER NOT NULL IDENTITY(1,1), 
	anio INTEGER NULL, 
	[Tipo] NVARCHAR(50) COLLATE Modern_Spanish_CI_AS NULL, 
	[No_Licencia] NVARCHAR(50) COLLATE Modern_Spanish_CI_AS NULL, 
	[No_Registro] NVARCHAR(50) COLLATE Modern_Spanish_CI_AS NULL, 
	[NombreComercial] NVARCHAR(200) COLLATE Modern_Spanish_CI_AS NULL, 
	[EmpresaImportadora] NVARCHAR(200) COLLATE Modern_Spanish_CI_AS NULL, 
	[FechaEmision] DATE NULL, 
	[UMedida] NVARCHAR(50) COLLATE Modern_Spanish_CI_AS NULL, 
	[Cantidad] FLOAT(53) NULL, 
	[PaisProcedencia] NVARCHAR(100) COLLATE Modern_Spanish_CI_AS NULL, 
	[PaisOrigen] NVARCHAR(100) COLLATE Modern_Spanish_CI_AS NULL, 
	[AduanadeIngreso] NVARCHAR(100) COLLATE Modern_Spanish_CI_AS NULL, 
	[CIF_dolares] MONEY NULL, 
	[CIF_Q] MONEY NULL, 
	[TimbresQ] MONEY NULL, 
	[Exportador] NVARCHAR(150) COLLATE Modern_Spanish_CI_AS NULL, 
	[Concentraciones] NVARCHAR(150) COLLATE Modern_Spanish_CI_AS NULL, 
	[Componentes] NVARCHAR(500) COLLATE Modern_Spanish_CI_AS NULL, 
	[VENTANILLA] NVARCHAR(50) COLLATE Modern_Spanish_CI_AS NULL, 
	[ProductoAgrupado] NVARCHAR(150) COLLATE Modern_Spanish_CI_AS NULL,
	[CodigoAgrupador] VARCHAR(20) COLLATE Modern_Spanish_CI_AS NULL,
	[Excluido] BIT NOT NULL DEFAULT (0),
	fechamod DATETIME NULL,
	userid INTEGER NULL,
	CONSTRAINT [PK_Nutrientes] PRIMARY KEY CLUSTERED (nutrienteid)
);
END
GO

IF OBJECT_ID('dbo.CatalogoNomenclaturaPlaguicidas', 'U') IS NULL
BEGIN
CREATE TABLE dbo.[CatalogoNomenclaturaPlaguicidas] (
	[IngredienteActivo_Key] VARCHAR(400) COLLATE Modern_Spanish_CI_AS NOT NULL, 
	[Agrupador] VARCHAR(350) COLLATE Modern_Spanish_CI_AS NULL, 
	[Codigo] VARCHAR(20) COLLATE Modern_Spanish_CI_AS NULL, 
	[FechaMod] DATETIME NOT NULL DEFAULT (getdate()), 
	CONSTRAINT [PK__Catalogo__03BD5E19E873713B] PRIMARY KEY CLUSTERED ([IngredienteActivo_Key])
);
END
GO

IF OBJECT_ID('dbo.CatalogoAgrupadorNutrientes', 'U') IS NULL
BEGIN
CREATE TABLE dbo.[CatalogoAgrupadorNutrientes] (
	[NombreComercial_Key] VARCHAR(400) COLLATE Modern_Spanish_CI_AS NOT NULL,
	[ProductoAgrupado] NVARCHAR(150) COLLATE Modern_Spanish_CI_AS NULL,
	[Codigo] VARCHAR(20) COLLATE Modern_Spanish_CI_AS NULL,
	[FechaMod] DATETIME NOT NULL DEFAULT (getdate()),
	[Excluido] BIT NOT NULL DEFAULT (0),
	CONSTRAINT [PK__Catalogo__5F0245891384BB33] PRIMARY KEY CLUSTERED ([NombreComercial_Key])
);
END
GO

IF OBJECT_ID('dbo.log_ExcepcionesAgrupador', 'U') IS NULL
BEGIN
CREATE TABLE dbo.[log_ExcepcionesAgrupador] (
	[LogId] INTEGER NOT NULL IDENTITY(1,1), 
	[FechaCorrida] DATETIME NOT NULL DEFAULT (sysdatetime()), 
	recibointerno VARCHAR(80) COLLATE Modern_Spanish_CI_AS NULL, 
	ingrediente_act VARCHAR(350) COLLATE Modern_Spanish_CI_AS NULL, 
	ingrediente_key VARCHAR(350) COLLATE Modern_Spanish_CI_AS NULL, 
	producto VARCHAR(250) COLLATE Modern_Spanish_CI_AS NULL, 
	cantidad DECIMAL(18, 2) NULL, 
	[cif_USD] DECIMAL(18, 2) NULL, 
	CONSTRAINT [PK__log_Exce__5E548648E725C2C8] PRIMARY KEY CLUSTERED ([LogId])
);
END
GO

IF OBJECT_ID('dbo.log_ExcepcionesAgrupadorNutrientes', 'U') IS NULL
BEGIN
CREATE TABLE dbo.[log_ExcepcionesAgrupadorNutrientes] (
	[LogId] INTEGER NOT NULL IDENTITY(1,1), 
	[FechaCorrida] DATETIME NOT NULL DEFAULT (sysdatetime()), 
	[No_Licencia] NVARCHAR(50) COLLATE Modern_Spanish_CI_AS NULL, 
	[NombreComercial] NVARCHAR(200) COLLATE Modern_Spanish_CI_AS NULL, 
	[NombreComercial_Key] NVARCHAR(200) COLLATE Modern_Spanish_CI_AS NULL, 
	[Cantidad] FLOAT(53) NULL, 
	[CIF_dolares] MONEY NULL, 
	CONSTRAINT [PK__log_Exce__5E548648D1716F7E] PRIMARY KEY CLUSTERED ([LogId])
);
END
GO

IF OBJECT_ID('dbo.stg_Importacion', 'U') IS NULL
BEGIN
CREATE TABLE dbo.[stg_Importacion] (
	anio INTEGER NULL, 
	recibointerno VARCHAR(max) COLLATE Modern_Spanish_CI_AS NULL, 
	serie_sat VARCHAR(max) COLLATE Modern_Spanish_CI_AS NULL, 
	numero_recibo_sat VARCHAR(max) COLLATE Modern_Spanish_CI_AS NULL, 
	aplicacion VARCHAR(max) COLLATE Modern_Spanish_CI_AS NULL, 
	fecha VARCHAR(max) COLLATE Modern_Spanish_CI_AS NULL, 
	importador VARCHAR(max) COLLATE Modern_Spanish_CI_AS NULL, 
	producto VARCHAR(max) COLLATE Modern_Spanish_CI_AS NULL, 
	ingrediente_act VARCHAR(max) COLLATE Modern_Spanish_CI_AS NULL, 
	ingrediente_key VARCHAR(max) COLLATE Modern_Spanish_CI_AS NULL, 
	exportador VARCHAR(max) COLLATE Modern_Spanish_CI_AS NULL, 
	origen VARCHAR(max) COLLATE Modern_Spanish_CI_AS NULL, 
	porcentaje FLOAT(53) NULL, 
	cantidad BIGINT NULL, 
	unidad_medida VARCHAR(max) COLLATE Modern_Spanish_CI_AS NULL, 
	[cif_USD] BIGINT NULL, 
	[cif_Q] BIGINT NULL, 
	tipo_cambio VARCHAR(max) COLLATE Modern_Spanish_CI_AS NULL, 
	institucion VARCHAR(max) COLLATE Modern_Spanish_CI_AS NULL, 
	umsp BIGINT NULL
);
END
GO

IF OBJECT_ID('dbo.stg_Nutrientes', 'U') IS NULL
BEGIN
CREATE TABLE dbo.[stg_Nutrientes] (
	[Tipo] VARCHAR(max) COLLATE Modern_Spanish_CI_AS NULL, 
	[No_Licencia] VARCHAR(max) COLLATE Modern_Spanish_CI_AS NULL, 
	[No_Registro] VARCHAR(max) COLLATE Modern_Spanish_CI_AS NULL, 
	[NombreComercial] VARCHAR(max) COLLATE Modern_Spanish_CI_AS NULL, 
	[NombreComercial_Key] VARCHAR(max) COLLATE Modern_Spanish_CI_AS NULL, 
	[EmpresaImportadora] VARCHAR(max) COLLATE Modern_Spanish_CI_AS NULL, 
	[FechaEmision] VARCHAR(max) COLLATE Modern_Spanish_CI_AS NULL, 
	anio INTEGER NULL, 
	[UMedida] VARCHAR(max) COLLATE Modern_Spanish_CI_AS NULL, 
	[Cantidad] BIGINT NULL, 
	[PaisProcedencia] VARCHAR(max) COLLATE Modern_Spanish_CI_AS NULL, 
	[PaisOrigen] VARCHAR(max) COLLATE Modern_Spanish_CI_AS NULL, 
	[AduanadeIngreso] VARCHAR(max) COLLATE Modern_Spanish_CI_AS NULL, 
	[CIF_dolares] FLOAT(53) NULL, 
	[CIF_Q] FLOAT(53) NULL, 
	[TimbresQ] FLOAT(53) NULL, 
	[Exportador] VARCHAR(max) COLLATE Modern_Spanish_CI_AS NULL, 
	[Concentraciones] VARCHAR(max) COLLATE Modern_Spanish_CI_AS NULL, 
	[Componentes] VARCHAR(max) COLLATE Modern_Spanish_CI_AS NULL, 
	[VENTANILLA] VARCHAR(max) COLLATE Modern_Spanish_CI_AS NULL
);
END
GO

IF OBJECT_ID('dbo.stg_Nomenclatura', 'U') IS NULL
BEGIN
CREATE TABLE dbo.[stg_Nomenclatura] (
	[IngredienteActivo_Key] VARCHAR(max) COLLATE Modern_Spanish_CI_AS NULL, 
	[Agrupador] VARCHAR(max) COLLATE Modern_Spanish_CI_AS NULL, 
	[Codigo] VARCHAR(max) COLLATE Modern_Spanish_CI_AS NULL
);
END
GO

IF OBJECT_ID('dbo.stg_AgrupadorNutrientes', 'U') IS NULL
BEGIN
CREATE TABLE dbo.[stg_AgrupadorNutrientes] (
	[NombreComercial_Key] VARCHAR(max) COLLATE Modern_Spanish_CI_AS NULL, 
	[ProductoAgrupado] VARCHAR(max) COLLATE Modern_Spanish_CI_AS NULL, 
	[Codigo] VARCHAR(max) COLLATE Modern_Spanish_CI_AS NULL
);
END
GO

/* ---------------------------------------------------------------------
   STORED PROCEDURES DE CARGA
   Mismo codigo exacto que usan hoy Agrequima/PIQ_IA en Desarrollo-2 --
   copiado con OBJECT_DEFINITION(), no reescrito a mano.
   --------------------------------------------------------------------- */

IF OBJECT_ID('dbo.usp_CargarImportacion', 'P') IS NOT NULL
    DROP PROCEDURE dbo.usp_CargarImportacion;
GO

CREATE PROCEDURE dbo.usp_CargarImportacion
    @UserId INT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        BEGIN TRANSACTION;

        -- A partir de la validación de "solo cargar el mes nuevo" en el
        -- ETL (Python), dbo.stg_Importacion YA viene filtrada para
        -- contener unicamente meses que todavia no existen en
        -- dbo.Importacion para su año -- por eso ya NO se borra nada
        -- antes de insertar (el DELETE + INSERT por año se quito: borraba
        -- los meses ya cargados de ese año antes de insertar los nuevos).
        INSERT INTO dbo.Importacion (
            anio, recibointerno, serie_sat, numero_recibo_sat, aplicacion, fecha,
            importador, producto, ingrediente_act, exportador, origen, porcentaje,
            cantidad, unidad_medida, cif_USD, cif_Q, tipo_cambio, institucion, umsp,
            fechamod, userid, Grupo, CodigoAgrupador
        )
        SELECT
            CAST(s.anio AS INT), s.recibointerno, s.serie_sat, s.numero_recibo_sat,
            s.aplicacion, s.fecha, s.importador, s.producto, s.ingrediente_act,
            s.exportador, s.origen, CAST(s.porcentaje AS DECIMAL(18,2)),
            CAST(s.cantidad AS DECIMAL(18,2)), s.unidad_medida,
            CAST(s.cif_USD AS DECIMAL(18,2)), CAST(s.cif_Q AS DECIMAL(18,2)),
            s.tipo_cambio, s.institucion, CAST(s.umsp AS DECIMAL(18,2)),
            GETDATE(), @UserId, c.Agrupador, c.Codigo
        FROM dbo.stg_Importacion s
        LEFT JOIN dbo.CatalogoNomenclaturaPlaguicidas c
               -- COLLATE DATABASE_DEFAULT: mismo fix de collation que
               -- usp_CargarNutrientes (stg_Importacion tambien la recrea
               -- pandas sin especificar collation).
               ON c.IngredienteActivo_Key COLLATE DATABASE_DEFAULT = s.ingrediente_key COLLATE DATABASE_DEFAULT;

        INSERT INTO dbo.log_ExcepcionesAgrupador
            (recibointerno, ingrediente_act, ingrediente_key, producto, cantidad, cif_USD)
        SELECT s.recibointerno, s.ingrediente_act, s.ingrediente_key, s.producto,
               CAST(s.cantidad AS DECIMAL(18,2)), CAST(s.cif_USD AS DECIMAL(18,2))
        FROM dbo.stg_Importacion s
        LEFT JOIN dbo.CatalogoNomenclaturaPlaguicidas c
               ON c.IngredienteActivo_Key COLLATE DATABASE_DEFAULT = s.ingrediente_key COLLATE DATABASE_DEFAULT
        WHERE c.IngredienteActivo_Key IS NULL AND s.ingrediente_key IS NOT NULL;

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END

GO

IF OBJECT_ID('dbo.usp_CargarNutrientes', 'P') IS NOT NULL
    DROP PROCEDURE dbo.usp_CargarNutrientes;
GO

CREATE PROCEDURE dbo.usp_CargarNutrientes
    @UserId INT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        BEGIN TRANSACTION;

        -- Ver comentario equivalente en usp_CargarImportacion: stg_Nutrientes
        -- ya viene filtrada por el ETL para solo traer meses nuevos, asi
        -- que ya no se borra nada antes de insertar.
        INSERT INTO dbo.Nutrientes (
            anio, Tipo, No_Licencia, No_Registro, NombreComercial, EmpresaImportadora,
            FechaEmision, UMedida, Cantidad, PaisProcedencia, PaisOrigen, AduanadeIngreso,
            CIF_dolares, CIF_Q, TimbresQ, Exportador, Concentraciones, Componentes,
            VENTANILLA, ProductoAgrupado, CodigoAgrupador, Excluido, fechamod, userid
        )
        SELECT
            CAST(s.anio AS INT), s.Tipo, s.No_Licencia, s.No_Registro, s.NombreComercial,
            s.EmpresaImportadora, TRY_CAST(s.FechaEmision AS DATE), s.UMedida,
            s.Cantidad, s.PaisProcedencia, s.PaisOrigen, s.AduanadeIngreso,
            s.CIF_dolares, s.CIF_Q, s.TimbresQ, s.Exportador, s.Concentraciones,
            s.Componentes, s.VENTANILLA, c.ProductoAgrupado, c.Codigo,
            ISNULL(c.Excluido, 0), GETDATE(), @UserId
        FROM dbo.stg_Nutrientes s
        LEFT JOIN dbo.CatalogoAgrupadorNutrientes c
               -- COLLATE DATABASE_DEFAULT en ambos lados: stg_Nutrientes lo recrea
               -- pandas (to_sql if_exists="replace") en cada carga sin especificar
               -- collation, asi que sus columnas de texto quedan con el collation
               -- default DE LA BASE (PIQ_IA/AGREQUIMA), mientras que
               -- CatalogoAgrupadorNutrientes.NombreComercial_Key quedo fijo en
               -- COLLATE Modern_Spanish_CI_AS. Si el collation default de la base
               -- del servidor real no es Modern_Spanish_CI_AS (ej.
               -- SQL_Latin1_General_CP1_CI_AS, el default de fabrica de SQL
               -- Server), este JOIN sin COLLATE explicito falla con el error 468
               -- "Cannot resolve the collation conflict..." -- paso en produccion al
               -- cargar Nutrientes de julio 2026, nunca en desarrollo porque ahi el
               -- collation de la instancia y el de la base coinciden.
               ON c.NombreComercial_Key COLLATE DATABASE_DEFAULT = s.NombreComercial_Key COLLATE DATABASE_DEFAULT;

        INSERT INTO dbo.log_ExcepcionesAgrupadorNutrientes
            (No_Licencia, NombreComercial, NombreComercial_Key, Cantidad, CIF_dolares)
        SELECT s.No_Licencia, s.NombreComercial, s.NombreComercial_Key, s.Cantidad, s.CIF_dolares
        FROM dbo.stg_Nutrientes s
        LEFT JOIN dbo.CatalogoAgrupadorNutrientes c
               ON c.NombreComercial_Key COLLATE DATABASE_DEFAULT = s.NombreComercial_Key COLLATE DATABASE_DEFAULT
        WHERE c.NombreComercial_Key IS NULL AND s.NombreComercial_Key IS NOT NULL;

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END

GO

IF OBJECT_ID('dbo.usp_ActualizarNomenclatura', 'P') IS NOT NULL
    DROP PROCEDURE dbo.usp_ActualizarNomenclatura;
GO

/* =====================================================================
   6. PROCEDIMIENTOS - PLAGUICIDAS
   ===================================================================== */
CREATE   PROCEDURE dbo.usp_ActualizarNomenclatura
AS
BEGIN
    SET NOCOUNT ON;

    MERGE dbo.CatalogoNomenclaturaPlaguicidas AS destino
    USING (
        SELECT DISTINCT IngredienteActivo_Key, Agrupador, Codigo
        FROM dbo.stg_Nomenclatura
        WHERE IngredienteActivo_Key IS NOT NULL
    ) AS origen
    -- COLLATE DATABASE_DEFAULT: mismo fix de collation que
    -- usp_CargarNutrientes (stg_Nomenclatura tambien la recrea pandas
    -- sin especificar collation).
    ON destino.IngredienteActivo_Key COLLATE DATABASE_DEFAULT = origen.IngredienteActivo_Key COLLATE DATABASE_DEFAULT
    WHEN MATCHED AND (
            ISNULL(destino.Agrupador,'') <> ISNULL(origen.Agrupador,'')
         OR ISNULL(destino.Codigo,'')    <> ISNULL(origen.Codigo,'')
    ) THEN
        UPDATE SET Agrupador = origen.Agrupador, Codigo = origen.Codigo, FechaMod = GETDATE()
    WHEN NOT MATCHED BY TARGET THEN
        INSERT (IngredienteActivo_Key, Agrupador, Codigo, FechaMod)
        VALUES (origen.IngredienteActivo_Key, origen.Agrupador, origen.Codigo, GETDATE());
END

GO

IF OBJECT_ID('dbo.usp_ActualizarAgrupadorNutrientes', 'P') IS NOT NULL
    DROP PROCEDURE dbo.usp_ActualizarAgrupadorNutrientes;
GO

/* =====================================================================
   7. PROCEDIMIENTOS - NUTRIENTES (nuevos, mismo patrÃ³n que plaguicidas)
   ===================================================================== */
CREATE   PROCEDURE dbo.usp_ActualizarAgrupadorNutrientes
AS
BEGIN
    SET NOCOUNT ON;

    MERGE dbo.CatalogoAgrupadorNutrientes AS destino
    USING (
        SELECT DISTINCT NombreComercial_Key, ProductoAgrupado, Codigo
        FROM dbo.stg_AgrupadorNutrientes
        WHERE NombreComercial_Key IS NOT NULL
    ) AS origen
    -- COLLATE DATABASE_DEFAULT: mismo fix de collation que
    -- usp_CargarNutrientes (stg_AgrupadorNutrientes tambien la recrea
    -- pandas sin especificar collation).
    ON destino.NombreComercial_Key COLLATE DATABASE_DEFAULT = origen.NombreComercial_Key COLLATE DATABASE_DEFAULT
    WHEN MATCHED AND (
            ISNULL(destino.ProductoAgrupado,'') <> ISNULL(origen.ProductoAgrupado,'')
         OR ISNULL(destino.Codigo,'')            <> ISNULL(origen.Codigo,'')
    ) THEN
        UPDATE SET ProductoAgrupado = origen.ProductoAgrupado, Codigo = origen.Codigo, FechaMod = GETDATE()
    WHEN NOT MATCHED BY TARGET THEN
        INSERT (NombreComercial_Key, ProductoAgrupado, Codigo, FechaMod)
        VALUES (origen.NombreComercial_Key, origen.ProductoAgrupado, origen.Codigo, GETDATE());
END

GO

/* ---------------------------------------------------------------------
   VERIFICACION -- correr esto despues para confirmar que todo se creo
   bien. Recien creada, cada tabla debe mostrar 0 filas (los datos los
   trae sync_piq_ia.py despues, no este script).
   --------------------------------------------------------------------- */
SELECT
    t.name AS tabla,
    p.rows AS filas
FROM sys.tables t
JOIN sys.partitions p ON p.object_id = t.object_id AND p.index_id IN (0, 1)
ORDER BY t.name;

SELECT name AS stored_procedure
FROM sys.procedures
ORDER BY name;

PRINT '=== Script de creacion de PIQ_IA finalizado. Revisa que no haya errores en rojo arriba. ===';
GO
