"""Data models shared by the service: what a document, an opportunity and a
claim look like, and the fixed lists of allowed values."""
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


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


class Opportunity(BaseModel):
    """One tracked opportunity from data/opportunities.json (fields used here)."""

    model_config = ConfigDict(extra="ignore")

    opportunity_id: NonEmptyStr
    title: str
    stack: str | None = None
    stage: str | None = None
    monitor_triggers: list[str] = Field(default_factory=list)


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


class DroppedClaim(BaseModel):
    index: int | None
    reason: DropReason


class ValidationResult(BaseModel):
    kept: list[Claim] = Field(default_factory=list)
    dropped: list[DroppedClaim] = Field(default_factory=list)
