"""Unit tests for interruption detector and social interaction graph."""

from app.services.transcript_parser import ParsedSegment
from app.services.interruption_detector import InterruptionDetector
from app.services.social_graph import SocialGraphService


def test_interruption_detection():
    detector = InterruptionDetector()
    segments = [
        ParsedSegment(speaker="Alice", start_time=100.0, end_time=110.0, text="Now looking at the infrastructure overhead--", turn_number=1),
        ParsedSegment(speaker="Bob", start_time=110.2, end_time=120.0, text="Can I jump in here? Looking at customer feedback, reliability is top priority.", turn_number=2),
        ParsedSegment(speaker="Charlie", start_time=130.0, end_time=145.0, text="I agree with that point.", turn_number=3)
    ]

    interruptions = detector.detect_interruptions(segments)
    assert len(interruptions) == 1
    item = interruptions[0]
    assert item["speaker_a"] == "Bob"  # Interrupter
    assert item["speaker_b"] == "Alice"  # Interrupted
    assert item["confidence"] >= 0.70
    assert "Alice's sentence appears incomplete" in item["evidence"]


def test_social_graph_generation():
    service = SocialGraphService()
    participants = {
        "Alice": {"speaking_time": 100.0, "speaking_percentage": 50.0, "turn_count": 5, "avatar_color": "#4f46e5"},
        "Bob": {"speaking_time": 60.0, "speaking_percentage": 30.0, "turn_count": 3, "avatar_color": "#06b6d4"},
        "Charlie": {"speaking_time": 40.0, "speaking_percentage": 20.0, "turn_count": 2, "avatar_color": "#10b981"}
    }
    segments = [
        ParsedSegment(speaker="Alice", start_time=0.0, end_time=10.0, text="Bob, can you check this?", turn_number=1),
        ParsedSegment(speaker="Bob", start_time=10.0, end_time=20.0, text="Sure Alice, checking now.", turn_number=2),
    ]
    interruptions = [
        {"speaker_a": "Bob", "speaker_b": "Alice", "confidence": 0.85}
    ]

    graph = service.build_graph(participants, segments, interruptions)
    assert len(graph["nodes"]) == 3
    assert len(graph["edges"]) >= 2
    edge_types = {e["type"] for e in graph["edges"]}
    assert "RESPONSE" in edge_types
    assert "INTERRUPTION" in edge_types
