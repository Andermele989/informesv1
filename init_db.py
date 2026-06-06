import os
from database import SessionLocal, engine, Base
import models

def init_db():
    print("Creating tables in the PostgreSQL database...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")
    
    # Optionally create an admin user
    db = SessionLocal()
    admin = db.query(models.User).filter(models.User.username == "admin").first()
    if not admin:
        print("Creating default admin user (admin / admin)...")
        # In a real app we would hash the password, but for simplicity here:
        new_admin = models.User(username="admin", password_hash="admin", role="admin")
        db.add(new_admin)
        db.commit()
    db.close()

if __name__ == "__main__":
    try:
        init_db()
    except Exception as e:
        print(f"Error initializing DB: {e}")
        print("Asegúrate de que PostgreSQL esté instalado, corriendo y que la base de datos 'informes_db' exista.")
