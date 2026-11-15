"""Data models shared by the service: what a document, an opportunity, a claim,
the model's answer and the output row look like, and the fixed lists of allowed
values.

Run `python -m ai_processing.models` after changing a model to regenerate the
JSON Schema in schemas/ai_processing/.
"""
import hashlib
import json
from enum import Enum
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

SCHEMA_FILE = Path(__file__).resolve().parents[1] / "schemas" / "ai_processing" / "llm_output.schema.json"


# --- fixed lists ---------------------------------------------------------------

class Dimension(str, Enum):
    """Which aspect of an opportunity a claim reports on."""

    CONTRACT_STAGE = "contract_stage"
    MARKET_ACCESS_STATUS = "market_access_status"
    TARIFF_OR_QUOTA = "tariff_or_quota"
    EXPIRY_DATE = "expiry_date"
    AMOUNT = "amount"
    CAPACITY_OR_VOLUME = "capacity_or_volume"
    REGULATORY_APPROVAL = "regulatory_approval"
    COUNTERPARTY = "counterparty"
    OTHER = "other"


class FocusArea(str, Enum):
    """The four working areas of the starter kit, or none."""

    ENERGY = "Energy supply"
    FOOD = "Food security"
    PAYMENTS = "Payments, settlement, and investment"
    PHARMA = "Pharmaceuticals and biotech"
    NONE = "none"

    @classmethod
    def parse(cls, value) -> "FocusArea":
        """Return the matching focus area (ignoring case and spaces), or NONE."""
        key = str(value or "").strip().lower()
        return next((area for area in cls if area.value.lower() == key), cls.NONE)


class Language(str, Enum):
    """Language of an article, as reported by the model."""

    ENGLISH = "en"
    MANDARIN = "zh"
    FRENCH = "fr"
    OTHER = "other"

    @classmethod
    def parse(cls, value) -> "Language":
        """Return the language for a code or common name ("zh", "Mandarin"...), or OTHER."""
        key = str(value or "").strip().lower()
        return LANGUAGE_ALIASES.get(key, cls.OTHER)


# Codes and names the model may use for each language.
LANGUAGE_ALIASES = {
    "en": Language.ENGLISH, "english": Language.ENGLISH,
    "zh": Language.MANDARIN, "zh-cn": Language.MANDARIN, "chinese": Language.MANDARIN,
    "mandarin": Language.MANDARIN,
    "fr": Language.FRENCH, "french": Language.FRENCH,
}


class ClaimType(str, Enum):
    REPORTED_FACT = "reported_fact"
    ANALYSIS = "analysis"


class DropReason(str, Enum):
    """Why a model claim was not kept."""

    CLAIMS_NOT_A_LIST = "claims_not_a_list"
    NOT_AN_OBJECT = "not_an_object"
    MISSING_FIELD = "missing_field"
    INVALID_DIMENSION = "invalid_dimension"
    UNKNOWN_OPPORTUNITY = "unknown_opportunity"
    QUOTE_NOT_IN_TEXT = "quote_not_in_text"
    BAD_LOCATOR = "bad_locator"
    UNRELATED_TO_OPPORTUNITY = "unrelated_to_opportunity"


# --- inputs --------------------------------------------------------------------

class Document(BaseModel):
    """One cleaned article, as defined in proposed_schemas.pdf."""

    model_config = ConfigDict(extra="ignore")

    source_id: NonEmptyStr
    url: str | None = None
    fetched_at: str | None = None
    status: str = "ok"
    title: str = ""
    published_at: str | None = None
    text: str = ""
    hash: str | None = None

    @classmethod
    def from_sample(cls, path: Path, source_id: str) -> "Document":
        """Build a document from a collection sample such as data/samples/R001.txt
        (header lines "Key: value", a line "---", then the article text)."""
        header, _, body = Path(path).read_text(encoding="utf-8").partition("\n---\n")
        fields = {}
        for line in header.splitlines():
            key, sep, value = line.partition(":")
            if sep:
                fields[key.strip()] = value.strip()
        text = body.strip()
        return cls(
            source_id=source_id,
            url=fields.get("URL"),
            fetched_at=fields.get("Collected on"),
            title=fields.get("Title", ""),
            published_at=fields.get("Publication date", "").split(" ")[0] or None,
            text=text,
            hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        )

    @property
    def paragraphs(self) -> list[str]:
        """The non-empty lines of the text (n8n joins paragraphs with line breaks).
        Paragraph N in a locator is item N-1 of this list."""
        return [line.strip() for line in self.text.split("\n") if line.strip()]


class Opportunity(BaseModel):
    """One tracked opportunity from data/opportunities.json (fields used here)."""

    model_config = ConfigDict(extra="ignore")

    opportunity_id: NonEmptyStr
    title: str
    stack: str | None = None
    monitor_triggers: list[str] = Field(default_factory=list)


# --- the model's answer ----------------------------------------------------------

class Claim(BaseModel):
    """One claim extracted by the model about one opportunity."""

    model_config = ConfigDict(extra="ignore", coerce_numbers_to_str=True)

    opportunity_id: NonEmptyStr
    dimension: Dimension
    value: NonEmptyStr
    claim_en: NonEmptyStr
    event_date: str | None = None
    locator: NonEmptyStr
    support_quote: NonEmptyStr
    support_quote_en: str | None = None
    claim_type: ClaimType = ClaimType.ANALYSIS
    uncertainty: list[str] = Field(default_factory=list)

    @field_validator("support_quote_en", mode="before")
    @classmethod
    def _empty_translation_is_none(cls, value):
        return value or None

    @field_validator("claim_type", mode="before")
    @classmethod
    def _unknown_type_is_analysis(cls, value):
        # Anything not clearly labelled a reported fact is never shown as a fact.
        return value if value in {item.value for item in ClaimType} else ClaimType.ANALYSIS

    @field_validator("uncertainty", mode="before")
    @classmethod
    def _uncertainty_as_strings(cls, value):
        return [str(item) for item in value] if isinstance(value, list) else []


class LLMAssessment(BaseModel):
    """What the model returns for one article (claims are validated separately)."""

    model_config = ConfigDict(extra="ignore")

    language: Language = Language.OTHER
    title_en: str = ""
    summary_en: str = ""
    focus_area: FocusArea = FocusArea.NONE
    relevance_score: int | None = None
    relevance_justification_en: str = ""
    credibility_adjustment: int = 0
    credibility_reason: str = ""
    uncertain: bool = False
    red_flags: list[str] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)

    @field_validator("language", mode="before")
    @classmethod
    def _parse_language(cls, value):
        return Language.parse(value)

    @field_validator("focus_area", mode="before")
    @classmethod
    def _parse_focus_area(cls, value):
        return FocusArea.parse(value)

    @field_validator("relevance_score", mode="before")
    @classmethod
    def _score_from_1_to_5(cls, value):
        if isinstance(value, bool):
            return None
        try:
            return min(5, max(1, round(float(value))))
        except (TypeError, ValueError, OverflowError):
            return None

    @field_validator("credibility_adjustment", mode="before")
    @classmethod
    def _adjustment_or_zero(cls, value):
        # Anything that is not a whole number counts as "no adjustment";
        # CredibilityScorer decides whether the number is allowed.
        return value if type(value) is int else 0

    @field_validator("red_flags", mode="before")
    @classmethod
    def _flags_as_strings(cls, value):
        return [str(item) for item in value] if isinstance(value, list) else []

    @classmethod
    def from_model_output(cls, raw: dict) -> tuple["LLMAssessment", list]:
        """Parse the article fields and return the raw claims for ClaimValidator.

        Claims are kept apart so one bad claim does not discard the whole answer.
        """
        raw_claims = raw.get("claims", [])
        assessment = cls.model_validate({**raw, "claims": []})
        return assessment, raw_claims

    @classmethod
    def json_schema(cls) -> dict:
        """JSON Schema sent to Ollama, with every field required so the model fills them all."""
        schema = cls.model_json_schema()
        for definition in [schema, *schema.get("$defs", {}).values()]:
            if "properties" in definition:
                definition["required"] = list(definition["properties"])
        return schema

    @classmethod
    def json_schema_text(cls) -> str:
        """The schema as written to SCHEMA_FILE."""
        return json.dumps(cls.json_schema(), indent=2, ensure_ascii=False) + "\n"


# --- results -----------------------------------------------------------------------

class DroppedClaim(BaseModel):
    index: int | None
    reason: DropReason


class ValidationResult(BaseModel):
    kept: list[Claim] = Field(default_factory=list)
    dropped: list[DroppedClaim] = Field(default_factory=list)


class AIClaimsRow(BaseModel):
    """One row of the ai_claims table: the service's answer for one document.

    The first block matches the columns of schemas/tables/ai_claims.txt; the
    second block holds the Role 4 additions. JSON lists are stored as text, like
    claims_json, so n8n can write them to text columns.
    """

    source_id: str
    url: str | None
    hash: str | None
    credibility_score: int | None
    relevance_score: int | None
    relevance_justification_en: str
    summary_en: str
    claims_json: str
    claims_dropped: int
    analyzed_at: str

    language: Language
    title_en: str
    focus_area: FocusArea
    credibility_reason: str
    uncertain: bool
    red_flags: str
    ai_status: str
    ai_error: str
    model: str
    prompt_version: str


if __name__ == "__main__":
    SCHEMA_FILE.parent.mkdir(parents=True, exist_ok=True)
    SCHEMA_FILE.write_text(LLMAssessment.json_schema_text(), encoding="utf-8")
    print(f"Wrote {SCHEMA_FILE}")
