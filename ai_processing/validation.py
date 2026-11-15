"""Checks applied to the model output before anything is stored.

ClaimValidator keeps a claim only if it has the expected fields, refers to a
known opportunity, quotes the article word for word, points to a paragraph and
relates to the opportunity it is attached to. Dropped claims carry a reason.
"""
import re
from datetime import date

from pydantic import ValidationError

from ai_processing.models import (
    Claim,
    Document,
    DropReason,
    DroppedClaim,
    Opportunity,
    ValidationResult,
)
from ai_processing.reference_data import ReferenceData

_QUOTE_CHARS = str.maketrans(
    {"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"'}
)  # curly quotes -> straight quotes
_LOCATOR = re.compile(r"^\s*paragraph\s+(\d+)\s*$", re.IGNORECASE)
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# --- small text helpers ----------------------------------------------------

def normalize_text(text) -> str:
    """Collapse whitespace and unify curly quotes so quotes can be compared."""
    return " ".join(str(text or "").translate(_QUOTE_CHARS).split())


def quote_in_text(quote, text) -> bool:
    """True if the quote is non-empty and appears word for word in the text."""
    needle = normalize_text(quote)
    return bool(needle) and needle in normalize_text(text)


def paragraph_number(locator) -> int | None:
    """Return N for a 'paragraph N' locator, otherwise None."""
    match = _LOCATOR.match(str(locator or ""))
    return int(match.group(1)) if match else None


def find_paragraph(quote, text) -> int | None:
    """Number (from 1) of the paragraph that contains the quote.

    Paragraphs are the non-empty lines of the text, as the n8n workflow joins
    paragraphs with line breaks. Returns None if no single paragraph contains it.
    """
    needle = normalize_text(quote)
    paragraphs = [line for line in str(text or "").split("\n") if line.strip()]
    for number, paragraph in enumerate(paragraphs, start=1):
        if needle and needle in normalize_text(paragraph):
            return number
    return None


def parse_event_date(value, fetched_at=None) -> str | None:
    """Return a YYYY-MM-DD date, or None if it is invalid or after fetched_at."""
    if not isinstance(value, str) or not _DATE.match(value):
        return None
    try:
        event = date.fromisoformat(value)
    except ValueError:
        return None
    try:
        fetched = date.fromisoformat(str(fetched_at)[:10]) if fetched_at else None
    except ValueError:
        fetched = None
    if fetched and event > fetched:
        return None
    return value


def clamp_score(value) -> int | None:
    """Round a score to an integer between 1 and 5; None if it is not a number."""
    if isinstance(value, bool):
        return None
    try:
        number = round(float(value))
    except (TypeError, ValueError, OverflowError):
        return None
    return min(5, max(1, number))


# --- quote / opportunity relation --------------------------------------------

class KeyTermMatcher:
    """Decides whether a quote shares meaningful words with an opportunity.

    Words are compared by their first five letters, so variants such as
    "expiry" and "expiring" match. Common words, and words found in almost all
    trade news, are ignored. This is a heuristic: it removes clearly unrelated
    claims but does not prove a claim is correct.
    """

    STEM_LENGTH = 5
    MIN_WORD_LENGTH = 3
    STOPWORDS = frozenset(
        {
            "a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "with", "by",
            "from", "at", "as", "is", "are", "was", "were", "be", "been", "has",
            "have", "had", "this", "that", "these", "those", "it", "its", "their",
            "there", "both", "sides", "will", "would", "can", "may", "also", "into",
            "up", "not", "all", "any", "more", "most", "new", "other", "such", "than",
            "then", "which", "who", "under", "over", "between", "through", "two",
            "our", "they", "them", "we", "he", "she", "his", "her",
            # words present in almost every article of this project
            "canada", "canadian", "china", "chinese", "prc", "trade",
        }
    )
    # agreement, country, government, economic, cooperation, minister, product,
    # change, investment, partnership, market
    GENERIC_STEMS = frozenset(
        {
            "agree", "count", "gover", "econo", "coope", "minis", "produ", "chang",
            "inves", "partn", "marke",
        }
    )

    _WORD = re.compile(r"[^\W\d_]+")

    def terms(self, text) -> set[str]:
        """Meaningful word stems of a text."""
        stems = set()
        for word in self._WORD.findall(str(text or "").lower()):
            if len(word) < self.MIN_WORD_LENGTH or word in self.STOPWORDS:
                continue
            stem = word[: self.STEM_LENGTH]
            if stem not in self.GENERIC_STEMS:
                stems.add(stem)
        return stems

    def opportunity_terms(self, opportunity: Opportunity) -> set[str]:
        return self.terms(" ".join([opportunity.title, *opportunity.monitor_triggers]))

    def relates(self, evidence: str, opportunity: Opportunity) -> bool:
        return bool(self.terms(evidence) & self.opportunity_terms(opportunity))


# --- claim validation --------------------------------------------------------

class ClaimValidator:
    """Validates the claims the model returns for one document."""

    def __init__(self, reference: ReferenceData, matcher: KeyTermMatcher | None = None):
        self.reference = reference
        self.matcher = matcher or KeyTermMatcher()

    def validate(self, raw_claims, document: Document) -> ValidationResult:
        """Split the model's claims into kept and dropped (with reasons)."""
        if not isinstance(raw_claims, list):
            return ValidationResult(dropped=[DroppedClaim(index=None, reason=DropReason.CLAIMS_NOT_A_LIST)])

        result = ValidationResult()
        for index, raw in enumerate(raw_claims):
            outcome = self.validate_one(raw, document)
            if isinstance(outcome, Claim):
                result.kept.append(outcome)
            else:
                result.dropped.append(DroppedClaim(index=index, reason=outcome))
        return result

    def validate_one(self, raw, document: Document) -> Claim | DropReason:
        """Return the cleaned claim, or the reason it is dropped."""
        claim = self._parse(raw)
        if isinstance(claim, DropReason):
            return claim

        opportunity = self.reference.opportunity(claim.opportunity_id)
        if opportunity is None:
            return DropReason.UNKNOWN_OPPORTUNITY
        if not quote_in_text(claim.support_quote, document.text):
            return DropReason.QUOTE_NOT_IN_TEXT

        stated = paragraph_number(claim.locator)
        if stated is None:
            return DropReason.BAD_LOCATOR
        if not self._relates(claim, opportunity):
            return DropReason.UNRELATED_TO_OPPORTUNITY

        return claim.model_copy(
            update={
                **self._checked_locator(claim, stated, document),
                "event_date": parse_event_date(claim.event_date, document.fetched_at),
            }
        )

    @staticmethod
    def _checked_locator(claim: Claim, stated: int, document: Document) -> dict:
        """Point the locator at the paragraph that really holds the quote.

        A wrong paragraph number is corrected (and noted in uncertainty) rather
        than dropping a claim whose quote is real.
        """
        actual = find_paragraph(claim.support_quote, document.text)
        if actual is None or actual == stated:
            return {"locator": f"paragraph {stated}"}
        note = f"locator corrected from paragraph {stated} to paragraph {actual}"
        return {"locator": f"paragraph {actual}", "uncertainty": [*claim.uncertainty, note]}

    @staticmethod
    def _parse(raw) -> Claim | DropReason:
        """Turn the model's raw output into a Claim, or explain why it cannot be."""
        if not isinstance(raw, dict):
            return DropReason.NOT_AN_OBJECT
        try:
            return Claim.model_validate(raw)
        except ValidationError as error:
            only_dimension = all(err["loc"] == ("dimension",) for err in error.errors())
            return DropReason.INVALID_DIMENSION if only_dimension else DropReason.MISSING_FIELD

    def _relates(self, claim: Claim, opportunity: Opportunity) -> bool:
        # Match on the source's own words (or their English rendering), never on
        # the model's paraphrase in claim_en.
        evidence = f"{claim.support_quote} {claim.support_quote_en or ''}"
        return self.matcher.relates(evidence, opportunity)
