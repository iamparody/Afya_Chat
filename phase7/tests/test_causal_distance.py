"""
Phase 7 schema validation — causal_distance field.

Verifies:
1. graph_entities.jsonl carries correct causal_distance values after backfill.
2. EnvironmentalEvidence can be constructed from both a direct (malaria/post_long_rains)
   and an indirect (anaemia/prolonged_drought) signal record.
3. ingest.py validate_environmental() warns when causal_distance is missing or invalid.

Run from the cds/ root:
    python phase7/tests/test_causal_distance.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from phase7.context_engine import EnvironmentalEvidence
from ingest import validate_environmental


def _load_graph_records() -> dict:
    path = ROOT / "graph_entities.jsonl"
    if not path.exists():
        raise SystemExit(f"graph_entities.jsonl not found — run python ingest.py first")
    records = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            records[r["condition"]] = r
    return records


def test_malaria_post_long_rains_is_direct():
    records = _load_graph_records()
    malaria = records["Malaria (unspecified)"]
    sig = next(s for s in malaria["environmental_signals"] if s["signal"] == "post_long_rains")
    assert sig["causal_distance"] == "direct", (
        f"Expected causal_distance=direct, got '{sig.get('causal_distance')}'"
    )
    assert sig["effect_type"] == "transmission_opportunity"
    assert sig["strength"] == "strong"
    print("PASS  malaria / post_long_rains -> causal_distance=direct, effect_type=transmission_opportunity")


def test_anaemia_drought_is_indirect():
    records = _load_graph_records()
    anaemia = records["Iron deficiency anaemia"]
    sig = next(s for s in anaemia["environmental_signals"] if s["signal"] == "prolonged_drought")
    assert sig["causal_distance"] == "indirect", (
        f"Expected causal_distance=indirect, got '{sig.get('causal_distance')}'"
    )
    assert sig["effect_type"] == "severity_modifier"
    assert sig["strength"] == "moderate"
    print("PASS  anaemia / prolonged_drought -> causal_distance=indirect, effect_type=severity_modifier")


def test_environmental_evidence_from_direct_signal():
    records = _load_graph_records()
    malaria = records["Malaria (unspecified)"]
    sig = next(s for s in malaria["environmental_signals"] if s["signal"] == "post_long_rains")

    ev = EnvironmentalEvidence(
        signal=sig["signal"],
        causal_distance=sig["causal_distance"],
        effect_type=sig["effect_type"],
        effect_direction=sig["effect_direction"],
        strength=sig["strength"],
        confidence=sig["confidence"],
        temporal_window=sig.get("lag_weeks", {}),
    )

    assert ev.causal_distance == "direct"
    assert ev.effect_type == "transmission_opportunity"
    assert ev.temporal_window == {"min": 4, "max": 8}
    assert ev.source == "static_calendar"   # default before engine wires providers
    print("PASS  EnvironmentalEvidence from direct signal (malaria/post_long_rains) — fields preserved")


def test_environmental_evidence_from_indirect_signal():
    records = _load_graph_records()
    anaemia = records["Iron deficiency anaemia"]
    sig = next(s for s in anaemia["environmental_signals"] if s["signal"] == "prolonged_drought")

    ev = EnvironmentalEvidence(
        signal=sig["signal"],
        causal_distance=sig["causal_distance"],
        effect_type=sig["effect_type"],
        effect_direction=sig["effect_direction"],
        strength=sig["strength"],
        confidence=sig["confidence"],
        temporal_window=sig.get("lag_weeks", {}),
    )

    assert ev.causal_distance == "indirect"
    assert ev.effect_type == "severity_modifier"
    assert ev.temporal_window == {"min": 4, "max": 16}
    assert ev.source == "static_calendar"   # default
    print("PASS  EnvironmentalEvidence from indirect signal (anaemia/prolonged_drought) — fields preserved")


def test_validator_warns_on_missing_causal_distance():
    meta = {
        "endemic_regions": ["coast"],
        "environmental_signals": [
            {
                "signal": "post_long_rains",
                "pathways": ["vector_borne"],
                "effect_type": "transmission_opportunity",
                "effect_direction": "up",
                "lag_weeks": {"min": 4, "max": 8},
                "strength": "moderate",
                "confidence": "moderate",
                # causal_distance intentionally omitted
                "evidence_type": "expert_estimate",
                "regions": ["coast"],
                "seasonal_basis": "typical_long_rains",
                "applicability": {"requires_exposure": [], "amplifiers": []},
            }
        ],
    }
    warnings = validate_environmental(meta, "TestCondition")
    matching = [w for w in warnings if "causal_distance" in w and "missing" in w]
    assert matching, f"Expected missing-causal_distance warning, got: {warnings}"
    print("PASS  validator warns when causal_distance is missing")


def test_validator_warns_on_invalid_causal_distance():
    meta = {
        "endemic_regions": ["coast"],
        "environmental_signals": [
            {
                "signal": "post_long_rains",
                "pathways": ["vector_borne"],
                "effect_type": "transmission_opportunity",
                "effect_direction": "up",
                "lag_weeks": {"min": 4, "max": 8},
                "strength": "moderate",
                "confidence": "moderate",
                "causal_distance": "medium",   # invalid value
                "evidence_type": "expert_estimate",
                "regions": ["coast"],
                "seasonal_basis": "typical_long_rains",
                "applicability": {"requires_exposure": [], "amplifiers": []},
            }
        ],
    }
    warnings = validate_environmental(meta, "TestCondition")
    matching = [w for w in warnings if "causal_distance" in w and "medium" in w]
    assert matching, f"Expected invalid-causal_distance warning, got: {warnings}"
    print("PASS  validator warns when causal_distance='medium' (invalid value)")


if __name__ == "__main__":
    test_malaria_post_long_rains_is_direct()
    test_anaemia_drought_is_indirect()
    test_environmental_evidence_from_direct_signal()
    test_environmental_evidence_from_indirect_signal()
    test_validator_warns_on_missing_causal_distance()
    test_validator_warns_on_invalid_causal_distance()
    print("\nAll 6 tests passed.")
