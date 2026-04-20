from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Uuid
from app.database import Base

class Habit(Base):
    __tablename__ = "habits"

    id = Column(Uuid, primary_key=True, index=True)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    streak = Column(Integer, default=0)
    last_completed = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
