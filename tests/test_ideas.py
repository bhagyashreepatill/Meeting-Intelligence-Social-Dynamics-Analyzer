"""Unit tests for idea detection, semantic similarity, idea journey, and attribution shift signals."""

from app.services.transcript_parser import ParsedSegment
from app.services.idea_detector import IdeaDetector
from app.services.idea_provenance import IdeaProvenanceTracker


def test_idea_detection_and_overlap():
    segments = [
        ParsedSegment(speaker="Alice", start_time=495.0, end_time=510.0, text="We could automate deployments using GitHub Actions and canary releases.", turn_number=8),
        ParsedSegment(speaker="Charlie", start_time=580.0, end_time=600.0, text="That sounds like a solid idea, containerized runners will give us speed.", turn_number=9),
        ParsedSegment(speaker="Bob", start_time=1120.0, end_time=1140.0, text="Let's automate our deployment pipeline with GitHub Actions and canary releases to minimize downtime.", turn_number=17)
    ]

    detector = IdeaDetector()
    ideas = detector.extract_ideas(segments)
    assert len(ideas) >= 2

    # Check Alice's idea
    assert ideas[0]["speaker"] == "Alice"
    assert "github actions" in ideas[0]["text"].lower()

    # Overlaps
    overlaps = detector.detect_overlaps(ideas, similarity_threshold=0.60)
    assert len(overlaps) >= 1
    ov = overlaps[0]
    assert ov["speaker_a"] == "Alice"
    assert ov["speaker_b"] == "Bob"
    assert ov["similarity_percentage"] >= 65.0


def test_idea_provenance_and_attribution_shift():
    segments = [
        ParsedSegment(speaker="Alice", start_time=495.0, end_time=510.0, text="We could automate deployments using GitHub Actions and canary releases.", turn_number=8),
        ParsedSegment(speaker="Charlie", start_time=580.0, end_time=600.0, text="That sounds like a solid idea, containerized runners will give us speed.", turn_number=9),
        ParsedSegment(speaker="Bob", start_time=1120.0, end_time=1140.0, text="Let's automate our deployment pipeline with GitHub Actions and canary releases to minimize downtime.", turn_number=17)
    ]

    detector = IdeaDetector()
    ideas = detector.extract_ideas(segments)
    overlaps = detector.detect_overlaps(ideas, similarity_threshold=0.60)

    decisions = [
        {"id": 1, "text": "Adopt GitHub Actions for our deployment automation pipeline", "timestamp": 1265.0}
    ]
    actions = [
        {"task": "Build the initial GitHub Actions CI/CD workflow", "owner": "Charlie", "due_date": "2026-09-25", "timestamp": 735.0, "evidence": "I'll build the workflow"}
    ]

    tracker = IdeaProvenanceTracker()
    journeys = tracker.build_idea_journeys(ideas, segments, overlaps, decisions, actions)
    assert len(journeys) >= 1
    journey = journeys[0]
    assert journey["originator"] == "Alice"
    assert journey["has_decision"] is True
    assert journey["has_action"] is True

    # Attribution shift
    shifts = tracker.detect_attribution_shifts(overlaps, segments)
    assert len(shifts) >= 1
    shift = shifts[0]
    assert shift["original_speaker"] == "Alice"
    assert shift["later_speaker"] == "Bob"
    assert shift["explicit_attribution"] == "Not detected"
    assert "Potential Attribution Shift" in shift["signal_label"]
