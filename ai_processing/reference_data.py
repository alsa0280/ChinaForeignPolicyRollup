"""Reference data the service depends on.

- data/opportunities.json: the 28 tracked opportunities.
- data/source_registry.json: the type of each source (official, company, reported).
"""
import json
from dataclasses import dataclass
from pathlib import Path

from ai_processing.models import Opportunity

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
OPPORTUNITIES_FILE = DATA_DIR / "opportunities.json"
SOURCE_REGISTRY_FILE = DATA_DIR / "source_registry.json"


def _read_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


@dataclass(frozen=True)
class ReferenceData:
    """Opportunities and source types, loaded once and shared by the service."""

    opportunities: dict[str, Opportunity]
    source_types: dict[str, str]

    @classmethod
    def from_files(
        cls,
        opportunities_file: Path = OPPORTUNITIES_FILE,
        source_registry_file: Path = SOURCE_REGISTRY_FILE,
    ) -> "ReferenceData":
        opportunities = [Opportunity.model_validate(item) for item in _read_json(opportunities_file)]
        return cls(
            opportunities={item.opportunity_id: item for item in opportunities},
            source_types={item["id"]: item.get("type", "") for item in _read_json(source_registry_file)},
        )

    def opportunity(self, opportunity_id: str) -> Opportunity | None:
        return self.opportunities.get(opportunity_id)

    def source_type(self, source_id: str) -> str | None:
        return self.source_types.get(source_id)
