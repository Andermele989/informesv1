"""El arranque debe funcionar sobre bases creadas por versiones antiguas, sin perder datos."""
import logging

import pytest
from sqlalchemy import inspect, text

from core import models
from core.arranque import preparar
from core.database import Base, engine, sesion

_ANTIGUA = """
CREATE TABLE users (id INTEGER PRIMARY KEY, username VARCHAR NOT NULL, password_hash VARCHAR NOT NULL, role VARCHAR);
CREATE TABLE groups (id INTEGER PRIMARY KEY, name VARCHAR NOT NULL);
CREATE TABLE privileges (id INTEGER PRIMARY KEY, name VARCHAR NOT NULL);
CREATE TABLE publishers (id INTEGER PRIMARY KEY, name VARCHAR NOT NULL, is_inactive BOOLEAN);
CREATE TABLE monthly_reports (id INTEGER PRIMARY KEY, user_id INTEGER, month VARCHAR, assigned_privileges VARCHAR,
                              service_report VARCHAR, bible_courses INTEGER);
INSERT INTO users (username, password_hash, role) VALUES
  ('admin', 'clave-antigua', 'admin'), ('Maria', 'x', NULL), ('ADMINISTRADOR', 'x', 'Admin');
INSERT INTO publishers (name, is_inactive) VALUES ('Ana', NULL), ('Beto', 0);
INSERT INTO monthly_reports (user_id, month, service_report, bible_courses) VALUES
  (1, '2026-01', '50 horas', 1), (1, '2026-01', 'Sí participé', NULL);
"""


@pytest.fixture()
def base_antigua():
    """Esquema y datos como los dejaban las versiones anteriores (sin columnas nuevas, con vacíos)."""
    Base.metadata.drop_all(bind=engine)
    with engine.begin() as conn:
        for tabla in ("monthly_reports", "publishers", "privileges", "groups", "users"):
            conn.execute(text(f"DROP TABLE IF EXISTS {tabla}"))
        for sentencia in filter(str.strip, _ANTIGUA.split(";\n")):
            conn.execute(text(sentencia))
    yield
    Base.metadata.drop_all(bind=engine)


def test_arranca_sobre_una_base_antigua_y_la_actualiza(base_antigua, caplog):
    caplog.set_level(logging.WARNING, logger="informes.arranque")
    preparar()
    preparar()  # idempotente: la segunda vez no hace nada ni falla

    columnas = {t: {c["name"] for c in inspect(engine).get_columns(t)} for t in ("users", "publishers", "monthly_reports")}
    assert "is_inactive" in columnas["users"] and {"group_id"} <= columnas["publishers"]
    assert {"publisher_id", "full_name", "notes"} <= columnas["monthly_reports"]
    assert "login_attempts" in inspect(engine).get_table_names()
    assert "se añadió la columna" in caplog.text


def test_repara_vacios_sin_borrar_datos(base_antigua):
    preparar()
    with sesion() as db:
        assert db.query(models.MonthlyReport).count() == 2           # no se perdió ningún informe
        assert {u.username: u.role for u in db.query(models.User)} == {"admin": "admin", "Maria": "user", "ADMINISTRADOR": "admin"}
        assert all(u.is_inactive is False for u in db.query(models.User))
        assert all(p.is_inactive is False for p in db.query(models.Publisher))   # los vacíos pasan a activos
        assert all(r.bible_courses is not None for r in db.query(models.MonthlyReport))


def test_vincula_informes_antiguos_por_nombre_sin_crear_duplicados(base_antigua):
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE monthly_reports ADD COLUMN full_name VARCHAR"))
        conn.execute(text("ALTER TABLE monthly_reports ADD COLUMN publisher_id INTEGER"))
        conn.execute(text("UPDATE monthly_reports SET full_name = 'Ana' WHERE id = 1"))
        conn.execute(text("UPDATE monthly_reports SET full_name = 'Ana' WHERE id = 2"))   # mismo publicador y mismo mes
        conn.execute(text("INSERT INTO monthly_reports (user_id, month, full_name) VALUES (1, '2026-02', 'Persona Desconocida')"))
    preparar()
    with sesion() as db:
        por_id = {r.id: r for r in db.query(models.MonthlyReport)}
        assert por_id[1].publisher_id is None
        assert por_id[2].publisher_id is None          # dos informes de Ana en 2026-01: ninguno se vincula (sería un duplicado)
        assert por_id[3].publisher_id is None          # nombre sin publicador: se conserva el informe


def test_vincula_un_informe_antiguo_cuando_el_nombre_coincide_y_es_unico(base_antigua):
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE monthly_reports ADD COLUMN full_name VARCHAR"))
        conn.execute(text("ALTER TABLE monthly_reports ADD COLUMN publisher_id INTEGER"))
        conn.execute(text("UPDATE monthly_reports SET full_name = 'Beto' WHERE id = 1"))
    preparar()
    with sesion() as db:
        beto = db.query(models.Publisher).filter_by(name="Beto").one()
        assert db.get(models.MonthlyReport, 1).publisher_id == beto.id


def test_datos_que_impiden_una_restriccion_solo_generan_advertencia(base_antigua, caplog):
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO users (username, password_hash, role) VALUES ('Admin', 'y', 'user')"))  # choca con 'admin'
    caplog.set_level(logging.WARNING, logger="informes.arranque")
    preparar()                                          # no lanza excepción
    assert "usuarios únicos sin distinguir mayúsculas" in caplog.text
    with sesion() as db:
        assert db.query(models.User).count() == 4       # no se borró nada


def test_no_crea_otro_admin_si_ya_existe_con_otro_nombre_de_caja(base_antigua):
    preparar()
    with sesion() as db:
        assert sum(u.username.lower() == "admin" for u in db.query(models.User)) == 1
