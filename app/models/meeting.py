"""Meeting database model."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import relationship
from app.database.database import Base


class Meeting(Base):
    """Database model for a processed meeting transcript."""
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, default="Untitled Meeting")
    date = Column(String(64), nullable=True)
    duration = Column(Float, nullable=False, default=0.0)  # In seconds
    transcript_filename = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(32), default="processed")
    summary = Column(Text, nullable=True)

    # Relationships
    participants = relationship("Participant", back_populates="meeting", cascade="all, delete-orphan")
    transcript_segments = relationship("TranscriptSegment", back_populates="meeting", cascade="all, delete-orphan")
    action_items = relationship("ActionItem", back_populates="meeting", cascade="all, delete-orphan")
    ideas = relationship("Idea", back_populates="meeting", cascade="all, delete-orphan")
    decisions = relationship("Decision", back_populates="meeting", cascade="all, delete-orphan")
    topics = relationship("Topic", back_populates="meeting", cascade="all, delete-orphan")
    interactions = relationship("Interaction", back_populates="meeting", cascade="all, delete-orphan")
    attendance_records = relationship("Attendance", back_populates="meeting", cascade="all, delete-orphan")
    meeting_plan = relationship("MeetingPlan", back_populates="meeting", uselist=False, cascade="all, delete-orphan")
    agenda_drifts = relationship("AgendaDrift", back_populates="meeting", cascade="all, delete-orphan")
