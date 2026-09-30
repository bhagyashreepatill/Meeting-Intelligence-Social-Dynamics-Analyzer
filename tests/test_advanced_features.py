"""Tests for the 7 new meeting intelligence features: attendance, planning, role contributions,
topic coverage, agenda drift, participation gaps, recurring topics, and export enhancements.
"""

import json
from fastapi.testclient import TestClient
from app.main import app
from app.services.semantic_matcher import semantic_matcher
from app.services.attendance_analyzer import AttendanceAnalyzer
from app.services.meeting_planner import meeting_planner
from app.services.role_contribution_analyzer import role_contribution_analyzer
from app.services.topic_coverage_analyzer import topic_coverage_analyzer
from app.services.agenda_drift_detector import agenda_drift_detector
from app.services.participation_gap_analyzer import participation_gap_analyzer
from app.services.recurring_topics_analyzer import recurring_topics_analyzer
from app.models import Meeting, Participant, TranscriptSegment, Topic, Decision, ActionItem, Attendance

client = TestClient(app)


def test_semantic_matcher():
    """Test token normalization and semantic similarity matching."""
    sim1 = semantic_matcher.similarity("API Error Handling", "Backend API response time and errors")
    assert sim1 > 0.30

    sim2 = semantic_matcher.similarity("Database migration to Postgres", "Database concurrency bottlenecks")
    assert sim2 > 0.25

    is_match, score = semantic_matcher.match_topic("Holiday party catering lunch", "Office Event & Catering Planning", threshold=0.25)
    assert is_match is True
    assert score > 0.25


def test_attendance_analyzer():
    """Test attendance duration, punctuality, late arrivals, and early departures."""
    analyzer = AttendanceAnalyzer()

    meeting = Meeting(id=1, duration=2700.0, title="Sprint Sync")
    p_bob = Participant(id=1, meeting_id=1, name="Bob", role="Data Scientist", employee_id="EMP-102")
    p_emily = Participant(id=2, meeting_id=1, name="Emily", role="QA Engineer", employee_id="EMP-105")

    # Bob: joined 300s (5 min late), left at 2700s
    att_bob = Attendance(
        meeting_id=1, participant_id=1, employee_name="Bob",
        join_time=300.0, leave_time=2700.0, is_verified=True
    )
    # Emily: joined 0s, left at 1680s (28 min, left 17 min early)
    att_emily = Attendance(
        meeting_id=1, participant_id=2, employee_name="Emily",
        join_time=0.0, leave_time=1680.0, is_verified=True
    )

    summary = analyzer.compute_attendance(
        meeting=meeting,
        participants=[p_bob, p_emily],
        segments=[],
        verified_attendance=[att_bob, att_emily]
    )

    assert summary["total_participants"] == 2
    assert summary["verified_count"] == 2
    assert summary["late_arrivals_count"] == 1
    assert summary["early_departures_count"] == 1

    bob_record = next(r for r in summary["records"] if r["employee_name"] == "Bob")
    assert bob_record["status"] == "Late"
    assert bob_record["late_duration"] == 300.0
    assert bob_record["attendance_percentage"] == 88.9
    assert bob_record["verification_label"] == "Verified attendance"

    emily_record = next(r for r in summary["records"] if r["employee_name"] == "Emily")
    assert emily_record["status"] == "Left early"
    assert emily_record["early_leave_duration"] == 1020.0  # 17 min
    assert emily_record["attendance_percentage"] == 62.2


def test_meeting_planner():
    """Test pre-meeting expected conversation and agenda generation."""
    plan = meeting_planner.generate_plan(
        topic="Q4 Sprint Planning & Architecture Sync",
        objective="Finalize CI/CD and database migration",
        duration_minutes=45,
        department="Engineering",
        meeting_type="Sprint Planning",
        participants=[
            {"name": "Alice", "role": "Project Manager"},
            {"name": "Charlie", "role": "Backend Developer"}
        ]
    )

    assert len(plan["expected_topics"]) >= 4
    assert len(plan["expected_questions"]) >= 3
    assert len(plan["expected_decisions"]) >= 2
    assert len(plan["expected_action_areas"]) >= 3
    assert len(plan["suggested_agenda"]) >= 3
    assert len(plan["role_expectations"]) == 2
    assert "AI-generated expected discussion" in plan["disclaimer"]


def test_topic_coverage_score():
    """Test topic coverage analyzer and explainable reason."""
    meeting = Meeting(id=1, duration=2700.0, title="Sync")
    t1 = Topic(id=1, meeting_id=1, name="Automated Deployment Pipeline", start_time=500.0, end_time=1300.0, status="Resolved", evidence="GitHub actions adopted")
    t2 = Topic(id=2, meeting_id=1, name="Database Migration to PostgreSQL", start_time=1400.0, end_time=1800.0, status="Resolved", evidence="PostgreSQL chosen")
    t3 = Topic(id=3, meeting_id=1, name="Cloud Migration Strategy", start_time=1850.0, end_time=2400.0, status="Unresolved", evidence="Tabled for next month")

    segs = [
        TranscriptSegment(id=1, meeting_id=1, speaker_name="Alice", start_time=500.0, end_time=560.0, turn_number=1, text="We should automate deployments using GitHub Actions.")
    ]

    res = topic_coverage_analyzer.analyze_coverage(
        meeting=meeting,
        topics=[t1, t2, t3],
        segments=segs,
        decisions=[],
        action_items=[],
        plan=None
    )

    assert res["total_expected"] > 0
    assert res["covered_count"] >= 2
    assert res["coverage_percentage"] > 0.0
    assert "covered" in res["explainable_reason"]
    assert "█" in res["coverage_bar"]


def test_agenda_drift_detector():
    """Test off-topic drift detection and timeline generation."""
    meeting = Meeting(id=1, duration=2700.0, title="Sprint")
    segs = [
        TranscriptSegment(id=1, meeting_id=1, speaker_name="Alice", start_time=0.0, end_time=100.0, turn_number=1, text="Let's align on sprint deliverables."),
        TranscriptSegment(id=2, meeting_id=1, speaker_name="Charlie", start_time=945.0, end_time=980.0, turn_number=2, text="Did anyone submit catering preferences for our holiday party and lunch venue?"),
        TranscriptSegment(id=3, meeting_id=1, speaker_name="Bob", start_time=985.0, end_time=1015.0, turn_number=3, text="I voted for the Italian buffet catering on the party spreadsheet."),
        TranscriptSegment(id=4, meeting_id=1, speaker_name="Alice", start_time=1020.0, end_time=1060.0, turn_number=4, text="Let's refocus on sprint deliverables for now.")
    ]

    drift_res = agenda_drift_detector.detect_drifts(meeting, segs)
    assert drift_res["drift_detected"] is True
    assert drift_res["total_drift_incidents"] == 1
    assert "Catering" in drift_res["drifts"][0]["detected_topic"]
    assert drift_res["drifts"][0]["confidence"] > 0.70
    assert len(drift_res["timeline"]) >= 2


def test_participation_gap_analyzer():
    """Test low speaking time detection under neutral governance."""
    meeting = Meeting(id=1, duration=2700.0, title="Sprint")
    p1 = Participant(id=1, meeting_id=1, name="Alice", speaking_time=1200.0, speaking_percentage=44.4, turn_count=15)
    p2 = Participant(id=2, meeting_id=1, name="Charlie", speaking_time=1000.0, speaking_percentage=37.0, turn_count=12)
    p3 = Participant(id=3, meeting_id=1, name="Emily", speaking_time=110.0, speaking_percentage=4.1, turn_count=3)

    segs = [
        TranscriptSegment(id=1, meeting_id=1, speaker_name="Emily", start_time=300.0, end_time=330.0, turn_number=1, text="We need automated test environments.")
    ]

    res = participation_gap_analyzer.analyze_gaps(
        meeting=meeting,
        participants=[p1, p2, p3],
        segments=segs
    )

    assert res["gaps_count"] == 1
    gap = res["gaps"][0]
    assert gap["participant_name"] == "Emily"
    assert gap["detection_label"] == "Low observed participation"
    assert "4.1%" in gap["neutral_explanation"]
    assert "Consider" in gap["facilitation_suggestion"]


def test_full_api_workflow_and_exports():
    """Test end-to-end API endpoints and export functionality."""
    # Seed demo meeting first
    seed_res = client.post("/api/meetings/seed-demo")
    assert seed_res.status_code == 200
    meeting_id = seed_res.json()["meeting_id"]

    # 1. Feature 1: Attendance API
    att_res = client.get(f"/api/meetings/{meeting_id}/attendance")
    assert att_res.status_code == 200
    att_data = att_res.json()
    assert att_data["total_participants"] >= 3
    assert att_data["verified_count"] >= 3

    # Update Bob attendance
    bob = next(p for p in att_data["records"] if p["employee_name"] == "Bob")
    put_att = client.put(
        f"/api/meetings/{meeting_id}/attendance/{bob['participant_id']}",
        json={"join_time": 300.0, "leave_time": 2700.0, "role": "Lead Data Scientist"}
    )
    assert put_att.status_code == 200
    assert put_att.json()["role"] == "Lead Data Scientist"

    # 2. Feature 2: Meeting Plan API
    plan_gen = client.post(
        "/api/meetings/meeting-plan/generate",
        json={
            "topic": "Frontend Performance Optimization",
            "duration_minutes": 30,
            "participants": [{"name": "David", "role": "UI Developer"}]
        }
    )
    assert plan_gen.status_code == 200
    assert len(plan_gen.json()["expected_topics"]) >= 3

    plan_get = client.get(f"/api/meetings/{meeting_id}/meeting-plan")
    assert plan_get.status_code == 200
    assert len(plan_get.json()["expected_topics"]) >= 3

    # 3. Feature 3: Role Contributions API
    roles_res = client.get(f"/api/meetings/{meeting_id}/role-contributions")
    assert roles_res.status_code == 200
    assert len(roles_res.json()["contributions"]) >= 3

    # 4. Feature 4: Topic Coverage API
    cov_res = client.get(f"/api/meetings/{meeting_id}/topic-coverage")
    assert cov_res.status_code == 200
    assert cov_res.json()["coverage_percentage"] > 0.0

    # 5. Feature 5: Agenda Drift API & Feedback
    drift_res = client.get(f"/api/meetings/{meeting_id}/agenda-drift")
    assert drift_res.status_code == 200
    assert drift_res.json()["drift_detected"] is True

    drift_id = drift_res.json()["drifts"][0]["id"]
    fb_res = client.post(
        f"/api/meetings/{meeting_id}/agenda-drift/{drift_id}/feedback",
        json={"feedback": "confirmed_drift"}
    )
    assert fb_res.status_code == 200
    assert fb_res.json()["feedback"] == "confirmed_drift"

    # 6. Feature 6: Participation Gaps API
    gaps_res = client.get(f"/api/meetings/{meeting_id}/participation-gaps")
    assert gaps_res.status_code == 200
    assert gaps_res.json()["gaps_count"] >= 1

    # 7. Feature 7: Recurring Topics (Per-Meeting & Global)
    rec_m_res = client.get(f"/api/meetings/{meeting_id}/recurring-topics")
    assert rec_m_res.status_code == 200

    rec_g_res = client.get("/api/analytics/recurring-topics")
    assert rec_g_res.status_code == 200
    assert rec_g_res.json()["total_recurring_topics"] >= 1

    # 8. Export Enhancements (JSON & CSV)
    json_exp = client.get(f"/api/meetings/{meeting_id}/export?format=json")
    assert json_exp.status_code == 200
    json_data = json_exp.json()
    assert "attendance" in json_data
    assert "topic_coverage" in json_data
    assert "role_contributions" in json_data
    assert "agenda_drift" in json_data
    assert "participation_gaps" in json_data
    assert "recurring_topics" in json_data

    csv_exp = client.get(f"/api/meetings/{meeting_id}/export?format=csv")
    assert csv_exp.status_code == 200
    csv_text = csv_exp.text
    assert "--- ATTENDANCE ---" in csv_text
    assert "--- TOPIC COVERAGE ---" in csv_text
    assert "--- ROLE CONTRIBUTIONS ---" in csv_text
    assert "--- AGENDA DRIFT ---" in csv_text
    assert "--- PARTICIPATION GAPS ---" in csv_text
