import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON, Uuid
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone_number = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    timezone = Column(String, default="Asia/Kolkata", nullable=False)
    location = Column(String, default="Surat", nullable=False)
    preferences = Column(JSON, default=dict, nullable=False)
    google_token = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_active = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
