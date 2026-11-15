"""Shared pytest fixtures for the ai_processing tests."""
import hashlib
import json
from pathlib import Path

import pytest

from ai_processing.models import Document
from ai_processing.reference_data import DATA_DIR, ReferenceData

FIXTURES_DIR = Path(__file__).parent / "fixtures"
R001_SAMPLE = DATA_DIR / "samples" / "R001.txt"


def read_document_json(name: str) -> dict:
    """Raw JSON of a document fixture in fixtures/documents/<name>.json."""
    path = FIXTURES_DIR / "documents" / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def document_from_sample(path: Path, source_id: str) -> Document:
    """Build a Document from a collection sample (header lines, '---', then text)."""
    header, _, body = path.read_text(encoding="utf-8").partition("\n---\n")
    fields = {}
    for line in header.splitlines():
        key, sep, value = line.partition(":")
        if sep:
            fields[key.strip()] = value.strip()
    text = body.strip()
    return Document(
        source_id=source_id,
        url=fields.get("URL"),
        fetched_at=fields.get("Collected on"),
        title=fields.get("Title", ""),
        published_at=fields.get("Publication date", "").split(" ")[0] or None,
        text=text,
        hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
    )


@pytest.fixture(scope="session")
def reference() -> ReferenceData:
    return ReferenceData.from_files()


@pytest.fixture(scope="session")
def r001_document() -> Document:
    """Daniele's R001 sample (Newsweek), as registered in source_registry.json."""
    return document_from_sample(R001_SAMPLE, "BRAVE-R001-1")


@pytest.fixture
def document():
    """Return a loader that turns a document fixture name into a Document."""
    return lambda name: Document.model_validate(read_document_json(name))


@pytest.fixture(scope="session")
def baseline_cases() -> list:
    path = FIXTURES_DIR / "baseline_mismatched_claims.json"
    return json.loads(path.read_text(encoding="utf-8"))["cases"]
