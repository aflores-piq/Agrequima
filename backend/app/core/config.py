import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[3]
load_dotenv(ROOT_DIR / ".env")

DB_SERVER = os.getenv("DB_SERVER")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
ODBC_DRIVER = os.getenv("ODBC_DRIVER", "ODBC Driver 17 for SQL Server")

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

# Orígenes permitidos por CORS (separados por coma). Antes estaba
# hardcodeado a "http://localhost:5173" en main.py -- eso bloqueaba
# cualquier dominio real de producción sin tocar código. El default
# preserva el comportamiento de desarrollo si la variable no está.
CORS_ORIGINS = [
    origen.strip()
    for origen in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origen.strip()
]

# Carpeta con el frontend YA COMPILADO (el resultado de "npm run build":
# index.html + assets/) que main.py sirve en "/". Default pensado para
# desarrollo local: apunta a donde quedaría frontend/dist si alguien
# corriera el build acá, pero en dev normalmente no existe (se usa el
# servidor de Vite aparte) -- main.py revisa si la carpeta existe antes
# de montarla, así que este default no rompe nada si no está.
FRONTEND_DIST_PATH = os.getenv("FRONTEND_DIST_PATH", str(ROOT_DIR / "frontend" / "dist"))

# Tamaño del pool de conexiones a la base de datos. Antes no se pasaban
# estos parámetros a create_engine(), así que quedaban en el default de
# SQLAlchemy (pool_size=5, max_overflow=10 -- 15 conexiones simultáneas
# como techo real). Con ~50 empresas usando la app a la vez, eso se
# queda corto. El default acá ya sube ese techo a 50 (20+30) para que
# alcance de entrada; en desarrollo no cambia nada en la práctica --
# nunca se usan más de un puñado de conexiones a la vez, así que un
# techo más alto no tiene ningún efecto visible, solo más margen.
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "20"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "30"))
