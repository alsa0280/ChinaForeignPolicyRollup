"""Tests for ranking.py."""
from ai_processing.ranking import OpportunityRanker, cosine
from ai_processing.tests.fakes import FakeLLM


def test_cosine():
    assert cosine([1, 0], [1, 0]) == 1
    assert cosine([1, 0], [0, 1]) == 0
    assert cosine([0, 0], [1, 0]) == 0


def test_best_paragraph_decides_and_chinese_matches_english(reference):
    ranker = OpportunityRanker(FakeLLM(), list(reference.opportunities.values()))
    paragraphs = ["Talks on finance continued.", "中方将继续对加拿大油菜籽粕降低关税。"]

    top = ranker.top(paragraphs, limit=3)

    assert top[0].opportunity_id == "F01"


def test_opportunities_are_embedded_once(reference):
    llm = FakeLLM()
    ranker = OpportunityRanker(llm, list(reference.opportunities.values()))
    ranker.top(["canola"], limit=1)
    ranker.top(["lng"], limit=1)
    assert llm.embed_calls == 3  # opportunities once + one call per article
