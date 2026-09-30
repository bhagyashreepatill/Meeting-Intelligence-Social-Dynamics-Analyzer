"""Multi-platform transcript parser with timestamp normalization and speaker identification."""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from app.utils.logging import logger


@dataclass
class ParsedSegment:
    """Normalized transcript segment."""
    speaker: str
    start_time: float  # In seconds from meeting start
    end_time: float    # In seconds from meeting start
    text: str
    turn_number: int


@dataclass
class ParsedTranscript:
    """Complete parsed transcript structure."""
    segments: List[ParsedSegment] = field(default_factory=list)
    participants: List[str] = field(default_factory=list)
    duration: float = 0.0
    detected_format: str = "generic"


def parse_timestamp_to_seconds(ts_str: str) -> float:
    """
    Convert varied timestamp strings to float seconds.
    Supports:
      - 01:23:45.678 or 01:23:45,678 (HH:MM:SS.mmm)
      - 23:45.678 (MM:SS.mmm)
      - 01:23:45 (HH:MM:SS)
      - 23:45 (MM:SS)
      - 1:23 (M:SS)
    """
    ts = ts_str.strip().replace(",", ".")
    parts = ts.split(":")
    try:
        if len(parts) == 3:
            h = float(parts[0])
            m = float(parts[1])
            s = float(parts[2])
            return h * 3600 + m * 60 + s
        elif len(parts) == 2:
            m = float(parts[0])
            s = float(parts[1])
            return m * 60 + s
        elif len(parts) == 1:
            return float(parts[0])
    except ValueError:
        pass
    return 0.0


def clean_speaker_name(name: str) -> str:
    """Normalize and clean speaker names."""
    name = name.strip().strip(":").strip()
    # If whole name is enclosed in brackets e.g. [Bob] or (Alice)
    if (name.startswith("[") and name.endswith("]")) or (name.startswith("(") and name.endswith(")")):
        name = name[1:-1].strip()

    # Remove email addresses or parenthetical roles/titles if attached
    name = re.sub(r"\s*<[^>]+>", "", name)
    name = re.sub(r"\s*\([^\)]+\)", "", name)
    name = re.sub(r"[\(\)\[\]\{\}\<\>:]+", "", name).strip()
    return name.title() if name.islower() else name


class TranscriptParser:
    """Parser for Zoom, Teams, Meet, and custom meeting transcripts."""

    # Regex patterns for different formats
    # Pattern 1: [00:01:10] Alice: Text or [00:01:10] Alice - Text
    BRACKET_TIMESTAMP_SPEAKER = re.compile(
        r"^\[(?P<time>\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?)\]\s*(?P<speaker>[^:\-\n]+)[:\-]\s*(?P<text>.*)$",
        re.MULTILINE
    )

    # Pattern 2: Alice [00:01:10]: Text or Alice (00:01:10): Text
    SPEAKER_PAREN_TIMESTAMP = re.compile(
        r"^(?P<speaker>[^\[\(\n]+)\s*[\(\[](?P<time>\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?)[\)\]][: ]\s*(?P<text>.*)$",
        re.MULTILINE
    )

    # Pattern 3: 00:01:10 Alice: Text
    BARE_TIMESTAMP_SPEAKER = re.compile(
        r"^(?P<time>\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?)\s+(?P<speaker>[^:\-\n]+)[:\-]\s*(?P<text>.*)$",
        re.MULTILINE
    )

    # Pattern 4: WebVTT / SRT Cue Pattern:
    # 00:01:23.450 --> 00:01:28.120\nAlice: Hello
    VTT_CUE = re.compile(
        r"(?P<start>\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?)\s*-->\s*(?P<end>\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?)\s*\n(?:<v\s+)?(?P<speaker>[^>:\n]+)?>?:?\s*(?P<text>.+?)(?=\n\n|\Z)",
        re.DOTALL
    )

    # Pattern 5: Teams/Meet multi-line format:
    # Alice Smith 12:42 PM\nHello world or Alice Smith 01:23\nHello world
    MULTILINE_HEADER = re.compile(
        r"^(?P<speaker>[A-Za-z\s\.\-]+?)\s+(?P<time>\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AaPp][Mm])?)\s*\n(?P<text>[^\n]+(?:\n(?![A-Za-z\s\.\-]+?\s+\d{1,2}:\d{2})[^\n]+)*)",
        re.MULTILINE
    )

    def parse(self, raw_content: str) -> ParsedTranscript:
        """Parse raw transcript string and return a normalized ParsedTranscript."""
        text = raw_content.replace("\r\n", "\n").replace("\r", "\n").strip()
        if not text:
            return ParsedTranscript()

        # Try WebVTT / SRT first
        if "-->" in text:
            vtt_result = self._parse_vtt(text)
            if vtt_result.segments:
                return vtt_result

        # Try Bracketed timestamps [HH:MM:SS] Speaker: Text
        bracket_result = self._parse_bracket_timestamps(text)
        if bracket_result.segments:
            return bracket_result

        # Try Speaker (Timestamp): Text
        paren_result = self._parse_speaker_paren(text)
        if paren_result.segments:
            return paren_result

        # Try Bare timestamp 00:01:10 Speaker: Text
        bare_result = self._parse_bare_timestamps(text)
        if bare_result.segments:
            return bare_result

        # Try Multi-line header (Teams/Meet)
        multiline_result = self._parse_multiline(text)
        if multiline_result.segments:
            return multiline_result

        # Fallback: Untimed Speaker: Text format
        return self._parse_fallback_untimed(text)

    def _parse_bracket_timestamps(self, text: str) -> ParsedTranscript:
        segments: List[ParsedSegment] = []
        turn = 1
        lines = text.split("\n")
        current_speaker: Optional[str] = None
        current_start: float = 0.0
        current_text_parts: List[str] = []

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            match = self.BRACKET_TIMESTAMP_SPEAKER.match(line_str)
            if match:
                if current_speaker and current_text_parts:
                    content = " ".join(current_text_parts).strip()
                    # Estimate end time based on word count (~150 words per minute = 2.5 words/sec, min 2s)
                    duration_est = max(3.0, len(content.split()) / 2.5)
                    segments.append(ParsedSegment(
                        speaker=current_speaker,
                        start_time=current_start,
                        end_time=current_start + duration_est,
                        text=content,
                        turn_number=turn
                    ))
                    turn += 1
                current_start = parse_timestamp_to_seconds(match.group("time"))
                current_speaker = clean_speaker_name(match.group("speaker"))
                current_text_parts = [match.group("text").strip()]
            else:
                if current_speaker:
                    current_text_parts.append(line_str)

        if current_speaker and current_text_parts:
            content = " ".join(current_text_parts).strip()
            duration_est = max(3.0, len(content.split()) / 2.5)
            segments.append(ParsedSegment(
                speaker=current_speaker,
                start_time=current_start,
                end_time=current_start + duration_est,
                text=content,
                turn_number=turn
            ))

        return self._finalize_transcript(segments, "bracket_timestamp")

    def _parse_speaker_paren(self, text: str) -> ParsedTranscript:
        segments: List[ParsedSegment] = []
        turn = 1
        lines = text.split("\n")
        current_speaker: Optional[str] = None
        current_start: float = 0.0
        current_text_parts: List[str] = []

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            match = self.SPEAKER_PAREN_TIMESTAMP.match(line_str)
            if match:
                if current_speaker and current_text_parts:
                    content = " ".join(current_text_parts).strip()
                    duration_est = max(3.0, len(content.split()) / 2.5)
                    segments.append(ParsedSegment(
                        speaker=current_speaker,
                        start_time=current_start,
                        end_time=current_start + duration_est,
                        text=content,
                        turn_number=turn
                    ))
                    turn += 1
                current_start = parse_timestamp_to_seconds(match.group("time"))
                current_speaker = clean_speaker_name(match.group("speaker"))
                current_text_parts = [match.group("text").strip()]
            else:
                if current_speaker:
                    current_text_parts.append(line_str)

        if current_speaker and current_text_parts:
            content = " ".join(current_text_parts).strip()
            duration_est = max(3.0, len(content.split()) / 2.5)
            segments.append(ParsedSegment(
                speaker=current_speaker,
                start_time=current_start,
                end_time=current_start + duration_est,
                text=content,
                turn_number=turn
            ))

        return self._finalize_transcript(segments, "speaker_paren")

    def _parse_bare_timestamps(self, text: str) -> ParsedTranscript:
        segments: List[ParsedSegment] = []
        turn = 1
        for match in self.BARE_TIMESTAMP_SPEAKER.finditer(text):
            t_sec = parse_timestamp_to_seconds(match.group("time"))
            speaker = clean_speaker_name(match.group("speaker"))
            content = match.group("text").strip()
            duration_est = max(3.0, len(content.split()) / 2.5)
            segments.append(ParsedSegment(
                speaker=speaker,
                start_time=t_sec,
                end_time=t_sec + duration_est,
                text=content,
                turn_number=turn
            ))
            turn += 1
        return self._finalize_transcript(segments, "bare_timestamp")

    def _parse_vtt(self, text: str) -> ParsedTranscript:
        segments: List[ParsedSegment] = []
        turn = 1
        for match in self.VTT_CUE.finditer(text):
            start = parse_timestamp_to_seconds(match.group("start"))
            end = parse_timestamp_to_seconds(match.group("end"))
            raw_speaker = match.group("speaker") or "Unknown"
            speaker = clean_speaker_name(raw_speaker)
            content = match.group("text").replace("\n", " ").strip()
            # If content starts with "Speaker: Text"
            if ":" in content and (speaker == "Unknown" or not speaker):
                parts = content.split(":", 1)
                speaker = clean_speaker_name(parts[0])
                content = parts[1].strip()

            segments.append(ParsedSegment(
                speaker=speaker,
                start_time=start,
                end_time=end,
                text=content,
                turn_number=turn
            ))
            turn += 1
        return self._finalize_transcript(segments, "webvtt")

    def _parse_multiline(self, text: str) -> ParsedTranscript:
        segments: List[ParsedSegment] = []
        turn = 1
        for match in self.MULTILINE_HEADER.finditer(text):
            speaker = clean_speaker_name(match.group("speaker"))
            t_str = match.group("time")
            # Handle PM/AM if needed
            t_sec = parse_timestamp_to_seconds(re.sub(r"[AaPp][Mm]", "", t_str))
            content = match.group("text").replace("\n", " ").strip()
            duration_est = max(3.0, len(content.split()) / 2.5)
            segments.append(ParsedSegment(
                speaker=speaker,
                start_time=t_sec,
                end_time=t_sec + duration_est,
                text=content,
                turn_number=turn
            ))
            turn += 1
        return self._finalize_transcript(segments, "multiline_teams_meet")

    def _parse_fallback_untimed(self, text: str) -> ParsedTranscript:
        """Parse transcripts with no timestamps, estimating sequential timestamps."""
        segments: List[ParsedSegment] = []
        turn = 1
        current_time = 0.0
        line_pattern = re.compile(r"^(?P<speaker>[A-Za-z\s]+)[:\-]\s*(?P<text>.*)$")

        for line in text.split("\n"):
            line_str = line.strip()
            if not line_str:
                continue
            m = line_pattern.match(line_str)
            if m:
                speaker = clean_speaker_name(m.group("speaker"))
                content = m.group("text").strip()
                duration = max(4.0, len(content.split()) / 2.5)
                segments.append(ParsedSegment(
                    speaker=speaker,
                    start_time=current_time,
                    end_time=current_time + duration,
                    text=content,
                    turn_number=turn
                ))
                current_time += duration + 1.0
                turn += 1

        return self._finalize_transcript(segments, "fallback_untimed")

    def _finalize_transcript(self, segments: List[ParsedSegment], format_name: str) -> ParsedTranscript:
        """Post-process segments: adjust overlapping end times to next start times when reasonable."""
        if not segments:
            return ParsedTranscript(detected_format=format_name)

        # Sort chronologically
        segments.sort(key=lambda s: (s.start_time, s.turn_number))

        # Re-number turns and adjust end times so turns don't exceed next turn by excessive amount
        for i in range(len(segments)):
            segments[i].turn_number = i + 1
            if i + 1 < len(segments):
                next_start = segments[i + 1].start_time
                if next_start > segments[i].start_time:
                    # If current end time is past next start time, clamp or adjust
                    if segments[i].end_time > next_start:
                        segments[i].end_time = next_start
                elif next_start == segments[i].start_time:
                    segments[i].end_time = segments[i].start_time + 2.0
            else:
                # Last segment
                if segments[i].end_time <= segments[i].start_time:
                    segments[i].end_time = segments[i].start_time + 4.0

        # Unique participants
        participants = sorted(list({s.speaker for s in segments if s.speaker and s.speaker != "Unknown"}))
        total_duration = max(s.end_time for s in segments) if segments else 0.0

        return ParsedTranscript(
            segments=segments,
            participants=participants,
            duration=total_duration,
            detected_format=format_name
        )
