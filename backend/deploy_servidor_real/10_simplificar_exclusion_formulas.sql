/* =====================================================================
   PIQ_IA -- Simplificar la exclusión por fórmula en usp_CargarNutrientes
   (Mancozeb, Propamocarbhydrocloride, Paraquat) -- literales en vez de
   tabla de referencia
   =====================================================================
   Contexto: 08_formulas_excluidas_nutrientes.sql implementó la
   exclusión por fórmula comparando Componentes contra
   dbo.FormulasExcluidasNutrientes.Formula (columna contra columna, vía
   JOIN/LIKE). Esa comparación columna-contra-columna volvió a generar
   el error 468 "Cannot resolve the collation conflict..." en el
   servidor real -- se corrigió agregando COLLATE DATABASE_DEFAULT en
   ambos lados.

   El jefe del cliente aplicó directamente en el servidor real un
   UPDATE con el patrón de una fórmula nueva (Paraquat) comparando
   Componentes contra un LITERAL de texto ('%paraq%') y funcionó SIN
   necesitar COLLATE -- porque una columna comparada contra un literal
   nunca genera conflicto de collation (el literal toma automáticamente
   el collation "coercible-default" de la base, que siempre cede ante
   el collation de la columna). El conflicto solo aparece al comparar
   dos COLUMNAS con collations distintos entre sí.

   Este script adopta ese enfoque más simple: reemplaza, dentro de
   usp_CargarNutrientes, la subconsulta contra
   dbo.FormulasExcluidasNutrientes por comparaciones LIKE directas
   contra las 3 fórmulas ya excluidas, hardcodeadas como literales en
   el propio procedimiento. Ya no hace falta COLLATE en esta
   comparación.

   Qué hace:
     1. Reemplaza usp_CargarNutrientes: el CASE que decide Excluido
        ahora compara Componentes contra los literales 'Mancozeb',
        'Propamocarbhydrocloride' y 'paraq' en vez de consultar
        dbo.FormulasExcluidasNutrientes.

   Qué NO hace (a propósito):
     - No toca dbo.FormulasExcluidasNutrientes -- la tabla se deja tal
       cual está (con sus 2 filas), sin usarla ni borrarla. Podría
       reutilizarse en el futuro si se decide volver a un esquema
       basado en tabla; por ahora simplemente queda inactiva.
     - No incluye el backfill de Paraquat sobre datos ya cargados
       (UPDATE Nutrientes/CatalogoAgrupadorNutrientes SET Excluido=1
       WHERE Componentes LIKE '%paraq%') -- el jefe del cliente ya lo
       aplicó a mano en el servidor real. Volver a correrlo acá no
       causaría duplicados (el patrón WHERE Excluido=0 lo evita), pero
       se omite deliberadamente para no mezclar un cambio de esquema
       (este script) con una carga de datos que ya se hizo por otra
       vía.

   Agregar una fórmula nueva en el futuro: agregar una línea más
   "OR s.Componentes LIKE '%NuevaFormula%'" al CASE de abajo y desplegar
   un script nuevo (ya no es un INSERT en una tabla).

   Es seguro volver a correr este script las veces que haga falta:
   CREATE OR ALTER PROCEDURE reemplaza la definición completa cada vez,
   sin depender de ningún estado previo.
   ===================================================================== */

USE PIQ_IA;
GO

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
            -- si Componentes contiene alguna de las fórmulas excluidas
            -- (comparación contra LITERAL, no contra columna -- no
            -- necesita COLLATE, ver nota arriba).
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

PRINT 'usp_CargarNutrientes actualizado -- exclusion por formula ahora usa literales (Mancozeb, Propamocarbhydrocloride, paraq) en vez de dbo.FormulasExcluidasNutrientes.';
GO
