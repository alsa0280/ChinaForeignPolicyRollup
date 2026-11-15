"""Tests for credibility.py."""
import pytest

from ai_processing.credibility import Credibility, CredibilityScorer


@pytest.fixture(scope="module")
def scorer():
    return CredibilityScorer()


@pytest.mark.parametrize(("source_type", "expected"), [("official", 4), ("reported", 3), ("blog", 2)])
def test_base_score_by_source_type(scorer, source_type, expected):
    assert scorer.score(source_type).score == expected


def test_adjustment_with_reason_is_applied(scorer):
    assert scorer.score("reported", 1, "cites named ministers") == Credibility(
        4, "reported source (base 3); +1: cites named ministers"
    )


@pytest.mark.parametrize(("adjustment", "reason"), [(2, "too big"), ("1", "wrong type"), (1, "")])
def test_invalid_adjustment_is_ignored(scorer, adjustment, reason):
    result = scorer.score("company", adjustment, reason)
    assert result.score == 3
    assert "model adjustment ignored" in result.reason


def test_score_stays_between_1_and_5(scorer):
    assert scorer.score("blog", -1, "anonymous").score == 1
    assert scorer.score("official", 1, "legal notice").score == 5
