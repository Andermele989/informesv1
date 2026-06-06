import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

DB_USER = "postgres"
DB_PASS = "123456"
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "informes_db"

def alter_table():
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            host=DB_HOST,
            port=DB_PORT
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        try:
            cursor.execute("ALTER TABLE users ADD COLUMN is_inactive BOOLEAN DEFAULT FALSE;")
            print("Columna 'is_inactive' añadida a 'users'.")
        except Exception as e:
            print(f"No se pudo añadir 'is_inactive' (puede que ya exista): {e}")

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error general: {e}")

if __name__ == '__main__':
    alter_table()
