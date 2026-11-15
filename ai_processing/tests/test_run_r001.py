"""Tests for run_r001.py, with the fake model."""
import json

from ai_processing.config import Settings
from ai_processing.run_r001 import run
from ai_processing.tests.conftest import FIXTURES_DIR
from ai_processing.tests.fakes import FakeLLM


def test_run_writes_the_ai_claims_row(tmp_path):
    answer = json.loads((FIXTURES_DIR / "llm_responses" / "r001_answer.json").read_text(encoding="utf-8"))
    output = tmp_path / "R001_output.json"

    row = run(Settings(), FakeLLM(answer), output)

    saved = json.loads(output.read_text(encoding="utf-8"))
    assert saved["source_id"] == "BRAVE-R001-1"
    assert saved["ai_status"] == "ok"
    assert saved == json.loads(row.model_dump_json())
