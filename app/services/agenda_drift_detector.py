"""Agenda Drift Detector identifying off-topic dialogue deviations with explainable confidence."""

import re
from typing import List, Dict, Any, Optional, Tuple
from app.models.meeting import Meeting
from app.models.transcript import TranscriptSegment
from app.models.agenda_drift import AgendaDrift
from app.models.meeting_plan import MeetingPlan
from app.services.semantic_matcher import semantic_matcher


def format_seconds(seconds: float) -> str:
    """Format seconds into MM:SS format."""
    if seconds is None or seconds < 0:
        return "00:00"
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


def format_duration(seconds: float) -> str:
    """Format seconds into readable duration string."""
    if seconds is None or seconds <= 0:
        return "0s"
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    if mins > 0 and secs > 0:
        return f"{mins}m {secs}s"
    elif mins > 0:
        return f"{mins}m"
    return f"{secs}s"


class AgendaDriftDetector:
    """Detects conversational divergence from the meeting's scheduled agenda."""

    # Off-topic topic indicators and common drift cues
    DRIFT_THEMES = [
        {
            "name": "Office Event & Catering Planning",
            "keywords": ["party", "catering", "holiday", "lunch", "dinner", "venue", "food", "drinks", "buffet", "rsvp", "cake", "celebration"],
            "expected_contrast": "Core Technical / Sprint Deliverables"
        },
        {
            "name": "Social Banter & Weekend Plans",
            "keywords": ["weekend", "movie", "football", "vacation", "trip", "flight", "weather", "concert", "holiday"],
            "expected_contrast": "Planned Agenda Discussion"
        },
        {
            "name": "Unscheduled Vendor & Licensing Query",
            "keywords": ["vendor contract", "sales rep", "discount", "licensing tier", "procurement invoice"],
            "expected_contrast": "Technical Architecture Alignment"
        }
    ]

    DRIFT_PULLBACK_CUES = [
        re.compile(r"\b(?:getting back to|back to the topic|anyway|let's refocus|returning to|as i was saying)\b", re.IGNORECASE)
    ]

    def detect_drifts(
        self,
        meeting: Meeting,
        segments: List[TranscriptSegment],
        plan: Optional[MeetingPlan] = None,
        existing_drifts: Optional[List[AgendaDrift]] = None
    ) -> Dict[str, Any]:
        """
        Identify segments that diverge from the agenda and generate timeline blocks.
        """
        meeting_duration = meeting.duration if meeting.duration and meeting.duration > 0 else 2700.0

        drifts: List[Dict[str, Any]] = []

        # Check if existing drifts are in database
        if existing_drifts:
            for ed in existing_drifts:
                pct = round((ed.duration / max(1.0, meeting_duration)) * 100.0, 1)
                drifts.append({
                    "id": ed.id,
                    "meeting_id": meeting.id,
                    "start_time": ed.start_time,
                    "start_time_display": format_seconds(ed.start_time),
                    "end_time": ed.end_time,
                    "end_time_display": format_seconds(ed.end_time),
                    "duration": ed.duration,
                    "duration_display": format_duration(ed.duration),
                    "percentage": pct,
                    "detected_topic": ed.detected_topic,
                    "expected_topic": ed.expected_topic,
                    "category": ed.category,
                    "confidence": ed.confidence,
                    "excerpt": ed.excerpt,
                    "feedback_status": ed.feedback_status or "unreviewed"
                })

        # If no stored drifts, scan dialogue segments algorithmically
        if not drifts and segments:
            detected_windows = self._scan_segments_for_drift(segments, meeting_duration)
            for idx, dw in enumerate(detected_windows):
                duration = dw["end_time"] - dw["start_time"]
                pct = round((duration / meeting_duration) * 100.0, 1)

                if duration >= 600 or pct >= 20.0:
                    cat = "Significant Drift"
                elif duration >= 300 or pct >= 10.0:
                    cat = "Moderate Drift"
                else:
                    cat = "Minor Drift"

                drifts.append({
                    "id": idx + 1,
                    "meeting_id": meeting.id,
                    "start_time": dw["start_time"],
                    "start_time_display": format_seconds(dw["start_time"]),
                    "end_time": dw["end_time"],
                    "end_time_display": format_seconds(dw["end_time"]),
                    "duration": duration,
                    "duration_display": format_duration(duration),
                    "percentage": pct,
                    "detected_topic": dw["detected_topic"],
                    "expected_topic": dw["expected_topic"],
                    "category": cat,
                    "confidence": dw["confidence"],
                    "excerpt": dw["excerpt"],
                    "feedback_status": "unreviewed"
                })

        # Construct contiguous timeline: On Agenda vs Potential Drift
        timeline_blocks = self._build_timeline(drifts, meeting_duration, segments)

        total_drift_sec = sum(d["duration"] for d in drifts)
        total_drift_pct = round((total_drift_sec / max(1.0, meeting_duration)) * 100.0, 1)

        return {
            "meeting_id": meeting.id,
            "total_meeting_duration": meeting_duration,
            "drift_detected": len(drifts) > 0,
            "total_drift_incidents": len(drifts),
            "total_drift_duration": total_drift_sec,
            "total_drift_percentage": total_drift_pct,
            "drifts": drifts,
            "timeline": timeline_blocks,
            "neutral_notice": "Neutral observation: Drift detection identifies semantic shifts from planned topics."
        }

    def _scan_segments_for_drift(
        self,
        segments: List[TranscriptSegment],
        meeting_duration: float
    ) -> List[Dict[str, Any]]:
        """Identify contiguous runs of off-topic keywords."""
        drifts = []
        i = 0
        n = len(segments)

        while i < n:
            seg = segments[i]
            matched_theme = None
            for theme in self.DRIFT_THEMES:
                text_lower = seg.text.lower()
                hits = sum(1 for kw in theme["keywords"] if kw in text_lower)
                if hits >= 2 or (hits >= 1 and any(k in text_lower for k in ["catering", "holiday party", "party"])):
                    matched_theme = theme
                    break

            if matched_theme:
                # Find contiguous boundary of this drift
                start_seg = seg
                end_seg = seg
                j = i + 1
                drift_texts = [f"{seg.speaker_name}: \"{seg.text}\""]

                while j < n:
                    next_seg = segments[j]
                    # Check if pullback phrase occurs
                    if any(pb.search(next_seg.text) for pb in self.DRIFT_PULLBACK_CUES):
                        break
                    # Check if still mentioning drift keywords
                    text_lower = next_seg.text.lower()
                    hits = sum(1 for kw in matched_theme["keywords"] if kw in text_lower)
                    if hits > 0 or (next_seg.start_time - end_seg.end_time < 30.0 and j - i < 5):
                        end_seg = next_seg
                        drift_texts.append(f"{next_seg.speaker_name}: \"{next_seg.text}\"")
                        j += 1
                    else:
                        break

                drifts.append({
                    "start_time": start_seg.start_time,
                    "end_time": end_seg.end_time,
                    "detected_topic": matched_theme["name"],
                    "expected_topic": matched_theme["expected_contrast"],
                    "confidence": 0.85,
                    "excerpt": " \n".join(drift_texts[:3])
                })
                i = j
            else:
                i += 1

        return drifts

    def _build_timeline(
        self,
        drifts: List[Dict[str, Any]],
        meeting_duration: float,
        segments: List[TranscriptSegment]
    ) -> List[Dict[str, Any]]:
        """Construct full timeline from 00:00 to meeting_duration with status tags."""
        if not drifts:
            return [{
                "start_time": 0.0,
                "end_time": meeting_duration,
                "start_display": "00:00",
                "end_display": format_seconds(meeting_duration),
                "duration": meeting_duration,
                "is_drift": False,
                "status_label": "On Agenda",
                "topic": "Scheduled Meeting Agenda",
                "category": None,
                "confidence": 1.0,
                "drift_id": None
            }]

        sorted_drifts = sorted(drifts, key=lambda d: d["start_time"])
        blocks = []
        curr = 0.0

        for d in sorted_drifts:
            d_start = d["start_time"]
            d_end = d["end_time"]

            if d_start > curr:
                # Preceding on-agenda block
                blocks.append({
                    "start_time": curr,
                    "end_time": d_start,
                    "start_display": format_seconds(curr),
                    "end_display": format_seconds(d_start),
                    "duration": d_start - curr,
                    "is_drift": False,
                    "status_label": "On Agenda",
                    "topic": "Scheduled Agenda Deliberation",
                    "category": None,
                    "confidence": 0.95,
                    "drift_id": None
                })

            # The drift block
            blocks.append({
                "start_time": d_start,
                "end_time": d_end,
                "start_display": format_seconds(d_start),
                "end_display": format_seconds(d_end),
                "duration": d_end - d_start,
                "is_drift": True,
                "status_label": "Potential Agenda Drift",
                "topic": d["detected_topic"],
                "category": d["category"],
                "confidence": d["confidence"],
                "drift_id": d["id"]
            })
            curr = d_end

        if curr < meeting_duration:
            # Trailing on-agenda block
            blocks.append({
                "start_time": curr,
                "end_time": meeting_duration,
                "start_display": format_seconds(curr),
                "end_display": format_seconds(meeting_duration),
                "duration": meeting_duration - curr,
                "is_drift": False,
                "status_label": "On Agenda",
                "topic": "Scheduled Agenda Wrap-up",
                "category": None,
                "confidence": 0.95,
                "drift_id": None
            })

        return blocks


agenda_drift_detector = AgendaDriftDetector()
