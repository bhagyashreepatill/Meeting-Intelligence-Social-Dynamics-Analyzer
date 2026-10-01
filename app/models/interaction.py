"""Interaction database model."""

from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database.database import Base


class Interaction(Base):
    """Database model for an interaction (interruption, response, reply, overlap) between two speakers."""
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True)
    speaker_a = Column(String(128), nullable=False)  # Initiator (e.g. Interrupter or Responder)
    speaker_b = Column(String(128), nullable=False)  # Target (e.g. Interrupted speaker or Addressee)
    interaction_type = Column(String(64), nullable=False)  # "INTERRUPTION", "RESPONSE", "DIRECT_REPLY", "IDEA_OVERLAP"
    timestamp = Column(Float, nullable=False)
    confidence = Column(Float, default=0.80)
    evidence = Column(Text, nullable=True)
    source_segment_id = Column(Integer, ForeignKey("transcript_segments.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    meeting = relationship("Meeting", back_populates="interactions")
    source_segment = relationship("TranscriptSegment")
