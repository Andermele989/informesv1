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
    "CREATE INDEX IF NOT EXISTS ix_publishers_group_id ON publishers (group_id)",
    "CREATE INDEX IF NOT EXISTS ix_publishers_is_inactive ON publishers (is_inactive)",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_report_publisher_month ON monthly_reports (publisher_id, month)",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_users_username_lower ON users (lower(username))",
)

_RESTRICCIONES_POSTGRES = (
    "ALTER TABLE monthly_reports ALTER COLUMN publisher_id SET NOT NULL",
    "ALTER TABLE monthly_reports ALTER COLUMN user_id SET NOT NULL",
    "ALTER TABLE monthly_reports ALTER COLUMN month SET NOT NULL",
    "ALTER TABLE monthly_reports ALTER COLUMN bible_courses SET NOT NULL",
    """DO $$ BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_monthly_reports_bible_courses_nonnegative') THEN
            ALTER TABLE monthly_reports ADD CONSTRAINT ck_monthly_reports_bible_courses_nonnegative CHECK (bible_courses >= 0);
        END IF;
    END $$""",
    """DO $$ BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_users_role') THEN
            ALTER TABLE users ADD CONSTRAINT ck_users_role CHECK (role IN ('admin', 'user'));
        END IF;
    END $$""",
)


def _validar_integridad_previa() -> None:
    """Evita aplicar restricciones sobre datos inconsistentes sin borrar ni alterar información."""
    with engine.connect() as conn:
        duplicados_informes = conn.execute(text("""
            SELECT publisher_id, month
            FROM monthly_reports
            GROUP BY publisher_id, month
            HAVING COUNT(*) > 1
            LIMIT 1
        """)).first()
        if duplicados_informes:
            raise RuntimeError(
                "Hay informes duplicados para el mismo publicador y mes. "
                "Corrígelos antes de iniciar la aplicación."
            )
        duplicados_usuarios = conn.execute(text("""
            SELECT lower(username)
            FROM users
            GROUP BY lower(username)
            HAVING COUNT(*) > 1
            LIMIT 1
        """)).first()
        if duplicados_usuarios:
            raise RuntimeError(
                "Hay usuarios duplicados que solo difieren por mayúsculas/minúsculas. "
                "Corrígelos antes de iniciar la aplicación."
            )
        informes_incompletos = conn.execute(text("""
            SELECT COUNT(*) FROM monthly_reports
            WHERE publisher_id IS NULL OR user_id IS NULL OR month IS NULL OR bible_courses IS NULL
        """)).scalar_one()
        if informes_incompletos:
            raise RuntimeError(
                "Hay informes sin publicador, usuario, mes o cursos bíblicos. Corrígelos antes de iniciar la aplicación."
            )
        cursos_invalidos = conn.execute(text("""
            SELECT COUNT(*) FROM monthly_reports WHERE bible_courses < 0
        """)).scalar_one()
        if cursos_invalidos:
            raise RuntimeError("Hay informes con cursos bíblicos negativos. Corrígelos antes de iniciar la aplicación.")
        roles_invalidos = conn.execute(text("""
            SELECT COUNT(*) FROM users WHERE role IS NULL OR role NOT IN ('admin', 'user')
        """)).scalar_one()
        if roles_invalidos:
            raise RuntimeError("Hay usuarios con un rol inválido. Corrígelos antes de iniciar la aplicación.")


def _migrar() -> None:
    _validar_integridad_previa()
    for sentencia in _MIGRACIONES:
        try:
            with engine.begin() as conn:
                conn.execute(text(sentencia))
        except Exception as exc:
            raise RuntimeError(f"No se pudo aplicar una migración crítica: {sentencia}") from exc
    if engine.dialect.name == "postgresql":
        for sentencia in _RESTRICCIONES_POSTGRES:
            try:
                with engine.begin() as conn:
                    conn.execute(text(sentencia))
            except Exception as exc:
                raise RuntimeError("No se pudo reforzar la integridad de la base de datos existente.") from exc


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
