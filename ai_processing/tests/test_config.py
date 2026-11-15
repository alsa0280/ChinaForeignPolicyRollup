"""Tests for config.py."""
from ai_processing.config import ReferenceData, Settings

ENV_VARS = [
    "OLLAMA_BASE_URL", "OLLAMA_MODEL", "OLLAMA_EMBED_MODEL", "OLLAMA_TIMEOUT_S",
    "OLLAMA_NUM_CTX", "MAX_TEXT_CHARS", "PROMPT_VERSION",
]


def test_defaults_when_nothing_is_set(monkeypatch):
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    settings = Settings.from_env(read_env_file=False)
    assert settings == Settings()
    assert settings.prompt_file.exists()


def test_environment_variables_override_defaults(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5:3b")
    monkeypatch.setenv("MAX_TEXT_CHARS", "4000")
    settings = Settings.from_env(read_env_file=False)
    assert settings.ollama_model == "qwen2.5:3b"
    assert settings.max_text_chars == 4000


def test_reference_data_loads_opportunities_and_source_types():
    reference = ReferenceData.from_files()
    assert len(reference.opportunities) == 28
    assert "expiry" in reference.opportunity("F01").monitor_triggers
    assert reference.source_type("S01") == "official"
    assert reference.source_type("BRAVE-R001-1") == "reported"
