"""Meeting Dynamics Replay Engine for temporal simulation and dynamic social graph updates."""

from typing import List, Dict, Any, Optional
from app.services.transcript_parser import ParsedSegment
from app.services.social_graph import SocialGraphService


class MeetingReplayEngine:
    """Computes time-sliced meeting state and dynamic social interaction snapshots."""

    def __init__(self):
        self.graph_service = SocialGraphService()

    def get_keyframes(
        self,
        segments: List[ParsedSegment],
        ideas: List[Dict[str, Any]],
        interruptions: List[Dict[str, Any]],
        decisions: List[Dict[str, Any]],
        action_items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate keyframe markers across the meeting timeline for instant scrubbing and navigation.
        """
        events = []

        # Turn starts
        for s in segments:
            events.append({
                "time": s.start_time,
                "type": "turn",
                "label": f"{s.speaker} speaking",
                "speaker": s.speaker,
                "turn_number": s.turn_number
            })

        # Ideas
        for idea in ideas:
            events.append({
                "time": idea["timestamp"],
                "type": "idea",
                "label": f"Idea: {idea['text'][:35]}...",
                "speaker": idea["speaker"],
                "id": idea["id"]
            })

        # Interruptions
        for intr in interruptions:
            events.append({
                "time": intr["timestamp"],
                "type": "interruption",
                "label": f"Interruption: {intr['speaker_a']} → {intr['speaker_b']}",
                "speaker": intr["speaker_a"]
            })

        # Decisions
        for dec in decisions:
            events.append({
                "time": dec["timestamp"],
                "type": "decision",
                "label": f"Decision: {dec['text'][:35]}...",
                "speaker": "Consensus"
            })

        # Action Items
        for act in action_items:
            events.append({
                "time": act["timestamp"],
                "type": "action_item",
                "label": f"Action: {act['task'][:35]}...",
                "speaker": act["owner"]
            })

        # Sort and deduplicate nearby events
        events.sort(key=lambda e: e["time"])
        return events

    def get_state_at_time(
        self,
        t: float,
        segments: List[ParsedSegment],
        participants: Dict[str, Any],
        ideas: List[Dict[str, Any]],
        interruptions: List[Dict[str, Any]],
        decisions: List[Dict[str, Any]],
        action_items: List[Dict[str, Any]],
        topics: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Compute snapshot of the meeting dynamics at exact second t.
        """
        # 1. Identify active segment and active speaker
        active_seg = None
        for s in segments:
            if s.start_time <= t <= s.end_time:
                active_seg = s
                break
        
        # If between turns or past end, use closest prior segment
        if not active_seg:
            past_segs = [s for s in segments if s.start_time <= t]
            if past_segs:
                active_seg = past_segs[-1]

        active_speaker = active_seg.speaker if active_seg else "None"

        # 2. Cumulative speaking time up to t
        cumulative_speaking: Dict[str, float] = {p: 0.0 for p in participants.keys()}
        for s in segments:
            if s.start_time > t:
                break
            if s.speaker not in cumulative_speaking:
                cumulative_speaking[s.speaker] = 0.0

            if s.end_time <= t:
                dur = max(1.0, s.end_time - s.start_time)
                cumulative_speaking[s.speaker] += dur
            elif s.start_time <= t < s.end_time:
                dur = max(1.0, t - s.start_time)
                cumulative_speaking[s.speaker] += dur

        tot_time = sum(cumulative_speaking.values()) or 1.0
        cumulative_pct = {
            sp: round((time_sp / tot_time) * 100, 1)
            for sp, time_sp in cumulative_speaking.items()
        }

        # 3. Filter items up to t
        segs_up_to_t = [s for s in segments if s.start_time <= t]
        ideas_up_to_t = [i for i in ideas if i["timestamp"] <= t]
        interruptions_up_to_t = [i for i in interruptions if i["timestamp"] <= t]
        decisions_up_to_t = [d for d in decisions if d["timestamp"] <= t]
        actions_up_to_t = [a for a in action_items if a["timestamp"] <= t]

        # 4. Active topic at t
        active_topic = next((top for top in topics if top["start_time"] <= t <= top["end_time"]), None)
        if not active_topic and topics:
            past_topics = [top for top in topics if top["start_time"] <= t]
            active_topic = past_topics[-1] if past_topics else topics[0]

        # 5. Dynamic social graph up to t
        replay_participants = {}
        for sp, data in participants.items():
            replay_participants[sp] = {
                **data,
                "speaking_time": round(cumulative_speaking.get(sp, 0.0), 1),
                "speaking_percentage": cumulative_pct.get(sp, 0.0),
                "is_currently_speaking": (sp == active_speaker)
            }

        graph_snapshot = self.graph_service.build_graph(
            replay_participants,
            segs_up_to_t,
            interruptions_up_to_t
        )

        return {
            "current_time": round(t, 1),
            "time_display": f"{int(t // 60):02d}:{int(t % 60):02d}",
            "active_speaker": active_speaker,
            "active_segment": {
                "turn_number": active_seg.turn_number if active_seg else 0,
                "speaker": active_seg.speaker if active_seg else "",
                "text": active_seg.text if active_seg else "",
                "start_time": active_seg.start_time if active_seg else 0.0,
                "end_time": active_seg.end_time if active_seg else 0.0
            } if active_seg else None,
            "active_topic": active_topic["name"] if active_topic else "General Discussion",
            "cumulative_speaking": cumulative_speaking,
            "cumulative_percentage": cumulative_pct,
            "counts": {
                "ideas": len(ideas_up_to_t),
                "interruptions": len(interruptions_up_to_t),
                "decisions": len(decisions_up_to_t),
                "action_items": len(actions_up_to_t),
                "turns_completed": len(segs_up_to_t)
            },
            "recent_idea": ideas_up_to_t[-1] if ideas_up_to_t else None,
            "recent_decision": decisions_up_to_t[-1] if decisions_up_to_t else None,
            "recent_interruption": interruptions_up_to_t[-1] if interruptions_up_to_t else None,
            "graph": graph_snapshot
        }
