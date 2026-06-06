from database import SessionLocal
import models

def rename_group():
    db = SessionLocal()
    try:
        grupo = db.query(models.Group).filter(models.Group.name == 'Grupo 1').first()
        if grupo:
            grupo.name = 'Grupo 7'
            db.commit()
            print("Grupo renombrado exitosamente.")
        else:
            print("Grupo no encontrado.")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    rename_group()
