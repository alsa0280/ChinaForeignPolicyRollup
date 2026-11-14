"""Checks that the package and its modules can be imported."""
import importlib

import pytest

MODULES = [
    "ai_processing",
    "ai_processing.config",
    "ai_processing.reference_data",
    "ai_processing.validation",
    "ai_processing.credibility",
    "ai_processing.language",
    "ai_processing.llm_client",
    "ai_processing.processor",
    "ai_processing.app",
]


@pytest.mark.parametrize("name", MODULES)
def test_module_imports(name):
    assert importlib.import_module(name) is not None
