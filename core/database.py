"""Conexión a la base de datos (SQLAlchemy).

Producción define `DATABASE_URL`; en local se arma desde `DB_USER`, `DB_PASS`, `DB_HOST`,
`DB_PORT` y `DB_NAME` (ver `.env.example`).
"""
import os
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.exc import ArgumentError, NoSuchModuleError
from sqlalchemy.orm import declarative_base, sessionmaker

from core.errores import ErrorDeConfiguracion

RAIZ_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(RAIZ_PROYECTO, ".env"))


def _limpiar_valor(valor: str | None) -> str:
    """Quita espacios, saltos de línea y comillas que sobran al pegar un valor en un panel de variables."""
    texto = (valor or "").strip().strip("\"'").strip()
    return texto.split("=", 1)[1].strip().strip("\"'") if texto.upper().startswith("DATABASE_URL=") else texto


def _entero(valor: str | None, predeterminado: int, nombre: str) -> int:
    texto = _limpiar_valor(valor)
    if not texto:
        return predeterminado
    try:
        return int(texto)
    except ValueError:
        raise ErrorDeConfiguracion(f"La variable {nombre} debe ser un número entero.") from None


def _url_base_de_datos() -> str | URL:
    url = _limpiar_valor(os.getenv("DATABASE_URL"))
    if url:
        # Render y Heroku entregan "postgres://", que SQLAlchemy 2 ya no acepta.
        return "postgresql://" + url[len("postgres://"):] if url.startswith("postgres://") else url
    # URL.create escapa la contraseña: caracteres como "@" o "/" no rompen la conexión.
    return URL.create(
        "postgresql",
        username=_limpiar_valor(os.getenv("DB_USER")) or "postgres",
        password=os.getenv("DB_PASS") or None,
        host=_limpiar_valor(os.getenv("DB_HOST")) or "localhost",
        port=_entero(os.getenv("DB_PORT"), 5432, "DB_PORT"),
        database=_limpiar_valor(os.getenv("DB_NAME")) or "informes_db",
    )


def origen_conexion() -> str:
    """De dónde sale la configuración: `DATABASE_URL` o las variables sueltas `DB_*`."""
    return "DATABASE_URL" if _limpiar_valor(os.getenv("DATABASE_URL")) else "DB_*"


def describir_destino() -> str:
    """Destino de la conexión sin usuario ni contraseña (para el registro del servidor)."""
    url = engine.url
    return f"origen={origen_conexion()} host={url.host} puerto={url.port} base={url.database}"


try:
    DATABASE_URL = _url_base_de_datos()
    _es_sqlite = str(DATABASE_URL).startswith("sqlite")
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=1800,
        # Con timeout, un servidor caído o inexistente falla en segundos en vez de dejar la app colgada.
        **({"connect_args": {"check_same_thread": False}} if _es_sqlite
           else {"pool_size": 10, "max_overflow": 10, "pool_timeout": 30, "connect_args": {"connect_timeout": 10}}),
    )
except (ArgumentError, NoSuchModuleError, ValueError) as exc:
    raise ErrorDeConfiguracion(
        "La variable DATABASE_URL no tiene un formato válido. Debe verse como "
        "postgresql://usuario:contraseña@servidor:5432/base (cópiala de nuevo desde el panel de tu base de datos)."
    ) from exc

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

