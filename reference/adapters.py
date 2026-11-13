"""Contracts for student-built live adapters. These are NOT implemented."""
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class Document:
    source_id: str
    canonical_url: str
    fetched_at: str
    publication_date: str | None
    sha256: str
    language: str
    text: str
    locator_map: dict

class SearchProvider(Protocol):
    def search(self, query: str, language: str, limit: int) -> list[dict]: ...

class Collector(Protocol):
    def fetch(self, source: dict) -> Document: ...

class Extractor(Protocol):
    def extract(self, document: Document, schema: dict) -> list[dict]: ...

class Verifier(Protocol):
    def verify(self, claims: list[dict], documents: list[Document]) -> dict: ...

# Do not put provider credentials here. Implement these contracts in an
# institution-approved environment, with credentials in its secret store.
# Before collection: source conditions, rate limits, redirect/private-network
# checks, file type/size limits, retry policy and visible source health.
