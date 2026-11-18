/* =====================================================================
   Copias fieles de las 6 tablas/vistas del PBIX de Indicadores (Viaticos, DTE y CuidAgro)
   (Script 30 del deploy_servidor_real: el 29 es 29_alinear_collation_homologadas.sql,
   de la rama homologacion; este va despues de ese.)
   =====================================================================
   Crea UNA tabla por cada objeto del servidor de origen, con el MISMO nombre,
   los MISMOS campos, en el MISMO orden y con los MISMOS tipos y nulabilidad.
   Origen: servidor 100.117.95.124,65280, base Agrequima (esquema dbo).
   Fuente de la estructura: INFORMATION_SCHEMA.COLUMNS de ese servidor
   (resumen.txt de la extraccion extraer_indicadores.ps1 del 2026-11-15 20:50).
   Sin resumenes ni transformaciones: los datos se copian tal cual.

     vw_piq_viaticos, Carga_DTE, vw_piq_indicadores_cuidagro,
     vw_piq_ecosistemas_cuidagro, vw_piq_resiliencia_cuidagro, vw_piq_salud_cuidagro

   Nota: en el origen las 5 vw_piq_* son VISTAS y Carga_DTE es una tabla; aqui
   las 6 son TABLAS (copias). No se copian las columnas calculadas del PBIX
   (ClaveNumero, FechaEmisionDTE, Imagen_URL, Fecha, Departamento_Pais): no
   existen en el origen, las calculaba Power BI.

   IDEMPOTENTE: se puede correr las veces que haga falta. Crea solo lo que
   falta y NUNCA borra ni modifica datos de una tabla que ya tiene la
   estructura correcta. Si existe una tabla con ese nombre pero con OTRA
   estructura, no se borra: se aparta como <nombre>_previa y se crea la correcta
   (si ya existe la _previa, se detiene con error y no toca nada).

   SIN "USE": el script crea las tablas en la base a la que esta CONECTADA la
   sesion, para que sirva igual en la base local (Agrequima) y luego en PIQ_IA.
   Para que no se aplique por error en una base de sistema, el primer lote
   revisa DB_NAME(): si es master, model, msdb o tempdb, avisa y desactiva
   la ejecucion del resto (SET NOEXEC ON) hasta el ultimo lote.
   Como correrlo eligiendo la base:
     - SSMS: seleccionar la base en la lista desplegable (o "USE <base>;" a mano)
       antes de ejecutar.
     - sqlcmd:  sqlcmd -S <servidor> -d <base> -i 30_copias_fieles_indicadores.sql
     - PowerShell (estilo aplicar_script24.ps1): Initial Catalog = <base>.

   NO crea indices ni claves: la estructura es identica a la del origen (que no
   expone claves). Se agregan despues, cuando se defina como las lee la web.
   Las columnas de texto toman el collation por defecto de la base donde se
   cree (Modern_Spanish_CI_AS en la local; revisar el de PIQ_IA al publicar).
   ===================================================================== */

SET NOCOUNT ON;
GO

/* ===================== 0. Proteccion: no aplicar en una base de sistema ===================== */
IF DB_NAME() IN (N'master', N'model', N'msdb', N'tempdb')
BEGIN
    RAISERROR('Este script no se aplica en una base de sistema (master, model, msdb o tempdb). Conectese a la base de la aplicacion (Agrequima o PIQ_IA) y vuelva a correrlo. No se hizo ningun cambio.', 16, 1);
    SET NOEXEC ON;
END
GO

PRINT 'Aplicando 30_copias_fieles_indicadores.sql en la base: ' + DB_NAME();
GO

/* ===================== 1. Copias (6) ===================== */
/* ---- dbo.vw_piq_viaticos ---- */
DECLARE @firma_real NVARCHAR(MAX) =
    STUFF((
        SELECT N'|' + c.COLUMN_NAME + N' ' + UPPER(c.DATA_TYPE)
             + CASE WHEN c.DATA_TYPE IN ('varchar', 'nvarchar', 'char', 'nchar')
                    THEN N'(' + CASE WHEN c.CHARACTER_MAXIMUM_LENGTH = -1 THEN N'MAX' ELSE CAST(c.CHARACTER_MAXIMUM_LENGTH AS NVARCHAR(10)) END + N')'
                    WHEN c.DATA_TYPE IN ('decimal', 'numeric')
                    THEN N'(' + CAST(c.NUMERIC_PRECISION AS NVARCHAR(5)) + N',' + CAST(c.NUMERIC_SCALE AS NVARCHAR(5)) + N')'
                    ELSE N'' END
             + N' ' + c.IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS c
        WHERE c.TABLE_SCHEMA = 'dbo' AND c.TABLE_NAME = 'vw_piq_viaticos'
        ORDER BY c.ORDINAL_POSITION
        FOR XML PATH(''), TYPE).value('.', 'NVARCHAR(MAX)'), 1, 1, N'');
IF OBJECT_ID('dbo.vw_piq_viaticos', 'U') IS NOT NULL
   AND ISNULL(@firma_real, N'') <> N'gastodetalleid BIGINT YES|gastoid INT YES|Tipo_gasto VARCHAR(500) YES|nitproveedor VARCHAR(30) YES|proveedor VARCHAR(200) YES|observacion VARCHAR(600) YES|tipomotivoid INT YES|motivo VARCHAR(500) YES|serie VARCHAR(80) YES|documento BIGINT YES|monto DECIMAL(18,2) YES|url_foto VARCHAR(200) YES|fecha_documento DATE YES|fecha_ingreso DATETIME YES|userid INT YES|nombre_completo VARCHAR(150) YES|fechainicial DATE YES|fechafinal DATE YES'
BEGIN
    -- Existe una tabla con ese nombre pero con OTRA estructura (p. ej. un espejo viejo):
    -- NO se borra, se aparta con otro nombre y se crea la correcta.
    IF OBJECT_ID('dbo.vw_piq_viaticos_previa', 'U') IS NOT NULL
        THROW 50029, 'dbo.vw_piq_viaticos tiene otra estructura y ya existe dbo.vw_piq_viaticos_previa. No se toco nada; revisar y renombrar o borrar la _previa a mano.', 1;
    EXEC sp_rename 'dbo.vw_piq_viaticos', 'vw_piq_viaticos_previa';
    PRINT 'dbo.vw_piq_viaticos tenia otra estructura: se renombro a dbo.vw_piq_viaticos_previa (sus datos se conservan).';
END
IF OBJECT_ID('dbo.vw_piq_viaticos', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.vw_piq_viaticos(
        gastodetalleid  BIGINT NULL,
        gastoid         INT NULL,
        Tipo_gasto      VARCHAR(500) NULL,
        nitproveedor    VARCHAR(30) NULL,
        proveedor       VARCHAR(200) NULL,
        observacion     VARCHAR(600) NULL,
        tipomotivoid    INT NULL,
        motivo          VARCHAR(500) NULL,
        serie           VARCHAR(80) NULL,
        documento       BIGINT NULL,
        monto           DECIMAL(18,2) NULL,
        url_foto        VARCHAR(200) NULL,
        fecha_documento DATE NULL,
        fecha_ingreso   DATETIME NULL,
        userid          INT NULL,
        nombre_completo VARCHAR(150) NULL,
        fechainicial    DATE NULL,
        fechafinal      DATE NULL
    );
    PRINT 'Tabla dbo.vw_piq_viaticos creada.';
END
ELSE
    PRINT 'dbo.vw_piq_viaticos ya tiene la estructura correcta -- no se toco.';
GO
/* ---- dbo.Carga_DTE ---- */
DECLARE @firma_real NVARCHAR(MAX) =
    STUFF((
        SELECT N'|' + c.COLUMN_NAME + N' ' + UPPER(c.DATA_TYPE)
             + CASE WHEN c.DATA_TYPE IN ('varchar', 'nvarchar', 'char', 'nchar')
                    THEN N'(' + CASE WHEN c.CHARACTER_MAXIMUM_LENGTH = -1 THEN N'MAX' ELSE CAST(c.CHARACTER_MAXIMUM_LENGTH AS NVARCHAR(10)) END + N')'
                    WHEN c.DATA_TYPE IN ('decimal', 'numeric')
                    THEN N'(' + CAST(c.NUMERIC_PRECISION AS NVARCHAR(5)) + N',' + CAST(c.NUMERIC_SCALE AS NVARCHAR(5)) + N')'
                    ELSE N'' END
             + N' ' + c.IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS c
        WHERE c.TABLE_SCHEMA = 'dbo' AND c.TABLE_NAME = 'Carga_DTE'
        ORDER BY c.ORDINAL_POSITION
        FOR XML PATH(''), TYPE).value('.', 'NVARCHAR(MAX)'), 1, 1, N'');
IF OBJECT_ID('dbo.Carga_DTE', 'U') IS NOT NULL
   AND ISNULL(@firma_real, N'') <> N'dteid BIGINT NO|fechaemision DATETIME YES|numeroautorizacion VARCHAR(100) YES|tipodte VARCHAR(30) YES|serie VARCHAR(100) YES|numero BIGINT YES|nit_emisor VARCHAR(30) YES|nombrecompleto_emisor VARCHAR(350) YES|codigo_establecimiento VARCHAR(20) YES|nombre_establecimiento VARCHAR(350) YES|id_receptor VARCHAR(50) YES|nombre_receptor VARCHAR(350) YES|nit_certificador VARCHAR(30) YES|nombre_certificador VARCHAR(350) YES|moneda VARCHAR(10) YES|monto_total DECIMAL(18,4) YES|estado VARCHAR(20) YES|marca_anulado VARCHAR(20) YES|fecha_anulacion DATETIME YES|iva DECIMAL(18,2) YES|petroleo_impuesto DECIMAL(18,2) YES|turismo_hopedaje_impuesto DECIMAL(18,2) YES|turismo_pasaje_impuesto DECIMAL(18,2) YES|timbre_prensa DECIMAL(18,2) YES|nomberos_impuesto DECIMAL(18,2) YES|tasa_municipal DECIMAL(18,2) YES|bebidas_alcoholicos_impuesto DECIMAL(18,2) YES|tabaco_impuesto DECIMAL(18,2) YES|cemento_impuesto DECIMAL(18,2) YES|bebidas_noalcoholicos_impuesto DECIMAL(18,2) YES|tarifa_portuaria DECIMAL(18,2) YES|fecha_carga DATETIME YES|userid INT YES'
BEGIN
    -- Existe una tabla con ese nombre pero con OTRA estructura (p. ej. un espejo viejo):
    -- NO se borra, se aparta con otro nombre y se crea la correcta.
    IF OBJECT_ID('dbo.Carga_DTE_previa', 'U') IS NOT NULL
        THROW 50029, 'dbo.Carga_DTE tiene otra estructura y ya existe dbo.Carga_DTE_previa. No se toco nada; revisar y renombrar o borrar la _previa a mano.', 1;
    EXEC sp_rename 'dbo.Carga_DTE', 'Carga_DTE_previa';
    PRINT 'dbo.Carga_DTE tenia otra estructura: se renombro a dbo.Carga_DTE_previa (sus datos se conservan).';
END
IF OBJECT_ID('dbo.Carga_DTE', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.Carga_DTE(
        dteid                          BIGINT NOT NULL,
        fechaemision                   DATETIME NULL,
        numeroautorizacion             VARCHAR(100) NULL,
        tipodte                        VARCHAR(30) NULL,
        serie                          VARCHAR(100) NULL,
        numero                         BIGINT NULL,
        nit_emisor                     VARCHAR(30) NULL,
        nombrecompleto_emisor          VARCHAR(350) NULL,
        codigo_establecimiento         VARCHAR(20) NULL,
        nombre_establecimiento         VARCHAR(350) NULL,
        id_receptor                    VARCHAR(50) NULL,
        nombre_receptor                VARCHAR(350) NULL,
        nit_certificador               VARCHAR(30) NULL,
        nombre_certificador            VARCHAR(350) NULL,
        moneda                         VARCHAR(10) NULL,
        monto_total                    DECIMAL(18,4) NULL,
        estado                         VARCHAR(20) NULL,
        marca_anulado                  VARCHAR(20) NULL,
        fecha_anulacion                DATETIME NULL,
        iva                            DECIMAL(18,2) NULL,
        petroleo_impuesto              DECIMAL(18,2) NULL,
        turismo_hopedaje_impuesto      DECIMAL(18,2) NULL,
        turismo_pasaje_impuesto        DECIMAL(18,2) NULL,
        timbre_prensa                  DECIMAL(18,2) NULL,
        nomberos_impuesto              DECIMAL(18,2) NULL,
        tasa_municipal                 DECIMAL(18,2) NULL,
        bebidas_alcoholicos_impuesto   DECIMAL(18,2) NULL,
        tabaco_impuesto                DECIMAL(18,2) NULL,
        cemento_impuesto               DECIMAL(18,2) NULL,
        bebidas_noalcoholicos_impuesto DECIMAL(18,2) NULL,
        tarifa_portuaria               DECIMAL(18,2) NULL,
        fecha_carga                    DATETIME NULL,
        userid                         INT NULL
    );
    PRINT 'Tabla dbo.Carga_DTE creada.';
END
ELSE
    PRINT 'dbo.Carga_DTE ya tiene la estructura correcta -- no se toco.';
GO
/* ---- dbo.vw_piq_indicadores_cuidagro ---- */
DECLARE @firma_real NVARCHAR(MAX) =
    STUFF((
        SELECT N'|' + c.COLUMN_NAME + N' ' + UPPER(c.DATA_TYPE)
             + CASE WHEN c.DATA_TYPE IN ('varchar', 'nvarchar', 'char', 'nchar')
                    THEN N'(' + CASE WHEN c.CHARACTER_MAXIMUM_LENGTH = -1 THEN N'MAX' ELSE CAST(c.CHARACTER_MAXIMUM_LENGTH AS NVARCHAR(10)) END + N')'
                    WHEN c.DATA_TYPE IN ('decimal', 'numeric')
                    THEN N'(' + CAST(c.NUMERIC_PRECISION AS NVARCHAR(5)) + N',' + CAST(c.NUMERIC_SCALE AS NVARCHAR(5)) + N')'
                    ELSE N'' END
             + N' ' + c.IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS c
        WHERE c.TABLE_SCHEMA = 'dbo' AND c.TABLE_NAME = 'vw_piq_indicadores_cuidagro'
        ORDER BY c.ORDINAL_POSITION
        FOR XML PATH(''), TYPE).value('.', 'NVARCHAR(MAX)'), 1, 1, N'');
IF OBJECT_ID('dbo.vw_piq_indicadores_cuidagro', 'U') IS NOT NULL
   AND ISNULL(@firma_real, N'') <> N'agriculturaSostenibleid BIGINT NO|tipo_indicador VARCHAR(68) YES|tipo_alianza VARCHAR(12) NO|cantidad INT YES|aliado VARCHAR(300) YES|Departamento VARCHAR(250) YES|Municipio VARCHAR(250) YES|Organizacion VARCHAR(250) YES|cantidadhombres INT YES|cantidadmujeres INT YES|Rango_edad VARCHAR(250) YES|observaciones VARCHAR(500) YES|responsable VARCHAR(300) YES|telefono VARCHAR(30) YES|Dirigido_a VARCHAR(250) YES|tema VARCHAR(250) YES|Disciplina VARCHAR(250) YES|Tipo_equipo VARCHAR(250) YES|fotoagenda_url VARCHAR(300) YES|fotoevento_url VARCHAR(300) YES|Region VARCHAR(250) YES|parcela VARCHAR(300) YES|beneficiario VARCHAR(300) YES|hectarea DECIMAL(15,2) YES|fotoparcela_url VARCHAR(300) YES|longitud VARCHAR(30) YES|latitud VARCHAR(30) YES|Estado_ind INT YES|Usuario VARCHAR(150) YES|fechaingreso DATETIME YES|Cultivo VARCHAR(250) YES|Estado_cultivo INT YES'
BEGIN
    -- Existe una tabla con ese nombre pero con OTRA estructura (p. ej. un espejo viejo):
    -- NO se borra, se aparta con otro nombre y se crea la correcta.
    IF OBJECT_ID('dbo.vw_piq_indicadores_cuidagro_previa', 'U') IS NOT NULL
        THROW 50029, 'dbo.vw_piq_indicadores_cuidagro tiene otra estructura y ya existe dbo.vw_piq_indicadores_cuidagro_previa. No se toco nada; revisar y renombrar o borrar la _previa a mano.', 1;
    EXEC sp_rename 'dbo.vw_piq_indicadores_cuidagro', 'vw_piq_indicadores_cuidagro_previa';
    PRINT 'dbo.vw_piq_indicadores_cuidagro tenia otra estructura: se renombro a dbo.vw_piq_indicadores_cuidagro_previa (sus datos se conservan).';
END
IF OBJECT_ID('dbo.vw_piq_indicadores_cuidagro', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.vw_piq_indicadores_cuidagro(
        agriculturaSostenibleid BIGINT NOT NULL,
        tipo_indicador          VARCHAR(68) NULL,
        tipo_alianza            VARCHAR(12) NOT NULL,
        cantidad                INT NULL,
        aliado                  VARCHAR(300) NULL,
        Departamento            VARCHAR(250) NULL,
        Municipio               VARCHAR(250) NULL,
        Organizacion            VARCHAR(250) NULL,
        cantidadhombres         INT NULL,
        cantidadmujeres         INT NULL,
        Rango_edad              VARCHAR(250) NULL,
        observaciones           VARCHAR(500) NULL,
        responsable             VARCHAR(300) NULL,
        telefono                VARCHAR(30) NULL,
        Dirigido_a              VARCHAR(250) NULL,
        tema                    VARCHAR(250) NULL,
        Disciplina              VARCHAR(250) NULL,
        Tipo_equipo             VARCHAR(250) NULL,
        fotoagenda_url          VARCHAR(300) NULL,
        fotoevento_url          VARCHAR(300) NULL,
        Region                  VARCHAR(250) NULL,
        parcela                 VARCHAR(300) NULL,
        beneficiario            VARCHAR(300) NULL,
        hectarea                DECIMAL(15,2) NULL,
        fotoparcela_url         VARCHAR(300) NULL,
        longitud                VARCHAR(30) NULL,
        latitud                 VARCHAR(30) NULL,
        Estado_ind              INT NULL,
        Usuario                 VARCHAR(150) NULL,
        fechaingreso            DATETIME NULL,
        Cultivo                 VARCHAR(250) NULL,
        Estado_cultivo          INT NULL
    );
    PRINT 'Tabla dbo.vw_piq_indicadores_cuidagro creada.';
END
ELSE
    PRINT 'dbo.vw_piq_indicadores_cuidagro ya tiene la estructura correcta -- no se toco.';
GO
/* ---- dbo.vw_piq_ecosistemas_cuidagro ---- */
DECLARE @firma_real NVARCHAR(MAX) =
    STUFF((
        SELECT N'|' + c.COLUMN_NAME + N' ' + UPPER(c.DATA_TYPE)
             + CASE WHEN c.DATA_TYPE IN ('varchar', 'nvarchar', 'char', 'nchar')
                    THEN N'(' + CASE WHEN c.CHARACTER_MAXIMUM_LENGTH = -1 THEN N'MAX' ELSE CAST(c.CHARACTER_MAXIMUM_LENGTH AS NVARCHAR(10)) END + N')'
                    WHEN c.DATA_TYPE IN ('decimal', 'numeric')
                    THEN N'(' + CAST(c.NUMERIC_PRECISION AS NVARCHAR(5)) + N',' + CAST(c.NUMERIC_SCALE AS NVARCHAR(5)) + N')'
                    ELSE N'' END
             + N' ' + c.IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS c
        WHERE c.TABLE_SCHEMA = 'dbo' AND c.TABLE_NAME = 'vw_piq_ecosistemas_cuidagro'
        ORDER BY c.ORDINAL_POSITION
        FOR XML PATH(''), TYPE).value('.', 'NVARCHAR(MAX)'), 1, 1, N'');
IF OBJECT_ID('dbo.vw_piq_ecosistemas_cuidagro', 'U') IS NOT NULL
   AND ISNULL(@firma_real, N'') <> N'IdActividad BIGINT NO|Programa NVARCHAR(22) NO|Actividad NVARCHAR(41) NO|Cantidad DECIMAL(15,2) YES|Hombres INT YES|Mujeres INT YES|LitrosAgua DECIMAL(15,2) YES|Kilos DECIMAL(15,2) YES|Departamento VARCHAR(250) YES|Municipio VARCHAR(250) YES|Rango_edad VARCHAR(250) YES|Tema VARCHAR(250) YES|Responsable VARCHAR(200) YES|Organizacion VARCHAR(400) YES|FechaInicio DATE YES|FechaFin DATE YES|longitud VARCHAR(40) YES|latitud VARCHAR(40) YES|Usuario VARCHAR(150) YES|FechaIngreso DATETIME YES|FechaMod DATETIME YES'
BEGIN
    -- Existe una tabla con ese nombre pero con OTRA estructura (p. ej. un espejo viejo):
    -- NO se borra, se aparta con otro nombre y se crea la correcta.
    IF OBJECT_ID('dbo.vw_piq_ecosistemas_cuidagro_previa', 'U') IS NOT NULL
        THROW 50029, 'dbo.vw_piq_ecosistemas_cuidagro tiene otra estructura y ya existe dbo.vw_piq_ecosistemas_cuidagro_previa. No se toco nada; revisar y renombrar o borrar la _previa a mano.', 1;
    EXEC sp_rename 'dbo.vw_piq_ecosistemas_cuidagro', 'vw_piq_ecosistemas_cuidagro_previa';
    PRINT 'dbo.vw_piq_ecosistemas_cuidagro tenia otra estructura: se renombro a dbo.vw_piq_ecosistemas_cuidagro_previa (sus datos se conservan).';
END
IF OBJECT_ID('dbo.vw_piq_ecosistemas_cuidagro', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.vw_piq_ecosistemas_cuidagro(
        IdActividad  BIGINT NOT NULL,
        Programa     NVARCHAR(22) NOT NULL,
        Actividad    NVARCHAR(41) NOT NULL,
        Cantidad     DECIMAL(15,2) NULL,
        Hombres      INT NULL,
        Mujeres      INT NULL,
        LitrosAgua   DECIMAL(15,2) NULL,
        Kilos        DECIMAL(15,2) NULL,
        Departamento VARCHAR(250) NULL,
        Municipio    VARCHAR(250) NULL,
        Rango_edad   VARCHAR(250) NULL,
        Tema         VARCHAR(250) NULL,
        Responsable  VARCHAR(200) NULL,
        Organizacion VARCHAR(400) NULL,
        FechaInicio  DATE NULL,
        FechaFin     DATE NULL,
        longitud     VARCHAR(40) NULL,
        latitud      VARCHAR(40) NULL,
        Usuario      VARCHAR(150) NULL,
        FechaIngreso DATETIME NULL,
        FechaMod     DATETIME NULL
    );
    PRINT 'Tabla dbo.vw_piq_ecosistemas_cuidagro creada.';
END
ELSE
    PRINT 'dbo.vw_piq_ecosistemas_cuidagro ya tiene la estructura correcta -- no se toco.';
GO
/* ---- dbo.vw_piq_resiliencia_cuidagro ---- */
DECLARE @firma_real NVARCHAR(MAX) =
    STUFF((
        SELECT N'|' + c.COLUMN_NAME + N' ' + UPPER(c.DATA_TYPE)
             + CASE WHEN c.DATA_TYPE IN ('varchar', 'nvarchar', 'char', 'nchar')
                    THEN N'(' + CASE WHEN c.CHARACTER_MAXIMUM_LENGTH = -1 THEN N'MAX' ELSE CAST(c.CHARACTER_MAXIMUM_LENGTH AS NVARCHAR(10)) END + N')'
                    WHEN c.DATA_TYPE IN ('decimal', 'numeric')
                    THEN N'(' + CAST(c.NUMERIC_PRECISION AS NVARCHAR(5)) + N',' + CAST(c.NUMERIC_SCALE AS NVARCHAR(5)) + N')'
                    ELSE N'' END
             + N' ' + c.IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS c
        WHERE c.TABLE_SCHEMA = 'dbo' AND c.TABLE_NAME = 'vw_piq_resiliencia_cuidagro'
        ORDER BY c.ORDINAL_POSITION
        FOR XML PATH(''), TYPE).value('.', 'NVARCHAR(MAX)'), 1, 1, N'');
IF OBJECT_ID('dbo.vw_piq_resiliencia_cuidagro', 'U') IS NOT NULL
   AND ISNULL(@firma_real, N'') <> N'IdActividad BIGINT NO|Programa NVARCHAR(11) NO|Hombres INT YES|Mujeres INT YES|TotalPersonas INT YES|CantidadHuertos INT YES|Metros DECIMAL(15,2) YES|Departamento VARCHAR(250) YES|Municipio VARCHAR(250) YES|Rango_edad VARCHAR(250) YES|Organizacion VARCHAR(250) YES|longitud VARCHAR(40) YES|latitud VARCHAR(40) YES|Usuario VARCHAR(150) YES|FechaIngreso DATETIME YES|FechaMod DATETIME YES'
BEGIN
    -- Existe una tabla con ese nombre pero con OTRA estructura (p. ej. un espejo viejo):
    -- NO se borra, se aparta con otro nombre y se crea la correcta.
    IF OBJECT_ID('dbo.vw_piq_resiliencia_cuidagro_previa', 'U') IS NOT NULL
        THROW 50029, 'dbo.vw_piq_resiliencia_cuidagro tiene otra estructura y ya existe dbo.vw_piq_resiliencia_cuidagro_previa. No se toco nada; revisar y renombrar o borrar la _previa a mano.', 1;
    EXEC sp_rename 'dbo.vw_piq_resiliencia_cuidagro', 'vw_piq_resiliencia_cuidagro_previa';
    PRINT 'dbo.vw_piq_resiliencia_cuidagro tenia otra estructura: se renombro a dbo.vw_piq_resiliencia_cuidagro_previa (sus datos se conservan).';
END
IF OBJECT_ID('dbo.vw_piq_resiliencia_cuidagro', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.vw_piq_resiliencia_cuidagro(
        IdActividad     BIGINT NOT NULL,
        Programa        NVARCHAR(11) NOT NULL,
        Hombres         INT NULL,
        Mujeres         INT NULL,
        TotalPersonas   INT NULL,
        CantidadHuertos INT NULL,
        Metros          DECIMAL(15,2) NULL,
        Departamento    VARCHAR(250) NULL,
        Municipio       VARCHAR(250) NULL,
        Rango_edad      VARCHAR(250) NULL,
        Organizacion    VARCHAR(250) NULL,
        longitud        VARCHAR(40) NULL,
        latitud         VARCHAR(40) NULL,
        Usuario         VARCHAR(150) NULL,
        FechaIngreso    DATETIME NULL,
        FechaMod        DATETIME NULL
    );
    PRINT 'Tabla dbo.vw_piq_resiliencia_cuidagro creada.';
END
ELSE
    PRINT 'dbo.vw_piq_resiliencia_cuidagro ya tiene la estructura correcta -- no se toco.';
GO
/* ---- dbo.vw_piq_salud_cuidagro ---- */
DECLARE @firma_real NVARCHAR(MAX) =
    STUFF((
        SELECT N'|' + c.COLUMN_NAME + N' ' + UPPER(c.DATA_TYPE)
             + CASE WHEN c.DATA_TYPE IN ('varchar', 'nvarchar', 'char', 'nchar')
                    THEN N'(' + CASE WHEN c.CHARACTER_MAXIMUM_LENGTH = -1 THEN N'MAX' ELSE CAST(c.CHARACTER_MAXIMUM_LENGTH AS NVARCHAR(10)) END + N')'
                    WHEN c.DATA_TYPE IN ('decimal', 'numeric')
                    THEN N'(' + CAST(c.NUMERIC_PRECISION AS NVARCHAR(5)) + N',' + CAST(c.NUMERIC_SCALE AS NVARCHAR(5)) + N')'
                    ELSE N'' END
             + N' ' + c.IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS c
        WHERE c.TABLE_SCHEMA = 'dbo' AND c.TABLE_NAME = 'vw_piq_salud_cuidagro'
        ORDER BY c.ORDINAL_POSITION
        FOR XML PATH(''), TYPE).value('.', 'NVARCHAR(MAX)'), 1, 1, N'');
IF OBJECT_ID('dbo.vw_piq_salud_cuidagro', 'U') IS NOT NULL
   AND ISNULL(@firma_real, N'') <> N'IdActividad BIGINT NO|Programa NVARCHAR(5) NO|Actividad VARCHAR(250) YES|Hombres INT NO|Mujeres INT NO|Total INT YES|Departamento VARCHAR(250) YES|Municipio VARCHAR(250) YES|Lugar VARCHAR(300) YES|contacto VARCHAR(300) YES|telefono VARCHAR(300) YES|RangoEdad VARCHAR(250) YES|longitud VARCHAR(40) YES|latitud VARCHAR(40) YES|Usuario VARCHAR(150) YES|FechaIngreso DATETIME YES'
BEGIN
    -- Existe una tabla con ese nombre pero con OTRA estructura (p. ej. un espejo viejo):
    -- NO se borra, se aparta con otro nombre y se crea la correcta.
    IF OBJECT_ID('dbo.vw_piq_salud_cuidagro_previa', 'U') IS NOT NULL
        THROW 50029, 'dbo.vw_piq_salud_cuidagro tiene otra estructura y ya existe dbo.vw_piq_salud_cuidagro_previa. No se toco nada; revisar y renombrar o borrar la _previa a mano.', 1;
    EXEC sp_rename 'dbo.vw_piq_salud_cuidagro', 'vw_piq_salud_cuidagro_previa';
    PRINT 'dbo.vw_piq_salud_cuidagro tenia otra estructura: se renombro a dbo.vw_piq_salud_cuidagro_previa (sus datos se conservan).';
END
IF OBJECT_ID('dbo.vw_piq_salud_cuidagro', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.vw_piq_salud_cuidagro(
        IdActividad  BIGINT NOT NULL,
        Programa     NVARCHAR(5) NOT NULL,
        Actividad    VARCHAR(250) NULL,
        Hombres      INT NOT NULL,
        Mujeres      INT NOT NULL,
        Total        INT NULL,
        Departamento VARCHAR(250) NULL,
        Municipio    VARCHAR(250) NULL,
        Lugar        VARCHAR(300) NULL,
        contacto     VARCHAR(300) NULL,
        telefono     VARCHAR(300) NULL,
        RangoEdad    VARCHAR(250) NULL,
        longitud     VARCHAR(40) NULL,
        latitud      VARCHAR(40) NULL,
        Usuario      VARCHAR(150) NULL,
        FechaIngreso DATETIME NULL
    );
    PRINT 'Tabla dbo.vw_piq_salud_cuidagro creada.';
END
ELSE
    PRINT 'dbo.vw_piq_salud_cuidagro ya tiene la estructura correcta -- no se toco.';
GO
/* ===================== 2. Verificacion ===================== */
-- Cada objeto debe mostrar estado = OK (mismos campos, tipos, nulabilidad y orden que el origen).
SELECT e.objeto,
       e.campos_esperados,
       (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS c
         WHERE c.TABLE_SCHEMA = 'dbo' AND c.TABLE_NAME = e.objeto) AS campos_en_la_base,
       CASE WHEN ISNULL(f.firma, N'') = e.firma_esperada THEN 'OK' ELSE 'REVISAR' END AS estado
FROM (VALUES
        (N'vw_piq_viaticos', 18, N'gastodetalleid BIGINT YES|gastoid INT YES|Tipo_gasto VARCHAR(500) YES|nitproveedor VARCHAR(30) YES|proveedor VARCHAR(200) YES|observacion VARCHAR(600) YES|tipomotivoid INT YES|motivo VARCHAR(500) YES|serie VARCHAR(80) YES|documento BIGINT YES|monto DECIMAL(18,2) YES|url_foto VARCHAR(200) YES|fecha_documento DATE YES|fecha_ingreso DATETIME YES|userid INT YES|nombre_completo VARCHAR(150) YES|fechainicial DATE YES|fechafinal DATE YES'),
        (N'Carga_DTE', 33, N'dteid BIGINT NO|fechaemision DATETIME YES|numeroautorizacion VARCHAR(100) YES|tipodte VARCHAR(30) YES|serie VARCHAR(100) YES|numero BIGINT YES|nit_emisor VARCHAR(30) YES|nombrecompleto_emisor VARCHAR(350) YES|codigo_establecimiento VARCHAR(20) YES|nombre_establecimiento VARCHAR(350) YES|id_receptor VARCHAR(50) YES|nombre_receptor VARCHAR(350) YES|nit_certificador VARCHAR(30) YES|nombre_certificador VARCHAR(350) YES|moneda VARCHAR(10) YES|monto_total DECIMAL(18,4) YES|estado VARCHAR(20) YES|marca_anulado VARCHAR(20) YES|fecha_anulacion DATETIME YES|iva DECIMAL(18,2) YES|petroleo_impuesto DECIMAL(18,2) YES|turismo_hopedaje_impuesto DECIMAL(18,2) YES|turismo_pasaje_impuesto DECIMAL(18,2) YES|timbre_prensa DECIMAL(18,2) YES|nomberos_impuesto DECIMAL(18,2) YES|tasa_municipal DECIMAL(18,2) YES|bebidas_alcoholicos_impuesto DECIMAL(18,2) YES|tabaco_impuesto DECIMAL(18,2) YES|cemento_impuesto DECIMAL(18,2) YES|bebidas_noalcoholicos_impuesto DECIMAL(18,2) YES|tarifa_portuaria DECIMAL(18,2) YES|fecha_carga DATETIME YES|userid INT YES'),
        (N'vw_piq_indicadores_cuidagro', 32, N'agriculturaSostenibleid BIGINT NO|tipo_indicador VARCHAR(68) YES|tipo_alianza VARCHAR(12) NO|cantidad INT YES|aliado VARCHAR(300) YES|Departamento VARCHAR(250) YES|Municipio VARCHAR(250) YES|Organizacion VARCHAR(250) YES|cantidadhombres INT YES|cantidadmujeres INT YES|Rango_edad VARCHAR(250) YES|observaciones VARCHAR(500) YES|responsable VARCHAR(300) YES|telefono VARCHAR(30) YES|Dirigido_a VARCHAR(250) YES|tema VARCHAR(250) YES|Disciplina VARCHAR(250) YES|Tipo_equipo VARCHAR(250) YES|fotoagenda_url VARCHAR(300) YES|fotoevento_url VARCHAR(300) YES|Region VARCHAR(250) YES|parcela VARCHAR(300) YES|beneficiario VARCHAR(300) YES|hectarea DECIMAL(15,2) YES|fotoparcela_url VARCHAR(300) YES|longitud VARCHAR(30) YES|latitud VARCHAR(30) YES|Estado_ind INT YES|Usuario VARCHAR(150) YES|fechaingreso DATETIME YES|Cultivo VARCHAR(250) YES|Estado_cultivo INT YES'),
        (N'vw_piq_ecosistemas_cuidagro', 21, N'IdActividad BIGINT NO|Programa NVARCHAR(22) NO|Actividad NVARCHAR(41) NO|Cantidad DECIMAL(15,2) YES|Hombres INT YES|Mujeres INT YES|LitrosAgua DECIMAL(15,2) YES|Kilos DECIMAL(15,2) YES|Departamento VARCHAR(250) YES|Municipio VARCHAR(250) YES|Rango_edad VARCHAR(250) YES|Tema VARCHAR(250) YES|Responsable VARCHAR(200) YES|Organizacion VARCHAR(400) YES|FechaInicio DATE YES|FechaFin DATE YES|longitud VARCHAR(40) YES|latitud VARCHAR(40) YES|Usuario VARCHAR(150) YES|FechaIngreso DATETIME YES|FechaMod DATETIME YES'),
        (N'vw_piq_resiliencia_cuidagro', 16, N'IdActividad BIGINT NO|Programa NVARCHAR(11) NO|Hombres INT YES|Mujeres INT YES|TotalPersonas INT YES|CantidadHuertos INT YES|Metros DECIMAL(15,2) YES|Departamento VARCHAR(250) YES|Municipio VARCHAR(250) YES|Rango_edad VARCHAR(250) YES|Organizacion VARCHAR(250) YES|longitud VARCHAR(40) YES|latitud VARCHAR(40) YES|Usuario VARCHAR(150) YES|FechaIngreso DATETIME YES|FechaMod DATETIME YES'),
        (N'vw_piq_salud_cuidagro', 16, N'IdActividad BIGINT NO|Programa NVARCHAR(5) NO|Actividad VARCHAR(250) YES|Hombres INT NO|Mujeres INT NO|Total INT YES|Departamento VARCHAR(250) YES|Municipio VARCHAR(250) YES|Lugar VARCHAR(300) YES|contacto VARCHAR(300) YES|telefono VARCHAR(300) YES|RangoEdad VARCHAR(250) YES|longitud VARCHAR(40) YES|latitud VARCHAR(40) YES|Usuario VARCHAR(150) YES|FechaIngreso DATETIME YES')
) AS e(objeto, campos_esperados, firma_esperada)
CROSS APPLY (
    SELECT
        STUFF((
        SELECT N'|' + c.COLUMN_NAME + N' ' + UPPER(c.DATA_TYPE)
             + CASE WHEN c.DATA_TYPE IN ('varchar', 'nvarchar', 'char', 'nchar')
                    THEN N'(' + CASE WHEN c.CHARACTER_MAXIMUM_LENGTH = -1 THEN N'MAX' ELSE CAST(c.CHARACTER_MAXIMUM_LENGTH AS NVARCHAR(10)) END + N')'
                    WHEN c.DATA_TYPE IN ('decimal', 'numeric')
                    THEN N'(' + CAST(c.NUMERIC_PRECISION AS NVARCHAR(5)) + N',' + CAST(c.NUMERIC_SCALE AS NVARCHAR(5)) + N')'
                    ELSE N'' END
             + N' ' + c.IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS c
        WHERE c.TABLE_SCHEMA = 'dbo' AND c.TABLE_NAME = e.objeto
        ORDER BY c.ORDINAL_POSITION
        FOR XML PATH(''), TYPE).value('.', 'NVARCHAR(MAX)'), 1, 1, N'') AS firma
) AS f
ORDER BY e.objeto;
GO

PRINT '=== 30_copias_fieles_indicadores.sql aplicado en ' + DB_NAME() + '. Siguiente paso: cargar los datos (CSV o sincronizacion). ===';
GO

/* ===================== 3. Cierre de la proteccion ===================== */
SET NOEXEC OFF;
GO
