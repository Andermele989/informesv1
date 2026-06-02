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

        # Try to add full_name
        try:
            cursor.execute("ALTER TABLE monthly_reports ADD COLUMN full_name VARCHAR;")
            print("Columna 'full_name' añadida.")
        except Exception as e:
            print(f"No se pudo añadir 'full_name' (puede que ya exista): {e}")
        
        # Try to add notes
        try:
            cursor.execute("ALTER TABLE monthly_reports ADD COLUMN notes VARCHAR;")
            print("Columna 'notes' añadida.")
        except Exception as e:
            print(f"No se pudo añadir 'notes' (puede que ya exista): {e}")

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error general: {e}")

if __name__ == '__main__':
    alter_table()
