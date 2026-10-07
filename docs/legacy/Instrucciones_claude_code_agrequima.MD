# Guía para construir el sistema web de Importaciones Agrequima con Claude Code

Este documento resume las decisiones tomadas, la arquitectura recomendada y el plan de trabajo, fase por fase, con los prompts que puedes copiar y pegar directamente en Claude Code para construir la aplicación. Está pensado para ejecutarse en **DESARROLLO-2**, la misma máquina donde vive el SQL Server (login `sa`), de modo que la aplicación se conecte a la base de datos por `localhost` sin configuración de red adicional.

## 1. Decisiones de partida

El stack elegido es **Python con FastAPI en el backend y React en el frontend**, porque permite reutilizar casi tal cual la lógica de tu script `Carga_Importaciones.py` (pandas, sqlalchemy, pyodbc) dentro de los endpoints de carga, en lugar de reescribirla en otro lenguaje. La aplicación tendrá dos áreas separadas por rol: un área de **Administración** (carga de archivos, gestión de nomenclatura/agrupadores, gestión de usuarios y revisión de excepciones) y un área de **Usuario final** de solo lectura con los dos dashboards. El acceso a ambas áreas se controla con usuario y contraseña propios, guardados en una tabla `Usuarios` con rol (`Administrador` o `Usuario`) dentro de la nueva base de datos `Agrequima`, que es independiente de la base de datos productiva que hoy corre en el servidor `10.10.0.6,65280`.

El archivo `agrequima_schema_sql_server.sql` que te entrego junto con esta guía contiene el diseño completo de esa base de datos nueva: las tablas que ya existían para plaguicidas, las tablas equivalentes para nutrientes (que nunca se llegaron a construir), las tablas de staging, los catálogos permanentes de agrupación y los procedimientos almacenados de integración. Este script es el punto de partida para Claude Code; no necesitas diseñarlo de nuevo, solo ejecutarlo o pedirle a Claude Code que lo aplique con Alembic u otra herramienta de migraciones si prefieres versionarlo así.

## 2. Arquitectura general

La aplicación se organiza como dos proyectos dentro de un mismo repositorio: `backend/` (FastAPI) y `frontend/` (React + Vite + TypeScript). El backend expone tres grupos de endpoints: autenticación (`/auth`), administración (`/admin/cargas`, `/admin/usuarios`, `/admin/nomenclatura`) y consulta (`/dashboard/plaguicidas`, `/dashboard/nutrientes`), cada uno protegido según el rol del token de sesión. El frontend tiene dos rutas raíz protegidas por rol, `/admin` y `/app`, y una pantalla de login compartida.

Para los gráficos se recomienda una librería como Recharts o Tremor, que permiten reproducir barras, dona y listas horizontales similares a las de Power BI sin mucho código adicional. La conexión a SQL Server desde Python se hace con `pyodbc` + `sqlalchemy` (igual que en el script actual) usando el driver ODBC 17 o 18 ya instalado en DESARROLLO-2.

Estructura de carpetas sugerida:

```
agrequima-app/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/          (config, seguridad, conexión a BD)
│   │   ├── models/        (ORM: Importacion, Nutrientes, Usuario, etc.)
│   │   ├── schemas/       (Pydantic)
│   │   ├── routers/       (auth.py, admin_cargas.py, admin_usuarios.py, dashboard_plaguicidas.py, dashboard_nutrientes.py)
│   │   ├── services/      (etl_plaguicidas.py, etl_nutrientes.py — lógica portada de Carga_Importaciones.py)
│   │   └── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── pages/admin/   (Login, CargaPlaguicidas, CargaNutrientes, Nomenclatura, Usuarios, Excepciones)
│   │   ├── pages/app/     (DashboardPlaguicidas, DashboardNutrientes)
│   │   ├── components/    (KpiCard, BarComparativa, DonutChart, TopList, DataTable)
│   │   └── api/
│   └── package.json
├── db/
│   └── agrequima_schema_sql_server.sql
└── README.md
```

## 3. Base de datos

Usa el script `agrequima_schema_sql_server.sql` para crear la base `Agrequima` en DESARROLLO-2. Ese script agrega, respecto a lo que ya tenías, dos piezas que faltaban: la tabla `Nutrientes` con clave primaria propia y columnas de agrupación (`ProductoAgrupado`, `CodigoAgrupador`) y auditoría (`fechamod`, `userid`), y los catálogos permanentes `CatalogoNomenclaturaPlaguicidas` y `CatalogoAgrupadorNutrientes`, que no aparecían en el DDL original — solo existían las tablas de staging, así que el procedimiento `usp_ActualizarNomenclatura` necesita un destino permanente donde acumular los códigos que se van asignando mes a mes sin perder los anteriores. También se agrega `AuditoriaCargas`, que reemplaza el archivo de texto `log_excepciones_historico.txt` del script actual por un registro consultable desde la pantalla de administración.

La tabla `dbo.Usuarios` queda vacía a propósito; el primer usuario administrador se crea desde un endpoint o script de arranque de la propia aplicación (para que la contraseña se guarde ya con el hash bcrypt correcto), no con un `INSERT` manual de una contraseña en texto plano.

## 4. Autenticación y roles

Con login por usuario y contraseña, el flujo recomendado es: la tabla `Roles` define `Administrador` y `Usuario`; cada usuario tiene un `RolId`; el backend emite un JWT de corta duración al iniciar sesión, con el rol embebido; cada router de FastAPI valida ese rol con una dependencia (`require_role("Administrador")` para todo lo que cuelga de `/admin`, `require_role("Usuario")` o cualquier rol autenticado para `/dashboard`). Las contraseñas se guardan con `passlib`/`bcrypt`, nunca en texto plano, y conviene forzar el cambio de contraseña en el primer login del usuario administrador inicial.

## 5. Área de administración — funcionalidad

La pantalla de **carga de plaguicidas** reemplaza al script `Carga_Importaciones.py` ejecutado a mano: el administrador sube el archivo Excel crudo del mes (el mismo formato `ImpPlagYYYY` que ya usas) y, opcionalmente, una nueva versión de `Nomenclatura_agrupador.xlsx` si hay agrupadores nuevos que agregar. El backend porta exactamente la lógica de tu script — detección de archivo/hoja, normalización de texto, truncado seguro de columnas, cálculo de año y formateo de fecha, manejo de combos de porcentaje — dentro de `services/etl_plaguicidas.py`, sube los datos a `stg_Importacion` y `stg_Nomenclatura`, y ejecuta `usp_ActualizarNomenclatura` y `usp_CargarImportacion`. Al terminar, la pantalla muestra el resumen (filas cargadas, filas truncadas, filas sin agrupador) y permite descargar el mismo reporte Excel de excepciones que ya conoces, además de dejar el resultado guardado en `AuditoriaCargas` para consultarlo después sin tener que rehacer la carga.

La pantalla de **carga de nutrientes** es la pieza nueva que falta construir. Sigue el mismo patrón: el administrador sube el CSV consolidado de licencias de importación de nutrientes (como el archivo `Licencias_de_Importación_nutrientes...csv` que adjuntaste, cuyas columnas — `Tipo, No_Licencia, No_Registro, NombreComercial, EmpresaImportadora, FechaEmision, UMedida, Cantidad, PaisProcedencia, PaisOrigen, AduanadeIngreso, CIF_dolares, CIF_Q, TimbresQ, Exportador, Concentraciones, Componentes, VENTANILLA` — ya coinciden uno a uno con `dbo.Nutrientes`) y, opcionalmente, una nueva versión de `Agrupador de Fertilizantes Importaciones.xlsx` (hoja "Diccionario Productos", columnas `Nombre Comercial (MAGA)` y `Producto Agrupado`). A diferencia de plaguicidas, aquí el cruce de agrupación **no es por ingrediente activo sino por nombre comercial normalizado** (`TRIM + UPPER + espacios colapsados`, igual que `normalizar()` en tu script actual), porque así está construido el diccionario de fertilizantes. La sección 6 de este documento detalla ese proceso ETL.

La pantalla de **nomenclatura/agrupadores** permite ver y editar manualmente, desde la web, los códigos de `CatalogoNomenclaturaPlaguicidas` y `CatalogoAgrupadorNutrientes` — hoy eso solo se puede hacer editando los archivos Excel a mano — y la pantalla de **excepciones** muestra, para cada tipo de carga, las transacciones sin agrupador encontrado (equivalente a las pestañas "Resumen" y "Detalle" del reporte Excel actual), con la marca de "posible error de captura" que ya calcula tu script para priorizar la revisión. Finalmente, la pantalla de **usuarios** permite al administrador crear, desactivar y cambiar el rol de otras cuentas.

## 6. Proceso ETL de nutrientes (a construir)

Este proceso no existe todavía y es, junto con los dashboards, la parte central de este proyecto. Debe replicar, adaptado a nutrientes, los cinco pasos que ya hace `Carga_Importaciones.py` para plaguicidas:

Primero, lee el diccionario de productos (`Agrupador de Fertilizantes Importaciones.xlsx`, hoja "Diccionario Productos") y normaliza `Nombre Comercial (MAGA)` con la misma función `normalizar()` para obtener `NombreComercial_Key`, guardando el resultado en `stg_AgrupadorNutrientes`. Un detalle a manejar: en el archivo de ejemplo hay celdas que combinan dos variantes de nombre en una sola fila (por ejemplo `"FORMULA 12-24-12 / FORMULA QUIMICA 12-24-12"` mapeando a un mismo `Producto Agrupado`); conviene separar esas celdas por `/` y registrar cada alias como una fila independiente antes de normalizar, para no perder coincidencias.

Segundo, lee el CSV crudo de licencias de nutrientes, limpia los campos de texto, calcula `anio` a partir de `FechaEmision`, y genera `NombreComercial_Key` normalizando `NombreComercial`; el resultado se sube a `stg_Nutrientes`. A diferencia del archivo de plaguicidas, este CSV no requiere mapear columnas por posición porque los encabezados ya coinciden en nombre con las columnas de `dbo.Nutrientes`, así que el mapeo puede hacerse por nombre de columna, con manejo de variantes de espacios en los encabezados (el archivo trae columnas como `" CIF_dolares "` con espacios extra, y viene en UTF-8 con BOM, así que hay que limpiar encabezados y usar `encoding="utf-8-sig"` al leerlo).

Tercero y cuarto, se ejecutan `usp_ActualizarAgrupadorNutrientes` y `usp_CargarNutrientes` (ver script SQL), que integran el catálogo y cargan `dbo.Nutrientes` con estrategia DELETE + INSERT por año, igual que plaguicidas. Quinto, se genera el reporte de transacciones sin agrupador (consultando `dbo.log_ExcepcionesAgrupadorNutrientes`), mostrado en la pantalla de administración y descargable como Excel si se quiere mantener ese hábito.

## 7. Dashboards — especificación funcional

Ambos dashboards reproducen los que ya existen en Power BI (capturas adjuntas), con filtros arriba, tarjetas de indicadores, gráficos comparativos y tablas de detalle. La tabla siguiente resume los componentes de cada uno; los nombres exactos de columnas del filtro "Departamento/Aduana" del dashboard de plaguicidas conviene confirmarlos contra el archivo `.pbix` original antes de programarlos, porque las categorías que aparecen en esa captura (Guatemala, Escuintla, Chiquimula, Suchitepéquez, Quetzaltenango, Sacatepéquez, Izabal) no corresponden a ninguna columna del esquema `dbo.Importacion` que tenemos documentado — es una de las preguntas abiertas de la sección 9.

| Elemento | Dashboard Plaguicidas | Dashboard Nutrientes |
|---|---|---|
| Filtros | Año, Comprador/Importador, Departamento/Aduana (a confirmar), Origen | Año, Comprador/Importador, Nombre comercial, País de origen |
| Tarjetas KPI | CIF total USD, CIF total Q, cantidad de transacciones, cantidad de importadores/productos | CIF total USD, CIF total Q, cantidad de transacciones, cantidad de licencias/productos |
| Gráfico 1 | Comparación anual de CIF (año actual vs. anterior), por categoría | Comparación acumulada de CIF por mes |
| Gráfico 2 | Comparación mensual de CIF (año actual vs. anterior) | Comparación mensual de CIF (año actual vs. anterior) |
| Gráfico 3 | Dona: diversificación por tipo de aplicación (herbicida, insecticida, fungicida, coadyuvante, otros) | Barra horizontal: top de fórmulas químicas por CIF |
| Gráfico 4 | Barra horizontal: top ingredientes activos por CIF | Barra horizontal: top aduanas de ingreso por CIF |
| Gráfico 5 | Barra horizontal: top importadores por CIF | — |
| Gráfico 6 | Barra horizontal: top países de origen por CIF | — |
| Tabla resumen | Importadores/aduanas — transacciones y CIF con barra de progreso | Fórmulas/componentes — transacciones y CIF con barra de progreso |
| Tabla detalle | Transacciones: fecha, recibo, aplicación, importador, producto, ingrediente, exportador, origen, institución | Transacciones: aduana, no. licencia, no. registro, nombre comercial, empresa importadora, fecha de emisión, unidad |

Cada gráfico y tarjeta debe recalcularse en el backend en función de los filtros activos (parámetros de query en el endpoint `/dashboard/plaguicidas` y `/dashboard/nutrientes`), y no en el navegador, para que la carga sea rápida incluso con varios años de datos acumulados.

## 8. Plan de trabajo por fases con prompts para Claude Code

Ejecuta estas fases en orden dentro de la carpeta del proyecto en DESARROLLO-2. Cada bloque de código es un prompt que puedes pegar directamente en Claude Code; ajústalo si tu proyecto ya tiene contexto acumulado de una fase anterior.

**Fase 0 — Base de datos**

```
Tengo el script db/agrequima_schema_sql_server.sql. Conéctate a SQL Server
en DESARROLLO-2 (usuario sa, ver .env) y ejecútalo para crear la base de
datos Agrequima con todas sus tablas y procedimientos. Después crea un
script Python de arranque (backend/app/scripts/seed_admin.py) que cree el
primer usuario administrador pidiendo usuario y contraseña por consola,
guardando la contraseña con bcrypt en dbo.Usuarios.
```

**Fase 1 — Backend base (FastAPI)**

```
Crea el proyecto backend/ en FastAPI con conexión a SQL Server (Agrequima
en DESARROLLO-2) vía SQLAlchemy + pyodbc. Implementa autenticación con
JWT: POST /auth/login valida usuario/contraseña contra dbo.Usuarios y
devuelve un token con el rol embebido (Administrador o Usuario). Agrega
una dependencia require_role(rol) para proteger routers. Incluye
requirements.txt y un .env.example con las variables de conexión
(server=DESARROLLO-2, database=Agrequima, usuario sa).
```

**Fase 2 — ETL de plaguicidas como endpoint**

```
Toma la lógica de Carga_Importaciones.py (te lo adjunto) y pórtala a
backend/app/services/etl_plaguicidas.py, sin rutas de archivo fijas:
debe recibir el Excel crudo de importaciones y, opcionalmente, un nuevo
Nomenclatura_agrupador.xlsx como UploadFile. Conserva toda la lógica de
normalización, truncado seguro por columna, manejo de combos de
porcentaje y detección de filas basura. Al final debe ejecutar
usp_ActualizarNomenclatura y usp_CargarImportacion, y devolver un resumen
JSON (filas cargadas, truncadas, sin agrupador) que además se guarda en
dbo.AuditoriaCargas. Expón esto como POST /admin/cargas/plaguicidas,
protegido con require_role("Administrador").
```

**Fase 3 — ETL de nutrientes (nuevo)**

```
Con el mismo patrón de etl_plaguicidas.py, crea
backend/app/services/etl_nutrientes.py. Recibe el CSV de licencias de
importación de nutrientes (columnas: Tipo, No_Licencia, No_Registro,
NombreComercial, EmpresaImportadora, FechaEmision, UMedida, Cantidad,
PaisProcedencia, PaisOrigen, AduanadeIngreso, CIF_dolares, CIF_Q,
TimbresQ, Exportador, Concentraciones, Componentes, VENTANILLA; viene en
UTF-8 con BOM y algunos encabezados con espacios extra) y, opcionalmente,
un nuevo Agrupador de Fertilizantes Importaciones.xlsx (hoja "Diccionario
Productos", columnas "Nombre Comercial (MAGA)" y "Producto Agrupado";
separa por "/" las celdas que traen varias variantes de nombre antes de
normalizar). Sube a stg_Nutrientes y stg_AgrupadorNutrientes, ejecuta
usp_ActualizarAgrupadorNutrientes y usp_CargarNutrientes, y expón todo
como POST /admin/cargas/nutrientes con el mismo formato de resumen que
plaguicidas.
```

**Fase 4 — Endpoints de dashboard**

```
Crea los endpoints GET /dashboard/plaguicidas y GET /dashboard/nutrientes
en FastAPI, protegidos para cualquier usuario autenticado, que acepten
filtros por query params (año, importador, origen/nombre comercial, y en
plaguicidas el filtro de departamento/aduana pendiente de confirmar) y
devuelvan en un solo JSON: los valores de las tarjetas KPI, las series de
los gráficos comparativos, los top N de cada ranking y la tabla de
detalle paginada, todo calculado en SQL/SQLAlchemy sobre dbo.Importacion
y dbo.Nutrientes respectivamente — no en el frontend.
```

**Fase 5 — Frontend**

```
Crea el frontend/ en React + Vite + TypeScript con dos áreas protegidas
por rol: /admin (login, carga de plaguicidas, carga de nutrientes,
nomenclatura/agrupadores, excepciones, usuarios) y /app (dashboard de
plaguicidas y dashboard de nutrientes, replicando el diseño oscuro con
tarjetas KPI, gráficos de barras comparativos, dona y rankings
horizontales que te muestro en las capturas adjuntas). Usa Recharts para
los gráficos y consume los endpoints ya creados.
```

**Fase 6 — Pruebas y pulido**

```
Escribe pruebas de integración para los dos endpoints de carga (con un
archivo de ejemplo pequeño) y para los endpoints de dashboard, validando
que los totales de las tarjetas KPI coincidan con la suma directa en la
base de datos. Revisa manejo de errores cuando el archivo subido no tiene
el formato esperado, y agrega logging de cada carga en AuditoriaCargas.
```

## 9. Puntos a confirmar antes o durante la construcción

Antes de programar el filtro y el primer gráfico del dashboard de plaguicidas conviene aclarar qué campo alimenta esas categorías tipo departamento (Guatemala, Escuintla, Chiquimula, Suchitepéquez, Quetzaltenango, Sacatepéquez, Izabal): no corresponden a ninguna columna documentada en `dbo.Importacion`, así que probablemente el reporte de Power BI original calcula esa dimensión a partir de otra fuente (catálogo de importadores con su departamento, o de aduanas) que no está en el alcance de los archivos que compartiste. Conviene revisar el archivo `.pbix` original o preguntar al equipo que lo construyó.

También vale la pena decidir, antes de la Fase 3, si el diccionario de fertilizantes seguirá siendo un Excel que sube el administrador mes a mes (como hoy) o si prefieres que el catálogo se edite directamente desde la pantalla de nomenclatura de la nueva aplicación — probablemente lo más práctico es permitir ambas cosas: subir el Excel cuando hay muchos cambios, y editar línea por línea desde la web para correcciones puntuales.

## 10. Módulo Financiero — "Ejecución gastos por mes" y "Ejecución gastos acumulado" (2026-09-23)

Este documento no tenía nada documentado sobre estas 2 páginas (es previo a todo el módulo Financiero). Esta sección deja constancia de la reconstrucción hecha contra el `.pbix` real (`PIQ_AGREQUIMA.pbix`), para que una sesión futura no tenga que repetir la investigación.

**Fuente de verdad usada:** páginas "Centros de Costo" (mensual) y "Centros de Costo acumulado" del `.pbix` real — extraídas con Python (`Report/Layout` del archivo, que es un ZIP con JSON UTF-16LE). Confirmado que son 2 páginas con configuración propia, no la misma reusada: orden de la tabla, negrita del encabezado y ancho de columnas difieren entre las dos.

**Cambios de diseño aplicados a las 2 páginas:**
- Tabla `Gastos | Administración | Peso en % | Operación | Peso en % | Consolidado`, encabezado verde, fuente 14px (antes 11px), celdas vacías cuando no hay monto (en vez de "Q0"/"0.0%"), fila "Total ejecutado" en verde y negrita, nombres de categoría con salto de línea en vez de truncar con "...".
- Orden ascendente de las categorías: "por mes" por **Consolidado**, "acumulado" por **Administración** (son medidas DAX distintas con `OrderBy` distinto, confirmado en el `pivotTable.config` de cada página). Desempate alfabético case-insensitive en los dos casos (antes quedaba mal por comparación case-sensitive de Python).
- Bloque "Presupuesto"/"Ejecución" SACADO de la tabla: es un elemento independiente debajo, con franjas de fondo gris (`FINANCIERO_SURFACE`, sin bordes/ring — un ring-1 anterior se veía como sombra oscura marcada), separación de la tabla (~32px), celdas alineadas a las columnas de la tabla.
- Gráficas Presupuesto vs Ejecutado: una sola categoría con 2 series (no 2 categorías separadas), barras centradas y juntas (`barSize=58`, `barGap=24`, calibrado para que las etiquetas de valor no se toquen ni en el caso más ancho — acumulado con montos de 7 dígitos — verificado midiendo el `getBoundingClientRect()` real de las etiquetas en el navegador), eje Y compartido entre las 3 gráficas, leyenda con círculos y el mismo color de texto en las 2 entradas, chips de cabecera (nombre | % ejecución 2 decimales | diferencia) afuera y arriba de la tarjeta, con la misma caja gris `FINANCIERO_SURFACE` que el resto (sin ring).
- Selector único "Año y Mes" (`FilterYearMonth`, el mismo componente ya aprobado en Estados Financieros) en las 2 páginas.
- Título "por mes": `Ejecución Gastos {Mes} {Año}`. Título "acumulado": `Detalle de Ejecución Gastos vs. Presupuesto al {último día real del mes} de {Mes} de {Año}` (confirmado por el usuario contra su captura real).
- Formato de moneda corregido en `formatQ` (`frontend/src/utils/format.ts`): sin espacio después de la Q y signo negativo ANTES de la Q (`Q930`, `-Q19,320`; antes `Q 930`, `-Q 19,320` por el formateador `Intl.NumberFormat` con `style:"currency"`). Es una utilidad **compartida**, así que el cambio impacta TODO el módulo Financiero, no solo estas 2 páginas: Cuotas Asociados, Estados Financieros (Ingresos y Desembolsos, mensual y acumulado), y cualquier otra pantalla que use `formatQ`. Verificado con captura que no rompió esas otras pantallas.

**Números de control validados (Agosto 2026), SQL directo contra la base vs. lo que muestra la web — sin diferencias:**
- Por mes: Total ejecutado Q143,505 / Q710,318 / Q853,823 (Admin/Oper/Consol). Presupuesto Q162,825 / Q734,909 / Q897,734. % Ejecución 88.13% / 96.65% / 95.11%. Diferencia -Q19,320 / -Q24,590 / -Q43,911.
- Acumulado (filtro `Sal_Mes <= 8`): Total ejecutado Q1,328,560 / Q5,247,423 / Q6,575,984. Presupuesto Q1,496,204 / Q6,943,846 / Q8,440,050. % Ejecución 88.80% / 75.57% / 77.91%. Diferencia -Q167,644 / -Q1,696,422 / -Q1,864,066.
- Septiembre 2026 "por mes" muestra 1 sola fila (Sueldos, Q73.35): confirmado con SQL directo contra `BalanceSaldos` que es dato real (mes en curso, carga parcial), no un bug de filtro/agrupación — máximo mes con movimiento real en 2026 es septiembre.

**Hallazgo: nombres de categoría sin comas.** La web mostraba "Sueldos Bonificaciones y Prestaciones de Ley" en vez de "Sueldos, Bonificaciones y Prestaciones de Ley" (y 2 casos más). Confirmado con SQL directo que `dbo.CatalogoAgrupadorCuentas.Nombre` **no tiene comas** en esos 3 registros — no es un bug de normalización en backend/frontend. La vista que usa el `.pbix` real (`vw_piq_balance_saldos`) no existe en esta base de datos para comparar directo. Se agregó un mapeo de texto explícito en `backend/app/services/dashboard_otros_informes.py` (`_NOMBRES_DISPLAY_EJECUCION_GASTOS`) que corrige SOLO el texto de presentación de esas 3 categorías (confirmadas por el usuario contra su captura real), sin tocar el nombre usado como clave de agrupamiento/suma. Si aparecen más categorías con el mismo problema, hay que agregarlas a mano a ese mapeo o corregir el dato en `CatalogoAgrupadorCuentas`.

**Revisado y sin cambios:** el `rowHeaders` del `pivotTable` real de "acumulado" no tiene ninguna regla de formato condicional (el usuario preguntó por un posible color distinto en algunos nombres de fila, ej. "Imagen y Divulgación") — es un color de tema fijo para toda la columna. No se replicó nada porque no hay nada que replicar.

**Pendientes:**
1. La escala del eje Y de "acumulado" (`Q0/Q5,000,000/Q10,000,000` en agosto 2026) es una aproximación por "número redondo" calculada de los datos reales cargados (`calcularEscalaEjeY` en `DashboardOtrosInformesPage.tsx`), NO la medida DAX real `_Calculos.EscalaEjeY_CentroAcumulado` — esa medida no es extraíble desde el `Layout.json` del `.pbix` sin Power BI Desktop/Tabular Editor. Si el usuario puede pasar el DAX real, hay que reemplazar la aproximación por la fórmula exacta.
2. Revisión pendiente de las líneas/bordes de TODAS las tablas del módulo Financiero (no solo esta página) — quedó explícitamente fuera de alcance de esta ronda, a pedido del usuario ("eso se revisa después en todas las tablas").

Finalmente, para el despliegue en DESARROLLO-2 conviene decidir si el backend corre como servicio de Windows (con NSSM o una tarea programada que mantenga `uvicorn` corriendo) o detrás de IIS con un proxy inverso, y si el frontend se sirve como build estático desde el propio FastAPI o desde IIS también — esto no bloquea el desarrollo, pero sí conviene resolverlo antes de poner la aplicación en manos de los usuarios finales.

## 11. Módulo Financiero — Conciliación bancaria y Flujo de caja (2026-09-25)

Estas 2 pantallas estaban detenidas desde antes por falta de datos (el `.pbix` no traía ningún origen para "Saldo Banco" ni para los saldos contables por banco/mes). Esta sección deja constancia de cómo se destrabaron y se construyeron, para que una sesión futura no repita la investigación.

**Hallazgo previo sobre el `.pbix`:** contrario a lo que se pensó al principio de la investigación (que era una "live connection" sin datos propios), el `.pbix` **sí trae el modelo completo** — es un archivo con datos importados, no solo layout. Con `pbixray` se puede leer el `DataModel` completo (tablas, medidas DAX, pasos de Power Query), y `Report/Layout` trae la posición y el tamaño exactos (x/y/width/height en píxeles) de cada visual de cada página — la misma fuente que ya se venía usando para los anchos de columna.

**Fuentes de datos:**
- **`dbo.SaldosBancos`** (nueva), cargada desde `vw_piq_saldos_bancos.csv` — export de la vista `vw_piq_saldos_bancos` de CONTACC. Es el lado **CONTABLE** de la conciliación (columna "Saldo Contabilidad"), NO el saldo que reporta el banco. Confirmado exacto (al centavo) contra `SUM(Debitos)`/`SUM(Creditos)` de `dbo.BalanceGeneral` para Agosto 2026.
- **`dbo.SaldoBancario`** (tabla que ya existía, antes sin cargar), cargada desde `SaldoBancario.csv` — export directo de `Agrequima.dbo.SaldoBancario`, servidor real **10.10.0.6,65280**, con los conceptos `Saldo inicial` / `Creditos` / `Debitos` por banco/mes. Es el lado **BANCO** real de la conciliación (columna "Saldo Banco"), y también la fuente de los saldos por banco de Flujo de Caja.
- **`dbo.ChequesCirculacion`** (ya existía) para los cheques/documentos en circulación de las 2 pantallas.
- El cruce `BANCOR` (código informal usado en `SaldoBancario`) ↔ `BAC 701111600 MONETARIA` (cuenta formal de `BalanceGeneral`) se hizo por coincidencia numérica exacta de Entradas/Salidas contra Débitos/Créditos en Agosto 2026, no por texto.

**Fórmulas reales usadas:**
- Cheques en circulación a una fecha de corte: `doc_fecha <= fin_de_mes AND (doc_fchcobro IS NULL OR doc_fchcobro > fin_de_mes)` — outstanding real a cierre de período, sobre todo el histórico (no agrupado por el mes de emisión del cheque).
- Caja ← `BalanceGeneral`, cuenta `110101001`, YTD dentro del año (`Sal_Ano = :anio AND Sal_Mes <= :mes`, la misma semántica ya documentada para Estados Financieros).
- Inversión Plazo Fijo BAC ← `BalanceGeneral`, cuenta `110103003`, mismo YTD. Inversión Plazo Fijo Promérica ← cuenta `110103004`, mismo YTD.
- Totales "Saldo Banco" por banco = Saldo inicial + Créditos − Débitos − Documentos en Circulación.

**Números de control validados (Agosto 2026), cuadrando exacto contra el `.pbix` de referencia:**
- Conciliación bancaria (Totales banco / contabilidad, por banco): BAC(BANCOR) Q3,061,395.55 / Q3,061,395.55. BANRURAL Q289,458.48 / Q289,458.64. BI Q41,349.17 / Q41,349.17. PROMÉRICA Q70,399.55 / Q70,399.55.
- Flujo de caja: Caja Q1,200. Bancos — Banrural Q289,459, Banco Industrial Q41,349, BAC Reformador Q3,061,396, Promérica Q70,400 — Total bancos Q3,463,803. (−) Cheques en circulación (Banrural Q4,000 + BAC Q19,250) Q23,250. Disponibilidad en depósitos monetarios y caja Q3,463,803. (+) Inversiones Plazo Fijo BAC Q2,300,001. (+) Inversiones Plazo Fijo Promérica Q1,500,000. Disponibilidad al 31 de Agosto de 2026: **Q7,263,804**.

**Hallazgo: BANRURAL no cuadra al centavo entre banco y contabilidad** (Q289,458.48 vs. Q289,458.64, diferencia de Q0.16). Confirmado que es real, existe también en el `.pbix` de referencia — no es un bug de la carga ni del cálculo.

**Hallazgo: "Disponibilidad en depósitos monetarios y caja" no vuelve a restar los cheques en circulación** del "Total bancos" en Flujo de Caja (ambos dan Q3,463,803) — así lo muestra el `.pbix` real; el descuento de cheques ya queda reflejado en la fila de Conciliación bancaria, no se resta dos veces. Confirmado contra el control del cliente, no es un error de la implementación.

**Regla para próximas pantallas (anchos y posiciones):** sacar siempre el ancho y la posición de cada visual directamente de `Report/Layout` dentro del `.pbix` (ZIP con JSON UTF-16LE con BOM). Referencia de canvas: página de **1920px**, menú lateral embebido del propio reporte de **262px**, área de contenido real de **1658px**. Expresar los anchos como % de esa área de contenido (no píxeles fijos) para que escale responsivo. Aplicado con este patrón en Conciliación bancaria (54.3%), Flujo de caja (61.8%, tabla y gráfica) y Ejecución de Gastos (67.2% tabla+resumen, 94.3% gráficas).

**Pendientes:**
1. Exportar `BalanceGeneral`, `SaldosBancos` y `SaldoBancario` juntos la próxima vez que se actualicen datos, para que los 3 queden sincronizados en el mismo período.
2. Correr `backend/deploy_servidor_real/13_saldos_bancos_financiero.sql` contra el servidor real cuando se publique el módulo Financiero ahí — hoy solo está probado contra la base de desarrollo.

## 12. Menú, filtros sincronizados y corrección de Cuotas Asociados (2026-09-26)

Antes de seguir construyendo pantallas (Presupuestos, Importaciones del Financiero) se ordenó la navegación y el filtro Año/Mes, y se corrigió un error real de Cuotas Asociados. Esta sección deja constancia de las 3 cosas.

**Los 3 sistemas de la plataforma** (confirmado en el backend, no solo 2): (1) **Importaciones** (Plaguicidas/Nutrientes, `dbo.Importacion`) — ya publicado en `main`. (2) **Financiero** — rama `financiero`, sin publicar. (3) **Indicadores** — existe SOLO como permiso reservado: columna `AccesoIndicadores` en `dbo.Usuarios` y la dependencia `require_acceso_indicadores` en `app/core/deps.py`, con el propio comentario del código diciendo que "Indicadores no tiene pantallas" — no tiene ni una ruta ni una mención previa en esta bitácora, listo para cuando ese proyecto arranque. El "Importaciones" del **Financiero** (ingresos de la gremial por importaciones) es un CUARTO bloque de pantallas, distinto del dashboard Plaguicidas/Nutrientes aunque comparta nombre (ver más abajo).

**Diferenciación visual de sistemas en el Sidebar** (`Sidebar.tsx`): cada sistema de primer nivel (Financiero/Importaciones) ahora lleva un encabezado no clicable ("DASHBOARD FINANCIERO"/"DASHBOARD IMPORTACIONES") con separador, un ícono (💰/📦) y un tema de color propio (`TEMA_FINANCIERO` ámbar, `TEMA_IMPORTACIONES` sky — este último es el color que ya tenía antes, sin cambio). La navegación no cambió: siguen siendo los mismos nodos colapsables de siempre, con los mismos flags de acceso (`accesoFinanciero`/`accesoImportaciones`) decidiendo si el bloque se muestra.

**Sección activa del menú** (`idsHastaActivo`): antes el `Set` de secciones abiertas estaba hardcodeado a `["financiero", "estados-financieros"]` sin importar la pantalla activa. Ahora se calcula una sola vez al montar el Sidebar, recorriendo el árbol hasta encontrar la hoja cuyo `href` coincide con la ruta+`?vista=` actual, y expandiendo solo el camino hasta ahí (sistema + sub-sección). Si la ruta activa no está en ningún árbol, queda todo colapsado. A partir de ahí el usuario abre/cierra secciones a mano sin que se le vuelvan a forzar.

**Estructura completa del menú Financiero según el `.pbix`** (5 secciones, confirmado en `Report/Layout`):
1. **Estados financieros**: Estado de ingresos y desembolsos mensual/acumulado; Balance general acumulado mensual/comparativo. (ya construidas)
2. **Otros informes financieros**: Cuotas asociados; Conciliación bancaria; Flujo de caja; Ejecución gastos por mes/acumulado. (ya construidas)
3. **Presupuestos**: Ejecución vs presupuesto; Ejecución vs presupuesto acumulado; Comparativo ejecutado. (siguiente a construir, sin `href` todavía)
4. **Importaciones** (del Financiero, NO el dashboard Plaguicidas/Nutrientes): Ingresos por importación; Ingresos por importación comparativo; Comparación importaciones kilolitros y precio kilolitro; Ingresos por contribución 4.5 por millar. Fuentes reales `vw_piq_*` de CONTACC (ingresos de la gremial), distintas de `dbo.Importacion` (licencias de importación de agroquímicos, el otro dashboard). Agregada esta ronda al árbol del Sidebar, sin `href` (mismo patrón usado antes con Conciliación/Flujo antes de construirlas).
5. **Otros ingresos**: Otros ingresos generados. (sin construir)

**Páginas del `.pbix` que NO se agregan al menú** (confirmado con `Report/Layout`, no aparecen en ningún menú real de Power BI): "Viáticos" (página suelta, sin sección visible); "Promedio Precio Kilolitro" (la página-gráfica que acompaña a "Comparación importaciones Kilolitros", mismo patrón que "Centros de Costo" + "Centros de Costo gráficas"); y varias páginas `"Duplicate of ..."`/`"Duplicado de ..."` (copias de Estados financieros, Centros de Costo y Conciliación bancaria — parecen borradores/backups del autor original del reporte, no pantallas reales).

**Filtro Año/Mes sincronizado** (`FinancieroFilterContext.tsx`, montado arriba del `<Outlet>` de `/app` en `AppLayout.tsx`): calca la sincronización de slicers real del `.pbix`, en 2 grupos:
- **Grupo 1 (Año+Mes)**: las 4 de Estados financieros, las 5 de Otros informes financieros y, cuando existan, las 3 de Presupuestos y "Comparación importaciones kilolitros". Implementado con el hook `useFinancieroFilterGrupo1(periodos)`: guarda la INTENCIÓN del usuario (último año+mes elegido en cualquier pantalla del grupo) en un contexto compartido, y cada pantalla recorta ese mes a su propio último mes disponible cuando no existe en sus datos (sin sobrescribir el valor compartido, para no romper el mes elegido en las demás pantallas del grupo).
- **Grupo 2 (solo Año)**: "Ingresos por importación" e "Ingresos por importación comparativo" — el hook `useFinancieroFilterGrupo2()` ya existe, listo para cuando esas 2 pantallas se construyan (todavía no las consume nadie).
- Las pantallas independientes ("Ingresos por contribución 4.5 por millar", "Otros ingresos generados") NO usan este contexto — mantendrán su propio estado local cuando se construyan.
Verificado con navegación real por clic en el sidebar (no recarga de página, que remontaría el contexto): cambiar el período en Conciliación bancaria y navegar a Flujo de caja y a Estado de ingresos y desembolsos mensual muestra el mismo período en las 3, sin tocar su filtro.

**Corrección de Cuotas Asociados — SÍ era un error respecto de Power BI.** El `.pbix` real define `MiCalendario = CALENDAR(DATE(2023,1,1), EOMONTH(MAX(vw_piq_balance_general[Fecha]), 0))`: el filtro de mes llega solo hasta el último mes con datos de BalanceGeneral (hoy Septiembre 2026), igual que las demás pantallas. Antes, `periodos_disponibles` traía solo años (de `dbo.AsociadosCuota`) y el selector de mes ofrecía los 12 meses siempre, permitiendo elegir Diciembre 2026 aunque no exista ese dato todavía. Corregido: `_periodos_disponibles_cuotas` ahora lee `SELECT DISTINCT Sal_Ano, Sal_Mes FROM dbo.BalanceGeneral` (continuo desde 2023-01 sin huecos, reproduce exacto la fórmula DAX sin necesidad de generar un calendario aparte), y la resolución de año/mes por default reutiliza `_anio_mes_default_gastos` (la misma función que ya usan Ejecución de Gastos/Conciliación/Flujo) en vez de años de `AsociadosCuota` + mes=12 fijo. El cálculo de Cancelado/Saldo en sí NO cambió (mismo SQL, mismo filtro `Sal_Mes <= mes`); verificado que Agosto 2026 sigue dando exacto Q756,000 / Q660,000 / Q96,000.

## 13. Módulo Financiero — Presupuestos: Ejecución vs presupuesto, Acumulado y Comparativo ejecutado (2026-09-27)

Las 3 pantallas de la sub-sección "Presupuestos" (ver sección 12), construidas con el `DataModel` real del `.pbix` extraído con `pbixray` (`C:\Users\angel\CODEMSA\Pronostiq-Powerbi - PRONOSTIQ\AGREQUIMA\PIQ_AGREQUIMA.pbix`) y `Report/Layout` para orden, formato condicional y anchos.

**Fuentes y medidas DAX reales:**
- "Ejecución vs Presupuesto" (mensual) y su Acumulado: mismas fuentes que Ejecución de Gastos (`dbo.BalanceSaldos` + `dbo.Presupuestos`, mismo `GroupEgresos` vía `CatalogoAgrupadorCuentas`), pero consolidando Administración+Operación en una sola fila por categoría en vez de mostrarlas separadas — confirmado que la medida real `TotalEjecutadoAdministrativo`/`TotalEjecutadoOperativo` de `vw_piq_balance_saldos` usa los mismos filtros de `Cod_Centro` (`IN {AD-01,AD-02}` / `LEFT=O` o `LEFT=A` excepto AD-01/AD-02) que ya existían en el código (`_FILTRO_ADMIN_SQL`/`_FILTRO_OP_SQL`).
- "Comparativo ejecutado": `vw_piq_balance_saldos.TotalEjecutado_Acumulado` (año actual) y `EgresosAnioAnterior` (año−1, mismo filtro `Sal_Mes <= mes` pero del año anterior — comparación pareja, NO año completo).
- Títulos confirmados con pbixray: `Texto comp_presupuesto` = "Ejecución Consolidados vs. Presupuesto {Mes} {Año}"; `Texto ctros_costoAcumulado` = "Detalle de Ejecución Gastos vs. Presupuesto al {día} de {Mes} de {Año}" (el `.pbix` real REUSA esta misma medida que ya usa "Ejecución Gastos Acumulado", no es una medida nueva); `TituloEjecutadoComparativo` = "Comparativo Ejecutado {Año-1} vs {Año} Acumulado al {día} de {Mes}" (sin el año repetido al final).

**Números de control validados (Agosto 2026), cuadrando exacto:**
- Mensual y Acumulado: **20 filas** cada uno (el universo completo de `CatalogoAgrupadorCuentas` con `TipoAgrupador='Egresos'` — el "22" que se mencionó al pedir la tarea era un conteo manual erróneo de la captura, confirmado y corregido con el usuario). Totales mensual: Q897,734 / Q853,823 / -Q43,911 / -4.9%. Acumulado: Q8,440,050 / Q6,575,984 / -Q1,864,066 / -22.1%.
- Comparativo: **17 filas** (solo categorías con movimiento en al menos uno de los 2 años). Total: Q6,145,507 / Q6,575,984 / Q430,476 / 7.00%.

**Orden y formato condicional reales (`Report/Layout`):** mensual ordena `Direction=1` (ascendente) por `GroupEgresos` (nombre de categoría); acumulado `Direction=2` (descendente) por `TotalPresupuesto_AcumuladoN`; comparativo `Direction=2` descendente por `DiferenciaEjecutado` (Variación Q.). Formato condicional: SOLO la tabla mensual tiene una regla `Diferencia < 0 → '#4BD72C'` (verde) en su `objects.values`; la de acumulado no tiene ningún objeto de formato condicional — confirmado que las negativas van en blanco ahí a propósito, no es una omisión. La fila "Total" nunca lleva color especial en ninguna de las 2.

**Corrección: encabezados cruzados en Comparativo.** En el `.pbix` real, la columna de tabla que dice "2026" trae los valores de `EgresosAnioAnterior` (2025) y viceversa — confirmado en el `prototypeQuery.Select` real. En la web se corrigió: la columna rotulada `{año-1}` siempre trae `EgresosAnioAnterior`, la columna `{año}` siempre `TotalEjecutado_Acumulado`, igual que la gráfica — los números no cambian, solo el rótulo de columna correcto.

**Ajustes de las 3 gráficas (título adentro, leyenda centrada, barras al 12%):**
- Título: DENTRO del recuadro gris de la gráfica (parte del propio visual en el `.pbix` real), centrado, negrita, 16px. El padding que lo separa del borde va en la TARJETA (el div contenedor), no en el `<p>` del título — el padding de un elemento no mueve su propio borde superior, así que ponerlo en el `<p>` no lo separaba de verdad del borde de la tarjeta (confirmado midiendo con `getBoundingClientRect`, aunque visualmente el texto sí se viera con aire).
- Leyenda: reemplazado el `<Legend>` de Recharts por una leyenda propia (`LeyendaCentrada`). El `<Legend align="center">` de Recharts centra respecto del `<svg>` COMPLETO, pero el eje Y solo ocupa espacio a la izquierda (sin espejo a la derecha) — eso deja el par de barras centrado en un área más angosta que el SVG, corrida hacia la derecha, con hasta 56px de desfase respecto de la leyenda. Se calcula a mano el centro real del par de barras (mismos gutters que usa el propio `BarChart`) y se posiciona la leyenda ahí — exacto, sin depender del algoritmo interno de Recharts.
- Barras: ~12% del ancho de la tarjeta (calcado del `"size":125` de un visual Deneb de 1062px del `.pbix` ≈ 12%). `barCategoryGap`/`barGap` en porcentaje resultó NO lineal y NO monótono con una sola categoría falsa (probado 40%→8.5%, 49%→0.6%, 76%→22.8%, 87%→32.4% del ancho, sin relación consistente) — se mide el ancho real de la tarjeta con `ResizeObserver` y se pasa `barSize` en píxeles calculado como 12% de ese ancho, exacto y estable a cualquier tamaño de pantalla.

**Decisiones de diseño del usuario que NO vienen de Power BI** (no inventadas, pedidas explícitamente):
- Eje Y de "Comparativo ejecutado": Q0 a Q8,000,000 cada Q2,000,000 (el `.pbix` real usa escala `nice` automática de Vega-Lite con pasos de 500,000 — se pidió explícitamente NO replicar eso).
- Separación tabla-gráfica: 3.0% (mensual) / 3.4% (acumulado) / 2.7% (comparativo) del ancho del área de contenido, medidos del `Report/Layout` real, pero aplicados con un truco de CSS: un `margin-top`/`margin-bottom` en % SIEMPRE se resuelve contra el ANCHO del contenedor (no su alto) — así que `marginTop: "3.0%"` da exactamente lo pedido sin ningún cálculo en JS.
- Proporción alto/ancho de las 3 gráficas: 0.38 (antes 0.47, la proporción real del `.pbix` — el usuario pidió bajarla como decisión de diseño propia). Ojo: el `aspect` de `ResponsiveContainer` solo controla el `<svg>`, no la tarjeta completa (que ahora incluye título+leyenda propios, ~60px extra) — el aspecto del SVG se calcula despejando esa altura extra para que la TARJETA COMPLETA dé 0.38, no solo el gráfico.

**Regla para futuras gráficas del módulo:** el título va DENTRO del recuadro de la gráfica (no arriba, como elemento aparte), y la leyenda centrada bajo el área de datos real (no bajo el ancho completo del SVG si el eje Y no está espejado a la derecha).

**Siguiente:** Presupuestos (3 pantallas: Ejecución vs presupuesto, Ejecución vs presupuesto acumulado, Comparativo ejecutado — ya con anchos/posiciones y campos DAX extraídos del `.pbix`, ver investigación de esta misma ronda). Después, Importaciones del Financiero (4 pantallas) — necesita investigación de fuentes primero (vistas `vw_piq_*` de ingresos por importación y contribución 4.5 por millar, mismo patrón de "diagnóstico antes de construir" que se usó para Conciliación/Flujo).

## 14. Módulo Financiero — Importaciones: Ingresos por importación, Comparativo, Kilolitros y Contribución 4.5 por millar (2026-09-27)

Las 4 pantallas de la sub-sección "Importaciones" del Financiero (ver sección 12) — DISTINTA del dashboard "Importaciones" Plaguicidas/Nutrientes ya publicado en `main`, aunque comparta tabla fuente. La investigación previa (PASO 0) descartó las vistas `vw_piq_*` mencionadas en la sección 12: la fuente real resultó ser `dbo.Importacion` directamente (ver abajo).

**Fuentes.** Las 4 pantallas leen `dbo.Importacion` — la MISMA tabla que usa Plaguicidas/Nutrientes, EN SOLO LECTURA, agrupada por `institucion` (`'Agrequima'` / `'Gremiagro'`) en vez de por producto/ingrediente activo: es la fuente real de ingresos de la gremial por importación, confirmada con `pbixray` contra el `.pbix` real (`Sql.Database("10.10.0.6,65280", "Agrequima")` → `dbo.Importacion`, `Mes = MONTH(fecha)`). No se tocó el módulo Plaguicidas/Nutrientes, sus endpoints ni sus datos en ningún momento. "Ingresos por contribución 4.5 por millar" además lee `dbo.BalanceSaldos`/`dbo.Presupuestos` (cuenta `410104001`), mismo patrón ya usado en Presupuestos (sección 13).

**DAX replicado (confirmado exacto contra números de control reales, vía SQL directo para 2026 y vía `pbixray.get_table()` — datos cacheados del `.pbix`, años 2023-2026 — para escenarios con 2024, ausente en la base de desarrollo):**
- CIF por mes = `SUM(cif_USD)` filtrado por año/mes/institución. `%` de cada fila = CIF del mes / total COMPLETO de su año (no limitado a los meses del otro año). "Total año": el CIF de año−1 mostrado suma SOLO los meses que también existen en año actual; sus 2 columnas de `%` son 100.00% fijo, no una razón calculada.
- Kilolitros: tarjetas de cambio de cantidad = `SUM(cantidad)` ACUMULADO enero→mes, año vs año−1 (mismo patrón "Total año" de arriba). Precio por kilolitro (tabla) = CIF/cantidad del MES SELECCIONADO SOLAMENTE, sin acumular.
- Contribución 4.5 por millar: `Realizado = SUM(Creditos)-SUM(Debitos)` de `BalanceSaldos`; `Presupuesto = SUM(pre_presupuesto)` de `Presupuestos`; acumulado con el mismo patrón "N" (`Sal_Mes`/`par_mes <= mes seleccionado`) ya usado en Presupuestos.

**Correcciones respecto de Power BI (pedidas explícitamente por el usuario, no inventadas):**
- Donde el DAX real usa `YEAR(TODAY())`, acá se usa el AÑO SELECCIONADO por el filtro — necesario porque esta app no vive "hoy" dentro del año que el `.pbix` original asumía.
- Precio por kilolitro: el título de la página dice "Acumulado" pero el DAX real (y esta réplica) calcula el precio del MES SELECCIONADO únicamente — mislabeling del reporte original, replicado tal cual (no se "corrigió" el texto).
- Eje Y de las 2 gráficas de "Ingresos por importación comparativo": Power BI arranca en $0; acá se ajusta a los datos reales (mínimo/máximo redondeados a un paso "nice" — 1/2/3/5/10 × 10ⁿ — buscando entre 5 y 7 marcas), decisión propia del usuario porque con datos lejos de 0 la mitad de la gráfica quedaba vacía. Se recalcula solo al cambiar de año. La gráfica CIF de "Ingresos por importación" (pantalla 1) mantiene su eje fijo ($12M–$34M cada $2M), sin este cambio.
- Año anterior sin datos (p.ej. año seleccionado 2025 → año−1 2024, ausente en desarrollo): esa serie NO se dibuja (ni línea, ni cajitas de valor), el eje se recalcula solo con el año actual, y la leyenda muestra "{Año−1} (sin datos)".
- Tablas: "—" en vez de "(Blank)"/$0 engañoso en las columnas de año anterior/VAR/VAR% cuando ese año no tiene ningún dato — mismo criterio ya usado en Kilolitros para la variación cuando falta el año de comparación.

**Ajustes propios de layout (igual que Presupuestos, sección 13):** título de cada gráfica DENTRO del recuadro; leyenda propia centrada bajo el área de datos (no el `<svg>` completo); etiquetas de valor completas sin abreviar ($32,963,070, no "$33M"), con cajita blanca de fondo sólido, borde de 1px del color de la serie en modo claro (en oscuro, igual que Power BI), dibujadas en una capa aparte AL FINAL del gráfico (Recharts `<Customized>`) para que ninguna línea tache el texto de una etiqueta ya dibujada. Colisión de etiquetas: algoritmo propio que prueba una lista de desplazamientos verticales (arriba, abajo, arriba apilado, abajo apilado…) evitando chocar con otras cajas, con las etiquetas del eje X y con los bordes de la tarjeta. Con más de 7 meses en una misma gráfica (año completo), los nombres del eje X se abrevian a 3 letras (Ene, Feb, Mar…).

**Números de control validados exactos:** los 3 escenarios completos del prompt original (2026 para pantallas 1/2/4; "Julio 2025" = año 2025 vs 2024 y "Agosto 2026 sin datos" para Kilolitros) — CIF por mes/Total año de ambos bloques del Comparativo, cambio de cantidad y precio por kilolitro (Total/Agrequima/Gremiagro), y acumulado a julio 2026 de Contribución 4.5 por millar (Q4,011,995.46).

**Pendiente (ya anticipado por el usuario, no bloqueante):**
- `dbo.Presupuestos` no tiene ninguna fila para la cuenta `410104001` en 2026 (solo las 12 de 2025) — el % de ejecución y la línea/barra de presupuesto quedan en "Sin presupuesto"/"(sin datos)" hasta que se cargue.
- Sin confirmar si `dbo.Importacion` del servidor real (`PIQ_IA` producción) tiene cargado el año 2024 — si no, al elegir 2025 la comparación con 2024 quedará vacía en producción hasta que se cargue ese año (dev tampoco lo tiene; se validó ese escenario con los datos cacheados del `.pbix` vía `pbixray`, no contra una base real).

**Siguiente:** "Otros ingresos generados" (última pantalla del Financiero) — `dbo.OtroIngreso` en desarrollo está vacía (0 filas); el usuario ya agregó por su cuenta `docs/legacy/financiero/OtroIngreso.csv` con datos reales para esa construcción.

## 15. Módulo Financiero — Otros ingresos generados (2026-09-27)

Última pantalla del Financiero: con esta queda completo el menú (Estados financieros, Otros informes financieros, Presupuestos, Importaciones, Otros ingresos).

**Fuente.** `dbo.OtroIngreso` (Tipo, Concepto, Anio, Mes, Valor) — export real de Agrequima.dbo.OtroIngreso del servidor 10.10.0.6, cargado desde `docs/legacy/financiero/OtroIngreso.csv` (480 filas, agregado por el usuario) con el mismo patrón que los demás CSV del módulo (`cargar_datos_financiero_inicial.py`, función `_cargar_otro_ingreso`). En desarrollo: años 2025 (12 meses completos) y 2026 (Enero-Agosto), 12 conceptos, todos con datos completos en ambos años. Script `14_otro_ingreso_financiero.sql` preparado para el servidor real (idempotente, solo crea la tabla si no existe) — no corrido.

**DAX replicado (confirmado con pbixray contra `_Calculos_otros_ingresos`):** los valores guardados son ACUMULADOS -- NO se suman meses entre sí, se toma el valor del ÚLTIMO MES CON DATOS de cada año, por concepto y tipo (`Ejecutado_año_actual`/`Ejecutado_año_anterior`/`Presupuesto_año_actual`). `Ejecutado {Año-1}` = 0 si ese año no tiene ninguna fila para el concepto (el DAX real usa `IF(ISBLANK(...), 0, ...)`). `% ejecutado` = Ejecutado{Año} / Presupuesto{Año}, 0 si el presupuesto es 0 (`DIVIDE(...,...,0)`).

**Números de control (Año 2026), validados exactos, los 12 conceptos + Total:** CropLife - Proyecto SPMF Q837,981/Q637,500/Q626,528/98%; Gremiagro Q300,000/Q300,000/Q100,000/33%; Venta de Material Reciclable Q354,690/Q275,000/Q255,115/93%; Aporte Industria Fertilizantes Q0/Q0/Q0/0%; Aporte Fundación Hanns R. Neumann Stiftung Q152,875/Q78,000/Q36,250/46%; Intereses Bancarios e Inversión Q176,472/Q229,950/Q131,301/57%; Carnet Aplicadores... Q144,449/Q125,000/Q96,799/77%; Venta de Sellos Q42,896/Q40,000/Q34,640/87%; Venta Minicentros de Plástico Reciclado Q24,554/Q20,000/Q4,464/22%; Proyecto ATRACSI Q0/Q0/Q0/0%; Localg.a.p. Guatemala Q0/Q0/Q0/0%; Venta de Vehículos Q15,000/Q225,000/Q0/0%; TOTAL Q2,048,918/Q1,930,450/Q1,285,097/67%.

**Correcciones respecto de Power BI:**
- Leyenda de la gráfica de barras: el `.pbix` real la trae MAL ETIQUETADA (dice "Ejecutado {Año} / Ejecutado {Año-1} / Presupuesto {Año}" para esos mismos 3 colores en ese orden) — en la web dice lo correcto según el color real de cada serie ("Ejecutado {Año-1}" #9FB6C3, "Presupuesto {Año}" #2F8C83, "Ejecutado {Año}" #00A6B8).
- Título: donde el DAX real usa `YEAR(TODAY())` (medida `TituloOtrosIngresos`), acá se usa el AÑO SELECCIONADO por el filtro.

**Pendiente para la revisión final (no bloqueante, ya reportado al usuario):**
- Encabezados de la tabla de detalle: se partieron en 2-3 líneas con un criterio propio (preservando el texto completo), a falta de un spec de texto limpio extraíble del `.pbix` real (esa tabla se arma con decenas de tarjetas individuales en una grilla, no con un visual de tabla/Deneb). Falta reemplazarlos por los textos cortos reales del spec Vega (Titulo1/Titulo2/Titulo3): "Venta de Material" / "Reciclable"; "Aporte Fundación" / "Hanns R. Neumann" / "Stiftung"; "Carnet Aplicadores y" / "Certificados y Cursos" / "Capacitaciones"; "Intereses Bancarios e" / "Inversión"; "Venta Minicentros de" / "Plástico Reciclado"; "CropLife - Proyecto" / "SPMF"; "Aporte Industria" / "Fertilizantes".
- Última marca del eje X cortada a la derecha, en las 2 gráficas (barras agrupadas y totales).
- Año anterior sin datos (2025 vs 2024, sin 2024 cargado): falta el mismo tratamiento ya usado en Importaciones -- "(sin datos)" en la leyenda y "—" en la tabla en vez de Q0 engañoso (hoy muestra Q0 literal, matemáticamente correcto según el DAX pero visualmente igual a "sin movimiento").

## 16. Revisión exhaustiva del módulo Financiero — estándares, filtros y datos (2026-09-29)

Ronda de auditoría completa de las 14 vistas del módulo (4 Estados financieros + 5 Otros informes financieros + 3 Presupuestos + 2 Importaciones con filtro Año+Mes, más Kilolitros y Contribución 4.5 por millar y Otros ingresos generados como independientes), con estándares nuevos aplicados a TODAS y 2 bugs de filtro corregidos. Ningún cambio de fórmulas/DAX ni de números de control en esta ronda -- solo layout, orden de tablas, sincronización de filtros y 3 pendientes puntuales de Otros ingresos (sección 15).

**Estándares del módulo (a partir de ahora, aplican a toda pantalla nueva):**
- **Título de página**: `text-2xl font-bold text-ink`, en las 14 vistas por igual (antes Estados financieros y Cuotas Asociados usaban `text-3xl` sin negrita, y Kilolitros `text-xl` -- un nivel más chico que el resto sin motivo documentado). Separación título→contenido unificada a `space-y-3`/`min-h-[40px]` (antes Estados financieros/Cuotas Asociados usaban `space-y-5`/`min-h-[64px]`).
- **Filtro**: `absolute right-0 top-0`, misma fila que el título, en las 14 vistas (antes Estados financieros/Cuotas Asociados lo ponían `top-full mt-5`, debajo del título, alineado con la fila de KPIs). Verificado con `getBoundingClientRect` que el filtro y la fila de KPIs de Estados financieros NO se superponen visualmente pese a compartir unos px de rango vertical (ocupan columnas horizontales distintas: KPIs centrados en el medio, filtro en la esquina); no hizo falta bajar las tarjetas.
- **Tablas sin líneas horizontales entre filas**: aplicado a las 6 archivos/componentes del módulo. Se mantiene encabezado verde, fondos, y un borde superior sutil (`border-t border-line`) solo en las filas Total que lo necesitaban para separación visual.
- **Orden por encabezado** (hook reutilizable `useTablaOrdenable` + componente `EncabezadoOrdenable`, ver ronda anterior): aplicado en `TablaCuotasTipo`, `TablaEjecucionGastos`, `TablaPresupuesto` (mensual/acumulado), `TablaComparativo`, `TablaCIFMes`, y (ronda 2026-09-29, ver más abajo) `TablaGrupoExpandible` con orden JERÁRQUICO propio. Excluidas (orden es parte del reporte): Conciliación bancaria y Flujo de caja (grillas `<div>`, ni siquiera son `<table>`), cuadro de precios de Kilolitros, tabla transpuesta de Otros ingresos, y `TablaCategorias` (resumen fijo de 3 filas, sin `<thead>`).
- **Orden JERÁRQUICO en Estados financieros** (`useTablaOrdenableJerarquica`, `hooks/useTablaOrdenable.ts`): las 8 tablas `TablaGrupoExpandible` de las 4 pantallas (Ingresos/Egresos ×2, Activo/Pasivo/Patrimonio ×2) ahora se ordenan por encabezado igual que el resto del módulo, pero respetando la jerarquía -- al clickear una columna, los GRUPOS se ordenan por su propio valor en esa columna y, DENTRO de cada uno, sus cuentas se ordenan igual (nunca se mezclan entre grupos); la fila Total queda siempre fija al final, fuera del orden. Mismo ciclo de 3 clics (asc/desc/original) y misma columna "nombre de grupo/cuenta" también ordenable (alfabético), igual que las demás tablas del módulo. Cada tabla (Ingresos vs. Egresos, Activo vs. Pasivo vs. Patrimonio) tiene su propio estado de orden independiente.
- **Encabezados alineados con su columna** (regla nueva de esta ronda, aplicada a las 20 tablas con `<thead>` de las 14 vistas): encabezado de columna numérica alineado a la DERECHA (mismo padding que la celda), encabezado de columna de texto a la izquierda; la flecha de orden va ANTES del texto en columnas numéricas y DESPUÉS en columnas de texto (inferido automáticamente en `EncabezadoOrdenable` a partir de si el `className` trae `text-right`), para que agregar/quitar la flecha nunca corra el borde que se mide contra la celda. Antes, varias tablas (`TablaPresupuesto`, `TablaComparativo`, `TablaEjecucionGastos`, `TablaCIFMes`, el cuadro de precios de Kilolitros) tenían sus encabezados centrados con un solo `className` compartido para toda la fila, aunque las celdas de datos ya iban a la derecha -- corregido a una clase de encabezado por tipo de columna (texto/numérica). Única excepción: la tabla transpuesta de Otros ingresos, centrada en encabezados y valores -- el prompt de construcción de esa pantalla (sección 15) pidió explícitamente valores Q y % centrados en la tabla de detalle, y el usuario aprobó la pantalla completa "tal como está". Como `TablaGrupoExpandible` y `TablaCuotasTipo` ya tenían esta alineación correcta desde su construcción original, no necesitaron cambios.

**Verificación automatizada (Playwright, scripts temporales, no versionados):** para las 20 tablas de las 14 vistas, se midió con `getBoundingClientRect`/`Range.getClientRects()` (el contenido renderizado, no la celda con su padding) el borde del texto del encabezado contra el de las celdas de su misma columna -- **111 columnas auditadas, diferencia máxima 0px en todas** (la única "centrada" es la tabla transpuesta de Otros ingresos, exceptuada a propósito). Para las 20 tablas ordenables se hizo clic real (Playwright `locator.click()`, no simulado) en cada encabezado y se validó, en las 3 etapas del ciclo (ascendente, descendente, original): que el resultado esté genuinamente ordenado (nulos/"—" siempre al final), y que el 3er clic restaure el orden original exacto -- **100 encabezados de tablas planas + 40 pruebas de las 8 tablas jerárquicas de Estados financieros (grupo por grupo, cuenta por cuenta, con la fila Total fija verificada en las 3 etapas): 0 fallas.**
- **Cifras completas**: confirmado por grep que no hay abreviaciones K/M en los 6 archivos de Financiero (los formateadores `formatUSDAbrev`/`formatQAbrev`/etc. son de uso exclusivo de Plaguicidas/Nutrientes, fuera de alcance).
- **Gráficas**: título SIEMPRE dentro del recuadro de la tarjeta, leyenda propia centrada bajo el área de datos (nunca la `<Legend>` de Recharts sin ajustar).

**Corrección 1 -- Filtro Grupo 1, año inexistente en la pantalla destino (bug real, no documentado antes).** `useFinancieroFilterGrupo1` (`frontend/src/financiero/FinancieroFilterContext.tsx`) solo recortaba el MES al último disponible cuando el año compartido no existía en los datos propios de la pantalla, pero devolvía el año compartido tal cual -- si ese año tampoco existía (ej. Grupo 1 en 2023, año que `SaldosBancos`/`SaldoBancario` no tienen, solo arrancan en 2024), el selector de año mostraba un valor fuera de sus propias opciones y el de mes quedaba con CERO opciones. Corregido: el hook ahora calcula un `anioEfectivo` (el año disponible más cercano por debajo del compartido, o el menor disponible si el compartido es anterior a todo) y recorta el mes contra ESE año, sin mutar el estado compartido (`grupo1Anio`/`grupo1Mes` -- otras pantallas del grupo no se enteran). Verificado navegando por el sidebar (sin reload): Cuotas Asociados en 2023 → Flujo de caja muestra Año=2024 (12 meses reales, Diciembre seleccionado, título "Flujo de caja al 31 de Diciembre de 2024"); al volver a Cuotas Asociados el año compartido sigue en 2023, intacto.
- **Pendiente:** `dbo.SaldosBancos` no tiene año 2023 (arranca en 2024) -- ver tabla de frescura de datos abajo.

**Corrección 2 -- Filtros independientes sin memoria de sesión.** Contribución 4.5 por millar y Otros ingresos generados usaban `useState` local: al navegar a otra pantalla y volver, el componente se remontaba y la selección manual del usuario se perdía (volvía al default del backend). Corregido: su año (y mes, en Contribución 4.5) ahora vive en `FinancieroFilterContext` (`contribucionAnio`/`contribucionMes`/`otrosIngresosAnio`, hooks `useFinancieroFilterContribucion`/`useFinancieroFilterOtrosIngresos`), sin sincronizarse con ningún grupo -- solo sobrevive al desmontar/remontar dentro de la misma sesión. Verificado: Otros ingresos en Año=2025 → navegar a Estados financieros → volver a Otros ingresos → selector sigue en 2025.

**Corrección 3 -- Ejecución Gastos Acumulado, escala real del eje Y.** Reemplazada la aproximación (redondear el máximo crudo hacia arriba al siguiente 1/2/5×10^n) por la medida DAX real extraída con pbixray, `_Calculos.EscalaEjeY_CentroAcumulado = MAX(TotalEjecutado_Acumulado, TotalPresupuesto_Acumulado) * 1.3`: el tope del eje ahora es ese valor real; las 2 marcas intermedias se redondean al 1/2/5×10^n MÁS CERCANO (no siempre hacia arriba). Verificado exacto contra Agosto 2026 real (Consolidado Ejecutado Q6,575,984 / Presupuesto Q8,440,050 → tope 10,972,065 → eje 0/5,000,000/10,000,000, igual que antes de la corrección y que el reporte real).

**Pendientes de Otros ingresos generados (sección 15), resueltos en esta ronda:**
- Encabezados de la tabla con los textos cortos reales del spec Vega -- aplicados los 5 que el usuario dio verbatim ("CropLife - Proyecto"/"SPMF", "Venta de Material"/"Reciclable", "Intereses Bancarios e"/"Inversión", "Carnet Aplicadores y"/"Certificados y Cursos"/"Capacitaciones", "Venta Minicentros de"/"Plástico Reciclado"); los demás conceptos conservan su nombre completo.
- Última marca del eje X: margen derecho subido de 24px a 56px en las 2 gráficas (barras agrupadas y totales) -- suficiente para el ancho de una etiqueta Q completa en negrita 12px sin abreviar.
- Año anterior sin datos: agregado `anio_anterior_sin_datos: bool` a la respuesta del backend (`OtroIngresoResponse`, calculado contra `anios_disponibles`, mismo criterio que Importaciones). En la web: leyenda "Ejecutado {Año-1} (sin datos)", sin barra dibujada para esa serie en ambas gráficas (la de totales muestra "(sin datos)" en vez de "Q0"), y "—" en su fila de la tabla (los 12 conceptos y el Total). Verificado con Año=2025 (año anterior 2024, sin datos en desarrollo).

**Datos para revisar -- tablas de la BD de desarrollo desactualizadas/incompletas frente al servidor real** (consultado 2026-09-29 contra `DESARROLLO-2`/`AGREQUIMA`):

| tabla | hasta dónde llega en desarrollo | ¿completa? | query para el servidor real | CSV destino |
|---|---|---|---|---|
| `dbo.BalanceGeneral` | 2023–2026, hasta Sept. 2026 | Sí | `SELECT * FROM vw_piq_balance_general;` (CONTACC) | `docs/legacy/financiero/vw_piq_balance_general.csv` |
| `dbo.BalanceSaldos` | 2023–2026, hasta Sept. 2026 | Sí | `SELECT * FROM vw_piq_balance_saldos;` (CONTACC) | `docs/legacy/financiero/vw_piq_balance_saldos.csv` |
| `dbo.SaldosBancos` | 2024–2026 (sin 2023), hasta Sept. 2026 | No -- falta 2023 (gap nuevo, no bloqueante hoy: ninguna pantalla pide 2023 en este grupo por defecto, pero rompía el filtro si se seleccionaba -- ver Corrección 1) | `SELECT * FROM vw_piq_saldos_bancos;` (CONTACC) | `docs/legacy/financiero/vw_piq_saldos_bancos.csv` |
| `dbo.SaldoBancario` | 2025–2026, solo hasta Agosto 2026 | No -- un mes atrasada respecto de BalanceGeneral/SaldosBancos (Flujo de caja y la columna "Saldo Banco" de Conciliación bancaria de Septiembre quedarán vacíos aunque "Saldo Contabilidad" ya tenga ese mes) | `SELECT Concepto, Anio, Mes, Banco, Valor FROM dbo.SaldoBancario;` (servidor real 10.10.0.6,65280, base Agrequima) | `docs/legacy/financiero/SaldoBancario.csv` |
| `dbo.ChequesCirculacion` | 2024-01-09 a 2026-09-10 | Sí | `SELECT * FROM vw_piq_cheques_circulacion;` (CONTACC) | `docs/legacy/financiero/vw_piq_cheques_circulacion.csv` |
| `dbo.Presupuestos` (general) | 2023–2026 | Sí | `SELECT * FROM vw_piq_presupuestos;` (CONTACC) | `docs/legacy/financiero/vw_piq_presupuestos.csv` |
| `dbo.Presupuestos`, cuenta `410104001` | Solo 2025 (12 filas) | No -- gap ya conocido, sigue igual | `SELECT * FROM vw_piq_presupuestos WHERE par_ano = 2026 AND cta_codigo = '410104001';` (confirmar antes de re-exportar todo) | mismo archivo de arriba |
| `dbo.Importacion` | Agrequima y Gremiagro: 2025–2026 | No -- falta 2024, gap ya conocido, sigue igual | `SELECT DISTINCT anio, institucion FROM dbo.Importacion ORDER BY anio, institucion;` (servidor real 10.10.0.6,65280, base Agrequima -- confirmar antes de exportar) | no es CSV de esta carpeta -- se sincroniza con el mecanismo ya usado para Plaguicidas/Nutrientes |
| `dbo.OtroIngreso` | 2025 completo, 2026 Enero–Agosto | Parcial -- falta Septiembre 2026 (esperable, mes en curso) | `SELECT Tipo, Concepto, Anio, Mes, Valor FROM dbo.OtroIngreso;` (servidor real 10.10.0.6, base Agrequima) | `docs/legacy/financiero/OtroIngreso.csv` |
| `dbo.AsociadosCuota` | 2023–2026 | Sí | `SELECT * FROM vw_piq_asociados_cuota;` (CONTACC) | `docs/legacy/financiero/vw_piq_asociados_cuota.csv` |

**Verificado sin diferencias:** los números de control de las secciones 10 a 15 (Ejecución de gastos, Conciliación bancaria, Flujo de caja, Cuotas Asociados, Presupuestos ×3, Contribución 4.5, Otros ingresos) siguen cuadrando exactos tras todos los cambios de esta ronda -- ninguno tocó fórmulas ni cálculos, solo layout/orden/filtros. Tests (108 backend), `tsc` y `build` limpios.

## 17. Métricas nuevas pedidas por el cliente: % Variación, % cobrado y tarjetas de resumen (2026-09-29)

Ronda de agregados pedidos directamente por el cliente, NINGUNO viene del `.pbix` real -- todos calculados en el **frontend** con valores que el backend ya devuelve (sin cambios de backend ni de DAX). Regla general aplicada: `pctSeguro(numerador, base) = base===0 ? 0 : numerador/base*100` (`utils/format.ts`), mismo criterio `DIVIDE(...,...,0)` que ya usa el resto del módulo.

**1. Balance general mensual** -- columna `% Variación` = Diferencia / mes anterior, agregada a la derecha de "Diferencia" en Activo, Pasivo, Patrimonio (grupos + desglose + Total) y en "Total pasivo y patrimonio". Formato `formatPercent` (1 decimal, igual que "Diferencia %" de Presupuestos). Ordenable jerárquicamente igual que las demás columnas de `TablaGrupoExpandible` (ver sección 16) -- no hizo falta ningún cambio en el hook, ya era genérico sobre la cantidad de columnas.

**2. Balance general comparativo** -- columna `% Variación` = Variación / año anterior, mismas filas que el punto 1. Formato `formatPercent2` (2 decimales, igual que "Comparativo ejecutado" en Presupuestos, que es el caso análogo año-vs-año ya existente en el módulo).

**3. Cuotas asociados** -- `% cobrado` = Cancelado/Total, agregado como una 4ª tarjeta (mismo componente `KpiCardIcono` que T/C/P) junto a las 3 tarjetas de arriba; y el `% cobrado` de cada tipo (Cancelado/Total del tipo) agregado junto al título "Tipo X" de cada una de las 3 tablas.

**4. Ejecución gastos por mes / acumulado** -- 3 tarjetas (`KpiCardIconoComparativo`, mismo componente que "Balance general comparativo") arriba de la tabla: Presupuesto (100% fijo + monto), Ejecutado (% de ejecución + monto), Diferencia (% de diferencia + monto) -- las 3 con los valores de **Consolidado** (`data.tarjetas.find(t => t.grupo === "Consolidado")`), coinciden exacto con el resumen de abajo (fila "Ejecución"/chip "Consolidado"). **NO se agregó** el par "% ejecutado y % por ejecutar" -- pendiente de consulta con el cliente (instrucción explícita: son 2 tarjetas con 2 % DISTINTOS -- ejecución y diferencia --, no ese par).

**5. Presupuestos > Ejecución vs presupuesto (mensual y acumulado)** -- mismas 3 tarjetas que el punto 4, mismos valores que la fila Total de la tabla (`data.fila_total`): Presupuesto 100%+monto, Ejecutado (ejecutado/presupuesto)+monto, Diferencia (`diferencia_pct`, ya provisto por el backend, sin recalcular)+monto.

**6. Presupuestos > Comparativo ejecutado** -- 3 tarjetas: "Año anterior" y "Año actual" con `KpiCardIcono` simple (mismo estilo que T/C/P de Cuotas Asociados, sin %) y "% de Variación" en el medio con `KpiCardIconoComparativo` (con `variacion_pct` y `variacion`, ya provistos por el backend). Coinciden exacto con la fila Total.

**Verificación previa (sin cambiar nada), encabezados 2025/2026 invertidos en "Comparativo ejecutado":** confirmado contra el `.pbix` real (bitácora sección 13) que esa inversión existe SOLO en el reporte original y ya fue corregida en la web. Re-verificado ahora en vivo: con Año=2026/Mes=Septiembre, "Ejecutado" (año actual) en "Ejecución vs presupuesto acumulado" = Q6,576,057, EXACTO igual a la columna "2026" del Total de "Comparativo ejecutado" (también Q6,576,057) -- la web NO repite la inversión del `.pbix` original.

**Verificación (Playwright, clics y cambios de filtro reales):**
- 10 filas de `% Variación`/`% cobrado` comparadas valor-a-valor contra su fórmula (numerador/base) en Balance mensual, Balance comparativo y Cuotas Asociados -- 10/10 exactas.
- 9 comparaciones tarjeta-vs-Total/resumen en las 6 pantallas de los puntos 4, 5 y 6 -- 9/9 coinciden exacto (mismo valor, no aproximado).
- Cambio de Año/Mes en "Ejecución vs presupuesto": título y tarjetas se actualizan, y la tarjeta Presupuesto sigue coincidiendo con la nueva fila Total tras el cambio.
- Alineación del nuevo encabezado `% Variación` (Balance mensual y comparativo): 0px de diferencia.
- Orden con clic real sobre `% Variación` (Balance mensual, jerárquico): cambia al ordenar y vuelve exacto al orden original al 3er clic.
- Tests (108 backend), `tsc` y `build` limpios.

**Pendiente de consulta con el cliente:** el par "% ejecutado y % por ejecutar" mencionado en el punto 4 (no agregado esta ronda).

**Corrección de regresión visual (2026-09-29, mismo día):** la primera versión de esta ronda rompió el estándar visual del módulo -- agregar una columna a una tabla o una tarjeta a una fila de tarjetas hacía que TODO lo demás en esa fila/tabla se reacomodara (se achicara o se agrandara) para hacerle lugar, en vez de mantener el tamaño ya aprobado de lo que ya existía. Confirmado midiendo con `getBoundingClientRect` contra el commit `cbf317b` (levantado en un worktree aparte, mismo backend): las tarjetas T/C/P de Cuotas Asociados pasaron de 205x51 a 180x45 (se achicaron al entrar la 4ª tarjeta de % cobrado, que compartía el mismo 58% de fila vía `flex-1`), y las tarjetas nuevas de Ejecución de gastos/Presupuestos/Comparativo ejecutado midieron hasta 331x92 (vs. 279x78 de "Balance general comparativo", su referencia real) por estar atadas al ancho de la TABLA (`anchoTabla`/`ANCHO_TABLA_COMPARATIVO`) en vez de a su propio tamaño de tarjeta. Las tablas de Balance general (mensual/comparativo) en sí NUNCA se rompieron -- midieron 832px en ambas versiones -- pero quedan las 2 reglas igual, para que no se repita en la próxima pantalla:

- **Agregar una columna o una tarjeta nueva NUNCA cambia el ancho de una tabla existente ni el tamaño de una tarjeta existente.** El tamaño se toma de lo que YA existe (la tabla no crece: la columna nueva entra redistribuyendo anchos de columna si hace falta, ver `TablaGrupoExpandible`, que ya reparte sus `anchosDatos`/colgroup en % de una sola vez; una tarjeta nueva NO se agrega con `flex-1` compartiendo el mismo contenedor de las demás -- eso las achica a todas -- se le da un ancho FIJO en px igual al de las tarjetas de referencia, ej. `style={{ width: 205 }}` o `style={{ width: 279 }}`, sin atar el contenedor de la fila de tarjetas al ancho de la tabla de abajo).
- **Regla de formato corregida (2026-09-29, mismo día): el % de una tarjeta nueva usa el MISMO formato que ese mismo valor en la tabla de su propia pantalla -- no un decimal fijo por default.** Si el valor de la tarjeta corresponde a una columna/celda que YA se muestra en una tabla de esa pantalla (ej. "% de Variación" de Comparativo ejecutado = la columna "Variación %" de la fila Total, con `formatPercent2`/2 decimales), la tarjeta usa EXACTAMENTE ese mismo formato, para que el texto sea idéntico entre la tarjeta y la tabla (la primera versión de esta regla forzaba 1 decimal en todas las tarjetas nuevas por default, lo que hacía que la tarjeta y la tabla mostraran el MISMO número con distinta cantidad de decimales -- "-6.0%" en la tarjeta vs. "-6.00%" en la tabla -- confuso para quien compara ambos). Solo si el valor de la tarjeta NO aparece en ninguna tabla de esa pantalla (ej. "% cobrado" de Cuotas Asociados, o el "% de ejecución"/"% de diferencia" de las tarjetas de Ejecución de gastos, que no tienen una columna equivalente en su tabla) va con 1 decimal (`formatPercent`), como el resto del módulo. Los % que YA existían antes de agregar algo nuevo (columnas de tabla ya aprobadas) NO se tocan bajo ningún concepto.

**Verificación (Playwright, worktree `cbf317b` vs. actual, mismo backend):**
- Anchos de tabla (Balance mensual/comparativo, Ejecución gastos ×2, Ejecución vs presupuesto ×2, Comparativo ejecutado): idénticos antes/después en las 7 pantallas (832/1016/1016/957/954/1061px) -- 0px de diferencia en todas.
- Tamaño de tarjetas: T/C/P/% de Cuotas = 205x51 en las 4 (antes 180x45 en las 4); las 5 pantallas con tarjetas nuevas = 279x78 en TODAS (Comparativo ejecutado inicialmente quedó con "Año anterior"/"Año actual" en 279x70 por usar `KpiCardIcono` en vez de `KpiCardIconoComparativo` -- corregido en la misma ronda para que las 3 sean el mismo componente y midan exacto 279x78, ver "Corrección 2" abajo) -- exacto contra la referencia real (antes 331x92/311x86/346x86-96).
- Alineación de las 30 columnas de las 6 tablas de Balance mensual/comparativo (Activo/Pasivo/Patrimonio ×2): 0px en las 30.
- Formato de %: todos los % NUEVOS de esta ronda confirmados en 1 decimal; los % preexistentes (columnas de tabla ya aprobadas antes de esta ronda) confirmados SIN cambios (2 decimales donde ya los tenían).
- Capturas lado a lado (`cbf317b` vs. actual) de las 8 pantallas tocadas.
- Tests (108 backend), `tsc` y `build` limpios.

**Corrección 2 (2026-09-29, mismo día): Comparativo ejecutado, mismo componente en las 3 tarjetas.** "Año anterior" y "Año actual" usaban `KpiCardIcono` (aspecto 4:1 propio, 279x70 con el mismo ancho fijo) mientras "% de Variación" usaba `KpiCardIconoComparativo` (aspecto 3.6:1, 279x78) -- dos tamaños de alto distintos en la misma fila. Corregido: las 3 usan `KpiCardIconoComparativo`; "Año anterior"/"Año actual" van con `porcentaje=""` (línea vacía, sin inventar un % que no tienen -- son montos, no una razón). Las 3 miden ahora 279x78 exacto. Verificado con Playwright: ancho y alto de las 3 tarjetas ±2px entre sí, y el texto de "% de Variación" comparado carácter por carácter contra la columna "Variación %" de la fila Total de la tabla de abajo -- coinciden exacto ("-6.00%" en ambas).

**Corrección 3 (2026-09-30): tarjetas de monto = tamaño de A/PA/PT del Balance mensual; separación título→primer elemento igual en todas las vistas (57px de Power BI escalados).**

1. **Tarjetas de Cuotas Asociados (T, C, P, % cobrado) al tamaño de A/PA/PT de Balance general mensual.** El cliente aclaró que en Power BI las tarjetas de Cuotas (290x95) y las del Balance (306x95) son del MISMO tamaño por diseño -- el ajuste de la ronda anterior (205x51, tamaño propio histórico de Cuotas contra `cbf317b`) partía de una premisa equivocada. Corregido: las 4 tarjetas de Cuotas pasan a 269px de ancho (antes 205px) con `gap-3`/12px entre sí (antes `gap-2`), igual que la fila de A/PA/PT. Al ampliarlas se detectó un efecto colateral: el contenedor de la fila de Cuotas (72% del área de contenido) es más angosto que lo que ocupan 4 tarjetas de 269px + 3 gaps (1112px vs. ~1078px disponibles a resoluciones normales), y el `flex-shrink` por defecto las comprimía de vuelta a ~260px -- se agregó `shrink-0` a cada tarjeta para que mantengan el ancho fijo sin comprimirse, igual que ya no dependen del ancho del contenedor.
2. **`GAP_TITULO_PRIMER_ELEMENTO` (40.2px): separación título→primer elemento igual en las 17 vistas del Financiero.** Calculado del `.pbix` real (Report/Layout): el título termina en y=100 y las tarjetas del Balance empiezan en y=157 -- 57px en la escala de Power BI (alto real de tarjeta ahí: 95px). Escalado a la web con el factor pedido por el cliente ("alto de la tarjeta A de la web / 95"): `57 * (67/95) = 40.2px` (67px es el alto medido de A/PA/PT). Constante única agregada a `TablaGrupoExpandible.tsx`, aplicada vía `style={{ marginTop: GAP_TITULO_PRIMER_ELEMENTO }}` en el primer elemento de contenido debajo del título (la fila de tarjetas si la pantalla tiene, o directamente la tabla/gráfica/filtro si no) en las 17 vistas -- reemplaza 2 convenciones previas que NO eran el valor real de Power BI: el `space-y-3` por defecto (12px, la mayoría de pantallas) y un `GAP_TITULO_CONTENIDO` local duplicado en 2 archivos (Importaciones/Otros ingresos, "4.6%"≈76px). La vista "Comparativo" de Importaciones (sin `<Title>` de página) usaba además un valor propio de 24px (`GAP_HEADER_COMPARATIVO`, decisión de una ronda anterior para no dejar un hueco vacío bajo un título inexistente) -- unificado también a 40.2px por instrucción explícita de esta ronda ("la MISMA en las 17 vistas... sin excepción").

**Verificación (Playwright en primer plano, viewport 1614x900 -- el ancho donde `ANCHO_TABLA_FINANCIERO` (55%) hace que A/PA/PT midan exactamente 269px, ya que esas tarjetas son proporcionales al contenedor y no de ancho fijo):**
- Tarjetas Cuotas (T/C/P/%) vs. A/PA/PT de Balance mensual: 269.00x67.25 vs. 269.02x67.25 en las 4 -- diferencia 0.02px, dentro de ±2px.
- Separación título→primer elemento: 40.19px IDÉNTICO en las 17 vistas (diferencia 0px entre todas).
- Anchos de tabla y tamaños de tarjetas ya fijados en rondas anteriores, sin cambios: tabla Balance mensual/comparativo 831.05px (antes 832px, diferencia atribuible al viewport de medición, no al código); tarjetas de Balance comparativo 279.08x77.52; tarjetas de Ejecución gastos ×2/Ejecución vs presupuesto ×2/Comparativo ejecutado 279.00x77.50 en TODAS -- sin cambios.
- Capturas de las 17 vistas en su estado final.
- Tests (108 backend), `tsc` y `build` limpios.

**Nota técnica de entorno:** el binario de Chromium embebido de Playwright en esta máquina falla al lanzar (`spawn UNKNOWN` / error de side-by-side de Windows) -- la verificación de esta ronda se corrió apuntando `executablePath` al Chrome del sistema (`C:\Program Files\Google\Chrome\Application\chrome.exe`). Además, el frontend de desarrollo solo acepta CORS desde `http://localhost:5173` (no `127.0.0.1:5173`, un origen distinto para el navegador) -- el script de verificación debe navegar a `localhost`, no a `127.0.0.1`.

## 18. Permisos por módulo: un usuario sin acceso no ve ni se entera de que el módulo existe (2026-10-01)

Hasta esta ronda, el control de acceso por módulo (`AccesoImportaciones`/`AccesoFinanciero`/`AccesoIndicadores`, sección 12) solo ocultaba el bloque del Sidebar y protegía los endpoints del backend -- pero la RUTA del frontend (`RequireRole` en `App.tsx`) solo validaba el ROL, no el módulo. Un usuario logueado que escribiera a mano la URL de un módulo sin permiso (ej. `/app/financiero` sin `AccesoFinanciero`) SÍ montaba la página (el `useEffect` de carga de datos llegaba a ejecutarse, aunque el fetch fallara con 403 después). Además, el `detail` del 403 nombraba el módulo exacto ("No tiene acceso al módulo Financiero."), confirmándole a quien no tiene acceso que ese módulo existe.

**Regla de permisos (a partir de ahora, aplica a todo módulo nuevo):** un usuario sin acceso a un módulo no debe poder enterarse de que existe por NINGÚN medio -- ni Sidebar, ni URL directa, ni mensaje de error, ni ninguna petición de red al backend de ese módulo.

**Implementado:**
1. **`RequireModulo`** (`frontend/src/auth/RequireRole.tsx`), mismo patrón que `RequireRole` pero por flag de módulo en vez de por rol -- se anida DENTRO de cada `<Route>` de un sistema (`App.tsx`), sin reemplazar a `RequireRole` (que sigue validando rol + aviso legal para todo `/app`). Si el usuario no tiene el flag, devuelve `<Navigate to="/app" replace />` en vez de los `children` -- la página del módulo NUNCA se monta (su `useEffect` de fetch nunca corre) y no se renderiza ningún texto (un `<Navigate>` no pinta nada).
2. **`AppIndexRedirect`** (`App.tsx`) reemplaza el `<Navigate to="plaguicidas">` fijo del índice de `/app`: calcula el primer módulo al que el usuario SÍ tiene acceso (Importaciones primero, después Financiero) en vez de un destino fijo -- el fijo rompía en loop infinito para un usuario con SOLO Financiero (rebotaba de `/app/plaguicidas` a `/app`, que lo volvía a mandar a `/app/plaguicidas`...). Si no tiene acceso a ningún módulo, muestra un texto neutro ("No tiene acceso a ningún módulo.") que no nombra ninguno.
3. **Backend** (`app/core/deps.py`, `_verificar_acceso_modulo`): el `detail` del 403 pasa a ser genérico ("No tiene acceso a este recurso.") en los 3 `require_acceso_*`, sin mencionar qué módulo. No se tocaron las pantallas de administración (`/admin/cargas/*`, protegidas por ROL "Administrador", no por módulo) -- fuera del alcance pedido.

**Verificación (Playwright en primer plano, 3 usuarios temporales -- Solo Importaciones, Solo Financiero, Ambos):**

| Usuario | Sidebar muestra | URL directa a módulo no permitido | Petición al backend del módulo denegado | Texto del módulo en pantalla | Llamada directa al endpoint |
|---|---|---|---|---|---|
| Solo Importaciones | Solo "Dashboard Importaciones" | `/app/financiero?vista=mensual` → redirige a `/app/plaguicidas` | Ninguna a `/dashboard/financiero/*` | No aparece "Financiero" en ningún lado | 403 "No tiene acceso a este recurso." |
| Solo Financiero | Solo "Dashboard Financiero" | `/app/plaguicidas` y `/app/nutrientes` → redirige a `/app/financiero` | Ninguna a `/dashboard/plaguicidas` ni `/dashboard/nutrientes` | No aparece "Plaguicidas" ni "Nutrientes" en ningún lado | 403 "No tiene acceso a este recurso." |
| Ambos | Los 2 bloques | (no aplica, tiene los 2 accesos) | (no aplica) | (no aplica) | (no aplica, control positivo) |

Tests (108 backend), `tsc` y `build` limpios. Nota de entorno: el backend de desarrollo estaba corriendo sin `--reload` (proceso persistente desde una sesión anterior) -- el primer intento de verificación trajo el `detail` VIEJO del 403 ("...módulo Financiero.") pese a que el código ya estaba corregido; se reinició el proceso (`uvicorn app.main:app --host 127.0.0.1 --port 8001`, mismo comando) para que tomara el cambio, y se confirmó el `detail` nuevo después.

## 19. Permisos de /admin: cargas exclusivas de "Administrador" (2026-10-02)

Auditoría pedida antes de cambiar nada: ¿qué ve hoy cada rol en `/admin` y qué rutas/endpoints de carga puede usar? Resultado -- **la protección de cargas por rol YA EXISTÍA, completa, en las 2 capas que importan:**
- **Frontend:** cada ruta de carga/nomenclatura (`cargas/plaguicidas`, `cargas/nutrientes`, `nomenclatura/plaguicidas`, `nomenclatura/nutrientes`, `cargas/saldos-bancarios`, `cargas/otros-ingresos`) ya estaba envuelta individualmente en `<RequireRole roles={["Administrador"]}>` dentro de `App.tsx` -- un link directo de "Administrador de Usuarios" o "Usuario" ya rebotaba sin montar la página. El menú de `AdminLayout.tsx` ya filtraba por `esAdministradorDeUsuarios` (ese rol solo ve "Usuarios" en el menú).
- **Backend:** los 5 endpoints de `admin_cargas.py` y el router completo de `admin_nomenclatura.py` ya exigían `Depends(require_role("Administrador"))`.
- El rol "Usuario" nunca llega ni siquiera a `AdminLayout`: el `RequireRole` que envuelve TODO `/admin` en `App.tsx` solo permite `["Administrador", "Administrador de Usuarios"]` -- un "Usuario" que escriba cualquier URL de `/admin/*` rebota a `/app` antes de que exista ninguna ruta hija que evaluar.

**El único cambio real de esta ronda:** unificar el texto del 403 por rol. `require_role()` (`app/core/deps.py`) devolvía `"No tiene permisos para esta acción"` -- genérico (no nombraba el rol ni la pantalla), pero con una redacción distinta del `"No tiene acceso a este recurso."` ya establecido para los permisos por módulo (sección 18). Cambiado a ese mismo texto exacto, para que los 2 tipos de 403 (por rol y por módulo) sean indistinguibles entre sí. No afecta ningún otro comportamiento: `require_role` solo se usa en `admin_cargas.py`, `admin_nomenclatura.py` y `admin_usuarios.py` (este último permite explícitamente "Administrador" Y "Administrador de Usuarios" -- sin cambios ahí, Administrador de Usuarios sigue pudiendo crear/editar usuarios).

**Verificación (Playwright en primer plano, 3 usuarios temporales -- uno por rol):**

| Rol | Aterriza en | URL directa a las 6 rutas de carga/nomenclatura | Petición al backend de carga/nomenclatura | Llamada directa a `/admin/cargas/historial` | Crear/editar usuarios |
|---|---|---|---|---|---|
| Administrador | `/admin/cargas/plaguicidas` (todo el menú de cargas + Usuarios) | Entra a las 6, cada una pide sus propios datos normalmente | Sí (esperado, tiene permiso) | (no aplica, sí tiene acceso) | (no aplica a este rol) |
| Administrador de Usuarios | `/admin/usuarios` (solo "Usuarios" en el menú) | Las 6 rebotan a `/admin/usuarios` | Ninguna (solo la navegación del propio React Router, 0 llamadas a `/api/admin/cargas/*` ni `/api/admin/nomenclatura/*`) | 403 "No tiene acceso a este recurso." | Crear: 201. Editar: 200 -- sigue funcionando |
| Usuario | `/app/plaguicidas` (nunca llega a `/admin`) | Las 6 rebotan a `/app/plaguicidas` | Ninguna | 403 "No tiene acceso a este recurso." | (no aplica a este rol) |

Tests (108 backend), `tsc` y `build` limpios.

## 20. Cuadre exhaustivo del módulo Financiero contra SQL independiente, datos del servidor real (2026-10-02)

Ronda de verificación pedida para dejar el módulo listo para publicar: datos actuales de las 10 tablas de Financiero (export real del servidor del cliente, reemplazando los CSV de `docs/legacy/financiero/` -- ver conteos abajo), consultas SQL independientes (sin reusar código del backend) para cada vista, comparadas contra la API en 2 períodos (Septiembre 2026 por defecto / Diciembre 2025), tolerancia Q0.01.

**Datos recargados.** Los 10 CSV de `docs/legacy/financiero/` se reemplazaron con una exportación real del servidor del cliente (hecha por el usuario) y se cargaron con `cargar_datos_financiero_inicial.py` (TRUNCATE + INSERT, confirmado sin duplicar). Conteos cargados: BalanceSaldos 15,105; BalanceGeneral 3,292; CatalogoCuentas 294; CentrosDeCosto 30; Presupuestos 128,016; AsociadosCuota 161; ChequesCirculacion 1,393; SaldosBancos 120 (186 filas crudas en el CSV, BANRURAL trae 3 filas por período que se suman al cargar -- comportamiento ya documentado, no un error); SaldoBancario 210; OtroIngreso 480. **Hallazgo positivo:** a diferencia de rondas anteriores, `BalanceGeneral`/`BalanceSaldos` ahora traen **2023-2026 completos** (antes solo 2025-2026) -- los huecos de "año anterior sin datos" documentados en secciones 13/16 para Diciembre 2025 vs. 2024 ya NO aplican con estos datos.

**BUG REAL ENCONTRADO Y CORREGIDO: "Ingresos"/"Egresos" de Estados Financieros sumaba cuentas del lado equivocado.** `_detalle_grupo_mensual`/`_detalle_grupo_comparativo` (`dashboard_financiero.py`) traían TODAS las cuentas de `BalanceSaldos` con movimiento en el período (sin filtrar por tipo de cuenta) y clasificaban por `CatalogoAgrupadorCuentas` solo para la ETIQUETA de grupo -- una cuenta que no matcheaba ningún `Codigo` del catálogo cae a "Sin clasificar" pero **igual se sumaba al total**. Encontrado comparando Diciembre 2025: la web mostraba Ingresos Q617,885.56, mi SQL independiente (filtrado por el catálogo real de Ingresos) daba Q607,094.58 -- diferencia de Q10,790.98, de 5 cuentas de EGRESOS (510xxxxxx: Alquileres, Mantenimiento de vehículos, etc.) con un crédito incidental (una devolución/corrección) que se colaban en el total de Ingresos. Confirmado contra la medida DAX real del `.pbix` (`PIQ_AGREQUIMA.pbix`, tabla `_Calculos`, medida `Acumulado Ingresos mes corriente`): el filtro real es `LEFT(Cta_Codigo,1) = "4"` para Ingresos y `"5"` para Egresos -- NO el catálogo de agrupación (ese solo decide la sub-categoría de MOSTRAR, dentro de las cuentas que ya pasan el filtro de primer dígito). Corregido: ambas funciones ahora reciben un `primer_digito` ("4"/"5") y lo agregan al `WHERE` de la consulta. Verificado exacto en Septiembre 2026 y Diciembre 2025, mensual y acumulado, contra la medida DAX real.

**BUG REAL ENCONTRADO Y CORREGIDO: años inválidos de `dbo.Importacion` sin excluir.** El cliente reportó filas con `anio=20126` (+100 años, error de captura viejo) y copias duplicadas de 2024/2025 con signo invertido (`-2024`/`-2025`, mismo contenido, ID distinto) en el servidor real -- ninguna de las 8 consultas de `dashboard_importaciones_financiero.py` las excluía (ni el selector de año `_anios_disponibles_importacion`, ni los agregados por año específico). Corregido: constante `_FILTRO_ANIO_VALIDO = "anio BETWEEN 2023 AND 2026"` (rango real de datos válidos del cliente, bump manual del límite superior cuando se cargue el año siguiente) agregada a las 8 consultas. **No se pudo reproducir el escenario completo en esta base de desarrollo**: no existen filas con `anio=20126` ni negativo acá, así que no hay forma de confirmar con una consulta "no se pierde ningún registro válido" contra esos datos puntuales -- el fix es correcto por inspección de código y por el rango documentado, pero la confirmación empírica queda pendiente de correr contra el servidor real. En esta base, `dbo.Importacion` tiene 2025 completo (12 meses, CIF válido en los 12, ambas instituciones) y 2026 Enero-Julio (también CIF válido en los 7) -- **no falta ningún mes de Agosto a Diciembre 2025** (ya estaba completo, no hubo que corregir nada ahí). Selector de año: sigue mostrando solo `[2025, 2026]` en esta base (no hay 2023/2024 cargados acá) -- el fix evita que basura se sume a esa lista el día que el servidor real sincronice esos años, pero no puede "inventar" los 2 años que faltan localmente.

**Verificado EXACTO (±Q0.01, la mayoría con diferencia 0.00) contra SQL independiente, Septiembre 2026 y Diciembre 2025:**

| Vista | Métrica verificada | Resultado |
|---|---|---|
| Ingresos y desembolsos mensual | Ingresos/Egresos/Resultado del mes | Exacto en los 2 períodos (tras el fix) |
| Ingresos y desembolsos acumulado | Ingresos/Egresos acumulados | Exacto en los 2 períodos (tras el fix) |
| Balance general mensual | KPIs Activo/Pasivo/Patrimonio | Exacto en los 2 períodos |
| Balance general comparativo | Variación Q y % de A/PA/PT | Exacto en los 2 períodos |
| Cuotas asociados | Total/Cancelado/Por cobrar | Exacto en los 2 períodos |
| Conciliación bancaria | Fila "Totales" por banco (Saldo Banco) | Exacto en Dic-2025 (los 4 bancos); Sep-2026 sin datos de `SaldoBancario` ese mes (gap de frescura ya conocido, no bug) |
| Flujo de caja | Disponibilidad final | Exacto en los 2 períodos (confirmado que NO se restan 2 veces los cheques en circulación, regla ya documentada en sección 11) |
| Ejecución gastos por mes/acumulado | Consolidado (presupuesto/ejecutado) | Exacto en los 2 períodos, ambas vistas |
| Ejecución vs presupuesto mensual/acumulado | Fila Total | Exacto en los 2 períodos, ambas vistas (mismo origen que Ejecución de gastos) |
| Comparativo ejecutado | Fila Total (año actual/anterior/variación) | Exacto en los 2 períodos -- confirma que 2024 ya tiene datos reales (antes "sin datos") |
| Ingresos por importación | CIF por año, regla especial "Total año" (solo meses que también existen en el año actual) | Exacto en 2025 y 2026, incluida la regla especial |
| Comparativo de importaciones | CIF por institución (Agrequima/Gremiagro) | Exacto en los 2 años |
| Kilolitros | Precio por kilolitro del mes específico | Exacto en Jul-2026 y Dic-2025 |
| Contribución 4.5 por millar | Tarjeta mes y acumulada (realizado/presupuesto/%) | Exacto en los 2 períodos -- confirma presupuesto 2026 ausente en origen (dato de origen, pendiente de consulta al cliente, ya documentado en sección 14) |
| Otros ingresos generados | Total (ejecutado año/año-1, presupuesto, %) | Exacto en 2025 y 2026 |

**Dato de origen, pendiente de consulta al cliente (NO modificado):** `dbo.Presupuestos`, cuenta `410104001` (Contribución 4.5 por millar), solo tiene 12 filas para 2025 (Q7,861,336.64 total) -- **2026 sigue sin existir en origen**, incluso con la exportación nueva de hoy. Confirmado con `SELECT par_ano, COUNT(*), SUM(pre_presupuesto) FROM dbo.Presupuestos WHERE cta_codigo='410104001' GROUP BY par_ano` -- una sola fila, año 2025.

**Diferencias intencionales con Power BI (ya documentadas en rondas anteriores, re-confirmadas esta ronda sin cambios):** año anterior siempre `año_seleccionado - 1` (nunca `YEAR(TODAY())`); encabezados de "Comparativo ejecutado" correctos (no invertidos como el `.pbix` original); "Disponibilidad en depósitos monetarios y caja" de Flujo de Caja NO resta los cheques en circulación una segunda vez.

**Verificación visual final (Playwright en primer plano, viewport 1614x900, las 17 vistas):** separación título→primer elemento 40.19px IDÉNTICA en las 17 (sin cambios tras los fixes de código); tamaños de tarjeta sin cambios (269x67.25 simples, 279x77.5-77.52 comparativas); capturas de las 17 vistas tomadas. `tsc -b`, `npm run build` y pytest (108) limpios después de los 2 fixes.

**Archivos de código corregidos esta ronda:**
- `backend/app/services/dashboard_financiero.py` -- filtro `LEFT(Cta_Codigo,1)` agregado a `_detalle_grupo_mensual`/`_detalle_grupo_comparativo` (bug de Ingresos/Egresos).
- `backend/app/services/dashboard_importaciones_financiero.py` -- `_FILTRO_ANIO_VALIDO` agregado a las 8 consultas sobre `dbo.Importacion` (años corruptos del servidor real).

## 21. Publicación Financiero -- plan exacto para mañana (2026-10-02)

Rama `financiero`, 35 commits por delante de `main`, que no se movió (0 commits propios) -- **el merge sería un fast-forward limpio, confirmado con `git merge-tree`: 0 conflictos**. Pasos en orden para publicar:

1. **Revisar y aprobar los cambios de código de esta ronda** (sección 20: `dashboard_financiero.py`, `dashboard_importaciones_financiero.py`) -- son los únicos archivos de código sin commitear a esta altura.
2. **Commit en `financiero`** de los archivos de código aprobados (y de la bitácora). Decisión pendiente del usuario: si los 10 CSV actualizados de `docs/legacy/financiero/` también se commitean (ver recomendación en el reporte final de esta ronda).
3. **Merge a `main`**: `git checkout main && git merge financiero` (fast-forward, sin `--no-ff` necesario dado que no hay divergencia -- confirmar con `git merge-tree` de nuevo justo antes, por si `main` se movió mientras tanto).
4. **Scripts SQL en el servidor real (PIQ_IA)**, en este orden (ver `LEEME.txt` actualizado, Pasos 1 a 3L): `01` → `02` → `03` → `04` a `10` (fixes de collation/exclusión, si no corrieron antes) → `11_aviso_legal_usuarios.sql` → `11b_control_acceso_por_modulo.sql` (renombrado de `11_control_acceso_por_modulo.sql` -- ver sección 23, dos scripts no pueden compartir el número 11) → `12_agrupador_cuentas_financiero.sql` → `13_saldos_bancos_financiero.sql` → `14_otro_ingreso_financiero.sql` → `15_tablas_financiero.sql` → `16a_datos_financiero.sql` → `16b_datos_financiero.sql`. Todos idempotentes -- seguro re-correrlos si no se está seguro de cuáles ya se aplicaron (ver las consultas de verificación en el nuevo LEEME.txt).
5. **Desplegar backend y frontend** (mismo mecanismo ya usado para Importaciones -- ver checklist del `LEEME.txt`).
6. **Dar acceso a Financiero** a los usuarios reales que correspondan (pantalla Usuarios, checkbox "Acceso a Financiero" -- ver `LEEME.txt`).
7. **Verificación final en el servidor real**: entrar con un usuario real, confirmar que las 17 vistas cargan sin error 500. Los NÚMEROS pueden diferir de los de esta ronda (los datos del servidor real evolucionan día a día) -- lo que hay que confirmar es que cargan, no que coincidan con los de hoy.
8. **Pendiente, no bloqueante:** decidir si se deja `sync_piq_ia.py` configurado tal cual (con la brecha de nombres de tabla documentada en el `LEEME.txt` -- no actualiza Financiero todavía) o se pospone arreglarlo. Mientras tanto, el refresh de datos de Financiero sigue siendo manual (repetir el Paso 3L).

## 22. Corrección del filtro de año fijo en Importaciones y cuadre fila por fila de las 17 vistas (2026-10-02)

El cliente corrigió 2 puntos de la sección 20: (1) el filtro `_FILTRO_ANIO_VALIDO` agregado ahí usaba un rango de calendario fijo (`BETWEEN 2023 AND 2026`) -- "no deberían de existir años fijos"; (2) la verificación de esa ronda solo cuadró totales/tarjetas, no cada cuenta -- "¿a mí de qué me sirve que cuadre un total?".

**Filtro sin años fijos.** `_FILTRO_ANIO_VALIDO` (`dashboard_importaciones_financiero.py`) pasa de un rango hardcodeado a una regla RELATIVA a hoy: `anio > 0 AND anio <= YEAR(GETDATE())` -- descarta cualquier año negativo (copias con signo invertido) y cualquier año mayor al actual (el "+100 años", ej. 20126, sin importar qué año sea "hoy"). No hace falta tocar el código cada año nuevo.

**Por qué solo se desplegaban 2 años, con evidencia.** Confirmado con 3 consultas independientes contra esta base de desarrollo (AGREQUIMA, DESARROLLO-2): `dbo.Importacion` (misma tabla y fuente que usa Plaguicidas/Nutrientes vía el modelo `Importacion` -- confirmado leyendo ambos `services/*.py` y, por separado, el Power Query real del `.pbix`: `Sql.Database("10.10.0.6,65280","Agrequima"){[Schema="dbo",Item="Importacion"]}`, sin ningún filtro de año en la M) tiene SOLO `anio IN (2025, 2026)` -- `SELECT DISTINCT anio` sin ningún filtro, antes y después del fix, da el mismo resultado. El selector del frontend (`FilterYear`/`FilterYearMonth`, `PowerBiFilter.tsx`) no trunca ni limita la lista en ningún punto -- renderiza `aniosOpciones` completo. El propio selector de años de Plaguicidas (`dashboard_plaguicidas.py`, `Importacion.anio.distinct()`, mismo patrón sin filtro) mostraría también solo 2 años con estos mismos datos. **Conclusión:** no hay ningún límite de código, ni acá ni en Plaguicidas -- la causa de "solo 2 años" es que esta base de desarrollo específica no tiene 2023/2024 cargados en `dbo.Importacion`. Si el servidor real sí los tiene (como afirma el cliente), el fix ya aplicado los mostrará automáticamente en cuanto esos datos estén en la base que lea la aplicación -- no se puede confirmar el escenario completo (incluyendo la exclusión real de `anio=20126`/negativos) sin acceso a esos datos, que no existen en esta base.

**Cuadre fila por fila, cuenta por cuenta, las 17 vistas (no solo totales):**

| Vista | Filas/cuentas comparadas | Coinciden exacto (±Q0.01) | Diferencias reales |
|---|---|---|---|
| Ingresos y desembolsos mensual | Por categoría (Ingresos LEFT='4', Egresos LEFT='5') | Todas (tras el fix de anoche) | 0 |
| Ingresos y desembolsos acumulado | Por categoría | Todas | 0 |
| Balance general mensual | 85 cuentas (Activo+Pasivo+Patrimonio) | 85/85 | 0 |
| Balance general comparativo | 91 cuentas | 91/91 | 0 |
| Cuotas asociados | 39 filas (3 tipos × asociados) | 39/39 | 0 |
| Conciliación bancaria | 20 filas (4 bancos × 5 líneas) | 20/20 | 0 |
| Flujo de caja | 12 filas (Caja+4 bancos+Totales+Disponibilidad+2 inversiones+Total final+cheques) | 12/12 | 0 |
| Ejecución gastos por mes | 20 categorías (catálogo completo, normalizando mayúscula/coma de etiqueta) | 20/20 | 0 |
| Ejecución gastos acumulado | 20 categorías | 20/20 | 0 |
| Ejecución vs presupuesto mensual | 20 categorías | 20/20 | 0 |
| Ejecución vs presupuesto acumulado | 20 categorías | 20/20 | 0 |
| Comparativo ejecutado | 17 categorías con movimiento (+3 correctamente excluidas, 0 en ambos años) | 17/17 | 0 |
| Ingresos por importación | 7 filas (2026) + 12 filas (2025) | 19/19 | 0 |
| Comparativo de importaciones | 7+7 (2026) + 12+12 (2025), por institución | 38/38 | 0 |
| Kilolitros | 3+3 filas de precio + 3+3 tarjetas de cambio | 6/6 (+ 3 tarjetas con "sin datos 2024" correctamente mostrado) | 0 |
| Contribución 4.5 por millar | 9 filas (2026) + 12 filas (2025) | 21/21 | 0 |
| Otros ingresos generados | 13 filas (12 conceptos + Total) × 2 años | 26/26 | 0 |

**Total: 471 filas/cuentas/categorías comparadas contra SQL independiente, 0 diferencias reales.** Hallazgo menor (no numérico): 3 categorías de Egresos tienen su nombre en `CatalogoAgrupadorCuentas` sin coma ("Sueldos Bonificaciones...") pero se muestran con coma en pantalla ("Sueldos, Bonificaciones...") -- mismo valor exacto en ambos lados, es una diferencia de rótulo, no de cálculo; no se tocó porque no fue parte de lo pedido.

**Filas no verificadas:** ninguna de las que la pantalla realmente muestra. Las únicas "faltantes" en mis conteos iniciales eran filas con valor 0.00 en ambos períodos que el propio criterio documentado de cada pantalla excluye a propósito (grupo entero en 0, o año sin ninguna fila de origen) -- no son filas que el usuario vea y no se hayan revisado, son filas que ni la pantalla ni los datos muestran.

Tests (108 backend), `tsc` y `build` limpios. Usuario temporal y los 7 scripts de verificación de esta ronda, borrados. No se regeneraron `16a_datos_financiero.sql`/`16b_datos_financiero.sql` ni se tocó el `LEEME.txt` de la sección 21: los datos de la base local no cambiaron esta ronda (solo 2 archivos de código), así que ambos siguen representando exactamente lo mismo que ya está cargado.

## 23. Publicación en el servidor real (VMI1979377\SQLEXPRESS) -- preparación y merge a main (2026-10-02)

El cliente confirmó el estado real del servidor de producción: base `PIQ_IA` en `VMI1979377\SQLEXPRESS`, con los scripts `01` a `10` y `11_aviso_legal_usuarios.sql` ya corridos -- **ninguna tabla de Financiero existe todavía ahí**. App instalada en `C:\Pronostiq\Agrequima-pronostiq` (`backend\`, `deploy\`, `frontend\`, `logs\`, `.env`, `nssm.exe` como servicio de Windows).

**Dos scripts con el mismo número 11.** `11_control_acceso_por_modulo.sql` (nunca corrido en el servidor real) se renombró a **`11b_control_acceso_por_modulo.sql`** (`git mv`) para no chocar con `11_aviso_legal_usuarios.sql` (ya corrido ahí) -- se actualizaron las 2 referencias existentes (`LEEME.txt`, esta bitácora, sección 21). Ninguna línea de código Python referencia el nombre del archivo, solo documentación.

**Revisión de `11b_control_acceso_por_modulo.sql`:**
- **Idempotente**: confirmado por lectura -- cada `ALTER TABLE` está protegido con `IF NOT EXISTS (...INFORMATION_SCHEMA.COLUMNS...)`.
- **`AccesoImportaciones=1` para cuentas existentes**: confirmado -- `ALTER TABLE ADD ... DEFAULT 1` sobre una tabla con filas backfillea el valor por defecto en las filas ya existentes (comportamiento estándar de T-SQL), no hizo falta corregir nada.
- **`AccesoFinanciero` para el Administrador**: el script original dejaba `AccesoFinanciero=0` para TODAS las cuentas sin ninguna excepción -- se agregó un `UPDATE` (incondicional, idempotente) que deja `AccesoFinanciero=1` para toda cuenta cuyo rol sea "Administrador", vía `JOIN` contra `dbo.Roles` (no por nombre de usuario literal, que podría ser cualquier cosa) -- el resto de los roles quedan en 0 como ya estaba.

**Paquetes y variables de entorno:** `backend/requirements.txt` es **idéntico** entre `main` y `financiero` (confirmado con `git diff`, sin salida) -- ningún paquete nuevo que instalar en el servidor. Ninguna variable de entorno nueva hace falta para que Financiero funcione: revisando `app/core/config.py` y los 6 archivos de servicios de Financiero, todos usan la MISMA conexión a `PIQ_IA` (`DB_SERVER`/`DB_NAME`/`DB_USER`/`DB_PASSWORD`) que ya usan Plaguicidas/Nutrientes, sin ninguna configuración propia (la sincronización nocturna contra CONTACC sí necesitaría variables nuevas, pero quedó fuera de esta ronda a pedido explícito).

**Guía de publicación para este servidor específico**, agregada a `LEEME.txt` (sección nueva al final, "PUBLICACIÓN DE FINANCIERO EN ESTE SERVIDOR YA INSTALADO"): respaldo de la base + carpetas antes de empezar, los 7 scripts SQL en orden con su consulta de verificación cada uno (`11b`→`12`→`13`→`14`→`15`→`16a`→`16b`, dejando explícito que `11_aviso_legal_usuarios.sql` NO se vuelve a correr), qué copiar (`backend\app`, el build nuevo de `frontend\dist`), cómo reiniciar con `nssm.exe restart`, verificación final (usuario solo-Importaciones no ve Financiero; con el permiso sí; cómo dar el permiso), y cómo volver atrás (detener servicio, restaurar carpetas de respaldo, restaurar el `.bak` de la base si hiciera falta).

**Merge a `main`:** `financiero` (36 commits propios) hacia `main` (0 commits propios desde la base común) -- fast-forward limpio, confirmado antes con `git merge-tree` (0 conflictos). Ver el hash y `git log` resultante en el reporte de esta ronda (no se repite acá para no duplicar).

## 24. Financiero: copias fieles de las vistas del cliente + sincronización nocturna (2026-10-05)

> **CORREGIDO en la sección 25:** esta sección describe `SaldoBancario` y `OtroIngreso` como parte de la sincronización (10 objetos). Fue un error de la instrucción: esas dos tablas se cargan SOLO por Excel y NO se sincronizan. Vale lo que dice la sección 25: la sincronización trae únicamente las 8 vistas de CONTACC.

**Pedido del cliente (textual, resumido):** que Financiero quede "tal cual como estaba en el Power BI": una tabla con el nombre de la vista por cada vista que se trae del servidor del cliente, con todos sus campos y sin resumir ("si mañana necesito un campo que tenía, no tengo que rehacer la tabla"), y que esas tablas se actualicen todas las noches con los datos del día anterior, desde el servidor del cliente (VPN).

**Qué se encontró (comparando `docs/legacy/financiero/estructura_vistas_cliente.csv`, sacado de `INFORMATION_SCHEMA.COLUMNS` del cliente, contra lo que había en `PIQ_IA`):**
- Las 8 tablas que lee la web (`BalanceSaldos`... `SaldosBancos`) tenían los **mismos campos de datos** que las 8 vistas de CONTACC (9, 11, 5, 5, 6, 7, 12 y 7), pero cargados a mano desde CSV con otros tipos: `money` → `DECIMAL(18,2)` (solo 8 filas de `Presupuestos` de 128.016 perdían decimales, ej. `738750.9448` → `738750.94`), `smallint` → `INT`, textos más anchos, más un id autonumérico, `fechamod` y `userid` propios. `SaldosBancos` además estaba **resumida**: se sumaban las 3 filas por período de BANRURAL.
- `SaldoBancario` y `OtroIngreso` tenían estructura distinta a la del cliente: id autonumérico al principio, columna `UsuarioId` (en el cliente es `userid`), `NVARCHAR(50)/(200)`, campos que aceptaban NULL (en el cliente son NOT NULL) y sin los dos campos del cliente en el mismo orden.
- El sync que existía (`sync_piq_ia.py` con `SYNC_VISTAS_CONTACC`) copiaba las vistas de CONTACC a tablas `vw_piq_*` que **ninguna pantalla leía**, y no traía `SaldoBancario`/`OtroIngreso`.

**Qué se construyó:**
1. `17_copias_fieles_financiero.sql`: crea en `PIQ_IA` una tabla por cada uno de los 10 objetos con el **mismo nombre, mismos campos, mismo orden y tipos equivalentes** (generado desde el CSV de estructura, sin transcripción manual) más un índice agrupado por año/mes en 6 de ellas. `SaldoBancario`/`OtroIngreso` se **reconstruyen con la estructura del cliente sin perder datos** (copia → verificación de filas y contenido en ambos sentidos → renombra la vieja a `*_respaldo`, todo en una transacción). Si ya existe una tabla homónima con otra estructura, la aparta como `*_previa` (no borra). Idempotente (el bloque de migración va en SQL dinámico para que la segunda corrida no falle por columnas viejas).
2. `18_vistas_financiero.sql`: en UNA transacción renombra las 8 tablas resumidas a `*_respaldo` y crea **vistas con el nombre original y las columnas de datos que la web usa** sobre las copias fieles, con la misma lógica del cargador manual (vacío→NULL, enteros→INT, importes→`DECIMAL(18,2)`, `SaldosBancos` sumado por banco/mes/año, `cta_codigo` NVARCHAR→VARCHAR). El código de la web **no cambió** en esa parte. Incluye cómo volver atrás (comentado).
3. `sync_financiero.py` (script nuevo y autónomo, en vez de modificar `sync_piq_ia.py`: ese refleja el esquema con SQLAlchemy y lo crea si falta, mientras acá la estructura es fija; además se necesitaba log diario por tabla, código de salida útil y reemplazo transaccional, y mezclarlo habría complicado ambos). Lee directo de CONTACC y de Agrequima (10.10.0.6,65280) con credenciales del `.env` del servidor. Por objeto: valida la estructura de la copia, lee TODO el origen a una tabla de staging real y recién al terminar completo hace `DELETE`+`INSERT` y `COMMIT` en una transacción; si algo falla la copia conserva los datos de ayer; si un objeto falla los demás siguen; si el origen devuelve 0 filas y la copia tenía datos, no la reemplaza; reintenta cada objeto 2 veces (60 s). Log diario `logs\sync_financiero_AAAAMMDD.log`; salida 0 = OK, 1 = falló algún objeto, 2 = falta configuración. Modos `--solo`, `--probar`, `--probar-completo`. Se quitó de `sync_piq_ia.py` (ambas copias) la rama de CONTACC para que no haya dos mecanismos escribiendo las mismas tablas.
4. PowerShell: `probar_conexion_origen.ps1`, `correr_sync_financiero.ps1`, `instalar_tarea_programada.ps1` (tarea "PIQ_IA_Sync_Financiero", diaria 2:00 a. m., cuenta SYSTEM, corre sin sesión iniciada). Guía completa en `deploy_servidor_real/LEEME_SYNC.txt`.
5. Cambio de código obligado: las cargas por Excel de `SaldoBancario`/`OtroIngreso` (`etl_saldo_bancario.py`, `etl_otro_ingreso.py`) insertan en `userid` en vez de `UsuarioId`. `db/agrequima_schema_sql_server.sql` actualizado a la estructura del cliente; la base de desarrollo y `Agrequima_Test` se migraron con el mismo bloque del script 17 (conservan `*_respaldo`).

**Variables nuevas del `.env` del servidor** (las de destino `DB_*` ya existen): `SYNC_CONTACC_DB_SERVER`, `SYNC_CONTACC_DB_NAME`, `SYNC_CONTACC_DB_USER`, `SYNC_CONTACC_DB_PASSWORD`; opcionales `SYNC_AGREQUIMA_DB_*` (por defecto reutiliza las de CONTACC y la base `Agrequima`), `SYNC_FINANCIERO_OMITIR`, `SYNC_FINANCIERO_REINTENTOS`, `SYNC_FINANCIERO_ESPERA_SEG`, `SYNC_FINANCIERO_LOG_DIR`.

**Verificación local (base de prueba: clon de la base de desarrollo como "PIQ_IA" + dos bases que simulan CONTACC y Agrequima con la estructura del CSV y los datos de `docs/legacy/financiero/`; todas borradas al terminar):**
- Copias fieles vs origen: 10/10 con los mismos campos (9, 11, 5, 5, 6, 7, 12, 7, 7, 7), mismas filas y `EXCEPT` en ambos sentidos = 0.
- 8 vistas vs 8 tablas resumidas anteriores (`*_respaldo`): mismas filas, valores **y tipos**, 0 diferencias.
- Cuadre de pantallas: los 14 endpoints del Financiero × 9 períodos (102 respuestas, 34.130 valores, 3.197 registros por cuenta contable) comparados antes/después del cambio: **0 diferencias** (control negativo: un valor alterado en 0,02 se detecta).
- Rendimiento: las vistas sin índice eran ~24 % más lentas que las tablas; con el índice agrupado por año/mes del script 17 son ~31 % más rápidas (suma de medianas de los 14 endpoints: 959 ms → 663 ms).
- Fallas (6 escenarios, todos con la copia fallida **idéntica a la de ayer** y las demás actualizadas): credenciales malas en CONTACC; un objeto inexistente en el origen; falla en pleno reemplazo (el `DELETE` se revierte); origen con 0 filas; corte real de la sesión de origen a mitad de la lectura, sin reintento (conserva) y con reintento (se recupera).
- Tests (108 backend), `tsc -b` y `npm run build` limpios.

**Lo que NO se pudo probar acá:** el registro real de la tarea programada (requiere PowerShell de administrador; se validó la construcción de la tarea, el chequeo de permisos y el comando exacto) y la conexión real a `10.10.0.6,65280` desde el servidor (esta máquina no es ese servidor).

**Riesgos documentados:** (1) `SaldoBancario`/`OtroIngreso` también se cargan por Excel desde la web; el sync nocturno reemplaza su contenido con el del cliente (opción `SYNC_FINANCIERO_OMITIR` para excluirlas). (2) El servidor tiene que llegar por red/VPN a 10.10.0.6,65280. (3) `16a/16b_datos_financiero.sql` y `cargar_datos_financiero_inicial.py` no sirven una vez creadas las vistas (escriben en tablas que pasan a ser vistas).

## 25. Corrección: SaldoBancario y OtroIngreso se cargan SOLO por Excel, no se sincronizan (2026-10-05)

**Aclaración del cliente (textual, resumida):** Saldos bancarios y Otros ingresos los manda el cliente por Excel y se cargan desde el mantenimiento de cargas del sistema, igual que Importaciones, Plaguicidas y Nutrientes; ellos ven directamente lo que se cargue. Las demás tablas sí se alimentan de la contabilidad. Esto siempre fue así: **nunca se pidió sincronizar `SaldoBancario` ni `OtroIngreso`**; la instrucción de la sección 24 las incluyó por error en la lista de objetos.

**Qué se revirtió (todo lo que la sección 24 hizo sobre esas dos tablas):**
- `17_copias_fieles_financiero.sql` ya no crea, migra ni renombra nada de `SaldoBancario`/`OtroIngreso` (se quitó el bloque de migración y su verificación); ahora maneja solo las 8 copias de CONTACC (+ sus índices).
- `etl_saldo_bancario.py` y `etl_otro_ingreso.py` vuelven a escribir `UsuarioId` (restaurados tal cual estaban antes del commit `3ff1ce5`); `db/agrequima_schema_sql_server.sql` vuelve a la definición original de las dos tablas (id autonumérico, `UsuarioId`, `NVARCHAR(50)/(200)`).
- En la base de desarrollo y en `Agrequima_Test` las dos tablas volvieron a su estructura y datos originales **desde los `*_respaldo` que había dejado la migración**, y esos respaldos dejaron de existir al renombrarse de vuelta. Desarrollo: antes tabla nueva 210/480 filas (idéntica a su respaldo), después 210 y 480 con id autonumérico, `UsuarioId`, PK y sin `*_respaldo`. `Agrequima_Test`: 5 y 2 filas (datos de las pruebas).

**`sync_financiero.py`:** ahora conoce solo las 8 vistas de CONTACC, **fijas en el código** (ya no depende de ninguna variable para excluir las otras dos). Se quitó la conexión a la base Agrequima del cliente, las variables `SYNC_AGREQUIMA_*` (del código, de `.env.ejemplo` y de la guía) y `SYNC_FINANCIERO_OMITIR`, que solo existía para este caso. `probar_conexion_origen.ps1` prueba solo CONTACC. `LEEME_SYNC.txt` reescrita: 8 vistas, `SaldoBancario`/`OtroIngreso` solo por Excel, y como el código de la web no cambia **ya no hace falta reiniciar el servicio**. `LEEME.txt` al día.

**Verificación local** (clon de la base de desarrollo anterior a todos los cambios como "PIQ_IA" + una base que simula solo CONTACC con los CSV; ambas borradas al terminar; el `.env` de prueba tenía únicamente variables de CONTACC):
- Pantallas que leen `SaldoBancario`/`OtroIngreso` (Conciliación bancaria, Flujo de caja, Otros ingresos): 102 respuestas de la API (14 endpoints × 9 períodos) antes y después de revertir las tablas: **0 valores distintos**; ningún cambio en esas tres pantallas.
- Carga por Excel en la base de desarrollo (archivos de ejemplo, año 2099): ambas pantallas responden 200, escriben `Concepto/Anio/Mes/Banco/Valor` (o `Tipo/Concepto/...`), `UsuarioId` del usuario que carga y `FechaMod`; recargar el mismo período reemplaza sin duplicar; los 210 y 480 registros reales no se tocaron; filas de prueba, auditorías y usuario temporal borrados, y las tablas `stg_` reconstruidas desde los CSV.
- Flujo completo con los archivos del paquete: 17 (2 corridas, idempotente: crea 8 tablas y 6 índices solo la primera vez) → primera carga con `correr_sync_financiero.ps1` (8 vistas OK, filas leídas = cargadas) → 18 (2 corridas). 8/8 copias idénticas al origen (campos, filas y `EXCEPT` en ambos sentidos = 0); 8/8 vistas idénticas a las tablas resumidas anteriores (filas, valores y tipos); `SaldoBancario`/`OtroIngreso` con el **mismo conteo, checksum y estructura** antes y después de 17 + sync + 18; cuadre de las 14 pantallas/endpoints que alimentan las 17 vistas del Financiero antes/después: 102 respuestas, 34.130 valores, **0 diferencias**.
- Fallas (7 escenarios, todos pasan): credenciales malas (las 8 conservan los datos de ayer); una vista inexistente en el origen (las otras 7 siguen); falla en pleno reemplazo (el `DELETE` se revierte); origen con 0 filas; corte real de la conexión de origen a mitad de la lectura sin reintento (conserva) y con reintento (se recupera); `SaldoBancario`/`OtroIngreso` intactas durante todas las corridas.
- Tests (108 backend), `tsc -b` y `npm run build` limpios.

**Defecto encontrado en el camino, sin relación con este cambio y NO corregido:** `dashboard_financiero.py` ordena las cuentas con `sorted(..., key=lambda c: -c.anio_actual)` (y variantes) sin criterio de desempate; las cuentas con el mismo importe (típicamente 0,00) salen en el orden en que SQL devolvió el `GROUP BY`, que no está garantizado y puede cambiar entre procesos (se observó una vez en Estados financieros, 2026-01: dos cuentas de Egresos con igual importe actual intercambiaron lugar, con los mismos valores). Arreglo posible: agregar el nombre de la cuenta como segundo criterio.

**Lo que NO se pudo probar acá:** el registro real de la tarea programada (requiere PowerShell de administrador) y la conexión real a `10.10.0.6,65280` desde el servidor.

## 26. Bancos e inversiones a plazo DINÁMICOS: dbo.CatalogoBancos (2026-10-06)

**Pedido (textual, resumido):** que si mañana aparece un banco nuevo salga solo en Conciliación bancaria y en Flujo de caja (saldos y cheques en circulación), "aunque sea sin color, y después yo le pongo el color", como hacía Deneb en Power BI; que las inversiones a plazo del Flujo de caja tampoco estén fijas; todo con una tabla nueva `CatalogoBancos`, sin nada estático, y que cuadre. Sin tocar Cuotas asociados, Plaguicidas/Nutrientes ni el diseño aprobado. Sin commit hasta aprobación.

**Qué se hizo**
1. `19_catalogo_bancos_financiero.sql` (nuevo, idempotente, BOM+CRLF; también agregado a `db/agrequima_schema_sql_server.sql`): `dbo.CatalogoBancos(ban_codigo, nombre_conciliacion, nombre_flujo, color_hex, orden, orden_flujo, activo, alias_saldo_bancario)`. Sembrada con los 4 bancos de hoy, sus nombres y colores (BAC `#E31B23`, BANRURAL `#009B4D`, BI `#004B87`, PROMÉRICA `#00A651`; en Flujo "Banrural", "Banco Industrial", "BAC Reformador", "Promerica"). **Columna extra `orden_flujo`** (no estaba en el pedido): el reporte original ordena distinto los bancos en cada pantalla (Conciliación BAC/BANRURAL/BI/PROMÉRICA; Flujo BANRURAL/BI/BAC/PROMÉRICA), y sin ella las pantallas no podían quedar idénticas a las de hoy; si es NULL se usa `orden`. La tilde de PROMÉRICA se arma con `NCHAR(201)` para que el script no dependa de la codificación del archivo.
2. `services/catalogo_bancos.py` (nuevo): normalización de códigos (mayúsculas, sin tildes, sin espacios ni caracteres invisibles: NBSP, CR/LF, tab, ancho cero...), lectura del catálogo y `ResolutorBancos` (alias del Excel de SaldoBancario, banco inactivo, color inválido -> gris, orden).
3. `services/dashboard_otros_informes.py`: **se eliminaron** `_ORDEN_BANCOS_CONCILIACION`, `_MAPA_BANCO_SALDO_BANCARIO` y `_ORDEN_BANCOS_FLUJO`. La lista de bancos es la unión de SaldosBancos + ChequesCirculacion + SaldoBancario (todos los períodos, como antes la lista fija salía siempre completa); los valores de cada fuente se unen por código normalizado (si dos filas del mismo banco caen en el mismo mes se SUMAN, antes la última pisaba a la anterior). Un banco fuera del catálogo sale igual: código como nombre, gris `#9E9E9E`, al final (alfabético). `activo = 0` oculta un banco en las dos pantallas y deja de sumar en los totales. Los totales de Flujo incluyen todos los bancos. Si la tabla `CatalogoBancos` no existe todavía (se publicó la app antes del SQL) la pantalla NO se rompe: se avisa en el log y todos los bancos salen en gris con su código.
4. Inversiones a plazo del Flujo: se quitaron las cuentas fijas `110103003`/`110103004` y las etiquetas fijas; se toman **todas** las cuentas de `BalanceGeneral` con `cod_n5` que empiece con `110103` (limpiando invisibles), ordenadas por cuenta, con la etiqueta derivada de `nom_n5` ("BAC - FONDO DE INVERSIÓN" -> "(+) Inversiones Plazo Fijo Bac": lo que va antes del primer " - ", sin tildes, capitalizado; así los textos de hoy no cambian). Una cuenta sin movimiento en el período se muestra en Q0 (como las dos de antes). El tipo de fila pasó de `INVERSION_BAC`/`INVERSION_PROMERICA` a `INVERSION` (frontend: `types/dashboardOtrosInformes.ts` y `DashboardOtrosInformesPage.tsx`, solo el nombre del tipo; sin cambios de diseño). Los totales se suman en el mismo orden que antes para que los centavos no cambien.
5. Pruebas nuevas: `tests/test_bancos_dinamicos.py` (16: 9 unitarias de normalización/ordenamiento/catálogo ausente/etiquetas + 4 de integración contra Agrequima_Test con banco nuevo en las 3 fuentes con NBSP/minúsculas, INSERT/UPDATE/`activo=0` en el catálogo y cuenta `110103999` nueva).

**Verificación local (base de desarrollo `Agrequima`, 2026-10-06)**
- Antes/después con los datos actuales: 69 respuestas de la API (Conciliación y Flujo en los 33 períodos + Otros ingresos 2025 y 2026 + la lista de períodos) **idénticas** (única diferencia aceptada: el texto del campo `tipo` de las 2 filas de inversión). Capturas A/B en `Desktop\capturas_bancos_dinamicos`.
- Datos inventados (`BANCO PRUEBA` en SaldosBancos, ChequesCirculacion con NBSP y SaldoBancario en minúsculas, y cuenta `110103005`): el banco aparece en gris al final en ambas pantallas, los totales lo incluyen (bancos 2.715.074,30 -> 2.716.374,30; cheques +250; inversiones 3.800.001 -> 4.500.001; total 6.515.075,30 -> 7.216.375,30). Con UN `INSERT` en CatalogoBancos (color `#7B1FA2`, orden 0) la franja pasa a morado y sube al primer lugar sin tocar código. Después se borró todo (incluida la fila de catálogo) y se restauraron los contadores de identidad: las tablas quedaron idénticas (filas y checksum).
- 124 pruebas backend (108 + 16), `tsc -b` y `npm run build` limpios.

**Para publicar:** respaldo de PIQ_IA, correr `19_catalogo_bancos_financiero.sql`, copiar `backend\app` y `frontend` (carpeta `Desktop\publicar_bancos_dinamicos`, con LEEME), `nssm restart PIQ_IA_App`.

**No se tocó (y por qué):** Cuotas asociados (pedido explícito), Otros ingresos (ya dinámico), colores/etiquetas de la gráfica de Flujo, la cuenta de caja `110101001`, las escalas fijas de los ejes. En el reporte de la sesión quedó la lista de lo que sigue fijo en el módulo (con archivo y línea, y si en el Power BI también era fijo) para que se decida caso por caso.

## 27. Ejes de gráficas calculados con los datos y degradado de color por banco (2026-10-06)

**Pedido (textual, resumido):** "las porquerías estáticas no las quiero... hasta la gráfica tiene un tope fijo, manual"; y, aprobado por el jefe, "un degradado del color principal sin colores secundarios". Se publica TODO junto (bancos dinámicos de la sección 26 + esto) en una sola publicación.

**Ejes (solo frontend, `utils/escalaEje.ts`):** se eliminaron todos los topes/marcas escritos a mano de las gráficas del Financiero: Flujo de caja (Q0-Q8,000,000), Ejecución gastos mensual (Q0-Q1,000,000), Presupuestos mensual/acumulado/comparativo (800,000 / 8,000,000 / 8,000,000), Ingresos por importación (precio 4-12, CIF 12M-34M, pasos de Q200,000 en Contribución), pasos de Q500,000 en los totales de Otros ingresos, y el tope de la gráfica de Cuotas (ahora considera también el cancelado). Regla: máximo = dato más alto + 8 %, redondeado hacia arriba a un paso limpio (1, 2, 2.5 o 5 × 10^k, entre 4 y 6 intervalos); con negativos el mínimo baja igual, sin negativos empieza en 0; se recalcula con cada año/mes/filtro. Los ejes automáticos de Recharts de Estados financieros y de la gráfica agrupada de Otros ingresos dejaron de recortar negativos. `calcularEscalaEjeY` (Ejecución gastos) ya era dinámica pero podía dejar el tope por debajo del dato (dato 1,050,000 -> tope 1,000,000): ahora sube un tramo. Con los datos actuales Ejecución gastos mensual/acumulado se ven igual (0/500k/1M y 0/5M/10M). Las gráficas de líneas de Importaciones que tenían tope fijo ahora empiezan en 0 por la regla. Probado: total de Flujo en Q7.2M y en Q10.2M (>Q8M) con la barra completa; las 69 respuestas de la API idénticas (los ejes son del frontend). No se tocaron los rankings horizontales (`domain [0, "dataMax"]`, ya dinámicos) ni las líneas del comparativo de Importaciones (ya dinámicas).

**Conciliación bancaria, diseño del encabezado de cada banco (solo frontend, `utils/colorBanco.ts` + `BloqueBanco`):** encabezado con degradado horizontal del color único del banco (a la izquierda `color_hex` tal cual, a la derecha 70 % color + 30 % blanco), nombre en blanco y negrita, borde izquierdo de 5 px del mismo color en toda la tarjeta; las filas (incluida Totales) quedan en el gris/superficie del tema; el encabezado verde general no se toca. Un banco sin color en el catálogo usa el gris `#9E9E9E` con la misma regla. Sin columnas nuevas: el degradado se calcula en el navegador. Verificado en modo claro y oscuro (agosto 2026) y con un banco inventado sin catálogo (gris con degradado, al final).

**Colores oficiales en `CatalogoBancos` (script 19 y esquema):** BAC `#E4002B`, BANRURAL `#365E3E`, BI `#003865`, PROMÉRICA `#00693C` (antes `#E31B23`, `#009B4D`, `#004B87`, `#00A651`). En desarrollo se actualizaron con un UPDATE. El script sigue siendo idempotente (la tabla y cada fila sembrada solo se crean si no existen). Efecto en la API: cambia únicamente el campo `color` de los 4 bancos en las 33 respuestas de Conciliación (una por período); las otras 36 respuestas quedan idénticas. **Aclaración:** la gráfica de Flujo de caja NO usa los colores de los bancos (sus 3 barras son colores fijos propios, `#4DB6AC`, `#90A4AE`, `#2C786C`), así que Flujo no cambia de aspecto.

**Verificación:** 124 pruebas backend, `tsc -b` y `npm run build` limpios; base de desarrollo idéntica salvo los 4 colores nuevos (el banco de prueba se borró).
