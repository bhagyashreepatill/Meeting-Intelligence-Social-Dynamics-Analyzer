"""Unit tests for decision detection and unresolved topic tracking."""

from app.services.transcript_parser import ParsedSegment
from app.services.decision_detector import DecisionDetector
from app.services.topic_detector import TopicDetector


def test_decision_detection():
    segments = [
        ParsedSegment(speaker="Alice", start_time=1260.0, end_time=1275.0, text="So the decision is made: we will adopt GitHub Actions for our deployment automation pipeline.", turn_number=20),
        ParsedSegment(speaker="Alice", start_time=1710.0, end_time=1725.0, text="Agreed. We will use PostgreSQL for the analytics service.", turn_number=27)
    ]

    detector = DecisionDetector()
    decisions = detector.detect_decisions(segments)
    assert len(decisions) == 2
    assert "github actions" in decisions[0]["text"].lower()
    assert "postgresql" in decisions[1]["text"].lower()
    assert decisions[0]["confidence"] >= 0.90


def test_topic_detection_and_unresolved():
    segments = [
        ParsedSegment(speaker="Alice", start_time=0.0, end_time=100.0, text="Let's do a quick alignment on Q4 sprint goals.", turn_number=1),
        ParsedSegment(speaker="Alice", start_time=1200.0, end_time=1250.0, text="Moving on to the database layer. We need PostgreSQL.", turn_number=10),
        ParsedSegment(speaker="Charlie", start_time=1860.0, end_time=1920.0, text="Now regarding the cloud migration strategy: should we migrate to GCP?", turn_number=15),
        ParsedSegment(speaker="Bob", start_time=2420.0, end_time=2460.0, text="Let's table the cloud migration strategy for next month's planning cycle until we have cost benchmarks.", turn_number=20),
        ParsedSegment(speaker="Alice", start_time=2500.0, end_time=2530.0, text="Agreed, cloud migration strategy remains unresolved for now.", turn_number=21),
        ParsedSegment(speaker="Alice", start_time=2600.0, end_time=2700.0, text="To wrap up, let's review action items.", turn_number=25)
    ]

    decisions = [
        {"id": 1, "text": "We will use PostgreSQL", "timestamp": 1220.0}
    ]

    detector = TopicDetector()
    topics = detector.segment_topics(segments, decisions=decisions)
    assert len(topics) >= 3

    # Check database topic is resolved
    db_topic = next((t for t in topics if "database" in t["name"].lower()), None)
    assert db_topic is not None
    assert db_topic["status"] == "Resolved"

    # Check cloud migration topic is Unresolved
    cloud_topic = next((t for t in topics if "cloud migration" in t["name"].lower()), None)
    assert cloud_topic is not None
    assert cloud_topic["status"] == "Unresolved"
    assert "remains unresolved" in cloud_topic["evidence"].lower() or "table" in cloud_topic["evidence"].lower()
