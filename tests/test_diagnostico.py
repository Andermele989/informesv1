"""Diagnóstico de fallos de conexión y limpieza de la configuración que llega desde Render."""
import os
import subprocess
import sys

import pytest
from sqlalchemy.exc import OperationalError

from conftest import RAIZ
from core import arranque, database, diagnostico
from streamlit.testing.v1 import AppTest


def _falla(mensaje: str) -> OperationalError:
    return OperationalError("SELECT 1", {}, Exception(mensaje))


@pytest.fixture()
def con_database_url(monkeypatch):
    """Simula un servicio de Render con DATABASE_URL definida (la base de pruebas sigue siendo SQLite)."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@host/db")


@pytest.mark.parametrize("mensaje, palabra", [
    ('FATAL:  password authentication failed for user "x"', "contraseña"),
    ('FATAL:  la autentificación password falló para el usuario "x"', "contraseña"),
    ('FATAL:  database "informes" does not exist', "no existe"),
    ('could not translate host name "dpg-abc-a" to address: Name or service not known', "no se encuentra"),
    ("connection to server at \"h\" (1.2.3.4), port 5432 failed: SSL connection has been closed unexpectedly", "caducó"),
    ("connection to server failed: timeout expired", "no responde"),
    ('connection to server at "h", port 5999 failed: Connection refused', "rechazó"),
    ("FATAL: remaining connection slots are reserved for non-replication superuser connections", "límite de conexiones"),
    ('FATAL: no pg_hba.conf entry for host "1.2.3.4", SSL off', "sslmode=require"),
    ("algo totalmente desconocido", "registro del servidor"),
])
def test_pistas_por_tipo_de_fallo(con_database_url, mensaje, palabra):
    assert palabra in diagnostico.causa_de_conexion(_falla(mensaje))


def test_sin_database_url_avisa_que_se_usa_localhost(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(database.engine, "url", database.engine.url.set(host="localhost"))
    assert "DATABASE_URL no está definida" in diagnostico.causa_de_conexion(_falla("Connection refused"))


def test_error_de_decodificacion_de_postgres_en_windows(con_database_url):
    assert "UTF-8" in diagnostico.causa_de_conexion(UnicodeDecodeError("utf-8", b"\xf3", 0, 1, "invalid"))


def test_la_pista_nunca_incluye_host_usuario_ni_clave(con_database_url):
    pista = diagnostico.causa_de_conexion(_falla('FATAL: password authentication failed for user "secreto" at host "dpg-1.render.com"'))
    assert not any(dato in pista for dato in ("secreto", "dpg-1", "render.com"))


@pytest.mark.parametrize("pegado, esperado", [
    ("  postgresql://u:p@h/db  \n", "postgresql://u:p@h/db"),
    ('"postgresql://u:p@h/db"', "postgresql://u:p@h/db"),
    ("'postgres://u:p@h/db'", "postgresql://u:p@h/db"),
    ("DATABASE_URL=postgres://u:p@h/db", "postgresql://u:p@h/db"),
])
def test_limpia_la_url_pegada_en_el_panel(monkeypatch, pegado, esperado):
    monkeypatch.setenv("DATABASE_URL", pegado)
    assert database._url_base_de_datos() == esperado


def test_url_vacia_cuenta_como_no_definida(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "   ")
    assert database.origen_conexion() == "DB_*"


def test_puerto_vacio_o_invalido(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DB_PORT", "")
    assert database._url_base_de_datos().port == 5432
    monkeypatch.setenv("DB_PORT", "abc")
    with pytest.raises(database.ErrorDeConfiguracion, match="DB_PORT"):
        database._url_base_de_datos()


def test_url_con_formato_invalido_da_un_error_claro_sin_mostrar_la_url():
    entorno = {**os.environ, "DATABASE_URL": "esto-no-es-una-url-con-clave-secreta-123", "PYTHONPATH": RAIZ}
    r = subprocess.run([sys.executable, "-c", "import core.database"], env=entorno, cwd=RAIZ, capture_output=True, text=True)
    assert r.returncode != 0 and "ErrorDeConfiguracion" in r.stderr and "formato válido" in r.stderr
    assert "clave-secreta-123" not in r.stderr.split("ErrorDeConfiguracion")[-1]


def test_pantalla_de_conexion_fallida_muestra_la_causa_sin_datos_sensibles(con_database_url, monkeypatch):
    def sin_conexion():
        raise _falla('connection to server at "dpg-secreto.render.com", port 5432 failed: SSL connection has been closed unexpectedly')

    monkeypatch.setattr(arranque, "preparar_base_de_datos", sin_conexion)
    app = AppTest.from_file(os.path.join(RAIZ, "main.py"), default_timeout=60).run()
    assert not app.exception
    texto = " ".join([e.value for e in app.error] + [w.value for w in app.warning] + [c.value for c in app.caption])
    assert "No se pudo conectar" in texto and "caducó" in texto and "DATABASE_URL" in texto
    assert "dpg-secreto" not in texto and "render.com" not in texto
    assert not app.text_input  # no se muestra el formulario de acceso


def test_pantalla_para_errores_que_no_son_de_conexion(monkeypatch):
    def rota():
        raise RuntimeError("detalle interno con password=ABC")

    monkeypatch.setattr(arranque, "preparar_base_de_datos", rota)
    app = AppTest.from_file(os.path.join(RAIZ, "main.py"), default_timeout=60).run()
    assert any("No se pudo preparar" in e.value for e in app.error)
    assert not any("ABC" in e.value for e in app.error)
