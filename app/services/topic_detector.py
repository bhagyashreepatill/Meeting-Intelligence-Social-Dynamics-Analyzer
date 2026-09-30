"""Topic segmentation, topic timeline generation, and unresolved topic detection."""

import re
from typing import List, Dict, Any, Optional
from app.services.transcript_parser import ParsedSegment


class TopicDetector:
    """Segments meetings into chronological topics and detects unresolved discussions."""

    # Phrases signaling topic transitions
    TRANSITION_PATTERNS = [
        re.compile(r"\b(?:moving on to|next up is|turning to|let's discuss|now regarding)\s+(?P<topic>[^\.,!\?]+)", re.IGNORECASE),
        re.compile(r"\b(?:quick alignment on|let's talk about|agenda item|regarding the)\s+(?P<topic>[^\.,!\?]+)", re.IGNORECASE),
        re.compile(r"\b(?:to wrap up|wrapping up|final item|review action items)\b", re.IGNORECASE),
    ]

    # Explicit signals that a topic was not resolved
    UNRESOLVED_SIGNALS = [
        re.compile(r"\b(?:remains unresolved|remains open|not resolved|unresolved for now)\b", re.IGNORECASE),
        re.compile(r"\b(?:table this|table the|put a pin in|defer this|push to next|table for next)\b", re.IGNORECASE),
        re.compile(r"\b(?:don't have enough|need more data|no definitive call|can't decide yet|need benchmark numbers)\b", re.IGNORECASE),
    ]

    def segment_topics(
        self,
        segments: List[ParsedSegment],
        decisions: Optional[List[Dict[str, Any]]] = None,
        action_items: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """Group transcript into chronological topics and evaluate their resolution status."""
        decisions = decisions or []
        action_items = action_items or []

        if not segments:
            return []

        # Find topic transition points
        topic_boundaries: List[Dict[str, Any]] = []

        for seg in segments:
            text = seg.text.strip()
            for pattern in self.TRANSITION_PATTERNS:
                match = pattern.search(text)
                if match:
                    group_dict = match.groupdict()
                    topic_name = group_dict.get("topic", "").strip() if "topic" in group_dict else ""
                    if not topic_name:
                        if "wrap up" in text.lower() or "action items" in text.lower():
                            topic_name = "Wrap-up & Action Items"
                        else:
                            topic_name = "Discussion Topic"
                    
                    clean_name = self._clean_topic_name(topic_name)
                    if len(clean_name) >= 3:
                        topic_boundaries.append({
                            "name": clean_name,
                            "turn_number": seg.turn_number,
                            "start_time": seg.start_time
                        })
                    break

        # Fallback or refinement: ensure first segment starts a topic
        if not topic_boundaries or topic_boundaries[0]["turn_number"] > 1:
            first_name = "Project Alignment & Goals"
            # Check if first segment has an alignment clue
            first_text = segments[0].text
            if "alignment on" in first_text.lower():
                m = re.search(r"alignment on\s+([^\.,!\?]+)", first_text, re.IGNORECASE)
                if m:
                    first_name = m.group(1).strip().title()

            topic_boundaries.insert(0, {
                "name": first_name,
                "turn_number": 1,
                "start_time": segments[0].start_time
            })

        # Construct contiguous topic ranges
        total_meeting_end = max(s.end_time for s in segments)
        topics: List[Dict[str, Any]] = []

        for idx, boundary in enumerate(topic_boundaries):
            t_start = boundary["start_time"]
            next_start = topic_boundaries[idx + 1]["start_time"] if idx + 1 < len(topic_boundaries) else total_meeting_end
            
            # Segments within this topic
            topic_segs = [s for s in segments if s.start_time >= t_start and s.start_time < next_start]
            if not topic_segs:
                continue

            t_end = max(s.end_time for s in topic_segs)
            participants_in_topic = sorted(list({s.speaker for s in topic_segs if s.speaker}))

            # Check for decisions within this topic window
            linked_decisions = [
                d for d in decisions
                if d["timestamp"] >= t_start and d["timestamp"] <= t_end
            ]

            # Check for action items within this topic window
            linked_actions = [
                a for a in action_items
                if a["timestamp"] >= t_start and a["timestamp"] <= t_end
            ]

            # Check for unresolved language cues in topic segments
            topic_full_text = " ".join(s.text for s in topic_segs)
            has_unresolved_signal = any(p.search(topic_full_text) for p in self.UNRESOLVED_SIGNALS)

            # Determine Status: Resolved, Partially Resolved, Unresolved
            evidence = ""
            if has_unresolved_signal and not linked_decisions:
                status = "Unresolved"
                # Find matching segment for evidence
                for s in topic_segs:
                    if any(p.search(s.text) for p in self.UNRESOLVED_SIGNALS):
                        evidence = f"{s.speaker}: '{s.text}'"
                        break
            elif linked_decisions:
                status = "Resolved"
                evidence = f"Decided: {linked_decisions[0]['text']}"
            elif linked_actions:
                status = "Partially Resolved"
                evidence = f"Action items assigned to {linked_actions[0]['owner']}"
            else:
                status = "Partially Resolved"
                evidence = "General exploratory discussion"

            mins = int((t_end - t_start) // 60)
            secs = int((t_end - t_start) % 60)

            topics.append({
                "id": idx + 1,
                "name": boundary["name"],
                "start_time": t_start,
                "end_time": t_end,
                "time_display": f"{int(t_start // 60):02d}:{int(t_start % 60):02d} – {int(t_end // 60):02d}:{int(t_end % 60):02d}",
                "duration_display": f"{mins}m {secs:02d}s" if mins > 0 else f"{secs}s",
                "participants": participants_in_topic,
                "turn_count": len(topic_segs),
                "status": status,
                "evidence": evidence,
                "decision_count": len(linked_decisions),
                "action_count": len(linked_actions),
                "segment_ids": [s.turn_number for s in topic_segs]
            })

        return topics

    def _clean_topic_name(self, raw_name: str) -> str:
        """Format and title-case clean topic names."""
        name = raw_name.strip()
        name = re.sub(r"^(?:the|our|a)\s+", "", name, flags=re.IGNORECASE).strip()
        name = re.sub(r"\b(?:and|for|in|on)\b", lambda m: m.group(0).lower(), name)
        words = name.split()
        if words:
            words[0] = words[0].capitalize()
        return " ".join(words).title()
