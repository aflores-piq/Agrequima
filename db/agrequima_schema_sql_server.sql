/* =====================================================================
   AGREQUIMA - Esquema de base de datos para la nueva aplicación web
   Servidor destino: DESARROLLO-2  (login sa)
   ---------------------------------------------------------------------
   Este script es el punto de partida que Claude Code debe ejecutar (o
   adaptar con un ORM/migraciones) al iniciar el proyecto. Contiene:
     1. Base de datos Agrequima
     2. Seguridad (Roles, Usuarios)
     3. Tablas finales: Importacion (plaguicidas) y Nutrientes
     4. Tablas de staging para ambas cargas
     5. Catálogos permanentes de agrupación (plaguicidas y nutrientes)
     6. Logs de excepciones (transacciones sin agrupador)
     7. Auditoría de cargas (reemplaza al log de texto del script .py)
     8. Procedimientos almacenados de integración para ambos procesos
     9. Preferencias de interfaz del usuario (tema/paleta de color)
   ===================================================================== */

IF DB_ID('Agrequima') IS NULL
BEGIN
    CREATE DATABASE Agrequima;
END
GO

USE Agrequima;
GO

/* =====================================================================
   1. SEGURIDAD
   ===================================================================== */
IF OBJECT_ID('dbo.Roles') IS NULL
BEGIN
    CREATE TABLE dbo.Roles(
        RolId       INT IDENTITY(1,1) PRIMARY KEY,
        NombreRol   VARCHAR(50) NOT NULL UNIQUE
    );
    INSERT INTO dbo.Roles (NombreRol) VALUES ('Administrador'), ('Usuario'), ('Administrador de Usuarios');
END
GO

IF OBJECT_ID('dbo.Usuarios') IS NULL
BEGIN
    CREATE TABLE dbo.Usuarios(
        UsuarioId       INT IDENTITY(1,1) PRIMARY KEY,
        NombreUsuario   VARCHAR(100) NOT NULL UNIQUE,
        NombreCompleto  VARCHAR(200) NULL,
        Email           VARCHAR(200) NULL,
        PasswordHash    VARCHAR(255) NOT NULL,   -- hash bcrypt/argon2, nunca texto plano
        RolId           INT NOT NULL,
        Activo          BIT NOT NULL DEFAULT 1,
        FechaCreacion   DATETIME NOT NULL DEFAULT GETDATE(),
        UltimoLogin     DATETIME NULL,
        PuedeExportar   BIT NOT NULL DEFAULT 0,  -- permiso para descargar Excel desde los dashboards
        AvisoLegalAceptado         BIT NOT NULL DEFAULT 0,  -- aviso legal y condiciones de uso, se pide una sola vez por usuario
        AvisoLegalFechaAceptacion  DATETIME NULL,           -- fecha/hora del SERVIDOR (GETDATE()), no del navegador -- respaldo ante reclamo
        CONSTRAINT FK_Usuarios_Roles FOREIGN KEY (RolId) REFERENCES dbo.Roles(RolId)
    );
END
GO

/* =====================================================================
   2. PLAGUICIDAS - tabla final, staging y catálogo de agrupación
   (Importacion, stg_Importacion, stg_Nomenclatura: mismas estructuras
   que ya existen en el servidor productivo; se recrean aquí porque la
   nueva app usa una base de datos propia en DESARROLLO-2)
   ===================================================================== */
IF OBJECT_ID('dbo.Importacion') IS NULL
BEGIN
    CREATE TABLE dbo.Importacion(
        importacionplaguicidaid INT IDENTITY(1,1) NOT NULL,
        anio                    INT NULL,
        recibointerno           VARCHAR(80) NULL,
        serie_sat               VARCHAR(70) NULL,
        numero_recibo_sat       VARCHAR(80) NULL,
        aplicacion              VARCHAR(150) NULL,
        fecha                   VARCHAR(15) NULL,
        importador              VARCHAR(250) NULL,
        producto                VARCHAR(250) NULL,
        ingrediente_act         VARCHAR(350) NULL,
        exportador              VARCHAR(350) NULL,
        origen                  VARCHAR(50) NULL,
        porcentaje              DECIMAL(18,2) NULL,
        cantidad                DECIMAL(18,2) NULL,
        unidad_medida           VARCHAR(50) NULL,
        cif_USD                 DECIMAL(18,2) NULL,
        cif_Q                   DECIMAL(18,2) NULL,
        tipo_cambio             VARCHAR(50) NULL,
        institucion             VARCHAR(150) NULL,
        umsp                    DECIMAL(18,2) NULL,
        fechamod                DATETIME NULL,
        userid                  INT NULL,
        Grupo                   VARCHAR(350) NULL,
        CodigoAgrupador         VARCHAR(20) NULL,
        CONSTRAINT PK_Importacion PRIMARY KEY CLUSTERED (importacionplaguicidaid ASC)
    );
END
GO

IF OBJECT_ID('dbo.stg_Importacion') IS NULL
BEGIN
    CREATE TABLE dbo.stg_Importacion(
        anio                FLOAT NULL,
        recibointerno       VARCHAR(MAX) NULL,
        serie_sat           VARCHAR(MAX) NULL,
        numero_recibo_sat   VARCHAR(MAX) NULL,
        aplicacion          VARCHAR(MAX) NULL,
        fecha               VARCHAR(MAX) NULL,
        importador          VARCHAR(MAX) NULL,
        producto            VARCHAR(MAX) NULL,
        ingrediente_act     VARCHAR(MAX) NULL,
        ingrediente_key     VARCHAR(MAX) NULL,
        exportador          VARCHAR(MAX) NULL,
        origen              VARCHAR(MAX) NULL,
        porcentaje          FLOAT NULL,
        cantidad            FLOAT NULL,
        unidad_medida       VARCHAR(MAX) NULL,
        cif_USD             FLOAT NULL,
        cif_Q               FLOAT NULL,
        tipo_cambio         VARCHAR(MAX) NULL,
        institucion         VARCHAR(MAX) NULL,
        umsp                FLOAT NULL
    );
END
GO

IF OBJECT_ID('dbo.stg_Nomenclatura') IS NULL
BEGIN
    CREATE TABLE dbo.stg_Nomenclatura(
        IngredienteActivo_Key VARCHAR(MAX) NULL,
        Agrupador             VARCHAR(MAX) NULL,
        Codigo                VARCHAR(MAX) NULL
    );
END
GO

-- Catálogo permanente (el script .py solo sube a stg_Nomenclatura; el
-- procedimiento usp_ActualizarNomenclatura lo integra aquí de forma
-- persistente, incremental, sin borrar códigos ya asignados a mano).
IF OBJECT_ID('dbo.CatalogoNomenclaturaPlaguicidas') IS NULL
BEGIN
    CREATE TABLE dbo.CatalogoNomenclaturaPlaguicidas(
        IngredienteActivo_Key  VARCHAR(400) NOT NULL PRIMARY KEY,
        Agrupador              VARCHAR(350) NULL,
        Codigo                 VARCHAR(20) NULL,
        FechaMod                DATETIME NOT NULL DEFAULT GETDATE()
    );
END
GO

/* =====================================================================
   3. NUTRIENTES - tabla final, staging y catálogo de agrupación
   La carga de nutrientes NO existía todavía; se diseña aquí siguiendo
   el mismo patrón que plaguicidas. La agrupación de nutrientes es por
   NOMBRE COMERCIAL (no por ingrediente activo), según el archivo
   "Agrupador de Fertilizantes Importaciones.xlsx" -> hoja
   "Diccionario Productos" (columnas "Nombre Comercial (MAGA)" y
   "Producto Agrupado").
   ===================================================================== */
IF OBJECT_ID('dbo.Nutrientes') IS NULL
BEGIN
    CREATE TABLE dbo.Nutrientes(
        nutrienteid         INT IDENTITY(1,1) NOT NULL,
        anio                INT NULL,               -- derivado de FechaEmision, para filtros
        Tipo                NVARCHAR(50) NULL,
        No_Licencia         NVARCHAR(50) NULL,
        No_Registro         NVARCHAR(50) NULL,
        NombreComercial     NVARCHAR(200) NULL,
        EmpresaImportadora  NVARCHAR(200) NULL,
        FechaEmision        DATE NULL,
        UMedida             NVARCHAR(50) NULL,
        Cantidad            FLOAT NULL,
        PaisProcedencia     NVARCHAR(100) NULL,
        PaisOrigen          NVARCHAR(100) NULL,
        AduanadeIngreso     NVARCHAR(100) NULL,
        CIF_dolares         MONEY NULL,
        CIF_Q               MONEY NULL,
        TimbresQ            MONEY NULL,
        Exportador          NVARCHAR(150) NULL,
        Concentraciones     NVARCHAR(150) NULL,
        Componentes         NVARCHAR(500) NULL,
        VENTANILLA          NVARCHAR(50) NULL,
        ProductoAgrupado    NVARCHAR(150) NULL,     -- resultado del cruce con el catálogo
        CodigoAgrupador     VARCHAR(20) NULL,
        Excluido            BIT NOT NULL DEFAULT 0,  -- copiado de CatalogoAgrupadorNutrientes.Excluido
        fechamod            DATETIME NULL,
        userid              INT NULL,
        CONSTRAINT PK_Nutrientes PRIMARY KEY CLUSTERED (nutrienteid ASC)
    );
END
GO

IF OBJECT_ID('dbo.stg_Nutrientes') IS NULL
BEGIN
    CREATE TABLE dbo.stg_Nutrientes(
        Tipo                    VARCHAR(MAX) NULL,
        No_Licencia             VARCHAR(MAX) NULL,
        No_Registro             VARCHAR(MAX) NULL,
        NombreComercial         VARCHAR(MAX) NULL,
        NombreComercial_Key     VARCHAR(MAX) NULL,   -- normalizado, para el cruce
        EmpresaImportadora      VARCHAR(MAX) NULL,
        FechaEmision            VARCHAR(MAX) NULL,
        anio                    FLOAT NULL,
        UMedida                 VARCHAR(MAX) NULL,
        Cantidad                FLOAT NULL,
        PaisProcedencia         VARCHAR(MAX) NULL,
        PaisOrigen              VARCHAR(MAX) NULL,
        AduanadeIngreso         VARCHAR(MAX) NULL,
        CIF_dolares             FLOAT NULL,
        CIF_Q                   FLOAT NULL,
        TimbresQ                FLOAT NULL,
        Exportador              VARCHAR(MAX) NULL,
        Concentraciones         VARCHAR(MAX) NULL,
        Componentes             VARCHAR(MAX) NULL,
        VENTANILLA              VARCHAR(MAX) NULL
    );
END
GO

IF OBJECT_ID('dbo.stg_AgrupadorNutrientes') IS NULL
BEGIN
    CREATE TABLE dbo.stg_AgrupadorNutrientes(
        NombreComercial_Key    VARCHAR(MAX) NULL,
        ProductoAgrupado       VARCHAR(MAX) NULL,
        Codigo                 VARCHAR(MAX) NULL
    );
END
GO

IF OBJECT_ID('dbo.CatalogoAgrupadorNutrientes') IS NULL
BEGIN
    CREATE TABLE dbo.CatalogoAgrupadorNutrientes(
        NombreComercial_Key VARCHAR(400) NOT NULL PRIMARY KEY,
        ProductoAgrupado    NVARCHAR(150) NULL,
        Codigo               VARCHAR(20) NULL,
        FechaMod             DATETIME NOT NULL DEFAULT GETDATE(),
        Excluido             BIT NOT NULL DEFAULT 0  -- productos que el cliente confirmó que NO corresponden a Nutrientes
    );
END
GO

-- Vista de solo lectura: dbo.Nutrientes sin las filas Excluido=1 --
-- solución ESTRUCTURAL a la exclusión de productos (en vez de que cada
-- dashboard/reporte/export se acuerde de agregar WHERE Excluido = 0 por
-- su cuenta, todo ese código lee de esta vista -- ver NutrienteActivo
-- en app/models/nutriente.py). dbo.Nutrientes (la tabla real) sigue
-- siendo la que usan la carga (usp_CargarNutrientes) y la
-- sincronización del catálogo, que sí necesitan ver las filas
-- excluidas también.
CREATE OR ALTER VIEW dbo.vw_NutrientesActivos AS
SELECT
    nutrienteid, anio, Tipo, No_Licencia, No_Registro, NombreComercial,
    EmpresaImportadora, FechaEmision, UMedida, Cantidad, PaisProcedencia,
    PaisOrigen, AduanadeIngreso, CIF_dolares, CIF_Q, TimbresQ, Exportador,
    Concentraciones, Componentes, VENTANILLA, ProductoAgrupado,
    CodigoAgrupador, Excluido, fechamod, userid
FROM dbo.Nutrientes
WHERE Excluido = 0;
GO

-- Fórmulas/componentes que el cliente confirmó que deben excluirse de
-- Nutrientes por completo (no un producto puntual -- CUALQUIER producto
-- cuyo Componentes contenga alguna de estas fórmulas). Agregar una
-- fórmula nueva en el futuro es un INSERT acá, no un cambio de código
-- -- ver usp_CargarNutrientes (la aplica automáticamente en cada carga)
-- y el backfill correspondiente en
-- deploy_servidor_real/08_formulas_excluidas_nutrientes.sql.
IF OBJECT_ID('dbo.FormulasExcluidasNutrientes') IS NULL
BEGIN
    CREATE TABLE dbo.FormulasExcluidasNutrientes(
        Formula       VARCHAR(200) NOT NULL PRIMARY KEY,
        FechaCreacion DATETIME NOT NULL DEFAULT GETDATE()
    );
END
GO

IF NOT EXISTS (SELECT 1 FROM dbo.FormulasExcluidasNutrientes WHERE Formula = 'Mancozeb')
    INSERT INTO dbo.FormulasExcluidasNutrientes (Formula) VALUES ('Mancozeb');
IF NOT EXISTS (SELECT 1 FROM dbo.FormulasExcluidasNutrientes WHERE Formula = 'Propamocarbhydrocloride')
    INSERT INTO dbo.FormulasExcluidasNutrientes (Formula) VALUES ('Propamocarbhydrocloride');
GO

/* =====================================================================
   3B. FINANCIERO - Saldos Bancarios y Otros Ingresos (tabla final +
   staging, mismo patrón que Nutrientes). Son cargas directas por
   Excel, sin cruce de catálogo/agrupador -- por eso no hay tabla
   intermedia de catálogo como en Nutrientes/Plaguicidas.
   ===================================================================== */
IF OBJECT_ID('dbo.SaldoBancario') IS NULL
BEGIN
    CREATE TABLE dbo.SaldoBancario(
        SaldoBancarioId INT IDENTITY(1,1) NOT NULL,
        Concepto        NVARCHAR(50) NULL,      -- 'Saldo inicial' | 'Creditos' | 'Debitos'
        Anio            INT NULL,
        Mes             INT NULL,
        Banco           NVARCHAR(50) NULL,      -- BANRURAL, BANCOR, BI, PROMERICA (hoy)
        Valor           DECIMAL(18,2) NULL,
        UsuarioId       INT NULL,
        FechaMod        DATETIME NOT NULL DEFAULT GETDATE(),
        CONSTRAINT PK_SaldoBancario PRIMARY KEY CLUSTERED (SaldoBancarioId ASC)
    );
END
GO

IF OBJECT_ID('dbo.stg_SaldoBancario') IS NULL
BEGIN
    CREATE TABLE dbo.stg_SaldoBancario(
        Concepto        VARCHAR(MAX) NULL,
        Anio            FLOAT NULL,
        Mes             FLOAT NULL,
        Banco           VARCHAR(MAX) NULL,
        Valor           FLOAT NULL
    );
END
GO

IF OBJECT_ID('dbo.OtroIngreso') IS NULL
BEGIN
    CREATE TABLE dbo.OtroIngreso(
        OtroIngresoId   INT IDENTITY(1,1) NOT NULL,
        Tipo            NVARCHAR(50) NULL,      -- 'Presupuesto' | 'Ejecutado'
        Concepto        NVARCHAR(200) NULL,     -- texto libre (hoy 12 valores fijos, no es catálogo)
        Anio            INT NULL,
        Mes             INT NULL,
        Valor           DECIMAL(18,2) NULL,
        UsuarioId       INT NULL,
        FechaMod        DATETIME NOT NULL DEFAULT GETDATE(),
        CONSTRAINT PK_OtroIngreso PRIMARY KEY CLUSTERED (OtroIngresoId ASC)
    );
END
GO

IF OBJECT_ID('dbo.stg_OtroIngreso') IS NULL
BEGIN
    CREATE TABLE dbo.stg_OtroIngreso(
        Tipo            VARCHAR(MAX) NULL,
        Concepto        VARCHAR(MAX) NULL,
        Anio            FLOAT NULL,
        Mes             FLOAT NULL,
        Valor           FLOAT NULL
    );
END
GO

/* =====================================================================
   4. LOGS DE EXCEPCIONES (transacciones sin agrupador encontrado)
   ===================================================================== */
IF OBJECT_ID('dbo.log_ExcepcionesAgrupador') IS NULL
BEGIN
    CREATE TABLE dbo.log_ExcepcionesAgrupador(
        LogId           INT IDENTITY(1,1) PRIMARY KEY,
        FechaCorrida    DATETIME NOT NULL DEFAULT SYSDATETIME(),
        recibointerno   VARCHAR(80) NULL,
        ingrediente_act VARCHAR(350) NULL,
        ingrediente_key VARCHAR(350) NULL,
        producto        VARCHAR(250) NULL,
        cantidad        DECIMAL(18,2) NULL,
        cif_USD         DECIMAL(18,2) NULL
    );
END
GO

IF OBJECT_ID('dbo.log_ExcepcionesAgrupadorNutrientes') IS NULL
BEGIN
    CREATE TABLE dbo.log_ExcepcionesAgrupadorNutrientes(
        LogId               INT IDENTITY(1,1) PRIMARY KEY,
        FechaCorrida        DATETIME NOT NULL DEFAULT SYSDATETIME(),
        No_Licencia         NVARCHAR(50) NULL,
        NombreComercial     NVARCHAR(200) NULL,
        NombreComercial_Key NVARCHAR(200) NULL,
        Cantidad            FLOAT NULL,
        CIF_dolares         MONEY NULL
    );
END
GO

/* =====================================================================
   5. AUDITORÍA DE CARGAS (reemplaza el log de texto plano del script)
   ===================================================================== */
IF OBJECT_ID('dbo.AuditoriaCargas') IS NULL
BEGIN
    CREATE TABLE dbo.AuditoriaCargas(
        CargaId             INT IDENTITY(1,1) PRIMARY KEY,
        TipoCarga           VARCHAR(20) NOT NULL,   -- 'Plaguicidas' | 'Nutrientes' | 'SaldosBancarios' | 'OtrosIngresos'
        NombreArchivo       VARCHAR(300) NULL,
        UsuarioId           INT NULL,
        FechaCarga          DATETIME NOT NULL DEFAULT GETDATE(),
        FilasProcesadas     INT NULL,
        FilasConExcepcion   INT NULL,
        Estado              VARCHAR(20) NULL,       -- 'OK' | 'ConExcepciones' | 'Error'
        MensajeError        VARCHAR(MAX) NULL,
        CONSTRAINT FK_AuditoriaCargas_Usuarios FOREIGN KEY (UsuarioId) REFERENCES dbo.Usuarios(UsuarioId)
    );
END
GO

/* =====================================================================
   6. PROCEDIMIENTOS - PLAGUICIDAS
   ===================================================================== */
CREATE OR ALTER PROCEDURE dbo.usp_ActualizarNomenclatura
AS
BEGIN
    SET NOCOUNT ON;

    MERGE dbo.CatalogoNomenclaturaPlaguicidas AS destino
    USING (
        SELECT DISTINCT IngredienteActivo_Key, Agrupador, Codigo
        FROM dbo.stg_Nomenclatura
        WHERE IngredienteActivo_Key IS NOT NULL
    ) AS origen
    -- COLLATE DATABASE_DEFAULT en los dos lados: stg_Nomenclatura la
    -- recrea pandas (to_sql if_exists="replace") en cada carga sin
    -- especificar collation -- mismo problema resuelto en
    -- usp_CargarNutrientes (ver ese procedimiento para la causa
    -- completa: error 468 si el collation default de la base no
    -- coincide con el de las columnas del catálogo permanente).
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
        -- antes de insertar (el DELETE + INSERT por año se quitó: borraba
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
               -- usp_CargarNutrientes (stg_Importacion también la
               -- recrea pandas sin especificar collation).
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

/* =====================================================================
   7. PROCEDIMIENTOS - NUTRIENTES (nuevos, mismo patrón que plaguicidas)
   ===================================================================== */
CREATE OR ALTER PROCEDURE dbo.usp_ActualizarAgrupadorNutrientes
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
    -- usp_CargarNutrientes (stg_AgrupadorNutrientes también la recrea
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

CREATE OR ALTER PROCEDURE dbo.usp_CargarNutrientes
    @UserId INT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        BEGIN TRANSACTION;

        -- Ver comentario equivalente en usp_CargarImportacion: stg_Nutrientes
        -- ya viene filtrada por el ETL para solo traer meses nuevos, así
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
            -- Excluido=1 si el catálogo ya lo marca para este producto, O
            -- si la fórmula/componente de la fila contiene alguna de las
            -- fórmulas excluidas -- esto último aplica automáticamente a
            -- CUALQUIER producto (nuevo o ya catalogado) que use esa
            -- fórmula, sin depender de que alguien lo agregue al catálogo
            -- a mano. Las fórmulas van hardcodeadas como literales (no
            -- contra dbo.FormulasExcluidasNutrientes, que se dejó de usar
            -- acá) porque comparar una columna contra un LITERAL de texto
            -- nunca genera conflicto de collation -- solo lo genera
            -- comparar columna contra columna (como pasaba antes al
            -- comparar contra FormulasExcluidasNutrientes.Formula, ver
            -- 08_formulas_excluidas_nutrientes.sql). Agregar una fórmula
            -- nueva requiere modificar este CASE y desplegar un script
            -- nuevo (no un INSERT en una tabla).
            CASE
                WHEN s.Componentes LIKE '%Mancozeb%'
                  OR s.Componentes LIKE '%Propamocarbhydrocloride%'
                  OR s.Componentes LIKE '%paraq%'
                THEN 1
                ELSE ISNULL(c.Excluido, 0)
            END,
            GETDATE(), @UserId
        FROM dbo.stg_Nutrientes s
        LEFT JOIN dbo.CatalogoAgrupadorNutrientes c
               -- COLLATE DATABASE_DEFAULT en ambos lados: stg_Nutrientes lo
               -- recrea pandas (to_sql if_exists="replace") en cada carga,
               -- sin especificar collation -- sus columnas de texto quedan
               -- con el collation DEFAULT DE LA BASE donde vive PIQ_IA/
               -- AGREQUIMA. CatalogoAgrupadorNutrientes.NombreComercial_Key
               -- en cambio quedó con COLLATE Modern_Spanish_CI_AS fijo desde
               -- que se generó este script. Si el collation default de la
               -- base del servidor real no es Modern_Spanish_CI_AS (ej.
               -- SQL_Latin1_General_CP1_CI_AS, el default de fábrica de SQL
               -- Server), este JOIN sin COLLATE explícito falla con el error
               -- 468 "Cannot resolve the collation conflict..." -- pasó en
               -- producción al cargar Nutrientes de julio 2026, nunca en
               -- desarrollo porque ahí el collation de la instancia y el de
               -- la base coinciden (los dos Modern_Spanish_CI_AS). Forzar
               -- DATABASE_DEFAULT en los dos lados hace la comparación
               -- funcionar sin importar cuál sea ese default.
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

/* =====================================================================
   8. USUARIO INICIAL (cambiar la contraseña en el primer login)
   El hash de ejemplo debe ser generado por la aplicación (bcrypt); este
   INSERT es solo un marcador de referencia, NO usar tal cual en
   producción.
   ===================================================================== */
-- INSERT INTO dbo.Usuarios (NombreUsuario, NombreCompleto, Email, PasswordHash, RolId)
-- VALUES ('admin', 'Administrador Agrequima', 'admin@agrequima.local', '<hash_bcrypt_aqui>', 1);
GO

/* =====================================================================
   9. PREFERENCIA DE INTERFAZ (tema claro/oscuro)
   Elegido desde el menú de cuenta del encabezado; se guarda por usuario
   para que se aplique de inmediato al iniciar sesión, sin depender solo
   de lo último guardado en el navegador.

   Nota: este mismo menú tuvo también un selector de paleta de acento
   (Verde/Teal/Naranja, columna Usuarios.PaletaColor) que se eliminó por
   decisión de producto — no solo de la interfaz, también la columna en
   BD. No confundir con los colores fijos por dashboard (Plaguicidas
   teal, Nutrientes naranja, ver theme/colors.ts en el frontend), que
   nunca dependieron de esta preferencia y siguen fijos.
   ===================================================================== */
IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'Usuarios' AND COLUMN_NAME = 'Tema'
)
BEGIN
    ALTER TABLE dbo.Usuarios ADD Tema VARCHAR(10) NOT NULL DEFAULT 'Claro';
END
GO

/* =====================================================================
   10. CONTROL DE ACCESO POR MÓDULO (Importaciones/Financiero/Indicadores)
   Mismo criterio que PuedeExportar: permiso individual por usuario (no
   por rol), consultado fresco en cada request (ver
   require_acceso_importaciones/require_acceso_financiero/
   require_acceso_indicadores en deps.py), no embebido de forma estática
   -- si un administrador se lo da/quita a alguien, aplica de inmediato.

   AccesoImportaciones arranca en 1 (no en 0 como los otros dos) para no
   romper el acceso de las cuentas que ya existen hoy -- todas seguían
   viendo Plaguicidas/Nutrientes antes de que este control existiera.
   AccesoIndicadores se agrega ahora aunque ese proyecto todavía no tiene
   pantallas propias -- mismo criterio "genérico desde el inicio" que ya
   se usó en sync_piq_ia.py (SYNC_VISTAS_CONTACC), para no tener que
   volver a tocar el esquema ni el JWT cuando Indicadores arranque.
   ===================================================================== */
IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'Usuarios' AND COLUMN_NAME = 'AccesoImportaciones'
)
BEGIN
    ALTER TABLE dbo.Usuarios ADD AccesoImportaciones BIT NOT NULL DEFAULT 1;
END
GO

IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'Usuarios' AND COLUMN_NAME = 'AccesoFinanciero'
)
BEGIN
    ALTER TABLE dbo.Usuarios ADD AccesoFinanciero BIT NOT NULL DEFAULT 0;
END
GO

IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'Usuarios' AND COLUMN_NAME = 'AccesoIndicadores'
)
BEGIN
    ALTER TABLE dbo.Usuarios ADD AccesoIndicadores BIT NOT NULL DEFAULT 0;
END
GO

/* =====================================================================
   11. AGRUPADOR DE CUENTAS CONTABLES (Financiero -- Estados Financieros)
   Fuente de la columna "Grupo" en las 4 páginas de Estados Financieros
   (ver services/dashboard_financiero.py). Emparejamiento jerárquico por
   código de cuenta: primero Nivel 3 (código completo exacto), si no hay
   coincidencia Nivel 2 (primeros 6 dígitos), si tampoco Nivel 1
   (primeros 4 dígitos) -- ver services/agrupador_cuentas.py.

   Hoy solo trae Egresos/Ingresos/Activo/Pasivo/Patrimonio (los grupos
   que ya usan las 4 páginas construidas). Presupuestos/Importaciones/
   Ingresos [sic, el grupo de Centros de Costo] quedan pendientes -- ese
   agrupador viene de la hoja CC y Asociados del mismo Excel, todavía no
   cargada.
   ===================================================================== */
IF OBJECT_ID('dbo.CatalogoAgrupadorCuentas') IS NULL
BEGIN
    CREATE TABLE dbo.CatalogoAgrupadorCuentas(
        TipoAgrupador VARCHAR(20) NOT NULL,
        Orden         INT NOT NULL,
        Nivel         INT NOT NULL,
        Codigo        VARCHAR(20) NOT NULL,
        Nombre        VARCHAR(150) NOT NULL,
        CONSTRAINT PK_CatalogoAgrupadorCuentas PRIMARY KEY CLUSTERED (TipoAgrupador, Codigo)
    );
END
GO

INSERT INTO dbo.CatalogoAgrupadorCuentas (TipoAgrupador, Orden, Nivel, Codigo, Nombre)
SELECT v.TipoAgrupador, v.Orden, v.Nivel, v.Codigo, v.Nombre
FROM (VALUES
    ('Egresos', 1, 1, '5101', 'Sueldos Bonificaciones y Prestaciones de Ley'),
    ('Egresos', 2, 1, '5102', 'Gastos Generales de Funcionamiento'),
    ('Egresos', 3, 3, '510201011', 'Cuentas Incobrables'),
    ('Egresos', 4, 2, '510206', 'Suscripciones y Membresías'),
    ('Egresos', 5, 1, '5106', 'Gastos de Viaje al Exterior'),
    ('Egresos', 6, 1, '5103', 'Literatura y Material para Capacitación Programa Educación'),
    ('Egresos', 7, 1, '5105', 'Viáticos e Insumos Programa Cuidagro'),
    ('Egresos', 7, 1, '5104', 'Viáticos e Insumos Programa Cuidagro'),
    ('Egresos', 8, 1, '5107', 'Imagen y Divulgación'),
    ('Egresos', 9, 1, '5108', 'Auditoria'),
    ('Egresos', 10, 1, '5109', 'Honorarios Profesionales'),
    ('Egresos', 11, 1, '5110', 'Viáticos Mantenimiento Incineración Programa CampoLimpio'),
    ('Egresos', 12, 1, '5111', 'Imprevistos'),
    ('Egresos', 13, 1, '5112', 'Gastos de Apoyo a Instituciones'),
    ('Egresos', 14, 1, '5113', 'Proyectos / Fundacion Mayan Field'),
    ('Egresos', 15, 1, '5114', 'Gastos Proyectos de Investigación'),
    ('Egresos', 16, 1, '5115', 'Provisión de Indemnización'),
    ('Egresos', 17, 1, '5116', 'Provisión de Depreciaciones'),
    ('Egresos', 18, 1, '5117', 'Donaciones'),
    ('Egresos', 19, 1, '5201', 'Gastos Financieros'),
    ('Egresos', 19, 1, '5202', 'Gastos Financieros'),
    ('Egresos', 20, 3, '510701017', 'Proyecto SPMF Croplife'),
    ('Ingresos', 1, 2, '410101', 'Cuotas Asociados'),
    ('Ingresos', 2, 2, '410104', 'Cuotas 4.5 por Millar'),
    ('Ingresos', 3, 2, '410103', 'Ingresos Facturados'),
    ('Ingresos', 4, 2, '410102', 'Donación'),
    ('Ingresos', 5, 2, '410105', 'Intereses bancarios e inversiones'),
    ('Activo', 6, 1, '1101', 'Caja y Bancos'),
    ('Activo', 7, 2, '110201', 'Cuentas por Cobrar Asociados'),
    ('Activo', 8, 3, '110204001', 'Cuentas por Cobrar BANRURAL'),
    ('Activo', 9, 1, '1102', 'Cuentas por Cobrar'),
    ('Activo', 10, 1, '1104', 'Inventario Sellos'),
    ('Activo', 11, 1, '1201', 'Propiedad y equipo'),
    ('Activo', 12, 1, '1202', 'Gastos diferidos'),
    ('Activo', 13, 1, '1103', 'Impuestos por cobrar'),
    ('Pasivo', 1, 2, '210102', 'Impuestos por pagar'),
    ('Pasivo', 2, 2, '210101', 'Cuentas por pagar'),
    ('Pasivo', 3, 2, '210103', 'Prestaciones laborales'),
    ('Pasivo', 4, 2, '210104', 'Ingresos anticipados'),
    ('Pasivo', 5, 3, '210105001', 'Fondos por aplicar acumulado'),
    ('Pasivo', 6, 3, '210105002', 'Fondos por aplicar caso judicial BANRURAL'),
    ('Patrimonio', 1, 3, '310101001', 'Patrimonio activos fijos')
) AS v(TipoAgrupador, Orden, Nivel, Codigo, Nombre)
WHERE NOT EXISTS (
    SELECT 1 FROM dbo.CatalogoAgrupadorCuentas x
    WHERE x.TipoAgrupador = v.TipoAgrupador AND x.Codigo = v.Codigo
);
GO

/* =====================================================================
   12. FINANCIERO -- CONTACC (7 tablas finales + su stg_ correspondiente)
   Reflejan la estructura real de las vistas del cliente (vw_piq_*).
   Mismo patrón que Importacion/stg_Importacion: stg_ con tipos sueltos
   (VARCHAR(MAX)/FLOAT) para la carga cruda desde CSV/Excel, tabla final
   tipada con IDENTITY + fechamod/userid de auditoría. Cargadas por
   primera vez con datos reales vía
   backend/app/services/cargar_datos_financiero_inicial.py (carga
   manual de una sola vez, NO es el sync nocturno -- ver
   sync_piq_ia.py, que todavía no toca estas tablas).
   ===================================================================== */
IF OBJECT_ID('dbo.BalanceSaldos') IS NULL
BEGIN
    CREATE TABLE dbo.BalanceSaldos(
        balancesaldoid  INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        emp_nit         VARCHAR(20) NULL,
        Cta_Codigo      VARCHAR(20) NULL,
        Cta_Descripcion VARCHAR(250) NULL,
        Sal_Ano         INT NULL,
        Sal_Mes         INT NULL,
        Debitos         DECIMAL(18,2) NULL,
        Creditos        DECIMAL(18,2) NULL,
        Saldo           DECIMAL(18,2) NULL,
        Cod_Centro      VARCHAR(20) NULL,
        fechamod        DATETIME NULL,
        userid          INT NULL
    );
END
GO

IF OBJECT_ID('dbo.stg_BalanceSaldos') IS NULL
BEGIN
    CREATE TABLE dbo.stg_BalanceSaldos(
        emp_nit         VARCHAR(MAX) NULL,
        Cta_Codigo      VARCHAR(MAX) NULL,
        Cta_Descripcion VARCHAR(MAX) NULL,
        Sal_Ano         FLOAT NULL,
        Sal_Mes         FLOAT NULL,
        Debitos         FLOAT NULL,
        Creditos        FLOAT NULL,
        Saldo           FLOAT NULL,
        Cod_Centro      VARCHAR(MAX) NULL
    );
END
GO

IF OBJECT_ID('dbo.BalanceGeneral') IS NULL
BEGIN
    CREATE TABLE dbo.BalanceGeneral(
        balancegeneralid INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        emp_nit          VARCHAR(20) NULL,
        Cod_n1           VARCHAR(20) NULL,
        Nom_n1           VARCHAR(250) NULL,
        cod_n5           VARCHAR(20) NULL,
        nom_n5           VARCHAR(250) NULL,
        Sal_Ano          INT NULL,
        Sal_Mes          INT NULL,
        Debitos          DECIMAL(18,2) NULL,
        Creditos         DECIMAL(18,2) NULL,
        Saldo            DECIMAL(18,2) NULL,
        Inicial          DECIMAL(18,2) NULL,
        fechamod         DATETIME NULL,
        userid           INT NULL
    );
END
GO

IF OBJECT_ID('dbo.stg_BalanceGeneral') IS NULL
BEGIN
    CREATE TABLE dbo.stg_BalanceGeneral(
        emp_nit  VARCHAR(MAX) NULL,
        Cod_n1   VARCHAR(MAX) NULL,
        Nom_n1   VARCHAR(MAX) NULL,
        cod_n5   VARCHAR(MAX) NULL,
        nom_n5   VARCHAR(MAX) NULL,
        Sal_Ano  FLOAT NULL,
        Sal_Mes  FLOAT NULL,
        Debitos  FLOAT NULL,
        Creditos FLOAT NULL,
        Saldo    FLOAT NULL,
        Inicial  FLOAT NULL
    );
END
GO

IF OBJECT_ID('dbo.CatalogoCuentas') IS NULL
BEGIN
    CREATE TABLE dbo.CatalogoCuentas(
        catalogocuentaid INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        cta_nivel        INT NULL,
        Codigo_N1        VARCHAR(20) NULL,
        Nombre_n1        VARCHAR(250) NULL,
        Codigo_N5        VARCHAR(20) NULL,
        Nombre_N5        VARCHAR(250) NULL,
        fechamod         DATETIME NULL,
        userid           INT NULL
    );
END
GO

IF OBJECT_ID('dbo.stg_CatalogoCuentas') IS NULL
BEGIN
    CREATE TABLE dbo.stg_CatalogoCuentas(
        cta_nivel FLOAT NULL,
        Codigo_N1 VARCHAR(MAX) NULL,
        Nombre_n1 VARCHAR(MAX) NULL,
        Codigo_N5 VARCHAR(MAX) NULL,
        Nombre_N5 VARCHAR(MAX) NULL
    );
END
GO

IF OBJECT_ID('dbo.CentrosDeCosto') IS NULL
BEGIN
    CREATE TABLE dbo.CentrosDeCosto(
        centrodecostoid INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        emp_nit         VARCHAR(20) NULL,
        Cod_centro      VARCHAR(20) NULL,
        Des_centro      VARCHAR(250) NULL,
        nivel           INT NULL,
        CC_Grupo1       VARCHAR(20) NULL,
        fechamod        DATETIME NULL,
        userid          INT NULL
    );
END
GO

IF OBJECT_ID('dbo.stg_CentrosDeCosto') IS NULL
BEGIN
    CREATE TABLE dbo.stg_CentrosDeCosto(
        emp_nit    VARCHAR(MAX) NULL,
        Cod_centro VARCHAR(MAX) NULL,
        Des_centro VARCHAR(MAX) NULL,
        nivel      FLOAT NULL,
        CC_Grupo1  VARCHAR(MAX) NULL
    );
END
GO

IF OBJECT_ID('dbo.Presupuestos') IS NULL
BEGIN
    CREATE TABLE dbo.Presupuestos(
        presupuestoid   INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        emp_nit         VARCHAR(20) NULL,
        par_ano         INT NULL,
        par_mes         INT NULL,
        cta_codigo      VARCHAR(20) NULL,
        pre_presupuesto DECIMAL(18,2) NULL,
        cod_centro      VARCHAR(20) NULL,
        fechamod        DATETIME NULL,
        userid          INT NULL
    );
END
GO

IF OBJECT_ID('dbo.stg_Presupuestos') IS NULL
BEGIN
    CREATE TABLE dbo.stg_Presupuestos(
        emp_nit         VARCHAR(MAX) NULL,
        par_ano         FLOAT NULL,
        par_mes         FLOAT NULL,
        cta_codigo      VARCHAR(MAX) NULL,
        pre_presupuesto FLOAT NULL,
        cod_centro      VARCHAR(MAX) NULL
    );
END
GO

IF OBJECT_ID('dbo.AsociadosCuota') IS NULL
BEGIN
    CREATE TABLE dbo.AsociadosCuota(
        asociadocuotaid INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        emp_nit         VARCHAR(20) NULL,
        Sal_Ano         INT NULL,
        cod_n5          VARCHAR(20) NULL,
        nom_n5          VARCHAR(250) NULL,
        grupo           VARCHAR(20) NULL,
        nombre_mostrar  VARCHAR(250) NULL,
        cuota           DECIMAL(18,2) NULL,
        fechamod        DATETIME NULL,
        userid          INT NULL
    );
END
GO

IF OBJECT_ID('dbo.stg_AsociadosCuota') IS NULL
BEGIN
    CREATE TABLE dbo.stg_AsociadosCuota(
        emp_nit        VARCHAR(MAX) NULL,
        Sal_Ano        FLOAT NULL,
        cod_n5         VARCHAR(MAX) NULL,
        nom_n5         VARCHAR(MAX) NULL,
        grupo          VARCHAR(MAX) NULL,
        nombre_mostrar VARCHAR(MAX) NULL,
        cuota          FLOAT NULL
    );
END
GO

IF OBJECT_ID('dbo.ChequesCirculacion') IS NULL
BEGIN
    CREATE TABLE dbo.ChequesCirculacion(
        chequecirculacionid INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        ban_codigo          VARCHAR(50) NULL,
        cta_numero          VARCHAR(50) NULL,
        cta_nombre          VARCHAR(250) NULL,
        Cta_Codigo          VARCHAR(20) NULL,
        par_ano             INT NULL,
        par_mes             INT NULL,
        doc_numero          VARCHAR(50) NULL,
        doc_fecha           DATETIME NULL,
        doc_fchcobro        DATETIME NULL,
        doc_nombre          VARCHAR(250) NULL,
        doc_motivo          VARCHAR(MAX) NULL,
        doc_monto           DECIMAL(18,2) NULL,
        fechamod            DATETIME NULL,
        userid              INT NULL
    );
END
GO

IF OBJECT_ID('dbo.stg_ChequesCirculacion') IS NULL
BEGIN
    CREATE TABLE dbo.stg_ChequesCirculacion(
        ban_codigo   VARCHAR(MAX) NULL,
        cta_numero   VARCHAR(MAX) NULL,
        cta_nombre   VARCHAR(MAX) NULL,
        Cta_Codigo   VARCHAR(MAX) NULL,
        par_ano      FLOAT NULL,
        par_mes      FLOAT NULL,
        doc_numero   VARCHAR(MAX) NULL,
        doc_fecha    VARCHAR(MAX) NULL,
        doc_fchcobro VARCHAR(MAX) NULL,
        doc_nombre   VARCHAR(MAX) NULL,
        doc_motivo   VARCHAR(MAX) NULL,
        doc_monto    FLOAT NULL
    );
END
GO