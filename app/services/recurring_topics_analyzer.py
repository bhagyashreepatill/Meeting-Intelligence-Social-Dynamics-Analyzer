"""Recurring Discussion & Cross-Meeting Topic Detector using semantic clustering."""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.meeting import Meeting
from app.models.topic import Topic
from app.models.decision import Decision
from app.models.transcript import TranscriptSegment
from app.models.recurring_topic import RecurringTopic, RecurringTopicOccurrence
from app.services.semantic_matcher import semantic_matcher


def format_seconds(seconds: float) -> str:
    """Format seconds into MM:SS format."""
    if seconds is None or seconds < 0:
        return "00:00"
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


class RecurringTopicsAnalyzer:
    """Detects repeated discussions and tracks their status across historical meetings."""

    SIMILARITY_THRESHOLD = 0.40

    def analyze_all_recurring_topics(
        self,
        db: Session,
        filter_status: Optional[str] = "all"
    ) -> Dict[str, Any]:
        """
        Analyze all meetings in database, cluster recurring topics, and return historical timelines.
        """
        meetings = db.query(Meeting).order_by(Meeting.id.asc()).all()
        if not meetings:
            return {
                "total_recurring_topics": 0,
                "unresolved_count": 0,
                "resolved_count": 0,
                "topics": []
            }

        # Collect all raw topic instances from all meetings
        raw_instances = []
        for m in meetings:
            for t in m.topics:
                # Find linked decisions in this meeting
                linked_dec = [
                    d.text for d in m.decisions
                    if d.timestamp >= t.start_time and d.timestamp <= t.end_time
                ]
                dec_text = linked_dec[0] if linked_dec else None

                # Find speakers in topic
                segs = [s for s in m.transcript_segments if s.start_time >= t.start_time and s.end_time <= t.end_time]
                speakers = sorted(list({s.speaker_name for s in segs if s.speaker_name}))
                excerpt = t.evidence or (segs[0].text if segs else "")

                raw_instances.append({
                    "meeting_id": m.id,
                    "meeting_title": m.title,
                    "meeting_date": m.date or "2026-09-29",
                    "topic_title": t.name,
                    "timestamp": t.start_time,
                    "timestamp_display": format_seconds(t.start_time),
                    "status": t.status or "Unresolved",
                    "decision_text": dec_text,
                    "excerpt": excerpt,
                    "speakers": ", ".join(speakers)
                })

        # Cluster topics across meetings using semantic similarity
        clusters: List[List[Dict[str, Any]]] = []

        for inst in raw_instances:
            matched_cluster = None
            best_sim = 0.0

            for cluster in clusters:
                # Compare against canonical representative
                rep = cluster[0]
                sim = semantic_matcher.similarity(inst["topic_title"], rep["topic_title"])
                if sim >= self.SIMILARITY_THRESHOLD and sim > best_sim:
                    best_sim = sim
                    matched_cluster = cluster

            if matched_cluster is not None:
                matched_cluster.append(inst)
            else:
                clusters.append([inst])

        # Build output objects for recurring topics
        recurring_list = []
        unresolved_cnt = 0
        resolved_cnt = 0

        for cluster in clusters:
            # We treat topics occurring in 2+ meetings as recurring, or topics with Unresolved status
            distinct_meetings = {c["meeting_id"] for c in cluster}
            is_recurring = len(distinct_meetings) >= 2

            canonical_name = cluster[0]["topic_title"]

            # Sort cluster items chronologically
            sorted_occurrences = sorted(cluster, key=lambda x: (x["meeting_id"], x["timestamp"]))

            # Evaluate overall status
            latest_occ = sorted_occurrences[-1]
            has_decision = any(bool(c["decision_text"]) for c in sorted_occurrences)

            if latest_occ["status"] == "Resolved" or has_decision:
                overall_status = "Resolved"
                resolved_cnt += 1
                latest_decision = next((c["decision_text"] for c in reversed(sorted_occurrences) if c["decision_text"]), "Consensus reached")
            elif is_recurring:
                overall_status = "Recurring / Unresolved"
                unresolved_cnt += 1
                latest_decision = "No final decision detected across meetings"
            else:
                overall_status = latest_occ["status"]
                if overall_status == "Unresolved":
                    unresolved_cnt += 1
                latest_decision = "Discussion open"

            # Historical timeline representation
            timeline = [
                {
                    "step": idx + 1,
                    "meeting_id": occ["meeting_id"],
                    "meeting_title": occ["meeting_title"],
                    "meeting_date": occ["meeting_date"],
                    "timestamp": occ["timestamp_display"],
                    "status": occ["status"],
                    "decision": occ["decision_text"] or "No decision",
                    "speakers": occ["speakers"],
                    "excerpt": occ["excerpt"]
                }
                for idx, occ in enumerate(sorted_occurrences)
            ]

            topic_item = {
                "id": len(recurring_list) + 1,
                "topic": canonical_name,
                "occurrences_count": len(sorted_occurrences),
                "distinct_meetings_count": len(distinct_meetings),
                "is_recurring": is_recurring,
                "first_detected_meeting": {
                    "id": sorted_occurrences[0]["meeting_id"],
                    "title": sorted_occurrences[0]["meeting_title"],
                    "date": sorted_occurrences[0]["meeting_date"]
                },
                "last_detected_meeting": {
                    "id": sorted_occurrences[-1]["meeting_id"],
                    "title": sorted_occurrences[-1]["meeting_title"],
                    "date": sorted_occurrences[-1]["meeting_date"]
                },
                "status": overall_status,
                "latest_decision": latest_decision,
                "historical_timeline": timeline,
                "occurrences": sorted_occurrences
            }

            # Filter logic
            if filter_status and filter_status.lower() != "all":
                fs = filter_status.lower()
                if fs == "unresolved" and "unresolved" not in overall_status.lower():
                    continue
                elif fs == "resolved" and "resolved" not in overall_status.lower():
                    continue
                elif fs == "repeated" and not is_recurring:
                    continue

            recurring_list.append(topic_item)

        # Sort by occurrences count descending
        recurring_list.sort(key=lambda t: (t["distinct_meetings_count"], t["occurrences_count"]), reverse=True)

        return {
            "total_recurring_topics": len(recurring_list),
            "unresolved_count": unresolved_cnt,
            "resolved_count": resolved_cnt,
            "topics": recurring_list
        }

    def get_meeting_recurring_topics(
        self,
        meeting_id: int,
        db: Session
    ) -> Dict[str, Any]:
        """Get recurring topics that appear in a specific meeting."""
        all_res = self.analyze_all_recurring_topics(db, filter_status="all")
        meeting_topics = [
            t for t in all_res["topics"]
            if any(occ["meeting_id"] == meeting_id for occ in t["occurrences"])
        ]
        return {
            "meeting_id": meeting_id,
            "total_recurring_topics": len(meeting_topics),
            "topics": meeting_topics
        }


recurring_topics_analyzer = RecurringTopicsAnalyzer()
