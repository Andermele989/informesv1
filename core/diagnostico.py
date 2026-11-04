"""Explica en lenguaje claro por qué falló la conexión a la base de datos.

Solo mira el tipo de fallo (no su texto literal) para mostrar una pista útil en pantalla sin revelar el
servidor, el usuario ni la contraseña. El detalle completo queda en el registro del servidor.
"""
from core import database

# (palabras que aparecen en el mensaje del servidor, en inglés y en español, pista para el usuario)
_PISTAS = (
    (("password authentication failed", "autentificación", "autenticación", "authentication failed"),
     "El usuario o la contraseña de la URL no son correctos. Copia de nuevo la URL desde el panel de tu base de datos."),
    (("does not exist", "no existe la base", "no existe"),
     "El nombre de la base de datos que aparece en la URL no existe en ese servidor."),
    (("could not translate host name", "name or service not known", "no se pudo traducir", "nodename nor servname",
      "temporary failure in name resolution"),
     "El nombre del servidor de la URL no se encuentra. Si usas la «Internal Database URL», la base y este servicio deben "
     "estar en la misma región y cuenta; si no, usa la «External Database URL»."),
    (("ssl connection has been closed", "ssl error", "ssl syscall", "sslv3", "server closed the connection unexpectedly",
      "terminating connection"),
     "El servidor cerró la conexión. Suele pasar cuando la base de Render está suspendida, caducó (las bases gratuitas "
     "caducan) o se eliminó, o cuando la URL es de una base antigua. Revisa su estado en el panel y copia su URL actual."),
    (("timeout expired", "timed out", "tiempo de espera", "tiempo agotado"),
     "El servidor no responde (tiempo agotado). La base puede estar suspendida o bloqueando la conexión por red."),
    (("connection refused", "conexión rechazada", "rechazó la conexión", "could not connect to server", "10061"),
     "El servidor rechazó la conexión: la base está apagada o el puerto no es el correcto."),
    (("too many connections", "remaining connection slots", "demasiadas conexiones"),
     "La base alcanzó su límite de conexiones. Espera un minuto y recarga, o reinicia el servicio."),
    (("no pg_hba.conf", "ssl required", "ssl is required", "requiere ssl"),
     "El servidor exige conexión segura: añade «?sslmode=require» al final de la URL."),
)


def causa_de_conexion(exc: BaseException) -> str:
    """Pista, en español y sin datos sensibles, de por qué no se pudo conectar."""
    if database.origen_conexion() == "DB_*" and database.engine.url.host in ("localhost", "127.0.0.1", "::1"):
        return ("La variable DATABASE_URL no está definida en este servicio, así que la app intenta conectarse a un "
                "PostgreSQL en el mismo equipo. En Render: Environment → añade DATABASE_URL con la «Internal Database URL» "
                "de tu base de datos.")
    if isinstance(exc, UnicodeDecodeError):
        return ("El servidor respondió con un error en un código de caracteres que no es UTF-8 (típico de PostgreSQL "
                "en Windows en español). Casi siempre significa usuario, contraseña o base de datos incorrectos.")
    texto = str(getattr(exc, "orig", exc)).lower()
    for palabras, pista in _PISTAS:
        if any(p in texto for p in palabras):
            return pista
    return "No se pudo establecer la conexión. El registro del servidor tiene el detalle exacto."
