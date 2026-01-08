from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from datetime import datetime
from typing import Generator

SQLALCHEMY_DATABASE_URL = "sqlite:///./nutrition.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    events = relationship("Event", back_populates="user")
    targets = relationship("UserTarget", back_populates="user")

class UserTarget(Base):
    __tablename__ = "user_targets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    kcal = Column(Float, nullable=True)
    protein_g = Column(Float, nullable=True)
    fiber_g = Column(Float, nullable=True)
    carbs_g = Column(Float, nullable=True)
    fat_g = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="targets")

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    event_type = Column(String, index=True)  # diet, activity, sleep
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Diet event fields
    food_name = Column(String, nullable=True)
    calories = Column(Float, nullable=True)
    protein_g = Column(Float, nullable=True)
    carbs_g = Column(Float, nullable=True)
    fat_g = Column(Float, nullable=True)

    # Activity event fields
    activity_type = Column(String, nullable=True)
    duration_minutes = Column(Float, nullable=True)
    calories_burned = Column(Float, nullable=True)

    # Sleep event fields
    sleep_hours = Column(Float, nullable=True)
    sleep_quality = Column(String, nullable=True)

    user = relationship("User", back_populates="events")

class Food(Base):
    __tablename__ = "foods"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    calories = Column(Float, nullable=True)
    protein_g = Column(Float, nullable=True)
    carbs_g = Column(Float, nullable=True)
    fat_g = Column(Float, nullable=True)
    fiber_g = Column(Float, nullable=True)
    sugar_g = Column(Float, nullable=True)
    sodium_mg = Column(Float, nullable=True)
    category = Column(String, nullable=True)
    source = Column(String, nullable=True)  # usda, custom, etc.

    created_at = Column(DateTime, default=datetime.utcnow)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()