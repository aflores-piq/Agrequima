from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import (
    DB_MAX_OVERFLOW,
    DB_NAME,
    DB_PASSWORD,
    DB_POOL_SIZE,
    DB_SERVER,
    DB_USER,
    ODBC_DRIVER,
)

CONN_STR = (
    f"mssql+pyodbc://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_SERVER}/{DB_NAME}"
    f"?driver={ODBC_DRIVER.replace(' ', '+')}"
)

engine = create_engine(
    CONN_STR,
    fast_executemany=True,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
