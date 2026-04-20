import uuid
from datetime import date, datetime
from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String, Uuid, UniqueConstraint
from app.database import Base


class DailyCheckin(Base):
    __tablename__ = "daily_checkins"
    __table_args__ = (
        UniqueConstraint("user_id", "checkin_date", name="uq_daily_checkins_user_date"),
    )

    id = Column(Uuid, primary_key=True, index=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    checkin_date = Column(Date, nullable=False, default=date.today)
    mood = Column(Integer, nullable=False)  # 1-10
    energy = Column(Integer, nullable=False)  # 1-10
    sleep_hours = Column(Float, nullable=True)
    daily_win = Column(String, nullable=True)
    blocker = Column(String, nullable=True)
    note = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
