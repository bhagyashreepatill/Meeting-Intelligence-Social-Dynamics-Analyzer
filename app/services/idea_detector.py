"""Idea detection, semantic embeddings, and idea overlap detection."""

import re
from typing import List, Dict, Any, Tuple, Optional
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from app.services.transcript_parser import ParsedSegment


class IdeaDetector:
    """Detects proposed ideas and evaluates semantic similarity between statements."""

    IDEA_TRIGGER_PATTERNS = [
        re.compile(r"\b(?:we could|what if we|my proposal is|i propose|i suggest|an idea would be)\s+(?P<idea>[^\.!\?]+)", re.IGNORECASE),
        re.compile(r"\b(?:let's|we can|why don't we|how about we)\s+(?P<idea>(?:automate|adopt|build|use|implement|migrate|create|deploy|set up|design)[^\.!\?]+)", re.IGNORECASE),
        re.compile(r"\b(?:if we use|one option is to|my recommendation is)\s+(?P<idea>[^\.!\?]+)", re.IGNORECASE),
    ]

    def extract_ideas(self, segments: List[ParsedSegment]) -> List[Dict[str, Any]]:
        """Identify meaningful proposals and ideas introduced during the meeting."""
        ideas: List[Dict[str, Any]] = []
        seen_ideas = set()

        for seg in segments:
            text = seg.text.strip()
            for pattern in self.IDEA_TRIGGER_PATTERNS:
                match = pattern.search(text)
                if match:
                    raw_idea = match.group("idea").strip()
                    clean_idea = self._sanitize_idea_text(raw_idea)

                    if len(clean_idea.split()) < 3:
                        continue

                    key = clean_idea.lower()[:30]
                    if key in seen_ideas:
                        continue
                    seen_ideas.add(key)

                    ideas.append({
                        "id": len(ideas) + 1,
                        "speaker": seg.speaker,
                        "text": clean_idea,
                        "full_quote": text,
                        "timestamp": seg.start_time,
                        "confidence": 0.88,
                        "lifecycle_stage": "Introduced",
                        "source_segment_id": seg.turn_number
                    })
                    break

        return ideas

    def _sanitize_idea_text(self, text: str) -> str:
        """Clean and capitalize extracted idea statement."""
        text = re.sub(r"^(?:that|we|to|and|also)\s+", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"\b(?:so that|in order to|because).*", "", text, flags=re.IGNORECASE).strip()
        if text:
            text = text[0].upper() + text[1:]
        return text

    def compute_similarity(self, text1: str, text2: str) -> float:
        """
        Compute robust semantic similarity between two statements using normalized token matching
        and CountVectorizer cosine similarity.
        """
        def normalize_stem(t: str) -> str:
            t = t.lower()
            t = re.sub(r"deployments?\b", "deployment", t)
            t = re.sub(r"automates?|automating|automation\b", "automate", t)
            t = re.sub(r"pipelines?\b", "pipeline", t)
            t = re.sub(r"releases?\b", "release", t)
            t = re.sub(r"workflows?\b", "workflow", t)
            t = re.sub(r"services?\b", "service", t)
            return t

        n1 = normalize_stem(text1)
        n2 = normalize_stem(text2)

        try:
            vec = CountVectorizer(stop_words="english", ngram_range=(1, 2))
            mat = vec.fit_transform([n1, n2])
            cos_sim = float(cosine_similarity(mat)[0][1])
        except Exception:
            cos_sim = 0.0

        # Word-level overlap (Jaccard) for short utterances
        stopwords = {"and", "with", "to", "the", "our", "a", "in", "of", "for", "using", "by"}
        w1 = {w for w in re.findall(r"\b[a-zA-Z]{3,}\b", n1) if w not in stopwords}
        w2 = {w for w in re.findall(r"\b[a-zA-Z]{3,}\b", n2) if w not in stopwords}
        
        union = w1.union(w2)
        jaccard = (len(w1.intersection(w2)) / len(union)) if union else 0.0

        # Combined metric takes maximum of ngram cosine and token overlap
        return max(cos_sim, jaccard)

    def detect_overlaps(self, ideas: List[Dict[str, Any]], similarity_threshold: float = 0.50) -> List[Dict[str, Any]]:
        """
        Compare ideas pairwise to detect potential overlaps across different speakers and timestamps.
        Feature 9: Idea Overlap Detection.
        """
        overlaps: List[Dict[str, Any]] = []
        if len(ideas) < 2:
            return overlaps

        for i in range(len(ideas)):
            for j in range(i + 1, len(ideas)):
                idea_a = ideas[i]
                idea_b = ideas[j]

                sim = self.compute_similarity(idea_a["text"], idea_b["text"])
                if sim >= similarity_threshold:
                    # Ensure chronological order (A is earlier, B is later)
                    if idea_a["timestamp"] > idea_b["timestamp"]:
                        idea_a, idea_b = idea_b, idea_a

                    time_diff = idea_b["timestamp"] - idea_a["timestamp"]
                    mins = int(time_diff // 60)
                    secs = int(time_diff % 60)

                    overlaps.append({
                        "idea_a_id": idea_a["id"],
                        "idea_b_id": idea_b["id"],
                        "speaker_a": idea_a["speaker"],
                        "speaker_b": idea_b["speaker"],
                        "text_a": idea_a["text"],
                        "text_b": idea_b["text"],
                        "timestamp_a": idea_a["timestamp"],
                        "timestamp_b": idea_b["timestamp"],
                        "similarity": round(sim, 2),
                        "similarity_percentage": round(sim * 100, 1),
                        "time_difference": round(time_diff, 1),
                        "time_diff_display": f"{mins}m {secs:02d}s" if mins > 0 else f"{secs}s"
                    })

        return overlaps
