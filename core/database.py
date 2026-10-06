"""Conexión a la base de datos (SQLAlchemy).

Producción define `DATABASE_URL`; en local se arma desde `DB_USER`, `DB_PASS`, `DB_HOST`,
`DB_PORT` y `DB_NAME` (ver `.env.example`).
"""
import os
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import declarative_base, sessionmaker

RAIZ_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(RAIZ_PROYECTO, ".env"))


def _url_base_de_datos() -> str | URL:
    url = os.getenv("DATABASE_URL")
    if url:
        # Render y Heroku entregan "postgres://", que SQLAlchemy 2 ya no acepta.
        return "postgresql://" + url[len("postgres://"):] if url.startswith("postgres://") else url
    # URL.create escapa la contraseña: caracteres como "@" o "/" no rompen la conexión.
    return URL.create(
        "postgresql",
        username=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASS") or None,
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "informes_db"),
    )


DATABASE_URL = _url_base_de_datos()
_es_sqlite = str(DATABASE_URL).startswith("sqlite")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=1800,
    **({"connect_args": {"check_same_thread": False}} if _es_sqlite else {"pool_size": 10, "max_overflow": 10, "pool_timeout": 30}),
)

SessionLocal = sessionmaker(autoflush=False, expire_on_commit=False, bind=engine)
Base = declarative_base()


@contextmanager
def sesion():
    """Sesión de base de datos que siempre se cierra (y revierte si hubo un error)."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
