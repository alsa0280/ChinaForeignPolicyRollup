"""Picks the opportunities an article is most likely about, before the model is called.

Uses a multilingual embedding model (bge-m3), so a Mandarin or French paragraph
can match an opportunity described in English. Each opportunity is scored by
its best-matching paragraph, so one strong paragraph is enough even when the
rest of the article is about something else.
"""
import math

from ai_processing.models import Opportunity


def cosine(a: list[float], b: list[float]) -> float:
    """Similarity of two vectors, from -1 to 1 (1 = same direction)."""
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


class OpportunityRanker:
    def __init__(self, embedder, opportunities: list[Opportunity]):
        self.embedder = embedder
        self.opportunities = opportunities
        self._opportunity_vectors: list[list[float]] | None = None

    def top(self, paragraphs: list[str], limit: int) -> list[Opportunity]:
        """The `limit` opportunities closest to any paragraph of the article."""
        paragraph_vectors = self.embedder.embed(paragraphs)
        scored = [
            (max(cosine(p, o) for p in paragraph_vectors), opportunity)
            for o, opportunity in zip(self._vectors(), self.opportunities)
        ]
        scored.sort(key=lambda item: item[0], reverse=True)
        return [opportunity for _, opportunity in scored[:limit]]

    def _vectors(self) -> list[list[float]]:
        # The opportunity list does not change while the service runs,
        # so it is embedded once and reused for every article.
        if self._opportunity_vectors is None:
            texts = [f"{o.title}. {'; '.join(o.monitor_triggers)}" for o in self.opportunities]
            self._opportunity_vectors = self.embedder.embed(texts)
        return self._opportunity_vectors
