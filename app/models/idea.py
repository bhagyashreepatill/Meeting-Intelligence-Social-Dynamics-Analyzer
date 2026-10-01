"""Idea and IdeaRelation database models."""

from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database.database import Base


class Idea(Base):
    """Database model for a proposed idea in a meeting."""
    __tablename__ = "ideas"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True)
    speaker = Column(String(128), nullable=False)
    text = Column(Text, nullable=False)
    timestamp = Column(Float, nullable=False)
    confidence = Column(Float, default=0.85)
    lifecycle_stage = Column(String(64), default="Introduced")  # "Introduced", "Discussed", "Converged", "Decided", "Actioned"
    source_segment_id = Column(Integer, ForeignKey("transcript_segments.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    meeting = relationship("Meeting", back_populates="ideas")
    source_segment = relationship("TranscriptSegment")
    decisions = relationship("Decision", back_populates="related_idea")


class IdeaRelation(Base):
    """Database model for relationship/similarity between two ideas."""
    __tablename__ = "idea_relations"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True)
    idea_a_id = Column(Integer, ForeignKey("ideas.id", ondelete="CASCADE"), nullable=False)
    idea_b_id = Column(Integer, ForeignKey("ideas.id", ondelete="CASCADE"), nullable=False)
    similarity_score = Column(Float, nullable=False)  # 0.0 to 1.0
    time_difference = Column(Float, nullable=False)  # In seconds
    relation_type = Column(String(64), default="OVERLAP")  # "OVERLAP", "EXPANSION", "ATTRIBUTION_SHIFT"
    details = Column(Text, nullable=True)

    # Relationships
    idea_a = relationship("Idea", foreign_keys=[idea_a_id])
    idea_b = relationship("Idea", foreign_keys=[idea_b_id])
