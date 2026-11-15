"""Tests for models.py."""
import pytest
from pydantic import ValidationError

from ai_processing.models import Claim, ClaimType, FocusArea, Language

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
