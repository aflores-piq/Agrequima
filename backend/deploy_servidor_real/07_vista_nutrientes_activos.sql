/* =====================================================================
   PIQ_IA -- Vista dbo.vw_NutrientesActivos (solución estructural a la
   exclusión de productos, reemplaza el filtro disperso por función)
   =====================================================================
   Hasta ahora, "los productos Excluido=1 no deben mostrarse" dependía
   de que CADA función que leyera dbo.Nutrientes se acordara de agregar
   `WHERE Excluido = 0` -- un parche puntual por cada pantalla/reporte,
   con riesgo real de que una función nueva (o una que ya existía y no
   se revisó) se olvide del filtro y vuelva a mostrar un producto que
   el cliente ya confirmó que no corresponde.

   Esta vista es la solución estructural: filtra por definición, así
   que nadie que lea de acá puede "olvidarse" -- las filas Excluido=1
   simplemente no existen desde la perspectiva de quien consulta la
   vista, sin que el código que consulta tenga que saber que existe
   una columna Excluido.

   Todo el código de dashboards/reportes/exports de Nutrientes en
   backend/app ya se migró para leer de esta vista en vez de
   dbo.Nutrientes directamente (ver NutrienteActivo en
   app/models/nutriente.py). dbo.Nutrientes (la tabla real, con TODAS
   las filas) sigue existiendo sin cambios -- la usan exclusivamente
   los procesos de carga (usp_CargarNutrientes) y de sincronización del
   catálogo (sincronizar_agrupador_nutrientes), que sí necesitan ver
   también las filas excluidas.

   Es seguro volver a correr este script las veces que haga falta:
   CREATE OR ALTER VIEW reemplaza la definición completa cada vez.
   ===================================================================== */

USE PIQ_IA;
GO

CREATE OR ALTER VIEW dbo.vw_NutrientesActivos AS
SELECT
    nutrienteid, anio, Tipo, No_Licencia, No_Registro, NombreComercial,
    EmpresaImportadora, FechaEmision, UMedida, Cantidad, PaisProcedencia,
    PaisOrigen, AduanadeIngreso, CIF_dolares, CIF_Q, TimbresQ, Exportador,
    Concentraciones, Componentes, VENTANILLA, ProductoAgrupado,
    CodigoAgrupador, Excluido, fechamod, userid
FROM dbo.Nutrientes
WHERE Excluido = 0;
GO

PRINT '=== dbo.vw_NutrientesActivos creada/actualizada. ===';
PRINT 'A partir de ahora, cualquier código nuevo que necesite leer Nutrientes';
PRINT 'para un dashboard/reporte/export debe usar esta vista, no dbo.Nutrientes.';
GO
