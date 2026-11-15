"""Two-part credibility score.

Part 1 (rule): base score from the source type in source_registry.json.
Part 2 (model): an adjustment of -1, 0 or +1, used only when it comes with a
reason. The final score stays between 1 and 5 and is explained in words.
"""
from dataclasses import dataclass

BASE_SCORES = {"official": 4, "company": 3, "reported": 3}
UNKNOWN_BASE = 2
ALLOWED_ADJUSTMENTS = (-1, 0, 1)


@dataclass(frozen=True)
class Credibility:
    score: int
    reason: str


class CredibilityScorer:
    def score(self, source_type, adjustment=0, reason: str = "") -> Credibility:
        """Combine the base score of the source type with the model's adjustment."""
        base = self.base_score(source_type)
        explanation = f"{self._label(source_type)} source (base {base})"

        if not self._is_usable(adjustment, reason):
            if adjustment not in (0, None):
                explanation += "; model adjustment ignored"
            return Credibility(base, explanation)

        if adjustment == 0:
            return Credibility(base, explanation)

        final = min(5, max(1, base + adjustment))
        return Credibility(final, f"{explanation}; {adjustment:+d}: {reason.strip()}")

    def base_score(self, source_type) -> int:
        return BASE_SCORES.get(self._key(source_type), UNKNOWN_BASE)

    def _label(self, source_type) -> str:
        key = self._key(source_type)
        return key if key in BASE_SCORES else "unknown"

    def _is_usable(self, adjustment, reason) -> bool:
        """An adjustment counts only if it is -1, 0 or +1 and a non-zero one has a reason."""
        if type(adjustment) is not int or adjustment not in ALLOWED_ADJUSTMENTS:
            return False
        return adjustment == 0 or bool(str(reason or "").strip())

    @staticmethod
    def _key(source_type) -> str:
        return str(source_type or "").strip().lower()
