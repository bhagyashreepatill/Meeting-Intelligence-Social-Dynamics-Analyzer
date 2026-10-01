"""Recurring topic database model for historical cross-meeting analysis."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database.database import Base


class RecurringTopic(Base):
    """Database model for recurring topics tracked across multiple meetings."""
    __tablename__ = "recurring_topics"

    id = Column(Integer, primary_key=True, index=True)
    canonical_name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    status = Column(String(64), default="Unresolved")  # "Unresolved", "Recurring", "Resolved"
    latest_decision = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    occurrences = relationship("RecurringTopicOccurrence", back_populates="recurring_topic", cascade="all, delete-orphan")


class RecurringTopicOccurrence(Base):
    """Occurrence of a recurring topic in a specific meeting."""
    __tablename__ = "recurring_topic_occurrences"

    id = Column(Integer, primary_key=True, index=True)
    recurring_topic_id = Column(Integer, ForeignKey("recurring_topics.id", ondelete="CASCADE"), nullable=False, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True)

    topic_title = Column(String(255), nullable=False)
    timestamp = Column(Float, default=0.0)  # Timestamp in seconds within the meeting
    status = Column(String(64), default="Unresolved")  # Resolved, Unresolved, Partially Resolved
    decision_text = Column(Text, nullable=True)
    excerpt = Column(Text, nullable=True)
    speakers = Column(String(255), nullable=True)

    # Relationships
    recurring_topic = relationship("RecurringTopic", back_populates="occurrences")
    meeting = relationship("Meeting")
