"""Attendance database model for participant in-time and attendance tracking."""

from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database.database import Base


class Attendance(Base):
    """Database model for tracking meeting attendance and punctuality."""
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True)
    participant_id = Column(Integer, ForeignKey("participants.id", ondelete="SET NULL"), nullable=True)

    employee_name = Column(String(128), nullable=False)
    employee_id = Column(String(64), nullable=True)
    role = Column(String(128), nullable=True)

    join_time = Column(Float, nullable=False, default=0.0)  # In seconds from meeting start
    leave_time = Column(Float, nullable=False, default=0.0)  # In seconds from meeting start
    duration = Column(Float, nullable=False, default=0.0)  # Total attendance in seconds
    attendance_percentage = Column(Float, nullable=False, default=0.0)  # 0 to 100%

    late_duration = Column(Float, nullable=False, default=0.0)  # In seconds (late arrival)
    early_leave_duration = Column(Float, nullable=False, default=0.0)  # In seconds (early departure)

    first_transcript_time = Column(Float, nullable=True)  # First detected dialogue turn
    last_transcript_time = Column(Float, nullable=True)  # Last detected dialogue turn

    is_verified = Column(Boolean, default=False)  # True = Verified attendance, False = Estimated from transcript
    status = Column(String(64), default="On time")  # "On time", "Late", "Left early", "Late & Left early", "Partial attendance"

    # Relationships
    meeting = relationship("Meeting", back_populates="attendance_records")
    participant = relationship("Participant", back_populates="attendance")
