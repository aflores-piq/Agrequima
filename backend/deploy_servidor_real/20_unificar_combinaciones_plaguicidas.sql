/* =====================================================================
   PIQ_IA -- Unificar las combinaciones de plaguicidas duplicadas
   (mismo ingrediente en orden invertido, p. ej. "2,4-D + Picloram"
   IA-011 y "Picloram + 2,4-D" IA-400) para que el dashboard muestre UN
   SOLO ingrediente por combinación.
   =====================================================================
   REGLA (acordada): en cada par, el código CANÓNICO es el de mayor
   monto de CIF USD; las filas del otro código (el "absorbido") pasan al
   canónico. El script hace dos cosas, en UNA transacción:

     1. dbo.CatalogoNomenclaturaPlaguicidas: toda clave de ingrediente
        que apuntaba al código absorbido pasa a apuntar al código
        canónico (Agrupador y Codigo del canónico). Así, las PRÓXIMAS
        cargas (que asignan el grupo por esa clave) ya caen en el
        canónico, sea cual sea el orden en que venga escrita la
        combinación.
     2. dbo.Importacion: las filas ya cargadas con el código absorbido
        pasan a Grupo/CodigoAgrupador del canónico (mismo resultado que
        dejaría sincronizar_agrupador_plaguicidas() de la app, pero
        acotado a estos códigos para no tocar nada más).

   RESPALDO AUTOMÁTICO (solo al aplicar, y solo si hay algo que cambiar):
   antes de modificar, copia CatalogoNomenclaturaPlaguicidas e Importacion
   a dbo.ZZ_bak_CatalogoNomenclaturaPlaguicidas_AAAAMMDD y
   dbo.ZZ_bak_Importacion_AAAAMMDD (fecha del día). Si esas tablas ya
   existen NO se vuelven a crear ni se pisan (así el respaldo del mismo día
   siempre es el de ANTES de aplicar). Sirve para revertir en el servidor
   sin respaldar toda la base (ver "CÓMO REVERTIR").

   NO toca importes ni cantidades: al final verifica que el número de
   filas y el CIF USD total de dbo.Importacion son EXACTAMENTE los de
   antes; si no, deshace todo (ROLLBACK) y falla.

   NO incluye: Fosfuro de aluminio (IA-296/IA-297) ni Hidróxido de cobre
   (IA-312/313 e IA-314/315): según acordado, esos ya se ven unificados.

   SEGURO DE REPETIR: si ya se corrió, no encuentra nada que cambiar y
   lo dice. Si un código no existe en esa base (por ejemplo, el absorbido
   ya no está), el par se omite.

   COLLATION: todas las comparaciones texto-contra-texto llevan COLLATE
   DATABASE_DEFAULT (evita el error 468).

   CÓMO USARLO
     - Vista previa SIN cambiar nada: poner @SoloVistaPrevia = 1 abajo,
       ejecutar y revisar la tabla (por cada par: código canónico, código
       que se absorbe, filas y CIF de cada uno y el CIF total esperado).
     - Aplicar: @SoloVistaPrevia = 0 (valor por defecto).
     - SIEMPRE con respaldo de la base antes (ver
       claude/Procedimiento_Publicacion_Servidor_Real.md).

   CÓMO REVERTIR (reemplazar AAAAMMDD por la fecha del respaldo):
       UPDATE c SET c.Agrupador = b.Agrupador, c.Codigo = b.Codigo, c.FechaMod = b.FechaMod
       FROM dbo.CatalogoNomenclaturaPlaguicidas c
       JOIN dbo.ZZ_bak_CatalogoNomenclaturaPlaguicidas_AAAAMMDD b
         ON b.IngredienteActivo_Key COLLATE DATABASE_DEFAULT = c.IngredienteActivo_Key COLLATE DATABASE_DEFAULT;
       UPDATE i SET i.Grupo = b.Grupo, i.CodigoAgrupador = b.CodigoAgrupador
       FROM dbo.Importacion i
       JOIN dbo.ZZ_bak_Importacion_AAAAMMDD b ON b.importacionplaguicidaid = i.importacionplaguicidaid;
   Cuando ya no hagan falta, las tablas ZZ_bak_* se borran con DROP TABLE.
   ===================================================================== */

USE PIQ_IA;
GO

SET NOCOUNT ON;

DECLARE @SoloVistaPrevia BIT = 0;   -- 1 = solo muestra la vista previa

-- (par, código que se absorbe, código canónico = el de mayor CIF)
DECLARE @pares TABLE (Par INT NOT NULL, CodigoAbsorbido VARCHAR(20) NOT NULL, CodigoCanonico VARCHAR(20) NOT NULL);
INSERT INTO @pares (Par, CodigoAbsorbido, CodigoCanonico) VALUES
    ( 1, 'IA-400', 'IA-011'),   -- 2,4-D + Picloram
    ( 2, 'IA-323', 'IA-185'),   -- Deltametrina + Imidacloprid
    ( 3, 'IA-410', 'IA-351'),   -- Lufenuron + Profenofos
    ( 4, 'IA-362', 'IA-148'),   -- Clorotalonil + Mandipropamid
    ( 5, 'IA-059', 'IA-128'),   -- Ciproconazol + Azoxistrobina
    ( 6, 'IA-194', 'IA-062'),   -- Azoxistrobina + Difenoconazol
    ( 7, 'IA-150', 'IA-002'),   -- 1,3 Dicloropropeno + clorpiricina
    ( 8, 'IA-347', 'IA-482'),   -- Tiametoxam + Lambda-cialotrina
    ( 9, 'IA-283', 'IA-065'),   -- Azoxistrobina + Flutriafol
    (10, 'IA-061', 'IA-145'),   -- Clorotalonil + Azoxistrobina
    (11, 'IA-322', 'IA-094'),   -- Bifentrina + Imidacloprid
    (12, 'IA-359', 'IA-207'),   -- Dimetomorf + Mancozeb
    (13, 'IA-350', 'IA-086'),   -- Benzoato de emamectina + Lufenuron
    (14, 'IA-356', 'IA-123'),   -- Cimoxanil + Mancozeb
    (15, 'IA-163', 'IA-358'),   -- Mancozeb + Cobre metalico
    (16, 'IA-345', 'IA-031'),   -- Acetamiprid + Lambda-cialotrina
    (17, 'IA-251', 'IA-481'),   -- Tiametoxam + Fipronil
    (18, 'IA-321', 'IA-014');   -- Abamectina + Imidacloprid

-- Totales de control de dbo.Importacion antes de tocar nada
DECLARE @filasAntes INT           = (SELECT COUNT(*) FROM dbo.Importacion);
DECLARE @cifAntes   DECIMAL(18,2) = (SELECT ISNULL(SUM(cif_USD), 0) FROM dbo.Importacion);

-- VISTA PREVIA: por cada par, canónico vs absorbido y el CIF total esperado
SELECT
    p.Par,
    p.CodigoCanonico                                           AS canonico_codigo,
    (SELECT TOP 1 k.Agrupador FROM dbo.CatalogoNomenclaturaPlaguicidas k
      WHERE k.Codigo COLLATE DATABASE_DEFAULT = p.CodigoCanonico COLLATE DATABASE_DEFAULT
      ORDER BY k.IngredienteActivo_Key)                        AS canonico_agrupador,
    ISNULL(ci.filas, 0)                                        AS canonico_filas,
    ISNULL(ci.cif, 0)                                          AS canonico_cif_usd,
    p.CodigoAbsorbido                                          AS absorbido_codigo,
    (SELECT TOP 1 k.Agrupador FROM dbo.CatalogoNomenclaturaPlaguicidas k
      WHERE k.Codigo COLLATE DATABASE_DEFAULT = p.CodigoAbsorbido COLLATE DATABASE_DEFAULT
      ORDER BY k.IngredienteActivo_Key)                        AS absorbido_agrupador,
    ISNULL(ai.filas, 0)                                        AS absorbido_filas,
    ISNULL(ai.cif, 0)                                          AS absorbido_cif_usd,
    (SELECT COUNT(*) FROM dbo.CatalogoNomenclaturaPlaguicidas k
      WHERE k.Codigo COLLATE DATABASE_DEFAULT = p.CodigoAbsorbido COLLATE DATABASE_DEFAULT) AS claves_catalogo_que_se_mueven,
    ISNULL(ci.filas, 0) + ISNULL(ai.filas, 0)                  AS filas_esperadas_despues,
    ISNULL(ci.cif, 0)  + ISNULL(ai.cif, 0)                     AS cif_total_esperado_despues
FROM @pares p
LEFT JOIN (SELECT CodigoAgrupador COLLATE DATABASE_DEFAULT AS cod, COUNT(*) AS filas, SUM(cif_USD) AS cif
           FROM dbo.Importacion GROUP BY CodigoAgrupador) ci ON ci.cod = p.CodigoCanonico COLLATE DATABASE_DEFAULT
LEFT JOIN (SELECT CodigoAgrupador COLLATE DATABASE_DEFAULT AS cod, COUNT(*) AS filas, SUM(cif_USD) AS cif
           FROM dbo.Importacion GROUP BY CodigoAgrupador) ai ON ai.cod = p.CodigoAbsorbido COLLATE DATABASE_DEFAULT
ORDER BY p.Par;

PRINT 'dbo.Importacion antes: ' + CAST(@filasAntes AS VARCHAR(20)) + ' filas, CIF USD total ' + CONVERT(VARCHAR(40), @cifAntes, 1);

IF @SoloVistaPrevia = 1
BEGIN
    PRINT '@SoloVistaPrevia = 1: no se cambió nada.';
    RETURN;
END

-- RESPALDO AUTOMÁTICO (solo si hay algo que unificar; nunca pisa uno existente)
DECLARE @hayCambios BIT = CASE WHEN
       EXISTS (SELECT 1 FROM dbo.CatalogoNomenclaturaPlaguicidas c
               JOIN @pares p ON c.Codigo COLLATE DATABASE_DEFAULT = p.CodigoAbsorbido COLLATE DATABASE_DEFAULT)
    OR EXISTS (SELECT 1 FROM dbo.Importacion i
               JOIN @pares p ON i.CodigoAgrupador COLLATE DATABASE_DEFAULT = p.CodigoAbsorbido COLLATE DATABASE_DEFAULT)
    THEN 1 ELSE 0 END;
IF @hayCambios = 1
BEGIN
    DECLARE @sufijo CHAR(8) = CONVERT(CHAR(8), GETDATE(), 112);
    DECLARE @bakCatalogo NVARCHAR(200) = N'dbo.ZZ_bak_CatalogoNomenclaturaPlaguicidas_' + @sufijo;
    DECLARE @bakImportacion NVARCHAR(200) = N'dbo.ZZ_bak_Importacion_' + @sufijo;
    IF OBJECT_ID(@bakCatalogo) IS NULL
    BEGIN
        EXEC (N'SELECT * INTO ' + @bakCatalogo + N' FROM dbo.CatalogoNomenclaturaPlaguicidas');
        PRINT 'Respaldo creado: ' + @bakCatalogo;
    END
    ELSE PRINT 'Respaldo ya existente (no se pisa): ' + @bakCatalogo;
    IF OBJECT_ID(@bakImportacion) IS NULL
    BEGIN
        EXEC (N'SELECT * INTO ' + @bakImportacion + N' FROM dbo.Importacion');
        PRINT 'Respaldo creado: ' + @bakImportacion;
    END
    ELSE PRINT 'Respaldo ya existente (no se pisa): ' + @bakImportacion;
END

BEGIN TRY
    BEGIN TRANSACTION;

    -- 1. Catálogo: las claves del código absorbido pasan al canónico
    UPDATE c
    SET c.Agrupador = k.Agrupador,
        c.Codigo    = k.Codigo,
        c.FechaMod  = GETDATE()
    FROM dbo.CatalogoNomenclaturaPlaguicidas c
    JOIN @pares p ON c.Codigo COLLATE DATABASE_DEFAULT = p.CodigoAbsorbido COLLATE DATABASE_DEFAULT
    CROSS APPLY (SELECT TOP 1 k2.Agrupador, k2.Codigo
                 FROM dbo.CatalogoNomenclaturaPlaguicidas k2
                 WHERE k2.Codigo COLLATE DATABASE_DEFAULT = p.CodigoCanonico COLLATE DATABASE_DEFAULT
                 ORDER BY k2.IngredienteActivo_Key) k;
    DECLARE @clavesCatalogo INT = @@ROWCOUNT;

    -- 2. Importacion: las filas ya cargadas con el código absorbido pasan al canónico
    UPDATE i
    SET i.Grupo           = k.Agrupador,
        i.CodigoAgrupador = k.Codigo
    FROM dbo.Importacion i
    JOIN @pares p ON i.CodigoAgrupador COLLATE DATABASE_DEFAULT = p.CodigoAbsorbido COLLATE DATABASE_DEFAULT
    CROSS APPLY (SELECT TOP 1 k2.Agrupador, k2.Codigo
                 FROM dbo.CatalogoNomenclaturaPlaguicidas k2
                 WHERE k2.Codigo COLLATE DATABASE_DEFAULT = p.CodigoCanonico COLLATE DATABASE_DEFAULT
                 ORDER BY k2.IngredienteActivo_Key) k;
    DECLARE @filasImportacion INT = @@ROWCOUNT;

    -- Control: ni una fila ni un centavo de CIF pueden cambiar
    DECLARE @filasDespues INT           = (SELECT COUNT(*) FROM dbo.Importacion);
    DECLARE @cifDespues   DECIMAL(18,2) = (SELECT ISNULL(SUM(cif_USD), 0) FROM dbo.Importacion);
    IF @filasDespues <> @filasAntes OR @cifDespues <> @cifAntes
        THROW 50020, 'Control fallido: cambió el número de filas o el CIF total de dbo.Importacion. Se deshace todo.', 1;

    COMMIT TRANSACTION;

    PRINT 'Claves del catalogo movidas al codigo canonico: ' + CAST(@clavesCatalogo AS VARCHAR(20));
    PRINT 'Filas de dbo.Importacion reasignadas:           ' + CAST(@filasImportacion AS VARCHAR(20));
    PRINT 'dbo.Importacion despues: ' + CAST(@filasDespues AS VARCHAR(20)) + ' filas, CIF USD total ' + CONVERT(VARCHAR(40), @cifDespues, 1) + ' (igual que antes).';
    IF @clavesCatalogo = 0 AND @filasImportacion = 0
        PRINT 'No habia nada que unificar (ya estaba aplicado o los codigos no existen en esta base).';
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH
GO
