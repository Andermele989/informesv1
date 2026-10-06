"""Configuración común de las pruebas: base SQLite temporal y entorno aislado.

El entorno se fija ANTES de importar `core.database` (el motor se crea al importar).
"""
import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DIRECTORIO = tempfile.mkdtemp(prefix="informes_tests_")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(_DIRECTORIO, 'pruebas.db')}"
os.environ["SECRET_KEY"] = "clave-de-pruebas-" + "x" * 32
sys.path.insert(0, RAIZ)

import pytest

from core import models
from core.database import Base, engine, sesion
from core.security import hash_password

PASSWORD_ADMIN = "Clave-Segura-2026"
_VARIABLES_SENSIBLES = ("GEMINI_API_KEY", "OPENAI_API_KEY", "ADMIN_INITIAL_PASSWORD")


@pytest.fixture(autouse=True)
def entorno_aislado(monkeypatch):
    """Las pruebas nunca usan claves reales ni llaman a servicios externos.

    `core.database` carga el `.env` del proyecto al importarse, por eso se limpia aquí y no antes.
    """
    for variable in _VARIABLES_SENSIBLES:
        monkeypatch.delenv(variable, raising=False)


@pytest.fixture()
def bd():
    """Base de datos vacía por prueba."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def datos_ejemplo(bd):
    """Un admin, dos grupos, cuatro publicadores (uno inactivo) y varios informes."""
    with sesion() as db:
        admin = models.User(username="admin", password_hash=hash_password(PASSWORD_ADMIN), role="admin")
        g1, g2 = models.Group(name="Grupo 1"), models.Group(name="Grupo 2")
        db.add_all([admin, g1, g2, models.Privilege(name="Publicador"), models.Privilege(name="Precursor Regular")])
        db.commit()
        ana = models.Publisher(name="Ana", group_id=g1.id)
        beto = models.Publisher(name="Beto", group_id=g1.id)
        carla = models.Publisher(name="Carla", group_id=g2.id)
        nico = models.Publisher(name="Nico", group_id=g2.id, is_inactive=True)
        db.add_all([ana, beto, carla, nico])
        db.commit()
        filas = [
            (ana, "2026-09", "Precursor Regular", "60 horas", 2),
            (beto, "2026-09", "Publicador", "Sí participé", 0),
            (ana, "2026-10", "Precursor Regular", "50 horas", 1),
            (beto, "2026-10", "Publicador", "No participé", 0),
            (carla, "2026-10", "Precursor Regular", "0 horas", 0),
        ]
        for pub, mes, priv, informe, cursos in filas:
            db.add(models.MonthlyReport(user_id=admin.id, publisher_id=pub.id, full_name=pub.name, month=mes,
                                        assigned_privileges=priv, service_report=informe, bible_courses=cursos, notes="privado"))
        db.commit()
        return {"admin_id": admin.id}
