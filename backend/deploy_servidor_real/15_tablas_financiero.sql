/* =====================================================================
   PIQ_IA -- 7 tablas de Financiero que todavía no tenían script de
   despliegue propio (BalanceSaldos, BalanceGeneral, CatalogoCuentas,
   CentrosDeCosto, Presupuestos, AsociadosCuota, ChequesCirculacion).
   =====================================================================
   Las otras 3 tablas de Financiero (SaldosBancos, SaldoBancario,
   OtroIngreso) ya tenían su script propio (13_saldos_bancos_financiero.sql
   y 14_otro_ingreso_financiero.sql) -- este script completa las 10 que
   usa `cargar_datos_financiero_inicial.py`.

   Definiciones copiadas EXACTAS de db/agrequima_schema_sql_server.sql
   (el esquema maestro de desarrollo), mismo patrón idempotente que
   "13_saldos_bancos_financiero.sql"/"14_otro_ingreso_financiero.sql":
   CREATE TABLE solo si no existe, no toca la estructura si ya está.
   No hay índices ni claves foráneas adicionales más allá de la PK
   propia de cada tabla -- confirmado por grep contra el esquema maestro
   (sin ningún CREATE INDEX en ese archivo).

   Este script solo crea las tablas, vacías. La carga de datos real es
   aparte: "16_datos_financiero.sql" (o "16a_..."/"16b_..." si hace
   falta partirlo), o a mano vía
   backend/app/services/cargar_datos_financiero_inicial.py.

   Es seguro volver a correr este script las veces que haga falta: cada
   CREATE TABLE está guardado con IF OBJECT_ID(...) IS NULL.
   ===================================================================== */

USE PIQ_IA;
GO

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
    PRINT 'Tabla dbo.BalanceSaldos creada.';
END
ELSE
    PRINT 'dbo.BalanceSaldos ya existía -- no se tocó su estructura.';
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
    PRINT 'Tabla dbo.stg_BalanceSaldos creada.';
END
ELSE
    PRINT 'dbo.stg_BalanceSaldos ya existía -- no se tocó su estructura.';
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
    PRINT 'Tabla dbo.BalanceGeneral creada.';
END
ELSE
    PRINT 'dbo.BalanceGeneral ya existía -- no se tocó su estructura.';
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
    PRINT 'Tabla dbo.stg_BalanceGeneral creada.';
END
ELSE
    PRINT 'dbo.stg_BalanceGeneral ya existía -- no se tocó su estructura.';
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
    PRINT 'Tabla dbo.CatalogoCuentas creada.';
END
ELSE
    PRINT 'dbo.CatalogoCuentas ya existía -- no se tocó su estructura.';
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
    PRINT 'Tabla dbo.stg_CatalogoCuentas creada.';
END
ELSE
    PRINT 'dbo.stg_CatalogoCuentas ya existía -- no se tocó su estructura.';
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
    PRINT 'Tabla dbo.CentrosDeCosto creada.';
END
ELSE
    PRINT 'dbo.CentrosDeCosto ya existía -- no se tocó su estructura.';
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
    PRINT 'Tabla dbo.stg_CentrosDeCosto creada.';
END
ELSE
    PRINT 'dbo.stg_CentrosDeCosto ya existía -- no se tocó su estructura.';
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
    PRINT 'Tabla dbo.Presupuestos creada.';
END
ELSE
    PRINT 'dbo.Presupuestos ya existía -- no se tocó su estructura.';
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
    PRINT 'Tabla dbo.stg_Presupuestos creada.';
END
ELSE
    PRINT 'dbo.stg_Presupuestos ya existía -- no se tocó su estructura.';
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
    PRINT 'Tabla dbo.AsociadosCuota creada.';
END
ELSE
    PRINT 'dbo.AsociadosCuota ya existía -- no se tocó su estructura.';
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
    PRINT 'Tabla dbo.stg_AsociadosCuota creada.';
END
ELSE
    PRINT 'dbo.stg_AsociadosCuota ya existía -- no se tocó su estructura.';
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
    PRINT 'Tabla dbo.ChequesCirculacion creada.';
END
ELSE
    PRINT 'dbo.ChequesCirculacion ya existía -- no se tocó su estructura.';
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
    PRINT 'Tabla dbo.stg_ChequesCirculacion creada.';
END
ELSE
    PRINT 'dbo.stg_ChequesCirculacion ya existía -- no se tocó su estructura.';
GO

SELECT 'BalanceSaldos' AS tabla, COUNT(*) AS filas_actuales FROM dbo.BalanceSaldos
UNION ALL SELECT 'BalanceGeneral', COUNT(*) FROM dbo.BalanceGeneral
UNION ALL SELECT 'CatalogoCuentas', COUNT(*) FROM dbo.CatalogoCuentas
UNION ALL SELECT 'CentrosDeCosto', COUNT(*) FROM dbo.CentrosDeCosto
UNION ALL SELECT 'Presupuestos', COUNT(*) FROM dbo.Presupuestos
UNION ALL SELECT 'AsociadosCuota', COUNT(*) FROM dbo.AsociadosCuota
UNION ALL SELECT 'ChequesCirculacion', COUNT(*) FROM dbo.ChequesCirculacion;
GO

PRINT '=== Las 7 tablas de Financiero sin script propio quedaron aplicadas. Junto con 13_saldos_bancos_financiero.sql y 14_otro_ingreso_financiero.sql, las 10 tablas que usa cargar_datos_financiero_inicial.py ya existen en PIQ_IA. Falta cargar los datos reales -- ver 16_datos_financiero.sql. ===';
GO
