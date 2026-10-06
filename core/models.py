"""Modelos de datos."""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="user")  # "admin" | "user"
    is_inactive = Column(Boolean, default=False)

    reports = relationship("MonthlyReport", back_populates="user")


class LoginAttempt(Base):
    """Intentos de acceso fallidos por usuario (limita la fuerza bruta)."""
    __tablename__ = "login_attempts"

    username = Column(String, primary_key=True)  # en minúsculas
    failures = Column(Integer, nullable=False, default=0)
    last_failure = Column(DateTime)
    locked_until = Column(DateTime)  # UTC


class Privilege(Base):
    __tablename__ = "privileges"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)


class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)

    publishers = relationship("Publisher", back_populates="group")


class Publisher(Base):
    __tablename__ = "publishers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    is_inactive = Column(Boolean, default=False, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True, index=True)

    group = relationship("Group", back_populates="publishers")
    reports = relationship("MonthlyReport", back_populates="publisher", cascade="all, delete-orphan")


class MonthlyReport(Base):
    __tablename__ = "monthly_reports"
    # Un solo informe por publicador y mes. `core.arranque` aplica este índice también
    # en bases ya existentes (create_all no altera tablas creadas antes).
    __table_args__ = (
        Index("uq_report_publisher_month", "publisher_id", "month", unique=True),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    publisher_id = Column(Integer, ForeignKey("publishers.id"), nullable=True)
    month = Column(String, index=True)  # "YYYY-MM"
    full_name = Column(String)
    assigned_privileges = Column(String)
    service_report = Column(String)  # "NN horas" | "Sí participé (...)" | "No participé (...)"
    notes = Column(String)
    bible_courses = Column(Integer, default=0)

    user = relationship("User", back_populates="reports")
    publisher = relationship("Publisher", back_populates="reports")
