"""
Persistence layer using SQLAlchemy. Defaults to a local SQLite file so
the prototype runs with zero external setup; pointing DATABASE_URL at a
postgresql://... URL is the entire migration to PostgreSQL - no code
change needed, since SQLAlchemy abstracts the dialect.
"""
import datetime
import json
import uuid

from sqlalchemy import JSON, Column, DateTime, Float, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class ApplicationRecord(Base):
    __tablename__ = "applications"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    account_id = Column(String, nullable=True, index=True)
    input_payload = Column(JSON)
    decision = Column(String)
    approval_probability = Column(Float)
    credit_intel_score = Column(Float)
    fused_score = Column(Float, nullable=True)
    explanation = Column(String)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def save_application(db, *, account_id, input_payload, result: dict) -> str:
    record = ApplicationRecord(
        account_id=account_id,
        input_payload=json.loads(json.dumps(input_payload, default=str)),
        decision=result["decision"],
        approval_probability=result["approval_probability"],
        credit_intel_score=result["credit_intel_score"],
        fused_score=result.get("fused_score"),
        explanation=result["explanation"],
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record.id
