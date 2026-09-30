"""Semantic matching utility for topics, agenda drift, and cross-meeting recurrence."""

import re
from typing import List, Tuple
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class SemanticMatcher:
    """Robust semantic similarity matcher with token normalization and fallback."""

    # Common domain synonyms and stems
    SYNONYM_MAP = {
        "api": "api endpoint service",
        "latency": "latency response time performance slowness",
        "performance": "performance speed latency optimization response time",
        "slow": "slow sluggish bottleneck latency performance",
        "database": "database db sql postgres sqlite storage",
        "deploy": "deploy deployment cicd actions canary release",
        "automation": "automation automate script pipeline",
        "cloud": "cloud aws gcp azure infrastructure compute",
        "migration": "migration migrate transition move transfer",
        "testing": "testing test qa regression playwright fixtures",
        "error": "error handling exception bug failure fault",
        "party": "party catering holiday social lunch dinner event",
        "catering": "catering food lunch party event social venue",
    }

    STOPWORDS = {
        "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
        "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
        "below", "between", "both", "but", "by", "can", "cannot", "could", "did", "do",
        "does", "doing", "down", "during", "each", "few", "for", "from", "further", "had",
        "has", "have", "having", "he", "her", "here", "hers", "herself", "him", "himself",
        "his", "how", "i", "if", "in", "into", "is", "isn't", "it", "its", "itself", "let's",
        "me", "more", "most", "my", "myself", "no", "nor", "not", "of", "off", "on", "once",
        "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own",
        "same", "she", "should", "so", "some", "such", "than", "that", "the", "their",
        "theirs", "them", "themselves", "then", "there", "these", "they", "this", "those",
        "through", "to", "too", "under", "until", "up", "very", "was", "we", "were",
        "what", "when", "where", "which", "while", "who", "whom", "why", "with", "would",
        "you", "your", "yours", "yourself", "yourselves"
    }

    def normalize(self, text: str) -> str:
        """Clean, lower, and expand text for semantic comparison."""
        text = text.lower()
        text = re.sub(r"[^\w\s]", " ", text)
        words = text.split()
        expanded = []
        for w in words:
            if w in self.STOPWORDS:
                continue
            expanded.append(w)
            # Expand known tech stems/synonyms
            if w in self.SYNONYM_MAP:
                expanded.append(self.SYNONYM_MAP[w])
        return " ".join(expanded)

    def similarity(self, text1: str, text2: str) -> float:
        """Compute cosine similarity with token-overlap fallback."""
        if not text1.strip() or not text2.strip():
            return 0.0

        n1 = self.normalize(text1)
        n2 = self.normalize(text2)

        if not n1.strip() or not n2.strip():
            # Direct token match without expansion
            t1_tokens = set(text1.lower().split())
            t2_tokens = set(text2.lower().split())
            if not t1_tokens or not t2_tokens:
                return 0.0
            return len(t1_tokens & t2_tokens) / max(len(t1_tokens), len(t2_tokens))

        try:
            vectorizer = CountVectorizer(ngram_range=(1, 2)).fit([n1, n2])
            vectors = vectorizer.transform([n1, n2])
            sim = float(cosine_similarity(vectors[0:1], vectors[1:2])[0][0])
            return round(min(1.0, max(0.0, sim)), 3)
        except Exception:
            # Fallback word-level Jaccard
            s1 = set(n1.split())
            s2 = set(n2.split())
            inter = len(s1.intersection(s2))
            union = len(s1.union(s2))
            return round(inter / max(1, union), 3)

    def match_topic(self, candidate: str, target: str, threshold: float = 0.35) -> Tuple[bool, float]:
        """Check if candidate text matches target topic above a threshold."""
        sim = self.similarity(candidate, target)
        return sim >= threshold, sim


semantic_matcher = SemanticMatcher()
