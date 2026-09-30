"""Interruption detection using temporal proximity and conversational incomplete syntax signals.

Principle: Always frame as 'Possible interruption' with confidence score and evidence.
Never assert certainty without audio overlap data.
"""

import re
from typing import List, Dict, Any, Tuple
from app.services.transcript_parser import ParsedSegment


class InterruptionDetector:
    """Detects possible interruptions between speakers based on timing and linguistic structure."""

    # Syntactic cues that the speaker's sentence was cut off or incomplete
    CUTOFF_PATTERNS = [
        re.compile(r"[-–—]{1,2}$"),          # Trailing dashes e.g. "We need to ensure that the cluster--"
        re.compile(r"\.{2,}$"),               # Trailing ellipsis e.g. "I was thinking we could..."
        re.compile(r"\b(?:and|but|so|or|because|if|although|that|with|for|to)\s*[-–—\.]*$", re.IGNORECASE),  # Dangling conjunctions/prepositions
    ]

    # Interrupter opening phrases that signal cutting in
    INTERRUPTIVE_STARTERS = [
        re.compile(r"^(?:can i jump in|can i interject|sorry to interrupt|wait|hold on|let me cut in|excuse me)\b", re.IGNORECASE),
        re.compile(r"^(?:but |no but |actually |wait a second)\b", re.IGNORECASE)
    ]

    def detect_interruptions(self, segments: List[ParsedSegment]) -> List[Dict[str, Any]]:
        """
        Analyze transitions between sequential turns to detect possible interruptions.
        Returns:
            List of detected possible interruption events with neutral framing, confidence, and evidence.
        """
        interruptions: List[Dict[str, Any]] = []
        if len(segments) < 2:
            return interruptions

        for i in range(len(segments) - 1):
            curr_seg = segments[i]
            next_seg = segments[i + 1]

            # Different speakers
            if curr_seg.speaker == next_seg.speaker or curr_seg.speaker == "Unknown" or next_seg.speaker == "Unknown":
                continue

            curr_text = curr_seg.text.strip()
            next_text = next_seg.text.strip()
            delta_time = next_seg.start_time - curr_seg.end_time

            # Check evidence signals
            is_cutoff = any(p.search(curr_text) for p in self.CUTOFF_PATTERNS)
            is_interruptive_starter = any(p.search(next_text) for p in self.INTERRUPTIVE_STARTERS)
            is_tight_transition = delta_time <= 0.8  # Turn started immediately or overlapped

            evidence_items = []
            confidence = 0.0

            if is_cutoff:
                evidence_items.append(f"{curr_seg.speaker}'s sentence appears incomplete or cut off ('{curr_text[-25:]}')")
                confidence += 0.45

            if is_interruptive_starter:
                evidence_items.append(f"{next_seg.speaker} used an interjection phrase ('{next_text[:30]}')")
                confidence += 0.35

            if is_tight_transition:
                evidence_items.append(f"Immediate turn onset ({delta_time:.1f}s transition latency)")
                confidence += 0.20

            # Only flag if there is substantial combined signal
            if confidence >= 0.50:
                interruptions.append({
                    "speaker_a": next_seg.speaker,  # Interrupter
                    "speaker_b": curr_seg.speaker,  # Interrupted
                    "timestamp": next_seg.start_time,
                    "confidence": min(0.92, round(confidence, 2)),
                    "evidence": " • ".join(evidence_items),
                    "interrupted_text": curr_text,
                    "interrupter_text": next_text,
                    "source_segment_id": next_seg.turn_number
                })

        return interruptions
