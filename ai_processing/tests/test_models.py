"""Tests for models.py."""
import pytest
from pydantic import ValidationError

from ai_processing.models import SCHEMA_FILE, Claim, ClaimType, FocusArea, Language, LLMAssessment

VALID_CLAIM = {
    "opportunity_id": "F01",
    "dimension": "expiry_date",
    "value": "extended",
    "claim_en": "Relief was extended.",
    "locator": "paragraph 1",
    "support_quote": "extend",
}


def test_focus_area_ignores_case_and_falls_back_to_none():
    assert FocusArea.parse("food Security ") is FocusArea.FOOD
    assert FocusArea.parse("Agriculture") is FocusArea.NONE


def test_language_accepts_codes_and_common_names():
    assert Language.parse("zh") is Language.MANDARIN
    assert Language.parse("Mandarin") is Language.MANDARIN
    assert Language.parse(" English ") is Language.ENGLISH
    assert Language.parse("German") is Language.OTHER


@pytest.mark.parametrize("changes", [{"value": "  "}, {"dimension": "tariff_status"}])
def test_claim_rejects_blank_text_or_unknown_dimension(changes):
    with pytest.raises(ValidationError):
        Claim.model_validate({**VALID_CLAIM, **changes})


def test_claim_cleans_loose_model_output():
    claim = Claim.model_validate(
        {**VALID_CLAIM, "claim_type": "fact", "uncertainty": "not a list", "support_quote_en": ""}
    )
    assert claim.claim_type is ClaimType.ANALYSIS
    assert claim.uncertainty == []
    assert claim.support_quote_en is None


def test_llm_assessment_cleans_answer_and_keeps_claims_apart():
    raw = {
        "language": "Mandarin",
        "focus_area": "food security",
        "relevance_score": 9,
        "credibility_adjustment": "1",
        "red_flags": "none",
        "claims": [{"opportunity_id": "F01"}, "junk"],
    }
    assessment, raw_claims = LLMAssessment.from_model_output(raw)
    assert assessment.language is Language.MANDARIN
    assert assessment.focus_area is FocusArea.FOOD
    assert assessment.relevance_score == 5
    assert assessment.credibility_adjustment == 0
    assert assessment.red_flags == []
    assert raw_claims == [{"opportunity_id": "F01"}, "junk"]


def test_schema_file_matches_models():
    """schemas/ai_processing/llm_output.schema.json must be regenerated after model changes:
    python -m ai_processing.models"""
    assert SCHEMA_FILE.read_text(encoding="utf-8") == LLMAssessment.json_schema_text()
