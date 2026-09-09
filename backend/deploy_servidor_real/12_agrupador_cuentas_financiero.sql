/* =====================================================================
   PIQ_IA -- Agrupador de cuentas contables (módulo Financiero, "Grupo"
   en las 4 páginas de Estados Financieros)
   =====================================================================
   Hasta ahora, la columna "Grupo" de las 4 páginas de Estados
   Financieros (Ingresos y desembolsos mensual/acumulado, Balance
   general mensual/comparativo) salía de vw_piq_balance_general.Nom_n1 /
   vw_catalogo_cuentas.Nombre_n1 -- eso no era el agrupador contable
   real del cliente, así que la columna quedaba mal.

   Este script crea dbo.CatalogoAgrupadorCuentas con el agrupador real
   que dio el cliente (Egresos, Ingresos, Activo, Pasivo, Patrimonio --
   Presupuestos/Importaciones/Centros de Costo quedan pendientes, vienen
   de otra hoja del mismo Excel todavía no cargada) y actualiza
   backend/app/services/dashboard_financiero.py (ya desplegado en el
   propio código de la app, no en SQL) para usarlo con un
   emparejamiento jerárquico por código de cuenta:

       1. Nivel 3 -- coincidencia EXACTA contra el código completo.
       2. Si no hay, Nivel 2 -- contra los primeros 6 dígitos.
       3. Si tampoco, Nivel 1 -- contra los primeros 4 dígitos.

   El primero que coincide gana (ver
   backend/app/services/agrupador_cuentas.py).

   Es seguro volver a correr este script las veces que haga falta: el
   INSERT usa un anti-join (WHERE NOT EXISTS) sobre (TipoAgrupador,
   Codigo), así que no duplica filas ya cargadas.
   ===================================================================== */

USE PIQ_IA;
GO

IF OBJECT_ID('dbo.CatalogoAgrupadorCuentas') IS NULL
BEGIN
    CREATE TABLE dbo.CatalogoAgrupadorCuentas(
        TipoAgrupador VARCHAR(20) NOT NULL,
        Orden         INT NOT NULL,
        Nivel         INT NOT NULL,
        Codigo        VARCHAR(20) NOT NULL,
        Nombre        VARCHAR(150) NOT NULL,
        CONSTRAINT PK_CatalogoAgrupadorCuentas PRIMARY KEY CLUSTERED (TipoAgrupador, Codigo)
    );
    PRINT 'Tabla dbo.CatalogoAgrupadorCuentas creada.';
END
ELSE
    PRINT 'dbo.CatalogoAgrupadorCuentas ya existía -- no se tocó su estructura.';
GO

INSERT INTO dbo.CatalogoAgrupadorCuentas (TipoAgrupador, Orden, Nivel, Codigo, Nombre)
SELECT v.TipoAgrupador, v.Orden, v.Nivel, v.Codigo, v.Nombre
FROM (VALUES
    ('Egresos', 1, 1, '5101', 'Sueldos Bonificaciones y Prestaciones de Ley'),
    ('Egresos', 2, 1, '5102', 'Gastos Generales de Funcionamiento'),
    ('Egresos', 3, 3, '510201011', 'Cuentas Incobrables'),
    ('Egresos', 4, 2, '510206', 'Suscripciones y Membresías'),
    ('Egresos', 5, 1, '5106', 'Gastos de Viaje al Exterior'),
    ('Egresos', 6, 1, '5103', 'Literatura y Material para Capacitación Programa Educación'),
    ('Egresos', 7, 1, '5105', 'Viáticos e Insumos Programa Cuidagro'),
    ('Egresos', 7, 1, '5104', 'Viáticos e Insumos Programa Cuidagro'),
    ('Egresos', 8, 1, '5107', 'Imagen y Divulgación'),
    ('Egresos', 9, 1, '5108', 'Auditoria'),
    ('Egresos', 10, 1, '5109', 'Honorarios Profesionales'),
    ('Egresos', 11, 1, '5110', 'Viáticos Mantenimiento Incineración Programa CampoLimpio'),
    ('Egresos', 12, 1, '5111', 'Imprevistos'),
    ('Egresos', 13, 1, '5112', 'Gastos de Apoyo a Instituciones'),
    ('Egresos', 14, 1, '5113', 'Proyectos / Fundacion Mayan Field'),
    ('Egresos', 15, 1, '5114', 'Gastos Proyectos de Investigación'),
    ('Egresos', 16, 1, '5115', 'Provisión de Indemnización'),
    ('Egresos', 17, 1, '5116', 'Provisión de Depreciaciones'),
    ('Egresos', 18, 1, '5117', 'Donaciones'),
    ('Egresos', 19, 1, '5201', 'Gastos Financieros'),
    ('Egresos', 19, 1, '5202', 'Gastos Financieros'),
    ('Egresos', 20, 3, '510701017', 'Proyecto SPMF Croplife'),
    ('Ingresos', 1, 2, '410101', 'Cuotas Asociados'),
    ('Ingresos', 2, 2, '410104', 'Cuotas 4.5 por Millar'),
    ('Ingresos', 3, 2, '410103', 'Ingresos Facturados'),
    ('Ingresos', 4, 2, '410102', 'Donación'),
    ('Ingresos', 5, 2, '410105', 'Intereses bancarios e inversiones'),
    ('Activo', 6, 1, '1101', 'Caja y Bancos'),
    ('Activo', 7, 2, '110201', 'Cuentas por Cobrar Asociados'),
    ('Activo', 8, 3, '110204001', 'Cuentas por Cobrar BANRURAL'),
    ('Activo', 9, 1, '1102', 'Cuentas por Cobrar'),
    ('Activo', 10, 1, '1104', 'Inventario Sellos'),
    ('Activo', 11, 1, '1201', 'Propiedad y equipo'),
    ('Activo', 12, 1, '1202', 'Gastos diferidos'),
    ('Activo', 13, 1, '1103', 'Impuestos por cobrar'),
    ('Pasivo', 1, 2, '210102', 'Impuestos por pagar'),
    ('Pasivo', 2, 2, '210101', 'Cuentas por pagar'),
    ('Pasivo', 3, 2, '210103', 'Prestaciones laborales'),
    ('Pasivo', 4, 2, '210104', 'Ingresos anticipados'),
    ('Pasivo', 5, 3, '210105001', 'Fondos por aplicar acumulado'),
    ('Pasivo', 6, 3, '210105002', 'Fondos por aplicar caso judicial BANRURAL'),
    ('Patrimonio', 1, 3, '310101001', 'Patrimonio activos fijos')
) AS v(TipoAgrupador, Orden, Nivel, Codigo, Nombre)
WHERE NOT EXISTS (
    SELECT 1 FROM dbo.CatalogoAgrupadorCuentas x
    WHERE x.TipoAgrupador = v.TipoAgrupador AND x.Codigo = v.Codigo
);
GO

SELECT TipoAgrupador, COUNT(*) AS filas
FROM dbo.CatalogoAgrupadorCuentas
GROUP BY TipoAgrupador
ORDER BY TipoAgrupador;
GO

PRINT '=== Agrupador de cuentas (Financiero) aplicado -- 42 filas esperadas en total (22 Egresos, 5 Ingresos, 8 Activo, 6 Pasivo, 1 Patrimonio). ===';
GO
