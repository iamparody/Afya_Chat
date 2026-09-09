"""
Phase 7d integration tests — prompt injection contract.

Verifies:
1. Zero-context (no location, no exposures) -> ## Environmental context absent from prompt
2. env_evidence=[] -> ## Environmental context absent (empty list is a no-op)
3. Suppressed-only ContextResult (evidence=[], suppressed=[...]) ->
   rag.py does NOT inject section (suppressed signals are not sent to Gemini)
4. Active evidence -> ## Environmental context present with source label
5. build_context() backward-compatible — old 3-arg call still works

Tests do not require API keys. They test the prompt-construction contract only.

Run from cds/ root:
    python phase7/tests/test_7d_integration.py
"""

import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "phase5"))

from prompts import build_context
from phase7.context_engine import (
    NO_RELEVANT_CONTEXT,
    ContextResult,
    EnvironmentalEvidence,
    _inject_signal_data,
    _reset_signal_cache,
    get_environmental_evidence,
)

# Minimal stubs for build_context() call
_CANDIDATES = [{"condition": "Malaria (unspecified)", "matched_symptoms": [], "argues_against": []}]
_PASSAGES   = [{"condition": "Malaria (unspecified)", "section": "cardinal_symptoms", "text": "Fever, chills."}]

ENV_SECTION_HEADER = "## Environmental context"


def test_zero_context_no_section():
    """
    No patient_location, no patient_exposures -> env_evidence stays empty ->
    ## Environmental context must NOT appear in the prompt.
    Verifies the old pathway is fully preserved.
    """
    ctx = build_context("Fever 3 days", _CANDIDATES, _PASSAGES, env_evidence=None)
    assert ENV_SECTION_HEADER not in ctx, (
        f"## Environmental context must not appear when env_evidence=None"
    )
    print("PASS  1. env_evidence=None -> no environmental context section in prompt")


def test_empty_list_no_section():
    """
    env_evidence=[] (empty list from ContextResult.evidence when all suppressed or no match)
    -> ## Environmental context must NOT appear in prompt.
    """
    ctx = build_context("Fever 3 days", _CANDIDATES, _PASSAGES, env_evidence=[])
    assert ENV_SECTION_HEADER not in ctx, (
        f"## Environmental context must not appear when env_evidence=[]"
    )
    print("PASS  2. env_evidence=[] -> no environmental context section in prompt")


def test_suppressed_only_result_no_section():
    """
    ContextResult(evidence=[], suppressed=[ev]) -> rag.py extracts .evidence (empty list) ->
    build_context() receives [] -> no section injected.
    Suppressed signals must NOT reach Gemini.
    """
    sup_ev = EnvironmentalEvidence(
        signal="cold_dry_season",
        causal_distance="indirect",
        effect_type="transmission_opportunity",
        effect_direction="up",
        strength="low",
        confidence="low",
        suppression_reason="strength:low/confidence:low below emission threshold",
        explanation="Cold dry season -- elevated transmission opportunity for CAP in highland. Source: static seasonal calendar. Clinical findings take precedence.",
        condition="Community-acquired pneumonia",
    )
    # Simulate what rag.py does with a suppressed-only result
    env_result = ContextResult(evidence=[], suppressed=[sup_ev])
    env_evidence = env_result.evidence if isinstance(env_result, ContextResult) else []

    ctx = build_context("Cough 5 days", _CANDIDATES, _PASSAGES, env_evidence=env_evidence)
    assert ENV_SECTION_HEADER not in ctx, (
        "Suppressed signals must not produce ## Environmental context section"
    )
    print("PASS  3. ContextResult(evidence=[], suppressed=[...]) -> no section (suppressed stays out of prompt)")


def test_active_evidence_section_present():
    """
    When evidence fires, ## Environmental context must appear with the signal's
    explanation and a source label.
    """
    ev = EnvironmentalEvidence(
        signal="post_long_rains",
        causal_distance="direct",
        effect_type="transmission_opportunity",
        effect_direction="up",
        strength="strong",
        confidence="high",
        source="static_calendar",
        spatial_basis="lake_basin",
        temporal_window={"min": 4, "max": 8},
        explanation="Post long rains -- elevated transmission opportunity for Malaria (unspecified) in lake_basin; lag 4-8 weeks. Source: static seasonal calendar. Clinical findings take precedence.",
        condition="Malaria (unspecified)",
    )
    ctx = build_context("Fever 3 days", _CANDIDATES, _PASSAGES, env_evidence=[ev])
    assert ENV_SECTION_HEADER in ctx, "## Environmental context section must appear when evidence fires"
    assert "static seasonal calendar" in ctx, "Source label must appear in prompt"
    assert "Post long rains" in ctx or "post_long_rains" in ctx or "post long rains" in ctx
    assert "Clinical findings take precedence" in ctx
    print("PASS  4. Active evidence -> ## Environmental context section present with source label")


def test_build_context_backward_compatible():
    """
    Old 3-arg call (no env_evidence kwarg) must still work unchanged.
    Ensures evaluate.py and any other callers are not broken.
    """
    ctx = build_context("Fever 3 days", _CANDIDATES, _PASSAGES)
    assert ENV_SECTION_HEADER not in ctx
    assert "## Patient presentation" in ctx
    assert "## Retrieved candidates" in ctx
    print("PASS  5. build_context() 3-arg (pre-7d) call still works; no environmental section")


def test_no_location_context_engine_passthrough():
    """
    get_environmental_evidence() with patient_location=None and a signal that has
    region restrictions: should NOT fail; region gate is skipped when location=None
    (benefit of doubt -- unknown location does not exclude signals).
    """
    _reset_signal_cache()
    _inject_signal_data({
        "Malaria (unspecified)": [
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
                "regions": ["lake_basin", "coast"],
                "seasonal_basis": "typical_long_rains",
                "applicability": {"requires_exposure": [], "amplifiers": []},
            }
        ]
    })

    # June (active month for post_long_rains), no location
    result = get_environmental_evidence(
        candidates=["Malaria (unspecified)"],
        encounter_date=datetime(2026, 6, 15),
        patient_location=None,   # no location supplied
    )
    # With no location, region gate is skipped -> signal is active -> should fire
    assert isinstance(result, ContextResult), (
        f"Expected ContextResult when location=None (region gate skipped), got: {result}"
    )
    assert result.has_evidence
    print("PASS  6. patient_location=None -> region gate skipped -> signal fires (benefit of doubt)")


if __name__ == "__main__":
    test_zero_context_no_section()
    test_empty_list_no_section()
    test_suppressed_only_result_no_section()
    test_active_evidence_section_present()
    test_build_context_backward_compatible()
    test_no_location_context_engine_passthrough()
    print("\nAll 6 integration tests passed.")
