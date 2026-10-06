from datetime import timedelta

from core import auth, models
from core.database import sesion
from core.security import verify_password

from conftest import PASSWORD_ADMIN


def test_login_correcto(datos_ejemplo):
    with sesion() as db:
        user, error = auth.autenticar(db, "admin", PASSWORD_ADMIN)
    assert error is None and user.username == "admin"


def test_mensaje_generico_si_falla_usuario_o_clave(datos_ejemplo):
    with sesion() as db:
        _, mal_clave = auth.autenticar(db, "admin", "incorrecta")
        _, mal_usuario = auth.autenticar(db, "fantasma", "incorrecta")
    assert mal_clave == mal_usuario == "Usuario o contraseña incorrectos."


def test_campos_vacios(bd):
    with sesion() as db:
        assert auth.autenticar(db, "", "x")[1] and auth.autenticar(db, "admin", "")[1]


def test_bloqueo_tras_cinco_fallos_y_reinicio_al_acertar(datos_ejemplo):
    with sesion() as db:
        for _ in range(auth.MAX_INTENTOS):
            auth.autenticar(db, "admin", "incorrecta")
        user, error = auth.autenticar(db, "admin", PASSWORD_ADMIN)  # clave buena, pero está bloqueado
        assert user is None and "Demasiados intentos" in error

        intento = db.get(models.LoginAttempt, "admin")
        intento.locked_until = auth._ahora() - timedelta(minutes=1)  # expira el bloqueo
        db.commit()
        user, error = auth.autenticar(db, "admin", PASSWORD_ADMIN)
        assert user and error is None
        assert db.get(models.LoginAttempt, "admin") is None  # contador reiniciado


def test_bloqueo_aplica_tambien_a_usuarios_inexistentes(bd):
    with sesion() as db:
        for _ in range(auth.MAX_INTENTOS):
            auth.autenticar(db, "fantasma", "x")
        assert "Demasiados intentos" in auth.autenticar(db, "fantasma", "x")[1]


def test_cuenta_inactiva(datos_ejemplo):
    with sesion() as db:
        db.query(models.User).update({models.User.is_inactive: True})
        db.commit()
        user, error = auth.autenticar(db, "admin", PASSWORD_ADMIN)
    assert user is None and "desactivada" in error


def test_texto_plano_heredado_se_convierte_a_bcrypt(bd):
    with sesion() as db:
        db.add(models.User(username="viejo", password_hash="clave-vieja", role="user"))
        db.commit()
        user, _ = auth.autenticar(db, "viejo", "clave-vieja")
        assert user and user.password_hash.startswith("$2")


def test_cambiar_password(datos_ejemplo):
    uid = datos_ejemplo["admin_id"]
    with sesion() as db:
        assert auth.cambiar_password(db, uid, "mala", "Nueva-Clave-2026")
        assert auth.cambiar_password(db, uid, PASSWORD_ADMIN, PASSWORD_ADMIN) == "La nueva contraseña debe ser distinta de la actual."
        assert auth.cambiar_password(db, uid, PASSWORD_ADMIN, "corta")
        assert auth.cambiar_password(db, uid, PASSWORD_ADMIN, "Nueva-Clave-2026") is None
        assert verify_password("Nueva-Clave-2026", db.get(models.User, uid).password_hash)[0]
