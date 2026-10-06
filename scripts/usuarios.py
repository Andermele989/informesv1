"""Gestión de usuarios desde la terminal (la app no tiene pantalla para crear usuarios).

Desde la raíz del proyecto:
    python -m scripts.usuarios listar
    python -m scripts.usuarios crear <usuario> [--admin]
    python -m scripts.usuarios password <usuario>      # restablece la contraseña
    python -m scripts.usuarios desbloquear <usuario>   # quita el bloqueo por intentos fallidos
    python -m scripts.usuarios desactivar <usuario> | activar <usuario>
Las contraseñas se piden por teclado: no quedan en el historial de la terminal.
"""
import getpass
import sys

from core import models
from core.database import sesion
from core.security import hash_password, normalizar_usuario, validar_password


def pedir_password(usuario: str) -> str:
    while True:
        clave = getpass.getpass("Nueva contraseña: ")
        error = validar_password(clave, usuario)
        if error:
            print(error)
        elif clave != getpass.getpass("Repite la contraseña: "):
            print("No coinciden.")
        else:
            return clave


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in {"listar", "crear", "password", "desbloquear", "activar", "desactivar"}:
        print(__doc__)
        return 2
    accion, nombre = argv[0], normalizar_usuario(argv[1] if len(argv) > 1 else "")
    with sesion() as db:
        if accion == "listar":
            for u in db.query(models.User).order_by(models.User.username):
                print(f"{u.username:20} {u.role:8} {'INACTIVO' if u.is_inactive else 'activo'}")
            return 0
        if not nombre:
            print("Falta el nombre de usuario.")
            return 2
        user = db.query(models.User).filter(models.User.username == nombre).first()
        if accion == "crear":
            if user:
                print(f"El usuario '{nombre}' ya existe.")
                return 1
            db.add(models.User(username=nombre, password_hash=hash_password(pedir_password(nombre)),
                               role="admin" if "--admin" in argv else "user"))
        elif not user:
            print(f"No existe el usuario '{nombre}'.")
            return 1
        elif accion == "password":
            user.password_hash = hash_password(pedir_password(nombre))  # invalida sus sesiones activas
        elif accion == "desbloquear":
            db.query(models.LoginAttempt).filter(models.LoginAttempt.username == nombre.lower()).delete()
        else:
            user.is_inactive = accion == "desactivar"
        db.commit()
    print("Listo.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
