"""Agenda drift database model for off-topic deviations."""

from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database.database import Base


class AgendaDrift(Base):
    """Database model for detected deviations from scheduled agenda."""
    __tablename__ = "agenda_drifts"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True)

    start_time = Column(Float, nullable=False)  # In seconds from meeting start
    end_time = Column(Float, nullable=False)  # In seconds from meeting start
    duration = Column(Float, nullable=False)  # In seconds
    percentage = Column(Float, nullable=False)  # Percentage of total meeting

    detected_topic = Column(String(255), nullable=False)
    expected_topic = Column(String(255), nullable=False)
    category = Column(String(64), default="Minor Drift")  # Minor Drift, Moderate Drift, Significant Drift
    confidence = Column(Float, default=0.85)

    excerpt = Column(Text, nullable=True)
    feedback_status = Column(String(64), default="unreviewed")  # "unreviewed", "confirmed_drift", "not_drift"

    # Relationships
    meeting = relationship("Meeting", back_populates="agenda_drifts")
