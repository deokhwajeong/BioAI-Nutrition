import os
from collections.abc import Generator
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker


def _utcnow():
    return datetime.now(UTC).replace(tzinfo=None)


SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./nutrition.db")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
    if SQLALCHEMY_DATABASE_URL.startswith("sqlite")
    else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

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
    created_at = Column(DateTime, default=_utcnow)

    user = relationship("User", back_populates="targets")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    event_type = Column(String, index=True)  # diet, activity, sleep
    timestamp = Column(DateTime, default=_utcnow)

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

    created_at = Column(DateTime, default=_utcnow)


# ── Accounts: per-user auth, profile, consent, and logged days ──────
# Deleting an Account cascades to its tokens, consents, and daily logs. Rows elsewhere that
# are keyed by the same user id (events, biomarker readings, ...) are removed explicitly by
# DELETE /users/{user_id}; see app/services/accounts.py.


class Account(Base):
    __tablename__ = "accounts"

    id = Column(String, primary_key=True)  # "usr_" + random hex; also the engine user_id
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)  # scrypt, see app/services/accounts.py
    created_at = Column(DateTime, default=_utcnow)

    # Profile (all optional; used to estimate energy needs)
    weight_kg = Column(Float, nullable=True)
    height_cm = Column(Float, nullable=True)
    age = Column(Integer, nullable=True)
    sex = Column(String, nullable=True)
    activity_level = Column(String, nullable=True)

    tokens = relationship("AuthToken", cascade="all, delete-orphan", back_populates="account")
    consents = relationship(
        "AccountConsent", cascade="all, delete-orphan", back_populates="account"
    )
    daily_logs = relationship("DailyLog", cascade="all, delete-orphan", back_populates="account")


class AuthToken(Base):
    """Opaque bearer token. Only its SHA-256 digest is stored."""

    __tablename__ = "auth_tokens"

    token_hash = Column(String, primary_key=True)
    account_id = Column(String, ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    created_at = Column(DateTime, default=_utcnow)
    expires_at = Column(DateTime, nullable=False)

    account = relationship("Account", back_populates="tokens")


class AccountConsent(Base):
    __tablename__ = "account_consents"
    __table_args__ = (UniqueConstraint("account_id", "scope", name="uq_account_scope"),)

    id = Column(Integer, primary_key=True)
    account_id = Column(String, ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    scope = Column(String, nullable=False)
    granted = Column(Boolean, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    account = relationship("Account", back_populates="consents")


class DailyLog(Base):
    """One logged day of intake, activity, and sleep (the DailyFeatures fields)."""

    __tablename__ = "daily_logs"
    __table_args__ = (UniqueConstraint("account_id", "date", name="uq_account_date"),)

    id = Column(Integer, primary_key=True)
    account_id = Column(String, ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    date = Column(String, nullable=False)  # ISO date
    calories = Column(Float, nullable=True)
    protein_g = Column(Float, nullable=True)
    carbs_g = Column(Float, nullable=True)
    fiber_g = Column(Float, nullable=True)
    sugar_g = Column(Float, nullable=True)
    omega3_g = Column(Float, nullable=True)
    water_ml = Column(Float, nullable=True)
    steps = Column(Float, nullable=True)
    sleep_hours = Column(Float, nullable=True)

    account = relationship("Account", back_populates="daily_logs")


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ═════════════════════════════════════════════════════════════════
#  Patent-Core: Biomarker Engine Models
# ═════════════════════════════════════════════════════════════════


class BiomarkerReading(Base):
    """Stores raw biomarker readings from heterogeneous sources.

    Patent reference: data ingestion layer for the heterogeneous
    biomarker temporal synchronization architecture.
    """

    __tablename__ = "biomarker_readings"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    biomarker_type = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    value = Column(Float, nullable=False)
    unit = Column(String, default="")
    confidence = Column(Float, default=1.0)
    raw_hash = Column(String, default="")
    metadata_json = Column(Text, default="{}")  # JSON string
    created_at = Column(DateTime, default=_utcnow)

    __table_args__ = (Index("ix_reading_user_type_ts", "user_id", "biomarker_type", "timestamp"),)


class PersonalBaseline(Base):
    """Stores learned personal baselines per user × biomarker.

    Patent reference: physiological-aware normalization layer with
    dual-timescale EWMA and circadian profile learning.
    """

    __tablename__ = "personal_baselines"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    biomarker_type = Column(String, nullable=False)
    short_term_mean = Column(Float, default=0.0)
    long_term_mean = Column(Float, default=0.0)
    variance = Column(Float, default=0.0)
    sample_count = Column(Integer, default=0)
    hourly_means_json = Column(Text, default="{}")
    hourly_counts_json = Column(Text, default="{}")
    last_updated = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    __table_args__ = (Index("ix_baseline_user_type", "user_id", "biomarker_type", unique=True),)


class GeneticProfile(Base):
    """Stores genetic variant data for nutrigenomic personalization.

    Patent reference: genetic modifier computation for
    dose-dependent nutrient demand adjustment.
    """

    __tablename__ = "genetic_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, unique=True, index=True)
    genotypes_json = Column(Text, default="{}")  # {rsID: genotype}
    computed_modifiers_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class ConsentAuditLog(Base):
    """Immutable audit trail for consent grant/revocation events.

    Patent reference: dynamic consent management system with
    real-time revocation and cryptographic audit trail.
    """

    __tablename__ = "consent_audit_log"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    scope = Column(String, nullable=False)
    action = Column(String, nullable=False)  # granted / revoked
    reason = Column(String, default="")
    ip_hash = Column(String, default="")
    consent_version = Column(String, default="1.0")
    expires_at = Column(DateTime, nullable=True)
    timestamp = Column(DateTime, default=_utcnow)


class NutrientBudgetSnapshot(Base):
    """Snapshots of calculated nutrient budgets for audit and ML training.

    Patent reference: real-time nutrient demand calculation output,
    preserving the full modification chain for reproducibility.
    """

    __tablename__ = "nutrient_budget_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False)
    targets_json = Column(Text, default="{}")
    metabolic_state = Column(String, default="")
    active_phases_json = Column(Text, default="[]")
    modifications_json = Column(Text, default="[]")
    confidence = Column(Float, default=0.0)
    frame_completeness = Column(Float, default=0.0)
    created_at = Column(DateTime, default=_utcnow)
