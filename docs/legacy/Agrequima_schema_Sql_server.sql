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
    INSERT INTO dbo.Roles (NombreRol) VALUES ('Administrador'), ('Usuario');
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
        FechaMod             DATETIME NOT NULL DEFAULT GETDATE()
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
        TipoCarga           VARCHAR(20) NOT NULL,   -- 'Plaguicidas' | 'Nutrientes'
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
    ON destino.IngredienteActivo_Key = origen.IngredienteActivo_Key
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

        -- Estrategia: DELETE + INSERT por cada año presente en el staging
        DELETE i
        FROM dbo.Importacion i
        WHERE i.anio IN (SELECT DISTINCT CAST(anio AS INT) FROM dbo.stg_Importacion WHERE anio IS NOT NULL);

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
               ON c.IngredienteActivo_Key = s.ingrediente_key;

        -- Log de transacciones sin agrupador (para el reporte de excepciones)
        INSERT INTO dbo.log_ExcepcionesAgrupador
            (recibointerno, ingrediente_act, ingrediente_key, producto, cantidad, cif_USD)
        SELECT s.recibointerno, s.ingrediente_act, s.ingrediente_key, s.producto,
               CAST(s.cantidad AS DECIMAL(18,2)), CAST(s.cif_USD AS DECIMAL(18,2))
        FROM dbo.stg_Importacion s
        LEFT JOIN dbo.CatalogoNomenclaturaPlaguicidas c
               ON c.IngredienteActivo_Key = s.ingrediente_key
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
    ON destino.NombreComercial_Key = origen.NombreComercial_Key
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

        DELETE n
        FROM dbo.Nutrientes n
        WHERE n.anio IN (SELECT DISTINCT CAST(anio AS INT) FROM dbo.stg_Nutrientes WHERE anio IS NOT NULL);

        INSERT INTO dbo.Nutrientes (
            anio, Tipo, No_Licencia, No_Registro, NombreComercial, EmpresaImportadora,
            FechaEmision, UMedida, Cantidad, PaisProcedencia, PaisOrigen, AduanadeIngreso,
            CIF_dolares, CIF_Q, TimbresQ, Exportador, Concentraciones, Componentes,
            VENTANILLA, ProductoAgrupado, CodigoAgrupador, fechamod, userid
        )
        SELECT
            CAST(s.anio AS INT), s.Tipo, s.No_Licencia, s.No_Registro, s.NombreComercial,
            s.EmpresaImportadora, TRY_CAST(s.FechaEmision AS DATE), s.UMedida,
            s.Cantidad, s.PaisProcedencia, s.PaisOrigen, s.AduanadeIngreso,
            s.CIF_dolares, s.CIF_Q, s.TimbresQ, s.Exportador, s.Concentraciones,
            s.Componentes, s.VENTANILLA, c.ProductoAgrupado, c.Codigo, GETDATE(), @UserId
        FROM dbo.stg_Nutrientes s
        LEFT JOIN dbo.CatalogoAgrupadorNutrientes c
               ON c.NombreComercial_Key = s.NombreComercial_Key;

        INSERT INTO dbo.log_ExcepcionesAgrupadorNutrientes
            (No_Licencia, NombreComercial, NombreComercial_Key, Cantidad, CIF_dolares)
        SELECT s.No_Licencia, s.NombreComercial, s.NombreComercial_Key, s.Cantidad, s.CIF_dolares
        FROM dbo.stg_Nutrientes s
        LEFT JOIN dbo.CatalogoAgrupadorNutrientes c
               ON c.NombreComercial_Key = s.NombreComercial_Key
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