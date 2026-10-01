"""Topic database model."""

from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database.database import Base


class Topic(Base):
    """Database model for a discussion topic within a meeting."""
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    status = Column(String(32), default="Resolved")  # "Resolved", "Partially Resolved", "Unresolved"
    evidence = Column(Text, nullable=True)

    # Relationships
    meeting = relationship("Meeting", back_populates="topics")
    segments = relationship("TranscriptSegment", back_populates="topic")
