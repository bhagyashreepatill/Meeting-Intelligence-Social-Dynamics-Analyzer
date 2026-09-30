"""Integration tests for all FastAPI endpoints, integrations, and analysis pipelines."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database.database import init_db

# Ensure tables exist
init_db()
client = TestClient(app)


def test_health_check():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["demo_mode"] is True


def test_seed_demo_and_lifecycle():
    # 1. Seed Demo Meeting
    res = client.post("/api/meetings/seed-demo")
    assert res.status_code == 200
    data = res.json()
    meeting_id = data["meeting_id"]
    assert meeting_id is not None

    # 2. List Meetings
    res = client.get("/api/meetings")
    assert res.status_code == 200
    meetings = res.json()
    assert any(m["id"] == meeting_id for m in meetings)

    # 3. Get Meeting Details
    res = client.get(f"/api/meetings/{meeting_id}")
    assert res.status_code == 200
    detail = res.json()
    assert len(detail["participants"]) >= 5
    assert len(detail["action_items"]) >= 3
    assert len(detail["decisions"]) >= 2
    assert len(detail["topics"]) >= 3

    # 4. Get Transcript
    res = client.get(f"/api/meetings/{meeting_id}/transcript")
    assert res.status_code == 200
    segs = res.json()
    assert len(segs) > 30

    # 5. Action Items Confirmation & Review Workflow
    res = client.get(f"/api/meetings/{meeting_id}/action-items")
    assert res.status_code == 200
    items = res.json()
    assert len(items) > 0
    item_id = items[0]["id"]

    # Accept action item
    accept_res = client.post(f"/api/action-items/{item_id}/accept")
    assert accept_res.status_code == 200
    assert accept_res.json()["status"] == "Confirmed"

    # Reject another item
    if len(items) > 1:
        item2_id = items[1]["id"]
        reject_res = client.post(f"/api/action-items/{item2_id}/reject")
        assert reject_res.status_code == 200
        assert reject_res.json()["status"] == "Rejected"

    # Edit action item
    edit_res = client.put(f"/api/action-items/{item_id}", json={
        "task": "Updated task description",
        "priority": "High"
    })
    assert edit_res.status_code == 200
    assert edit_res.json()["task"] == "Updated task description"
    assert edit_res.json()["priority"] == "High"

    # 6. Ideas & Provenance
    res = client.get(f"/api/meetings/{meeting_id}/ideas")
    assert res.status_code == 200
    assert len(res.json()["ideas"]) >= 2

    # Idea Journeys
    res = client.get(f"/api/meetings/{meeting_id}/idea-journeys")
    assert res.status_code == 200
    journeys = res.json()
    assert len(journeys) >= 1
    assert journeys[0]["has_decision"] is True

    # Attribution Shifts
    res = client.get(f"/api/meetings/{meeting_id}/attribution-shifts")
    assert res.status_code == 200
    shifts = res.json()
    assert len(shifts) >= 1
    assert "Potential Attribution Shift" in shifts[0]["signal_label"]

    # 7. Social Graph
    res = client.get(f"/api/meetings/{meeting_id}/social-graph")
    assert res.status_code == 200
    graph = res.json()
    assert len(graph["nodes"]) >= 5
    assert len(graph["edges"]) >= 3

    # 8. Meeting Dynamics Replay
    res = client.get(f"/api/meetings/{meeting_id}/replay?t=600")
    assert res.status_code == 200
    replay = res.json()
    assert replay["current_time"] == 600.0
    assert "cumulative_speaking" in replay
    assert len(replay["keyframes"]) >= 10

    # 9. Integrations (Slack, Jira, Trello) in Demo Mode
    slack_res = client.post("/api/integrations/slack", json={"meeting_id": meeting_id})
    assert slack_res.status_code == 200
    assert slack_res.json()["status"] == "success"

    jira_res = client.post("/api/integrations/jira", json={"meeting_id": meeting_id})
    assert jira_res.status_code == 200
    assert jira_res.json()["status"] == "success"

    trello_res = client.post("/api/integrations/trello", json={"meeting_id": meeting_id})
    assert trello_res.status_code == 200
    assert trello_res.json()["status"] == "success"

    # 10. Export JSON & CSV
    json_export = client.get(f"/api/meetings/{meeting_id}/export?format=json")
    assert json_export.status_code == 200
    assert "meeting" in json_export.json()

    csv_export = client.get(f"/api/meetings/{meeting_id}/export?format=csv")
    assert csv_export.status_code == 200
    assert "text/csv" in csv_export.headers["content-type"]

    # 11. Meeting Comparison
    compare_res = client.get(f"/api/meetings/compare/metrics?ids={meeting_id}")
    assert compare_res.status_code == 200
    assert len(compare_res.json()) == 1
