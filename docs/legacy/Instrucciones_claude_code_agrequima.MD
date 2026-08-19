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

Finalmente, para el despliegue en DESARROLLO-2 conviene decidir si el backend corre como servicio de Windows (con NSSM o una tarea programada que mantenga `uvicorn` corriendo) o detrás de IIS con un proxy inverso, y si el frontend se sirve como build estático desde el propio FastAPI o desde IIS también — esto no bloquea el desarrollo, pero sí conviene resolverlo antes de poner la aplicación en manos de los usuarios finales.