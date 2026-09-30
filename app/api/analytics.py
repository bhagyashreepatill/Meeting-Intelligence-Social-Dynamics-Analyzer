"""Analytics API router for social graph, replay engine, interactions, and temporal dynamics."""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models import (
    Meeting, Participant, TranscriptSegment, ActionItem, Idea,
    Decision, Topic, Interaction, Attendance, MeetingPlan, AgendaDrift, RecurringTopic
)
from app.schemas.schemas import (
    InteractionSchema, TopicCoverageResponse, RoleContributionsResponse,
    AgendaDriftResponse, AgendaDriftFeedbackRequest, ParticipationGapsResponse,
    RecurringTopicsResponse
)
from app.services.transcript_parser import ParsedSegment
from app.services.social_graph import SocialGraphService
from app.services.meeting_replay import MeetingReplayEngine
from app.services.speaker_analyzer import SpeakerAnalyzer
from app.services.topic_coverage_analyzer import topic_coverage_analyzer
from app.services.role_contribution_analyzer import role_contribution_analyzer
from app.services.agenda_drift_detector import agenda_drift_detector
from app.services.participation_gap_analyzer import participation_gap_analyzer
from app.services.recurring_topics_analyzer import recurring_topics_analyzer

router = APIRouter(prefix="/api/meetings/{meeting_id}", tags=["analytics"])
global_analytics_router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/interactions", response_model=List[InteractionSchema])
def get_interactions(meeting_id: int, db: Session = Depends(get_db)):
    """Get detected speaker interactions (interruptions, responses, overlaps)."""
    interactions = db.query(Interaction).filter(Interaction.meeting_id == meeting_id).all()
    return interactions


@router.get("/social-graph")
def get_social_graph(
    meeting_id: int,
    filter_type: Optional[str] = Query("all", description="all, interruptions, responses, direct_replies"),
    db: Session = Depends(get_db)
):
    """
    Generate interactive social graph with NetworkX metrics for Cytoscape.js visualization.
    Feature 7, 17, 23: Social Interaction & Flow Graph.
    """
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    participants = db.query(Participant).filter(Participant.meeting_id == meeting_id).all()
    segs = db.query(TranscriptSegment).filter(TranscriptSegment.meeting_id == meeting_id).order_by(TranscriptSegment.turn_number.asc()).all()
    interactions = db.query(Interaction).filter(Interaction.meeting_id == meeting_id).all()

    p_dict = {
        p.name: {
            "speaking_time": p.speaking_time,
            "speaking_percentage": p.speaking_percentage,
            "turn_count": p.turn_count,
            "interruptions_made": p.interruptions_made,
            "interruptions_received": p.interruptions_received,
            "avatar_color": p.avatar_color,
            "ideas_introduced": p.ideas_introduced
        }
        for p in participants
    }

    parsed_segs = [
        ParsedSegment(speaker=s.speaker_name, start_time=s.start_time, end_time=s.end_time, text=s.text, turn_number=s.turn_number)
        for s in segs
    ]

    interruptions = [
        {"speaker_a": i.speaker_a, "speaker_b": i.speaker_b, "confidence": i.confidence}
        for i in interactions if i.interaction_type == "INTERRUPTION"
    ]

    graph_service = SocialGraphService()
    graph_data = graph_service.build_graph(p_dict, parsed_segs, interruptions)

    # Filter edges if requested
    if filter_type and filter_type.lower() != "all":
        ft = filter_type.upper()
        graph_data["edges"] = [e for e in graph_data["edges"] if e["type"] == ft]

    return graph_data


@router.get("/replay")
def get_replay_state(
    meeting_id: int,
    t: Optional[float] = Query(0.0, description="Meeting timestamp in seconds"),
    db: Session = Depends(get_db)
):
    """
    Get meeting state snapshot and dynamic social graph at timestamp t.
    Feature 12: Meeting Dynamics Replay.
    """
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    participants = db.query(Participant).filter(Participant.meeting_id == meeting_id).all()
    segs = db.query(TranscriptSegment).filter(TranscriptSegment.meeting_id == meeting_id).order_by(TranscriptSegment.turn_number.asc()).all()
    ideas = db.query(Idea).filter(Idea.meeting_id == meeting_id).all()
    decisions = db.query(Decision).filter(Decision.meeting_id == meeting_id).all()
    actions = db.query(ActionItem).filter(ActionItem.meeting_id == meeting_id).all()
    topics = db.query(Topic).filter(Topic.meeting_id == meeting_id).all()
    interactions = db.query(Interaction).filter(Interaction.meeting_id == meeting_id).all()

    p_dict = {
        p.name: {
            "speaking_time": p.speaking_time,
            "speaking_percentage": p.speaking_percentage,
            "turn_count": p.turn_count,
            "avatar_color": p.avatar_color
        }
        for p in participants
    }

    parsed_segs = [
        ParsedSegment(speaker=s.speaker_name, start_time=s.start_time, end_time=s.end_time, text=s.text, turn_number=s.turn_number)
        for s in segs
    ]

    ideas_list = [
        {"id": i.id, "speaker": i.speaker, "text": i.text, "timestamp": i.timestamp}
        for i in ideas
    ]
    decisions_list = [
        {"id": d.id, "text": d.text, "timestamp": d.timestamp}
        for d in decisions
    ]
    actions_list = [
        {"task": a.task, "owner": a.owner, "timestamp": a.source_segment.start_time if a.source_segment else 0.0, "due_date": a.due_date}
        for a in actions
    ]
    topics_list = [
        {"name": top.name, "start_time": top.start_time, "end_time": top.end_time, "status": top.status}
        for top in topics
    ]
    interruptions = [
        {"speaker_a": i.speaker_a, "speaker_b": i.speaker_b, "timestamp": i.timestamp, "confidence": i.confidence}
        for i in interactions if i.interaction_type == "INTERRUPTION"
    ]

    engine = MeetingReplayEngine()
    state = engine.get_state_at_time(
        t=t,
        segments=parsed_segs,
        participants=p_dict,
        ideas=ideas_list,
        interruptions=interruptions,
        decisions=decisions_list,
        action_items=actions_list,
        topics=topics_list
    )

    # Attach keyframes for the slider
    keyframes = engine.get_keyframes(parsed_segs, ideas_list, interruptions, decisions_list, actions_list)
    state["keyframes"] = keyframes
    state["total_duration"] = meeting.duration

    return state


@router.get("/temporal-shifts")
def get_temporal_shifts(meeting_id: int, db: Session = Depends(get_db)):
    """
    Compare participation across Beginning (0-33%), Middle (33-66%), and End (66-100%).
    Feature 18: Participation Change Detection.
    """
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    segs = db.query(TranscriptSegment).filter(TranscriptSegment.meeting_id == meeting_id).order_by(TranscriptSegment.turn_number.asc()).all()
    parsed_segs = [
        ParsedSegment(speaker=s.speaker_name, start_time=s.start_time, end_time=s.end_time, text=s.text, turn_number=s.turn_number)
        for s in segs
    ]

    analyzer = SpeakerAnalyzer()
    res = analyzer.analyze(parsed_segs, total_duration=meeting.duration)
    return {
        "temporal_shifts": res["temporal_shifts"],
        "quartiles": res["quartiles"]
    }


@router.get("/health-timeline")
def get_health_timeline(meeting_id: int, db: Session = Depends(get_db)):
    """
    Empirical 10-minute interval observations on participation, turn cadence, and dynamics.
    Feature 13: Meeting Health Timeline.
    """
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    segs = db.query(TranscriptSegment).filter(TranscriptSegment.meeting_id == meeting_id).order_by(TranscriptSegment.turn_number.asc()).all()
    parsed_segs = [
        ParsedSegment(speaker=s.speaker_name, start_time=s.start_time, end_time=s.end_time, text=s.text, turn_number=s.turn_number)
        for s in segs
    ]

    analyzer = SpeakerAnalyzer()
    res = analyzer.analyze(parsed_segs, total_duration=meeting.duration)
    return res["health_timeline"]


# =============================================================
# Feature 3: Role-Based Expected Contribution
# =============================================================
@router.get("/role-contributions", response_model=RoleContributionsResponse)
def get_role_contributions(meeting_id: int, db: Session = Depends(get_db)):
    """
    Evaluate expected vs actual participant contribution across topics and dialogue cadence.
    Feature 3: Role-Based Expected Contribution.
    """
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    participants = db.query(Participant).filter(Participant.meeting_id == meeting_id).all()
    segments = db.query(TranscriptSegment).filter(TranscriptSegment.meeting_id == meeting_id).order_by(TranscriptSegment.turn_number.asc()).all()
    topics = db.query(Topic).filter(Topic.meeting_id == meeting_id).all()
    ideas = db.query(Idea).filter(Idea.meeting_id == meeting_id).all()
    decisions = db.query(Decision).filter(Decision.meeting_id == meeting_id).all()
    action_items = db.query(ActionItem).filter(ActionItem.meeting_id == meeting_id).all()
    plan = db.query(MeetingPlan).filter(MeetingPlan.meeting_id == meeting_id).first()

    contributions = role_contribution_analyzer.analyze_contributions(
        meeting=meeting,
        participants=participants,
        segments=segments,
        topics=topics,
        ideas=ideas,
        decisions=decisions,
        action_items=action_items,
        plan=plan
    )

    return RoleContributionsResponse(
        meeting_id=meeting_id,
        contributions=contributions
    )


# =============================================================
# Feature 4: Meeting Topic Coverage Score
# =============================================================
@router.get("/topic-coverage", response_model=TopicCoverageResponse)
def get_topic_coverage(meeting_id: int, db: Session = Depends(get_db)):
    """
    Compare planned expected topics against actual transcript dialogue topics.
    Feature 4: Meeting Topic Coverage Score.
    """
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    topics = db.query(Topic).filter(Topic.meeting_id == meeting_id).all()
    segments = db.query(TranscriptSegment).filter(TranscriptSegment.meeting_id == meeting_id).order_by(TranscriptSegment.turn_number.asc()).all()
    decisions = db.query(Decision).filter(Decision.meeting_id == meeting_id).all()
    action_items = db.query(ActionItem).filter(ActionItem.meeting_id == meeting_id).all()
    plan = db.query(MeetingPlan).filter(MeetingPlan.meeting_id == meeting_id).first()

    coverage = topic_coverage_analyzer.analyze_coverage(
        meeting=meeting,
        topics=topics,
        segments=segments,
        decisions=decisions,
        action_items=action_items,
        plan=plan
    )
    return TopicCoverageResponse(**coverage)


@router.get("/expected-topics")
def get_expected_topics(meeting_id: int, db: Session = Depends(get_db)):
    """Get raw list of expected topics configured for the meeting."""
    plan = db.query(MeetingPlan).filter(MeetingPlan.meeting_id == meeting_id).first()
    if plan and plan.expected_topics:
        import json
        try:
            return json.loads(plan.expected_topics)
        except Exception:
            pass
    return topic_coverage_analyzer.DEFAULT_EXPECTED_TOPICS


# =============================================================
# Feature 5: Agenda Drift Detector
# =============================================================
@router.get("/agenda-drift", response_model=AgendaDriftResponse)
def get_agenda_drift(meeting_id: int, db: Session = Depends(get_db)):
    """
    Detect conversational deviations away from the planned meeting agenda.
    Feature 5: Agenda Drift Detector.
    """
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    segments = db.query(TranscriptSegment).filter(TranscriptSegment.meeting_id == meeting_id).order_by(TranscriptSegment.turn_number.asc()).all()
    plan = db.query(MeetingPlan).filter(MeetingPlan.meeting_id == meeting_id).first()
    existing_drifts = db.query(AgendaDrift).filter(AgendaDrift.meeting_id == meeting_id).all()

    drift_data = agenda_drift_detector.detect_drifts(
        meeting=meeting,
        segments=segments,
        plan=plan,
        existing_drifts=existing_drifts
    )
    return AgendaDriftResponse(**drift_data)


@router.post("/agenda-drift/{drift_id}/feedback")
def submit_drift_feedback(
    meeting_id: int,
    drift_id: int,
    payload: AgendaDriftFeedbackRequest,
    db: Session = Depends(get_db)
):
    """
    Record human feedback confirming or disputing a detected agenda drift.
    """
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    fb = payload.feedback.lower().strip()
    if fb not in ["confirmed_drift", "not_drift"]:
        raise HTTPException(status_code=400, detail="Feedback must be 'confirmed_drift' or 'not_drift'")

    drift = db.query(AgendaDrift).filter(
        AgendaDrift.id == drift_id,
        AgendaDrift.meeting_id == meeting_id
    ).first()

    if drift:
        drift.feedback_status = fb
        db.commit()
        db.refresh(drift)
    else:
        # If drift was computed in-memory, persist it with user feedback
        segments = db.query(TranscriptSegment).filter(TranscriptSegment.meeting_id == meeting_id).all()
        drift_data = agenda_drift_detector.detect_drifts(meeting, segments)
        matched_item = next((d for d in drift_data["drifts"] if d["id"] == drift_id), None)
        if matched_item:
            drift = AgendaDrift(
                meeting_id=meeting_id,
                start_time=matched_item["start_time"],
                end_time=matched_item["end_time"],
                duration=matched_item["duration"],
                percentage=matched_item["percentage"],
                detected_topic=matched_item["detected_topic"],
                expected_topic=matched_item["expected_topic"],
                category=matched_item["category"],
                confidence=matched_item["confidence"],
                excerpt=matched_item["excerpt"],
                feedback_status=fb
            )
            db.add(drift)
            db.commit()
            db.refresh(drift)

    return {"status": "success", "drift_id": drift_id, "feedback": fb}


# =============================================================
# Feature 6: Silent Participant / Participation Gap
# =============================================================
@router.get("/participation-gaps", response_model=ParticipationGapsResponse)
def get_participation_gaps(meeting_id: int, db: Session = Depends(get_db)):
    """
    Identify participants with low observed participation relative to meeting distribution.
    Feature 6: Silent Participant / Participation Gap.
    """
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    participants = db.query(Participant).filter(Participant.meeting_id == meeting_id).all()
    segments = db.query(TranscriptSegment).filter(TranscriptSegment.meeting_id == meeting_id).order_by(TranscriptSegment.turn_number.asc()).all()
    attendance_records = db.query(Attendance).filter(Attendance.meeting_id == meeting_id).all()
    topics = db.query(Topic).filter(Topic.meeting_id == meeting_id).all()
    ideas = db.query(Idea).filter(Idea.meeting_id == meeting_id).all()
    action_items = db.query(ActionItem).filter(ActionItem.meeting_id == meeting_id).all()

    gaps_data = participation_gap_analyzer.analyze_gaps(
        meeting=meeting,
        participants=participants,
        segments=segments,
        attendance_records=attendance_records,
        topics=topics,
        ideas=ideas,
        action_items=action_items
    )
    return ParticipationGapsResponse(**gaps_data)


# =============================================================
# Feature 7: Recurring Topics (Per-Meeting & Global)
# =============================================================
@router.get("/recurring-topics", response_model=RecurringTopicsResponse)
def get_meeting_recurring_topics(meeting_id: int, db: Session = Depends(get_db)):
    """
    Retrieve recurring topics affecting this specific meeting.
    Feature 7: Repeated Discussion Detector.
    """
    res = recurring_topics_analyzer.get_meeting_recurring_topics(meeting_id, db)
    return RecurringTopicsResponse(
        total_recurring_topics=res["total_recurring_topics"],
        unresolved_count=sum(1 for t in res["topics"] if "unresolved" in t["status"].lower()),
        resolved_count=sum(1 for t in res["topics"] if "resolved" in t["status"].lower()),
        topics=res["topics"]
    )


@global_analytics_router.get("/recurring-topics", response_model=RecurringTopicsResponse)
def get_global_recurring_topics(
    status: Optional[str] = Query("all", description="all, unresolved, repeated, resolved"),
    db: Session = Depends(get_db)
):
    """
    Cross-meeting historical recurring topics across entire organization.
    Feature 7: Repeated Discussion Detector.
    """
    res = recurring_topics_analyzer.analyze_all_recurring_topics(db, filter_status=status)
    return RecurringTopicsResponse(**res)

