import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from database import engine, SessionLocal, Base
import models

DB_USER = "postgres"
DB_PASS = "123456"
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "informes_db"

def migrate():
    # 1. Crear las nuevas tablas (la tabla publishers) usando SQLAlchemy
    print("Creando tabla publishers y asegurando esquema...")
    Base.metadata.create_all(bind=engine)
    
    # 2. Añadir la columna publisher_id usando DB puro si sqlalchemy no la agregó por ser tabla existente
    try:
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        try:
            cursor.execute("ALTER TABLE monthly_reports ADD COLUMN publisher_id INTEGER REFERENCES publishers(id);")
            print("Columna publisher_id añadida.")
        except Exception as e:
            print(f"Columna publisher_id ya existe o error: {e}")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error conectando a PostgreSQL para el ALTER: {e}")

    # 3. Mapear usuarios existentes a publicadores
    db = SessionLocal()
    users = db.query(models.User).filter(models.User.role != "admin").all()
    
    for u in users:
        # Check if publisher exists
        pub = db.query(models.Publisher).filter(models.Publisher.name == u.username).first()
        if not pub:
            pub = models.Publisher(name=u.username, is_inactive=u.is_inactive)
            db.add(pub)
            db.commit()
            db.refresh(pub)
            print(f"Publicador '{pub.name}' creado desde usuario.")
        
        # Link existing reports to this publisher
        reports = db.query(models.MonthlyReport).filter(models.MonthlyReport.user_id == u.id).all()
        for r in reports:
            if r.publisher_id is None:
                r.publisher_id = pub.id
        db.commit()
        
    db.close()
    print("Migración completada.")

if __name__ == "__main__":
    migrate()
