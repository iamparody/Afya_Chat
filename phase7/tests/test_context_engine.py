"""
Phase 7c -- Context engine unit tests (10 cases).

Covers:
  1.  Asthma (no environmental_signals) -> NO_RELEVANT_CONTEXT
  2.  AGE + flooding + unsafe_water -> evidence fires
  3.  AGE + flooding + no exposure -> suppressed (exposure gate)
  4.  CAP cold_dry_season low/low -> ContextResult with suppressed, NOT NO_RELEVANT_CONTEXT
  5.  IDA + drought -> indirect, lag 4-16 w preserved in temporal_window
  6.  onset_date supplied -> onset_date used instead of encounter_date
  7.  Region mismatch -> signal suppressed (NO_RELEVANT_CONTEXT)
  8.  nationwide region -> passes for any patient_location
  9.  CHIRPS unavailable -> explicit StaticCalendar fallback (source_label = static_calendar)
  10. Multiple candidates with signals -> all valid signals preserved, not overwritten

Gate ordering design note (from colleague review):
  Strength/confidence is gate 4 -- AFTER seasonal activation (gate 3).
  A low/low signal that is seasonally active goes into ContextResult.suppressed,
  NOT into NO_RELEVANT_CONTEXT.  The audit trail must distinguish "matched but
  suppressed" from "no signal declared."  Tests 4 and 7 verify this distinction.

Tests use injected fixtures -- do not depend on graph_entities.jsonl on disk.

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
    ContextResult,
    EnvironmentalEvidence,
    StaticCalendarProvider,
    _inject_signal_data,
    _reset_signal_cache,
    get_environmental_evidence,
)

# ---------------------------------------------------------------------------
# Fixture signal data (verbatim card structure, not read from disk)
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

_CAP_SIGNALS = [
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

_IDA_SIGNALS = [
    {
        "signal": "prolonged_drought",
        "pathways": ["nutritional_vulnerability"],
        "effect_type": "severity_modifier",
        "effect_direction": "up",
        "lag_weeks": {"min": 4, "max": 16},
        "strength": "moderate",
        "confidence": "moderate",
        "causal_distance": "indirect",
        "evidence_type": "regional_epidemiological_evidence",
        "regions": ["arid_semi_arid", "northern_kenya"],
        "seasonal_basis": "dry_season",
        "applicability": {"requires_exposure": [], "amplifiers": []},
    },
]

# Two conditions each contributing one signal active in July + lake_basin
_MULTI_CONDITION_A = [
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
        "regions": ["lake_basin"],
        "seasonal_basis": "typical_long_rains",
        "applicability": {"requires_exposure": [], "amplifiers": []},
    },
]

_MULTI_CONDITION_B = [
    {
        "signal": "cold_dry_season",
        "pathways": ["respiratory_mucosal"],
        "effect_type": "severity_modifier",
        "effect_direction": "up",
        "lag_weeks": {"min": 0, "max": 4},
        "strength": "strong",   # strong/high so it is NOT suppressed
        "confidence": "high",
        "causal_distance": "direct",
        "evidence_type": "surveillance_data",
        "regions": ["lake_basin"],
        "seasonal_basis": "cold_dry_season",
        "applicability": {"requires_exposure": [], "amplifiers": []},
    },
]

_BASE_FIXTURES: dict = {
    "Malaria (unspecified)":              _MALARIA_SIGNALS,
    "Acute gastroenteritis (infectious)": _AGE_SIGNALS,
    "Community-acquired pneumonia":       _CAP_SIGNALS,
    "Iron deficiency anaemia":            _IDA_SIGNALS,
    "Essential hypertension":             [],
    "Asthma":                             [],
    "Multi Condition A":                  _MULTI_CONDITION_A,
    "Multi Condition B":                  _MULTI_CONDITION_B,
}


def _setup() -> None:
    _reset_signal_cache()
    _inject_signal_data(_BASE_FIXTURES)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_1_asthma_no_signals():
    """Asthma has no environmental_signals -> NO_RELEVANT_CONTEXT."""
    _setup()
    result = get_environmental_evidence(
        candidates=["Asthma"],
        encounter_date=datetime(2026, 7, 15),
        patient_location="highland",
    )
    assert result == NO_RELEVANT_CONTEXT, f"Expected NO_RELEVANT_CONTEXT, got: {result}"
    print("PASS  1. Asthma -> NO_RELEVANT_CONTEXT (no environmental_signals)")


def test_2_age_flooding_with_exposure_fires():
    """April + unsafe_water -> flooding signal passes all 4 gates."""
    _setup()
    result = get_environmental_evidence(
        candidates=["Acute gastroenteritis (infectious)"],
        encounter_date=datetime(2026, 4, 15),
        patient_location="coast",
        patient_exposures=["unsafe_water"],
    )
    assert isinstance(result, ContextResult), f"Expected ContextResult, got: {result}"
    assert result.has_evidence, f"Expected evidence, got suppressed only: {result.suppressed}"
    ev = result.evidence[0]
    assert ev.signal == "flooding"
    assert ev.source == "static_calendar"
    assert ev.suppression_reason == ""
    assert ev.condition == "Acute gastroenteritis (infectious)"
    print("PASS  2. AGE + April + unsafe_water -> flooding evidence fires")


def test_3_age_flooding_without_exposure_suppressed():
    """Same date, no exposure -> exposure gate (gate 2) fails -> NO_RELEVANT_CONTEXT.
    Distinct from test 4: signal fails BEFORE gate 4 so result is NO_RELEVANT_CONTEXT,
    not a ContextResult with suppressed."""
    _setup()
    result = get_environmental_evidence(
        candidates=["Acute gastroenteritis (infectious)"],
        encounter_date=datetime(2026, 4, 15),
        patient_location="coast",
        patient_exposures=[],
    )
    assert result == NO_RELEVANT_CONTEXT, (
        f"Expected NO_RELEVANT_CONTEXT (exposure gate fails before gate 4), got: {result}"
    )
    print("PASS  3. AGE + April + no exposure -> NO_RELEVANT_CONTEXT (exposure gate, not gate 4)")


def test_4_cap_low_low_suppressed_with_audit_trail():
    """
    CAP cold_dry_season: July + highland -> passes gates 1-3.
    strength=low/confidence=low -> gate 4 suppresses.
    Must return ContextResult with non-empty .suppressed, NOT NO_RELEVANT_CONTEXT.
    This is the critical audit-trail distinction: 'matched but suppressed' != 'no signal'.
    """
    _setup()
    result = get_environmental_evidence(
        candidates=["Community-acquired pneumonia"],
        encounter_date=datetime(2026, 7, 15),
        patient_location="highland",
    )
    assert isinstance(result, ContextResult), (
        f"Expected ContextResult (signal matched but suppressed), got: {result!r}"
    )
    assert not result.has_evidence, f"evidence should be empty, got: {result.evidence}"
    assert len(result.suppressed) == 1, f"Expected 1 suppressed signal, got: {result.suppressed}"
    sup = result.suppressed[0]
    assert sup.signal == "cold_dry_season"
    assert sup.causal_distance == "indirect"
    assert "strength:low/confidence:low" in sup.suppression_reason
    print("PASS  4. CAP low/low -> ContextResult.suppressed (not NO_RELEVANT_CONTEXT) -- audit trail preserved")


def test_5_ida_drought_indirect_lag_preserved():
    """
    IDA prolonged_drought: July + arid_semi_arid -> matches.
    Verifies: indirect causal_distance carried, lag 4-16 w preserved in temporal_window.
    """
    _setup()
    result = get_environmental_evidence(
        candidates=["Iron deficiency anaemia"],
        encounter_date=datetime(2026, 7, 15),
        patient_location="arid_semi_arid",
    )
    assert isinstance(result, ContextResult), f"Expected ContextResult, got: {result}"
    assert result.has_evidence, f"Expected evidence, got: {result}"
    ev = result.evidence[0]
    assert ev.signal == "prolonged_drought"
    assert ev.causal_distance == "indirect"
    assert ev.effect_type == "severity_modifier"
    assert ev.temporal_window == {"min": 4, "max": 16}, (
        f"Expected lag {{min:4, max:16}}, got: {ev.temporal_window}"
    )
    assert ev.condition == "Iron deficiency anaemia"
    assert "[indirect association]" in ev.explanation
    print("PASS  5. IDA + drought -> indirect, lag 4-16 w in temporal_window, hedged explanation")


def test_6_onset_date_overrides_encounter_date():
    """
    encounter_date = September (not a post_long_rains month).
    onset_date = July (post_long_rains active month).
    Signal should fire because onset_date is used as reference.
    Without onset_date: would return NO_RELEVANT_CONTEXT.
    """
    _setup()

    # Confirm encounter_date alone gives NO_RELEVANT_CONTEXT
    without_onset = get_environmental_evidence(
        candidates=["Malaria (unspecified)"],
        encounter_date=datetime(2026, 9, 10),
        patient_location="lake_basin",
    )
    assert without_onset == NO_RELEVANT_CONTEXT, (
        f"Baseline check failed: expected NO_RELEVANT_CONTEXT without onset_date, got: {without_onset}"
    )

    # Now supply onset_date in July -> should fire
    with_onset = get_environmental_evidence(
        candidates=["Malaria (unspecified)"],
        encounter_date=datetime(2026, 9, 10),
        patient_location="lake_basin",
        onset_date=datetime(2026, 7, 15),
    )
    assert isinstance(with_onset, ContextResult), f"Expected ContextResult with onset_date, got: {with_onset}"
    assert with_onset.has_evidence
    signals = {ev.signal for ev in with_onset.evidence}
    assert "post_long_rains" in signals, f"post_long_rains expected, got: {signals}"
    print("PASS  6. onset_date July used instead of encounter_date September -> post_long_rains fires")


def test_7_region_mismatch_suppressed():
    """
    Malaria post_long_rains: regions=[lake_basin, coast, highland_margins].
    patient_location=highland (not in list) -> region gate fails -> NO_RELEVANT_CONTEXT.
    January: post_short_rains active but regions=[lake_basin, coast] -- also excluded.
    All malaria signals region-gated out.
    """
    _setup()
    result = get_environmental_evidence(
        candidates=["Malaria (unspecified)"],
        encounter_date=datetime(2026, 1, 15),
        patient_location="highland",
    )
    assert result == NO_RELEVANT_CONTEXT, (
        f"Expected NO_RELEVANT_CONTEXT (region mismatch for all signals), got: {result}"
    )
    print("PASS  7. Malaria + highland -> NO_RELEVANT_CONTEXT (all signals region-gated out)")


def test_8_nationwide_region_passes_any_location():
    """
    AGE flooding: regions=['nationwide'].
    'nationwide' must pass region gate for any patient_location value.
    """
    _setup()
    for location in ["highland", "coast", "lake_basin", "arid_semi_arid", "urban_informal"]:
        result = get_environmental_evidence(
            candidates=["Acute gastroenteritis (infectious)"],
            encounter_date=datetime(2026, 4, 15),
            patient_location=location,
            patient_exposures=["unsafe_water"],
        )
        assert isinstance(result, ContextResult) and result.has_evidence, (
            f"Expected flooding to fire for patient_location={location!r}, got: {result}"
        )
    print("PASS  8. nationwide region -> flooding fires for all tested patient_location values")


def test_9_chirps_fallback_source_label():
    """CHIRPSProvider falls back to StaticCalendarProvider; source_label must be 'static_calendar'."""
    provider = CHIRPSProvider()

    # Active month check
    is_active, source = provider.is_signal_active("post_long_rains", datetime(2026, 7, 1))
    assert source == "static_calendar", f"Expected static_calendar, got: {source}"
    assert is_active is True

    # Inactive month check
    is_active_jan, source_jan = provider.is_signal_active("post_long_rains", datetime(2026, 1, 1))
    assert source_jan == "static_calendar"
    assert is_active_jan is False

    print("PASS  9. CHIRPSProvider always falls back -> source_label = static_calendar (Phase 7)")


def test_10_multiple_candidates_all_signals_preserved():
    """
    Two candidates each contribute one active signal in July + lake_basin.
    Both must appear in result.evidence -- the second must not overwrite the first.
    """
    _setup()
    result = get_environmental_evidence(
        candidates=["Multi Condition A", "Multi Condition B"],
        encounter_date=datetime(2026, 7, 15),
        patient_location="lake_basin",
    )
    assert isinstance(result, ContextResult), f"Expected ContextResult, got: {result}"
    assert result.has_evidence
    assert len(result.evidence) == 2, (
        f"Expected 2 evidence objects (one per condition), got: {len(result.evidence)}"
    )
    conditions_found = {ev.condition for ev in result.evidence}
    assert "Multi Condition A" in conditions_found
    assert "Multi Condition B" in conditions_found
    signals_found = {ev.signal for ev in result.evidence}
    assert "post_long_rains" in signals_found
    assert "cold_dry_season" in signals_found
    print("PASS  10. Two candidates with active signals -> both preserved in result.evidence")


if __name__ == "__main__":
    test_1_asthma_no_signals()
    test_2_age_flooding_with_exposure_fires()
    test_3_age_flooding_without_exposure_suppressed()
    test_4_cap_low_low_suppressed_with_audit_trail()
    test_5_ida_drought_indirect_lag_preserved()
    test_6_onset_date_overrides_encounter_date()
    test_7_region_mismatch_suppressed()
    test_8_nationwide_region_passes_any_location()
    test_9_chirps_fallback_source_label()
    test_10_multiple_candidates_all_signals_preserved()
    print("\nAll 10 tests passed.")
