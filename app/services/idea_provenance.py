"""Idea Provenance, Idea Journey tracking, and neutral Attribution Shift signal detection."""

import re
from typing import List, Dict, Any, Optional
from app.services.transcript_parser import ParsedSegment


class IdeaProvenanceTracker:
    """Builds chronological idea lifecycles and detects evidence-based attribution signals."""

    def build_idea_journeys(
        self,
        ideas: List[Dict[str, Any]],
        segments: List[ParsedSegment],
        overlaps: List[Dict[str, Any]],
        decisions: List[Dict[str, Any]],
        action_items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Synthesize the end-to-end journey for each major idea from introduction to action item.
        Feature 10: Idea Provenance / Idea Journey.
        """
        journeys: List[Dict[str, Any]] = []

        # Focus on primary introduced ideas (earliest ideas or cluster roots)
        overlap_targets = {o["idea_b_id"] for o in overlaps}

        for idea in ideas:
            # Skip ideas that are merely later overlaps of an earlier idea in root list
            if idea["id"] in overlap_targets:
                continue

            idea_id = idea["id"]
            root_speaker = idea["speaker"]
            idea_text = idea["text"]
            t0 = idea["timestamp"]

            steps = [
                {
                    "stage": "Introduced",
                    "speaker": root_speaker,
                    "timestamp": t0,
                    "time_display": f"{int(t0 // 60):02d}:{int(t0 % 60):02d}",
                    "description": f"{root_speaker} introduced the idea: '{idea_text}'",
                    "badge": "introduced",
                    "quote": idea.get("full_quote", idea_text)
                }
            ]

            # 1. Look for discussion and expansions in subsequent segments
            subsequent_segs = [s for s in segments if s.start_time > t0 and s.start_time <= t0 + 900]
            idea_keywords = set(re.findall(r"\b[a-zA-Z]{4,}\b", idea_text.lower()))

            discussed_speakers = set()
            for seg in subsequent_segs:
                if seg.speaker == root_speaker:
                    continue
                seg_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", seg.text.lower()))
                common_words = idea_keywords.intersection(seg_words)
                if len(common_words) >= 2 and seg.speaker not in discussed_speakers:
                    discussed_speakers.add(seg.speaker)
                    steps.append({
                        "stage": "Discussed / Expanded",
                        "speaker": seg.speaker,
                        "timestamp": seg.start_time,
                        "time_display": f"{int(seg.start_time // 60):02d}:{int(seg.start_time % 60):02d}",
                        "description": f"{seg.speaker} contributed technical expansion / response",
                        "badge": "discussion",
                        "quote": seg.text
                    })

            # 2. Check for Reiteration / Overlap from another speaker
            matching_overlaps = [o for o in overlaps if o["idea_a_id"] == idea_id]
            for ov in matching_overlaps:
                steps.append({
                    "stage": "Reiterated / Overlap",
                    "speaker": ov["speaker_b"],
                    "timestamp": ov["timestamp_b"],
                    "time_display": f"{int(ov['timestamp_b'] // 60):02d}:{int(ov['timestamp_b'] % 60):02d}",
                    "description": f"{ov['speaker_b']} expressed a highly similar proposal ({ov['similarity_percentage']}% similarity)",
                    "badge": "overlap",
                    "quote": ov["text_b"]
                })

            # 3. Check for Decision matching this idea
            for dec in decisions:
                dec_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", dec["text"].lower()))
                if len(idea_keywords.intersection(dec_words)) >= 2:
                    steps.append({
                        "stage": "Decision",
                        "speaker": "Team Consensus",
                        "timestamp": dec["timestamp"],
                        "time_display": f"{int(dec['timestamp'] // 60):02d}:{int(dec['timestamp'] % 60):02d}",
                        "description": f"Team formalized decision: '{dec['text']}'",
                        "badge": "decision",
                        "quote": dec["text"]
                    })
                    break

            # 4. Check for Action Items assigned matching this idea
            for act in action_items:
                act_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", act["task"].lower()))
                if len(idea_keywords.intersection(act_words)) >= 1 or any(kw in act["evidence"].lower() for kw in idea_keywords):
                    steps.append({
                        "stage": "Action Item",
                        "speaker": act["owner"],
                        "timestamp": act["timestamp"],
                        "time_display": f"{int(act['timestamp'] // 60):02d}:{int(act['timestamp'] % 60):02d}",
                        "description": f"Assigned to {act['owner']} (Due: {act['due_date']}): '{act['task']}'",
                        "badge": "action",
                        "quote": act["evidence"]
                    })
                    break

            # Sort steps chronologically
            steps.sort(key=lambda s: s["timestamp"])

            journeys.append({
                "idea_id": idea_id,
                "title": idea_text,
                "originator": root_speaker,
                "total_steps": len(steps),
                "has_decision": any(s["stage"] == "Decision" for s in steps),
                "has_action": any(s["stage"] == "Action Item" for s in steps),
                "steps": steps
            })

        return journeys

    def detect_attribution_shifts(
        self,
        overlaps: List[Dict[str, Any]],
        segments: List[ParsedSegment],
        similarity_threshold: float = 0.55
    ) -> List[Dict[str, Any]]:
        """
        Detect cases where Speaker A introduces an idea, Speaker B later states a similar idea without explicit attribution.
        Feature 11: Potential Attribution Shift (Framed neutrally with strict explainability).
        """
        shifts: List[Dict[str, Any]] = []

        for ov in overlaps:
            speaker_a = ov["speaker_a"]  # Original
            speaker_b = ov["speaker_b"]  # Later
            if speaker_a == speaker_b:
                continue

            # Check if Speaker B gave explicit attribution to Speaker A
            # (e.g., "As Alice said", "Building on Alice's suggestion", "Alice proposed", "Like Alice mentioned")
            text_b = ov["text_b"]
            # Look up full turn text of Speaker B
            later_seg = next((s for s in segments if s.start_time == ov["timestamp_b"]), None)
            full_statement_b = later_seg.text if later_seg else text_b

            attribution_pattern = re.compile(
                rf"\b(?:as\s+{re.escape(speaker_a)}|like\s+{re.escape(speaker_a)}|building on\s+{re.escape(speaker_a)}|{re.escape(speaker_a)}'s\s+idea|{re.escape(speaker_a)}\s+suggested|{re.escape(speaker_a)}\s+proposed)\b",
                re.IGNORECASE
            )
            has_explicit_attribution = bool(attribution_pattern.search(full_statement_b))

            if not has_explicit_attribution and ov["similarity"] >= similarity_threshold:
                t_a = ov["timestamp_a"]
                t_b = ov["timestamp_b"]
                shifts.append({
                    "original_speaker": speaker_a,
                    "original_timestamp": t_a,
                    "original_time_display": f"{int(t_a // 60):02d}:{int(t_a % 60):02d}",
                    "original_statement": ov["text_a"],
                    "later_speaker": speaker_b,
                    "later_timestamp": t_b,
                    "later_time_display": f"{int(t_b // 60):02d}:{int(t_b % 60):02d}",
                    "later_statement": full_statement_b,
                    "semantic_similarity": ov["similarity_percentage"],
                    "time_difference": ov["time_diff_display"],
                    "explicit_attribution": "Not detected",
                    "signal_label": "Potential Attribution Shift",
                    "explanation": (
                        f"{speaker_a} introduced a concept at {int(t_a // 60):02d}:{int(t_a % 60):02d}. "
                        f"{speaker_b} later stated a highly similar proposal ({ov['similarity_percentage']}% similarity) at {int(t_b // 60):02d}:{int(t_b % 60):02d} "
                        f"without detected explicit attribution to {speaker_a} in that turn."
                    )
                })

        return shifts
