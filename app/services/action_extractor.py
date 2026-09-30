"""Smart action item extraction with owner, due date, priority, and confidence scoring."""

import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.services.transcript_parser import ParsedSegment
from app.services.owner_detector import OwnerDetector
from app.services.date_extractor import DateExtractor


class ActionItemExtractor:
    """Extracts verifiable action items from transcript segments."""

    # Action item indicator triggers
    ACTION_TRIGGERS = [
        re.compile(r"\b(?:i'll|i will|i can|i'm going to)\s+(?P<task>[^,\.!\?]+)", re.IGNORECASE),
        re.compile(r"\b(?:can you|could you|please)\s+(?:publish|create|build|write|prepare|finalize|check|test|review|set up|document|handle)\s+(?P<task>[^,\.!\?]+)", re.IGNORECASE),
        re.compile(r"\b(?P<owner>[A-Z][a-z]+)\s+will\s+(?:handle|take care of|lead|write|prepare|create|build|implement|review|test|publish|document)\s+(?P<task>[^,\.!\?]+)", re.IGNORECASE),
        re.compile(r"\b(?:action item|takeaway|todo|task is to)\s*[:\-]?\s*(?P<task>[^,\.!\?]+)", re.IGNORECASE),
        re.compile(r"\b(?:we should|we need to|let's ensure we|let's make sure to)\s+(?P<task>[^,\.!\?]+)", re.IGNORECASE),
        re.compile(r"\b(?:will have|working prototype ready by)\s+(?P<task>[^,\.!\?]+)", re.IGNORECASE),
    ]

    HIGH_PRIORITY_KEYWORDS = [
        "urgent", "critical", "blocking", "blocker", "asap", "top priority",
        "highest priority", "p0", "p1", "today", "immediately", "must have", "priority is getting"
    ]
    LOW_PRIORITY_KEYWORDS = [
        "when time permits", "nice to have", "low priority", "p3", "backlog", "eventually", "someday"
    ]

    def __init__(self, known_participants: Optional[List[str]] = None, reference_date: Optional[datetime] = None):
        self.owner_detector = OwnerDetector(known_participants)
        self.date_extractor = DateExtractor()
        self.reference_date = reference_date or datetime(2026, 9, 23, 10, 0, 0)

    def extract(self, segments: List[ParsedSegment]) -> List[Dict[str, Any]]:
        """Extract action items from transcript segments."""
        action_items: List[Dict[str, Any]] = []
        seen_tasks = set()

        for seg in segments:
            text = seg.text.strip()
            
            # Skip brief pleasantries or pure questions without action commitments
            if len(text.split()) < 4 or text.endswith("?"):
                # Exception: "Can you publish the schema..." is a question that delegates an action item!
                if not any(kw in text.lower() for kw in ["can you", "could you", "please"]):
                    continue

            # Check if segment contains an action trigger
            triggered = False
            candidate_task = ""
            base_confidence = 0.85

            for pattern in self.ACTION_TRIGGERS:
                match = pattern.search(text)
                if match:
                    triggered = True
                    group_dict = match.groupdict()
                    if "task" in group_dict and group_dict["task"]:
                        candidate_task = group_dict["task"].strip()
                    break

            if not triggered:
                # Secondary check for modal commitment
                if any(w in text.lower() for w in ["i'll ", "i will ", "will handle", "action item", "we should "]):
                    triggered = True
                    base_confidence = 0.75
                    candidate_task = text

            if triggered:
                # Detect Owner
                owner, owner_conf = self.owner_detector.detect_owner(text, seg.speaker)
                
                # Detect Due Date
                display_date, iso_date = self.date_extractor.extract_due_date(text, self.reference_date)

                # Refine clean task description
                task_description = self._clean_task_description(candidate_task or text)
                
                # Deduplication check
                task_key = task_description.lower()[:30]
                if task_key in seen_tasks or len(task_description.split()) < 2:
                    continue
                seen_tasks.add(task_key)

                # Detect Priority
                priority = self._detect_priority(text)

                # Compute overall confidence
                conf = base_confidence
                if owner != "Unknown":
                    conf += 0.08
                if iso_date != "Unknown":
                    conf += 0.05
                conf = min(0.96, round(conf, 2))

                action_items.append({
                    "task": task_description,
                    "owner": owner,
                    "due_date": iso_date if iso_date != "Unknown" else (display_date if display_date != "Unknown" else "Unknown"),
                    "due_date_display": display_date,
                    "priority": priority,
                    "source_segment_id": seg.turn_number,
                    "source_speaker": seg.speaker,
                    "timestamp": seg.start_time,
                    "confidence": conf,
                    "status": "Detected",
                    "evidence": text
                })

        return action_items

    def _clean_task_description(self, raw_task: str) -> str:
        """Sanitize and format task descriptions starting with strong action verbs."""
        task = raw_task.strip()
        
        # Remove trailing date clauses from the task title itself for clarity
        task = re.sub(r"\b(?:by|before|on)\s+(?:tomorrow|today|friday|monday|tuesday|wednesday|thursday|next\s+\w+|the end of\s+\w+).*", "", task, flags=re.IGNORECASE).strip()
        task = re.sub(r"\b(?:so|because|in order to)\s+.*", "", task, flags=re.IGNORECASE).strip()

        # Clean leading words like "publish", "create", "to", "that we", "we"
        task = re.sub(r"^(?:that|we|to|and|also)\s+", "", task, flags=re.IGNORECASE).strip()
        
        if task:
            # Capitalize first letter
            task = task[0].upper() + task[1:]
        return task

    def _detect_priority(self, text: str) -> str:
        """Determine priority level based on linguistic markers."""
        text_lower = text.lower()
        if any(kw in text_lower for kw in self.HIGH_PRIORITY_KEYWORDS):
            return "High"
        if any(kw in text_lower for kw in self.LOW_PRIORITY_KEYWORDS):
            return "Low"
        return "Medium"
