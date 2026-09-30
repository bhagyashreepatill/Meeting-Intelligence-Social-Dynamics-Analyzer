"""Participation analytics, turn-length dynamics, temporal change detection, and meeting health timeline."""

import numpy as np
from typing import List, Dict, Any, Optional
from app.services.transcript_parser import ParsedSegment


AVATAR_PALETTE = [
    "#4f46e5", "#06b6d4", "#10b981", "#f59e0b",
    "#ec4899", "#8b5cf6", "#14b8a6", "#f97316"
]


class SpeakerAnalyzer:
    """Calculates granular participation metrics, turn distributions, temporal shifts, and health signals."""

    def analyze(self, segments: List[ParsedSegment], total_duration: Optional[float] = None) -> Dict[str, Any]:
        """Perform comprehensive speaker and participation analysis."""
        if not segments:
            return {"participants": {}, "meeting_metrics": {}, "temporal_shifts": {}, "health_timeline": []}

        if not total_duration or total_duration <= 0.0:
            total_duration = max(s.end_time for s in segments)

        # Group turns and turn durations by speaker
        speaker_turns: Dict[str, List[float]] = {}
        speaker_turn_indices: Dict[str, List[int]] = {}

        for s in segments:
            speaker = s.speaker or "Unknown"
            duration = max(1.0, s.end_time - s.start_time)
            speaker_turns.setdefault(speaker, []).append(duration)
            speaker_turn_indices.setdefault(speaker, []).append(s.turn_number)

        total_speaking_time = sum(sum(durations) for durations in speaker_turns.values())
        if total_speaking_time <= 0:
            total_speaking_time = total_duration

        # Compute participant statistics
        participants_data: Dict[str, Dict[str, Any]] = {}
        sorted_speakers = sorted(speaker_turns.keys())

        for idx, speaker in enumerate(sorted_speakers):
            durations = speaker_turns[speaker]
            sp_time = float(sum(durations))
            pct = round((sp_time / total_speaking_time) * 100, 1)
            turn_count = len(durations)
            avg_len = round(float(np.mean(durations)), 1)
            med_len = round(float(np.median(durations)), 1)
            std_len = round(float(np.std(durations)), 1) if turn_count > 1 else 0.0
            longest = round(float(np.max(durations)), 1)
            shortest = round(float(np.min(durations)), 1)

            participants_data[speaker] = {
                "name": speaker,
                "avatar_color": AVATAR_PALETTE[idx % len(AVATAR_PALETTE)],
                "speaking_time": round(sp_time, 1),
                "speaking_percentage": pct,
                "turn_count": turn_count,
                "avg_turn_length": avg_len,
                "median_turn_length": med_len,
                "turn_std_dev": std_len,
                "longest_turn": longest,
                "shortest_turn": shortest,
                "interruptions_made": 0,
                "interruptions_received": 0,
                "responses_count": 0,
                "ideas_introduced": 0,
                "actions_assigned": 0
            }

        # Calculate Temporal Quartiles (0-25%, 25-50%, 50-75%, 75-100%)
        quartile_data = self._calculate_quartiles(segments, total_duration)

        # Calculate Participation Changes (Beginning 0-33%, Middle 33-66%, End 66-100%)
        temporal_shifts = self._calculate_temporal_shifts(segments, total_duration)

        # Calculate Meeting Health Observations over 10-minute intervals
        health_timeline = self._calculate_health_timeline(segments, total_duration)

        return {
            "participants": participants_data,
            "meeting_metrics": {
                "total_duration": round(total_duration, 1),
                "total_speaking_time": round(total_speaking_time, 1),
                "total_turns": len(segments),
                "unique_speakers": len(speaker_turns)
            },
            "quartiles": quartile_data,
            "temporal_shifts": temporal_shifts,
            "health_timeline": health_timeline
        }

    def _calculate_quartiles(self, segments: List[ParsedSegment], total_duration: float) -> Dict[str, Dict[str, float]]:
        """Calculate speaking time share by participant across 4 temporal quartiles."""
        bounds = [
            ("0-25%", 0.0, total_duration * 0.25),
            ("25-50%", total_duration * 0.25, total_duration * 0.50),
            ("50-75%", total_duration * 0.50, total_duration * 0.75),
            ("75-100%", total_duration * 0.75, total_duration)
        ]
        result: Dict[str, Dict[str, float]] = {}

        for label, start_t, end_t in bounds:
            seg_slice = [s for s in segments if s.start_time >= start_t and s.start_time < end_t]
            slice_totals: Dict[str, float] = {}
            for s in seg_slice:
                dur = max(1.0, s.end_time - s.start_time)
                slice_totals[s.speaker] = slice_totals.get(s.speaker, 0.0) + dur
            
            total_slice_time = sum(slice_totals.values()) or 1.0
            result[label] = {
                sp: round((time_sp / total_slice_time) * 100, 1)
                for sp, time_sp in slice_totals.items()
            }

        return result

    def _calculate_temporal_shifts(self, segments: List[ParsedSegment], total_duration: float) -> Dict[str, Dict[str, float]]:
        """
        Compare participation across Beginning (0-33%), Middle (33-66%), and End (66-100%).
        Feature 18: Participation Change Detection.
        """
        trimesters = [
            ("beginning", 0.0, total_duration * 0.333),
            ("middle", total_duration * 0.333, total_duration * 0.666),
            ("end", total_duration * 0.666, total_duration + 1.0)
        ]

        shares_by_section: Dict[str, Dict[str, float]] = {"beginning": {}, "middle": {}, "end": {}}

        for name, t_start, t_end in trimesters:
            sub_segs = [s for s in segments if s.start_time >= t_start and s.start_time < t_end]
            sub_totals: Dict[str, float] = {}
            for s in sub_segs:
                dur = max(1.0, s.end_time - s.start_time)
                sub_totals[s.speaker] = sub_totals.get(s.speaker, 0.0) + dur
            
            tot = sum(sub_totals.values()) or 1.0
            for sp, t in sub_totals.items():
                shares_by_section[name][sp] = round((t / tot) * 100, 1)

        # Structure by participant
        all_speakers = {s.speaker for s in segments if s.speaker}
        speaker_shifts: Dict[str, Dict[str, float]] = {}

        for sp in all_speakers:
            beg = shares_by_section["beginning"].get(sp, 0.0)
            mid = shares_by_section["middle"].get(sp, 0.0)
            end = shares_by_section["end"].get(sp, 0.0)
            speaker_shifts[sp] = {
                "beginning_pct": beg,
                "middle_pct": mid,
                "end_pct": end,
                "net_change": round(end - beg, 1)
            }

        return speaker_shifts

    def _calculate_health_timeline(self, segments: List[ParsedSegment], total_duration: float) -> List[Dict[str, Any]]:
        """
        Generate empirical observations over 10-minute intervals.
        Feature 13: Meeting Health Timeline (Neutral, measurable observations).
        """
        interval_secs = 600.0  # 10 minutes
        intervals_count = max(1, int(np.ceil(total_duration / interval_secs)))
        health_timeline = []

        for i in range(intervals_count):
            start_t = i * interval_secs
            end_t = min(total_duration, (i + 1) * interval_secs)
            slice_segs = [s for s in segments if s.start_time >= start_t and s.start_time < end_t]

            time_label = f"{int(start_t // 60):02d}–{int(end_t // 60):02d} min"

            if not slice_segs:
                continue

            # Calculate speaking distribution
            slice_durations: Dict[str, float] = {}
            for s in slice_segs:
                dur = max(1.0, s.end_time - s.start_time)
                slice_durations[s.speaker] = slice_durations.get(s.speaker, 0.0) + dur

            speakers_in_slice = len(slice_durations)
            total_slice_time = sum(slice_durations.values())
            
            # Speaking time balance metric
            max_share = max(slice_durations.values()) / total_slice_time if total_slice_time > 0 else 0.0

            observations = []
            if speakers_in_slice >= 3 and max_share < 0.45:
                observations.append("Participation: Balanced cross-functional discussion")
            elif max_share >= 0.60:
                observations.append("Speaking-time concentration increased around lead topic")
            else:
                observations.append("Active discussion with steady turn-taking")

            # Check turn lengths in slice
            turn_lens = [max(1.0, s.end_time - s.start_time) for s in slice_segs]
            avg_turn = float(np.mean(turn_lens))
            if avg_turn > 45.0:
                observations.append("Extended speaking turns during deep-dive explanation")
            elif avg_turn < 12.0:
                observations.append("High conversational cadence with rapid turns")

            health_timeline.append({
                "interval": time_label,
                "start_time": start_t,
                "end_time": end_t,
                "active_speakers": list(slice_durations.keys()),
                "turn_count": len(slice_segs),
                "observation": " • ".join(observations),
                "speaking_balance": "Balanced" if max_share < 0.50 else "Concentrated"
            })

        return health_timeline
