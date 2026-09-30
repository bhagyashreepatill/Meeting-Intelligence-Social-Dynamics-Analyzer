"""Unit tests for transcript parser and timestamp normalizer."""

import os
import pytest
from app.services.transcript_parser import (
    TranscriptParser,
    parse_timestamp_to_seconds,
    clean_speaker_name
)


def test_parse_timestamp_to_seconds():
    assert parse_timestamp_to_seconds("00:01:10") == 70.0
    assert parse_timestamp_to_seconds("01:10") == 70.0
    assert parse_timestamp_to_seconds("01:02:03.500") == 3723.5
    assert parse_timestamp_to_seconds("00:00:05,250") == 5.25
    assert parse_timestamp_to_seconds("invalid") == 0.0


def test_clean_speaker_name():
    assert clean_speaker_name("Alice:") == "Alice"
    assert clean_speaker_name("[Bob]") == "Bob"
    assert clean_speaker_name("charlie") == "Charlie"
    assert clean_speaker_name("David Smith (Engineering)") == "David Smith"


def test_parse_sample_meeting_file():
    sample_path = os.path.join(os.path.dirname(__file__), "..", "sample_data", "sample_meeting.txt")
    with open(sample_path, "r", encoding="utf-8") as f:
        content = f.read()

    parser = TranscriptParser()
    result = parser.parse(content)

    assert len(result.segments) > 30
    assert "Alice" in result.participants
    assert "Bob" in result.participants
    assert "Charlie" in result.participants
    assert "David" in result.participants
    assert "Emily" in result.participants
    assert result.duration > 2000.0  # Around 45 minutes = 2700s


def test_parse_vtt_format():
    vtt = """WEBVTT

00:01:00.000 --> 00:01:05.000
<v Alice>Hello everyone welcome to the meeting.

00:01:06.000 --> 00:01:10.000
Bob: Thanks Alice, glad to be here.
"""
    parser = TranscriptParser()
    result = parser.parse(vtt)
    assert len(result.segments) == 2
    assert result.segments[0].speaker == "Alice"
    assert result.segments[0].start_time == 60.0
    assert result.segments[1].speaker == "Bob"
    assert result.segments[1].start_time == 66.0


def test_parse_teams_multiline_format():
    teams = """Alice Smith 01:15
Good morning team.

Bob Jones 01:25
Good morning Alice.
"""
    parser = TranscriptParser()
    result = parser.parse(teams)
    assert len(result.segments) == 2
    assert "Alice Smith" in result.participants
    assert "Bob Jones" in result.participants
