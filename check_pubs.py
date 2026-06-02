from database import SessionLocal
import models

def check_publishers():
    db = SessionLocal()
    try:
        publishers = db.query(models.Publisher).all()
        for p in publishers:
            print(f"- {p.name}")
    finally:
        db.close()

if __name__ == "__main__":
    check_publishers()
