/* =====================================================================
   PIQ_IA -- Fix: mismo conflicto de collation que usp_CargarNutrientes,
   en los otros 3 procedimientos que comparten el patrón de riesgo
   =====================================================================
   Corrige preventivamente usp_CargarImportacion, usp_ActualizarNomenclatura
   y usp_ActualizarAgrupadorNutrientes -- el mismo bug de collation que
   se corrigió en usp_CargarNutrientes (ver
   05_fix_colacion_usp_cargarnutrientes.sql) también existe en estos 3:
   ninguno había fallado todavía en producción por casualidad (Plaguicidas
   de julio no se había cargado, o Nomenclatura/Agrupador no se habían
   editado desde que existe PIQ_IA), pero el mismo error 468 "Cannot
   resolve the collation conflict..." va a aparecer apenas se use
   cualquiera de estos tres caminos.

   CAUSA (idéntica a usp_CargarNutrientes, ver ese script para el detalle
   completo): las 4 tablas de staging (stg_Importacion, stg_Nomenclatura,
   stg_Nutrientes, stg_AgrupadorNutrientes) las recrea pandas
   (`to_sql(..., if_exists="replace")`) en cada carga, sin especificar
   COLLATE -- sus columnas de texto quedan con el collation por defecto
   DE LA BASE (heredado de la instancia, ya que `CREATE DATABASE PIQ_IA;`
   tampoco especifica COLLATE). Las tablas permanentes de catálogo
   (CatalogoNomenclaturaPlaguicidas, CatalogoAgrupadorNutrientes) tienen
   sus columnas de texto fijas en COLLATE Modern_Spanish_CI_AS desde que
   se generaron los scripts. Si el collation por defecto del servidor
   real no es Modern_Spanish_CI_AS, cualquier comparación entre una
   tabla de staging y el catálogo permanente falla con el error 468.

   CORRECCIÓN: mismo patrón que usp_CargarNutrientes -- COLLATE
   DATABASE_DEFAULT en ambos lados de cada comparación de clave (JOIN o
   MERGE...ON), sin cambiar ninguna otra lógica de los procedimientos.

   Es seguro volver a correr este script las veces que haga falta:
   CREATE OR ALTER PROCEDURE reemplaza cada definición completa cada
   vez, sin depender de ningún estado previo.
   ===================================================================== */

USE PIQ_IA;
GO


/* ---------------------------------------------------------------------
   1. usp_CargarImportacion (Plaguicidas)
   --------------------------------------------------------------------- */

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
        -- antes de insertar.
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
               -- Fix collation: DATABASE_DEFAULT en los dos lados (ver
               -- encabezado de este archivo).
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

PRINT 'usp_CargarImportacion actualizado con COLLATE DATABASE_DEFAULT.';
GO


/* ---------------------------------------------------------------------
   2. usp_ActualizarNomenclatura (Plaguicidas)
   --------------------------------------------------------------------- */

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
    -- Fix collation: DATABASE_DEFAULT en los dos lados (ver encabezado
    -- de este archivo).
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

PRINT 'usp_ActualizarNomenclatura actualizado con COLLATE DATABASE_DEFAULT.';
GO


/* ---------------------------------------------------------------------
   3. usp_ActualizarAgrupadorNutrientes (Nutrientes)
   --------------------------------------------------------------------- */

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
    -- Fix collation: DATABASE_DEFAULT en los dos lados (ver encabezado
    -- de este archivo).
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

PRINT 'usp_ActualizarAgrupadorNutrientes actualizado con COLLATE DATABASE_DEFAULT.';
GO

PRINT '=== Fix de collation aplicado a los 3 procedimientos restantes. ===';
GO
