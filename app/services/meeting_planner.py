"""Meeting Preparation & Expected Conversation Planning Engine."""

import json
from typing import List, Dict, Any, Optional
from app.utils.config import settings
from app.utils.logging import logger


class MeetingPlanner:
    """Generates pre-meeting expectations, agenda, and role-based contributions."""

    DEFAULT_ROLES_TOPICS = {
        "project manager": [
            "Project status & milestones", "Timeline & sprint delivery dates",
            "Resource allocation & blockers", "Cross-team dependencies", "Final decisions & assignments"
        ],
        "pm": [
            "Project status & milestones", "Timeline & sprint delivery dates",
            "Resource allocation & blockers", "Cross-team dependencies", "Final decisions & assignments"
        ],
        "data scientist": [
            "Dataset & training pipeline", "Model performance & metrics",
            "Data quality & feature engineering", "ML experiment results & inference speed"
        ],
        "backend developer": [
            "API architecture & endpoints", "Database migration & query performance",
            "CI/CD automation & deployments", "Backend service reliability & caching"
        ],
        "ui developer": [
            "Frontend component progress", "UI/UX issues & responsiveness",
            "API contract alignment with frontend", "User interaction performance"
        ],
        "frontend developer": [
            "Frontend component progress", "UI/UX issues & responsiveness",
            "API contract alignment with frontend", "User interaction performance"
        ],
        "qa engineer": [
            "Automated test environments", "Playwright & Pytest regression suites",
            "Release gating & test coverage", "Bug verification & staging validation"
        ],
        "devops": [
            "Infrastructure cost & multi-cloud", "Container runners & Kubernetes",
            "Deployment pipeline security", "Uptime & monitoring alerts"
        ],
        "product manager": [
            "Customer feedback & user priorities", "Beta launch timeline",
            "Feature scope & requirement trade-offs", "Acceptance criteria"
        ]
    }

    def generate_plan(
        self,
        topic: str,
        objective: Optional[str] = None,
        duration_minutes: int = 45,
        department: Optional[str] = None,
        meeting_type: str = "Sprint Planning",
        industry_context: Optional[str] = None,
        participants: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Generate structured meeting plan with suggested agenda and role expectations."""
        participants = participants or []

        # If LLM configured and key is present, try LLM first
        if settings.llm_provider != "demo" and settings.openai_api_key:
            try:
                plan = self._generate_with_llm(
                    topic=topic,
                    objective=objective,
                    duration_minutes=duration_minutes,
                    department=department,
                    meeting_type=meeting_type,
                    industry_context=industry_context,
                    participants=participants
                )
                if plan:
                    return plan
            except Exception as e:
                logger.warning("LLM meeting plan generation failed, falling back to deterministic template: %s", e)

        # Deterministic rule & template based generation
        return self._generate_deterministic_plan(
            topic=topic,
            objective=objective,
            duration_minutes=duration_minutes,
            department=department,
            meeting_type=meeting_type,
            industry_context=industry_context,
            participants=participants
        )

    def _generate_deterministic_plan(
        self,
        topic: str,
        objective: Optional[str] = None,
        duration_minutes: int = 45,
        department: Optional[str] = None,
        meeting_type: str = "Sprint Planning",
        industry_context: Optional[str] = None,
        participants: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Deterministic template generator ensuring 100% offline, zero-dependency reliability."""
        participants = participants or []
        t_clean = topic.strip()
        obj_clean = (objective or f"Align the team and make definitive decisions regarding {t_clean}.").strip()

        # Derive expected topics based on topic keywords and meeting type
        base_topics = []
        is_tech = any(k in t_clean.lower() for k in ["sprint", "tech", "architecture", "migration", "database", "api", "pipeline"])

        if is_tech or "sprint" in meeting_type.lower():
            base_topics = [
                f"Current {t_clean} Status & Deliverables",
                "Automated Deployment Pipeline & CI/CD",
                "Database Migration & Query Performance",
                "Cloud Migration Strategy & Latency Benchmarks",
                "API Error Handling & Response Time Optimization",
                "Resource Allocation & Testing Requirements"
            ]
        elif "budget" in t_clean.lower() or "financial" in t_clean.lower():
            base_topics = [
                "Financial Overview & Budget Allocation",
                "Quarterly Spend vs Forecast",
                "Cost Optimization Areas",
                "Vendor & Infrastructure Expenses",
                "Approval of Revised Capital Outlay"
            ]
        else:
            base_topics = [
                f"Overview & Strategic Context of {t_clean}",
                "Work Completed to Date",
                "Identified Blockers & Operational Risks",
                "Timeline & Deliverable Milestones",
                "Resource Allocation & Task Ownership",
                "Final Decisions & Next Steps"
            ]

        # Expected Questions
        expected_questions = [
            f"What are the critical blockers currently impeding progress on {t_clean}?",
            "What is the realistic timeline for delivering the proposed changes?",
            "Are additional engineering, QA, or infrastructure resources required?",
            "What latency or reliability trade-offs exist with our current approach?",
            "Who is the directly responsible individual for each follow-up deliverable?"
        ]

        # Expected Decisions
        expected_decisions = [
            f"Finalize consensus architectural or strategic approach for {t_clean}",
            "Approve deployment automation tooling and framework selection",
            "Establish firm dates and acceptance criteria for upcoming sprint milestones",
            "Resolve or formally table unresolved infrastructure proposals"
        ]

        # Expected Action Areas
        expected_action_areas = [
            "Backend Engineering & API Architecture",
            "Frontend UI Components & Schema Validation",
            "QA Automated Regression Suites & Environments",
            "Infrastructure Provisioning & CI/CD Pipelines",
            "Documentation & Team Review Artifacts"
        ]

        # Build Suggested Timed Agenda
        total_m = max(15, duration_minutes)
        part_m = max(5, total_m // (len(base_topics) or 1))
        suggested_agenda = []
        curr_min = 0

        for i, top in enumerate(base_topics):
            seg_len = min(part_m, total_m - curr_min)
            if i == len(base_topics) - 1:
                seg_len = total_m - curr_min  # take remainder

            start_str = f"{curr_min:02d}:00"
            end_str = f"{(curr_min + seg_len):02d}:00"
            lead_name = participants[i % len(participants)]["name"] if participants else "Facilitator"

            suggested_agenda.append({
                "time_window": f"{start_str} – {end_str}",
                "title": top,
                "lead": lead_name,
                "objective": f"Deliberate on {top.lower()} and establish action points."
            })
            curr_min += seg_len

        # Feature 3: Role-based expected contributions
        role_expectations = []
        for p in participants:
            name = p.get("name", "Participant")
            role = p.get("role", "Participant")
            dept = p.get("department", department or "Engineering")
            resp = p.get("responsibilities", "")

            # Match role topics
            matched_topics = []
            for r_key, r_tops in self.DEFAULT_ROLES_TOPICS.items():
                if r_key in role.lower():
                    matched_topics.extend(r_tops)
                    break

            if not matched_topics:
                # Custom inference based on responsibilities or generic role
                if "backend" in role.lower() or "backend" in resp.lower():
                    matched_topics = ["API endpoints", "Database architecture", "Backend performance"]
                elif "ui" in role.lower() or "frontend" in role.lower() or "design" in role.lower():
                    matched_topics = ["UI components", "User experience", "Frontend integration"]
                elif "qa" in role.lower() or "test" in role.lower():
                    matched_topics = ["Automated test environments", "Regression test coverage"]
                elif "data" in role.lower() or "ml" in role.lower():
                    matched_topics = ["Dataset quality", "Model performance", "ML pipeline"]
                else:
                    matched_topics = [f"Domain contribution for {role}", "Operational alignment", "Deliverables"]

            role_expectations.append({
                "name": name,
                "role": role,
                "department": dept,
                "responsibilities": resp or f"Lead {role} initiatives and review team deliverables.",
                "expected_topics": matched_topics[:4]
            })

        return {
            "topic": t_clean,
            "objective": obj_clean,
            "duration_minutes": total_m,
            "department": department or "Product & Engineering",
            "meeting_type": meeting_type,
            "industry_context": industry_context or "Software Architecture & Delivery",
            "suggested_agenda": suggested_agenda,
            "expected_topics": base_topics,
            "expected_questions": expected_questions,
            "expected_decisions": expected_decisions,
            "expected_action_areas": expected_action_areas,
            "role_expectations": role_expectations,
            "disclaimer": "AI-generated expected discussion (Predictions / planning suggestions, NOT actual meeting facts)",
            "is_ai_generated": True
        }

    def _generate_with_llm(
        self,
        topic: str,
        objective: Optional[str],
        duration_minutes: int,
        department: Optional[str],
        meeting_type: str,
        industry_context: Optional[str],
        participants: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Optionally call OpenAI LLM if configured."""
        try:
            import openai
            client = openai.OpenAI(api_key=settings.openai_api_key)
            prompt = f"""
You are an expert meeting planning AI. Create a detailed meeting plan in strict JSON format.
Meeting Topic: {topic}
Objective: {objective}
Duration: {duration_minutes} minutes
Department: {department}
Type: {meeting_type}
Industry: {industry_context}
Participants: {json.dumps(participants)}

Return ONLY valid JSON matching this structure:
{{
  "suggested_agenda": [{{"time_window": "00:00 – 10:00", "title": "...", "lead": "...", "objective": "..."}}],
  "expected_topics": ["topic 1", "topic 2", ...],
  "expected_questions": ["question 1", ...],
  "expected_decisions": ["decision 1", ...],
  "expected_action_areas": ["area 1", ...],
  "role_expectations": [
    {{"name": "...", "role": "...", "department": "...", "responsibilities": "...", "expected_topics": ["..."]}}
  ]
}}
"""
            resp = client.chat.completions.create(
                model=settings.openai_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
            )
            raw = resp.choices[0].message.content.strip()
            if raw.startswith("```json"):
                raw = raw[7:]
            if raw.endswith("```"):
                raw = raw[:-3]
            parsed = json.loads(raw.strip())
            parsed["topic"] = topic
            parsed["objective"] = objective
            parsed["duration_minutes"] = duration_minutes
            parsed["department"] = department
            parsed["meeting_type"] = meeting_type
            parsed["industry_context"] = industry_context
            parsed["disclaimer"] = "AI-generated expected discussion (Predictions / planning suggestions, NOT actual meeting facts)"
            parsed["is_ai_generated"] = True
            return parsed
        except Exception as e:
            logger.error("Error invoking OpenAI for meeting plan: %s", e)
            return None


meeting_planner = MeetingPlanner()
