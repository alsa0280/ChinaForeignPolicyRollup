"""Turns one document into one ai_claims row.

Steps: trim the text, pick the opportunities the article may be about, call the
model, check its claims, compute credibility and build the row. Always returns a
row; on any failure the row has ai_status "failed", the error message and no
claims.
"""
import json
from datetime import datetime, timezone

from pydantic import ValidationError

from ai_processing.checks import ClaimValidator, CredibilityScorer
from ai_processing.config import ReferenceData, Settings
from ai_processing.llm_client import LLMError
from ai_processing.models import (
    AIClaimsRow,
    Claim,
    Dimension,
    Document,
    FocusArea,
    Language,
    LLMAssessment,
    Opportunity,
)
from ai_processing.ranking import OpportunityRanker

# How many opportunities are sent to the model. Fewer candidates means fewer
# mixed-up IDs and a shorter, faster prompt.
MAX_CANDIDATES = 5


class Processor:
    def __init__(self, settings: Settings, reference: ReferenceData, llm):
        """`llm` provides generate_json() and embed(), like OllamaClient."""
        self.settings = settings
        self.reference = reference
        self.llm = llm
        self.ranker = OpportunityRanker(llm, list(reference.opportunities.values()))
        self.validator = ClaimValidator(reference)
        self.scorer = CredibilityScorer()
        self.system_prompt = settings.prompt_file.read_text(encoding="utf-8")

    def process(self, document: Document) -> AIClaimsRow:
        paragraphs, truncated = self._trimmed(document.paragraphs)
        if not paragraphs:
            return self._failed(document, "document has no text")

        try:
            raw = self.llm.generate_json(
                self.system_prompt,
                self._payload(document, paragraphs, self._candidates(paragraphs)),
                LLMAssessment.json_schema(),
            )
            assessment, raw_claims = LLMAssessment.from_model_output(raw)
        except (LLMError, ValidationError) as error:
            return self._failed(document, str(error))

        result = self.validator.validate(raw_claims, document)
        claims = [self._tidy(claim, document, assessment.language) for claim in result.kept]
        credibility = self.scorer.score(
            self.reference.source_type(document.source_id),
            assessment.credibility_adjustment,
            assessment.credibility_reason,
        )
        red_flags = [*assessment.red_flags, *(["text truncated"] if truncated else [])]

        return AIClaimsRow(
            **self._identity(document),
            credibility_score=credibility.score,
            relevance_score=assessment.relevance_score,
            relevance_justification_en=assessment.relevance_justification_en,
            summary_en=assessment.summary_en,
            claims_json=json.dumps([c.model_dump(mode="json") for c in claims], ensure_ascii=False),
            claims_dropped=len(result.dropped),
            language=assessment.language,
            title_en=assessment.title_en,
            focus_area=self._focus_area(claims, assessment.focus_area),
            credibility_reason=credibility.reason,
            uncertain=assessment.uncertain or truncated,
            red_flags=json.dumps(red_flags, ensure_ascii=False),
            ai_status="ok",
            ai_error="",
        )

    # --- preparing the request ----------------------------------------------

    def _trimmed(self, paragraphs: list[str]) -> tuple[list[str], bool]:
        """Paragraphs up to MAX_TEXT_CHARS (whole paragraphs only), and whether text was cut."""
        kept, size = [], 0
        for paragraph in paragraphs:
            if kept and size + len(paragraph) > self.settings.max_text_chars:
                break
            kept.append(paragraph)
            size += len(paragraph)
        return kept, len(kept) < len(paragraphs)

    def _candidates(self, paragraphs: list[str]) -> list[Opportunity]:
        """The opportunities closest in meaning to the article.

        If the embedding model is unavailable, all opportunities are sent, so the
        article is still analysed (more slowly and with more risk of mixed-up IDs).
        """
        try:
            return self.ranker.top(paragraphs, MAX_CANDIDATES)
        except LLMError:
            return list(self.reference.opportunities.values())

    @staticmethod
    def _payload(document: Document, paragraphs: list[str], candidates: list[Opportunity]) -> dict:
        return {
            "article": {
                "title": document.title,
                "published_at": document.published_at,
                "paragraphs": paragraphs,
            },
            "opportunities": [
                {"opportunity_id": o.opportunity_id, "title": o.title, "monitor_triggers": o.monitor_triggers}
                for o in candidates
            ],
            "dimensions": [d.value for d in Dimension],
            "focus_areas": [f.value for f in FocusArea],
        }

    # --- tidying the answer ---------------------------------------------------

    @staticmethod
    def _tidy(claim: Claim, document: Document, language: Language) -> Claim:
        """Fix two things the model often gets wrong."""
        updates = {}
        # A publication date is not an event date.
        if claim.event_date and claim.event_date == str(document.published_at or "")[:10]:
            updates["event_date"] = None
        # An English quote needs no English translation.
        if language is Language.ENGLISH:
            updates["support_quote_en"] = None
        return claim.model_copy(update=updates)

    def _focus_area(self, claims: list[Claim], model_choice: FocusArea) -> FocusArea:
        """Use the working area of the first claim's opportunity; else the model's choice."""
        for claim in claims:
            opportunity = self.reference.opportunity(claim.opportunity_id)
            area = FocusArea.parse(opportunity.stack if opportunity else None)
            if area is not FocusArea.NONE:
                return area
        return model_choice

    # --- building rows --------------------------------------------------------

    def _identity(self, document: Document) -> dict:
        return {
            "source_id": document.source_id,
            "url": document.url,
            "hash": document.hash,
            "analyzed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "model": self.settings.ollama_model,
            "prompt_version": self.settings.prompt_version,
        }

    def _failed(self, document: Document, error: str) -> AIClaimsRow:
        return AIClaimsRow(
            **self._identity(document),
            credibility_score=None,
            relevance_score=None,
            relevance_justification_en="",
            summary_en="",
            claims_json="[]",
            claims_dropped=0,
            language=Language.OTHER,
            title_en="",
            focus_area=FocusArea.NONE,
            credibility_reason="",
            uncertain=True,
            red_flags="[]",
            ai_status="failed",
            ai_error=error,
        )
