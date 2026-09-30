"""Topic Coverage Analyzer comparing planned expected topics with actual meeting dialogue."""

import json
from typing import List, Dict, Any, Optional
from app.models.meeting import Meeting
from app.models.topic import Topic
from app.models.transcript import TranscriptSegment
from app.models.decision import Decision
from app.models.action_item import ActionItem
from app.models.meeting_plan import MeetingPlan
from app.services.semantic_matcher import semantic_matcher


def generate_coverage_bar(percentage: float, length: int = 10) -> str:
    """Generate visual text representation of coverage percentage e.g. ██████░░░░ 60%."""
    filled = int(round((percentage / 100.0) * length))
    filled = min(length, max(0, filled))
    empty = length - filled
    return f"{'█' * filled}{'░' * empty} {int(round(percentage))}%"


class TopicCoverageAnalyzer:
    """Evaluates coverage of expected topics against actual transcript dialogue turns and topics."""

    DEFAULT_EXPECTED_TOPICS = [
        "Sprint Deliverables & Current Status",
        "Automated Deployment Pipeline",
        "Database Migration to PostgreSQL",
        "Cloud Migration Strategy",
        "API Error Handling & Performance",
        "Resource Budget Allocation",
        "Mobile Responsive Experience"
    ]

    def analyze_coverage(
        self,
        meeting: Meeting,
        topics: List[Topic],
        segments: List[TranscriptSegment],
        decisions: List[Decision],
        action_items: List[ActionItem],
        plan: Optional[MeetingPlan] = None
    ) -> Dict[str, Any]:
        """Compute explainable topic coverage score and detailed itemized breakdown."""
        # 1. Determine expected topics
        expected_topics: List[str] = []
        if plan and plan.expected_topics:
            try:
                expected_topics = json.loads(plan.expected_topics)
            except Exception:
                expected_topics = [t.strip() for t in plan.expected_topics.split("\n") if t.strip()]

        if not expected_topics:
            expected_topics = list(self.DEFAULT_EXPECTED_TOPICS)

        # 2. Extract transcript full text and segments per topic
        topic_segments_map: Dict[str, List[TranscriptSegment]] = {}
        all_transcript_text = " ".join(s.text for s in segments)

        for t in topics:
            t_segs = [s for s in segments if s.start_time >= t.start_time and s.end_time <= t.end_time]
            topic_segments_map[t.name] = t_segs

        items: List[Dict[str, Any]] = []
        covered_count = 0
        partially_covered_count = 0
        not_discussed_count = 0

        missing_topics: List[str] = []
        partially_covered_topics: List[str] = []
        fully_covered_topics: List[str] = []

        for exp_topic in expected_topics:
            best_sim = 0.0
            best_matched_topic: Optional[Topic] = None

            # Compare against existing segmented topics
            for t in topics:
                sim = semantic_matcher.similarity(exp_topic, t.name)
                # Also check topic evidence / transcript text in that topic
                t_text = " ".join(s.text for s in topic_segments_map.get(t.name, []))
                sim_text = semantic_matcher.similarity(exp_topic, t_text)
                effective_sim = max(sim, sim_text * 0.9)

                if effective_sim > best_sim:
                    best_sim = effective_sim
                    best_matched_topic = t

            # Compare against whole transcript if no topic segment matched well
            if best_sim < 0.35:
                sim_all = semantic_matcher.similarity(exp_topic, all_transcript_text)
                if sim_all > best_sim:
                    best_sim = sim_all

            # Calculate topic duration, decisions, action items
            duration_sec = 0.0
            evidence = ""
            matched_name = best_matched_topic.name if best_matched_topic else None
            dec_cnt = 0
            act_cnt = 0

            if best_matched_topic:
                duration_sec = max(0.0, best_matched_topic.end_time - best_matched_topic.start_time)
                evidence = best_matched_topic.evidence or f"Discussed in {best_matched_topic.name}"
                # Count linked decisions
                dec_cnt = sum(
                    1 for d in decisions
                    if d.timestamp >= best_matched_topic.start_time and d.timestamp <= best_matched_topic.end_time
                )
                act_cnt = sum(
                    1 for a in action_items
                    if (a.source_segment and a.source_segment.start_time >= best_matched_topic.start_time and a.source_segment.start_time <= best_matched_topic.end_time)
                )

            # Determine Status
            if best_sim >= 0.45 or (best_matched_topic and duration_sec >= 120.0 and best_sim >= 0.30):
                status = "Covered"
                covered_count += 1
                fully_covered_topics.append(exp_topic)
            elif best_sim >= 0.25:
                status = "Partially Covered"
                partially_covered_count += 1
                partially_covered_topics.append(exp_topic)
                if not evidence:
                    evidence = "Briefly touched upon in discussion without dedicated consensus or action items."
            else:
                status = "Not Discussed"
                not_discussed_count += 1
                missing_topics.append(exp_topic)
                evidence = "No substantive dialogue turns matched this expected topic."
                duration_sec = 0.0

            mins = int(duration_sec // 60)
            secs = int(duration_sec % 60)
            duration_disp = f"{mins}m {secs:02d}s" if mins > 0 else f"{secs}s"

            items.append({
                "expected_topic": exp_topic,
                "status": status,
                "similarity_score": round(best_sim, 2),
                "matched_transcript_topic": matched_name,
                "duration_seconds": duration_sec,
                "duration_display": duration_disp,
                "evidence": evidence,
                "decisions_count": dec_cnt,
                "action_items_count": act_cnt
            })

        total = len(expected_topics)
        # Score calculation: Covered = 1.0, Partially Covered = 0.5
        effective_covered = covered_count + (partially_covered_count * 0.5)
        coverage_pct = round((effective_covered / max(1, total)) * 100.0, 1)

        explainable_reason = (
            f"{covered_count} of {total} expected topics were fully covered"
            f"{f', {partially_covered_count} partially covered' if partially_covered_count else ''}"
            f"{f', and {not_discussed_count} not discussed' if not_discussed_count else ''}."
        )

        return {
            "meeting_id": meeting.id,
            "total_expected": total,
            "covered_count": covered_count,
            "partially_covered_count": partially_covered_count,
            "not_discussed_count": not_discussed_count,
            "coverage_percentage": coverage_pct,
            "coverage_bar": generate_coverage_bar(coverage_pct),
            "explainable_reason": explainable_reason,
            "topics": items,
            "missing_topics": missing_topics,
            "partially_covered_topics": partially_covered_topics,
            "fully_covered_topics": fully_covered_topics
        }


topic_coverage_analyzer = TopicCoverageAnalyzer()
