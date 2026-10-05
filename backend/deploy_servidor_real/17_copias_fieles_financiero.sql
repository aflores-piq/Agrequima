/* =====================================================================
   PIQ_IA -- Copias fieles de las vistas/tablas del cliente (módulo Financiero)
   =====================================================================
   Crea, en PIQ_IA, UNA tabla por cada uno de los 10 objetos de origen,
   con el MISMO nombre, los MISMOS campos, en el MISMO orden y con tipos
   equivalentes a los del servidor del cliente (10.10.0.6,65280). Fuente
   de la estructura: docs/legacy/financiero/estructura_vistas_cliente.csv
   (INFORMATION_SCHEMA.COLUMNS del cliente). Sin resúmenes ni
   transformaciones: la sincronización nocturna (sync_financiero.py)
   copia ahí los datos completos tal cual vienen del cliente.

     Base CONTACC  (8): vw_piq_balance_saldos, vw_piq_balance_general,
                        vw_catalogo_cuentas, vw_piq_centrosdecosto,
                        vw_piq_presupuestos, vw_piq_asociados_cuota,
                        vw_piq_cheques_circulacion, vw_piq_saldos_bancos
     Base Agrequima (2): SaldoBancario, OtroIngreso

   dbo.SaldoBancario y dbo.OtroIngreso YA EXISTÍAN en PIQ_IA con otra
   estructura (id autonumérico al principio, columna UsuarioId, textos
   NVARCHAR(50)/(200), campos que aceptaban NULL). Este script las
   reconstruye con la estructura exacta del cliente SIN perder datos:
     1. crea dbo.<tabla>_nueva con la estructura del cliente,
     2. copia todas las filas,
     3. verifica que la cantidad de filas y el contenido sean idénticos
        (si no lo son, revierte todo y no toca nada),
     4. renombra la tabla vieja a dbo.<tabla>_respaldo y la nueva a
        dbo.<tabla>, todo dentro de una transacción.
   La tabla _respaldo se conserva (se puede borrar a mano cuando se
   verifique todo).

   IDEMPOTENTE: se puede correr las veces que haga falta. Crea solo lo que
   falta y NUNCA borra ni modifica datos de una tabla que ya tiene la
   estructura correcta.

   NO toca: las 8 tablas resumidas que lee la web hoy (BalanceSaldos,
   BalanceGeneral, CatalogoCuentas, CentrosDeCosto, Presupuestos,
   AsociadosCuota, ChequesCirculacion, SaldosBancos) -- eso lo hace
   18_vistas_financiero.sql, DESPUÉS de la primera sincronización.

   Conectado con SSMS a VMI1979377\SQLEXPRESS, base PIQ_IA.
   ===================================================================== */

USE PIQ_IA;
GO

SET NOCOUNT ON;
GO

/* ===================== 1. Copias de CONTACC (8) ===================== */
/* ---- dbo.vw_piq_balance_saldos ---- */
DECLARE @firma_real NVARCHAR(MAX) =
    STUFF((
        SELECT N'|' + c.COLUMN_NAME + N' ' + UPPER(c.DATA_TYPE)
             + CASE WHEN c.DATA_TYPE IN ('varchar', 'nvarchar', 'char', 'nchar')
                    THEN N'(' + CASE WHEN c.CHARACTER_MAXIMUM_LENGTH = -1 THEN N'MAX' ELSE CAST(c.CHARACTER_MAXIMUM_LENGTH AS NVARCHAR(10)) END + N')'
                    WHEN c.DATA_TYPE IN ('decimal', 'numeric')
                    THEN N'(' + CAST(c.NUMERIC_PRECISION AS NVARCHAR(5)) + N',' + CAST(c.NUMERIC_SCALE AS NVARCHAR(5)) + N')'
                    ELSE N'' END
             + N' ' + c.IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS c
        WHERE c.TABLE_SCHEMA = 'dbo' AND c.TABLE_NAME = 'vw_piq_balance_saldos'
        ORDER BY c.ORDINAL_POSITION
        FOR XML PATH(''), TYPE).value('.', 'NVARCHAR(MAX)'), 1, 1, N'');
IF OBJECT_ID('dbo.vw_piq_balance_saldos', 'U') IS NOT NULL
   AND ISNULL(@firma_real, N'') <> N'emp_nit VARCHAR(20) NO|Cta_Codigo VARCHAR(20) NO|Cta_Descripcion VARCHAR(100) NO|Sal_Ano SMALLINT NO|Sal_Mes SMALLINT NO|Debitos MONEY YES|Creditos MONEY YES|Saldo MONEY YES|Cod_Centro VARCHAR(20) NO'
BEGIN
    -- Existe una tabla con ese nombre pero con OTRA estructura (p. ej. un espejo viejo):
    -- NO se borra, se aparta con otro nombre y se crea la correcta.
    IF OBJECT_ID('dbo.vw_piq_balance_saldos_previa', 'U') IS NOT NULL
        THROW 50020, 'dbo.vw_piq_balance_saldos tiene otra estructura y ya existe dbo.vw_piq_balance_saldos_previa. No se tocó nada; revisar y renombrar o borrar la _previa a mano.', 1;
    EXEC sp_rename 'dbo.vw_piq_balance_saldos', 'vw_piq_balance_saldos_previa';
    PRINT 'dbo.vw_piq_balance_saldos tenía otra estructura: se renombró a dbo.vw_piq_balance_saldos_previa (sus datos se conservan).';
END
IF OBJECT_ID('dbo.vw_piq_balance_saldos', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.vw_piq_balance_saldos(
        emp_nit         VARCHAR(20) NOT NULL,
        Cta_Codigo      VARCHAR(20) NOT NULL,
        Cta_Descripcion VARCHAR(100) NOT NULL,
        Sal_Ano         SMALLINT NOT NULL,
        Sal_Mes         SMALLINT NOT NULL,
        Debitos         MONEY NULL,
        Creditos        MONEY NULL,
        Saldo           MONEY NULL,
        Cod_Centro      VARCHAR(20) NOT NULL
    );
    PRINT 'Tabla dbo.vw_piq_balance_saldos creada.';
END
ELSE
    PRINT 'dbo.vw_piq_balance_saldos ya tiene la estructura correcta -- no se tocó.';
GO
/* ---- dbo.vw_piq_balance_general ---- */
DECLARE @firma_real NVARCHAR(MAX) =
    STUFF((
        SELECT N'|' + c.COLUMN_NAME + N' ' + UPPER(c.DATA_TYPE)
             + CASE WHEN c.DATA_TYPE IN ('varchar', 'nvarchar', 'char', 'nchar')
                    THEN N'(' + CASE WHEN c.CHARACTER_MAXIMUM_LENGTH = -1 THEN N'MAX' ELSE CAST(c.CHARACTER_MAXIMUM_LENGTH AS NVARCHAR(10)) END + N')'
                    WHEN c.DATA_TYPE IN ('decimal', 'numeric')
                    THEN N'(' + CAST(c.NUMERIC_PRECISION AS NVARCHAR(5)) + N',' + CAST(c.NUMERIC_SCALE AS NVARCHAR(5)) + N')'
                    ELSE N'' END
             + N' ' + c.IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS c
        WHERE c.TABLE_SCHEMA = 'dbo' AND c.TABLE_NAME = 'vw_piq_balance_general'
        ORDER BY c.ORDINAL_POSITION
        FOR XML PATH(''), TYPE).value('.', 'NVARCHAR(MAX)'), 1, 1, N'');
IF OBJECT_ID('dbo.vw_piq_balance_general', 'U') IS NOT NULL
   AND ISNULL(@firma_real, N'') <> N'emp_nit VARCHAR(20) YES|Cod_n1 VARCHAR(20) YES|Nom_n1 VARCHAR(100) YES|cod_n5 VARCHAR(20) YES|nom_n5 VARCHAR(100) YES|Sal_Ano SMALLINT NO|Sal_Mes SMALLINT YES|Debitos MONEY YES|Creditos MONEY YES|Saldo MONEY YES|Inicial INT NO'
BEGIN
    -- Existe una tabla con ese nombre pero con OTRA estructura (p. ej. un espejo viejo):
    -- NO se borra, se aparta con otro nombre y se crea la correcta.
    IF OBJECT_ID('dbo.vw_piq_balance_general_previa', 'U') IS NOT NULL
        THROW 50020, 'dbo.vw_piq_balance_general tiene otra estructura y ya existe dbo.vw_piq_balance_general_previa. No se tocó nada; revisar y renombrar o borrar la _previa a mano.', 1;
    EXEC sp_rename 'dbo.vw_piq_balance_general', 'vw_piq_balance_general_previa';
    PRINT 'dbo.vw_piq_balance_general tenía otra estructura: se renombró a dbo.vw_piq_balance_general_previa (sus datos se conservan).';
END
IF OBJECT_ID('dbo.vw_piq_balance_general', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.vw_piq_balance_general(
        emp_nit  VARCHAR(20) NULL,
        Cod_n1   VARCHAR(20) NULL,
        Nom_n1   VARCHAR(100) NULL,
        cod_n5   VARCHAR(20) NULL,
        nom_n5   VARCHAR(100) NULL,
        Sal_Ano  SMALLINT NOT NULL,
        Sal_Mes  SMALLINT NULL,
        Debitos  MONEY NULL,
        Creditos MONEY NULL,
        Saldo    MONEY NULL,
        Inicial  INT NOT NULL
    );
    PRINT 'Tabla dbo.vw_piq_balance_general creada.';
END
ELSE
    PRINT 'dbo.vw_piq_balance_general ya tiene la estructura correcta -- no se tocó.';
GO
/* ---- dbo.vw_catalogo_cuentas ---- */
DECLARE @firma_real NVARCHAR(MAX) =
    STUFF((
        SELECT N'|' + c.COLUMN_NAME + N' ' + UPPER(c.DATA_TYPE)
             + CASE WHEN c.DATA_TYPE IN ('varchar', 'nvarchar', 'char', 'nchar')
                    THEN N'(' + CASE WHEN c.CHARACTER_MAXIMUM_LENGTH = -1 THEN N'MAX' ELSE CAST(c.CHARACTER_MAXIMUM_LENGTH AS NVARCHAR(10)) END + N')'
                    WHEN c.DATA_TYPE IN ('decimal', 'numeric')
                    THEN N'(' + CAST(c.NUMERIC_PRECISION AS NVARCHAR(5)) + N',' + CAST(c.NUMERIC_SCALE AS NVARCHAR(5)) + N')'
                    ELSE N'' END
             + N' ' + c.IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS c
        WHERE c.TABLE_SCHEMA = 'dbo' AND c.TABLE_NAME = 'vw_catalogo_cuentas'
        ORDER BY c.ORDINAL_POSITION
        FOR XML PATH(''), TYPE).value('.', 'NVARCHAR(MAX)'), 1, 1, N'');
IF OBJECT_ID('dbo.vw_catalogo_cuentas', 'U') IS NOT NULL
   AND ISNULL(@firma_real, N'') <> N'cta_nivel TINYINT YES|Codigo_N1 VARCHAR(20) NO|Nombre_n1 VARCHAR(100) NO|Codigo_N5 VARCHAR(20) YES|Nombre_N5 VARCHAR(100) YES'
BEGIN
    -- Existe una tabla con ese nombre pero con OTRA estructura (p. ej. un espejo viejo):
    -- NO se borra, se aparta con otro nombre y se crea la correcta.
    IF OBJECT_ID('dbo.vw_catalogo_cuentas_previa', 'U') IS NOT NULL
        THROW 50020, 'dbo.vw_catalogo_cuentas tiene otra estructura y ya existe dbo.vw_catalogo_cuentas_previa. No se tocó nada; revisar y renombrar o borrar la _previa a mano.', 1;
    EXEC sp_rename 'dbo.vw_catalogo_cuentas', 'vw_catalogo_cuentas_previa';
    PRINT 'dbo.vw_catalogo_cuentas tenía otra estructura: se renombró a dbo.vw_catalogo_cuentas_previa (sus datos se conservan).';
END
IF OBJECT_ID('dbo.vw_catalogo_cuentas', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.vw_catalogo_cuentas(
        cta_nivel TINYINT NULL,
        Codigo_N1 VARCHAR(20) NOT NULL,
        Nombre_n1 VARCHAR(100) NOT NULL,
        Codigo_N5 VARCHAR(20) NULL,
        Nombre_N5 VARCHAR(100) NULL
    );
    PRINT 'Tabla dbo.vw_catalogo_cuentas creada.';
END
ELSE
    PRINT 'dbo.vw_catalogo_cuentas ya tiene la estructura correcta -- no se tocó.';
GO
/* ---- dbo.vw_piq_centrosdecosto ---- */
DECLARE @firma_real NVARCHAR(MAX) =
    STUFF((
        SELECT N'|' + c.COLUMN_NAME + N' ' + UPPER(c.DATA_TYPE)
             + CASE WHEN c.DATA_TYPE IN ('varchar', 'nvarchar', 'char', 'nchar')
                    THEN N'(' + CASE WHEN c.CHARACTER_MAXIMUM_LENGTH = -1 THEN N'MAX' ELSE CAST(c.CHARACTER_MAXIMUM_LENGTH AS NVARCHAR(10)) END + N')'
                    WHEN c.DATA_TYPE IN ('decimal', 'numeric')
                    THEN N'(' + CAST(c.NUMERIC_PRECISION AS NVARCHAR(5)) + N',' + CAST(c.NUMERIC_SCALE AS NVARCHAR(5)) + N')'
                    ELSE N'' END
             + N' ' + c.IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS c
        WHERE c.TABLE_SCHEMA = 'dbo' AND c.TABLE_NAME = 'vw_piq_centrosdecosto'
        ORDER BY c.ORDINAL_POSITION
        FOR XML PATH(''), TYPE).value('.', 'NVARCHAR(MAX)'), 1, 1, N'');
IF OBJECT_ID('dbo.vw_piq_centrosdecosto', 'U') IS NOT NULL
   AND ISNULL(@firma_real, N'') <> N'emp_nit VARCHAR(20) NO|Cod_centro VARCHAR(20) NO|Des_centro VARCHAR(40) YES|nivel TINYINT YES|CC_Grupo1 VARCHAR(20) YES'
BEGIN
    -- Existe una tabla con ese nombre pero con OTRA estructura (p. ej. un espejo viejo):
    -- NO se borra, se aparta con otro nombre y se crea la correcta.
    IF OBJECT_ID('dbo.vw_piq_centrosdecosto_previa', 'U') IS NOT NULL
        THROW 50020, 'dbo.vw_piq_centrosdecosto tiene otra estructura y ya existe dbo.vw_piq_centrosdecosto_previa. No se tocó nada; revisar y renombrar o borrar la _previa a mano.', 1;
    EXEC sp_rename 'dbo.vw_piq_centrosdecosto', 'vw_piq_centrosdecosto_previa';
    PRINT 'dbo.vw_piq_centrosdecosto tenía otra estructura: se renombró a dbo.vw_piq_centrosdecosto_previa (sus datos se conservan).';
END
IF OBJECT_ID('dbo.vw_piq_centrosdecosto', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.vw_piq_centrosdecosto(
        emp_nit    VARCHAR(20) NOT NULL,
        Cod_centro VARCHAR(20) NOT NULL,
        Des_centro VARCHAR(40) NULL,
        nivel      TINYINT NULL,
        CC_Grupo1  VARCHAR(20) NULL
    );
    PRINT 'Tabla dbo.vw_piq_centrosdecosto creada.';
END
ELSE
    PRINT 'dbo.vw_piq_centrosdecosto ya tiene la estructura correcta -- no se tocó.';
GO
/* ---- dbo.vw_piq_presupuestos ---- */
DECLARE @firma_real NVARCHAR(MAX) =
    STUFF((
        SELECT N'|' + c.COLUMN_NAME + N' ' + UPPER(c.DATA_TYPE)
             + CASE WHEN c.DATA_TYPE IN ('varchar', 'nvarchar', 'char', 'nchar')
                    THEN N'(' + CASE WHEN c.CHARACTER_MAXIMUM_LENGTH = -1 THEN N'MAX' ELSE CAST(c.CHARACTER_MAXIMUM_LENGTH AS NVARCHAR(10)) END + N')'
                    WHEN c.DATA_TYPE IN ('decimal', 'numeric')
                    THEN N'(' + CAST(c.NUMERIC_PRECISION AS NVARCHAR(5)) + N',' + CAST(c.NUMERIC_SCALE AS NVARCHAR(5)) + N')'
                    ELSE N'' END
             + N' ' + c.IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS c
        WHERE c.TABLE_SCHEMA = 'dbo' AND c.TABLE_NAME = 'vw_piq_presupuestos'
        ORDER BY c.ORDINAL_POSITION
        FOR XML PATH(''), TYPE).value('.', 'NVARCHAR(MAX)'), 1, 1, N'');
IF OBJECT_ID('dbo.vw_piq_presupuestos', 'U') IS NOT NULL
   AND ISNULL(@firma_real, N'') <> N'emp_nit VARCHAR(20) NO|par_ano SMALLINT NO|par_mes SMALLINT NO|cta_codigo NVARCHAR(20) NO|pre_presupuesto MONEY YES|cod_centro VARCHAR(20) NO'
BEGIN
    -- Existe una tabla con ese nombre pero con OTRA estructura (p. ej. un espejo viejo):
    -- NO se borra, se aparta con otro nombre y se crea la correcta.
    IF OBJECT_ID('dbo.vw_piq_presupuestos_previa', 'U') IS NOT NULL
        THROW 50020, 'dbo.vw_piq_presupuestos tiene otra estructura y ya existe dbo.vw_piq_presupuestos_previa. No se tocó nada; revisar y renombrar o borrar la _previa a mano.', 1;
    EXEC sp_rename 'dbo.vw_piq_presupuestos', 'vw_piq_presupuestos_previa';
    PRINT 'dbo.vw_piq_presupuestos tenía otra estructura: se renombró a dbo.vw_piq_presupuestos_previa (sus datos se conservan).';
END
IF OBJECT_ID('dbo.vw_piq_presupuestos', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.vw_piq_presupuestos(
        emp_nit         VARCHAR(20) NOT NULL,
        par_ano         SMALLINT NOT NULL,
        par_mes         SMALLINT NOT NULL,
        cta_codigo      NVARCHAR(20) NOT NULL,
        pre_presupuesto MONEY NULL,
        cod_centro      VARCHAR(20) NOT NULL
    );
    PRINT 'Tabla dbo.vw_piq_presupuestos creada.';
END
ELSE
    PRINT 'dbo.vw_piq_presupuestos ya tiene la estructura correcta -- no se tocó.';
GO
/* ---- dbo.vw_piq_asociados_cuota ---- */
DECLARE @firma_real NVARCHAR(MAX) =
    STUFF((
        SELECT N'|' + c.COLUMN_NAME + N' ' + UPPER(c.DATA_TYPE)
             + CASE WHEN c.DATA_TYPE IN ('varchar', 'nvarchar', 'char', 'nchar')
                    THEN N'(' + CASE WHEN c.CHARACTER_MAXIMUM_LENGTH = -1 THEN N'MAX' ELSE CAST(c.CHARACTER_MAXIMUM_LENGTH AS NVARCHAR(10)) END + N')'
                    WHEN c.DATA_TYPE IN ('decimal', 'numeric')
                    THEN N'(' + CAST(c.NUMERIC_PRECISION AS NVARCHAR(5)) + N',' + CAST(c.NUMERIC_SCALE AS NVARCHAR(5)) + N')'
                    ELSE N'' END
             + N' ' + c.IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS c
        WHERE c.TABLE_SCHEMA = 'dbo' AND c.TABLE_NAME = 'vw_piq_asociados_cuota'
        ORDER BY c.ORDINAL_POSITION
        FOR XML PATH(''), TYPE).value('.', 'NVARCHAR(MAX)'), 1, 1, N'');
IF OBJECT_ID('dbo.vw_piq_asociados_cuota', 'U') IS NOT NULL
   AND ISNULL(@firma_real, N'') <> N'emp_nit VARCHAR(20) YES|Sal_Ano SMALLINT NO|cod_n5 VARCHAR(20) YES|nom_n5 VARCHAR(100) YES|grupo VARCHAR(1) YES|nombre_mostrar VARCHAR(25) YES|cuota MONEY YES'
BEGIN
    -- Existe una tabla con ese nombre pero con OTRA estructura (p. ej. un espejo viejo):
    -- NO se borra, se aparta con otro nombre y se crea la correcta.
    IF OBJECT_ID('dbo.vw_piq_asociados_cuota_previa', 'U') IS NOT NULL
        THROW 50020, 'dbo.vw_piq_asociados_cuota tiene otra estructura y ya existe dbo.vw_piq_asociados_cuota_previa. No se tocó nada; revisar y renombrar o borrar la _previa a mano.', 1;
    EXEC sp_rename 'dbo.vw_piq_asociados_cuota', 'vw_piq_asociados_cuota_previa';
    PRINT 'dbo.vw_piq_asociados_cuota tenía otra estructura: se renombró a dbo.vw_piq_asociados_cuota_previa (sus datos se conservan).';
END
IF OBJECT_ID('dbo.vw_piq_asociados_cuota', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.vw_piq_asociados_cuota(
        emp_nit        VARCHAR(20) NULL,
        Sal_Ano        SMALLINT NOT NULL,
        cod_n5         VARCHAR(20) NULL,
        nom_n5         VARCHAR(100) NULL,
        grupo          VARCHAR(1) NULL,
        nombre_mostrar VARCHAR(25) NULL,
        cuota          MONEY NULL
    );
    PRINT 'Tabla dbo.vw_piq_asociados_cuota creada.';
END
ELSE
    PRINT 'dbo.vw_piq_asociados_cuota ya tiene la estructura correcta -- no se tocó.';
GO
/* ---- dbo.vw_piq_cheques_circulacion ---- */
DECLARE @firma_real NVARCHAR(MAX) =
    STUFF((
        SELECT N'|' + c.COLUMN_NAME + N' ' + UPPER(c.DATA_TYPE)
             + CASE WHEN c.DATA_TYPE IN ('varchar', 'nvarchar', 'char', 'nchar')
                    THEN N'(' + CASE WHEN c.CHARACTER_MAXIMUM_LENGTH = -1 THEN N'MAX' ELSE CAST(c.CHARACTER_MAXIMUM_LENGTH AS NVARCHAR(10)) END + N')'
                    WHEN c.DATA_TYPE IN ('decimal', 'numeric')
                    THEN N'(' + CAST(c.NUMERIC_PRECISION AS NVARCHAR(5)) + N',' + CAST(c.NUMERIC_SCALE AS NVARCHAR(5)) + N')'
                    ELSE N'' END
             + N' ' + c.IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS c
        WHERE c.TABLE_SCHEMA = 'dbo' AND c.TABLE_NAME = 'vw_piq_cheques_circulacion'
        ORDER BY c.ORDINAL_POSITION
        FOR XML PATH(''), TYPE).value('.', 'NVARCHAR(MAX)'), 1, 1, N'');
IF OBJECT_ID('dbo.vw_piq_cheques_circulacion', 'U') IS NOT NULL
   AND ISNULL(@firma_real, N'') <> N'ban_codigo VARCHAR(10) NO|cta_numero VARCHAR(30) YES|cta_nombre VARCHAR(50) YES|Cta_Codigo VARCHAR(20) YES|par_ano SMALLINT NO|par_mes SMALLINT NO|doc_numero VARCHAR(20) NO|doc_fecha DATETIME YES|doc_fchcobro DATETIME YES|doc_nombre VARCHAR(100) YES|doc_motivo VARCHAR(250) NO|doc_monto MONEY YES'
BEGIN
    -- Existe una tabla con ese nombre pero con OTRA estructura (p. ej. un espejo viejo):
    -- NO se borra, se aparta con otro nombre y se crea la correcta.
    IF OBJECT_ID('dbo.vw_piq_cheques_circulacion_previa', 'U') IS NOT NULL
        THROW 50020, 'dbo.vw_piq_cheques_circulacion tiene otra estructura y ya existe dbo.vw_piq_cheques_circulacion_previa. No se tocó nada; revisar y renombrar o borrar la _previa a mano.', 1;
    EXEC sp_rename 'dbo.vw_piq_cheques_circulacion', 'vw_piq_cheques_circulacion_previa';
    PRINT 'dbo.vw_piq_cheques_circulacion tenía otra estructura: se renombró a dbo.vw_piq_cheques_circulacion_previa (sus datos se conservan).';
END
IF OBJECT_ID('dbo.vw_piq_cheques_circulacion', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.vw_piq_cheques_circulacion(
        ban_codigo   VARCHAR(10) NOT NULL,
        cta_numero   VARCHAR(30) NULL,
        cta_nombre   VARCHAR(50) NULL,
        Cta_Codigo   VARCHAR(20) NULL,
        par_ano      SMALLINT NOT NULL,
        par_mes      SMALLINT NOT NULL,
        doc_numero   VARCHAR(20) NOT NULL,
        doc_fecha    DATETIME NULL,
        doc_fchcobro DATETIME NULL,
        doc_nombre   VARCHAR(100) NULL,
        doc_motivo   VARCHAR(250) NOT NULL,
        doc_monto    MONEY NULL
    );
    PRINT 'Tabla dbo.vw_piq_cheques_circulacion creada.';
END
ELSE
    PRINT 'dbo.vw_piq_cheques_circulacion ya tiene la estructura correcta -- no se tocó.';
GO
/* ---- dbo.vw_piq_saldos_bancos ---- */
DECLARE @firma_real NVARCHAR(MAX) =
    STUFF((
        SELECT N'|' + c.COLUMN_NAME + N' ' + UPPER(c.DATA_TYPE)
             + CASE WHEN c.DATA_TYPE IN ('varchar', 'nvarchar', 'char', 'nchar')
                    THEN N'(' + CASE WHEN c.CHARACTER_MAXIMUM_LENGTH = -1 THEN N'MAX' ELSE CAST(c.CHARACTER_MAXIMUM_LENGTH AS NVARCHAR(10)) END + N')'
                    WHEN c.DATA_TYPE IN ('decimal', 'numeric')
                    THEN N'(' + CAST(c.NUMERIC_PRECISION AS NVARCHAR(5)) + N',' + CAST(c.NUMERIC_SCALE AS NVARCHAR(5)) + N')'
                    ELSE N'' END
             + N' ' + c.IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS c
        WHERE c.TABLE_SCHEMA = 'dbo' AND c.TABLE_NAME = 'vw_piq_saldos_bancos'
        ORDER BY c.ORDINAL_POSITION
        FOR XML PATH(''), TYPE).value('.', 'NVARCHAR(MAX)'), 1, 1, N'');
IF OBJECT_ID('dbo.vw_piq_saldos_bancos', 'U') IS NOT NULL
   AND ISNULL(@firma_real, N'') <> N'ban_codigo VARCHAR(10) NO|Sal_Mes INT NO|Sal_Ano INT NO|InicialL MONEY YES|EntradasL MONEY YES|SalidasL MONEY YES|FinalL MONEY YES'
BEGIN
    -- Existe una tabla con ese nombre pero con OTRA estructura (p. ej. un espejo viejo):
    -- NO se borra, se aparta con otro nombre y se crea la correcta.
    IF OBJECT_ID('dbo.vw_piq_saldos_bancos_previa', 'U') IS NOT NULL
        THROW 50020, 'dbo.vw_piq_saldos_bancos tiene otra estructura y ya existe dbo.vw_piq_saldos_bancos_previa. No se tocó nada; revisar y renombrar o borrar la _previa a mano.', 1;
    EXEC sp_rename 'dbo.vw_piq_saldos_bancos', 'vw_piq_saldos_bancos_previa';
    PRINT 'dbo.vw_piq_saldos_bancos tenía otra estructura: se renombró a dbo.vw_piq_saldos_bancos_previa (sus datos se conservan).';
END
IF OBJECT_ID('dbo.vw_piq_saldos_bancos', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.vw_piq_saldos_bancos(
        ban_codigo VARCHAR(10) NOT NULL,
        Sal_Mes    INT NOT NULL,
        Sal_Ano    INT NOT NULL,
        InicialL   MONEY NULL,
        EntradasL  MONEY NULL,
        SalidasL   MONEY NULL,
        FinalL     MONEY NULL
    );
    PRINT 'Tabla dbo.vw_piq_saldos_bancos creada.';
END
ELSE
    PRINT 'dbo.vw_piq_saldos_bancos ya tiene la estructura correcta -- no se tocó.';
GO
/* ============ 2. Copias de Agrequima (2) -- ya existían: se migran ============ */
/* ---- dbo.SaldoBancario: migración a la estructura del cliente (sin perder datos) ---- */
DECLARE @firma_real NVARCHAR(MAX) =
    STUFF((
        SELECT N'|' + c.COLUMN_NAME + N' ' + UPPER(c.DATA_TYPE)
             + CASE WHEN c.DATA_TYPE IN ('varchar', 'nvarchar', 'char', 'nchar')
                    THEN N'(' + CASE WHEN c.CHARACTER_MAXIMUM_LENGTH = -1 THEN N'MAX' ELSE CAST(c.CHARACTER_MAXIMUM_LENGTH AS NVARCHAR(10)) END + N')'
                    WHEN c.DATA_TYPE IN ('decimal', 'numeric')
                    THEN N'(' + CAST(c.NUMERIC_PRECISION AS NVARCHAR(5)) + N',' + CAST(c.NUMERIC_SCALE AS NVARCHAR(5)) + N')'
                    ELSE N'' END
             + N' ' + c.IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS c
        WHERE c.TABLE_SCHEMA = 'dbo' AND c.TABLE_NAME = 'SaldoBancario'
        ORDER BY c.ORDINAL_POSITION
        FOR XML PATH(''), TYPE).value('.', 'NVARCHAR(MAX)'), 1, 1, N'');
IF OBJECT_ID('dbo.SaldoBancario', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.SaldoBancario(
        concepto VARCHAR(100) NOT NULL,
        anio     INT NOT NULL,
        mes      INT NOT NULL,
        banco    VARCHAR(100) NOT NULL,
        valor    DECIMAL(18,2) NULL,
        userid   INT NULL,
        fechamod DATETIME NULL
    );
    PRINT 'Tabla dbo.SaldoBancario creada (no existía).';
END
ELSE IF COL_LENGTH('dbo.SaldoBancario', 'SaldoBancarioId') IS NULL
BEGIN
    IF ISNULL(@firma_real, N'') <> N'concepto VARCHAR(100) NO|anio INT NO|mes INT NO|banco VARCHAR(100) NO|valor DECIMAL(18,2) YES|userid INT YES|fechamod DATETIME YES'
        THROW 50005, 'dbo.SaldoBancario no tiene ni la estructura vieja de la app ni la del cliente. No se tocó nada; revisarla a mano.', 1;
    PRINT 'dbo.SaldoBancario ya tiene la estructura del cliente -- no se tocó.';
END
ELSE
BEGIN
    -- Se ejecuta como SQL dinámico: así SQL Server solo compila las columnas viejas
    -- (UsuarioId, SaldoBancarioId...) cuando de verdad hace falta migrar; si la tabla ya
    -- tiene la estructura nueva, este bloque ni se compila y el script sigue siendo idempotente.
    DECLARE @migracion NVARCHAR(MAX) = N'    SET XACT_ABORT ON;
    BEGIN TRY
        IF OBJECT_ID(''dbo.SaldoBancario_respaldo'', ''U'') IS NOT NULL
            THROW 50001, ''Ya existe dbo.SaldoBancario_respaldo (de una migración anterior). Revisarla y renombrarla o borrarla a mano antes de reintentar; no se tocó nada.'', 1;

        IF EXISTS (SELECT 1 FROM dbo.SaldoBancario WHERE Anio IS NULL OR Mes IS NULL)
            THROW 50002, ''dbo.SaldoBancario tiene filas con NULL en campos que la estructura del cliente no acepta nulos (año/mes). No se tocó nada; revisar esas filas.'', 1;

        BEGIN TRANSACTION;

        IF OBJECT_ID(''dbo.SaldoBancario_nueva'', ''U'') IS NOT NULL DROP TABLE dbo.SaldoBancario_nueva;
        CREATE TABLE dbo.SaldoBancario_nueva(
        concepto VARCHAR(100) NOT NULL,
        anio     INT NOT NULL,
        mes      INT NOT NULL,
        banco    VARCHAR(100) NOT NULL,
        valor    DECIMAL(18,2) NULL,
        userid   INT NULL,
        fechamod DATETIME NULL
        );

        INSERT INTO dbo.SaldoBancario_nueva (concepto, anio, mes, banco, valor, userid, fechamod)
        SELECT ISNULL(Concepto, N''''), Anio, Mes, ISNULL(Banco, N''''), Valor, UsuarioId, FechaMod
        FROM dbo.SaldoBancario;

        -- Verificación ANTES de tocar nada: misma cantidad de filas y mismo contenido.
        IF (SELECT COUNT(*) FROM dbo.SaldoBancario) <> (SELECT COUNT(*) FROM dbo.SaldoBancario_nueva)
            THROW 50003, ''La copia migrada no tiene la misma cantidad de filas que la tabla original. Se revirtió todo; no se perdió nada.'', 1;

        IF EXISTS (
            SELECT ISNULL(Concepto, N''''), Anio, Mes, ISNULL(Banco, N''''), Valor, UsuarioId, FechaMod FROM dbo.SaldoBancario
            EXCEPT
            SELECT CAST(concepto AS NVARCHAR(100)), anio, mes, CAST(banco AS NVARCHAR(100)), valor, userid, fechamod FROM dbo.SaldoBancario_nueva
        ) OR EXISTS (
            SELECT CAST(concepto AS NVARCHAR(100)), anio, mes, CAST(banco AS NVARCHAR(100)), valor, userid, fechamod FROM dbo.SaldoBancario_nueva
            EXCEPT
            SELECT ISNULL(Concepto, N''''), Anio, Mes, ISNULL(Banco, N''''), Valor, UsuarioId, FechaMod FROM dbo.SaldoBancario
        )
            THROW 50004, ''El contenido de la copia migrada no coincide con la tabla original (¿caracteres que no entran en VARCHAR?). Se revirtió todo; no se perdió nada.'', 1;

        EXEC sp_rename ''dbo.SaldoBancario'', ''SaldoBancario_respaldo'';
        EXEC sp_rename ''dbo.SaldoBancario_nueva'', ''SaldoBancario'';

        COMMIT TRANSACTION;
        PRINT ''dbo.SaldoBancario migrada a la estructura del cliente. La tabla anterior quedó como dbo.SaldoBancario_respaldo (se puede borrar cuando se verifique todo).'';
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
';
    EXEC sp_executesql @migracion;
END
GO
/* ---- dbo.OtroIngreso: migración a la estructura del cliente (sin perder datos) ---- */
DECLARE @firma_real NVARCHAR(MAX) =
    STUFF((
        SELECT N'|' + c.COLUMN_NAME + N' ' + UPPER(c.DATA_TYPE)
             + CASE WHEN c.DATA_TYPE IN ('varchar', 'nvarchar', 'char', 'nchar')
                    THEN N'(' + CASE WHEN c.CHARACTER_MAXIMUM_LENGTH = -1 THEN N'MAX' ELSE CAST(c.CHARACTER_MAXIMUM_LENGTH AS NVARCHAR(10)) END + N')'
                    WHEN c.DATA_TYPE IN ('decimal', 'numeric')
                    THEN N'(' + CAST(c.NUMERIC_PRECISION AS NVARCHAR(5)) + N',' + CAST(c.NUMERIC_SCALE AS NVARCHAR(5)) + N')'
                    ELSE N'' END
             + N' ' + c.IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS c
        WHERE c.TABLE_SCHEMA = 'dbo' AND c.TABLE_NAME = 'OtroIngreso'
        ORDER BY c.ORDINAL_POSITION
        FOR XML PATH(''), TYPE).value('.', 'NVARCHAR(MAX)'), 1, 1, N'');
IF OBJECT_ID('dbo.OtroIngreso', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.OtroIngreso(
        tipo     VARCHAR(100) NOT NULL,
        concepto VARCHAR(150) NOT NULL,
        anio     INT NOT NULL,
        mes      INT NOT NULL,
        valor    DECIMAL(18,2) NULL,
        userid   INT NULL,
        fechamod DATETIME NULL
    );
    PRINT 'Tabla dbo.OtroIngreso creada (no existía).';
END
ELSE IF COL_LENGTH('dbo.OtroIngreso', 'OtroIngresoId') IS NULL
BEGIN
    IF ISNULL(@firma_real, N'') <> N'tipo VARCHAR(100) NO|concepto VARCHAR(150) NO|anio INT NO|mes INT NO|valor DECIMAL(18,2) YES|userid INT YES|fechamod DATETIME YES'
        THROW 50005, 'dbo.OtroIngreso no tiene ni la estructura vieja de la app ni la del cliente. No se tocó nada; revisarla a mano.', 1;
    PRINT 'dbo.OtroIngreso ya tiene la estructura del cliente -- no se tocó.';
END
ELSE
BEGIN
    -- Se ejecuta como SQL dinámico: así SQL Server solo compila las columnas viejas
    -- (UsuarioId, SaldoBancarioId...) cuando de verdad hace falta migrar; si la tabla ya
    -- tiene la estructura nueva, este bloque ni se compila y el script sigue siendo idempotente.
    DECLARE @migracion NVARCHAR(MAX) = N'    SET XACT_ABORT ON;
    BEGIN TRY
        IF OBJECT_ID(''dbo.OtroIngreso_respaldo'', ''U'') IS NOT NULL
            THROW 50001, ''Ya existe dbo.OtroIngreso_respaldo (de una migración anterior). Revisarla y renombrarla o borrarla a mano antes de reintentar; no se tocó nada.'', 1;

        IF EXISTS (SELECT 1 FROM dbo.OtroIngreso WHERE Anio IS NULL OR Mes IS NULL)
            THROW 50002, ''dbo.OtroIngreso tiene filas con NULL en campos que la estructura del cliente no acepta nulos (año/mes). No se tocó nada; revisar esas filas.'', 1;

        BEGIN TRANSACTION;

        IF OBJECT_ID(''dbo.OtroIngreso_nueva'', ''U'') IS NOT NULL DROP TABLE dbo.OtroIngreso_nueva;
        CREATE TABLE dbo.OtroIngreso_nueva(
        tipo     VARCHAR(100) NOT NULL,
        concepto VARCHAR(150) NOT NULL,
        anio     INT NOT NULL,
        mes      INT NOT NULL,
        valor    DECIMAL(18,2) NULL,
        userid   INT NULL,
        fechamod DATETIME NULL
        );

        INSERT INTO dbo.OtroIngreso_nueva (tipo, concepto, anio, mes, valor, userid, fechamod)
        SELECT ISNULL(Tipo, N''''), ISNULL(Concepto, N''''), Anio, Mes, Valor, UsuarioId, FechaMod
        FROM dbo.OtroIngreso;

        -- Verificación ANTES de tocar nada: misma cantidad de filas y mismo contenido.
        IF (SELECT COUNT(*) FROM dbo.OtroIngreso) <> (SELECT COUNT(*) FROM dbo.OtroIngreso_nueva)
            THROW 50003, ''La copia migrada no tiene la misma cantidad de filas que la tabla original. Se revirtió todo; no se perdió nada.'', 1;

        IF EXISTS (
            SELECT ISNULL(Tipo, N''''), ISNULL(Concepto, N''''), Anio, Mes, Valor, UsuarioId, FechaMod FROM dbo.OtroIngreso
            EXCEPT
            SELECT CAST(tipo AS NVARCHAR(100)), CAST(concepto AS NVARCHAR(150)), anio, mes, valor, userid, fechamod FROM dbo.OtroIngreso_nueva
        ) OR EXISTS (
            SELECT CAST(tipo AS NVARCHAR(100)), CAST(concepto AS NVARCHAR(150)), anio, mes, valor, userid, fechamod FROM dbo.OtroIngreso_nueva
            EXCEPT
            SELECT ISNULL(Tipo, N''''), ISNULL(Concepto, N''''), Anio, Mes, Valor, UsuarioId, FechaMod FROM dbo.OtroIngreso
        )
            THROW 50004, ''El contenido de la copia migrada no coincide con la tabla original (¿caracteres que no entran en VARCHAR?). Se revirtió todo; no se perdió nada.'', 1;

        EXEC sp_rename ''dbo.OtroIngreso'', ''OtroIngreso_respaldo'';
        EXEC sp_rename ''dbo.OtroIngreso_nueva'', ''OtroIngreso'';

        COMMIT TRANSACTION;
        PRINT ''dbo.OtroIngreso migrada a la estructura del cliente. La tabla anterior quedó como dbo.OtroIngreso_respaldo (se puede borrar cuando se verifique todo).'';
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
';
    EXEC sp_executesql @migracion;
END
GO
/* ======= 3. Índices (hacen que las vistas de 18_vistas_financiero.sql lean más rápido
   que las tablas resumidas actuales: medido, la suma de los 14 endpoints del Financiero
   baja ~30%). Son índices agrupados por año/mes, que es como filtra la web. Idempotentes. ======= */
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('dbo.vw_piq_balance_saldos') AND name = 'IX_vw_piq_balance_saldos')
BEGIN
    CREATE CLUSTERED INDEX IX_vw_piq_balance_saldos ON dbo.vw_piq_balance_saldos (Sal_Ano, Sal_Mes);
    PRINT 'Índice IX_vw_piq_balance_saldos creado.';
END
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('dbo.vw_piq_balance_general') AND name = 'IX_vw_piq_balance_general')
BEGIN
    CREATE CLUSTERED INDEX IX_vw_piq_balance_general ON dbo.vw_piq_balance_general (Sal_Ano, Sal_Mes);
    PRINT 'Índice IX_vw_piq_balance_general creado.';
END
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('dbo.vw_piq_presupuestos') AND name = 'IX_vw_piq_presupuestos')
BEGIN
    CREATE CLUSTERED INDEX IX_vw_piq_presupuestos ON dbo.vw_piq_presupuestos (par_ano, par_mes);
    PRINT 'Índice IX_vw_piq_presupuestos creado.';
END
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('dbo.vw_piq_cheques_circulacion') AND name = 'IX_vw_piq_cheques_circulacion')
BEGIN
    CREATE CLUSTERED INDEX IX_vw_piq_cheques_circulacion ON dbo.vw_piq_cheques_circulacion (par_ano, par_mes);
    PRINT 'Índice IX_vw_piq_cheques_circulacion creado.';
END
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('dbo.vw_piq_saldos_bancos') AND name = 'IX_vw_piq_saldos_bancos')
BEGIN
    CREATE CLUSTERED INDEX IX_vw_piq_saldos_bancos ON dbo.vw_piq_saldos_bancos (Sal_Ano, Sal_Mes);
    PRINT 'Índice IX_vw_piq_saldos_bancos creado.';
END
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('dbo.vw_piq_asociados_cuota') AND name = 'IX_vw_piq_asociados_cuota')
BEGIN
    CREATE CLUSTERED INDEX IX_vw_piq_asociados_cuota ON dbo.vw_piq_asociados_cuota (Sal_Ano);
    PRINT 'Índice IX_vw_piq_asociados_cuota creado.';
END
GO
/* ===================== 4. Verificación ===================== */
-- Cada objeto debe mostrar estado = OK (mismos campos, tipos, nulabilidad y orden que el cliente).
SELECT e.objeto,
       e.campos_esperados,
       (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS c
         WHERE c.TABLE_SCHEMA = 'dbo' AND c.TABLE_NAME = e.objeto) AS campos_en_PIQ_IA,
       CASE WHEN ISNULL(f.firma, N'') = e.firma_esperada THEN 'OK' ELSE 'REVISAR' END AS estado
FROM (VALUES
        (N'vw_piq_balance_saldos', 9, N'emp_nit VARCHAR(20) NO|Cta_Codigo VARCHAR(20) NO|Cta_Descripcion VARCHAR(100) NO|Sal_Ano SMALLINT NO|Sal_Mes SMALLINT NO|Debitos MONEY YES|Creditos MONEY YES|Saldo MONEY YES|Cod_Centro VARCHAR(20) NO'),
        (N'vw_piq_balance_general', 11, N'emp_nit VARCHAR(20) YES|Cod_n1 VARCHAR(20) YES|Nom_n1 VARCHAR(100) YES|cod_n5 VARCHAR(20) YES|nom_n5 VARCHAR(100) YES|Sal_Ano SMALLINT NO|Sal_Mes SMALLINT YES|Debitos MONEY YES|Creditos MONEY YES|Saldo MONEY YES|Inicial INT NO'),
        (N'vw_catalogo_cuentas', 5, N'cta_nivel TINYINT YES|Codigo_N1 VARCHAR(20) NO|Nombre_n1 VARCHAR(100) NO|Codigo_N5 VARCHAR(20) YES|Nombre_N5 VARCHAR(100) YES'),
        (N'vw_piq_centrosdecosto', 5, N'emp_nit VARCHAR(20) NO|Cod_centro VARCHAR(20) NO|Des_centro VARCHAR(40) YES|nivel TINYINT YES|CC_Grupo1 VARCHAR(20) YES'),
        (N'vw_piq_presupuestos', 6, N'emp_nit VARCHAR(20) NO|par_ano SMALLINT NO|par_mes SMALLINT NO|cta_codigo NVARCHAR(20) NO|pre_presupuesto MONEY YES|cod_centro VARCHAR(20) NO'),
        (N'vw_piq_asociados_cuota', 7, N'emp_nit VARCHAR(20) YES|Sal_Ano SMALLINT NO|cod_n5 VARCHAR(20) YES|nom_n5 VARCHAR(100) YES|grupo VARCHAR(1) YES|nombre_mostrar VARCHAR(25) YES|cuota MONEY YES'),
        (N'vw_piq_cheques_circulacion', 12, N'ban_codigo VARCHAR(10) NO|cta_numero VARCHAR(30) YES|cta_nombre VARCHAR(50) YES|Cta_Codigo VARCHAR(20) YES|par_ano SMALLINT NO|par_mes SMALLINT NO|doc_numero VARCHAR(20) NO|doc_fecha DATETIME YES|doc_fchcobro DATETIME YES|doc_nombre VARCHAR(100) YES|doc_motivo VARCHAR(250) NO|doc_monto MONEY YES'),
        (N'vw_piq_saldos_bancos', 7, N'ban_codigo VARCHAR(10) NO|Sal_Mes INT NO|Sal_Ano INT NO|InicialL MONEY YES|EntradasL MONEY YES|SalidasL MONEY YES|FinalL MONEY YES'),
        (N'SaldoBancario', 7, N'concepto VARCHAR(100) NO|anio INT NO|mes INT NO|banco VARCHAR(100) NO|valor DECIMAL(18,2) YES|userid INT YES|fechamod DATETIME YES'),
        (N'OtroIngreso', 7, N'tipo VARCHAR(100) NO|concepto VARCHAR(150) NO|anio INT NO|mes INT NO|valor DECIMAL(18,2) YES|userid INT YES|fechamod DATETIME YES')
) AS e(objeto, campos_esperados, firma_esperada)
CROSS APPLY (
    SELECT
        STUFF((
            SELECT N'|' + c.COLUMN_NAME + N' ' + UPPER(c.DATA_TYPE)
                 + CASE WHEN c.DATA_TYPE IN ('varchar', 'nvarchar', 'char', 'nchar')
                        THEN N'(' + CASE WHEN c.CHARACTER_MAXIMUM_LENGTH = -1 THEN N'MAX' ELSE CAST(c.CHARACTER_MAXIMUM_LENGTH AS NVARCHAR(10)) END + N')'
                        WHEN c.DATA_TYPE IN ('decimal', 'numeric')
                        THEN N'(' + CAST(c.NUMERIC_PRECISION AS NVARCHAR(5)) + N',' + CAST(c.NUMERIC_SCALE AS NVARCHAR(5)) + N')'
                        ELSE N'' END
                 + N' ' + c.IS_NULLABLE
            FROM INFORMATION_SCHEMA.COLUMNS c
            WHERE c.TABLE_SCHEMA = 'dbo' AND c.TABLE_NAME = e.objeto
            ORDER BY c.ORDINAL_POSITION
            FOR XML PATH(''), TYPE).value('.', 'NVARCHAR(MAX)'), 1, 1, N'') AS firma
) AS f
ORDER BY e.objeto;
GO

PRINT '=== 17_copias_fieles_financiero.sql aplicado. Siguiente paso: primera sincronización (correr_sync_financiero.ps1). ===';
GO
