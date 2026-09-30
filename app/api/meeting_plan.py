"""Meeting Plan API router for pre-meeting conversation expectations and agenda planning."""

import json
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.meeting import Meeting
from app.models.meeting_plan import MeetingPlan
from app.models.participant import Participant
from app.schemas.schemas import (
    MeetingPlanGenerateRequest, MeetingPlanResponse,
    MeetingPlanSaveRequest
)
from app.services.meeting_planner import meeting_planner

router = APIRouter(prefix="/api/meetings", tags=["meeting-plan"])


@router.post("/meeting-plan/generate", response_model=MeetingPlanResponse)
def generate_unlinked_meeting_plan(payload: MeetingPlanGenerateRequest):
    """
    Generate an AI-driven expected conversation plan before a meeting is held.
    Feature 2: Topic → Expected Conversation Generator.
    Feature 3: Role-Based Expected Contribution.
    """
    part_dicts = [p.model_dump() for p in payload.participants]
    plan = meeting_planner.generate_plan(
        topic=payload.topic,
        objective=payload.objective,
        duration_minutes=payload.duration_minutes,
        department=payload.department,
        meeting_type=payload.meeting_type,
        industry_context=payload.industry_context,
        participants=part_dicts
    )
    return MeetingPlanResponse(**plan)


@router.post("/{meeting_id}/meeting-plan/generate", response_model=MeetingPlanResponse)
def generate_meeting_plan_for_meeting(
    meeting_id: int,
    payload: Optional[MeetingPlanGenerateRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Generate an expected conversation plan tailored to an existing meeting and its detected participants.
    """
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    participants = db.query(Participant).filter(Participant.meeting_id == meeting_id).all()
    part_dicts = []
    if payload and payload.participants:
        part_dicts = [p.model_dump() for p in payload.participants]
    else:
        part_dicts = [
            {
                "name": p.name,
                "role": p.role or ("Project Manager" if "alice" in p.name.lower() else "Engineer"),
                "department": p.department or "Engineering",
                "responsibilities": p.responsibilities or f"Contribution to {meeting.title}"
            }
            for p in participants
        ]

    topic = payload.topic if payload and payload.topic else meeting.title
    objective = payload.objective if payload and payload.objective else meeting.summary
    duration_min = payload.duration_minutes if payload and payload.duration_minutes else int(meeting.duration // 60 or 45)
    dept = payload.department if payload and payload.department else "Engineering"
    m_type = payload.meeting_type if payload and payload.meeting_type else "Sprint Planning"

    plan = meeting_planner.generate_plan(
        topic=topic,
        objective=objective,
        duration_minutes=duration_min,
        department=dept,
        meeting_type=m_type,
        industry_context=payload.industry_context if payload else "Software Architecture",
        participants=part_dicts
    )
    plan["meeting_id"] = meeting_id

    # Save to database if not already present
    existing = db.query(MeetingPlan).filter(MeetingPlan.meeting_id == meeting_id).first()
    if not existing:
        existing = MeetingPlan(
            meeting_id=meeting_id,
            topic=plan["topic"],
            objective=plan["objective"],
            duration_minutes=plan["duration_minutes"],
            department=plan["department"],
            meeting_type=plan["meeting_type"],
            industry_context=plan["industry_context"],
            suggested_agenda=json.dumps(plan["suggested_agenda"]),
            expected_topics=json.dumps(plan["expected_topics"]),
            expected_questions=json.dumps(plan["expected_questions"]),
            expected_decisions=json.dumps(plan["expected_decisions"]),
            expected_action_areas=json.dumps(plan["expected_action_areas"]),
            role_expectations=json.dumps(plan["role_expectations"])
        )
        db.add(existing)
        db.commit()
        db.refresh(existing)
        plan["id"] = existing.id
    else:
        plan["id"] = existing.id

    return MeetingPlanResponse(**plan)


@router.get("/{meeting_id}/meeting-plan", response_model=MeetingPlanResponse)
def get_meeting_plan(meeting_id: int, db: Session = Depends(get_db)):
    """Retrieve saved meeting preparation plan."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    plan = db.query(MeetingPlan).filter(MeetingPlan.meeting_id == meeting_id).first()
    if not plan:
        # Generate default plan automatically for convenience
        participants = db.query(Participant).filter(Participant.meeting_id == meeting_id).all()
        part_dicts = [
            {
                "name": p.name,
                "role": p.role or ("Project Manager" if "alice" in p.name.lower() else "Engineer"),
                "department": p.department or "Engineering",
                "responsibilities": p.responsibilities or f"Contribution to {meeting.title}"
            }
            for p in participants
        ]
        generated = meeting_planner.generate_plan(
            topic=meeting.title,
            objective=meeting.summary or f"Deliverables alignment for {meeting.title}",
            duration_minutes=int(meeting.duration // 60 or 45),
            department="Engineering",
            meeting_type="Sprint Planning",
            participants=part_dicts
        )
        plan = MeetingPlan(
            meeting_id=meeting_id,
            topic=generated["topic"],
            objective=generated["objective"],
            duration_minutes=generated["duration_minutes"],
            department=generated["department"],
            meeting_type=generated["meeting_type"],
            industry_context=generated["industry_context"],
            suggested_agenda=json.dumps(generated["suggested_agenda"]),
            expected_topics=json.dumps(generated["expected_topics"]),
            expected_questions=json.dumps(generated["expected_questions"]),
            expected_decisions=json.dumps(generated["expected_decisions"]),
            expected_action_areas=json.dumps(generated["expected_action_areas"]),
            role_expectations=json.dumps(generated["role_expectations"])
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)

    return MeetingPlanResponse(
        id=plan.id,
        meeting_id=meeting_id,
        topic=plan.topic,
        objective=plan.objective,
        duration_minutes=plan.duration_minutes,
        department=plan.department,
        meeting_type=plan.meeting_type,
        industry_context=plan.industry_context,
        suggested_agenda=json.loads(plan.suggested_agenda or "[]"),
        expected_topics=json.loads(plan.expected_topics or "[]"),
        expected_questions=json.loads(plan.expected_questions or "[]"),
        expected_decisions=json.loads(plan.expected_decisions or "[]"),
        expected_action_areas=json.loads(plan.expected_action_areas or "[]"),
        role_expectations=json.loads(plan.role_expectations or "[]"),
        disclaimer="AI-generated expected discussion (Predictions / planning suggestions, NOT actual meeting facts)",
        is_ai_generated=True
    )


@router.post("/{meeting_id}/meeting-plan", response_model=MeetingPlanResponse)
def save_meeting_plan(
    meeting_id: int,
    payload: MeetingPlanSaveRequest,
    db: Session = Depends(get_db)
):
    """Save or update custom meeting plan."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    existing = db.query(MeetingPlan).filter(MeetingPlan.meeting_id == meeting_id).first()
    if existing:
        existing.topic = payload.topic
        existing.objective = payload.objective
        existing.duration_minutes = payload.duration_minutes
        existing.department = payload.department
        existing.meeting_type = payload.meeting_type
        existing.industry_context = payload.industry_context
        existing.suggested_agenda = json.dumps(payload.suggested_agenda)
        existing.expected_topics = json.dumps(payload.expected_topics)
        existing.expected_questions = json.dumps(payload.expected_questions)
        existing.expected_decisions = json.dumps(payload.expected_decisions)
        existing.expected_action_areas = json.dumps(payload.expected_action_areas)
        existing.role_expectations = json.dumps(payload.role_expectations)
        db.commit()
        db.refresh(existing)
        target = existing
    else:
        target = MeetingPlan(
            meeting_id=meeting_id,
            topic=payload.topic,
            objective=payload.objective,
            duration_minutes=payload.duration_minutes,
            department=payload.department,
            meeting_type=payload.meeting_type,
            industry_context=payload.industry_context,
            suggested_agenda=json.dumps(payload.suggested_agenda),
            expected_topics=json.dumps(payload.expected_topics),
            expected_questions=json.dumps(payload.expected_questions),
            expected_decisions=json.dumps(payload.expected_decisions),
            expected_action_areas=json.dumps(payload.expected_action_areas),
            role_expectations=json.dumps(payload.role_expectations)
        )
        db.add(target)
        db.commit()
        db.refresh(target)

    return MeetingPlanResponse(
        id=target.id,
        meeting_id=meeting_id,
        topic=target.topic,
        objective=target.objective,
        duration_minutes=target.duration_minutes,
        department=target.department,
        meeting_type=target.meeting_type,
        industry_context=target.industry_context,
        suggested_agenda=json.loads(target.suggested_agenda or "[]"),
        expected_topics=json.loads(target.expected_topics or "[]"),
        expected_questions=json.loads(target.expected_questions or "[]"),
        expected_decisions=json.loads(target.expected_decisions or "[]"),
        expected_action_areas=json.loads(target.expected_action_areas or "[]"),
        role_expectations=json.loads(target.role_expectations or "[]"),
        disclaimer="AI-generated expected discussion (Predictions / planning suggestions, NOT actual meeting facts)",
        is_ai_generated=True
    )
