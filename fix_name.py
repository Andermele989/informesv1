from database import SessionLocal
import models

def fix_publisher_name():
    db = SessionLocal()
    try:
        # Se encontró como 'Yenfren Ojeda (S. de grupo)'
        search_name = "Yenfren Ojeda (S. de grupo)"
        target_name = "Yenfer ojeda"

        # 1. Actualizar en la tabla de Publishers
        publisher = db.query(models.Publisher).filter(models.Publisher.name == search_name).first()
        if publisher:
            print(f"Encontrado publicador: {publisher.name}")
            publisher.name = target_name
            print(f"Nombre actualizado a: {publisher.name}")
        else:
            print(f"No se encontró al publicador '{search_name}' en la tabla publishers.")

        # 2. Actualizar en la tabla de MonthlyReports (histórico)
        reports = db.query(models.MonthlyReport).filter(models.MonthlyReport.full_name == search_name).all()
        if reports:
            print(f"Actualizando {len(reports)} informes antiguos...")
            for r in reports:
                r.full_name = target_name
        
        db.commit()
        print("Cambios guardados exitosamente.")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    fix_publisher_name()
