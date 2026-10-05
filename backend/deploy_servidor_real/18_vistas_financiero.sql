/* =====================================================================
   PIQ_IA -- Las tablas resumidas que lee la web pasan a ser VISTAS
   =====================================================================
   Hasta ahora la web leía 8 tablas resumidas (BalanceSaldos,
   BalanceGeneral, CatalogoCuentas, CentrosDeCosto, Presupuestos,
   AsociadosCuota, ChequesCirculacion, SaldosBancos) cargadas a mano desde
   CSV. Este script:
     1. renombra cada una a dbo.<nombre>_respaldo (NO borra nada), y
     2. crea una VISTA con el nombre original y las mismas columnas de
        datos que la web usa, calculada sobre las copias fieles que llena
        la sincronización nocturna (17_copias_fieles_financiero.sql +
        sync_financiero.py), con la misma lógica que aplicaba el cargador
        manual:
          - texto vacío -> NULL;
          - Sal_Ano / Sal_Mes / par_ano / par_mes / nivel / cta_nivel -> INT;
          - importes (money) -> DECIMAL(18,2); BalanceGeneral.Inicial -> DECIMAL(18,2);
          - SaldosBancos: se suman las filas repetidas de un mismo
            banco/mes/año (BANRURAL trae 3 por período);
          - Presupuestos.cta_codigo: NVARCHAR(20) -> VARCHAR(20).
     El código de la web NO cambia (sigue leyendo dbo.BalanceSaldos, etc.).
     Las vistas no incluyen el id autonumérico, fechamod ni userid de las
     tablas viejas: ningún código de la app los usa.

   Todo en UNA transacción: si algo falla, no se renombra ni se crea nada.
   IDEMPOTENTE: si una de las 8 ya es una vista, no la renombra y solo la
   vuelve a crear (CREATE OR ALTER).

   REQUISITO: haber corrido 17_copias_fieles_financiero.sql y haber hecho la
   primera sincronización (correr_sync_financiero.ps1), con las 8 copias
   fieles ya con datos. Si falta alguna copia, el script se detiene sin
   tocar nada.

   Las tablas dbo.<nombre>_respaldo se conservan; se pueden borrar a mano
   cuando se verifique todo. Al final del archivo (comentado) está cómo
   volver atrás.
   ===================================================================== */

USE PIQ_IA;
GO

SET NOCOUNT ON;
GO

BEGIN TRY
    SET XACT_ABORT ON;
    BEGIN TRANSACTION;

    /* ---- 1. Las 8 copias fieles tienen que existir ---- */
    IF OBJECT_ID('dbo.vw_piq_balance_saldos', 'U') IS NULL
        THROW 50010, 'Falta la copia fiel dbo.vw_piq_balance_saldos. Correr primero 17_copias_fieles_financiero.sql y la primera sincronizacion.', 1;
    IF OBJECT_ID('dbo.vw_piq_balance_general', 'U') IS NULL
        THROW 50010, 'Falta la copia fiel dbo.vw_piq_balance_general. Correr primero 17_copias_fieles_financiero.sql y la primera sincronizacion.', 1;
    IF OBJECT_ID('dbo.vw_catalogo_cuentas', 'U') IS NULL
        THROW 50010, 'Falta la copia fiel dbo.vw_catalogo_cuentas. Correr primero 17_copias_fieles_financiero.sql y la primera sincronizacion.', 1;
    IF OBJECT_ID('dbo.vw_piq_centrosdecosto', 'U') IS NULL
        THROW 50010, 'Falta la copia fiel dbo.vw_piq_centrosdecosto. Correr primero 17_copias_fieles_financiero.sql y la primera sincronizacion.', 1;
    IF OBJECT_ID('dbo.vw_piq_presupuestos', 'U') IS NULL
        THROW 50010, 'Falta la copia fiel dbo.vw_piq_presupuestos. Correr primero 17_copias_fieles_financiero.sql y la primera sincronizacion.', 1;
    IF OBJECT_ID('dbo.vw_piq_asociados_cuota', 'U') IS NULL
        THROW 50010, 'Falta la copia fiel dbo.vw_piq_asociados_cuota. Correr primero 17_copias_fieles_financiero.sql y la primera sincronizacion.', 1;
    IF OBJECT_ID('dbo.vw_piq_cheques_circulacion', 'U') IS NULL
        THROW 50010, 'Falta la copia fiel dbo.vw_piq_cheques_circulacion. Correr primero 17_copias_fieles_financiero.sql y la primera sincronizacion.', 1;
    IF OBJECT_ID('dbo.vw_piq_saldos_bancos', 'U') IS NULL
        THROW 50010, 'Falta la copia fiel dbo.vw_piq_saldos_bancos. Correr primero 17_copias_fieles_financiero.sql y la primera sincronizacion.', 1;

    /* ---- 2. Por cada tabla resumida: respaldo + vista ---- */
    -- dbo.BalanceSaldos
    IF OBJECT_ID('dbo.BalanceSaldos', 'U') IS NOT NULL
    BEGIN
        IF OBJECT_ID('dbo.BalanceSaldos_respaldo', 'U') IS NOT NULL
            THROW 50011, 'dbo.BalanceSaldos sigue siendo una tabla y ya existe dbo.BalanceSaldos_respaldo. No se toco nada; revisar y renombrar o borrar el respaldo viejo a mano.', 1;
        EXEC sp_rename 'dbo.BalanceSaldos', 'BalanceSaldos_respaldo';
        PRINT 'dbo.BalanceSaldos (tabla) renombrada a dbo.BalanceSaldos_respaldo.';
    END
    EXEC(N'CREATE OR ALTER VIEW dbo.BalanceSaldos AS
    SELECT CASE WHEN DATALENGTH(emp_nit) = 0 THEN NULL ELSE emp_nit END AS emp_nit,
           CASE WHEN DATALENGTH(Cta_Codigo) = 0 THEN NULL ELSE Cta_Codigo END AS Cta_Codigo,
           CASE WHEN DATALENGTH(Cta_Descripcion) = 0 THEN NULL ELSE Cta_Descripcion END AS Cta_Descripcion,
           CAST(Sal_Ano AS INT) AS Sal_Ano,
           CAST(Sal_Mes AS INT) AS Sal_Mes,
           CAST(Debitos AS DECIMAL(18,2)) AS Debitos,
           CAST(Creditos AS DECIMAL(18,2)) AS Creditos,
           CAST(Saldo AS DECIMAL(18,2)) AS Saldo,
           CASE WHEN DATALENGTH(Cod_Centro) = 0 THEN NULL ELSE Cod_Centro END AS Cod_Centro
    FROM dbo.vw_piq_balance_saldos');
    PRINT 'Vista dbo.BalanceSaldos creada sobre dbo.vw_piq_balance_saldos.';

    -- dbo.BalanceGeneral
    IF OBJECT_ID('dbo.BalanceGeneral', 'U') IS NOT NULL
    BEGIN
        IF OBJECT_ID('dbo.BalanceGeneral_respaldo', 'U') IS NOT NULL
            THROW 50011, 'dbo.BalanceGeneral sigue siendo una tabla y ya existe dbo.BalanceGeneral_respaldo. No se toco nada; revisar y renombrar o borrar el respaldo viejo a mano.', 1;
        EXEC sp_rename 'dbo.BalanceGeneral', 'BalanceGeneral_respaldo';
        PRINT 'dbo.BalanceGeneral (tabla) renombrada a dbo.BalanceGeneral_respaldo.';
    END
    EXEC(N'CREATE OR ALTER VIEW dbo.BalanceGeneral AS
    SELECT CASE WHEN DATALENGTH(emp_nit) = 0 THEN NULL ELSE emp_nit END AS emp_nit,
           CASE WHEN DATALENGTH(Cod_n1) = 0 THEN NULL ELSE Cod_n1 END AS Cod_n1,
           CASE WHEN DATALENGTH(Nom_n1) = 0 THEN NULL ELSE Nom_n1 END AS Nom_n1,
           CASE WHEN DATALENGTH(cod_n5) = 0 THEN NULL ELSE cod_n5 END AS cod_n5,
           CASE WHEN DATALENGTH(nom_n5) = 0 THEN NULL ELSE nom_n5 END AS nom_n5,
           CAST(Sal_Ano AS INT) AS Sal_Ano,
           CAST(Sal_Mes AS INT) AS Sal_Mes,
           CAST(Debitos AS DECIMAL(18,2)) AS Debitos,
           CAST(Creditos AS DECIMAL(18,2)) AS Creditos,
           CAST(Saldo AS DECIMAL(18,2)) AS Saldo,
           CAST(Inicial AS DECIMAL(18,2)) AS Inicial
    FROM dbo.vw_piq_balance_general');
    PRINT 'Vista dbo.BalanceGeneral creada sobre dbo.vw_piq_balance_general.';

    -- dbo.CatalogoCuentas
    IF OBJECT_ID('dbo.CatalogoCuentas', 'U') IS NOT NULL
    BEGIN
        IF OBJECT_ID('dbo.CatalogoCuentas_respaldo', 'U') IS NOT NULL
            THROW 50011, 'dbo.CatalogoCuentas sigue siendo una tabla y ya existe dbo.CatalogoCuentas_respaldo. No se toco nada; revisar y renombrar o borrar el respaldo viejo a mano.', 1;
        EXEC sp_rename 'dbo.CatalogoCuentas', 'CatalogoCuentas_respaldo';
        PRINT 'dbo.CatalogoCuentas (tabla) renombrada a dbo.CatalogoCuentas_respaldo.';
    END
    EXEC(N'CREATE OR ALTER VIEW dbo.CatalogoCuentas AS
    SELECT CAST(cta_nivel AS INT) AS cta_nivel,
           CASE WHEN DATALENGTH(Codigo_N1) = 0 THEN NULL ELSE Codigo_N1 END AS Codigo_N1,
           CASE WHEN DATALENGTH(Nombre_n1) = 0 THEN NULL ELSE Nombre_n1 END AS Nombre_n1,
           CASE WHEN DATALENGTH(Codigo_N5) = 0 THEN NULL ELSE Codigo_N5 END AS Codigo_N5,
           CASE WHEN DATALENGTH(Nombre_N5) = 0 THEN NULL ELSE Nombre_N5 END AS Nombre_N5
    FROM dbo.vw_catalogo_cuentas');
    PRINT 'Vista dbo.CatalogoCuentas creada sobre dbo.vw_catalogo_cuentas.';

    -- dbo.CentrosDeCosto
    IF OBJECT_ID('dbo.CentrosDeCosto', 'U') IS NOT NULL
    BEGIN
        IF OBJECT_ID('dbo.CentrosDeCosto_respaldo', 'U') IS NOT NULL
            THROW 50011, 'dbo.CentrosDeCosto sigue siendo una tabla y ya existe dbo.CentrosDeCosto_respaldo. No se toco nada; revisar y renombrar o borrar el respaldo viejo a mano.', 1;
        EXEC sp_rename 'dbo.CentrosDeCosto', 'CentrosDeCosto_respaldo';
        PRINT 'dbo.CentrosDeCosto (tabla) renombrada a dbo.CentrosDeCosto_respaldo.';
    END
    EXEC(N'CREATE OR ALTER VIEW dbo.CentrosDeCosto AS
    SELECT CASE WHEN DATALENGTH(emp_nit) = 0 THEN NULL ELSE emp_nit END AS emp_nit,
           CASE WHEN DATALENGTH(Cod_centro) = 0 THEN NULL ELSE Cod_centro END AS Cod_centro,
           CASE WHEN DATALENGTH(Des_centro) = 0 THEN NULL ELSE Des_centro END AS Des_centro,
           CAST(nivel AS INT) AS nivel,
           CASE WHEN DATALENGTH(CC_Grupo1) = 0 THEN NULL ELSE CC_Grupo1 END AS CC_Grupo1
    FROM dbo.vw_piq_centrosdecosto');
    PRINT 'Vista dbo.CentrosDeCosto creada sobre dbo.vw_piq_centrosdecosto.';

    -- dbo.Presupuestos
    IF OBJECT_ID('dbo.Presupuestos', 'U') IS NOT NULL
    BEGIN
        IF OBJECT_ID('dbo.Presupuestos_respaldo', 'U') IS NOT NULL
            THROW 50011, 'dbo.Presupuestos sigue siendo una tabla y ya existe dbo.Presupuestos_respaldo. No se toco nada; revisar y renombrar o borrar el respaldo viejo a mano.', 1;
        EXEC sp_rename 'dbo.Presupuestos', 'Presupuestos_respaldo';
        PRINT 'dbo.Presupuestos (tabla) renombrada a dbo.Presupuestos_respaldo.';
    END
    EXEC(N'CREATE OR ALTER VIEW dbo.Presupuestos AS
    SELECT CASE WHEN DATALENGTH(emp_nit) = 0 THEN NULL ELSE emp_nit END AS emp_nit,
           CAST(par_ano AS INT) AS par_ano,
           CAST(par_mes AS INT) AS par_mes,
           CAST(CASE WHEN DATALENGTH(cta_codigo) = 0 THEN NULL ELSE cta_codigo END AS VARCHAR(20)) AS cta_codigo,
           CAST(pre_presupuesto AS DECIMAL(18,2)) AS pre_presupuesto,
           CASE WHEN DATALENGTH(cod_centro) = 0 THEN NULL ELSE cod_centro END AS cod_centro
    FROM dbo.vw_piq_presupuestos');
    PRINT 'Vista dbo.Presupuestos creada sobre dbo.vw_piq_presupuestos.';

    -- dbo.AsociadosCuota
    IF OBJECT_ID('dbo.AsociadosCuota', 'U') IS NOT NULL
    BEGIN
        IF OBJECT_ID('dbo.AsociadosCuota_respaldo', 'U') IS NOT NULL
            THROW 50011, 'dbo.AsociadosCuota sigue siendo una tabla y ya existe dbo.AsociadosCuota_respaldo. No se toco nada; revisar y renombrar o borrar el respaldo viejo a mano.', 1;
        EXEC sp_rename 'dbo.AsociadosCuota', 'AsociadosCuota_respaldo';
        PRINT 'dbo.AsociadosCuota (tabla) renombrada a dbo.AsociadosCuota_respaldo.';
    END
    EXEC(N'CREATE OR ALTER VIEW dbo.AsociadosCuota AS
    SELECT CASE WHEN DATALENGTH(emp_nit) = 0 THEN NULL ELSE emp_nit END AS emp_nit,
           CAST(Sal_Ano AS INT) AS Sal_Ano,
           CASE WHEN DATALENGTH(cod_n5) = 0 THEN NULL ELSE cod_n5 END AS cod_n5,
           CASE WHEN DATALENGTH(nom_n5) = 0 THEN NULL ELSE nom_n5 END AS nom_n5,
           CASE WHEN DATALENGTH(grupo) = 0 THEN NULL ELSE grupo END AS grupo,
           CASE WHEN DATALENGTH(nombre_mostrar) = 0 THEN NULL ELSE nombre_mostrar END AS nombre_mostrar,
           CAST(cuota AS DECIMAL(18,2)) AS cuota
    FROM dbo.vw_piq_asociados_cuota');
    PRINT 'Vista dbo.AsociadosCuota creada sobre dbo.vw_piq_asociados_cuota.';

    -- dbo.ChequesCirculacion
    IF OBJECT_ID('dbo.ChequesCirculacion', 'U') IS NOT NULL
    BEGIN
        IF OBJECT_ID('dbo.ChequesCirculacion_respaldo', 'U') IS NOT NULL
            THROW 50011, 'dbo.ChequesCirculacion sigue siendo una tabla y ya existe dbo.ChequesCirculacion_respaldo. No se toco nada; revisar y renombrar o borrar el respaldo viejo a mano.', 1;
        EXEC sp_rename 'dbo.ChequesCirculacion', 'ChequesCirculacion_respaldo';
        PRINT 'dbo.ChequesCirculacion (tabla) renombrada a dbo.ChequesCirculacion_respaldo.';
    END
    EXEC(N'CREATE OR ALTER VIEW dbo.ChequesCirculacion AS
    SELECT CASE WHEN DATALENGTH(ban_codigo) = 0 THEN NULL ELSE ban_codigo END AS ban_codigo,
           CASE WHEN DATALENGTH(cta_numero) = 0 THEN NULL ELSE cta_numero END AS cta_numero,
           CASE WHEN DATALENGTH(cta_nombre) = 0 THEN NULL ELSE cta_nombre END AS cta_nombre,
           CASE WHEN DATALENGTH(Cta_Codigo) = 0 THEN NULL ELSE Cta_Codigo END AS Cta_Codigo,
           CAST(par_ano AS INT) AS par_ano,
           CAST(par_mes AS INT) AS par_mes,
           CASE WHEN DATALENGTH(doc_numero) = 0 THEN NULL ELSE doc_numero END AS doc_numero,
           doc_fecha,
           doc_fchcobro,
           CASE WHEN DATALENGTH(doc_nombre) = 0 THEN NULL ELSE doc_nombre END AS doc_nombre,
           CASE WHEN DATALENGTH(doc_motivo) = 0 THEN NULL ELSE doc_motivo END AS doc_motivo,
           CAST(doc_monto AS DECIMAL(18,2)) AS doc_monto
    FROM dbo.vw_piq_cheques_circulacion');
    PRINT 'Vista dbo.ChequesCirculacion creada sobre dbo.vw_piq_cheques_circulacion.';

    -- dbo.SaldosBancos
    IF OBJECT_ID('dbo.SaldosBancos', 'U') IS NOT NULL
    BEGIN
        IF OBJECT_ID('dbo.SaldosBancos_respaldo', 'U') IS NOT NULL
            THROW 50011, 'dbo.SaldosBancos sigue siendo una tabla y ya existe dbo.SaldosBancos_respaldo. No se toco nada; revisar y renombrar o borrar el respaldo viejo a mano.', 1;
        EXEC sp_rename 'dbo.SaldosBancos', 'SaldosBancos_respaldo';
        PRINT 'dbo.SaldosBancos (tabla) renombrada a dbo.SaldosBancos_respaldo.';
    END
    EXEC(N'CREATE OR ALTER VIEW dbo.SaldosBancos AS
    SELECT ban_codigo,
           CAST(Sal_Mes AS INT) AS Sal_Mes,
           CAST(Sal_Ano AS INT) AS Sal_Ano,
           CAST(SUM(ISNULL(InicialL, 0)) AS DECIMAL(18,2)) AS InicialL,
           CAST(SUM(ISNULL(EntradasL, 0)) AS DECIMAL(18,2)) AS EntradasL,
           CAST(SUM(ISNULL(SalidasL, 0)) AS DECIMAL(18,2)) AS SalidasL,
           CAST(SUM(ISNULL(FinalL, 0)) AS DECIMAL(18,2)) AS FinalL
    FROM dbo.vw_piq_saldos_bancos
    GROUP BY ban_codigo, Sal_Mes, Sal_Ano');
    PRINT 'Vista dbo.SaldosBancos creada sobre dbo.vw_piq_saldos_bancos.';

    COMMIT TRANSACTION;
    PRINT '=== Las 8 vistas quedaron creadas. ===';
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    PRINT 'ERROR -- se revirtio todo, no se cambio nada: ' + ERROR_MESSAGE();
    THROW;
END CATCH
GO

/* ---- 3. Verificación ----
   filas_vista debe ser > 0 en las 8. filas_respaldo es la tabla vieja (puede
   diferir un poco si los datos del cliente cambiaron desde la última carga
   manual). filas_copia_fiel = filas_vista en todas salvo SaldosBancos, que
   se resume (un banco/mes/año por fila). */
SELECT v.vista,
       (SELECT SUM(p.rows) FROM sys.partitions p WHERE p.object_id = OBJECT_ID('dbo.' + v.vista + '_respaldo') AND p.index_id IN (0, 1)) AS filas_respaldo,
       v.filas_vista,
       v.filas_copia_fiel
FROM (
    SELECT 'BalanceSaldos' AS vista, (SELECT COUNT(*) FROM dbo.BalanceSaldos) AS filas_vista, (SELECT COUNT(*) FROM dbo.vw_piq_balance_saldos) AS filas_copia_fiel
    UNION ALL
    SELECT 'BalanceGeneral' AS vista, (SELECT COUNT(*) FROM dbo.BalanceGeneral) AS filas_vista, (SELECT COUNT(*) FROM dbo.vw_piq_balance_general) AS filas_copia_fiel
    UNION ALL
    SELECT 'CatalogoCuentas' AS vista, (SELECT COUNT(*) FROM dbo.CatalogoCuentas) AS filas_vista, (SELECT COUNT(*) FROM dbo.vw_catalogo_cuentas) AS filas_copia_fiel
    UNION ALL
    SELECT 'CentrosDeCosto' AS vista, (SELECT COUNT(*) FROM dbo.CentrosDeCosto) AS filas_vista, (SELECT COUNT(*) FROM dbo.vw_piq_centrosdecosto) AS filas_copia_fiel
    UNION ALL
    SELECT 'Presupuestos' AS vista, (SELECT COUNT(*) FROM dbo.Presupuestos) AS filas_vista, (SELECT COUNT(*) FROM dbo.vw_piq_presupuestos) AS filas_copia_fiel
    UNION ALL
    SELECT 'AsociadosCuota' AS vista, (SELECT COUNT(*) FROM dbo.AsociadosCuota) AS filas_vista, (SELECT COUNT(*) FROM dbo.vw_piq_asociados_cuota) AS filas_copia_fiel
    UNION ALL
    SELECT 'ChequesCirculacion' AS vista, (SELECT COUNT(*) FROM dbo.ChequesCirculacion) AS filas_vista, (SELECT COUNT(*) FROM dbo.vw_piq_cheques_circulacion) AS filas_copia_fiel
    UNION ALL
    SELECT 'SaldosBancos' AS vista, (SELECT COUNT(*) FROM dbo.SaldosBancos) AS filas_vista, (SELECT COUNT(*) FROM dbo.vw_piq_saldos_bancos) AS filas_copia_fiel
) AS v
ORDER BY v.vista;
GO

/* =====================================================================
   COMO VOLVER ATRAS (descomentar y correr SOLO si hace falta)
   Borra las 8 vistas y devuelve las tablas resumidas originales.
   No toca las copias fieles ni la sincronizacion.
   =====================================================================
BEGIN TRY
    SET XACT_ABORT ON;
    BEGIN TRANSACTION;
    IF OBJECT_ID('dbo.BalanceSaldos', 'V') IS NOT NULL AND OBJECT_ID('dbo.BalanceSaldos_respaldo', 'U') IS NOT NULL
    BEGIN
        DROP VIEW dbo.BalanceSaldos;
        EXEC sp_rename 'dbo.BalanceSaldos_respaldo', 'BalanceSaldos';
    END
    IF OBJECT_ID('dbo.BalanceGeneral', 'V') IS NOT NULL AND OBJECT_ID('dbo.BalanceGeneral_respaldo', 'U') IS NOT NULL
    BEGIN
        DROP VIEW dbo.BalanceGeneral;
        EXEC sp_rename 'dbo.BalanceGeneral_respaldo', 'BalanceGeneral';
    END
    IF OBJECT_ID('dbo.CatalogoCuentas', 'V') IS NOT NULL AND OBJECT_ID('dbo.CatalogoCuentas_respaldo', 'U') IS NOT NULL
    BEGIN
        DROP VIEW dbo.CatalogoCuentas;
        EXEC sp_rename 'dbo.CatalogoCuentas_respaldo', 'CatalogoCuentas';
    END
    IF OBJECT_ID('dbo.CentrosDeCosto', 'V') IS NOT NULL AND OBJECT_ID('dbo.CentrosDeCosto_respaldo', 'U') IS NOT NULL
    BEGIN
        DROP VIEW dbo.CentrosDeCosto;
        EXEC sp_rename 'dbo.CentrosDeCosto_respaldo', 'CentrosDeCosto';
    END
    IF OBJECT_ID('dbo.Presupuestos', 'V') IS NOT NULL AND OBJECT_ID('dbo.Presupuestos_respaldo', 'U') IS NOT NULL
    BEGIN
        DROP VIEW dbo.Presupuestos;
        EXEC sp_rename 'dbo.Presupuestos_respaldo', 'Presupuestos';
    END
    IF OBJECT_ID('dbo.AsociadosCuota', 'V') IS NOT NULL AND OBJECT_ID('dbo.AsociadosCuota_respaldo', 'U') IS NOT NULL
    BEGIN
        DROP VIEW dbo.AsociadosCuota;
        EXEC sp_rename 'dbo.AsociadosCuota_respaldo', 'AsociadosCuota';
    END
    IF OBJECT_ID('dbo.ChequesCirculacion', 'V') IS NOT NULL AND OBJECT_ID('dbo.ChequesCirculacion_respaldo', 'U') IS NOT NULL
    BEGIN
        DROP VIEW dbo.ChequesCirculacion;
        EXEC sp_rename 'dbo.ChequesCirculacion_respaldo', 'ChequesCirculacion';
    END
    IF OBJECT_ID('dbo.SaldosBancos', 'V') IS NOT NULL AND OBJECT_ID('dbo.SaldosBancos_respaldo', 'U') IS NOT NULL
    BEGIN
        DROP VIEW dbo.SaldosBancos;
        EXEC sp_rename 'dbo.SaldosBancos_respaldo', 'SaldosBancos';
    END
    COMMIT TRANSACTION;
    PRINT 'Listo: las 8 tablas resumidas originales volvieron a su nombre.';
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH
   ===================================================================== */
