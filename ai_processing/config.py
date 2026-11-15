"""Everything loaded when the service starts: settings from environment variables
(and a local .env file) and the reference data in data/.

Defaults work on a local machine with Ollama running and qwen2.5:7b and bge-m3 pulled.
"""
import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from ai_processing.models import Opportunity

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
PROMPTS_DIR = REPO_ROOT / "prompts" / "ai_processing"
OPPORTUNITIES_FILE = DATA_DIR / "opportunities.json"
SOURCE_REGISTRY_FILE = DATA_DIR / "source_registry.json"


@dataclass(frozen=True)
class Settings:
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    ollama_embed_model: str = "bge-m3"
    ollama_timeout_s: float = 600.0
    ollama_num_ctx: int = 8192
    max_text_chars: int = 6000
    prompt_version: str = "assess_v1"

    @classmethod
    def from_env(cls, read_env_file: bool = True) -> "Settings":
        """Build settings from environment variables, falling back to the defaults."""
        if read_env_file:
            load_dotenv()
        defaults = cls()
        return cls(
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", defaults.ollama_base_url),
            ollama_model=os.getenv("OLLAMA_MODEL", defaults.ollama_model),
            ollama_embed_model=os.getenv("OLLAMA_EMBED_MODEL", defaults.ollama_embed_model),
            ollama_timeout_s=float(os.getenv("OLLAMA_TIMEOUT_S", defaults.ollama_timeout_s)),
            ollama_num_ctx=int(os.getenv("OLLAMA_NUM_CTX", defaults.ollama_num_ctx)),
            max_text_chars=int(os.getenv("MAX_TEXT_CHARS", defaults.max_text_chars)),
            prompt_version=os.getenv("PROMPT_VERSION", defaults.prompt_version),
        )

    @property
    def prompt_file(self) -> Path:
        return PROMPTS_DIR / f"{self.prompt_version}.md"


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
