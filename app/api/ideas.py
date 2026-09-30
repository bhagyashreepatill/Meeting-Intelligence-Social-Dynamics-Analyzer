"""Ideas, Idea Journeys, Attribution Shifts, Decisions, and Topics API router."""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models import Meeting, Idea, IdeaRelation, Decision, Topic, TranscriptSegment, ActionItem
from app.schemas.schemas import IdeaSchema, DecisionSchema, TopicSchema
from app.services.transcript_parser import ParsedSegment
from app.services.idea_detector import IdeaDetector
from app.services.idea_provenance import IdeaProvenanceTracker

router = APIRouter(prefix="/api/meetings/{meeting_id}", tags=["ideas_decisions_topics"])


@router.get("/ideas", response_model=Dict[str, Any])
def get_meeting_ideas(meeting_id: int, db: Session = Depends(get_db)):
    """Get ideas and detected semantic overlaps for a meeting."""
    ideas = db.query(Idea).filter(Idea.meeting_id == meeting_id).all()
    relations = db.query(IdeaRelation).filter(IdeaRelation.meeting_id == meeting_id).all()

    return {
        "ideas": [
            {
                "id": i.id,
                "speaker": i.speaker,
                "text": i.text,
                "timestamp": i.timestamp,
                "time_display": f"{int(i.timestamp // 60):02d}:{int(i.timestamp % 60):02d}",
                "confidence": i.confidence,
                "lifecycle_stage": i.lifecycle_stage,
                "source_segment_id": i.source_segment_id
            }
            for i in ideas
        ],
        "relations": [
            {
                "id": r.id,
                "idea_a_id": r.idea_a_id,
                "idea_b_id": r.idea_b_id,
                "similarity_score": r.similarity_score,
                "similarity_percentage": round(r.similarity_score * 100, 1),
                "time_difference": r.time_difference,
                "relation_type": r.relation_type,
                "details": r.details
            }
            for r in relations
        ]
    }


@router.get("/idea-journeys", response_model=List[Dict[str, Any]])
def get_idea_journeys(meeting_id: int, db: Session = Depends(get_db)):
    """
    Get synthesized end-to-end Idea Journeys from introduction to action item.
    Feature 10: Idea Provenance / Idea Journey.
    """
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    ideas_db = db.query(Idea).filter(Idea.meeting_id == meeting_id).all()
    segs_db = db.query(TranscriptSegment).filter(TranscriptSegment.meeting_id == meeting_id).order_by(TranscriptSegment.turn_number.asc()).all()
    decisions_db = db.query(Decision).filter(Decision.meeting_id == meeting_id).all()
    actions_db = db.query(ActionItem).filter(ActionItem.meeting_id == meeting_id).all()

    # Convert to service format
    ideas_list = [
        {"id": i.id, "speaker": i.speaker, "text": i.text, "timestamp": i.timestamp, "full_quote": i.text}
        for i in ideas_db
    ]
    parsed_segs = [
        ParsedSegment(speaker=s.speaker_name, start_time=s.start_time, end_time=s.end_time, text=s.text, turn_number=s.turn_number)
        for s in segs_db
    ]
    decisions_list = [
        {"id": d.id, "text": d.text, "timestamp": d.timestamp}
        for d in decisions_db
    ]
    actions_list = [
        {"id": a.id, "task": a.task, "owner": a.owner, "due_date": a.due_date, "timestamp": a.source_segment.start_time if a.source_segment else 0.0, "evidence": a.evidence or a.task}
        for a in actions_db
    ]

    detector = IdeaDetector()
    overlaps = detector.detect_overlaps(ideas_list, similarity_threshold=0.50)

    tracker = IdeaProvenanceTracker()
    journeys = tracker.build_idea_journeys(ideas_list, parsed_segs, overlaps, decisions_list, actions_list)
    return journeys


@router.get("/attribution-shifts", response_model=List[Dict[str, Any]])
def get_attribution_shifts(meeting_id: int, db: Session = Depends(get_db)):
    """
    Get detected Potential Attribution Shifts with evidence and neutral framing.
    Feature 11: Potential Attribution Shift.
    """
    ideas_db = db.query(Idea).filter(Idea.meeting_id == meeting_id).all()
    segs_db = db.query(TranscriptSegment).filter(TranscriptSegment.meeting_id == meeting_id).order_by(TranscriptSegment.turn_number.asc()).all()

    ideas_list = [
        {"id": i.id, "speaker": i.speaker, "text": i.text, "timestamp": i.timestamp, "full_quote": i.text}
        for i in ideas_db
    ]
    parsed_segs = [
        ParsedSegment(speaker=s.speaker_name, start_time=s.start_time, end_time=s.end_time, text=s.text, turn_number=s.turn_number)
        for s in segs_db
    ]

    detector = IdeaDetector()
    overlaps = detector.detect_overlaps(ideas_list, similarity_threshold=0.50)

    tracker = IdeaProvenanceTracker()
    shifts = tracker.detect_attribution_shifts(overlaps, parsed_segs)
    return shifts


@router.get("/decisions", response_model=List[DecisionSchema])
def get_meeting_decisions(meeting_id: int, db: Session = Depends(get_db)):
    """List all consensus decisions detected in the meeting."""
    decisions = db.query(Decision).filter(Decision.meeting_id == meeting_id).all()
    return decisions


@router.get("/topics", response_model=List[TopicSchema])
def get_meeting_topics(meeting_id: int, db: Session = Depends(get_db)):
    """List chronological topics and resolution statuses."""
    topics = db.query(Topic).filter(Topic.meeting_id == meeting_id).order_by(Topic.start_time.asc()).all()
    return topics
