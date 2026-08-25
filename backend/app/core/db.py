from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import DB_NAME, DB_PASSWORD, DB_SERVER, DB_USER, ODBC_DRIVER

CONN_STR = (
    f"mssql+pyodbc://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_SERVER}/{DB_NAME}"
    f"?driver={ODBC_DRIVER.replace(' ', '+')}"
)

engine = create_engine(CONN_STR, fast_executemany=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
