"""Role-Based Expected vs Actual Contribution Analyzer."""

import re
from typing import List, Dict, Any, Optional
from app.models.meeting import Meeting
from app.models.participant import Participant
from app.models.transcript import TranscriptSegment
from app.models.topic import Topic
from app.models.idea import Idea
from app.models.decision import Decision
from app.models.action_item import ActionItem
from app.models.meeting_plan import MeetingPlan
from app.services.semantic_matcher import semantic_matcher


class RoleContributionAnalyzer:
    """Evaluates expected vs actual contributions across topics and dialogue metrics under neutral governance."""

    QUESTION_PATTERNS = [
        re.compile(r"\?"),
        re.compile(r"\b(?:what|how|why|when|where|who|can you|could we|is there|are we)\b", re.IGNORECASE)
    ]

    def analyze_contributions(
        self,
        meeting: Meeting,
        participants: List[Participant],
        segments: List[TranscriptSegment],
        topics: List[Topic],
        ideas: List[Idea],
        decisions: List[Decision],
        action_items: List[ActionItem],
        plan: Optional[MeetingPlan] = None
    ) -> List[Dict[str, Any]]:
        """Compute expected vs actual contribution metrics per participant."""
        # Parse plan role expectations if present
        role_expectations_map: Dict[str, Dict[str, Any]] = {}
        if plan and plan.role_expectations:
            try:
                import json
                re_list = json.loads(plan.role_expectations)
                for item in re_list:
                    role_expectations_map[item.get("name", "").lower().strip()] = item
            except Exception:
                pass

        # Map topics by ID
        topic_name_map = {t.id: t.name for t in topics}

        # Segments by speaker
        speaker_segments: Dict[str, List[TranscriptSegment]] = {}
        for s in segments:
            sp = s.speaker_name.lower().strip()
            speaker_segments.setdefault(sp, []).append(s)

        contributions = []

        for p in participants:
            sp_key = p.name.lower().strip()
            p_segs = speaker_segments.get(sp_key, [])

            # Role & metadata
            exp_info = role_expectations_map.get(sp_key, {})
            role = p.role or exp_info.get("role") or self._infer_default_role(p.name)
            dept = p.department or exp_info.get("department") or "Engineering"
            resp = p.responsibilities or exp_info.get("responsibilities") or f"Domain contribution for {role}"

            expected_topics = exp_info.get("expected_topics") or self._get_default_expected_topics(role)

            # Detect actually discussed topics by this speaker
            actual_topic_ids = {s.topic_id for s in p_segs if s.topic_id is not None}
            actually_discussed = [topic_name_map[tid] for tid in actual_topic_ids if tid in topic_name_map]

            # Also check text matching if topic_ids aren't tagged
            if not actually_discussed:
                speaker_full_text = " ".join(s.text for s in p_segs)
                for top in topics:
                    is_match, _ = semantic_matcher.match_topic(speaker_full_text, top.name, threshold=0.25)
                    if is_match and top.name not in actually_discussed:
                        actually_discussed.append(top.name)

            # Match expected topics against actually discussed topics
            covered_expected = []
            speaker_text = " ".join(s.text for s in p_segs)
            for exp in expected_topics:
                # Direct match with discussed topics or text similarity
                matched = False
                for act in actually_discussed:
                    is_m, _ = semantic_matcher.match_topic(act, exp, threshold=0.30)
                    if is_m:
                        covered_expected.append(exp)
                        matched = True
                        break
                if not matched and speaker_text:
                    is_m, _ = semantic_matcher.match_topic(speaker_text, exp, threshold=0.30)
                    if is_m:
                        covered_expected.append(exp)

            coverage_pct = round(
                (len(covered_expected) / max(1, len(expected_topics))) * 100.0,
                1
            )

            # Questions asked count
            q_count = sum(
                1 for s in p_segs
                if any(qp.search(s.text) for qp in self.QUESTION_PATTERNS)
            )

            # Ideas contributed
            p_ideas = sum(1 for i in ideas if i.speaker.lower().strip() == sp_key)

            # Actions assigned
            p_actions = sum(1 for a in action_items if a.owner.lower().strip() == sp_key)

            # Decisions contributed (either named in participants_involved or spoke within 60s of decision)
            p_decisions = 0
            for d in decisions:
                involved = (d.participants_involved or "").lower()
                if sp_key in involved:
                    p_decisions += 1
                else:
                    # Check if spoke near timestamp
                    spoke_near = any(abs(s.start_time - d.timestamp) <= 60.0 for s in p_segs)
                    if spoke_near:
                        p_decisions += 1

            mins = int(p.speaking_time // 60)
            secs = int(p.speaking_time % 60)

            contributions.append({
                "name": p.name,
                "role": role,
                "department": dept,
                "responsibilities": resp,
                "expected_topics": expected_topics,
                "covered_topics": covered_expected,
                "coverage_percentage": coverage_pct,
                "speaking_time": p.speaking_time,
                "speaking_time_display": f"{mins}m {secs:02d}s",
                "speaking_percentage": p.speaking_percentage,
                "ideas_contributed": p_ideas,
                "questions_asked": q_count,
                "action_items_assigned": p_actions,
                "decisions_contributed": p_decisions,
                "neutral_observation": f"Topic coverage is {coverage_pct}% with {len(covered_expected)} of {len(expected_topics)} expected focus areas actively engaged in dialogue."
            })

        return contributions

    def _infer_default_role(self, name: str) -> str:
        name_lower = name.lower()
        if "alice" in name_lower:
            return "Project Manager"
        elif "bob" in name_lower:
            return "Data Scientist"
        elif "charlie" in name_lower:
            return "Backend Developer"
        elif "david" in name_lower:
            return "UI Developer"
        elif "emily" in name_lower:
            return "QA Engineer"
        return "Team Member"

    def _get_default_expected_topics(self, role: str) -> List[str]:
        r = role.lower()
        if "project manager" in r or "pm" in r:
            return ["Project Status & Deliverables", "Timeline & Milestones", "Resource Allocation", "Blockers"]
        elif "data" in r or "scientist" in r:
            return ["Model Performance & Training", "Data Quality", "Feature Engineering", "Inference Latency"]
        elif "backend" in r:
            return ["API Contracts & Architecture", "Database Performance", "CI/CD Pipeline", "Backend Bottlenecks"]
        elif "ui" in r or "frontend" in r:
            return ["UI Components", "User Experience", "Frontend Schema Draft", "API Contract Alignment"]
        elif "qa" in r or "test" in r:
            return ["Automated Test Environments", "Regression Test Coverage", "Playwright Configurations"]
        return ["Domain Contribution", "Operational Alignment", "Deliverables"]


role_contribution_analyzer = RoleContributionAnalyzer()
