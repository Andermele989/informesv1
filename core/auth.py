"""Autenticación y sesión.

- La sesión vive en `st.session_state` y se restaura tras recargar con una cookie firmada
  (`core.security`). Ningún token, rol o usuario viaja en la URL.
- Tras `MAX_INTENTOS` fallos seguidos, la cuenta se bloquea un rato (tabla `login_attempts`).
- Cambiar la contraseña invalida todas las cookies de sesión anteriores.
"""
import logging
import time
from datetime import datetime, timedelta, UTC

import streamlit as st
from sqlalchemy import func

from core import models
from core.database import sesion
from core.security import (
    SESSION_TTL_SECONDS, hash_password, huella_password, make_session_token, read_session_token,
    normalizar_usuario, validar_password, verify_password, verificar_senuelo,
)

log = logging.getLogger("informes.auth")

COOKIE_NAME = "informes_session"
COOKIE_MAX_AGE = SESSION_TTL_SECONDS  # misma duración que el token firmado
_COOKIE_PENDIENTE = "_cookie_pendiente"

MAX_INTENTOS = 5
BLOQUEO_BASE_MIN = 15
BLOQUEO_MAX_MIN = 120

# Parámetros de URL que versiones antiguas usaban para arrastrar la sesión.
PARAMS_SENSIBLES = ("token", "username", "role", "user_id", "password", "session")


# ---------------------------------------------------------------------------
# Lógica de acceso (sin Streamlit: recibe una sesión de base de datos)
# ---------------------------------------------------------------------------

def _ahora() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _mensaje_bloqueo(minutos: int) -> str:
    return f"Demasiados intentos fallidos. Inténtalo de nuevo en {minutos} min."


def _registrar_fallo(db, clave: str, intento: models.LoginAttempt | None, ahora: datetime) -> int:
    """Suma un fallo y, si toca, bloquea la cuenta. Devuelve los minutos de bloqueo (0 si no hay)."""
    minutos = 0
    if intento is None:
        intento = models.LoginAttempt(username=clave, failures=0)
        db.add(intento)
    intento.failures += 1
    intento.last_failure = ahora
    if intento.failures % MAX_INTENTOS == 0:
        minutos = min(BLOQUEO_BASE_MIN * (intento.failures // MAX_INTENTOS), BLOQUEO_MAX_MIN)
        intento.locked_until = ahora + timedelta(minutes=minutos)
        log.warning("Cuenta bloqueada %s min tras %s fallos: %s", minutos, intento.failures, clave)
    # Limpieza de registros viejos para que la tabla no crezca sin límite.
    db.query(models.LoginAttempt).filter(
        models.LoginAttempt.last_failure < ahora - timedelta(days=1),
        models.LoginAttempt.username != clave,
    ).delete(synchronize_session=False)
    db.commit()
    return minutos


def autenticar(db, username: str, password: str) -> tuple[models.User | None, str | None]:
    """Comprueba credenciales. Devuelve `(usuario, None)` o `(None, mensaje_de_error)`."""
    nombre = normalizar_usuario(username)
    if not nombre or not password:
        return None, "Ingresa tu usuario y tu contraseña."

    clave = nombre
    ahora = _ahora()
    intento = db.get(models.LoginAttempt, clave)
    if intento and intento.locked_until and intento.locked_until > ahora:
        return None, _mensaje_bloqueo(int((intento.locked_until - ahora).total_seconds() // 60) + 1)

    user = db.query(models.User).filter(func.lower(models.User.username) == nombre).first()
    if user:
        valida, mejorar_hash = verify_password(password, user.password_hash)
    else:
        verificar_senuelo(password)
        valida = mejorar_hash = False

    if not valida:
        bloqueo = _registrar_fallo(db, clave, intento, ahora)
        return None, _mensaje_bloqueo(bloqueo) if bloqueo else "Usuario o contraseña incorrectos."
    if user.is_inactive:
        return None, "Esta cuenta está desactivada. Contacta con un administrador."

    if mejorar_hash:  # contraseña en texto plano heredada: pasa a bcrypt
        user.password_hash = hash_password(password)
    if intento:
        db.delete(intento)
    db.commit()
    return user, None


def cambiar_password(db, user_id: int, actual: str, nueva: str) -> str | None:
    """Cambia la contraseña de un usuario. Devuelve un mensaje de error o `None` si salió bien."""
    user = db.get(models.User, user_id)
    if not user or not verify_password(actual, user.password_hash)[0]:
        return "La contraseña actual no es correcta."
    if nueva == actual:
        return "La nueva contraseña debe ser distinta de la actual."
    error = validar_password(nueva, user.username)
    if error:
        return error
    user.password_hash = hash_password(nueva)
    db.commit()
    return None


# ---------------------------------------------------------------------------
# Sesión de Streamlit
# ---------------------------------------------------------------------------

def hay_sesion() -> bool:
    return bool(st.session_state.get("logged_in") and st.session_state.get("user_id"))


def es_admin() -> bool:
    return hay_sesion() and st.session_state.get("role") == "admin"


def _limpiar_query_params() -> None:
    for param in PARAMS_SENSIBLES:
        if param in st.query_params:
            del st.query_params[param]


def _es_https() -> bool:
    try:
        proto = st.context.headers.get("X-Forwarded-Proto", "")
        return proto.split(",")[0].strip() == "https" or str(st.context.url).startswith("https")
    except Exception:
        return False


def _controlador_cookies():
    """CookieController, o `None` si el componente no está disponible."""
    try:
        from streamlit_cookies_controller import CookieController
        return CookieController(key="_informes_cc")
    except Exception:
        return None


def _programar_cookie(accion: str, token: str | None = None) -> None:
    st.session_state[_COOKIE_PENDIENTE] = (accion, token)


def _aplicar_cookie_pendiente() -> None:
    """Escribe o borra la cookie programada en la ejecución anterior.

    El componente de cookies es un iframe que debe seguir en pantalla para ejecutar su JS.
    Si se renderiza justo antes de `st.rerun()` (login/logout) desaparece antes de actuar.
    Por eso la cookie se programa y se aplica al inicio del siguiente render.
    """
    pendiente = st.session_state.pop(_COOKIE_PENDIENTE, None)
    controlador = _controlador_cookies() if pendiente else None
    if not controlador:
        return
    accion, token = pendiente
    try:
        if accion == "set":
            controlador.set(COOKIE_NAME, token, max_age=COOKIE_MAX_AGE, same_site="strict",
                            secure=True if _es_https() else None)
        else:
            controlador.remove(COOKIE_NAME)
    except Exception:  # remove() lanza KeyError si la cookie no estaba en su caché local
        pass


def _abrir_sesion(user: models.User, password_debil: bool) -> None:
    st.session_state.update(
        logged_in=True, logged_out=False, user_id=user.id, username=user.username,
        role=user.role, password_debil=password_debil, _auth_check_ts=time.time(),
    )


def iniciar_sesion(user: models.User, password: str) -> None:
    """Abre la sesión tras un login correcto y programa la cookie."""
    _abrir_sesion(user, password_debil=validar_password(password, user.username) is not None)
    _programar_cookie("set", make_session_token(user.id, user.password_hash))


def _es_password_debil(user: models.User) -> bool:
    """Para sesiones restauradas por cookie (no hay contraseña en claro): prueba las típicas."""
    return any(verify_password(c, user.password_hash)[0] for c in {"admin", user.username})


def restaurar_sesion() -> None:
    """Punto de entrada de cada ejecución: limpia la URL, aplica cookies y restaura la sesión."""
    _limpiar_query_params()
    _aplicar_cookie_pendiente()
    if hay_sesion() or st.session_state.get("logged_out"):
        return

    controlador = _controlador_cookies()
    try:
        token = controlador.get(COOKIE_NAME) if controlador else None
    except Exception:
        log.warning("No se pudo leer la cookie de sesión; se solicitará iniciar sesión de nuevo.")
        return
    datos = read_session_token(token) if token else None
    if not datos:
        return
    with sesion() as db:
        user = db.get(models.User, datos["user_id"])
        # Cuenta eliminada/inactiva o contraseña cambiada desde que se emitió la cookie.
        if user and not user.is_inactive and huella_password(user.password_hash) == datos["huella"]:
            _abrir_sesion(user, password_debil=_es_password_debil(user))


def validar_sesion_vigente(intervalo_segundos: int = 30) -> bool:
    """Confirma que el usuario sigue existiendo y activo, y refresca su rol desde la BD."""
    if not hay_sesion():
        return False
    ahora = time.time()
    ultimo_chequeo = st.session_state.get("_auth_check_ts")
    if ultimo_chequeo is not None and (ahora - ultimo_chequeo < intervalo_segundos):
        return True
    with sesion() as db:
        user = db.get(models.User, st.session_state.user_id)
        if not user or user.is_inactive:
            vaciar_sesion()
            return False
        st.session_state.role, st.session_state.username = user.role, user.username
    st.session_state["_auth_check_ts"] = ahora
    return True


def vaciar_sesion() -> None:
    _programar_cookie("remove")
    st.session_state.pop("_auth_check_ts", None)
    st.session_state.update(logged_in=False, logged_out=True, user_id=None, username="",
                            role="", password_debil=False)


def cerrar_sesion() -> None:
    vaciar_sesion()
    st.query_params.clear()
    st.rerun()


def actualizar_cookie_tras_cambio(user_id: int) -> None:
    """Tras cambiar la contraseña, emite una cookie nueva para esta sesión."""
    with sesion() as db:
        user = db.get(models.User, user_id)
        if user:
            _programar_cookie("set", make_session_token(user.id, user.password_hash))
    st.session_state.password_debil = False


def require_login() -> None:
    """Guardia de vistas: sin sesión no se renderiza nada."""
    if not hay_sesion():
        st.warning("Inicia sesión para continuar.")
        st.stop()


def require_admin() -> None:
    """Guardia de vistas de administración."""
    require_login()
    if not es_admin():
        st.error("Acceso denegado. Solo los administradores pueden ver esta página.")
        st.stop()
