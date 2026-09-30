"""Attendance Analytics Engine for meeting in-time and duration tracking."""

from typing import List, Dict, Any, Optional
from app.models.meeting import Meeting
from app.models.participant import Participant
from app.models.attendance import Attendance
from app.models.transcript import TranscriptSegment


def format_seconds(seconds: float) -> str:
    """Format seconds into MM:SS format."""
    if seconds is None or seconds < 0:
        return "00:00"
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


def format_duration(seconds: float) -> str:
    """Format seconds into readable minutes string."""
    if seconds is None or seconds <= 0:
        return "0 min"
    mins = round(seconds / 60, 1)
    if mins.is_integer():
        return f"{int(mins)} min"
    return f"{mins:.1f} min"


class AttendanceAnalyzer:
    """Computes participant attendance, punctuality, late arrivals, and early departures."""

    LATE_THRESHOLD_SECONDS = 60.0  # > 1 min after meeting start counts as late
    EARLY_LEAVE_THRESHOLD_SECONDS = 60.0  # > 1 min before meeting end counts as left early

    def compute_attendance(
        self,
        meeting: Meeting,
        participants: List[Participant],
        segments: List[TranscriptSegment],
        verified_attendance: Optional[List[Attendance]] = None
    ) -> Dict[str, Any]:
        """
        Generate complete attendance metrics distinguishing verified data from transcript-inferred data.
        """
        meeting_duration = meeting.duration if meeting.duration and meeting.duration > 0 else 2700.0

        # Map existing verified attendance by employee name
        verified_map: Dict[str, Attendance] = {}
        if verified_attendance:
            for att in verified_attendance:
                verified_map[att.employee_name.lower().strip()] = att

        # Also map participant-level metadata (role, employee_id)
        participant_map: Dict[str, Participant] = {
            p.name.lower().strip(): p for p in participants
        }

        # Calculate transcript appearances (first detected & last detected turn)
        transcript_first: Dict[str, float] = {}
        transcript_last: Dict[str, float] = {}
        for s in segments:
            sp = s.speaker_name.lower().strip()
            if sp not in transcript_first or s.start_time < transcript_first[sp]:
                transcript_first[sp] = s.start_time
            if sp not in transcript_last or s.end_time > transcript_last[sp]:
                transcript_last[sp] = s.end_time

        records: List[Dict[str, Any]] = []

        # Determine all participants to evaluate
        all_names = set(p.name for p in participants)
        if verified_attendance:
            for att in verified_attendance:
                all_names.add(att.employee_name)

        for name in sorted(all_names):
            name_key = name.lower().strip()
            p = participant_map.get(name_key)
            existing_att = verified_map.get(name_key)

            first_seen = transcript_first.get(name_key)
            last_seen = transcript_last.get(name_key)

            employee_id = (
                (existing_att.employee_id if existing_att and existing_att.employee_id else None) or
                (p.employee_id if p and p.employee_id else None) or
                f"EMP-{abs(hash(name)) % 900 + 100}"
            )
            role = (
                (existing_att.role if existing_att and existing_att.role else None) or
                (p.role if p and p.role else None) or
                "Participant"
            )

            if existing_att and existing_att.is_verified:
                # Actual verified attendance
                is_verified = True
                join_time = existing_att.join_time
                leave_time = existing_att.leave_time if existing_att.leave_time > 0 else meeting_duration
                verification_label = "Verified attendance"
            else:
                # Inferred from transcript
                is_verified = False
                join_time = first_seen if first_seen is not None else 0.0
                leave_time = last_seen if last_seen is not None else meeting_duration
                verification_label = "Estimated from transcript"

            # Compute duration and punctuality
            join_time = max(0.0, float(join_time))
            leave_time = min(meeting_duration, max(join_time, float(leave_time)))
            duration = max(0.0, leave_time - join_time)

            attendance_pct = round(min(100.0, max(0.0, (duration / meeting_duration) * 100.0)), 1)

            # Late arrival calculation
            late_duration = max(0.0, join_time)
            is_late = late_duration > self.LATE_THRESHOLD_SECONDS

            # Early departure calculation
            early_leave_duration = max(0.0, meeting_duration - leave_time)
            is_early_leave = early_leave_duration > self.EARLY_LEAVE_THRESHOLD_SECONDS

            # Assign badges
            if is_late and is_early_leave:
                status = "Late & Left early"
            elif is_late:
                status = "Late"
            elif is_early_leave:
                status = "Left early"
            elif attendance_pct < 70.0:
                status = "Partial attendance"
            else:
                status = "On time"

            records.append({
                "id": existing_att.id if existing_att else None,
                "meeting_id": meeting.id,
                "participant_id": p.id if p else None,
                "employee_name": name,
                "employee_id": employee_id,
                "role": role,
                "join_time": join_time,
                "join_time_display": format_seconds(join_time),
                "leave_time": leave_time,
                "leave_time_display": format_seconds(leave_time),
                "duration": duration,
                "duration_display": format_duration(duration),
                "meeting_duration": meeting_duration,
                "meeting_duration_display": format_duration(meeting_duration),
                "attendance_percentage": attendance_pct,
                "late_duration": late_duration if is_late else 0.0,
                "late_display": format_duration(late_duration) if is_late else "0 min",
                "early_leave_duration": early_leave_duration if is_early_leave else 0.0,
                "early_leave_display": format_duration(early_leave_duration) if is_early_leave else "0 min",
                "first_transcript_time": first_seen,
                "first_transcript_display": format_seconds(first_seen) if first_seen is not None else "None",
                "last_transcript_time": last_seen,
                "last_transcript_display": format_seconds(last_seen) if last_seen is not None else "None",
                "is_verified": is_verified,
                "verification_label": verification_label,
                "status": status
            })

        # Summary statistics
        total_p = len(records)
        verified_cnt = sum(1 for r in records if r["is_verified"])
        estimated_cnt = total_p - verified_cnt
        avg_pct = round(sum(r["attendance_percentage"] for r in records) / max(1, total_p), 1)
        late_cnt = sum(1 for r in records if "Late" in r["status"])
        early_cnt = sum(1 for r in records if "Left early" in r["status"])

        return {
            "meeting_id": meeting.id,
            "meeting_duration": meeting_duration,
            "total_participants": total_p,
            "verified_count": verified_cnt,
            "estimated_count": estimated_cnt,
            "average_attendance_percentage": avg_pct,
            "late_arrivals_count": late_cnt,
            "early_departures_count": early_cnt,
            "records": records
        }
