"""Lectura de la configuración del entorno (lo que Render entrega como variables)."""
from sqlalchemy.engine import URL, make_url

from core import database


def _url(monkeypatch, **entorno):
    for variable in ("DATABASE_URL", "DB_USER", "DB_PASS", "DB_HOST", "DB_PORT", "DB_NAME"):
        monkeypatch.delenv(variable, raising=False)
    for clave, valor in entorno.items():
        monkeypatch.setenv(clave, valor)
    return database._url_base_de_datos()


def test_render_entrega_postgres_y_sqlalchemy_necesita_postgresql(monkeypatch):
    url = _url(monkeypatch, DATABASE_URL="postgres://usuario:clave@host.render.com:5432/informes")
    assert url == "postgresql://usuario:clave@host.render.com:5432/informes"
    assert make_url(url).get_backend_name() == "postgresql"


def test_acepta_postgresql_y_parametros_de_ssl(monkeypatch):
    url = _url(monkeypatch, DATABASE_URL="postgresql://u:p@h/db?sslmode=require")
    assert url == "postgresql://u:p@h/db?sslmode=require"


def test_sqlite_se_deja_igual(monkeypatch):
    assert _url(monkeypatch, DATABASE_URL="sqlite:///prueba.db") == "sqlite:///prueba.db"


def test_variables_sueltas_escapan_caracteres_especiales_de_la_contrasena(monkeypatch):
    url = _url(monkeypatch, DB_USER="postgres", DB_PASS="p@ss/w:rd#1", DB_HOST="db.interno", DB_PORT="5433", DB_NAME="informes")
    assert isinstance(url, URL)
    assert (url.username, url.password, url.host, url.port, url.database) == ("postgres", "p@ss/w:rd#1", "db.interno", 5433, "informes")
    assert "p@ss/w:rd#1" not in url.render_as_string(hide_password=True)  # nunca se muestra en logs


def test_sin_variables_usa_los_valores_locales(monkeypatch):
    url = _url(monkeypatch)
    assert (url.host, url.port, url.database) == ("localhost", 5432, "informes_db")
