from datetime import datetime
from sqlalchemy import Column, String, DateTime, Float, ForeignKey, Uuid
from app.database import Base

class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Uuid, primary_key=True, index=True)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    category = Column(String, default="General")
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
