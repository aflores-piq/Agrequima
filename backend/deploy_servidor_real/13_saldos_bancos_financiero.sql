/* =====================================================================
   PIQ_IA -- dbo.SaldosBancos y dbo.SaldoBancario (módulo Financiero,
   pantallas "Conciliación bancaria" y "Flujo de caja")
   =====================================================================
   dbo.SaldosBancos:
   Fuente real: vw_piq_saldos_bancos.csv (docs/legacy/financiero/), 7
   columnas sin encabezado: ban_codigo, Mes, Año, InicialL, EntradasL,
   SalidasL, FinalL -- es el saldo CONTABLE por banco/mes (columna
   "Saldo Contabilidad" de la conciliación real, NO el saldo que reporta
   el banco). Confirmado contra Agosto 2026: EntradasL/SalidasL cuadran
   exacto (al centavo) contra SUM(Debitos)/SUM(Creditos) de
   dbo.BalanceGeneral para esas mismas cuentas de banco.

   dbo.SaldoBancario:
   Fuente real: SaldoBancario.csv (docs/legacy/financiero/), export
   directo de Agrequima.dbo.SaldoBancario del servidor real
   10.10.0.6,65280 -- columnas Concepto ('Saldo inicial' | 'Creditos' |
   'Debitos'), Anio, Mes, Banco, Valor. Es el saldo que reporta el BANCO
   (columna "Saldo Banco" de la conciliación real), confirmado exacto
   contra los 4 bancos de Agosto 2026 del .pbix.

   Este script solo crea las tablas (idempotente, igual patrón que
   "12_agrupador_cuentas_financiero.sql"). La carga de datos real es
   aparte, vía Python (backend/app/services/cargar_datos_financiero_inicial.py,
   funciones _cargar_saldos_bancos y _cargar_saldo_bancario -- leen los
   CSV y hacen TRUNCATE + INSERT).

   Es seguro volver a correr este script las veces que haga falta: los
   CREATE TABLE están guardados con IF OBJECT_ID(...) IS NULL, no tocan
   la estructura si la tabla ya existe.
   ===================================================================== */

USE PIQ_IA;
GO

IF OBJECT_ID('dbo.SaldosBancos') IS NULL
BEGIN
    CREATE TABLE dbo.SaldosBancos(
        saldobancoid INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        ban_codigo   VARCHAR(50) NULL,
        Sal_Mes      INT NULL,
        Sal_Ano      INT NULL,
        InicialL     DECIMAL(18,2) NULL,
        EntradasL    DECIMAL(18,2) NULL,
        SalidasL     DECIMAL(18,2) NULL,
        FinalL       DECIMAL(18,2) NULL,
        fechamod     DATETIME NULL,
        userid       INT NULL
    );
    PRINT 'Tabla dbo.SaldosBancos creada.';
END
ELSE
    PRINT 'dbo.SaldosBancos ya existía -- no se tocó su estructura.';
GO

IF OBJECT_ID('dbo.stg_SaldosBancos') IS NULL
BEGIN
    CREATE TABLE dbo.stg_SaldosBancos(
        ban_codigo VARCHAR(MAX) NULL,
        Sal_Mes    FLOAT NULL,
        Sal_Ano    FLOAT NULL,
        InicialL   FLOAT NULL,
        EntradasL  FLOAT NULL,
        SalidasL   FLOAT NULL,
        FinalL     FLOAT NULL
    );
    PRINT 'Tabla dbo.stg_SaldosBancos creada.';
END
ELSE
    PRINT 'dbo.stg_SaldosBancos ya existía -- no se tocó su estructura.';
GO

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
        CONSTRAINT PK_SaldoBancario_13 PRIMARY KEY CLUSTERED (SaldoBancarioId ASC)
    );
    PRINT 'Tabla dbo.SaldoBancario creada.';
END
ELSE
    PRINT 'dbo.SaldoBancario ya existía -- no se tocó su estructura.';
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
    PRINT 'Tabla dbo.stg_SaldoBancario creada.';
END
ELSE
    PRINT 'dbo.stg_SaldoBancario ya existía -- no se tocó su estructura.';
GO

SELECT COUNT(*) AS filas_actuales FROM dbo.SaldosBancos;
GO

SELECT COUNT(*) AS filas_actuales FROM dbo.SaldoBancario;
GO

PRINT '=== dbo.SaldosBancos y dbo.SaldoBancario aplicados. Falta correr la carga de datos real (cargar_datos_financiero_inicial.py, funciones _cargar_saldos_bancos y _cargar_saldo_bancario) para que dejen de estar vacías. ===';
GO
