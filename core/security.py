"""Seguridad: contraseñas, token de sesión firmado y saneamiento de texto."""
import base64
import functools
import hashlib
import hmac
import html
import json
import logging
import os
import re
import secrets
import time

import bcrypt

log = logging.getLogger("informes.security")

BCRYPT_ROUNDS = 12
PASSWORD_MIN = 8
PASSWORD_MAX_BYTES = 72  # límite real de bcrypt


def _dias_de_sesion() -> int:
    try:
        return max(1, int(os.getenv("SESSION_TTL_DAYS", "7")))
    except ValueError:  # valor no numérico en el .env: se usa el predeterminado en vez de romper el arranque
        return 7


SESSION_TTL_SECONDS = _dias_de_sesion() * 24 * 3600

_PASSWORDS_COMUNES = frozenset({
    "admin", "administrador", "password", "password1", "contraseña", "contrasena", "informes",
    "12345678", "123456789", "1234567890", "qwertyui", "qwerty123", "11111111", "00000000",
})


# ---------------------------------------------------------------------------
# Contraseñas
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Hash bcrypt de una contraseña en texto plano."""
    if not password:
        raise ValueError("La contraseña no puede estar vacía")
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode("utf-8")


def is_bcrypt_hash(candidato: str) -> bool:
    return bool(candidato) and candidato.startswith(("$2a$", "$2b$", "$2y$")) and len(candidato) >= 59


def verify_password(plain: str, almacenado: str) -> tuple[bool, bool]:
    """Compara una contraseña con lo guardado. Devuelve `(es_valida, hay_que_actualizar_hash)`.

    Si lo guardado es texto plano heredado de versiones antiguas y coincide, devuelve
    `(True, True)` para que el llamador lo reemplace por un hash bcrypt.
    """
    if not plain or not almacenado or len(plain.encode("utf-8")) > PASSWORD_MAX_BYTES:
        return False, False
    if is_bcrypt_hash(almacenado):
        try:
            return bcrypt.checkpw(plain.encode("utf-8"), almacenado.encode("utf-8")), False
        except ValueError:
            return False, False
    coincide = secrets.compare_digest(plain.encode("utf-8"), almacenado.encode("utf-8"))
    return coincide, coincide


@functools.lru_cache(maxsize=1)
def _hash_senuelo() -> str:
    return hash_password(secrets.token_urlsafe(16))


def verificar_senuelo(plain: str) -> None:
    """Gasta el mismo tiempo que una verificación real.

    Se usa cuando el usuario no existe, para que el tiempo de respuesta no delate qué
    usuarios están registrados.
    """
    verify_password(plain, _hash_senuelo())


def validar_password(nueva: str, usuario: str = "") -> str | None:
    """Devuelve un mensaje de error si la contraseña no cumple la política; si no, `None`."""
    if len(nueva or "") < PASSWORD_MIN:
        return f"La contraseña debe tener al menos {PASSWORD_MIN} caracteres."
    if len(nueva.encode("utf-8")) > PASSWORD_MAX_BYTES:
        return f"La contraseña es demasiado larga (máximo {PASSWORD_MAX_BYTES} bytes)."
    if nueva.lower() in _PASSWORDS_COMUNES or (usuario and nueva.lower() == usuario.lower()):
        return "Esa contraseña es demasiado fácil de adivinar. Elige otra."
    if nueva.isdigit() or len(set(nueva)) < 4:
        return "Usa una combinación de letras, números o símbolos."
    return None


def generar_password(longitud: int = 16) -> str:
    return secrets.token_urlsafe(longitud)[:longitud]


# ---------------------------------------------------------------------------
# Clave secreta y token de sesión
# ---------------------------------------------------------------------------

def get_secret_key() -> str:
    """`SECRET_KEY` del entorno; si falta, una clave efímera (las sesiones no sobreviven reinicios)."""
    secret = os.getenv("SECRET_KEY")
    if not secret:
        secret = secrets.token_hex(32)
        os.environ["SECRET_KEY"] = secret
        log.warning("SECRET_KEY no está definida: se usa una clave temporal y las sesiones "
                    "se perderán al reiniciar. Defínela en .env o en las variables del servidor.")
    elif len(secret) < 32:
        log.warning("SECRET_KEY es corta (<32 caracteres). Usa una clave aleatoria larga.")
    return secret


def _firmar(mensaje: str) -> bytes:
    return hmac.new(get_secret_key().encode("utf-8"), mensaje.encode("utf-8"), hashlib.sha256).digest()


def _b64_codificar(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64_decodificar(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def huella_password(password_hash: str) -> str:
    """Identificador derivado del hash de la contraseña (no permite recuperarla).

    Va dentro del token de sesión: al cambiar la contraseña la huella cambia y todas las
    cookies de sesión anteriores dejan de valer.
    """
    return _firmar("pw|" + (password_hash or "")).hex()[:20]


def make_session_token(user_id: int, password_hash: str, ttl_seconds: int = SESSION_TTL_SECONDS) -> str:
    """Token `<payload>.<firma>` firmado con HMAC-SHA256. No lleva usuario ni rol."""
    payload = {"uid": int(user_id), "pv": huella_password(password_hash), "exp": int(time.time()) + int(ttl_seconds)}
    cuerpo = _b64_codificar(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    return f"{cuerpo}.{_b64_codificar(_firmar('session|' + cuerpo))}"


def read_session_token(token: str) -> dict | None:
    """Valida firma y caducidad. Devuelve `{"user_id", "huella"}` o `None`."""
    if not token or token.count(".") != 1:
        return None
    try:
        cuerpo, firma = token.split(".")
        if not hmac.compare_digest(_firmar("session|" + cuerpo), _b64_decodificar(firma)):
            return None
        payload = json.loads(_b64_decodificar(cuerpo))
        if int(payload["exp"]) < time.time():
            return None
        return {"user_id": int(payload["uid"]), "huella": str(payload["pv"])}
    except (ValueError, KeyError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Texto
# ---------------------------------------------------------------------------

_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def sanitize_text(valor: object) -> str:
    """Escapa texto para incrustarlo en HTML (`unsafe_allow_html=True`)."""
    return "" if valor is None else html.escape(str(valor), quote=True)


def limpiar_texto(valor: object, max_len: int = 200, multilinea: bool = False) -> str:
    """Quita caracteres de control, recorta espacios y limita la longitud."""
    texto = _CONTROL.sub("", "" if valor is None else str(valor))
    texto = texto.strip() if multilinea else " ".join(texto.split())
    return texto[:max_len]
