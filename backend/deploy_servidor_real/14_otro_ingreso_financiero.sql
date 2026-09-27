/* =====================================================================
   PIQ_IA -- dbo.OtroIngreso (módulo Financiero, pantalla "Otros ingresos
   generados")
   =====================================================================
   Fuente real: OtroIngreso.csv (docs/legacy/financiero/), export
   directo de Agrequima.dbo.OtroIngreso del servidor real 10.10.0.6 --
   columnas Tipo ('Ejecutado' | 'Presupuesto'), Concepto, Anio, Mes,
   Valor. Los valores son ACUMULADOS (no se suman meses, ver
   dashboard_otro_ingreso.py) -- confirmado exacto contra los 13 números
   de control (12 conceptos + Total) del .pbix real, Año 2026.

   Este script solo crea las tablas (idempotente, igual patrón que
   "13_saldos_bancos_financiero.sql"). La carga de datos real es aparte,
   vía Python (backend/app/services/cargar_datos_financiero_inicial.py,
   función _cargar_otro_ingreso -- lee el CSV y hace TRUNCATE + INSERT).

   Es seguro volver a correr este script las veces que haga falta: los
   CREATE TABLE están guardados con IF OBJECT_ID(...) IS NULL, no tocan
   la estructura si la tabla ya existe (confirmado que dbo.OtroIngreso YA
   EXISTE en la base de desarrollo con esta misma estructura -- este
   script es por si el servidor real todavía no la tiene).
   ===================================================================== */

USE PIQ_IA;
GO

IF OBJECT_ID('dbo.OtroIngreso') IS NULL
BEGIN
    CREATE TABLE dbo.OtroIngreso(
        OtroIngresoId INT IDENTITY(1,1) NOT NULL,
        Tipo          NVARCHAR(50) NULL,      -- 'Ejecutado' | 'Presupuesto'
        Concepto      NVARCHAR(200) NULL,
        Anio          INT NULL,
        Mes           INT NULL,
        Valor         DECIMAL(18,2) NULL,
        UsuarioId     INT NULL,
        FechaMod      DATETIME NOT NULL DEFAULT GETDATE(),
        CONSTRAINT PK_OtroIngreso_14 PRIMARY KEY CLUSTERED (OtroIngresoId ASC)
    );
    PRINT 'Tabla dbo.OtroIngreso creada.';
END
ELSE
    PRINT 'dbo.OtroIngreso ya existía -- no se tocó su estructura.';
GO

IF OBJECT_ID('dbo.stg_OtroIngreso') IS NULL
BEGIN
    CREATE TABLE dbo.stg_OtroIngreso(
        Tipo     VARCHAR(MAX) NULL,
        Concepto VARCHAR(MAX) NULL,
        Anio     FLOAT NULL,
        Mes      FLOAT NULL,
        Valor    FLOAT NULL
    );
    PRINT 'Tabla dbo.stg_OtroIngreso creada.';
END
ELSE
    PRINT 'dbo.stg_OtroIngreso ya existía -- no se tocó su estructura.';
GO

SELECT COUNT(*) AS filas_actuales FROM dbo.OtroIngreso;
GO

PRINT '=== dbo.OtroIngreso aplicado. Falta correr la carga de datos real (cargar_datos_financiero_inicial.py, función _cargar_otro_ingreso) para que deje de estar vacía. ===';
GO
