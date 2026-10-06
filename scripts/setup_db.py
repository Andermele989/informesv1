"""Instalación inicial: crea la base de datos `DB_NAME`, las tablas y el usuario `admin`.

Desde la raíz del proyecto:  python -m scripts.setup_db
Si `ADMIN_INITIAL_PASSWORD` no está definida, se genera una contraseña aleatoria y se muestra una vez.
"""
import os
import sys

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from core.database import RAIZ_PROYECTO  # noqa: F401  (carga el .env)


def crear_base_de_datos() -> bool:
    usuario, host, puerto = os.getenv("DB_USER", "postgres"), os.getenv("DB_HOST", "localhost"), os.getenv("DB_PORT", "5432")
    nombre = os.getenv("DB_NAME", "informes_db")
    print(f"Conectando a PostgreSQL como '{usuario}' en {host}:{puerto}...")
    try:
        conn = psycopg2.connect(dbname="postgres", user=usuario, password=os.getenv("DB_PASS", ""), host=host, port=puerto)
    except psycopg2.Error as exc:
        print(f"No se pudo conectar: {exc}\n\nRevisa que PostgreSQL esté activo y que DB_USER, DB_PASS, DB_HOST y DB_PORT "
              "estén bien definidos en .env.")
        return False
    with conn:
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (nombre,))
            if cur.fetchone():
                print(f"La base de datos '{nombre}' ya existe.")
            else:
                cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(nombre)))
                print(f"Base de datos '{nombre}' creada.")
    conn.close()
    return True


def main() -> int:
    if not crear_base_de_datos():
        return 1
    from core.arranque import preparar
    preparar()
    print("Tablas y usuario admin listos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
