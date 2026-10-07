/* =====================================================================
   PIQ_IA -- dbo.CatalogoBancos (módulo Financiero, pantallas
   "Conciliación bancaria" y "Flujo de caja")
   =====================================================================
   QUÉ ES
   La lista de bancos de esas dos pantallas SALE DE LOS DATOS (unión de
   dbo.SaldosBancos, dbo.ChequesCirculacion y dbo.SaldoBancario). Esta
   tabla NO decide qué bancos existen: solo dice CÓMO SE VE cada uno
   (nombre en cada pantalla, color, orden) y permite ocultar uno.

   - Un banco que aparece en los datos y NO está en esta tabla se muestra
     igual, con sus datos, con su código como nombre, en gris #9E9E9E y
     al final de la lista.
   - Para darle nombre/color/orden a un banco nuevo basta UN INSERT (o un
     UPDATE si ya está), sin tocar código ni volver a publicar. Se ve al
     recargar la pantalla. Ejemplo:

         INSERT INTO dbo.CatalogoBancos (ban_codigo, nombre_conciliacion, nombre_flujo, color_hex, orden)
         VALUES (N'BANCO NUEVO', N'BANCO NUEVO', N'Banco Nuevo', '#7B1FA2', 50);

         UPDATE dbo.CatalogoBancos SET color_hex = '#7B1FA2' WHERE ban_codigo = N'BANCO NUEVO';

   COLUMNAS
     ban_codigo           Código del banco tal como viene en SaldosBancos /
                          ChequesCirculacion (se compara SIN mayúsculas, SIN
                          tildes y SIN espacios ni caracteres invisibles:
                          PROMÉRICA, Promerica y "PROMERICA " son el mismo).
     nombre_conciliacion  Nombre que se ve en Conciliación bancaria.
                          NULL = se usa el código.
     nombre_flujo         Nombre que se ve en Flujo de caja (distinto en el
                          reporte original: "BAC" vs "BAC Reformador").
                          NULL = se usa el código.
     color_hex            Color de la franja en Conciliación, formato
                          '#RRGGBB'. NULL = gris #9E9E9E.
     orden                Posición en Conciliación (menor = más arriba).
                          NULL = después de los que tienen orden.
     orden_flujo          Posición en Flujo de caja. NULL = usa "orden".
                          (Existe porque el reporte original ordena distinto
                          los bancos en cada pantalla.)
     activo               1 = se muestra. 0 = se oculta el banco en ambas
                          pantallas (y no suma en los totales), aunque tenga
                          datos. Sirve para retirar un banco que ya no se usa.
     alias_saldo_bancario Cómo se llama el banco en dbo.SaldoBancario (el
                          Excel de Saldos bancarios) cuando NO coincide con
                          ban_codigo. Se compara igual de normalizado.

   SEMBRADO
   Los 4 bancos de hoy, con sus nombres, colores y órdenes actuales, para
   que las pantallas se vean EXACTAMENTE igual que antes.

   Es seguro volver a correr este script las veces que haga falta: la
   tabla solo se crea si no existe y cada banco sembrado solo se inserta si
   no está (no pisa lo que se haya cambiado a mano).
   ===================================================================== */

USE PIQ_IA;
GO

IF OBJECT_ID('dbo.CatalogoBancos') IS NULL
BEGIN
    CREATE TABLE dbo.CatalogoBancos(
        catalogobancoid      INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_CatalogoBancos PRIMARY KEY,
        ban_codigo           NVARCHAR(50)  NOT NULL CONSTRAINT UQ_CatalogoBancos_ban_codigo UNIQUE,
        nombre_conciliacion  NVARCHAR(100) NULL,
        nombre_flujo         NVARCHAR(100) NULL,
        color_hex            VARCHAR(7)    NULL,
        orden                INT           NULL,
        orden_flujo          INT           NULL,
        activo               BIT           NOT NULL CONSTRAINT DF_CatalogoBancos_activo DEFAULT 1,
        alias_saldo_bancario NVARCHAR(100) NULL,
        fechamod             DATETIME      NOT NULL CONSTRAINT DF_CatalogoBancos_fechamod DEFAULT GETDATE(),
        CONSTRAINT CK_CatalogoBancos_color CHECK (
            color_hex IS NULL OR color_hex LIKE '#[0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f]')
    );
    PRINT 'Tabla dbo.CatalogoBancos creada.';
END
ELSE
    PRINT 'dbo.CatalogoBancos ya existía -- no se tocó su estructura.';
GO

/* Las tildes se arman con NCHAR (201 = É) para que el script no dependa
   de la codificación del archivo. */
DECLARE @promerica NVARCHAR(50) = N'PROM' + NCHAR(201) + N'RICA';

IF NOT EXISTS (SELECT 1 FROM dbo.CatalogoBancos WHERE ban_codigo = N'BANCOR')
    INSERT INTO dbo.CatalogoBancos (ban_codigo, nombre_conciliacion, nombre_flujo, color_hex, orden, orden_flujo, activo, alias_saldo_bancario)
    VALUES (N'BANCOR', N'BAC', N'BAC Reformador', '#E4002B', 1, 3, 1, N'BANCOR');

IF NOT EXISTS (SELECT 1 FROM dbo.CatalogoBancos WHERE ban_codigo = N'BANRURAL')
    INSERT INTO dbo.CatalogoBancos (ban_codigo, nombre_conciliacion, nombre_flujo, color_hex, orden, orden_flujo, activo, alias_saldo_bancario)
    VALUES (N'BANRURAL', N'BANRURAL', N'Banrural', '#365E3E', 2, 1, 1, N'BANRURAL');

IF NOT EXISTS (SELECT 1 FROM dbo.CatalogoBancos WHERE ban_codigo = N'BI')
    INSERT INTO dbo.CatalogoBancos (ban_codigo, nombre_conciliacion, nombre_flujo, color_hex, orden, orden_flujo, activo, alias_saldo_bancario)
    VALUES (N'BI', N'BI', N'Banco Industrial', '#003865', 3, 2, 1, N'BI');

IF NOT EXISTS (SELECT 1 FROM dbo.CatalogoBancos WHERE ban_codigo = @promerica)
    INSERT INTO dbo.CatalogoBancos (ban_codigo, nombre_conciliacion, nombre_flujo, color_hex, orden, orden_flujo, activo, alias_saldo_bancario)
    VALUES (@promerica, @promerica, N'Promerica', '#00693C', 4, 4, 1, N'PROMERICA');
GO

PRINT 'dbo.CatalogoBancos lista. Filas actuales:';
SELECT ban_codigo, nombre_conciliacion, nombre_flujo, color_hex, orden, orden_flujo, activo, alias_saldo_bancario
FROM dbo.CatalogoBancos
ORDER BY ISNULL(orden, 2147483647), ban_codigo;
GO
