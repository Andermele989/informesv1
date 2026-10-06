"""Restricciones que protegen la integridad directamente en la base de datos."""
import pytest
from sqlalchemy.exc import IntegrityError

from core import models
from core.arranque import _crear_admin_si_falta
from core.database import sesion
from core.security import hash_password


def test_usuario_no_admite_duplicado_por_mayusculas(bd):
    with sesion() as db:
        db.add(models.User(username="Admin", password_hash=hash_password("Clave-Segura-2026"), role="admin"))
        db.commit()

    with pytest.raises(IntegrityError), sesion() as db:
        db.add(models.User(username="admin", password_hash=hash_password("Otra-Clave-Segura-2026")))
        db.commit()


def test_informe_no_admite_duplicado_por_publicador_y_mes(bd):
    ids = {}
    with sesion() as db:
        user = models.User(username="ana", password_hash=hash_password("Clave-Segura-2026"))
        publisher = models.Publisher(name="Ana")
        db.add_all([user, publisher])
        db.commit()
        ids = {"user": user.id, "publisher": publisher.id}
        db.add(models.MonthlyReport(user_id=user.id, publisher_id=publisher.id, month="2026-10"))
        db.commit()

    with pytest.raises(IntegrityError), sesion() as db:
        db.add(models.MonthlyReport(user_id=ids["user"], publisher_id=ids["publisher"], month="2026-10"))
        db.commit()


def test_informe_rechaza_cursos_negativos(bd):
    with sesion() as db:
        user = models.User(username="beto", password_hash=hash_password("Clave-Segura-2026"))
        publisher = models.Publisher(name="Beto")
        db.add_all([user, publisher])
        db.commit()
        ids = {"user": user.id, "publisher": publisher.id}

    with pytest.raises(IntegrityError), sesion() as db:
        db.add(models.MonthlyReport(
            user_id=ids["user"], publisher_id=ids["publisher"], month="2026-10", bible_courses=-1
        ))
        db.commit()


def test_no_intenta_recrear_admin_si_existe_con_mayusculas(bd):
    with sesion() as db:
        db.add(models.User(username="Admin", password_hash=hash_password("Clave-Segura-2026"), role="admin"))
        db.commit()

    _crear_admin_si_falta()

    with sesion() as db:
        assert db.query(models.User).count() == 1
