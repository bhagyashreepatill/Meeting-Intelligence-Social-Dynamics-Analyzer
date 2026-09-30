"""Unit tests for meeting dynamics replay engine and dynamic social graph slicing."""

from app.services.transcript_parser import ParsedSegment
from app.services.meeting_replay import MeetingReplayEngine


def test_meeting_replay_state_slicing():
    engine = MeetingReplayEngine()

    segments = [
        ParsedSegment(speaker="Alice", start_time=0.0, end_time=30.0, text="Alice speaking turn 1", turn_number=1),
        ParsedSegment(speaker="Bob", start_time=30.0, end_time=60.0, text="Bob speaking turn 2", turn_number=2),
        ParsedSegment(speaker="Charlie", start_time=60.0, end_time=90.0, text="Charlie speaking turn 3", turn_number=3),
    ]
    participants = {
        "Alice": {"speaking_time": 30.0, "avatar_color": "#4f46e5"},
        "Bob": {"speaking_time": 30.0, "avatar_color": "#06b6d4"},
        "Charlie": {"speaking_time": 30.0, "avatar_color": "#10b981"}
    }
    ideas = [
        {"id": 1, "speaker": "Alice", "text": "Canary deployment idea", "timestamp": 15.0}
    ]
    interruptions = [
        {"speaker_a": "Bob", "speaker_b": "Alice", "timestamp": 30.5, "confidence": 0.82}
    ]
    decisions = [
        {"id": 1, "text": "Adopt canary deployment", "timestamp": 75.0}
    ]
    actions = [
        {"task": "Build script", "owner": "Charlie", "timestamp": 80.0, "due_date": "2026-09-25"}
    ]
    topics = [
        {"id": 1, "name": "Deployment Discussion", "start_time": 0.0, "end_time": 90.0}
    ]

    # At t = 20s (During Alice's turn)
    state_20 = engine.get_state_at_time(
        20.0, segments, participants, ideas, interruptions, decisions, actions, topics
    )
    assert state_20["active_speaker"] == "Alice"
    assert state_20["counts"]["ideas"] == 1
    assert state_20["counts"]["interruptions"] == 0
    assert state_20["counts"]["decisions"] == 0
    assert state_20["active_topic"] == "Deployment Discussion"

    # At t = 50s (During Bob's turn)
    state_50 = engine.get_state_at_time(
        50.0, segments, participants, ideas, interruptions, decisions, actions, topics
    )
    assert state_50["active_speaker"] == "Bob"
    assert state_50["counts"]["interruptions"] == 1
    assert state_50["counts"]["decisions"] == 0

    # At t = 85s (During Charlie's turn, after decision and action item)
    state_85 = engine.get_state_at_time(
        85.0, segments, participants, ideas, interruptions, decisions, actions, topics
    )
    assert state_85["active_speaker"] == "Charlie"
    assert state_85["counts"]["decisions"] == 1
    assert state_85["counts"]["action_items"] == 1
    assert len(state_85["graph"]["nodes"]) == 3

    # Keyframes
    keyframes = engine.get_keyframes(segments, ideas, interruptions, decisions, actions)
    assert len(keyframes) >= 6
