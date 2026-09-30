"""Meetings API router for uploads, seeding demo data, exports, and comparisons."""

import os
import json
import csv
import io
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models import (
    Meeting, Participant, TranscriptSegment, ActionItem, Idea,
    IdeaRelation, Decision, Topic, Interaction, Attendance, MeetingPlan, AgendaDrift, RecurringTopic
)
from app.schemas.schemas import MeetingSummarySchema, MeetingDetailSchema, TranscriptSegmentSchema, ParticipantSchema
from app.services.transcript_parser import TranscriptParser
from app.services.action_extractor import ActionItemExtractor
from app.services.speaker_analyzer import SpeakerAnalyzer
from app.services.interruption_detector import InterruptionDetector
from app.services.idea_detector import IdeaDetector
from app.services.idea_provenance import IdeaProvenanceTracker
from app.services.decision_detector import DecisionDetector
from app.services.topic_detector import TopicDetector
from app.services.attendance_analyzer import AttendanceAnalyzer
from app.services.meeting_planner import meeting_planner
from app.services.role_contribution_analyzer import role_contribution_analyzer
from app.services.topic_coverage_analyzer import topic_coverage_analyzer
from app.services.agenda_drift_detector import agenda_drift_detector
from app.services.participation_gap_analyzer import participation_gap_analyzer
from app.services.recurring_topics_analyzer import recurring_topics_analyzer
from app.utils.logging import logger

router = APIRouter(prefix="/api/meetings", tags=["meetings"])


def process_and_save_transcript(
    title: str,
    raw_text: str,
    filename: str,
    db: Session
) -> Meeting:
    """End-to-end analytical pipeline: parses transcript, executes all analyzers, and persists results."""
    # 1. Parse transcript
    parser = TranscriptParser()
    parsed = parser.parse(raw_text)

    if not parsed.segments:
        raise HTTPException(status_code=400, detail="Unable to extract any valid dialogue turns from transcript.")

    # 2. Extract Participation & Turn Analytics
    analyzer = SpeakerAnalyzer()
    speaker_data = analyzer.analyze(parsed.segments, total_duration=parsed.duration)

    # 3. Interruption Detection
    interruption_detector = InterruptionDetector()
    interruptions = interruption_detector.detect_interruptions(parsed.segments)

    # Update interruption counters on participants
    for intr in interruptions:
        src = intr["speaker_a"]
        tgt = intr["speaker_b"]
        if src in speaker_data["participants"]:
            speaker_data["participants"][src]["interruptions_made"] += 1
        if tgt in speaker_data["participants"]:
            speaker_data["participants"][tgt]["interruptions_received"] += 1

    # 4. Action Item Extraction
    action_extractor = ActionItemExtractor(known_participants=parsed.participants)
    action_items_data = action_extractor.extract(parsed.segments)

    # Update action counters on participants
    for act in action_items_data:
        owner = act["owner"]
        if owner in speaker_data["participants"]:
            speaker_data["participants"][owner]["actions_assigned"] += 1

    # 5. Idea Detection & Overlaps
    idea_detector = IdeaDetector()
    ideas_data = idea_detector.extract_ideas(parsed.segments)
    overlaps_data = idea_detector.detect_overlaps(ideas_data, similarity_threshold=0.50)

    for id_item in ideas_data:
        sp = id_item["speaker"]
        if sp in speaker_data["participants"]:
            speaker_data["participants"][sp]["ideas_introduced"] += 1

    # 6. Decision Detection
    decision_detector = DecisionDetector()
    decisions_data = decision_detector.detect_decisions(parsed.segments, ideas=ideas_data)

    # 7. Topic Segmentation & Unresolved Topics
    topic_detector = TopicDetector()
    topics_data = topic_detector.segment_topics(
        parsed.segments,
        decisions=decisions_data,
        action_items=action_items_data
    )

    # 8. Persist to Database
    now_utc = datetime.now(timezone.utc)
    meeting = Meeting(
        title=title,
        date=now_utc.strftime("%Y-%m-%d"),
        duration=parsed.duration,
        transcript_filename=filename,
        created_at=now_utc,
        status="processed",
        summary=f"Meeting with {len(parsed.participants)} participants, {len(action_items_data)} action items, and {len(decisions_data)} decisions."
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)

    # Save Participants
    participant_id_map: Dict[str, int] = {}
    for sp_name, data in speaker_data["participants"].items():
        p = Participant(
            meeting_id=meeting.id,
            name=sp_name,
            avatar_color=data.get("avatar_color", "#4f46e5"),
            speaking_time=data.get("speaking_time", 0.0),
            speaking_percentage=data.get("speaking_percentage", 0.0),
            turn_count=data.get("turn_count", 0),
            avg_turn_length=data.get("avg_turn_length", 0.0),
            median_turn_length=data.get("median_turn_length", 0.0),
            longest_turn=data.get("longest_turn", 0.0),
            shortest_turn=data.get("shortest_turn", 0.0),
            turn_std_dev=data.get("turn_std_dev", 0.0),
            interruptions_made=data.get("interruptions_made", 0),
            interruptions_received=data.get("interruptions_received", 0),
            responses_count=data.get("responses_count", 0),
            ideas_introduced=data.get("ideas_introduced", 0),
            actions_assigned=data.get("actions_assigned", 0)
        )
        db.add(p)
        db.commit()
        db.refresh(p)
        participant_id_map[sp_name] = p.id

    # Save Topics
    topic_id_map: Dict[int, int] = {}
    for top in topics_data:
        t = Topic(
            meeting_id=meeting.id,
            name=top["name"],
            start_time=top["start_time"],
            end_time=top["end_time"],
            status=top["status"],
            evidence=top.get("evidence", "")
        )
        db.add(t)
        db.commit()
        db.refresh(t)
        topic_id_map[top["id"]] = t.id

    # Save Transcript Segments
    for seg in parsed.segments:
        # Match topic
        matched_topic_id = None
        for top in topics_data:
            if seg.turn_number in top.get("segment_ids", []):
                matched_topic_id = topic_id_map.get(top["id"])
                break

        ts = TranscriptSegment(
            meeting_id=meeting.id,
            participant_id=participant_id_map.get(seg.speaker),
            speaker_name=seg.speaker,
            start_time=seg.start_time,
            end_time=seg.end_time,
            text=seg.text,
            turn_number=seg.turn_number,
            topic_id=matched_topic_id
        )
        db.add(ts)
    db.commit()

    # Save Action Items
    for act in action_items_data:
        ai = ActionItem(
            meeting_id=meeting.id,
            task=act["task"],
            owner=act["owner"],
            due_date=act["due_date"],
            priority=act["priority"],
            source_segment_id=act.get("source_segment_id"),
            confidence=act["confidence"],
            status="Detected",
            evidence=act.get("evidence", "")
        )
        db.add(ai)

    # Save Ideas & Relations
    idea_db_map: Dict[int, int] = {}
    for id_item in ideas_data:
        idea_row = Idea(
            meeting_id=meeting.id,
            speaker=id_item["speaker"],
            text=id_item["text"],
            timestamp=id_item["timestamp"],
            confidence=id_item["confidence"],
            lifecycle_stage="Introduced",
            source_segment_id=id_item.get("source_segment_id")
        )
        db.add(idea_row)
        db.commit()
        db.refresh(idea_row)
        idea_db_map[id_item["id"]] = idea_row.id

    for ov in overlaps_data:
        a_id = idea_db_map.get(ov["idea_a_id"])
        b_id = idea_db_map.get(ov["idea_b_id"])
        if a_id and b_id:
            rel = IdeaRelation(
                meeting_id=meeting.id,
                idea_a_id=a_id,
                idea_b_id=b_id,
                similarity_score=ov["similarity"],
                time_difference=ov["time_difference"],
                relation_type="OVERLAP",
                details=f"{ov['speaker_a']} and {ov['speaker_b']} shared {ov['similarity_percentage']}% similar idea"
            )
            db.add(rel)

    # Save Decisions
    for dec in decisions_data:
        d = Decision(
            meeting_id=meeting.id,
            text=dec["text"],
            timestamp=dec["timestamp"],
            confidence=dec["confidence"],
            participants_involved=",".join(dec["participants_involved"]),
            related_idea_id=idea_db_map.get(dec.get("related_idea_id")),
            source_segment_id=dec.get("source_segment_id")
        )
        db.add(d)

    # Save Interactions (Interruptions & Overlaps)
    for intr in interruptions:
        interaction = Interaction(
            meeting_id=meeting.id,
            speaker_a=intr["speaker_a"],
            speaker_b=intr["speaker_b"],
            interaction_type="INTERRUPTION",
            timestamp=intr["timestamp"],
            confidence=intr["confidence"],
            evidence=intr.get("evidence", ""),
            source_segment_id=intr.get("source_segment_id")
        )
        db.add(interaction)

    db.commit()
    db.refresh(meeting)
    return meeting


def _seed_historical_q3_meeting(db: Session) -> Meeting:
    """Seed prior historical meeting for demonstrating cross-meeting recurring topics."""
    hist = db.query(Meeting).filter(Meeting.title == "Q3 Retrospective & Architecture Review").first()
    if hist:
        return hist

    now_utc = datetime.now(timezone.utc)
    m = Meeting(
        title="Q3 Retrospective & Architecture Review",
        date="2026-09-15",
        duration=1800.0,  # 30 minutes
        transcript_filename="q3_retro.txt",
        created_at=now_utc,
        status="processed",
        summary="Historical retrospective covering API response times, latency, and database bottlenecks."
    )
    db.add(m)
    db.commit()
    db.refresh(m)

    # Participants
    p_alice = Participant(meeting_id=m.id, name="Alice", role="Project Manager", employee_id="EMP-101", speaking_time=620.0, speaking_percentage=34.4, turn_count=12)
    p_charlie = Participant(meeting_id=m.id, name="Charlie", role="Backend Developer", employee_id="EMP-103", speaking_time=740.0, speaking_percentage=41.1, turn_count=14)
    p_bob = Participant(meeting_id=m.id, name="Bob", role="Data Scientist", employee_id="EMP-102", speaking_time=440.0, speaking_percentage=24.5, turn_count=8)
    db.add_all([p_alice, p_charlie, p_bob])
    db.commit()

    # Topics
    t1 = Topic(
        meeting_id=m.id,
        name="API Error Handling & Performance",
        start_time=120.0,
        end_time=900.0,
        status="Unresolved",
        evidence="Alice: 'API error handling remains unresolved. Latency is high, but we didn't reach consensus on whether to rewrite or cache.'"
    )
    t2 = Topic(
        meeting_id=m.id,
        name="Database Concurrency Bottlenecks",
        start_time=900.0,
        end_time=1700.0,
        status="Resolved",
        evidence="Decided: Team will investigate PostgreSQL to replace SQLite in staging"
    )
    db.add_all([t1, t2])

    # Transcript segments
    db.add(TranscriptSegment(meeting_id=m.id, speaker_name="Alice", start_time=120.0, end_time=180.0, turn_number=1, text="We are hitting high error rates and latency on our API endpoints during peak load."))
    db.add(TranscriptSegment(meeting_id=m.id, speaker_name="Charlie", start_time=185.0, end_time=260.0, turn_number=2, text="The backend response time has degraded. We need better error handling and caching."))
    db.add(TranscriptSegment(meeting_id=m.id, speaker_name="Alice", start_time=265.0, end_time=320.0, turn_number=3, text="Let's table API error handling for now as we don't have enough benchmark metrics yet."))
    db.add(TranscriptSegment(meeting_id=m.id, speaker_name="Charlie", start_time=910.0, end_time=980.0, turn_number=4, text="Regarding database bottlenecks, SQLite is locking under parallel tests."))
    db.add(TranscriptSegment(meeting_id=m.id, speaker_name="Alice", start_time=990.0, end_time=1050.0, turn_number=5, text="Agreed. We will evaluate migrating to PostgreSQL next quarter."))

    # Decision
    db.add(Decision(meeting_id=m.id, text="Evaluate PostgreSQL to replace SQLite in staging", timestamp=1050.0, confidence=0.92, participants_involved="Alice,Charlie"))
    db.commit()
    return m


@router.post("/seed-demo", response_model=Dict[str, Any])
def seed_demo_meeting(db: Session = Depends(get_db)):
    """Seed sample 45-minute sprint meeting with verified attendance, plan, drift, and historical meeting."""
    # Seed historical meeting first for cross-meeting recurring topics
    _seed_historical_q3_meeting(db)

    existing = db.query(Meeting).filter(Meeting.title == "Q4 Sprint Planning & Architecture Sync").first()
    if existing:
        # Ensure attendance and plan are attached
        _populate_demo_extensions(existing, db)
        return {"status": "exists", "meeting_id": existing.id, "message": "Demo meeting already available and configured"}

    sample_path = os.path.join(os.path.dirname(__file__), "..", "..", "sample_data", "sample_meeting.txt")
    if not os.path.exists(sample_path):
        raise HTTPException(status_code=404, detail="sample_meeting.txt not found")

    with open(sample_path, "r", encoding="utf-8") as f:
        content = f.read()

    meeting = process_and_save_transcript(
        title="Q4 Sprint Planning & Architecture Sync",
        raw_text=content,
        filename="sample_meeting.txt",
        db=db
    )

    _populate_demo_extensions(meeting, db)
    return {"status": "created", "meeting_id": meeting.id, "message": "Demo meeting processed and initialized with complete 7 features successfully"}


def _populate_demo_extensions(meeting: Meeting, db: Session):
    """Enrich meeting with verified attendance, pre-meeting plan, and agenda drift."""
    # 1. Update participant metadata
    role_meta = {
        "alice": {"role": "Project Manager", "emp_id": "EMP-101", "dept": "Engineering Management", "resp": "Sprint planning, timeline alignment, unblocking dependencies"},
        "bob": {"role": "Data Scientist", "emp_id": "EMP-102", "dept": "Machine Learning", "resp": "Data pipelines, model evaluation, ML infrastructure"},
        "charlie": {"role": "Backend Developer", "emp_id": "EMP-103", "dept": "Core Backend", "resp": "API contracts, database architecture, CI/CD deployment automation"},
        "david": {"role": "UI Developer", "emp_id": "EMP-104", "dept": "Frontend Engineering", "resp": "UI components, frontend design system, API client integration"},
        "emily": {"role": "QA Engineer", "emp_id": "EMP-105", "dept": "Quality Assurance", "resp": "Automated regression tests, Playwright configs, staging validation"}
    }

    for p in meeting.participants:
        sp_key = p.name.lower().strip()
        if sp_key in role_meta:
            meta = role_meta[sp_key]
            p.role = meta["role"]
            p.employee_id = meta["emp_id"]
            p.department = meta["dept"]
            p.responsibilities = meta["resp"]
            if sp_key == "emily":
                p.speaking_time = 120.0
                p.speaking_percentage = 4.4
                p.turn_count = 3
    db.commit()

    # 2. Seed verified attendance
    # Duration: 2700s (45m)
    # Alice: 00:00 - 45:00 (100% on time)
    # Bob: 05:00 (300s) - 45:00 (88.9%, Late: 5 min)
    # Charlie: 00:00 - 45:00 (100% on time)
    # David: 00:00 - 45:00 (100% on time)
    # Emily: 00:00 - 28:00 (1680s) (62.2%, Left early: 17 min)
    att_specs = [
        {"name": "Alice", "join": 0.0, "leave": 2700.0, "status": "On time"},
        {"name": "Bob", "join": 300.0, "leave": 2700.0, "status": "Late"},
        {"name": "Charlie", "join": 0.0, "leave": 2700.0, "status": "On time"},
        {"name": "David", "join": 0.0, "leave": 2700.0, "status": "On time"},
        {"name": "Emily", "join": 0.0, "leave": 1680.0, "status": "Left early"}
    ]

    for spec in att_specs:
        existing_att = db.query(Attendance).filter(
            Attendance.meeting_id == meeting.id,
            Attendance.employee_name.ilike(spec["name"])
        ).first()

        p = next((x for x in meeting.participants if x.name.lower() == spec["name"].lower()), None)
        dur = spec["leave"] - spec["join"]
        pct = round((dur / 2700.0) * 100.0, 1)
        late_d = spec["join"] if spec["join"] > 60.0 else 0.0
        early_d = (2700.0 - spec["leave"]) if (2700.0 - spec["leave"]) > 60.0 else 0.0

        if not existing_att:
            db.add(Attendance(
                meeting_id=meeting.id,
                participant_id=p.id if p else None,
                employee_name=spec["name"],
                employee_id=p.employee_id if p else f"EMP-{spec['name']}",
                role=p.role if p else "Participant",
                join_time=spec["join"],
                leave_time=spec["leave"],
                duration=dur,
                attendance_percentage=pct,
                late_duration=late_d,
                early_leave_duration=early_d,
                is_verified=True,
                status=spec["status"]
            ))
        else:
            existing_att.join_time = spec["join"]
            existing_att.leave_time = spec["leave"]
            existing_att.duration = dur
            existing_att.attendance_percentage = pct
            existing_att.late_duration = late_d
            existing_att.early_leave_duration = early_d
            existing_att.is_verified = True
            existing_att.status = spec["status"]

    # 3. Seed Meeting Plan
    existing_plan = db.query(MeetingPlan).filter(MeetingPlan.meeting_id == meeting.id).first()
    if not existing_plan:
        plan_dict = meeting_planner.generate_plan(
            topic="Q4 Sprint Planning & Architecture Sync",
            objective="Finalize Q4 sprint priorities, automate deployment pipelines, resolve database bottlenecks, and align engineering team on cloud migration.",
            duration_minutes=45,
            department="Product & Engineering",
            meeting_type="Sprint Planning",
            participants=[
                {"name": "Alice", "role": "Project Manager", "department": "Management", "responsibilities": "Project status & sprint timeline"},
                {"name": "Bob", "role": "Data Scientist", "department": "Data Science", "responsibilities": "ML model performance & customer priority"},
                {"name": "Charlie", "role": "Backend Developer", "department": "Core Backend", "responsibilities": "API contracts & deployment automation"},
                {"name": "David", "role": "UI Developer", "department": "Frontend", "responsibilities": "UI components & dashboard design"},
                {"name": "Emily", "role": "QA Engineer", "department": "Quality Assurance", "responsibilities": "Automated regression tests & Playwright"}
            ]
        )
        db.add(MeetingPlan(
            meeting_id=meeting.id,
            topic=plan_dict["topic"],
            objective=plan_dict["objective"],
            duration_minutes=plan_dict["duration_minutes"],
            department=plan_dict["department"],
            meeting_type=plan_dict["meeting_type"],
            industry_context=plan_dict["industry_context"],
            suggested_agenda=json.dumps(plan_dict["suggested_agenda"]),
            expected_topics=json.dumps(plan_dict["expected_topics"]),
            expected_questions=json.dumps(plan_dict["expected_questions"]),
            expected_decisions=json.dumps(plan_dict["expected_decisions"]),
            expected_action_areas=json.dumps(plan_dict["expected_action_areas"]),
            role_expectations=json.dumps(plan_dict["role_expectations"])
        ))

    # 4. Seed Agenda Drift
    existing_drift = db.query(AgendaDrift).filter(AgendaDrift.meeting_id == meeting.id).first()
    if not existing_drift:
        db.add(AgendaDrift(
            meeting_id=meeting.id,
            start_time=945.0,  # 15:45
            end_time=1015.0,  # 16:55
            duration=70.0,
            percentage=2.6,
            detected_topic="Office Event & Catering Planning",
            expected_topic="Automated Deployment Pipeline",
            category="Minor Drift",
            confidence=0.88,
            excerpt=(
                "Charlie: Before we dive deeper into infrastructure, did anyone submit catering preferences for our upcoming team holiday party and lunch venue? \n"
                "Bob: I voted for the Italian buffet catering, but we need everyone to RSVP on the party spreadsheet so HR can finalize the venue booking. \n"
                "Alice: Let's refocus on our sprint deliverables and coordinate holiday party catering asynchronously."
            ),
            feedback_status="unreviewed"
        ))

    db.commit()


@router.post("/upload")
async def upload_meeting(
    file: Optional[UploadFile] = File(None),
    raw_text: Optional[str] = Form(None),
    title: Optional[str] = Form("Product & Engineering Meeting"),
    db: Session = Depends(get_db)
):
    """Upload meeting transcript file or submit raw transcript text."""
    content = ""
    filename = "manual_transcript.txt"

    if file:
        filename = file.filename or "uploaded_transcript.txt"
        file_bytes = await file.read()
        try:
            content = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            content = file_bytes.decode("latin-1")
    elif raw_text:
        content = raw_text
    else:
        raise HTTPException(status_code=400, detail="Either a file upload or raw_text is required.")

    if not content.strip():
        raise HTTPException(status_code=400, detail="Transcript content cannot be empty.")

    meeting = process_and_save_transcript(
        title=title or "Untitled Meeting",
        raw_text=content,
        filename=filename,
        db=db
    )
    return {"status": "success", "meeting_id": meeting.id, "title": meeting.title}


@router.get("", response_model=List[MeetingSummarySchema])
def list_meetings(db: Session = Depends(get_db)):
    """List all analyzed meetings with summary counts."""
    meetings = db.query(Meeting).order_by(Meeting.id.desc()).all()
    results = []
    for m in meetings:
        results.append(MeetingSummarySchema(
            id=m.id,
            title=m.title,
            date=m.date,
            duration=m.duration,
            transcript_filename=m.transcript_filename,
            created_at=m.created_at,
            status=m.status,
            participant_count=len(m.participants),
            action_item_count=len(m.action_items),
            decision_count=len(m.decisions)
        ))
    return results


@router.get("/{meeting_id}", response_model=MeetingDetailSchema)
def get_meeting(meeting_id: int, db: Session = Depends(get_db)):
    """Get full details of a specific meeting."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting


@router.get("/{meeting_id}/transcript", response_model=List[TranscriptSegmentSchema])
def get_transcript(meeting_id: int, db: Session = Depends(get_db)):
    """Get chronological transcript segments for a meeting."""
    segments = db.query(TranscriptSegment).filter(TranscriptSegment.meeting_id == meeting_id).order_by(TranscriptSegment.turn_number.asc()).all()
    return segments


@router.get("/{meeting_id}/participants", response_model=List[ParticipantSchema])
def get_participants(meeting_id: int, db: Session = Depends(get_db)):
    """Get participants and participation statistics."""
    participants = db.query(Participant).filter(Participant.meeting_id == meeting_id).all()
    return participants


@router.get("/{meeting_id}/export")
def export_meeting(meeting_id: int, format: str = "json", db: Session = Depends(get_db)):
    """
    Export meeting analytics to JSON or CSV.
    Feature 25: Export.
    """
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Compute analytics for enhanced export
    participants = db.query(Participant).filter(Participant.meeting_id == meeting_id).all()
    segments = db.query(TranscriptSegment).filter(TranscriptSegment.meeting_id == meeting_id).order_by(TranscriptSegment.turn_number.asc()).all()
    stored_att = db.query(Attendance).filter(Attendance.meeting_id == meeting_id).all()
    plan = db.query(MeetingPlan).filter(MeetingPlan.meeting_id == meeting_id).first()
    existing_drifts = db.query(AgendaDrift).filter(AgendaDrift.meeting_id == meeting_id).all()

    att_analyzer = AttendanceAnalyzer()
    att_summary = att_analyzer.compute_attendance(meeting, participants, segments, stored_att)

    cov_summary = topic_coverage_analyzer.analyze_coverage(
        meeting, meeting.topics, segments, meeting.decisions, meeting.action_items, plan
    )

    role_contribs = role_contribution_analyzer.analyze_contributions(
        meeting, participants, segments, meeting.topics, meeting.ideas, meeting.decisions, meeting.action_items, plan
    )

    drift_summary = agenda_drift_detector.detect_drifts(
        meeting, segments, plan, existing_drifts
    )

    gap_summary = participation_gap_analyzer.analyze_gaps(
        meeting, participants, segments, stored_att, meeting.topics, meeting.ideas, meeting.action_items
    )

    rec_summary = recurring_topics_analyzer.get_meeting_recurring_topics(meeting_id, db)

    if format.lower() == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 1. Export Action Items
        writer.writerow(["--- ACTION ITEMS ---"])
        writer.writerow(["ID", "Task", "Owner", "Due Date", "Priority", "Status", "Confidence", "Evidence"])
        for a in meeting.action_items:
            writer.writerow([a.id, a.task, a.owner, a.due_date, a.priority, a.status, a.confidence, a.evidence])

        writer.writerow([])
        # 2. Export Decisions
        writer.writerow(["--- DECISIONS ---"])
        writer.writerow(["ID", "Decision", "Timestamp (s)", "Participants", "Confidence"])
        for d in meeting.decisions:
            writer.writerow([d.id, d.text, d.timestamp, d.participants_involved, d.confidence])

        writer.writerow([])
        # 3. Export Participants
        writer.writerow(["--- PARTICIPANTS ---"])
        writer.writerow(["Name", "Speaking Time (s)", "Speaking %", "Turns", "Avg Turn (s)", "Interruptions Made", "Interruptions Received"])
        for p in meeting.participants:
            writer.writerow([p.name, p.speaking_time, p.speaking_percentage, p.turn_count, p.avg_turn_length, p.interruptions_made, p.interruptions_received])

        writer.writerow([])
        # 4. Feature 1: Export Attendance
        writer.writerow(["--- ATTENDANCE ---"])
        writer.writerow(["Participant", "Role", "Join Time", "Leave Time", "Duration (s)", "Attendance %", "Late Arrival (s)", "Early Leave (s)", "Status", "Verification"])
        for rec in att_summary["records"]:
            writer.writerow([
                rec["employee_name"], rec["role"], rec["join_time_display"], rec["leave_time_display"],
                rec["duration"], rec["attendance_percentage"], rec["late_duration"], rec["early_leave_duration"],
                rec["status"], rec["verification_label"]
            ])

        writer.writerow([])
        # 5. Feature 4: Export Topic Coverage
        writer.writerow(["--- TOPIC COVERAGE ---"])
        writer.writerow(["Expected Topic", "Status", "Similarity Score", "Matched Topic", "Duration (s)", "Evidence"])
        for tc in cov_summary["topics"]:
            writer.writerow([
                tc["expected_topic"], tc["status"], tc["similarity_score"],
                tc["matched_transcript_topic"], tc["duration_seconds"], tc["evidence"]
            ])

        writer.writerow([])
        # 6. Feature 3: Export Role Contributions
        writer.writerow(["--- ROLE CONTRIBUTIONS ---"])
        writer.writerow(["Name", "Role", "Coverage %", "Speaking Time (s)", "Speaking %", "Ideas", "Questions", "Actions Assigned", "Decisions Contributed"])
        for rc in role_contribs:
            writer.writerow([
                rc["name"], rc["role"], rc["coverage_percentage"], rc["speaking_time"],
                rc["speaking_percentage"], rc["ideas_contributed"], rc["questions_asked"],
                rc["action_items_assigned"], rc["decisions_contributed"]
            ])

        writer.writerow([])
        # 7. Feature 5: Export Agenda Drift
        writer.writerow(["--- AGENDA DRIFT ---"])
        writer.writerow(["Start", "End", "Duration (s)", "Percentage %", "Detected Topic", "Expected Topic", "Category", "Confidence", "Feedback Status"])
        for ad in drift_summary["drifts"]:
            writer.writerow([
                ad["start_time_display"], ad["end_time_display"], ad["duration"], ad["percentage"],
                ad["detected_topic"], ad["expected_topic"], ad["category"], ad["confidence"], ad["feedback_status"]
            ])

        writer.writerow([])
        # 8. Feature 6: Export Participation Gaps
        writer.writerow(["--- PARTICIPATION GAPS ---"])
        writer.writerow(["Participant", "Role", "Speaking Time (s)", "Speaking %", "Turns", "Label", "Explanation"])
        for pg in gap_summary["gaps"]:
            writer.writerow([
                pg["participant_name"], pg["role"], pg["speaking_time"], pg["speaking_share_percentage"],
                pg["turn_count"], pg["detection_label"], pg["neutral_explanation"]
            ])

        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode("utf-8")),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=meeting_{meeting_id}_analytics.csv"}
        )

    # JSON export
    data = {
        "meeting": {
            "id": meeting.id,
            "title": meeting.title,
            "date": meeting.date,
            "duration": meeting.duration,
            "created_at": str(meeting.created_at)
        },
        "participants": [
            {
                "name": p.name,
                "role": p.role,
                "employee_id": p.employee_id,
                "speaking_time": p.speaking_time,
                "speaking_percentage": p.speaking_percentage,
                "turn_count": p.turn_count,
                "avg_turn_length": p.avg_turn_length,
                "interruptions_made": p.interruptions_made,
                "interruptions_received": p.interruptions_received
            }
            for p in meeting.participants
        ],
        "action_items": [
            {
                "id": a.id,
                "task": a.task,
                "owner": a.owner,
                "due_date": a.due_date,
                "priority": a.priority,
                "status": a.status,
                "confidence": a.confidence,
                "evidence": a.evidence
            }
            for a in meeting.action_items
        ],
        "decisions": [
            {
                "id": d.id,
                "text": d.text,
                "timestamp": d.timestamp,
                "participants": d.participants_involved,
                "confidence": d.confidence
            }
            for d in meeting.decisions
        ],
        "topics": [
            {
                "name": t.name,
                "start_time": t.start_time,
                "end_time": t.end_time,
                "status": t.status,
                "evidence": t.evidence
            }
            for t in meeting.topics
        ],
        "attendance": att_summary,
        "expected_topics": [tc["expected_topic"] for tc in cov_summary["topics"]],
        "actual_topics": [t.name for t in meeting.topics],
        "topic_coverage": cov_summary,
        "role_contributions": role_contribs,
        "agenda_drift": drift_summary,
        "participation_gaps": gap_summary,
        "recurring_topics": rec_summary["topics"]
    }
    return Response(content=json.dumps(data, indent=2), media_type="application/json")


@router.get("/compare/metrics")
def compare_meetings(ids: str, db: Session = Depends(get_db)):
    """
    Compare multiple meetings on measurable metrics without arbitrary quality rankings.
    Feature 24: Meeting Comparison.
    """
    id_list = [int(i.strip()) for i in ids.split(",") if i.strip().isdigit()]
    if not id_list:
        raise HTTPException(status_code=400, detail="Provide valid comma-separated meeting IDs in 'ids' query parameter.")

    meetings = db.query(Meeting).filter(Meeting.id.in_(id_list)).all()
    comparisons = []

    for m in meetings:
        participants = m.participants
        total_interruptions = sum(p.interruptions_made for p in participants)
        avg_turn = round(float(sum(p.avg_turn_length for p in participants) / max(1, len(participants))), 1)

        comparisons.append({
            "id": m.id,
            "title": m.title,
            "date": m.date,
            "duration": m.duration,
            "participant_count": len(participants),
            "total_turns": sum(p.turn_count for p in participants),
            "average_turn_length": avg_turn,
            "total_interruptions": total_interruptions,
            "action_items_count": len(m.action_items),
            "decisions_count": len(m.decisions),
            "unresolved_topics_count": sum(1 for t in m.topics if t.status == "Unresolved"),
            "speakers": [
                {"name": p.name, "speaking_pct": p.speaking_percentage, "speaking_time": p.speaking_time}
                for p in participants
            ]
        })

    return comparisons
