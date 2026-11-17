/* =====================================================================
   PRUEBA DE HUMO DE LOS DASHBOARDS DE PLAGUICIDAS Y NUTRIENTES
   Solo lectura (SELECT). Se corre contra la base real despues de cada script que toca
   columnas homologadas o collations (26, 27, 29) y desde el runner de la publicacion.

   Ejecuta, con COLLATE explicito igual al de app/core/collation.py, las mismas expresiones
   que usan los dashboards: COUNT(DISTINCT COALESCE(...)), GROUP BY COALESCE(...), IS NOT NULL,
   ORDER BY y DISTINCT sobre columna homologada + columna original. Si la base tuviera un
   conflicto de collation, SQL Server responde error 446/468 y esta prueba FALLA con el error.
   "RESULTADO: OK" solo si TODAS las consultas responden sin error.

   Hay dos bloques (para poder correr el de empresas en el script 26, antes de que exista la
   columna de nombres comerciales del script 27):
       >>> PRUEBA DE HUMO EMPRESAS   ...  <<< PRUEBA DE HUMO EMPRESAS
       >>> PRUEBA DE HUMO NOMBRES    ...  <<< PRUEBA DE HUMO NOMBRES
   Cada bloque es IDENTICO en este archivo y en los scripts que lo incluyen (26 empresas;
   27 nombres; 29 los dos); lo comprueba una prueba automatica.
   ===================================================================== */

-- >>> PRUEBA DE HUMO EMPRESAS
SET NOCOUNT ON;
SELECT p.prueba, p.valor, 'OK' AS estado
FROM (
    SELECT 'Nutrientes - KPI empresas: COUNT(DISTINCT COALESCE(...))' AS prueba,
           CAST(COUNT(DISTINCT COALESCE(EmpresaHomologada COLLATE Modern_Spanish_CI_AS, EmpresaImportadora COLLATE Modern_Spanish_CI_AS)) AS BIGINT) AS valor
    FROM dbo.vw_NutrientesActivos
    UNION ALL
    SELECT 'Nutrientes - Top empresas importadoras: GROUP BY COALESCE(...)', CAST(COUNT(*) AS BIGINT)
    FROM (SELECT TOP 10 COALESCE(EmpresaHomologada COLLATE Modern_Spanish_CI_AS, EmpresaImportadora COLLATE Modern_Spanish_CI_AS) AS empresa, SUM(CIF_dolares) AS cif
          FROM dbo.vw_NutrientesActivos
          WHERE COALESCE(EmpresaHomologada COLLATE Modern_Spanish_CI_AS, EmpresaImportadora COLLATE Modern_Spanish_CI_AS) IS NOT NULL
          GROUP BY COALESCE(EmpresaHomologada COLLATE Modern_Spanish_CI_AS, EmpresaImportadora COLLATE Modern_Spanish_CI_AS)
          ORDER BY SUM(CIF_dolares) DESC) t
    UNION ALL
    SELECT 'Plaguicidas - Top importadores: GROUP BY COALESCE(...)', CAST(COUNT(*) AS BIGINT)
    FROM (SELECT TOP 10 COALESCE(EmpresaHomologada COLLATE Modern_Spanish_CI_AS, importador COLLATE Modern_Spanish_CI_AS) AS empresa, SUM(cif_USD) AS cif
          FROM dbo.Importacion
          WHERE COALESCE(EmpresaHomologada COLLATE Modern_Spanish_CI_AS, importador COLLATE Modern_Spanish_CI_AS) IS NOT NULL
          GROUP BY COALESCE(EmpresaHomologada COLLATE Modern_Spanish_CI_AS, importador COLLATE Modern_Spanish_CI_AS)
          ORDER BY SUM(cif_USD) DESC) t
) p;
-- <<< PRUEBA DE HUMO EMPRESAS

-- >>> PRUEBA DE HUMO NOMBRES
SET NOCOUNT ON;
SELECT p.prueba, p.valor, 'OK' AS estado
FROM (
    SELECT 'Plaguicidas - Nombres comerciales: DISTINCT COALESCE(...)' AS prueba,
           CAST(COUNT(DISTINCT COALESCE(NombreComercialHomologado COLLATE Modern_Spanish_CI_AS, producto COLLATE Modern_Spanish_CI_AS)) AS BIGINT) AS valor
    FROM dbo.Importacion
    UNION ALL
    SELECT 'Plaguicidas - Detalle: ORDER BY COALESCE(...)', CAST(COUNT(*) AS BIGINT)
    FROM (SELECT TOP 20 COALESCE(NombreComercialHomologado COLLATE Modern_Spanish_CI_AS, producto COLLATE Modern_Spanish_CI_AS) AS producto_efectivo
          FROM dbo.Importacion
          ORDER BY COALESCE(NombreComercialHomologado COLLATE Modern_Spanish_CI_AS, producto COLLATE Modern_Spanish_CI_AS)) t
) p;
-- <<< PRUEBA DE HUMO NOMBRES
