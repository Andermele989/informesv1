from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="user") # "admin" or "user"
    is_inactive = Column(Boolean, default=False)
    
    reports = relationship("MonthlyReport", back_populates="user")

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
    is_inactive = Column(Boolean, default=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)
    
    group = relationship("Group", back_populates="publishers")
    reports = relationship("MonthlyReport", back_populates="publisher")

class MonthlyReport(Base):
    __tablename__ = "monthly_reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    publisher_id = Column(Integer, ForeignKey("publishers.id"), nullable=True)
    month = Column(String, index=True) # Format "YYYY-MM"
    full_name = Column(String) # Nombre completo
    assigned_privileges = Column(String) # Comma separated list of privileges
    service_report = Column(String) # Qualitative or quantitative
    notes = Column(String) # Justificacion si no predico
    bible_courses = Column(Integer, default=0)

    user = relationship("User", back_populates="reports")
    publisher = relationship("Publisher", back_populates="reports")
