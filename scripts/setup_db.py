"""
Script para crear la base de datos informes_db y las tablas necesarias.
Ejecutar UNA sola vez: python setup_db.py
"""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

DB_USER = "postgres"
DB_PASS = "123456"
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "informes_db"

def create_database():
    print(f"Conectando a PostgreSQL como '{DB_USER}'...")
    try:
        # Conectar a la DB por defecto 'postgres' para poder crear informes_db
        conn = psycopg2.connect(
            dbname="postgres",
            user=DB_USER,
            password=DB_PASS,
            host=DB_HOST,
            port=DB_PORT
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Verificar si ya existe
        cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (DB_NAME,))
        exists = cursor.fetchone()

        if not exists:
            cursor.execute(f'CREATE DATABASE "{DB_NAME}"')
            print(f"✅ Base de datos '{DB_NAME}' creada exitosamente.")
        else:
            print(f"ℹ️  La base de datos '{DB_NAME}' ya existe. No se creó de nuevo.")

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error al conectar a PostgreSQL: {e}")
        print()
        print("VERIFICA QUE:")
        print("  1. PostgreSQL esté instalado y corriendo (servicio activo en Windows).")
        print("  2. El usuario 'postgres' exista y la contraseña sea '1234'.")
        print("  3. PostgreSQL escucha en localhost:5432 (configuración por defecto).")
        return False
    return True


def init_tables():
    print("Creando tablas en la base de datos...")
    try:
        # Importar después de garantizar la BD existe
        from database import engine, Base
        import models  # noqa: importa los modelos para que Base los conozca
        Base.metadata.create_all(bind=engine)
        print("✅ Tablas creadas correctamente.")
    except Exception as e:
        print(f"❌ Error al crear tablas: {e}")
        return False
    return True


def create_admin():
    print("Verificando usuario administrador...")
    try:
        from database import SessionLocal
        import models
        db = SessionLocal()
        admin = db.query(models.User).filter(models.User.username == "admin").first()
        if not admin:
            new_admin = models.User(username="admin", password_hash="admin", role="admin")
            db.add(new_admin)
            db.commit()
            print("✅ Usuario admin creado (usuario: admin / contraseña: admin).")
        else:
            print("ℹ️  El usuario admin ya existe.")
        db.close()
    except Exception as e:
        print(f"❌ Error al crear usuario admin: {e}")
        return False
    return True


if __name__ == "__main__":
    print("=" * 50)
    print("  CONFIGURACIÓN INICIAL DE LA BASE DE DATOS")
    print("=" * 50)
    if create_database():
        if init_tables():
            create_admin()
    print("=" * 50)
    print("  PROCESO FINALIZADO")
    print("=" * 50)
