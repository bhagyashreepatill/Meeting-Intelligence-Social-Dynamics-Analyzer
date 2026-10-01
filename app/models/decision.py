"""Decision database model."""

from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database.database import Base


class Decision(Base):
    """Database model for a consensus decision reached in a meeting."""
    __tablename__ = "decisions"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True)
    text = Column(Text, nullable=False)
    timestamp = Column(Float, nullable=False)
    confidence = Column(Float, default=0.90)
    participants_involved = Column(String(255), nullable=True)  # Comma-separated names
    related_idea_id = Column(Integer, ForeignKey("ideas.id", ondelete="SET NULL"), nullable=True)
    source_segment_id = Column(Integer, ForeignKey("transcript_segments.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    meeting = relationship("Meeting", back_populates="decisions")
    related_idea = relationship("Idea", back_populates="decisions")
    source_segment = relationship("TranscriptSegment")
