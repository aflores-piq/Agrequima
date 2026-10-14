/* =====================================================================
   PIQ_IA -- Nutrientes: aplicar la regla de la letra F a lo ya cargado
   (script 23_excluir_nutrientes_sin_letra_F)
   =====================================================================
   POR QUE: desde el 2026-09-07 el cargador de Nutrientes solo carga filas
   cuyo No_Registro contiene la letra F (cualquier mayuscula o minuscula);
   las demas se descartan. Pero todo lo que ya estaba cargado (la carga
   masiva del 2026-08-28) se cargo ANTES de esa regla, y nunca se le aplico.
   Por eso el dashboard de Nutrientes todavia muestra productos de
   plaguicidas (2,4-D, glifosato, etc.): sus registros no tienen letra F.

   REGLA (EXACTAMENTE la del cargador, etl_nutrientes.py,
   _filtrar_solo_con_f_en_no_registro):
        se conserva la fila si No_Registro es texto y contiene la letra F
        (sin distinguir mayusculas);  si no, se descarta.
   Aqui "se descarta" = Excluido = 1 (el mismo mecanismo que ya usan la
   vista dbo.vw_NutrientesActivos y todos los dashboards/exports).
   No_Registro NULL o vacio: NO tiene letra F, asi que SE MARCA (igual que el
   cargador, que descarta lo que no es texto con F).

   QUE HACE (en UNA transaccion):
     - Marca Excluido = 1 solo en filas que hoy tienen Excluido = 0 y no
       cumplen la regla. Las que ya estan en 1 no se tocan. NO borra filas.
     - No toca importes, cantidades ni ningun otro dato: al final verifica
       que el numero de filas y la suma de CIF (USD y Q) de dbo.Nutrientes son
       EXACTAMENTE los de antes; si no, ROLLBACK y falla.

   QUE MUESTRA: cuantas filas marca, por anio, por componente y por
   producto, y el efecto en lo que muestra el dashboard (leido de la vista
   dbo.vw_NutrientesActivos, 2026 de enero a julio, con los mismos criterios
   del dashboard: sin tipo PLAGUICIDA y sin duplicados exactos): registros,
   CIF USD y empresas, antes y despues. Al final devuelve la tabla de filas
   ocultadas (agrupadas por NombreComercial y Componentes, con filas y CIF
   USD y la marca ParecenNutrienteReal) que publicar.ps1 guarda como
   ocultados_regla_F.csv para mostrarsela al cliente.

   ParecenNutrienteReal = SI cuando TODAS las partes del componente estan en
   el vocabulario de nutrientes de abajo (ej. Fosforita "CaO, P2O5" u oxido de
   magnesio "MgO"): son las que la regla F oculta aunque parezcan fertilizantes.
   El vocabulario se edita en la lista @vocabulario.

   RESPALDO AUTOMATICO (solo al aplicar, y solo si hay algo que marcar):
   copia dbo.Nutrientes a dbo.ZZ_bak23_Nutrientes_AAAAMMDD (fecha del dia). Si
   esa tabla ya existe NO se vuelve a crear ni se pisa.

   SEGURO DE REPETIR: una segunda corrida no encuentra nada que marcar (0
   cambios) y lo dice. COLLATE DATABASE_DEFAULT en las comparaciones
   texto-contra-texto entre tablas (evita el error 468).

   COMO USARLO
     - Vista previa SIN cambiar nada: poner @SoloVistaPrevia = 1 abajo.
     - Aplicar: @SoloVistaPrevia = 0 (valor por defecto).

   COMO REVERTIR (reemplazar AAAAMMDD por la fecha del respaldo):
       UPDATE n SET n.Excluido = b.Excluido
       FROM dbo.Nutrientes n
       JOIN dbo.ZZ_bak23_Nutrientes_AAAAMMDD b ON b.nutrienteid = n.nutrienteid
       WHERE n.Excluido <> b.Excluido;
   Cuando ya no haga falta, el respaldo se borra con DROP TABLE.
   ===================================================================== */

USE PIQ_IA;
GO

SET NOCOUNT ON;

DECLARE @SoloVistaPrevia BIT = 0;   -- 1 = solo muestra la vista previa

-- Vocabulario de nutrientes (para marcar los ocultados que parecen fertilizantes reales)
DECLARE @vocabulario TABLE (Parte VARCHAR(20) NOT NULL PRIMARY KEY);
INSERT INTO @vocabulario (Parte) VALUES
    ('N'), ('P'), ('K'), ('S'), ('Ca'), ('Mg'), ('Zn'), ('B'), ('Fe'), ('Mn'), ('Cu'), ('Mo'), ('Si'), ('Na'), ('Cl'),
    ('Se'), ('Co'), ('Ni'), ('Al'), ('I'), ('V'),
    ('P2O5'), ('K2O'), ('MgO'), ('CaO'), ('SO3'), ('SiO2'), ('Na2O'), ('Al2O3'), ('Fe2O3'), ('B2O3'), ('MnO'), ('ZnO'), ('CuO'),
    ('Urea');

-- Filas que la regla oculta: activas hoy (Excluido = 0) cuyo No_Registro no es texto con letra F
DECLARE @marcadas TABLE (nutrienteid INT NOT NULL PRIMARY KEY);
INSERT INTO @marcadas (nutrienteid)
SELECT n.nutrienteid
FROM dbo.Nutrientes n
WHERE n.Excluido = 0
  AND (n.No_Registro IS NULL OR UPPER(n.No_Registro) NOT LIKE '%F%');
DECLARE @aMarcar INT = (SELECT COUNT(*) FROM @marcadas);

-- Totales de control de dbo.Nutrientes antes de tocar nada
DECLARE @filasAntes     INT           = (SELECT COUNT(*) FROM dbo.Nutrientes);
DECLARE @cifAntes       DECIMAL(19,4) = (SELECT ISNULL(SUM(CAST(CIF_dolares AS DECIMAL(19,4))), 0) FROM dbo.Nutrientes);
DECLARE @cifQAntes      DECIMAL(19,4) = (SELECT ISNULL(SUM(CAST(CIF_Q AS DECIMAL(19,4))), 0) FROM dbo.Nutrientes);
DECLARE @excluidasAntes INT           = (SELECT COUNT(*) FROM dbo.Nutrientes WHERE Excluido = 1);

-- Lo que muestra hoy el dashboard de Nutrientes (2026, enero a julio): mismos criterios que
-- dashboard_nutrientes.py (vista de filas activas, sin Tipo PLAGUICIDA, sin duplicados exactos).
DECLARE @sqlEfecto NVARCHAR(MAX) = N'
SELECT @reg = COUNT(*),
       @cif = ISNULL(SUM(CAST(n.CIF_dolares AS DECIMAL(19,4))), 0),
       @emp = COUNT(DISTINCT n.EmpresaImportadora)
FROM {V} n
WHERE n.anio = 2026
  AND n.FechaEmision >= ''2026-01-01'' AND n.FechaEmision < ''2026-08-01''
  AND n.Tipo NOT IN (''PLAGUICIDA'')
  AND NOT EXISTS (
      SELECT 1 FROM {V} o
      WHERE o.anio = n.anio AND o.nutrienteid < n.nutrienteid
        AND (o.No_Licencia = n.No_Licencia OR (o.No_Licencia IS NULL AND n.No_Licencia IS NULL))
        AND (o.No_Registro = n.No_Registro OR (o.No_Registro IS NULL AND n.No_Registro IS NULL))
        AND (o.FechaEmision = n.FechaEmision OR (o.FechaEmision IS NULL AND n.FechaEmision IS NULL))
        AND (o.EmpresaImportadora = n.EmpresaImportadora OR (o.EmpresaImportadora IS NULL AND n.EmpresaImportadora IS NULL))
        AND (o.NombreComercial = n.NombreComercial OR (o.NombreComercial IS NULL AND n.NombreComercial IS NULL))
        AND (o.CIF_dolares = n.CIF_dolares OR (o.CIF_dolares IS NULL AND n.CIF_dolares IS NULL)))';
DECLARE @vistaHoy NVARCHAR(400) = N'dbo.vw_NutrientesActivos';
DECLARE @vistaConF NVARCHAR(400) = N'(SELECT * FROM dbo.vw_NutrientesActivos WHERE No_Registro IS NOT NULL AND UPPER(No_Registro) LIKE ''%F%'')';
DECLARE @sqlHoy NVARCHAR(MAX) = REPLACE(@sqlEfecto, N'{V}', @vistaHoy);
DECLARE @sqlConF NVARCHAR(MAX) = REPLACE(@sqlEfecto, N'{V}', @vistaConF);

DECLARE @regAntes INT, @cifDashAntes DECIMAL(19,4), @empAntes INT;
EXEC sp_executesql @sqlHoy, N'@reg INT OUTPUT, @cif DECIMAL(19,4) OUTPUT, @emp INT OUTPUT',
     @reg = @regAntes OUTPUT, @cif = @cifDashAntes OUTPUT, @emp = @empAntes OUTPUT;

-- ---------------------------------------------------------------------
-- VISTA PREVIA
-- ---------------------------------------------------------------------
PRINT 'dbo.Nutrientes antes: ' + CAST(@filasAntes AS VARCHAR(20)) + ' filas (' + CAST(@excluidasAntes AS VARCHAR(20)) + ' ya excluidas), CIF USD total ' + FORMAT(@cifAntes, 'N2', 'en-US');
PRINT 'Filas que la regla de la letra F marcaria Excluido = 1: ' + CAST(@aMarcar AS VARCHAR(20));

SELECT n.anio,
       COUNT(*)                                      AS filas_a_marcar,
       SUM(CAST(n.CIF_dolares AS DECIMAL(19,4)))     AS cif_usd,
       SUM(CASE WHEN n.No_Registro IS NULL OR LTRIM(RTRIM(n.No_Registro)) = '' THEN 1 ELSE 0 END) AS con_registro_vacio_o_null
FROM dbo.Nutrientes n JOIN @marcadas m ON m.nutrienteid = n.nutrienteid
GROUP BY n.anio ORDER BY n.anio;

SELECT TOP (30) n.Componentes AS componente,
       COUNT(*)                                      AS filas_a_marcar,
       SUM(CAST(n.CIF_dolares AS DECIMAL(19,4)))     AS cif_usd,
       COUNT(DISTINCT n.NombreComercial)             AS productos
FROM dbo.Nutrientes n JOIN @marcadas m ON m.nutrienteid = n.nutrienteid
GROUP BY n.Componentes ORDER BY SUM(CAST(n.CIF_dolares AS DECIMAL(19,4))) DESC;

SELECT TOP (30) n.NombreComercial AS producto,
       COUNT(*)                                      AS filas_a_marcar,
       SUM(CAST(n.CIF_dolares AS DECIMAL(19,4)))     AS cif_usd,
       MIN(n.Componentes)                            AS componente_ejemplo
FROM dbo.Nutrientes n JOIN @marcadas m ON m.nutrienteid = n.nutrienteid
GROUP BY n.NombreComercial ORDER BY SUM(CAST(n.CIF_dolares AS DECIMAL(19,4))) DESC;

-- Efecto esperado en el dashboard (vista previa): lo mismo, quedandose solo con las filas con letra F
DECLARE @regEsp INT, @cifEsp DECIMAL(19,4), @empEsp INT;
EXEC sp_executesql @sqlConF, N'@reg INT OUTPUT, @cif DECIMAL(19,4) OUTPUT, @emp INT OUTPUT',
     @reg = @regEsp OUTPUT, @cif = @cifEsp OUTPUT, @emp = @empEsp OUTPUT;

-- Tabla de ocultadas por NombreComercial y Componentes (la que publicar.ps1 guarda como CSV)
DECLARE @tablaOcultadas TABLE (
    NombreComercial NVARCHAR(200) NULL, Componentes NVARCHAR(500) NULL, FilasOcultadas INT NOT NULL,
    CifUsd DECIMAL(19,2) NOT NULL, PrimerAnio INT NULL, UltimoAnio INT NULL,
    ParecenNutrienteReal VARCHAR(2) NOT NULL, PartesFueraDelVocabulario NVARCHAR(500) NULL);
INSERT INTO @tablaOcultadas
SELECT g.NombreComercial, g.Componentes, g.Filas, g.Cif, g.PrimerAnio, g.UltimoAnio,
       CASE WHEN g.Componentes IS NOT NULL
             AND EXISTS (SELECT 1 FROM STRING_SPLIT(REPLACE(REPLACE(REPLACE(g.Componentes, '+', ','), ';', ','), '/', ','), ',') s
                         WHERE LTRIM(RTRIM(s.value)) <> '')
             AND NOT EXISTS (SELECT 1 FROM STRING_SPLIT(REPLACE(REPLACE(REPLACE(g.Componentes, '+', ','), ';', ','), '/', ','), ',') s
                             WHERE LTRIM(RTRIM(s.value)) <> ''
                               AND LTRIM(RTRIM(s.value)) COLLATE DATABASE_DEFAULT NOT IN (SELECT Parte COLLATE DATABASE_DEFAULT FROM @vocabulario))
            THEN 'SI' ELSE '' END,
       (SELECT STRING_AGG(LTRIM(RTRIM(s.value)), ' ; ')
        FROM STRING_SPLIT(REPLACE(REPLACE(REPLACE(g.Componentes, '+', ','), ';', ','), '/', ','), ',') s
        WHERE LTRIM(RTRIM(s.value)) <> ''
          AND LTRIM(RTRIM(s.value)) COLLATE DATABASE_DEFAULT NOT IN (SELECT Parte COLLATE DATABASE_DEFAULT FROM @vocabulario))
FROM (SELECT n.NombreComercial, n.Componentes, COUNT(*) AS Filas,
             SUM(CAST(n.CIF_dolares AS DECIMAL(19,2))) AS Cif, MIN(n.anio) AS PrimerAnio, MAX(n.anio) AS UltimoAnio
      FROM dbo.Nutrientes n JOIN @marcadas m ON m.nutrienteid = n.nutrienteid
      GROUP BY n.NombreComercial, n.Componentes) g;

IF @SoloVistaPrevia = 1
BEGIN
    SELECT 'Antes (hoy)' AS momento, @regAntes AS registros, @cifDashAntes AS cif_usd, @empAntes AS empresas
    UNION ALL SELECT 'Despues (esperado)', @regEsp, @cifEsp, @empEsp;
    SELECT NombreComercial, Componentes, FilasOcultadas, CifUsd, PrimerAnio, UltimoAnio, ParecenNutrienteReal, PartesFueraDelVocabulario
    FROM @tablaOcultadas ORDER BY CASE WHEN ParecenNutrienteReal = 'SI' THEN 0 ELSE 1 END, CifUsd DESC;
    PRINT '@SoloVistaPrevia = 1: no se cambio nada.';
    RETURN;
END

IF @aMarcar = 0
BEGIN
    SELECT 'Antes (hoy)' AS momento, @regAntes AS registros, @cifDashAntes AS cif_usd, @empAntes AS empresas;
    PRINT 'No habia nada que marcar (ya estaba aplicado, o todas las filas activas cumplen la regla). dbo.Nutrientes no cambio.';
    RETURN;
END

-- ---------------------------------------------------------------------
-- RESPALDO AUTOMATICO (nunca pisa uno existente)
-- ---------------------------------------------------------------------
DECLARE @sufijo CHAR(8) = CONVERT(CHAR(8), GETDATE(), 112);
DECLARE @bakNutrientes NVARCHAR(200) = N'dbo.ZZ_bak23_Nutrientes_' + @sufijo;
IF OBJECT_ID(@bakNutrientes) IS NULL
BEGIN
    EXEC (N'SELECT * INTO ' + @bakNutrientes + N' FROM dbo.Nutrientes');
    PRINT 'Respaldo creado: ' + @bakNutrientes;
END
ELSE PRINT 'Respaldo ya existente (no se pisa): ' + @bakNutrientes;

-- ---------------------------------------------------------------------
-- APLICAR (una transaccion)
-- ---------------------------------------------------------------------
BEGIN TRY
    BEGIN TRANSACTION;

    UPDATE n
    SET n.Excluido = 1
    FROM dbo.Nutrientes n
    JOIN @marcadas m ON m.nutrienteid = n.nutrienteid
    WHERE n.Excluido = 0;
    DECLARE @filasMarcadas INT = @@ROWCOUNT;

    -- Control: solo cambian marcas; ni una fila ni un centavo de CIF
    DECLARE @filasDespues INT           = (SELECT COUNT(*) FROM dbo.Nutrientes);
    DECLARE @cifDespues   DECIMAL(19,4) = (SELECT ISNULL(SUM(CAST(CIF_dolares AS DECIMAL(19,4))), 0) FROM dbo.Nutrientes);
    DECLARE @cifQDespues  DECIMAL(19,4) = (SELECT ISNULL(SUM(CAST(CIF_Q AS DECIMAL(19,4))), 0) FROM dbo.Nutrientes);
    DECLARE @excluidasDespues INT       = (SELECT COUNT(*) FROM dbo.Nutrientes WHERE Excluido = 1);
    IF @filasDespues <> @filasAntes OR @cifDespues <> @cifAntes OR @cifQDespues <> @cifQAntes
        THROW 50023, 'Control fallido: cambio el numero de filas o el CIF total de dbo.Nutrientes. Se deshace todo.', 1;
    IF @filasMarcadas <> @aMarcar OR @excluidasDespues <> @excluidasAntes + @filasMarcadas
        THROW 50024, 'Control fallido: la cantidad de filas marcadas no coincide con la prevista. Se deshace todo.', 1;

    -- Lo que muestra el dashboard despues (dentro de la transaccion, ya con las marcas)
    DECLARE @regDespues INT, @cifDashDespues DECIMAL(19,4), @empDespues INT;
    EXEC sp_executesql @sqlHoy, N'@reg INT OUTPUT, @cif DECIMAL(19,4) OUTPUT, @emp INT OUTPUT',
         @reg = @regDespues OUTPUT, @cif = @cifDashDespues OUTPUT, @emp = @empDespues OUTPUT;

    COMMIT TRANSACTION;

    PRINT 'Filas marcadas Excluido = 1: ' + CAST(@filasMarcadas AS VARCHAR(20));
    PRINT 'dbo.Nutrientes despues: ' + CAST(@filasDespues AS VARCHAR(20)) + ' filas, CIF USD total ' + FORMAT(@cifDespues, 'N2', 'en-US') + ' (igual que antes).';
    SELECT 'Antes' AS momento, @regAntes AS registros, @cifDashAntes AS cif_usd, @empAntes AS empresas
    UNION ALL SELECT 'Despues', @regDespues, @cifDashDespues, @empDespues
    UNION ALL SELECT 'Despues (esperado en la vista previa)', @regEsp, @cifEsp, @empEsp;
    SELECT NombreComercial, Componentes, FilasOcultadas, CifUsd, PrimerAnio, UltimoAnio, ParecenNutrienteReal, PartesFueraDelVocabulario
    FROM @tablaOcultadas ORDER BY CASE WHEN ParecenNutrienteReal = 'SI' THEN 0 ELSE 1 END, CifUsd DESC;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH
GO
