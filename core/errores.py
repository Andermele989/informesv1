"""Excepciones propias. Sus mensajes son seguros: nunca incluyen contraseñas ni la URL de conexión."""


class ErrorDeConfiguracion(Exception):
    """La configuración del entorno (p. ej. `DATABASE_URL`) no se puede usar."""
