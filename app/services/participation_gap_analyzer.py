"""Participation Gap & Silent Participant Analyzer under strict scientific neutrality."""

import re
from typing import List, Dict, Any, Optional
from app.models.meeting import Meeting
from app.models.participant import Participant
from app.models.transcript import TranscriptSegment
from app.models.attendance import Attendance
from app.models.topic import Topic
from app.models.idea import Idea
from app.models.action_item import ActionItem


def format_duration(seconds: float) -> str:
    """Format seconds into readable minutes string."""
    if seconds is None or seconds <= 0:
        return "0 min"
    mins = round(seconds / 60, 1)
    if mins.is_integer():
        return f"{int(mins)} min"
    return f"{mins:.1f} min"


class ParticipationGapAnalyzer:
    """Detects participants with low observed participation relative to meeting distribution."""

    QUESTION_PATTERNS = [
        re.compile(r"\?"),
        re.compile(r"\b(?:what|how|why|when|where|who|could we|can you)\b", re.IGNORECASE)
    ]

    def analyze_gaps(
        self,
        meeting: Meeting,
        participants: List[Participant],
        segments: List[TranscriptSegment],
        attendance_records: Optional[List[Attendance]] = None,
        topics: Optional[List[Topic]] = None,
        ideas: Optional[List[Idea]] = None,
        action_items: Optional[List[ActionItem]] = None
    ) -> Dict[str, Any]:
        """
        Identify participation gaps using neutral, explainable metrics.
        """
        attendance_records = attendance_records or []
        topics = topics or []
        ideas = ideas or []
        action_items = action_items or []

        total_p = len(participants)
        if total_p == 0:
            return {
                "meeting_id": meeting.id,
                "average_speaking_share": 0.0,
                "threshold_percentage": 0.0,
                "total_participants": 0,
                "gaps_count": 0,
                "gaps": [],
                "all_participants_overview": [],
                "neutral_governance_notice": "Participation gaps reflect observed dialogue cadence and should not be used as performance ratings."
            }

        avg_share = round(100.0 / total_p, 1)
        # Threshold: less than 12% or less than 60% of the fair share
        threshold_pct = max(10.0, round(avg_share * 0.6, 1))

        # Attendance lookup
        att_map = {a.employee_name.lower().strip(): a for a in attendance_records}

        # Segments by speaker
        speaker_segs: Dict[str, List[TranscriptSegment]] = {}
        for s in segments:
            speaker_segs.setdefault(s.speaker_name.lower().strip(), []).append(s)

        gaps = []
        all_overview = []

        for p in participants:
            sp_key = p.name.lower().strip()
            p_segs = speaker_segs.get(sp_key, [])
            att = att_map.get(sp_key)

            # Topic participation count
            topic_ids = {s.topic_id for s in p_segs if s.topic_id is not None}
            topic_part_count = len(topic_ids)

            # Questions asked count
            q_cnt = sum(1 for s in p_segs if any(qp.search(s.text) for qp in self.QUESTION_PATTERNS))

            # Ideas count
            p_ideas = sum(1 for i in ideas if i.speaker.lower().strip() == sp_key)

            # Actions count
            p_actions = sum(1 for a in action_items if a.owner.lower().strip() == sp_key)

            # Attendance info
            att_dur = att.duration if att else meeting.duration
            att_pct = att.attendance_percentage if att else 100.0

            speaking_pct = round(p.speaking_percentage, 1)
            speaking_sec = p.speaking_time
            mins = int(speaking_sec // 60)
            secs = int(speaking_sec % 60)
            speaking_disp = f"{mins}m {secs:02d}s" if mins > 0 else f"{secs}s"

            item_data = {
                "participant_name": p.name,
                "role": p.role or "Team Member",
                "speaking_time": speaking_sec,
                "speaking_time_display": speaking_disp,
                "speaking_share_percentage": speaking_pct,
                "turn_count": p.turn_count,
                "questions_count": q_cnt,
                "ideas_count": p_ideas,
                "responses_count": p.responses_count,
                "actions_assigned": p_actions,
                "topic_participation_count": topic_part_count,
                "attendance_duration": att_dur,
                "attendance_display": format_duration(att_dur),
                "attendance_percentage": att_pct
            }
            all_overview.append(item_data)

            # Check if participant meets low participation criteria
            if speaking_pct <= threshold_pct or (p.turn_count <= 3 and total_p >= 3):
                gaps.append({
                    **item_data,
                    "detection_label": "Low observed participation",
                    "neutral_explanation": (
                        f"{p.name} had {speaking_pct}% of observed speaking time ({speaking_disp}) across {p.turn_count} dialogue turns. "
                        "Low speaking time may have multiple causes, including meeting role, topic relevance, or meeting structure."
                    ),
                    "facilitation_suggestion": (
                        f"Consider directly inviting input from {p.name} during discussions on relevant domain topics, "
                        "or providing asynchronous input channels before and after the meeting."
                    )
                })

        return {
            "meeting_id": meeting.id,
            "average_speaking_share": avg_share,
            "threshold_percentage": threshold_pct,
            "total_participants": total_p,
            "gaps_count": len(gaps),
            "gaps": gaps,
            "all_participants_overview": all_overview,
            "neutral_governance_notice": "Participation gaps reflect observed dialogue cadence and should not be used as performance ratings."
        }


participation_gap_analyzer = ParticipationGapAnalyzer()
