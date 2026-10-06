"""Preparación de la base de datos al iniciar la app: tablas, migraciones y cuenta admin."""
import logging
import os

import streamlit as st
from sqlalchemy import text

from core import models
from core.database import Base, engine, sesion
from core.security import generar_password, hash_password

log = logging.getLogger("informes.arranque")

# `create_all` no modifica tablas que ya existen; estos pasos son idempotentes y
# ponen al día las bases creadas con versiones anteriores.
_MIGRACIONES = (
    "CREATE INDEX IF NOT EXISTS ix_monthly_reports_publisher_id ON monthly_reports (publisher_id)",
    "CREATE INDEX IF NOT EXISTS ix_monthly_reports_user_id ON monthly_reports (user_id)",
    "CREATE INDEX IF NOT EXISTS ix_monthly_reports_user_id ON monthly_reports (user_id)",
    "CREATE INDEX IF NOT EXISTS ix_publishers_group_id ON publishers (group_id)",
    "CREATE INDEX IF NOT EXISTS ix_publishers_is_inactive ON publishers (is_inactive)",
    "CREATE INDEX IF NOT EXISTS ix_publishers_is_inactive ON publishers (is_inactive)",
    # Falla (y se registra) si ya hay informes duplicados; en ese caso corrígelos y reinicia.
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_report_publisher_month ON monthly_reports (publisher_id, month)",
)


def _migrar() -> None:
    for sentencia in _MIGRACIONES:
        try:
            with engine.begin() as conn:
                conn.execute(text(sentencia))
        except Exception as exc:
            log.warning("Migración omitida (%s): %s", sentencia.split(" ON ")[0], exc)


def _crear_admin_si_falta() -> None:
    """Crea `admin` en la primera ejecución con `ADMIN_INITIAL_PASSWORD` o una clave aleatoria."""
    with sesion() as db:
        if db.query(models.User).filter(models.User.username == "admin").first():
            return
        password = os.getenv("ADMIN_INITIAL_PASSWORD") or generar_password(16)
        db.add(models.User(username="admin", password_hash=hash_password(password), role="admin"))
        db.commit()
        if not os.getenv("ADMIN_INITIAL_PASSWORD"):
            # Se muestra una sola vez en la consola del servidor; no se guarda en ningún archivo.
            log.warning("Usuario 'admin' creado. Contraseña inicial (cámbiala al entrar): %s", password)


def preparar() -> None:
    """Crea tablas, aplica migraciones y crea `admin` si falta. También la usan los scripts."""
    Base.metadata.create_all(bind=engine)
    _migrar()
    _crear_admin_si_falta()


@st.cache_resource(show_spinner=False)
def preparar_base_de_datos() -> bool:
    """`preparar()` una vez por proceso. Si falla no se cachea y se reintenta en la siguiente carga."""
    preparar()
    return True
