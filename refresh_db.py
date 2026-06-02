import os
import sys

# Asegurar que el PATH incluya el directorio actual para encontrar 'database' y 'models'
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, engine, Base
import models

def refresh_data():
    db = SessionLocal()
    try:
        # 1. Limpiar datos (Borrar registros de las tablas principales)
        print("Borrando informes...")
        db.query(models.MonthlyReport).delete()
        print("Borrando publicadores...")
        db.query(models.Publisher).delete()
        print("Borrando privilegios...")
        db.query(models.Privilege).delete()
        db.commit()
        print("✅ Base de datos vaciada exitosamente.")

        # 2. Agregar Privilegios Base
        print("Cargando privilegios base...")
        privs = ["Publicador", "Publicadora", "Precursor", "Precursora", "Auxiliar"]
        for p_name in privs:
            if not db.query(models.Privilege).filter(models.Privilege.name == p_name).first():
                db.add(models.Privilege(name=p_name))
        
        # 3. Agregar Publicadores de la lista corregida (con etiquetas especiales)
        print("Cargando listado de publicadores...")
        lista_publicadores = [
            ("Yenfer Ojeda (S. de grupo)", False),
            ("Anderson Melendez (Aux.)", False),
            ("Yolmarys Ojeda", False),
            ("Jose Arbelaez", False),
            ("Erosilda Arbelaez", False),
            ("Mario Arbelaez", False),
            ("Ender Requena", False),
            ("Delis Requena", False),
            ("David Requena", False),
            ("Esteban Requena", False),
            ("Lina Sanchez", False),
            ("Elizandrit Rebolledo", False),
            ("Teonilda Porto", False),
            ("Diana Maestre", False),
            ("Zenaida Jimenez", False)
        ]
        
        for name, inactive in lista_publicadores:
            db.add(models.Publisher(name=name, is_inactive=inactive))
        
        db.commit()
        print(f"✅ Se han cargado {len(lista_publicadores)} publicadores correctamente con etiquetas especiales.")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error durante el refresh: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    refresh_data()
