/* =====================================================================
   PIQ_IA -- Unificar combinaciones de plaguicidas duplicadas, 2ª parte
   (script 21; el 20 ya unificó los primeros 18 pares)
   =====================================================================
   POR QUÉ: el catálogo tiene el MISMO producto con códigos distintos
   porque la combinación está en otro orden ("Cymoxanil + Mancozeb" /
   "Mancozeb + Cymoxanil"), con errores de ortografía o tipeo
   ("Cyprozonazol" / "Ciproconazol"), en inglés y en español
   ("Pyriproxyfen" / "Pyriproxifen"), o con otro separador. En los
   tableros salen como 2 ingredientes. Este script deja UNO solo.

   REGLA (la misma del script 20): en cada caso, el código CANÓNICO es el
   de mayor monto de CIF USD; las filas del otro código (el "absorbido")
   pasan al canónico. En UNA transacción:
     1. dbo.CatalogoNomenclaturaPlaguicidas: toda clave de ingrediente que
        apuntaba al código absorbido pasa a apuntar al canónico (Agrupador
        y Codigo del canónico). Así las PRÓXIMAS cargas ya caen en el
        canónico, sea cual sea el orden/ortografía en que venga escrito.
     2. dbo.Importacion: las filas ya cargadas con el código absorbido
        pasan al Grupo/CodigoAgrupador del canónico.

   QUÉ UNIFICA (28 absorciones, 27 productos): mismos ingredientes en otro
   orden, ortografía o tipeo, inglés vs español y combinaciones de 3 o 4
   componentes. QUÉ NO UNIFICA (a propósito, por dudoso o por indicación):
   Metalaxil vs Metalaxil-M, las variantes de cobre (cobre, cobre metálico,
   sulfatos, hidróxido, oxicloruro), Ciantraniliprole vs Clorantraniliprole,
   Cipermetrina vs Permetrina vs Zeta-cipermetrina, sales (Paraquat /
   Dicloruro de paraquat, Diquat / Diquat dibromida, Glifosato / Sal de
   glifosato de potasio, Propamocarb / Hidrocloruro de propamocarb),
   Haloxifop-metil vs Haloxifop-P-metil, Thiocyclam y su oxalato, el caso
   de cobre con porcentajes (IA-160 / IA-357, pendiente de decisión) y los
   que ya se ven unificados por mayúsculas/tildes (Fosfuro de aluminio,
   Hidróxido de cobre).

   NO toca importes ni cantidades: al final verifica que el número de filas
   y el CIF USD total de dbo.Importacion son EXACTAMENTE los de antes; si
   no, deshace todo (ROLLBACK) y falla.

   RESPALDO AUTOMÁTICO (solo al aplicar, y solo si hay algo que cambiar):
   copia CatalogoNomenclaturaPlaguicidas e Importacion a
   dbo.ZZ_bak21_CatalogoNomenclaturaPlaguicidas_AAAAMMDD y
   dbo.ZZ_bak21_Importacion_AAAAMMDD (fecha del día). El prefijo "bak21"
   evita chocar con las ZZ_bak_..._20261007 del script 20. Si esas tablas ya
   existen NO se vuelven a crear ni se pisan.

   SEGURO DE REPETIR: si ya se corrió, no encuentra nada que cambiar y lo
   dice. Si un código no existe en esa base, el caso se omite.

   COLLATION: todas las comparaciones texto-contra-texto llevan COLLATE
   DATABASE_DEFAULT (evita el error 468).

   CÓMO USARLO
     - Vista previa SIN cambiar nada: poner @SoloVistaPrevia = 1 abajo,
       ejecutar y revisar la tabla.
     - Aplicar: @SoloVistaPrevia = 0 (valor por defecto).
     - SIEMPRE con respaldo antes.

   CÓMO REVERTIR (reemplazar AAAAMMDD por la fecha del respaldo):
       UPDATE c SET c.Agrupador = b.Agrupador, c.Codigo = b.Codigo, c.FechaMod = b.FechaMod
       FROM dbo.CatalogoNomenclaturaPlaguicidas c
       JOIN dbo.ZZ_bak21_CatalogoNomenclaturaPlaguicidas_AAAAMMDD b
         ON b.IngredienteActivo_Key COLLATE DATABASE_DEFAULT = c.IngredienteActivo_Key COLLATE DATABASE_DEFAULT;
       UPDATE i SET i.Grupo = b.Grupo, i.CodigoAgrupador = b.CodigoAgrupador
       FROM dbo.Importacion i
       JOIN dbo.ZZ_bak21_Importacion_AAAAMMDD b ON b.importacionplaguicidaid = i.importacionplaguicidaid;
   Cuando ya no hagan falta, las tablas ZZ_bak21_* se borran con DROP TABLE.
   ===================================================================== */

USE PIQ_IA;
GO

SET NOCOUNT ON;

DECLARE @SoloVistaPrevia BIT = 0;   -- 1 = solo muestra la vista previa

-- (caso, código que se absorbe, código canónico = el de mayor CIF)
DECLARE @pares TABLE (Par INT NOT NULL, CodigoAbsorbido VARCHAR(20) NOT NULL, CodigoCanonico VARCHAR(20) NOT NULL);
INSERT INTO @pares (Par, CodigoAbsorbido, CodigoCanonico) VALUES
    ( 1, 'IA-140', 'IA-311'),   -- Hidrocloruro dee Propamocarb  <-  Clorhidrato de Propamocarb
    ( 2, 'IA-425', 'IA-424'),   -- Pyriproxifen  <-  Pyriproxyfen
    ( 3, 'IA-441', 'IA-440'),   -- Spirotetramat  <-  Spirotetramate
    ( 4, 'IA-303', 'IA-301'),   -- Glufosinato de amonio  <-  Glufosinatodeamonio
    ( 5, 'IA-143', 'IA-004'),   -- 1,3-Dicloropropeno + Cloropricrina  <-  Cloropicrina + 1,3 Dicloropropeno
    ( 6, 'IA-002', 'IA-004'),   -- 1,3-Dicloropropeno + Cloropricrina  <-  1,3 Dicloropropeno + clorpiricina
    ( 7, 'IA-486', 'IA-470'),   -- Thiodicarb  <-  Tiodicarb
    ( 8, 'IA-123', 'IA-174'),   -- Cymoxanil + Mancozeb  <-  Cimoxanil + Mancozeb
    ( 9, 'IA-001', 'IA-003'),   -- 1,3-Dicloropropeno  <-  1,3 Dicloropropeno
    (10, 'IA-404', 'IA-422'),   -- Pyrimetanil  <-  Pirimetanil
    (11, 'IA-069', 'IA-062'),   -- Azoxistrobina + Difenoconazol  <-  Azoxixtrobin + Difenacozole
    (12, 'IA-131', 'IA-130'),   -- Ciproconazol + Trifloxistrobin  <-  Ciproconazol + Trifloxistrobina
    (13, 'IA-435', 'IA-434'),   -- Spinosad  <-  Spinosad (Spinosin A + Spinosin D)
    (14, 'IA-127', 'IA-181'),   -- Cyprozonazol  <-  Ciproconazol
    (15, 'IA-008', 'IA-277'),   -- Fluroxipir + 2,4-D + Amminopyralid  <-  2,4-D + Aminopiralid + Fluroxipir
    (16, 'IA-393', 'IA-394'),   -- Oxyfluorfen  <-  Oxifluorfen
    (17, 'IA-205', 'IA-146'),   -- Clorotalonil + Dimetomorph  <-  Dimetomorf + Clorotalonil
    (18, 'IA-272', 'IA-280'),   -- Fluroxypyr + Picloram  <-  Fluoroxipir + Picloram
    (19, 'IA-289', 'IA-255'),   -- Fluazifop-P-Butil + Fomesafen  <-  Fomesafen + Fluazifop-P-Butyl
    (20, 'IA-484', 'IA-474'),   -- Tiametoxam  <-  Tiametoxan
    (21, 'IA-195', 'IA-178'),   -- Cyprodinil + Difeconazol  <-  Difenoconazol + Cyprodinil
    (22, 'IA-179', 'IA-132'),   -- Ciprodinil + Fludioxonil  <-  Cyprodinil + Fludioxonil
    (23, 'IA-455', 'IA-068'),   -- Azoxistrobina + Tebuconazol  <-  Tebuconazol + Azoxixtrobina
    (24, 'IA-456', 'IA-406'),   -- Prochloraz + Tebuconazole  <-  Tebuconazol + Procloraz
    (25, 'IA-412', 'IA-176'),   -- Cymoxanil + Propamocarb  <-  Propamocarb + Cimoxanil
    (26, 'IA-475', 'IA-018'),   -- Abamectina + Thiamethoxam  <-  Tiametoxam + Abamectina
    (27, 'IA-346', 'IA-324'),   -- Imidacloprid + Lambda cialotrina  <-  Lambda-cialotrina + Imidacloprid
    (28, 'IA-260', 'IA-483');   -- Tiametoxam, Tiabendazol, Fludioxonil, Metalaxi  <-  Fludioxonil + Metalaxil-M + Tiabendazol + Tiam

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
    DECLARE @bakCatalogo NVARCHAR(200) = N'dbo.ZZ_bak21_CatalogoNomenclaturaPlaguicidas_' + @sufijo;
    DECLARE @bakImportacion NVARCHAR(200) = N'dbo.ZZ_bak21_Importacion_' + @sufijo;
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
        THROW 50021, 'Control fallido: cambió el número de filas o el CIF total de dbo.Importacion. Se deshace todo.', 1;

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
