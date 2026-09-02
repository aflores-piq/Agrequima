# Servidor de producción (VMI1979377)

Este documento describe el **estado actual** del servidor de producción,
para que cualquiera del equipo pueda darle mantenimiento sin tener que
reconstruir la historia de cómo se armó. No es una crónica de
decisiones (eso vive en otro lado) — si algo de lo que dice acá deja de
ser cierto, actualizá este documento, no agregues una segunda versión
"histórica" al lado.

## 1. Acceso e infraestructura

- **Servidor**: `VMI1979377`. Acceso remoto por RDP, usuario
  `VMI1979377\Administrator`.
- **Dominio público**: `agrequima-pronostiq.duckdns.org` (DuckDNS,
  cuenta `pronostiqgt@gmail.com`).
- **Certificado SSL**: Let's Encrypt, emitido y renovado vía win-acme.
  Vive en `C:\ssl\agrequima-pronostiq\`. La renovación automática ya
  está configurada como tarea programada de Windows (no requiere
  intervención manual).
- **Firewall de Windows**: regla de entrada, TCP 443, permitir, todos
  los perfiles de red.

## 2. Base de datos

- **Motor**: SQL Server, instancia `VMI1979377\SQLEXPRESS`.
- **Modo de autenticación**: mixto ("SQL Server and Windows
  Authentication") — se tuvo que cambiar a mano desde el modo original
  de solo autenticación de Windows, porque la app se conecta con
  usuario y contraseña de SQL Server (no hay soporte para Windows
  Authentication en el código, ver `backend/app/core/db.py`).
- **Base de la app**: `PIQ_IA`. Confirmado contra el `.env` de este
  servidor (`backend/deploy_servidor_real/.env.backend_servidor_real`,
  no versionado): `DB_SERVER=VMI1979377\SQLEXPRESS`,
  `DB_NAME=PIQ_IA`.
- **Usuario de conexión de la app**: `piq_app`. La contraseña vive
  únicamente en el `.env` del servidor, no en este repositorio.
  ⚠️ *Nota de verificación*: en la plantilla local
  `.env.backend_servidor_real`, los campos `DB_USER` y `DB_PASSWORD`
  todavía están sin completar (`[[COMPLETAR]]`) — eso es intencional
  (se llenan a mano directo en el servidor, nunca por git), pero
  significa que el nombre de usuario `piq_app` no se puede verificar
  contra el repo; queda documentado tal como me lo pasaste.
- **Pool de conexiones**: `DB_POOL_SIZE=20` / `DB_MAX_OVERFLOW=30`
  (30 conexiones simultáneas de margen sobre las 20 fijas). Son los
  valores por default en `backend/app/core/config.py` si no se
  sobrescriben por variable de entorno — el `.env` de este servidor no
  los redefine, así que hoy corre con estos defaults.
- **Límite de licencia a futuro**: SQL Server Express tiene tope de
  1 GB de buffer pool y 4 núcleos. Con las ~50 empresas usando el
  sistema, si aparece lentitud, la solución es migrar a SQL Server
  Standard (no es algo que se resuelva ajustando configuración).

## 3. Estructura de carpetas en el servidor

```
C:\Pronostiq\Agrequima-pronostiq\
├── backend\     -- código de la API + entorno virtual de Python
├── frontend\    -- build YA COMPILADO (salida de "npm run build"),
│                   no el código fuente del frontend
├── deploy\      -- scripts de deploy
├── .env         -- configuración con secretos (nunca en git)
├── nssm.exe
└── logs\
    ├── stdout.log
    └── stderr.log
```

## 4. Cómo corre la app

La app corre como **servicio de Windows** vía NSSM, con nombre de
servicio `PIQ_IA_App`. Ya no depende de ninguna ventana de comandos
abierta ni de una sesión de usuario iniciada — administrala con:

```
nssm start PIQ_IA_App
nssm stop PIQ_IA_App
nssm restart PIQ_IA_App
```

## 5. Rutas de la API y frontend

Todas las rutas de negocio del backend están bajo el prefijo `/api/`
(`/health` es la única excepción — endpoint de infraestructura, no de
negocio). Verificado contra `backend/app/main.py`: todos los routers
(`auth`, `admin_cargas`, `admin_nomenclatura`, `admin_usuarios`,
`dashboard`) se montan con `prefix="/api"`.

El frontend compilado se sirve directamente desde el mismo proceso de
FastAPI (no hay un servidor web aparte tipo IIS/nginx delante): una
ruta catch-all registrada *después* de todas las rutas de la API sirve
los archivos estáticos de `frontend/`, y cualquier ruta que no sea un
archivo real cae a `index.html` para que React Router resuelva las
rutas del lado del cliente (ej. `/admin/usuarios`) también al recargar
la página.

## 6. Modelo de roles y permisos

Verificado contra `backend/app/core/deps.py` y los routers de
`backend/app/routers/`.

| Rol | Quién lo usa | Acceso |
|---|---|---|
| **Administrador** | Uso interno de Pronostiq | Todo: Carga, Nomenclatura, Usuarios, Dashboards |
| **Administrador de Usuarios** | Personal de Agrequima | Administra cuentas (crear, cambiar contraseña, activar/desactivar) y ve ambos dashboards. **Sin acceso** a Carga ni Nomenclatura (esos endpoints exigen únicamente `Administrador`) |
| **Usuario** | Cada una de las ~50 empresas cliente | Solo ve dashboards |

Detalles importantes:

- Los endpoints de dashboard (`GET /api/dashboard/...`) no exigen un
  rol puntual, solo sesión válida — por eso cualquier rol autenticado
  los ve.
- Todas las empresas ("Usuario") ven el **mismo** conjunto completo de
  datos — no hay segregación de datos por empresa en el modelo actual.
- **Administrador de Usuarios** no puede ver ni tocar ninguna cuenta
  con rol `Administrador` o `Administrador de Usuarios` (ni listarlas,
  ni editarlas, ni cambiarles la contraseña, ni asignarles esos roles a
  otra cuenta) — corrección de seguridad para que no pueda escalar
  privilegios resetando la contraseña de una cuenta Administrador real.
- **"Puede exportar a Excel"** es un permiso individual por usuario
  (`dbo.Usuarios.PuedeExportar`), independiente del rol — un
  Administrador puede no tenerlo, y un Usuario puede tenerlo.
- Cualquier usuario autenticado puede cambiar su propia contraseña
  desde el menú de cuenta (`PATCH /api/auth/password`), sin depender de
  un administrador — pide la contraseña actual como confirmación.

## 7. Cómo se cargan los datos de negocio

**No hay sincronización automática con el servidor de Agrequima.** El
flujo real hoy es manual: Agrequima manda archivos Excel, y el
personal de Pronostiq los sube a mano, en producción, desde las
pantallas de Carga del panel de administración — directamente hacia
`PIQ_IA` (la base a la que apunta el sistema).

La carga inicial (el histórico ya correcto al momento del despliegue)
se hizo una sola vez con
[`backend/deploy_servidor_real/03_cargar_datos_iniciales.sql`](../backend/deploy_servidor_real/03_cargar_datos_iniciales.sql).

> El paquete de deploy también incluye un script de sincronización
> nocturna automática (`sync_piq_ia.py`, pensado para espejar datos
> desde el servidor de Agrequima hacia PIQ_IA vía VPN). **No es el
> mecanismo que se usa hoy** para los datos de negocio reales — la
> conectividad hacia el servidor de Agrequima todavía no estaba
> confirmada al armar ese script. Ver la sección 9.

## 8. Paquete de deploy (`backend/deploy_servidor_real/`)

Qué hace cada archivo que hay hoy en esa carpeta:

- **`01_crear_base_piq_ia.sql`** — crea la base `PIQ_IA` completa desde
  cero: las 13 tablas y los 4 stored procedures que necesita la app.
- **`02_seed_roles_y_admin.sql`** — crea los 3 roles del sistema
  (Administrador, Usuario, Administrador de Usuarios) y una cuenta
  administradora inicial de producción.
- **`03_cargar_datos_iniciales.sql`** — dump con los datos reales de
  Importacion/Nutrientes/catálogos, para la carga inicial única
  descrita en la sección 7.
- **`generar_datos_iniciales.py`** — herramienta permanente para
  regenerar el `.sql` anterior con datos más frescos, el día que haga
  falta reconstruir PIQ_IA desde cero con información actualizada.
- **`generar_hash_password.py`** — genera el hash bcrypt de una
  contraseña para pegar en `02_seed_roles_y_admin.sql`, sin que la
  contraseña real quede escrita en texto plano en ningún archivo.
- **`sync_piq_ia.py`** — script de sincronización nocturna (mirror de
  solo lectura) descrito en la sección 7; no está activo como
  mecanismo real de datos hoy.
- **`requirements.txt`** — dependencias de Python necesarias para
  correr `sync_piq_ia.py` de forma independiente, sin instalar todo el
  backend.
- **`.env.ejemplo`** — plantilla de configuración para
  `sync_piq_ia.py` (variables `SYNC_*`).
- **`.env.backend_servidor_real`** — plantilla (parcialmente
  completada) del `.env` real que usa la app en este servidor.
  **Nunca se sube a git** — ya trae valores reales (servidor, base de
  datos, `JWT_SECRET_KEY`) y por eso está excluido del repositorio a
  mano; los campos de usuario/contraseña de base de datos se completan
  directo en el servidor.
- **`LEEME.txt`** — guía paso a paso de instalación (la crónica de
  cómo instalar todo esto desde cero; no es el objeto de este
  documento).

## 9. Pendiente conocido (no resuelto)

Falta un mecanismo para que, además de cargarse en PIQ_IA vía las
pantallas de Carga, esos mismos datos actualicen también las tablas
del servidor de Agrequima — porque otros sistemas del cliente dependen
de que esos datos estén ahí. Hoy esa actualización no ocurre en
ningún sentido automático: los datos entran a PIQ_IA por carga manual
(sección 7), y no hay ningún camino de vuelta hacia el servidor de
Agrequima. Esto todavía no está construido.

## Cómo reiniciar la app

```
nssm restart PIQ_IA_App
```

(o `nssm stop PIQ_IA_App` seguido de `nssm start PIQ_IA_App` si se
necesita más control sobre cada paso).

## Cómo ver los logs si algo falla

```
C:\Pronostiq\Agrequima-pronostiq\logs\stdout.log
C:\Pronostiq\Agrequima-pronostiq\logs\stderr.log
```

`stderr.log` es el primer lugar para mirar ante un error o un reinicio
inesperado del servicio.
