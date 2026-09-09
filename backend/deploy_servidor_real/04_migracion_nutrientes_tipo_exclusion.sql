/* =====================================================================
   PIQ_IA -- Migracion: columna Excluido + backfill de Tipo/Exclusion
   en dbo.Nutrientes y dbo.CatalogoAgrupadorNutrientes
   =====================================================================
   Correr esto DESPUES de 01_crear_base_piq_ia.sql, 02_seed_roles_y_admin.sql
   y 03_cargar_datos_iniciales.sql (necesita que dbo.Nutrientes y
   dbo.CatalogoAgrupadorNutrientes ya existan, con datos reales cargados).

   Aplica en PIQ_IA los mismos cambios de esquema y correccion de datos
   que ya se aplicaron y verificaron en AGREQUIMA (base de desarrollo,
   con la copia de datos reales del cliente) y en Agrequima_Test:

     1. Agrega la columna Excluido (BIT, default 0) a
        CatalogoAgrupadorNutrientes y a Nutrientes -- si ya existen (por
        ejemplo porque este script ya se corrio antes), no hace nada.
     2. Marca Excluido=1 en el catalogo para 29 productos que el cliente
        confirmo que NO corresponden a Nutrientes (plaguicidas que se
        habian colado en el diccionario de productos, ej. Glifosato,
        Atrazina, Boscalid+Pyraclostrobin, etc.).
     3. Propaga ese Excluido=1 hacia TODAS las filas de dbo.Nutrientes ya
        cargadas que coinciden con esos productos (mismo mecanismo que
        sincronizar_agrupador_nutrientes() en el backend, corrido acá
        una sola vez como backfill manual).
     4. Corrige Tipo="." (o vacio) a "Licencias" en dbo.Nutrientes --
        confirmado por el cliente que ese es su significado real.

   Es seguro volver a correr este script las veces que haga falta: los
   ALTER TABLE verifican que la columna no exista todavia, y los UPDATE
   solo tocan filas que todavia no tienen el valor correcto (no
   duplican nada, y una segunda corrida no vuelve a contar las mismas
   filas como "actualizadas").

   Sobre los conteos esperados (paso 5, mas abajo): en AGREQUIMA (la
   base de desarrollo, con una copia mas completa del historico real)
   estos mismos pasos dejaron 216 filas de Nutrientes en Excluido=1 y
   corrigieron 5,750 filas de Tipo="." a "Licencias". Si en PIQ_IA los
   numeros salen MENORES, probablemente es normal: PIQ_IA pudo haberse
   poblado con 03_cargar_datos_iniciales.sql en una fecha distinta, con
   menos meses de historico cargados todavia (ver LEEME.txt). Si salen
   en CERO cuando dbo.Nutrientes sí tiene filas, o muy por encima de los
   valores de referencia, no asumir que salió bien -- revisar antes de
   seguir.
   ===================================================================== */

USE PIQ_IA;
GO


/* ---------------------------------------------------------------------
   1. COLUMNA Excluido (si no existe todavía)
   --------------------------------------------------------------------- */

IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'CatalogoAgrupadorNutrientes' AND COLUMN_NAME = 'Excluido'
)
BEGIN
    ALTER TABLE dbo.CatalogoAgrupadorNutrientes ADD Excluido BIT NOT NULL DEFAULT 0;
    PRINT 'Columna Excluido agregada a dbo.CatalogoAgrupadorNutrientes.';
END
ELSE
    PRINT 'dbo.CatalogoAgrupadorNutrientes.Excluido ya existía -- no se tocó.';
GO

IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'Nutrientes' AND COLUMN_NAME = 'Excluido'
)
BEGIN
    ALTER TABLE dbo.Nutrientes ADD Excluido BIT NOT NULL DEFAULT 0;
    PRINT 'Columna Excluido agregada a dbo.Nutrientes.';
END
ELSE
    PRINT 'dbo.Nutrientes.Excluido ya existía -- no se tocó.';
GO


/* ---------------------------------------------------------------------
   2. MARCAR Excluido=1 EN EL CATÁLOGO (29 productos confirmados por el
      cliente como que NO corresponden a Nutrientes -- ver
      "Agrupador de Fertilizantes Importaciones_RevRMolina_20260904.xlsx",
      columna "Observaciones Rmolina" = "no incluir")
   --------------------------------------------------------------------- */

UPDATE dbo.CatalogoAgrupadorNutrientes
SET Excluido = 1
WHERE Excluido = 0
  AND NombreComercial_Key IN (
    '2,4-D TECNICO',
    'ACTILER 38 WG',
    'AMETRINA TECNICA',
    'ARKO 80 WP',
    'ATRAZINA TECNICA',
    'AZOXYSTROBIN',
    'BASAMID 97 MG',
    'BENOMIL TECNICO',
    'BOSCALID + PYRACLOSTROBIN',
    'BOSCALID+PYRACLOSTROBIN',
    'CEPADIK 5.7 SG',
    'DIMFO 69 WP',
    'DIURON 80 WG',
    'DUO MAXX',
    'EMAMECTIN BENZOATE',
    'GLIFOSATO TECNICO',
    'GLUFOSINATO DE AMONIO TECNICO',
    'KUMULUS 80 WG',
    'MAGNUM',
    'MISIL 60 WP',
    'POLYRAM 70 WG',
    'PROFENOFOS TECNICO',
    'ROVER 50 WG',
    'SALVATE 20 SP',
    'SIEGE PRO 0.73 GR',
    'TODIVIN',
    'VIGILANT',
    'ZIRAM GRANUFLO 76 WG'
  );
PRINT 'Paso 2a (28 claves limpias): ' + CAST(@@ROWCOUNT AS VARCHAR(10)) + ' filas del catálogo marcadas Excluido=1.';
GO

/* La clave #29 ("Glifosato Técnico") en el archivo de origen tiene un
   caracter corrupto en vez de la "é" (problema de codificación del
   archivo del cliente, no nuestro) -- en AGREQUIMA (desarrollo) esa
   MISMA clave corrupta ya existía en el catálogo (cargada previamente
   desde el mismo archivo con el mismo defecto), así que ahí se pudo
   marcar por coincidencia exacta. Ese byte exacto no es portable entre
   servidores/collations, así que acá se busca por patrón: "GLIFOSATO T"
   + un solo carácter cualquiera + "CNICO" -- el "_" es el comodín de UN
   carácter en LIKE. Si en PIQ_IA esa fila no existe (por ejemplo, si
   nunca se cargó ese archivo corrupto en particular), este UPDATE
   simplemente no afecta ninguna fila -- no es un error. */
UPDATE dbo.CatalogoAgrupadorNutrientes
SET Excluido = 1
WHERE Excluido = 0
  AND NombreComercial_Key LIKE 'GLIFOSATO T_CNICO'
  AND NombreComercial_Key <> 'GLIFOSATO TECNICO';
PRINT 'Paso 2b (variante corrupta "Glifosato Técnico"): ' + CAST(@@ROWCOUNT AS VARCHAR(10)) + ' filas adicionales marcadas Excluido=1.';
GO


/* ---------------------------------------------------------------------
   3. PROPAGAR Excluido=1 A dbo.Nutrientes YA CARGADAS
      (mismo cruce normalizado que sincronizar_agrupador_nutrientes():
      TRIM + UPPER + colapsar espacios internos múltiples a uno solo)
   --------------------------------------------------------------------- */

UPDATE n
SET n.Excluido = 1
FROM dbo.Nutrientes n
JOIN dbo.CatalogoAgrupadorNutrientes c
  ON c.NombreComercial_Key = UPPER(LTRIM(RTRIM(
        REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
            n.NombreComercial
        , '  ', ' '), '  ', ' '), '  ', ' '), '  ', ' '), '  ', ' ')
    )))
WHERE c.Excluido = 1
  AND n.Excluido = 0
  AND n.NombreComercial IS NOT NULL;
PRINT 'Paso 3: ' + CAST(@@ROWCOUNT AS VARCHAR(10)) + ' filas de dbo.Nutrientes quedaron Excluido=1 (dejan de mostrarse en dashboards/exports).';
GO


/* ---------------------------------------------------------------------
   4. CORREGIR Tipo="." (o vacío) A "Licencias"
   --------------------------------------------------------------------- */

UPDATE dbo.Nutrientes
SET Tipo = 'Licencias'
WHERE Tipo = '.' OR Tipo IS NULL OR LTRIM(RTRIM(Tipo)) = '';
PRINT 'Paso 4: ' + CAST(@@ROWCOUNT AS VARCHAR(10)) + ' filas de dbo.Nutrientes corregidas de Tipo="." (o vacío) a "Licencias".';
GO


/* ---------------------------------------------------------------------
   5. VERIFICACIÓN -- comparar contra los números de referencia de
      AGREQUIMA (desarrollo): 216 filas Excluido, 5,750 filas de Tipo
      corregidas (ver el encabezado de este archivo para la explicación
      de por qué PIQ_IA puede dar números distintos).
   --------------------------------------------------------------------- */

SELECT
    'Productos Excluido=1 en el catálogo'      AS metrica, COUNT(*) AS valor FROM dbo.CatalogoAgrupadorNutrientes WHERE Excluido = 1
UNION ALL
SELECT
    'Filas de Nutrientes con Excluido=1',         COUNT(*) FROM dbo.Nutrientes WHERE Excluido = 1
UNION ALL
SELECT
    'Filas de Nutrientes con Tipo=''Licencias''', COUNT(*) FROM dbo.Nutrientes WHERE Tipo = 'Licencias'
UNION ALL
SELECT
    'Filas con Tipo="." o vacío restantes (debe ser 0)', COUNT(*)
    FROM dbo.Nutrientes WHERE Tipo = '.' OR Tipo IS NULL OR LTRIM(RTRIM(Tipo)) = ''
UNION ALL
SELECT
    'Total de filas en dbo.Nutrientes (referencia de tamaño)', COUNT(*) FROM dbo.Nutrientes;
GO

PRINT '=== Migración de Tipo/Exclusión en Nutrientes finalizada. ===';
PRINT 'Referencia (AGREQUIMA/desarrollo): 29 productos excluidos, 216 filas de Nutrientes con Excluido=1, 5750 filas de Tipo corregidas.';
PRINT 'Si "Filas con Tipo=. o vacío restantes" NO dio 0, o "Productos Excluido=1" no dio 29, revisar antes de dar esto por bueno.';
GO
