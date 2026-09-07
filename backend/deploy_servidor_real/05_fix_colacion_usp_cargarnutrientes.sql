/* =====================================================================
   PIQ_IA -- Fix: conflicto de collation en dbo.usp_CargarNutrientes
   =====================================================================
   Corrige el error real visto en producción al cargar el archivo de
   julio de Nutrientes desde la pantalla de Carga:

     pyodbc.ProgrammingError: ('42000', '[42000] [Microsoft][ODBC Driver
     17 for SQL Server][SQL Server]Cannot resolve the collation conflict
     between "SQL_Latin1_General_CP1_CI_AS" and "Modern_Spanish_CI_AS"
     in the equal to operation. (468)')

   CAUSA REAL (confirmada, no supuesta):

   dbo.stg_Nutrientes NO es una tabla fija del esquema -- el backend la
   recrea desde cero en CADA carga con pandas
   (`to_sql("stg_Nutrientes", engine, if_exists="replace")`, ver
   app/services/etl_nutrientes.py). Esa recreación NO especifica
   COLLATE en ninguna columna, así que sus columnas de texto (incluida
   NombreComercial_Key) quedan con el collation POR DEFECTO DE LA BASE
   DE DATOS donde vive PIQ_IA -- y `CREATE DATABASE PIQ_IA;` (ver
   01_crear_base_piq_ia.sql) tampoco especifica COLLATE, así que esa
   base hereda el collation por defecto DE LA INSTANCIA de SQL Server
   del servidor real.

   dbo.CatalogoAgrupadorNutrientes.NombreComercial_Key, en cambio, quedó
   con COLLATE Modern_Spanish_CI_AS fijo desde que se generó el script
   01_crear_base_piq_ia.sql (scripteado desde la base de desarrollo,
   donde la instancia también es Modern_Spanish_CI_AS).

   Verificado en la base de desarrollo (AGREQUIMA, Desarrollo-2):
       SELECT SERVERPROPERTY('Collation')                    -> Modern_Spanish_CI_AS
       SELECT DATABASEPROPERTYEX('AGREQUIMA', 'Collation')    -> Modern_Spanish_CI_AS
   Ahí instancia y base COINCIDEN -- por eso este bug nunca apareció en
   desarrollo: dbo.stg_Nutrientes recreada por pandas también queda en
   Modern_Spanish_CI_AS, igual que el catálogo, y el JOIN nunca choca.

   En el servidor real, el error nombra explícitamente
   "SQL_Latin1_General_CP1_CI_AS" (el collation de fábrica más común de
   SQL Server) como uno de los dos lados en conflicto -- eso confirma
   que ahí la instancia (y por lo tanto la base PIQ_IA, que no
   sobrescribe el collation al crearse) NO es Modern_Spanish_CI_AS,
   a diferencia del catálogo permanente que sí lo tiene fijo.

   CORRECCIÓN: agregar COLLATE DATABASE_DEFAULT a ambos lados de las
   dos comparaciones NombreComercial_Key = NombreComercial_Key dentro
   del procedimiento -- fuerza una collation común sin importar cuál
   sea el default real de la instancia o de la base, así que funciona
   igual en cualquier servidor, no solo donde instancia y base
   coincidan por casualidad. Corrección permanente (queda en el cuerpo
   del procedimiento), no un parche de una sola vez.

   Es seguro volver a correr este script las veces que haga falta:
   CREATE OR ALTER PROCEDURE reemplaza la definición completa cada vez,
   no duplica nada ni depende de un estado previo.
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

        -- Ver comentario equivalente en usp_CargarImportacion: stg_Nutrientes
        -- ya viene filtrada por el ETL para solo traer meses nuevos, así
        -- que ya no se borra nada antes de insertar.
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
            ISNULL(c.Excluido, 0), GETDATE(), @UserId
        FROM dbo.stg_Nutrientes s
        LEFT JOIN dbo.CatalogoAgrupadorNutrientes c
               -- Fix collation (ver encabezado de este archivo): DATABASE_DEFAULT
               -- en los dos lados evita el error 468 sin importar el collation
               -- real de la instancia o de la base.
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

PRINT '=== usp_CargarNutrientes actualizado con COLLATE DATABASE_DEFAULT. ===';
PRINT 'Ya podés volver a intentar la carga de Nutrientes desde la pantalla de Carga.';
GO
