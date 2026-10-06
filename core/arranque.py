"""Preparación de la base de datos al iniciar la app.

Regla de oro: **arrancar siempre que la base sea utilizable**. Las bases creadas con versiones antiguas
(a base de scripts ALTER sueltos) se ponen al día solas y de forma segura. Lo que no se pueda arreglar sin
adivinar se deja como está y se registra una advertencia; nunca impide el arranque.
`python -m scripts.audit` lista esos puntos pendientes.

Orden: tablas nuevas -> columnas que faltan -> reparación de datos -> índices y restricciones -> usuario admin.
Solo el fallo de conexión o de crear las tablas detiene la app.
"""
import logging
import os

import streamlit as st
from sqlalchemy import func, inspect, text

from core import models
from core.database import Base, engine, sesion
from core.security import generar_password, hash_password

log = logging.getLogger("informes.arranque")
_POSTGRES = engine.dialect.name == "postgresql"

# Reparaciones seguras e idempotentes: solo rellenan vacíos con el valor que el modelo ya consideraba normal.
_REPARACIONES = (
    ("usuarios sin estado -> activos", "UPDATE users SET is_inactive = FALSE WHERE is_inactive IS NULL"),
    ("publicadores sin estado -> activos", "UPDATE publishers SET is_inactive = FALSE WHERE is_inactive IS NULL"),
    ("usuarios sin rol -> 'user' (el de menor privilegio)",
     "UPDATE users SET role = 'user' WHERE role IS NULL OR trim(role) = ''"),
    ("roles con mayúsculas -> minúsculas",
     "UPDATE users SET role = lower(trim(role)) WHERE lower(trim(role)) IN ('admin', 'user') AND role <> lower(trim(role))"),
    ("informes sin cursos bíblicos -> 0", "UPDATE monthly_reports SET bible_courses = 0 WHERE bible_courses IS NULL"),
    # Los informes antiguos guardan el nombre en full_name pero no el publicador. Se vinculan solo si el nombre
    # coincide exactamente con un publicador y no crea un duplicado (publicador + mes).
    ("informes sin publicador -> vinculados por nombre",
     """UPDATE monthly_reports
        SET publisher_id = (SELECT p.id FROM publishers p WHERE p.name = monthly_reports.full_name)
        WHERE publisher_id IS NULL
          AND full_name IN (SELECT name FROM publishers)
          AND NOT EXISTS (SELECT 1 FROM monthly_reports x JOIN publishers q ON q.id = x.publisher_id
                          WHERE q.name = monthly_reports.full_name AND x.month = monthly_reports.month)
          AND (SELECT COUNT(*) FROM monthly_reports y
               WHERE y.publisher_id IS NULL AND y.full_name = monthly_reports.full_name AND y.month = monthly_reports.month) = 1"""),
)

_NO_NULO = "ALTER TABLE {t} ALTER COLUMN {c} SET NOT NULL"
_CHECK = """DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = '{nombre}') THEN
        ALTER TABLE {tabla} ADD CONSTRAINT {nombre} CHECK ({condicion});
    END IF;
END $$"""

# (descripción, sentencia, consulta de filas que lo impiden o None, solo PostgreSQL)
_RESTRICCIONES = (
    ("índice de informes por publicador",
     "CREATE INDEX IF NOT EXISTS ix_monthly_reports_publisher_id ON monthly_reports (publisher_id)", None, False),
    ("índice de informes por usuario",
     "CREATE INDEX IF NOT EXISTS ix_monthly_reports_user_id ON monthly_reports (user_id)", None, False),
    ("índice de publicadores por grupo",
     "CREATE INDEX IF NOT EXISTS ix_publishers_group_id ON publishers (group_id)", None, False),
    ("índice de publicadores por estado",
     "CREATE INDEX IF NOT EXISTS ix_publishers_is_inactive ON publishers (is_inactive)", None, False),
    ("un solo informe por publicador y mes",
     "CREATE UNIQUE INDEX IF NOT EXISTS uq_report_publisher_month ON monthly_reports (publisher_id, month)",
     "SELECT COUNT(*) FROM (SELECT 1 FROM monthly_reports WHERE publisher_id IS NOT NULL "
     "GROUP BY publisher_id, month HAVING COUNT(*) > 1) t", False),
    ("usuarios únicos sin distinguir mayúsculas",
     "CREATE UNIQUE INDEX IF NOT EXISTS uq_users_username_lower ON users (lower(username))",
     "SELECT COUNT(*) FROM (SELECT 1 FROM users GROUP BY lower(username) HAVING COUNT(*) > 1) t", False),
    ("informes con publicador obligatorio", _NO_NULO.format(t="monthly_reports", c="publisher_id"),
     "SELECT COUNT(*) FROM monthly_reports WHERE publisher_id IS NULL", True),
    ("informes con usuario obligatorio", _NO_NULO.format(t="monthly_reports", c="user_id"),
     "SELECT COUNT(*) FROM monthly_reports WHERE user_id IS NULL", True),
    ("informes con mes obligatorio", _NO_NULO.format(t="monthly_reports", c="month"),
     "SELECT COUNT(*) FROM monthly_reports WHERE month IS NULL", True),
    ("informes con cursos obligatorios", _NO_NULO.format(t="monthly_reports", c="bible_courses"),
     "SELECT COUNT(*) FROM monthly_reports WHERE bible_courses IS NULL", True),
    ("usuarios con rol obligatorio", _NO_NULO.format(t="users", c="role"),
     "SELECT COUNT(*) FROM users WHERE role IS NULL", True),
    ("usuarios con estado obligatorio", _NO_NULO.format(t="users", c="is_inactive"),
     "SELECT COUNT(*) FROM users WHERE is_inactive IS NULL", True),
    ("publicadores con estado obligatorio", _NO_NULO.format(t="publishers", c="is_inactive"),
     "SELECT COUNT(*) FROM publishers WHERE is_inactive IS NULL", True),
    ("cursos bíblicos no negativos",
     _CHECK.format(nombre="ck_monthly_reports_bible_courses_nonnegative", tabla="monthly_reports", condicion="bible_courses >= 0"),
     "SELECT COUNT(*) FROM monthly_reports WHERE bible_courses < 0", True),
    ("rol de usuario válido",
     _CHECK.format(nombre="ck_users_role", tabla="users", condicion="role IN ('admin', 'user')"),
     "SELECT COUNT(*) FROM users WHERE role IS NOT NULL AND role NOT IN ('admin', 'user')", True),
)


def _ejecutar(sentencia: str) -> int:
    with engine.begin() as conn:
        return conn.execute(text(sentencia)).rowcount


def _contar(consulta: str) -> int:
    with engine.connect() as conn:
        return conn.execute(text(consulta)).scalar_one()


def _definicion_columna(col) -> str:
    """DDL de una columna que falta en una tabla existente (siempre admite nulos: ya hay filas)."""
    ddl = col.type.compile(dialect=engine.dialect)
    if col.type.python_type is bool:
        ddl += " DEFAULT FALSE"
    elif col.default is not None and getattr(col.default, "is_scalar", False) and isinstance(col.default.arg, int):
        ddl += f" DEFAULT {int(col.default.arg)}"
    for fk in col.foreign_keys:
        ddl += f' REFERENCES "{fk.column.table.name}" ("{fk.column.name}")'
    return ddl


def _completar_columnas() -> None:
    """Añade las columnas del modelo que no existan en bases antiguas."""
    inspector = inspect(engine)
    existentes = set(inspector.get_table_names())
    for tabla in Base.metadata.sorted_tables:
        if tabla.name not in existentes:
            continue
        presentes = {c["name"] for c in inspector.get_columns(tabla.name)}
        for col in tabla.columns:
            if col.name in presentes:
                continue
            try:
                _ejecutar(f'ALTER TABLE "{tabla.name}" ADD COLUMN "{col.name}" {_definicion_columna(col)}')
                log.warning("Base antigua: se añadió la columna %s.%s", tabla.name, col.name)
            except Exception as exc:
                log.warning("No se pudo añadir la columna %s.%s: %s", tabla.name, col.name, exc)


def _reparar_datos() -> None:
    for descripcion, sentencia in _REPARACIONES:
        try:
            filas = _ejecutar(sentencia)
        except Exception as exc:
            log.warning("No se pudo aplicar la reparación «%s»: %s", descripcion, exc)
            continue
        if filas and filas > 0:
            log.warning("Base antigua: %s fila(s) reparadas: %s", filas, descripcion)


def _aplicar_restricciones() -> None:
    for descripcion, sentencia, bloqueo, solo_postgres in _RESTRICCIONES:
        if solo_postgres and not _POSTGRES:
            continue
        try:
            if bloqueo and (impiden := _contar(bloqueo)):
                log.warning("Se omite «%s»: %s fila(s) lo impiden. Corrígelas; `python -m scripts.audit` da el detalle.",
                            descripcion, impiden)
                continue
            _ejecutar(sentencia)
        except Exception as exc:
            log.warning("Se omite «%s»: %s", descripcion, exc)


def _crear_admin_si_falta() -> None:
    """Crea `admin` en la primera ejecución con `ADMIN_INITIAL_PASSWORD` o una clave aleatoria."""
    with sesion() as db:
        # La unicidad ignora mayúsculas: no crear "admin" si ya existe p. ej. "Admin" en una base histórica.
        if db.query(models.User).filter(func.lower(models.User.username) == "admin").first():
            return
        password = os.getenv("ADMIN_INITIAL_PASSWORD") or generar_password(16)
        db.add(models.User(username="admin", password_hash=hash_password(password), role="admin"))
        db.commit()
        if not os.getenv("ADMIN_INITIAL_PASSWORD"):
            # Se muestra una sola vez en la consola del servidor; no se guarda en ningún archivo.
            log.warning("Usuario 'admin' creado. Contraseña inicial (cámbiala al entrar): %s", password)


def preparar() -> None:
    """Pone la base al día y crea `admin` si falta. También la usan los scripts."""
    Base.metadata.create_all(bind=engine)  # si esto falla (conexión, permisos), sí se detiene
    _completar_columnas()
    _reparar_datos()
    _aplicar_restricciones()
    _crear_admin_si_falta()


@st.cache_resource(show_spinner=False)
def preparar_base_de_datos() -> bool:
    """`preparar()` una vez por proceso. Si falla no se cachea y se reintenta en la siguiente carga."""
    preparar()
    return True
