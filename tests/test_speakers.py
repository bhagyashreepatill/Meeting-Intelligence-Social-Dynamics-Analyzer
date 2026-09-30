"""Unit tests for speaker analytics and participation change detection."""

from app.services.transcript_parser import ParsedSegment
from app.services.speaker_analyzer import SpeakerAnalyzer


def test_speaker_analyzer_metrics():
    segments = [
        ParsedSegment(speaker="Alice", start_time=0.0, end_time=30.0, text="Turn 1 Alice", turn_number=1),
        ParsedSegment(speaker="Bob", start_time=30.0, end_time=60.0, text="Turn 2 Bob", turn_number=2),
        ParsedSegment(speaker="Alice", start_time=60.0, end_time=90.0, text="Turn 3 Alice", turn_number=3),
        ParsedSegment(speaker="Charlie", start_time=90.0, end_time=120.0, text="Turn 4 Charlie", turn_number=4),
    ]

    analyzer = SpeakerAnalyzer()
    res = analyzer.analyze(segments, total_duration=120.0)

    participants = res["participants"]
    assert "Alice" in participants
    assert "Bob" in participants
    assert "Charlie" in participants

    # Alice spoke for 60s out of 120s = 50%
    assert participants["Alice"]["speaking_time"] == 60.0
    assert participants["Alice"]["speaking_percentage"] == 50.0
    assert participants["Alice"]["turn_count"] == 2
    assert participants["Alice"]["avg_turn_length"] == 30.0
    assert participants["Alice"]["median_turn_length"] == 30.0

    # Bob spoke for 30s = 25%
    assert participants["Bob"]["speaking_percentage"] == 25.0

    # Quartiles present
    assert "0-25%" in res["quartiles"]
    assert "75-100%" in res["quartiles"]

    # Temporal shifts present
    assert "Alice" in res["temporal_shifts"]
    assert "beginning_pct" in res["temporal_shifts"]["Alice"]

    # Health timeline generated
    assert len(res["health_timeline"]) >= 1
