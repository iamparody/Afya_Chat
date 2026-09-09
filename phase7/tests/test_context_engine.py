"""
Phase 7c -- Context engine unit tests.

Verifies:
1. Malaria in lake_basin in June -> evidence fires (post_long_rains, direct, strong/high)
2. Malaria in highland in January -> NO_RELEVANT_CONTEXT (region + seasonal mismatch)
3. Hypertension -> NO_RELEVANT_CONTEXT (no environmental_signals on card)
4. AGE + flooding in April + unsafe_water exposure -> evidence fires
5. AGE + flooding in April + no exposure -> suppressed (requires_exposure gate)
6. CHIRPSProvider falls back to static_calendar source label in Phase 7
7. Pneumonia cold_dry_season low/low -> suppressed -> NO_RELEVANT_CONTEXT

Tests use injected fixtures -- do not depend on graph_entities.jsonl.

Run from cds/ root:
    python phase7/tests/test_context_engine.py
"""

import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from phase7.context_engine import (
    NO_RELEVANT_CONTEXT,
    CHIRPSProvider,
    EnvironmentalEvidence,
    StaticCalendarProvider,
    _inject_signal_data,
    _reset_signal_cache,
    get_environmental_evidence,
)

# ---------------------------------------------------------------------------
# Fixture data (verbatim from card structure, not read from disk)
# ---------------------------------------------------------------------------

_MALARIA_SIGNALS = [
    {
        "signal": "post_long_rains",
        "pathways": ["vector_borne"],
        "effect_type": "transmission_opportunity",
        "effect_direction": "up",
        "lag_weeks": {"min": 4, "max": 8},
        "strength": "strong",
        "confidence": "high",
        "causal_distance": "direct",
        "evidence_type": "observed_outbreaks",
        "regions": ["lake_basin", "coast", "highland_margins"],
        "seasonal_basis": "typical_long_rains",
        "applicability": {"requires_exposure": [], "amplifiers": ["mosquito_exposure_high"]},
    },
    {
        "signal": "post_short_rains",
        "pathways": ["vector_borne"],
        "effect_type": "transmission_opportunity",
        "effect_direction": "up",
        "lag_weeks": {"min": 4, "max": 8},
        "strength": "moderate",
        "confidence": "moderate",
        "causal_distance": "direct",
        "evidence_type": "surveillance_data",
        "regions": ["lake_basin", "coast"],
        "seasonal_basis": "typical_short_rains",
        "applicability": {"requires_exposure": [], "amplifiers": ["mosquito_exposure_high"]},
    },
]

_AGE_SIGNALS = [
    {
        "signal": "flooding",
        "pathways": ["waterborne"],
        "effect_type": "transmission_opportunity",
        "effect_direction": "up",
        "lag_weeks": {"min": 0, "max": 2},
        "strength": "moderate",
        "confidence": "moderate",
        "causal_distance": "direct",
        "evidence_type": "observed_outbreaks",
        "regions": ["nationwide"],
        "seasonal_basis": "outbreak_associated",
        "applicability": {"requires_exposure": ["unsafe_water"], "amplifiers": ["floodwater_contact"]},
    },
]

_PNEUMONIA_SIGNALS = [
    {
        "signal": "cold_dry_season",
        "pathways": ["respiratory_mucosal"],
        "effect_type": "transmission_opportunity",
        "effect_direction": "up",
        "lag_weeks": {"min": 0, "max": 4},
        "strength": "low",
        "confidence": "low",
        "causal_distance": "indirect",
        "evidence_type": "expert_estimate",
        "regions": ["highland"],
        "seasonal_basis": "cold_dry_season",
        "applicability": {"requires_exposure": [], "amplifiers": []},
    },
]

_TEST_SIGNALS: dict = {
    "Malaria (unspecified)": _MALARIA_SIGNALS,
    "Acute gastroenteritis (infectious)": _AGE_SIGNALS,
    "Community-acquired pneumonia": _PNEUMONIA_SIGNALS,
    "Essential hypertension": [],
}


def _setup() -> None:
    _reset_signal_cache()
    _inject_signal_data(_TEST_SIGNALS)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_malaria_lake_basin_june_fires():
    """post_long_rains is active in June; lake_basin is in the signal's regions."""
    _setup()
    result = get_environmental_evidence(
        candidates=["Malaria (unspecified)"],
        encounter_date=datetime(2026, 6, 15),
        patient_location="lake_basin",
    )
    assert isinstance(result, list), f"Expected list, got: {result}"
    signals_found = {ev.signal for ev in result}
    assert "post_long_rains" in signals_found, f"post_long_rains not in {signals_found}"
    ev = next(ev for ev in result if ev.signal == "post_long_rains")
    assert ev.causal_distance == "direct"
    assert ev.source == "static_calendar"
    assert ev.strength == "strong"
    assert ev.confidence == "high"
    assert ev.condition == "Malaria (unspecified)"
    assert ev.temporal_window == {"min": 4, "max": 8}
    print("PASS  Malaria + lake_basin + June -> post_long_rains fires (direct, strong/high)")


def test_malaria_highland_january_no_context():
    """
    January: post_long_rains not active (Jun-Aug), post_short_rains active but
    regions=[lake_basin, coast] -- highland is excluded. No flooding in January.
    All signals filtered -> NO_RELEVANT_CONTEXT.
    """
    _setup()
    result = get_environmental_evidence(
        candidates=["Malaria (unspecified)"],
        encounter_date=datetime(2026, 1, 15),
        patient_location="highland",
    )
    assert result == NO_RELEVANT_CONTEXT, f"Expected NO_RELEVANT_CONTEXT, got: {result}"
    print("PASS  Malaria + highland + January -> NO_RELEVANT_CONTEXT (region + seasonal mismatch)")


def test_hypertension_no_signals():
    """Hypertension has no environmental_signals declared -> NO_RELEVANT_CONTEXT."""
    _setup()
    result = get_environmental_evidence(
        candidates=["Essential hypertension"],
        encounter_date=datetime(2026, 6, 15),
        patient_location="highland",
    )
    assert result == NO_RELEVANT_CONTEXT, f"Expected NO_RELEVANT_CONTEXT, got: {result}"
    print("PASS  Hypertension -> NO_RELEVANT_CONTEXT (no environmental_signals)")


def test_age_flooding_with_unsafe_water_fires():
    """April is a flooding month; regions=nationwide; patient has unsafe_water -> fires."""
    _setup()
    result = get_environmental_evidence(
        candidates=["Acute gastroenteritis (infectious)"],
        encounter_date=datetime(2026, 4, 15),
        patient_location="coast",
        patient_exposures=["unsafe_water"],
    )
    assert isinstance(result, list), f"Expected list, got: {result}"
    assert len(result) >= 1
    ev = result[0]
    assert ev.signal == "flooding"
    assert ev.source == "static_calendar"
    assert ev.condition == "Acute gastroenteritis (infectious)"
    print("PASS  AGE + April + unsafe_water -> flooding evidence fires")


def test_age_flooding_without_exposure_suppressed():
    """
    Same date and location as above, but no patient exposures.
    flooding requires unsafe_water -> exposure gate fails -> NO_RELEVANT_CONTEXT.
    """
    _setup()
    result = get_environmental_evidence(
        candidates=["Acute gastroenteritis (infectious)"],
        encounter_date=datetime(2026, 4, 15),
        patient_location="coast",
        patient_exposures=[],
    )
    assert result == NO_RELEVANT_CONTEXT, f"Expected NO_RELEVANT_CONTEXT, got: {result}"
    print("PASS  AGE + April + no exposure -> flooding suppressed (requires unsafe_water)")


def test_chirps_falls_back_to_static_calendar():
    """CHIRPSProvider returns source='static_calendar' in Phase 7."""
    provider = CHIRPSProvider()
    is_active, source = provider.is_signal_active("post_long_rains", datetime(2026, 7, 1))
    assert source == "static_calendar", f"Expected static_calendar, got: {source}"
    assert is_active is True, "post_long_rains should be active in July"
    print("PASS  CHIRPSProvider falls back -> source_label = static_calendar")


def test_pneumonia_low_low_suppressed():
    """
    July is cold_dry_season month; highland is in signal regions.
    strength=low, confidence=low -> suppressed by strength/confidence gate.
    """
    _setup()
    result = get_environmental_evidence(
        candidates=["Community-acquired pneumonia"],
        encounter_date=datetime(2026, 7, 15),
        patient_location="highland",
    )
    assert result == NO_RELEVANT_CONTEXT, (
        f"Expected NO_RELEVANT_CONTEXT (low/low suppressed), got: {result}"
    )
    print("PASS  Pneumonia cold_dry_season low/low -> suppressed -> NO_RELEVANT_CONTEXT")


if __name__ == "__main__":
    test_malaria_lake_basin_june_fires()
    test_malaria_highland_january_no_context()
    test_hypertension_no_signals()
    test_age_flooding_with_unsafe_water_fires()
    test_age_flooding_without_exposure_suppressed()
    test_chirps_falls_back_to_static_calendar()
    test_pneumonia_low_low_suppressed()
    print("\nAll 7 tests passed.")
