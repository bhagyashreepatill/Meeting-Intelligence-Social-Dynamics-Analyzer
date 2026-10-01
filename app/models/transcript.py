"""Transcript segment database model."""

from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database.database import Base


class TranscriptSegment(Base):
    """Database model for a single transcript segment or turn."""
    __tablename__ = "transcript_segments"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True)
    participant_id = Column(Integer, ForeignKey("participants.id", ondelete="SET NULL"), nullable=True, index=True)
    speaker_name = Column(String(128), nullable=False)
    start_time = Column(Float, nullable=False, index=True)  # Seconds from start
    end_time = Column(Float, nullable=False)  # Seconds from start
    text = Column(Text, nullable=False)
    turn_number = Column(Integer, nullable=False, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    meeting = relationship("Meeting", back_populates="transcript_segments")
    participant = relationship("Participant", back_populates="segments")
    topic = relationship("Topic", back_populates="segments")
