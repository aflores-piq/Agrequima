# Agrequima — Sistema de Importaciones (Plaguicidas y Nutrientes)

Aplicación web que reemplaza el proceso manual de carga de importaciones de
plaguicidas (`Carga_Importaciones.py`) y agrega el proceso equivalente para
nutrientes, con dos dashboards de consulta (estilo Power BI) y un área de
administración para cargas, catálogos de agrupación, excepciones y usuarios.

Diseño completo, arquitectura y plan de fases en
[`docs/legacy/Instrucciones_claude_code_agrequima.MD`](docs/legacy/Instrucciones_claude_code_agrequima.MD).

## Estructura del repositorio

- `db/` — script de creación de la base de datos SQL Server `Agrequima`
  (tablas, catálogos, staging y procedimientos almacenados).
- `backend/` — API en FastAPI (Python) con SQLAlchemy + pyodbc, autenticación
  JWT por roles (`Administrador` / `Usuario`) y los procesos ETL de carga.
- `frontend/` — aplicación React + Vite + TypeScript con las pantallas de
  administración y los dos dashboards de consulta.

## Requisitos

- SQL Server accesible (desarrollo: `DESARROLLO-2`, login `sa`) con el
  driver **ODBC Driver 17 for SQL Server** instalado.
- Python 3.12+ y Node.js 20+.
- Un archivo `.env` en la raíz del repo (no versionado) con las variables
  de conexión y el secreto JWT — ver `.env.example` para la lista completa.

## Puesta en marcha (backend)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Crear el usuario administrador inicial

Después de aplicar `db/agrequima_schema_sql_server.sql` contra el SQL
Server de destino:

```bash
cd backend
python -m app.scripts.seed_admin
```

El script pide usuario y contraseña por consola y guarda la contraseña ya
hasheada con bcrypt en `dbo.Usuarios`, con rol `Administrador`.

## Puesta en marcha (frontend)

```bash
cd frontend
npm install
npm run dev
```

Requiere `frontend/.env` con `VITE_API_URL` apuntando al backend (ver
`frontend/.env.example`). Stack: React + Vite + TypeScript, Tailwind CSS,
Tremor (`@tremor/react`) para los componentes de dashboard, y Recharts
directo solo para los rankings con escala de intensidad (caso no cubierto
por el wrapper de Tremor).

## Pruebas de integración

Las pruebas corren contra una base de datos separada, **`Agrequima_Test`**
(mismo esquema que `Agrequima`), nunca contra la base real. Crearla una vez:

```bash
sed 's/Agrequima/Agrequima_Test/g' db/agrequima_schema_sql_server.sql > db/_schema_test_tmp.sql
sqlcmd -S DESARROLLO-2 -U sa -P sa2019 -C -i db/_schema_test_tmp.sql
rm db/_schema_test_tmp.sql
```

Luego, desde `backend/`:

```bash
pip install -r requirements-dev.txt
pytest
```

Cubren: login (éxito, contraseña incorrecta, usuario inactivo/inexistente),
ambos endpoints de carga (caso feliz con cruce real de catálogo, rol no
autorizado, extensión inválida, archivo con formato inesperado — y que
quede registrado en `AuditoriaCargas` con `Estado='Error'`), y ambos
endpoints de dashboard (incluyendo que los totales de las tarjetas KPI
coincidan exactamente con `SUM(...)`/`COUNT(...)` calculado directo en la
base de datos).

## Estado del proyecto

En construcción, siguiendo el plan de fases de la sección 8 de
`docs/legacy/Instrucciones_claude_code_agrequima.MD`:

- [x] Fase 0 — Base de datos y usuario administrador inicial
- [x] Fase 1 — Backend base (FastAPI + JWT)
- [x] Fase 2 — ETL de plaguicidas como endpoint
- [x] Fase 3 — ETL de nutrientes
- [x] Fase 4 — Endpoints de dashboard
- [x] Fase 4.5 — Endpoints de nomenclatura/agrupadores, excepciones, usuarios e historial de cargas (necesarios para la Fase 5, no estaban en el plan original de 6 fases)
- [x] Fase 5 — Frontend (React + Vite + TS, Tailwind + Tremor, dos áreas `/admin` y `/app` protegidas por rol)
- [x] Fase 6 — Pruebas y pulido (17 pruebas de integración con pytest + logging de aplicación en los ETL)
- [x] `POST /admin/cargas/plaguicidas` acepta también `.csv` con las mismas columnas y orden que el `.xlsx` (fecha `DD/MM/YYYY` y montos con símbolo de moneda, como llega el archivo real de ejemplo)
