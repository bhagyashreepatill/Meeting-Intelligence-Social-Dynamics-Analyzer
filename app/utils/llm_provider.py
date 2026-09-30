"""LLM Abstraction Layer for flexible AI backend selection."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from app.utils.config import settings
from app.services.transcript_parser import ParsedSegment


class LLMProvider(ABC):
    """Abstract interface for LLM operations. Allows swapping between demo/local and cloud AI."""

    @abstractmethod
    def extract_action_items(self, text: str) -> List[Dict[str, Any]]:
        """Extract action items from transcript text."""
        pass

    @abstractmethod
    def extract_decisions(self, text: str) -> List[Dict[str, Any]]:
        """Extract decisions from transcript text."""
        pass

    @abstractmethod
    def analyze_ideas(self, segments: List[ParsedSegment]) -> List[Dict[str, Any]]:
        """Identify key ideas and proposals from transcript segments."""
        pass


class DemoLocalLLMProvider(LLMProvider):
    """Local, offline LLM provider executing heuristic and semantic algorithms without API calls."""

    def __init__(self):
        from app.services.action_extractor import ActionItemExtractor
        from app.services.decision_detector import DecisionDetector
        from app.services.idea_detector import IdeaDetector
        
        self.action_extractor = ActionItemExtractor()
        self.decision_detector = DecisionDetector()
        self.idea_detector = IdeaDetector()

    def extract_action_items(self, text: str) -> List[Dict[str, Any]]:
        from app.services.transcript_parser import ParsedSegment
        dummy_seg = ParsedSegment(speaker="Speaker", start_time=0.0, end_time=10.0, text=text, turn_number=1)
        return self.action_extractor.extract([dummy_seg])

    def extract_decisions(self, text: str) -> List[Dict[str, Any]]:
        from app.services.transcript_parser import ParsedSegment
        dummy_seg = ParsedSegment(speaker="Speaker", start_time=0.0, end_time=10.0, text=text, turn_number=1)
        return self.decision_detector.detect_decisions([dummy_seg])

    def analyze_ideas(self, segments: List[ParsedSegment]) -> List[Dict[str, Any]]:
        return self.idea_detector.extract_ideas(segments)


def get_llm_provider() -> LLMProvider:
    """Factory function returning the active LLMProvider instance."""
    # When in demo mode or without external keys, always return DemoLocalLLMProvider
    return DemoLocalLLMProvider()
