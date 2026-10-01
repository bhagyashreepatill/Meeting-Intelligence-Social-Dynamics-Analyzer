"""Action item database model."""

from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database.database import Base


class ActionItem(Base):
    """Database model for extracted action items with complete lifecycle tracking."""
    __tablename__ = "action_items"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True)
    task = Column(Text, nullable=False)
    owner = Column(String(128), default="Unknown")
    due_date = Column(String(64), default="Unknown")
    priority = Column(String(32), default="Medium")  # "High", "Medium", "Low"
    source_segment_id = Column(Integer, ForeignKey("transcript_segments.id", ondelete="SET NULL"), nullable=True)
    confidence = Column(Float, default=0.85)
    
    # Lifecycle status: "Detected", "Confirmed", "Assigned", "In Progress", "Completed", "Overdue", "Rejected"
    status = Column(String(32), default="Detected", index=True)
    evidence = Column(Text, nullable=True)
    external_reference = Column(String(255), nullable=True)  # Slack ts, Jira key, Trello card id

    # Relationships
    meeting = relationship("Meeting", back_populates="action_items")
    source_segment = relationship("TranscriptSegment")
