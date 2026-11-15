"""Tests for reference_data.py."""


def test_loads_opportunities_and_source_types(reference):
    assert len(reference.opportunities) == 28
    assert "expiry" in reference.opportunity("F01").monitor_triggers
    assert reference.source_type("S01") == "official"
    assert reference.source_type("BRAVE-R001-1") == "reported"
