"""
migrate_groups.py — Agrega tabla 'groups' y columna 'group_id' en publishers.
Crea un grupo por defecto y asigna todos los publicadores existentes.
"""
import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from sqlalchemy import text
from database import engine, SessionLocal
import models

def migrate():
    db = SessionLocal()
    try:
        # 1. Crear tabla groups si no existe
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'groups')"
            ))
            table_exists = result.scalar()

        if not table_exists:
            models.Group.__table__.create(bind=engine)
            print("✅ Tabla 'groups' creada exitosamente.")
        else:
            print("ℹ️  Tabla 'groups' ya existe.")

        # 2. Agregar columna group_id a publishers si no existe
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.columns "
                "WHERE table_name = 'publishers' AND column_name = 'group_id')"
            ))
            column_exists = result.scalar()

        if not column_exists:
            with engine.connect() as conn:
                conn.execute(text(
                    "ALTER TABLE publishers ADD COLUMN group_id INTEGER REFERENCES groups(id)"
                ))
                conn.commit()
            print("✅ Columna 'group_id' agregada a publishers.")
        else:
            print("ℹ️  Columna 'group_id' ya existe en publishers.")

        # 3. Crear grupo por defecto si no hay ninguno
        grupo_defecto = db.query(models.Group).first()
        if not grupo_defecto:
            grupo_defecto = models.Group(name="Grupo 1")
            db.add(grupo_defecto)
            db.commit()
            db.refresh(grupo_defecto)
            print(f"✅ Grupo por defecto '{grupo_defecto.name}' creado (ID: {grupo_defecto.id}).")
        else:
            print(f"ℹ️  Ya existe al menos un grupo: '{grupo_defecto.name}'.")

        # 4. Asignar publicadores sin grupo al grupo por defecto
        sin_grupo = db.query(models.Publisher).filter(models.Publisher.group_id == None).all()
        if sin_grupo:
            for pub in sin_grupo:
                pub.group_id = grupo_defecto.id
            db.commit()
            print(f"✅ {len(sin_grupo)} publicadores asignados a '{grupo_defecto.name}'.")
        else:
            print("ℹ️  Todos los publicadores ya tienen grupo asignado.")

        print("\n🎉 Migración completada exitosamente.")

    except Exception as e:
        db.rollback()
        print(f"❌ Error en la migración: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
