"""Tests for app.py, with the fake model instead of Ollama."""
import json

import pytest
from fastapi.testclient import TestClient

from ai_processing.app import create_app
from ai_processing.config import Settings
from ai_processing.tests.conftest import FIXTURES_DIR
from ai_processing.tests.fakes import FakeLLM


@pytest.fixture
def client():
    answer = json.loads((FIXTURES_DIR / "llm_responses" / "r001_answer.json").read_text(encoding="utf-8"))
    return TestClient(create_app(Settings(), FakeLLM(answer)))


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "model": "qwen2.5:7b", "prompt_version": "assess_v1"}


def test_process_returns_the_ai_claims_row(client, r001_document):
    response = client.post("/process", json=r001_document.model_dump())

    row = response.json()
    assert response.status_code == 200
    assert row["source_id"] == "BRAVE-R001-1"
    assert row["ai_status"] == "ok"
    assert [c["opportunity_id"] for c in json.loads(row["claims_json"])] == ["F01"]


def test_process_rejects_a_document_without_source_id(client):
    response = client.post("/process", json={"text": "Some text"})

    assert response.status_code == 422
