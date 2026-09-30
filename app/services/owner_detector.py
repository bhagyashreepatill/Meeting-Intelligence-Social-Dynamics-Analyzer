"""Linguistic pattern-based owner detection for action items.

Strict Principle: If uncertain, return 'Unknown'. Never guess.
"""

import re
from typing import Optional, List, Tuple
from app.services.transcript_parser import clean_speaker_name


class OwnerDetector:
    """Detects task ownership using precise linguistic patterns and context."""

    def __init__(self, known_participants: Optional[List[str]] = None):
        self.known_participants = [clean_speaker_name(p) for p in (known_participants or [])]

    # Pattern 1: Self-assignment ("I'll...", "I will...", "I can...", "Let me...")
    SELF_ASSIGN_PATTERNS = [
        re.compile(r"\b(?:i'll|i will|i can|i'm going to|let me|leave it to me)\b", re.IGNORECASE),
        re.compile(r"\b(?:i am going to|i'll handle|i'll prepare|i will take care of)\b", re.IGNORECASE)
    ]

    # Pattern 2: Direct address / request: "Name, can you...", "Name, please...", "Can you, Name, ..."
    DIRECT_ADDRESS_PATTERNS = [
        re.compile(r"^(?P<name>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)[,\s]+(?:can you|could you|please|would you)\b", re.IGNORECASE),
        re.compile(r"\b(?:can you|could you|would you)\s*,\s*(?P<name>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*,", re.IGNORECASE),
        re.compile(r"\b(?:can you|could you|would you)\s+(?P<name>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:please\s+)?(?:do|take|handle|create|build|write|prepare|finalize|check|test|review|publish)\b", re.IGNORECASE),
        re.compile(r"^(?P<name>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*[:\-]\s*(?:can you|please|will you)\b", re.IGNORECASE)
    ]

    # Pattern 3: 3rd party assignment: "Name will handle...", "Let's have Name...", "Name is going to..."
    THIRD_PARTY_PATTERNS = [
        re.compile(r"\b(?P<name>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:will|is going to|has agreed to|should)\s+(?:handle|take care of|lead|drive|prepare|create|build|write|implement|review|test|publish|document)\b", re.IGNORECASE),
        re.compile(r"\b(?:let's have|assign to|assigned to)\s+(?P<name>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b", re.IGNORECASE)
    ]

    def detect_owner(self, text: str, current_speaker: str) -> Tuple[str, float]:
        """
        Detect owner from statement.
        Returns:
            Tuple of (owner_name, confidence_score)
            owner_name defaults strictly to 'Unknown' if uncertain.
        """
        text_clean = text.strip()
        speaker_clean = clean_speaker_name(current_speaker)

        # Check Direct Address first: e.g. "David, can you publish the frontend schema...?"
        for pattern in self.DIRECT_ADDRESS_PATTERNS:
            match = pattern.search(text_clean)
            if match:
                raw_name = clean_speaker_name(match.group("name"))
                if self._is_valid_name(raw_name):
                    return raw_name, 0.92

        # Check Third-party assignment: e.g. "Sarah will handle writing the test runner..."
        for pattern in self.THIRD_PARTY_PATTERNS:
            match = pattern.search(text_clean)
            if match:
                raw_name = clean_speaker_name(match.group("name"))
                if self._is_valid_name(raw_name):
                    return raw_name, 0.90

        # Check Self-assignment: e.g. "I'll create the Jira tickets..."
        for pattern in self.SELF_ASSIGN_PATTERNS:
            if pattern.search(text_clean):
                if speaker_clean and speaker_clean != "Unknown":
                    return speaker_clean, 0.95

        # Fallback: strict refusal to guess
        return "Unknown", 0.0

    def _is_valid_name(self, name: str) -> bool:
        """Verify candidate is a realistic person name or in known participants list."""
        if not name or len(name) < 2:
            return False
        # Disallow generic words that might be capitalized
        invalid_words = {
            "we", "you", "they", "our", "team", "everyone", "today", "tomorrow", "friday",
            "monday", "tuesday", "wednesday", "thursday", "saturday", "sunday", "good",
            "great", "now", "so", "yes", "no", "well", "okay", "jira", "github", "aws", "gcp"
        }
        if name.lower() in invalid_words:
            return False

        # If known participants are provided, prefer matching them
        if self.known_participants:
            for p in self.known_participants:
                if name.lower() == p.lower() or name.lower() in p.lower():
                    return True

        # Otherwise verify it looks like a proper capitalized Name
        return bool(re.match(r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?$", name))
