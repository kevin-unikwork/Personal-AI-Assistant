from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Uuid
from sqlalchemy.orm import relationship
from app.database import Base

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    due_datetime = Column(DateTime, nullable=True)
    repeat = Column(String, default="none", nullable=False) # none, daily, weekly, hourly
    status = Column(String, default="pending", nullable=False) # pending, completed, reminded
    assigned_to = Column(String, nullable=True) # phone number or email of someone else
    assigned_by = Column(String, nullable=True) # phone number of the person who assigned it
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", backref="tasks")
