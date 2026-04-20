from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Uuid
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class ActionLog(Base):
    __tablename__ = "action_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    intent = Column(String, nullable=False)
    action_taken = Column(String, nullable=False)
    tool_used = Column(String, nullable=True)
    success = Column(Boolean, nullable=False)
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", backref="action_logs")
