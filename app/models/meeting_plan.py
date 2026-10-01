"""Meeting plan database model for pre-meeting agenda and expectations."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database.database import Base


class MeetingPlan(Base):
    """Database model for pre-meeting AI-generated or user-defined meeting plan."""
    __tablename__ = "meeting_plans"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=True, index=True)

    topic = Column(String(255), nullable=False)
    objective = Column(Text, nullable=True)
    duration_minutes = Column(Integer, default=45)
    department = Column(String(128), nullable=True)
    meeting_type = Column(String(128), default="Sprint Planning")
    industry_context = Column(Text, nullable=True)

    # JSON-encoded structures
    suggested_agenda = Column(Text, nullable=True)  # List of agenda items with timing
    expected_topics = Column(Text, nullable=True)  # List of expected topics
    expected_questions = Column(Text, nullable=True)  # List of expected questions
    expected_decisions = Column(Text, nullable=True)  # List of expected decisions
    expected_action_areas = Column(Text, nullable=True)  # List of expected action domains
    role_expectations = Column(Text, nullable=True)  # List of participant role expectations

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    meeting = relationship("Meeting", back_populates="meeting_plan")
