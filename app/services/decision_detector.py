"""Decision detection and consensus tracking."""

import re
from typing import List, Dict, Any, Optional
from app.services.transcript_parser import ParsedSegment


class DecisionDetector:
    """Detects explicit consensus decisions and formal agreements."""

    DECISION_PATTERNS = [
        re.compile(r"\b(?:the decision is made|we decided|decision is)\s*[:\-]?\s*(?P<decision>[^\.!\?]+)", re.IGNORECASE),
        re.compile(r"\b(?:we will adopt|we will use|we'll use|we will go with|let's go with)\s+(?P<decision>[^\.!\?]+)", re.IGNORECASE),
        re.compile(r"\b(?:it's decided that|we've agreed to|agreed\s*,\s*we will|consensus is to)\s+(?P<decision>[^\.!\?]+)", re.IGNORECASE),
    ]

    def detect_decisions(
        self,
        segments: List[ParsedSegment],
        ideas: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """Extract explicit decisions from transcript segments and link to related ideas."""
        ideas = ideas or []
        decisions: List[Dict[str, Any]] = []
        seen_decisions = set()

        for seg in segments:
            text = seg.text.strip()
            for pattern in self.DECISION_PATTERNS:
                match = pattern.search(text)
                if match:
                    raw_dec = match.group("decision").strip()
                    clean_dec = self._clean_decision_text(raw_dec)

                    if len(clean_dec.split()) < 3:
                        continue

                    key = clean_dec.lower()[:30]
                    if key in seen_decisions:
                        continue
                    seen_decisions.add(key)

                    # Find related idea if any
                    related_idea_id = None
                    related_idea_title = None
                    dec_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", clean_dec.lower()))
                    for idea in ideas:
                        idea_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", idea["text"].lower()))
                        if len(dec_words.intersection(idea_words)) >= 1:
                            related_idea_id = idea["id"]
                            related_idea_title = idea["text"]
                            break

                    # Participants involved in this segment and preceding 2 turns
                    start_turn = max(1, seg.turn_number - 2)
                    recent_speakers = {
                        s.speaker for s in segments
                        if s.turn_number >= start_turn and s.turn_number <= seg.turn_number and s.speaker
                    }

                    decisions.append({
                        "id": len(decisions) + 1,
                        "text": clean_dec,
                        "timestamp": seg.start_time,
                        "time_display": f"{int(seg.start_time // 60):02d}:{int(seg.start_time % 60):02d}",
                        "speaker": seg.speaker,
                        "participants_involved": sorted(list(recent_speakers)),
                        "related_idea_id": related_idea_id,
                        "related_idea_title": related_idea_title,
                        "confidence": 0.92,
                        "source_segment_id": seg.turn_number,
                        "evidence": text
                    })
                    break

        return decisions

    def _clean_decision_text(self, text: str) -> str:
        """Sanitize decision text starting with an affirmative phrase."""
        text = re.sub(r"^(?:that|we|to|and|also)\s+", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"\b(?:for now|before public launch|so that).*", "", text, flags=re.IGNORECASE).strip()
        if text:
            text = text[0].upper() + text[1:]
        return text
