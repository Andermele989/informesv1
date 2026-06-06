import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import psycopg2

try:
    conn = psycopg2.connect(
        host='localhost',
        dbname='informes_db',
        user='postgres',
        password='123456'
    )
    cur = conn.cursor()
    cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")
    tables = [t[0] for t in cur.fetchall()]
    print("CONEXION EXITOSA a informes_db")
    print("Tablas encontradas:", tables)
    conn.close()
except Exception as e:
    print("ERROR:", str(e).encode('ascii', 'replace').decode())
