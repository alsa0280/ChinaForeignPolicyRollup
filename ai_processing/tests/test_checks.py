"""Tests for checks.py: claim validation and credibility."""
import pytest

from ai_processing.checks import (
    ClaimValidator,
    Credibility,
    CredibilityScorer,
    KeyTermMatcher,
    parse_event_date,
    quote_in_text,
)
from ai_processing.models import Claim, DropReason

R001_QUOTE = "Both countries have also agreed to extend an existing trade deal until the end of 2028."
CURLY_APOSTROPHE = "\u2019"


def f01_claim(**changes) -> dict:
    """A valid raw claim for F01 based on the R001 article."""
    claim = {
        "opportunity_id": "F01",
        "dimension": "expiry_date",
        "value": "relief extended until end of 2028",
        "claim_en": "Canada and China agreed to extend the existing trade deal until the end of 2028.",
        "locator": "paragraph 8",
        "support_quote": R001_QUOTE,
        "claim_type": "reported_fact",
    }
    claim.update(changes)
    return claim


@pytest.fixture(scope="module")
def validator(reference):
    return ClaimValidator(reference)


# --- helpers ---------------------------------------------------------------------

def test_quote_ignores_whitespace_and_curly_quotes():
    assert quote_in_text("the People's Republic", f"the People{CURLY_APOSTROPHE}s \n Republic")
    assert not quote_in_text("signed a contract", "They agreed to extend the deal.")


def test_event_date_must_be_valid_and_not_after_fetch():
    assert parse_event_date("2026-03-01", "2026-11-12") == "2026-03-01"
    assert parse_event_date("end of 2028") is None
    assert parse_event_date("2026-12-01", "2026-11-14T15:17:00-05:00") is None


def test_key_terms_match_variants_and_skip_generic_words():
    matcher = KeyTermMatcher()
    assert matcher.terms("expiring") == matcher.terms("expiry")
    assert matcher.terms("agreement countries investment market") == set()


# --- ClaimValidator ----------------------------------------------------------------

def test_valid_claim_is_kept_and_cleaned(validator, r001_document):
    claim = validator.validate_one(f01_claim(locator="Paragraph 08"), r001_document)
    assert isinstance(claim, Claim)
    assert claim.locator == "paragraph 8"
    assert claim.uncertainty == []


def test_wrong_paragraph_number_is_corrected(validator, r001_document):
    claim = validator.validate_one(f01_claim(locator="paragraph 3"), r001_document)
    assert claim.locator == "paragraph 8"
    assert claim.uncertainty == ["locator corrected from paragraph 3 to paragraph 8"]


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"value": ""}, DropReason.MISSING_FIELD),
        ({"opportunity_id": "Z99"}, DropReason.UNKNOWN_OPPORTUNITY),
        ({"dimension": "tariff_status"}, DropReason.INVALID_DIMENSION),
        ({"support_quote": "China signed a binding canola contract."}, DropReason.QUOTE_NOT_IN_TEXT),
        ({"locator": "https://www.newsweek.com/"}, DropReason.BAD_LOCATOR),
        ({"opportunity_id": "E01", "claim_en": "LNG Canada contract signed."}, DropReason.UNRELATED_TO_OPPORTUNITY),
    ],
)
def test_invalid_claim_is_dropped_with_reason(validator, r001_document, changes, reason):
    assert validator.validate_one(f01_claim(**changes), r001_document) is reason


def test_non_english_quote_is_matched_through_its_translation(validator, document):
    raw = f01_claim(
        support_quote="中加双方同意将对加拿大油菜籽粕、豌豆、龙虾和螃蟹的关税减免措施延长至2028年底。",
        support_quote_en="Both sides agreed to extend tariff relief on canola meal, peas, lobster and crab.",
        locator="paragraph 2",
    )
    assert isinstance(validator.validate_one(raw, document("zh_synthetic")), Claim)


def test_baseline_mismatched_claims_are_all_dropped(validator, baseline_cases, document):
    """Regression: the 9 wrong claims from the n8n run of 2026-11-14."""
    for case in baseline_cases:
        outcome = validator.validate_one(case["claim"], document(case["document"]))
        assert outcome is DropReason.UNRELATED_TO_OPPORTUNITY, case["claim"]["opportunity_id"]


def test_validate_reports_kept_and_dropped(validator, r001_document):
    result = validator.validate([f01_claim(), "junk"], r001_document)
    assert [claim.opportunity_id for claim in result.kept] == ["F01"]
    assert [(d.index, d.reason) for d in result.dropped] == [(1, DropReason.NOT_AN_OBJECT)]


# --- CredibilityScorer -----------------------------------------------------------

@pytest.mark.parametrize(("source_type", "expected"), [("official", 4), ("reported", 3), ("blog", 2)])
def test_base_score_by_source_type(source_type, expected):
    assert CredibilityScorer().score(source_type).score == expected


def test_adjustment_with_reason_is_applied():
    assert CredibilityScorer().score("reported", 1, "cites named ministers") == Credibility(
        4, "reported source (base 3); +1: cites named ministers"
    )


@pytest.mark.parametrize(("adjustment", "reason"), [(2, "too big"), ("1", "wrong type"), (1, "")])
def test_invalid_adjustment_is_ignored(adjustment, reason):
    result = CredibilityScorer().score("company", adjustment, reason)
    assert result.score == 3
    assert "model adjustment ignored" in result.reason


def test_score_stays_between_1_and_5():
    assert CredibilityScorer().score("blog", -1, "anonymous").score == 1
    assert CredibilityScorer().score("official", 1, "legal notice").score == 5
