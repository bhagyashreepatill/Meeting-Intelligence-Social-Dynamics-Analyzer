"""Participant database model."""

from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.database.database import Base


class Participant(Base):
    """Database model for a participant in a meeting."""
    __tablename__ = "participants"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    avatar_color = Column(String(32), default="#4f46e5")
    
    # Participation metrics
    speaking_time = Column(Float, default=0.0)  # In seconds
    speaking_percentage = Column(Float, default=0.0)  # 0 to 100
    turn_count = Column(Integer, default=0)
    avg_turn_length = Column(Float, default=0.0)
    median_turn_length = Column(Float, default=0.0)
    longest_turn = Column(Float, default=0.0)
    shortest_turn = Column(Float, default=0.0)
    turn_std_dev = Column(Float, default=0.0)
    
    # Interaction metrics
    interruptions_made = Column(Integer, default=0)
    interruptions_received = Column(Integer, default=0)
    responses_count = Column(Integer, default=0)
    ideas_introduced = Column(Integer, default=0)
    actions_assigned = Column(Integer, default=0)

    # Employee metadata
    employee_id = Column(String(64), nullable=True)
    role = Column(String(128), nullable=True)
    department = Column(String(128), nullable=True)
    responsibilities = Column(String(512), nullable=True)

    # Relationships
    meeting = relationship("Meeting", back_populates="participants")
    segments = relationship("TranscriptSegment", back_populates="participant")
    attendance = relationship("Attendance", back_populates="participant", uselist=False, cascade="all, delete-orphan")
