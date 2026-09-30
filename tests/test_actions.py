"""Unit tests for action item extraction, owner detection, and due date normalization."""

from datetime import datetime
from app.services.transcript_parser import ParsedSegment
from app.services.owner_detector import OwnerDetector
from app.services.date_extractor import DateExtractor
from app.services.action_extractor import ActionItemExtractor


def test_owner_detector():
    detector = OwnerDetector(known_participants=["Alice", "Bob", "Charlie", "David", "Emily", "Sarah"])

    # Self-assignment
    owner, conf = detector.detect_owner("I'll prepare the report.", current_speaker="Alice")
    assert owner == "Alice"
    assert conf >= 0.90

    # Direct address
    owner, conf = detector.detect_owner("John, can you create the Jira ticket?", current_speaker="Alice")
    assert owner == "John"
    assert conf >= 0.90

    # 3rd party
    owner, conf = detector.detect_owner("Sarah will handle deployment.", current_speaker="Emily")
    assert owner == "Sarah"
    assert conf >= 0.90

    # Ambiguous / General: Strictly Unknown
    owner, conf = detector.detect_owner("We should improve the API.", current_speaker="Alice")
    assert owner == "Unknown"
    assert conf == 0.0


def test_date_extractor():
    ref_date = datetime(2026, 9, 23, 10, 0, 0)  # Wednesday, Sep 23, 2026
    extractor = DateExtractor()

    # Tomorrow (Sep 24, 2026)
    display, iso = extractor.extract_due_date("I will send it by tomorrow.", ref_date)
    assert iso == "2026-09-24"

    # Friday (Sep 25, 2026)
    display, iso = extractor.extract_due_date("I'll have it ready by Friday.", ref_date)
    assert iso == "2026-09-25"

    # Today
    display, iso = extractor.extract_due_date("We need this today before 5 PM.", ref_date)
    assert iso == "2026-09-23"

    # No date
    display, iso = extractor.extract_due_date("We should improve the database queries.", ref_date)
    assert iso == "Unknown"
    assert display == "Unknown"


def test_action_item_extractor():
    ref_date = datetime(2026, 9, 23, 10, 0, 0)
    extractor = ActionItemExtractor(
        known_participants=["Alice", "Bob", "Charlie", "David", "Emily", "Sarah"],
        reference_date=ref_date
    )

    segments = [
        ParsedSegment(speaker="David", start_time=295.0, end_time=305.0, text="I'll publish the schema draft by tomorrow afternoon so backend can review it.", turn_number=5),
        ParsedSegment(speaker="Emily", start_time=920.0, end_time=930.0, text="Sarah will handle writing the test runner configurations for Playwright by next Monday.", turn_number=14),
        ParsedSegment(speaker="Alice", start_time=2700.0, end_time=2710.0, text="We should improve the API error handling before public launch.", turn_number=41),
        ParsedSegment(speaker="Bob", start_time=1790.0, end_time=1800.0, text="I'll create the Jira epic and tickets today before 5 PM.", turn_number=28)
    ]

    actions = extractor.extract(segments)
    assert len(actions) >= 3

    # Check David's task
    david_tasks = [a for a in actions if a["owner"] == "David"]
    assert len(david_tasks) == 1
    assert "publish the schema draft" in david_tasks[0]["task"].lower()
    assert david_tasks[0]["due_date"] == "2026-09-24"

    # Check Sarah's task
    sarah_tasks = [a for a in actions if a["owner"] == "Sarah"]
    assert len(sarah_tasks) == 1
    assert "Playwright" in sarah_tasks[0]["evidence"]

    # Check unassigned / ambiguous task: Strictly Unknown!
    unassigned = [a for a in actions if a["owner"] == "Unknown"]
    assert len(unassigned) >= 1
    assert "improve the api" in unassigned[0]["task"].lower()
    assert unassigned[0]["due_date"] == "Unknown"
