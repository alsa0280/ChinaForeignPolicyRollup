"""Shared pytest fixtures for the ai_processing tests."""
import json
from pathlib import Path

import pytest

from ai_processing.config import ReferenceData
from ai_processing.models import Document
from ai_processing.run_r001 import R001_SAMPLE, R001_SOURCE_ID

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def read_document_json(name: str) -> dict:
    """Raw JSON of a document fixture in fixtures/documents/<name>.json."""
    path = FIXTURES_DIR / "documents" / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def reference() -> ReferenceData:
    return ReferenceData.from_files()


@pytest.fixture(scope="session")
def r001_document() -> Document:
    """Daniele's R001 sample (Newsweek), as registered in source_registry.json."""
    return Document.from_sample(R001_SAMPLE, R001_SOURCE_ID)


@pytest.fixture
def document():
    """Return a loader that turns a document fixture name into a Document."""
    return lambda name: Document.model_validate(read_document_json(name))


@pytest.fixture(scope="session")
def baseline_cases() -> list:
    path = FIXTURES_DIR / "baseline_mismatched_claims.json"
    return json.loads(path.read_text(encoding="utf-8"))["cases"]
