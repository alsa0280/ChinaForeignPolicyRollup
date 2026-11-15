"""Tests for processor.py, with a fake model instead of Ollama."""
import json
from dataclasses import replace

import pytest

from ai_processing.config import Settings
from ai_processing.llm_client import LLMError
from ai_processing.models import FocusArea
from ai_processing.processor import MAX_CANDIDATES, Processor
from ai_processing.tests.conftest import FIXTURES_DIR
from ai_processing.tests.fakes import FakeLLM


@pytest.fixture
def r001_answer():
    path = FIXTURES_DIR / "llm_responses" / "r001_answer.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_r001_row_is_built_and_model_mistakes_are_fixed(reference, r001_document, r001_answer):
    row = Processor(Settings(), reference, FakeLLM(r001_answer)).process(r001_document)

    claims = json.loads(row.claims_json)
    assert row.ai_status == "ok"
    assert [c["opportunity_id"] for c in claims] == ["F01"]
    assert claims[0]["locator"] == "paragraph 8"  # model said paragraph 2
    assert claims[0]["event_date"] is None  # model used the publication date
    assert claims[0]["support_quote_en"] is None  # English quote needs no translation
    assert row.focus_area is FocusArea.FOOD  # model said Energy supply
    assert row.credibility_score == 4  # reported (3) + 1 with a reason
    assert row.prompt_version == "assess_v1"


@pytest.mark.parametrize("doc_name", ["r001", "zh_synthetic"])
def test_closest_opportunities_are_sent(reference, r001_document, document, r001_answer, doc_name):
    llm = FakeLLM(r001_answer)
    doc = r001_document if doc_name == "r001" else document(doc_name)
    Processor(Settings(), reference, llm).process(doc)

    sent = [o["opportunity_id"] for o in llm.payload["opportunities"]]
    assert sent[0] == "F01"
    assert len(sent) == MAX_CANDIDATES


def test_all_opportunities_are_sent_when_embeddings_fail(reference, r001_document, r001_answer):
    llm = FakeLLM(r001_answer, embed_error=LLMError("bge-m3 not installed"))
    Processor(Settings(), reference, llm).process(r001_document)
    assert len(llm.payload["opportunities"]) == len(reference.opportunities)


def test_long_text_is_trimmed_and_flagged(reference, r001_document, r001_answer):
    settings = replace(Settings(), max_text_chars=1000)
    llm = FakeLLM(r001_answer)
    row = Processor(settings, reference, llm).process(r001_document)

    assert sum(len(p) for p in llm.payload["article"]["paragraphs"]) <= 1000
    assert "text truncated" in json.loads(row.red_flags)
    assert row.uncertain is True


@pytest.mark.parametrize(
    ("llm", "doc_name", "error"),
    [
        (FakeLLM(error=LLMError("Ollama request failed")), "s01_excerpt", "Ollama request failed"),
        (FakeLLM(answer={"anything": 1}), "empty_text", "document has no text"),
    ],
)
def test_failures_return_a_failed_row(reference, document, llm, doc_name, error):
    row = Processor(Settings(), reference, llm).process(document(doc_name))
    assert row.ai_status == "failed"
    assert error in row.ai_error
    assert row.claims_json == "[]"
