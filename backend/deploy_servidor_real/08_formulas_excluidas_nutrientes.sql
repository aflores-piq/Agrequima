/* =====================================================================
   PIQ_IA -- Exclusión por fórmula/componente completa (Mancozeb,
   Propamocarbhydrocloride) en Nutrientes
   =====================================================================
   El cliente confirmó (WhatsApp) que quiere excluir de Nutrientes
   CUALQUIER producto cuya fórmula/componente contenga "Mancozeb" o
   "Propamocarbhydrocloride" -- no solo el producto puntual que ya
   estaba marcado (ARKO 80 WP), sino TODOS los productos que compartan
   esas fórmulas (el widget "Fórmulas/Componentes ordenado por CIF USD"
   seguía mostrando esas fórmulas porque decenas de otros productos
   comerciales legítimos también las usan como ingrediente, y la
   exclusión hasta ahora era por producto puntual, no por fórmula).

   Qué hace:
     1. Crea dbo.FormulasExcluidasNutrientes -- catálogo de fórmulas a
        excluir. Trae "Mancozeb" y "Propamocarbhydrocloride" ya
        cargadas. Agregar una fórmula nueva en el futuro es un INSERT
        en esta tabla, no un cambio de código ni de este script.
     2. Backfill: marca Excluido=1 en dbo.Nutrientes para TODAS las
        filas ya cargadas cuyo Componentes coincide (LIKE, sin
        distinguir mayúsculas) con alguna fórmula de esa tabla --
        incluye productos que nunca estuvieron en el catálogo
        (Componentes es un campo de la transacción, no del catálogo).
        También marca Excluido=1 en dbo.CatalogoAgrupadorNutrientes
        para los productos que sí tienen entrada en el catálogo, para
        que la pantalla de Nomenclatura quede consistente.
     3. Actualiza usp_CargarNutrientes: de ahora en más, CUALQUIER
        carga futura marca Excluido=1 automáticamente si el Componentes
        de la fila coincide con una fórmula de
        dbo.FormulasExcluidasNutrientes -- sin depender de que el
        producto ya esté en el catálogo ni de que alguien lo marque a
        mano.

   Es seguro volver a correr este script las veces que haga falta: el
   INSERT de fórmulas no duplica, y los UPDATE de backfill solo tocan
   filas que todavía tienen Excluido=0 (una segunda corrida no vuelve a
   contar las mismas filas como "cambiadas" -- @@ROWCOUNT dará 0 la
   segunda vez si nada nuevo coincide).
   ===================================================================== */

USE PIQ_IA;
GO


/* ---------------------------------------------------------------------
   1. TABLA dbo.FormulasExcluidasNutrientes
   --------------------------------------------------------------------- */

IF OBJECT_ID('dbo.FormulasExcluidasNutrientes', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.FormulasExcluidasNutrientes(
        Formula       VARCHAR(200) NOT NULL PRIMARY KEY,
        FechaCreacion DATETIME NOT NULL DEFAULT GETDATE()
    );
    PRINT 'Tabla dbo.FormulasExcluidasNutrientes creada.';
END
ELSE
    PRINT 'dbo.FormulasExcluidasNutrientes ya existía -- no se tocó.';
GO

IF NOT EXISTS (SELECT 1 FROM dbo.FormulasExcluidasNutrientes WHERE Formula = 'Mancozeb')
    INSERT INTO dbo.FormulasExcluidasNutrientes (Formula) VALUES ('Mancozeb');
IF NOT EXISTS (SELECT 1 FROM dbo.FormulasExcluidasNutrientes WHERE Formula = 'Propamocarbhydrocloride')
    INSERT INTO dbo.FormulasExcluidasNutrientes (Formula) VALUES ('Propamocarbhydrocloride');
GO

DECLARE @formulas_listado VARCHAR(MAX);
SELECT @formulas_listado = STRING_AGG(Formula, ', ') FROM dbo.FormulasExcluidasNutrientes;
PRINT 'Fórmulas excluidas cargadas: ' + @formulas_listado;
GO


/* ---------------------------------------------------------------------
   2. BACKFILL -- dbo.Nutrientes
   --------------------------------------------------------------------- */

UPDATE n
SET n.Excluido = 1
FROM dbo.Nutrientes n
WHERE n.Excluido = 0
  AND EXISTS (
      SELECT 1 FROM dbo.FormulasExcluidasNutrientes f
      WHERE n.Componentes LIKE CONCAT('%', f.Formula, '%')
  );
PRINT 'Backfill dbo.Nutrientes: ' + CAST(@@ROWCOUNT AS VARCHAR(10)) + ' filas pasaron de Excluido=0 a Excluido=1.';
GO


/* ---------------------------------------------------------------------
   3. BACKFILL -- dbo.CatalogoAgrupadorNutrientes (para los productos
      que ya tienen entrada en el catálogo)
   --------------------------------------------------------------------- */

UPDATE c
SET c.Excluido = 1
FROM dbo.CatalogoAgrupadorNutrientes c
WHERE c.Excluido = 0
  AND EXISTS (
      SELECT 1
      FROM dbo.Nutrientes n
      JOIN dbo.FormulasExcluidasNutrientes f
        ON n.Componentes LIKE CONCAT('%', f.Formula, '%')
      WHERE n.NombreComercial IS NOT NULL
        AND UPPER(LTRIM(RTRIM(
              REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                  n.NombreComercial
              , '  ', ' '), '  ', ' '), '  ', ' '), '  ', ' '), '  ', ' ')
          ))) = c.NombreComercial_Key
  );
PRINT 'Backfill dbo.CatalogoAgrupadorNutrientes: ' + CAST(@@ROWCOUNT AS VARCHAR(10)) + ' productos pasaron de Excluido=0 a Excluido=1.';
GO


/* ---------------------------------------------------------------------
   4. usp_CargarNutrientes -- aplica la regla automáticamente en cada
      carga futura
   --------------------------------------------------------------------- */

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
            VENTANILLA, ProductoAgrupado, CodigoAgrupador, Excluido, fechamod, userid
        )
        SELECT
            CAST(s.anio AS INT), s.Tipo, s.No_Licencia, s.No_Registro, s.NombreComercial,
            s.EmpresaImportadora, TRY_CAST(s.FechaEmision AS DATE), s.UMedida,
            s.Cantidad, s.PaisProcedencia, s.PaisOrigen, s.AduanadeIngreso,
            s.CIF_dolares, s.CIF_Q, s.TimbresQ, s.Exportador, s.Concentraciones,
            s.Componentes, s.VENTANILLA, c.ProductoAgrupado, c.Codigo,
            -- Excluido=1 si el catálogo ya lo marca para este producto, O
            -- si la fórmula/componente de la fila coincide con alguna de
            -- dbo.FormulasExcluidasNutrientes -- esto último aplica
            -- automáticamente a CUALQUIER producto (nuevo o ya
            -- catalogado) que use esa fórmula.
            CASE
                WHEN EXISTS (
                    SELECT 1 FROM dbo.FormulasExcluidasNutrientes f
                    WHERE s.Componentes LIKE CONCAT('%', f.Formula, '%')
                ) THEN 1
                ELSE ISNULL(c.Excluido, 0)
            END,
            GETDATE(), @UserId
        FROM dbo.stg_Nutrientes s
        LEFT JOIN dbo.CatalogoAgrupadorNutrientes c
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

PRINT 'usp_CargarNutrientes actualizado -- aplica FormulasExcluidasNutrientes automáticamente.';
GO


/* ---------------------------------------------------------------------
   5. VERIFICACIÓN
   --------------------------------------------------------------------- */

SELECT
    'Fórmulas excluidas registradas' AS metrica, COUNT(*) AS valor FROM dbo.FormulasExcluidasNutrientes
UNION ALL
SELECT
    'Filas de Nutrientes con Excluido=1 (total)', COUNT(*) FROM dbo.Nutrientes WHERE Excluido = 1
UNION ALL
SELECT
    'Filas activas (vw_NutrientesActivos) que todavía mencionan Mancozeb/Propamocarbhydrocloride (debe ser 0)',
    (SELECT COUNT(*) FROM dbo.vw_NutrientesActivos v WHERE EXISTS (
        SELECT 1 FROM dbo.FormulasExcluidasNutrientes f WHERE v.Componentes LIKE CONCAT('%', f.Formula, '%')
    ));
GO

PRINT '=== Exclusión por fórmula en Nutrientes finalizada. ===';
PRINT 'Si la última fila de la verificación no dio 0, revisar antes de dar esto por bueno.';
GO
