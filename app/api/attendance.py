"""Attendance API router for participant in-time, punctuality, and attendance analytics."""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.meeting import Meeting
from app.models.participant import Participant
from app.models.attendance import Attendance
from app.models.transcript import TranscriptSegment
from app.schemas.schemas import (
    AttendanceSummarySchema, AttendanceRecordSchema,
    AttendanceUpdateSchema, AttendanceCreateSchema
)
from app.services.attendance_analyzer import AttendanceAnalyzer

router = APIRouter(prefix="/api/meetings/{meeting_id}/attendance", tags=["attendance"])
analyzer = AttendanceAnalyzer()


@router.get("", response_model=AttendanceSummarySchema)
def get_attendance(meeting_id: int, db: Session = Depends(get_db)):
    """
    Retrieve attendance metrics, punctuality, and late/early departure analytics.
    Feature 1: Employee Meeting In-Time & Attendance Analytics.
    """
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    participants = db.query(Participant).filter(Participant.meeting_id == meeting_id).all()
    segments = db.query(TranscriptSegment).filter(TranscriptSegment.meeting_id == meeting_id).all()
    stored_att = db.query(Attendance).filter(Attendance.meeting_id == meeting_id).all()

    summary = analyzer.compute_attendance(
        meeting=meeting,
        participants=participants,
        segments=segments,
        verified_attendance=stored_att
    )
    return summary


@router.post("", response_model=AttendanceRecordSchema)
def create_or_import_attendance(
    meeting_id: int,
    payload: AttendanceCreateSchema,
    db: Session = Depends(get_db)
):
    """
    Import or manually submit verified participant join/leave attendance records.
    """
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Match participant by name if exists
    participant = db.query(Participant).filter(
        Participant.meeting_id == meeting_id,
        Participant.name.ilike(payload.employee_name.strip())
    ).first()

    existing = db.query(Attendance).filter(
        Attendance.meeting_id == meeting_id,
        Attendance.employee_name.ilike(payload.employee_name.strip())
    ).first()

    meeting_dur = meeting.duration if meeting.duration > 0 else 2700.0
    join_t = max(0.0, float(payload.join_time))
    leave_t = min(meeting_dur, max(join_t, float(payload.leave_time)))
    dur = max(0.0, leave_t - join_t)
    pct = round(min(100.0, (dur / meeting_dur) * 100.0), 1)

    late_dur = join_t if join_t > 60.0 else 0.0
    early_dur = (meeting_dur - leave_t) if (meeting_dur - leave_t) > 60.0 else 0.0

    if late_dur > 0 and early_dur > 0:
        status = "Late & Left early"
    elif late_dur > 0:
        status = "Late"
    elif early_dur > 0:
        status = "Left early"
    elif pct < 70.0:
        status = "Partial attendance"
    else:
        status = "On time"

    if existing:
        att = existing
        att.join_time = join_t
        att.leave_time = leave_t
        att.duration = dur
        att.attendance_percentage = pct
        att.late_duration = late_dur
        att.early_leave_duration = early_dur
        att.is_verified = payload.is_verified
        att.status = status
        if payload.employee_id:
            att.employee_id = payload.employee_id
        if payload.role:
            att.role = payload.role
    else:
        att = Attendance(
            meeting_id=meeting_id,
            participant_id=participant.id if participant else None,
            employee_name=payload.employee_name.strip(),
            employee_id=payload.employee_id or f"EMP-{abs(hash(payload.employee_name)) % 900 + 100}",
            role=payload.role or (participant.role if participant else "Participant"),
            join_time=join_t,
            leave_time=leave_t,
            duration=dur,
            attendance_percentage=pct,
            late_duration=late_dur,
            early_leave_duration=early_dur,
            is_verified=payload.is_verified,
            status=status
        )
        db.add(att)

    # Sync back to participant model if available
    if participant:
        if payload.employee_id:
            participant.employee_id = payload.employee_id
        if payload.role:
            participant.role = payload.role

    db.commit()
    db.refresh(att)

    # Format response record
    return AttendanceRecordSchema(
        id=att.id,
        meeting_id=meeting_id,
        participant_id=att.participant_id,
        employee_name=att.employee_name,
        employee_id=att.employee_id,
        role=att.role,
        join_time=att.join_time,
        join_time_display=f"{int(att.join_time // 60):02d}:{int(att.join_time % 60):02d}",
        leave_time=att.leave_time,
        leave_time_display=f"{int(att.leave_time // 60):02d}:{int(att.leave_time % 60):02d}",
        duration=att.duration,
        duration_display=f"{round(att.duration / 60, 1)} min",
        meeting_duration=meeting_dur,
        meeting_duration_display=f"{round(meeting_dur / 60, 1)} min",
        attendance_percentage=att.attendance_percentage,
        late_duration=att.late_duration,
        late_display=f"{round(att.late_duration / 60, 1)} min" if att.late_duration > 0 else "0 min",
        early_leave_duration=att.early_leave_duration,
        early_leave_display=f"{round(att.early_leave_duration / 60, 1)} min" if att.early_leave_duration > 0 else "0 min",
        is_verified=att.is_verified,
        verification_label="Verified attendance" if att.is_verified else "Estimated from transcript",
        status=att.status
    )


@router.put("/{participant_id}", response_model=AttendanceRecordSchema)
def update_participant_attendance(
    meeting_id: int,
    participant_id: int,
    payload: AttendanceUpdateSchema,
    db: Session = Depends(get_db)
):
    """
    Update verified attendance record for a specific participant.
    """
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    participant = db.query(Participant).filter(
        Participant.id == participant_id,
        Participant.meeting_id == meeting_id
    ).first()
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    att = db.query(Attendance).filter(
        Attendance.meeting_id == meeting_id,
        (Attendance.participant_id == participant_id) | (Attendance.employee_name.ilike(participant.name.strip()))
    ).first()

    meeting_dur = meeting.duration if meeting.duration > 0 else 2700.0
    join_t = max(0.0, float(payload.join_time if payload.join_time is not None else (att.join_time if att else 0.0)))
    leave_t = min(meeting_dur, max(join_t, float(payload.leave_time if payload.leave_time is not None else (att.leave_time if att else meeting_dur))))
    dur = max(0.0, leave_t - join_t)
    pct = round(min(100.0, (dur / meeting_dur) * 100.0), 1)

    late_dur = join_t if join_t > 60.0 else 0.0
    early_dur = (meeting_dur - leave_t) if (meeting_dur - leave_t) > 60.0 else 0.0

    if late_dur > 0 and early_dur > 0:
        status = "Late & Left early"
    elif late_dur > 0:
        status = "Late"
    elif early_dur > 0:
        status = "Left early"
    elif pct < 70.0:
        status = "Partial attendance"
    else:
        status = "On time"

    if not att:
        att = Attendance(
            meeting_id=meeting_id,
            participant_id=participant_id,
            employee_name=participant.name,
            employee_id=payload.employee_id or participant.employee_id or f"EMP-{participant.id + 100}",
            role=payload.role or participant.role or "Participant",
            join_time=join_t,
            leave_time=leave_t,
            duration=dur,
            attendance_percentage=pct,
            late_duration=late_dur,
            early_leave_duration=early_dur,
            is_verified=payload.is_verified if payload.is_verified is not None else True,
            status=status
        )
        db.add(att)
    else:
        att.participant_id = participant_id
        att.join_time = join_t
        att.leave_time = leave_t
        att.duration = dur
        att.attendance_percentage = pct
        att.late_duration = late_dur
        att.early_leave_duration = early_dur
        att.is_verified = payload.is_verified if payload.is_verified is not None else True
        att.status = status
        if payload.employee_id:
            att.employee_id = payload.employee_id
            participant.employee_id = payload.employee_id
        if payload.role:
            att.role = payload.role
            participant.role = payload.role

    db.commit()
    db.refresh(att)

    return AttendanceRecordSchema(
        id=att.id,
        meeting_id=meeting_id,
        participant_id=att.participant_id,
        employee_name=att.employee_name,
        employee_id=att.employee_id,
        role=att.role,
        join_time=att.join_time,
        join_time_display=f"{int(att.join_time // 60):02d}:{int(att.join_time % 60):02d}",
        leave_time=att.leave_time,
        leave_time_display=f"{int(att.leave_time // 60):02d}:{int(att.leave_time % 60):02d}",
        duration=att.duration,
        duration_display=f"{round(att.duration / 60, 1)} min",
        meeting_duration=meeting_dur,
        meeting_duration_display=f"{round(meeting_dur / 60, 1)} min",
        attendance_percentage=att.attendance_percentage,
        late_duration=att.late_duration,
        late_display=f"{round(att.late_duration / 60, 1)} min" if att.late_duration > 0 else "0 min",
        early_leave_duration=att.early_leave_duration,
        early_leave_display=f"{round(att.early_leave_duration / 60, 1)} min" if att.early_leave_duration > 0 else "0 min",
        is_verified=att.is_verified,
        verification_label="Verified attendance" if att.is_verified else "Estimated from transcript",
        status=att.status
    )
