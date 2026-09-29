"""Offline tests for api/intake_extractor.py — no LLM, Neo4j or Chroma needed."""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.intake_extractor import (  # noqa: E402
    enriched_presentation,
    extract_intake,
    hmis_vitals_payload,
    normalize_transcript,
    nurse_notes,
    onset_from_duration,
    reconcile_red_flags,
)

DICTATION = (
    "Patient is a 34 year old male. Temperature 38.7 degrees Celsius taken orally, "
    "blood pressure 150 over 95, pulse 112 beats per minute, respiratory rate 24, "
    "oxygen saturation 94 percent on room air, weight 70 kilograms, height 172 centimetres, "
    "random blood sugar 7.8 millimoles per litre. Complains of fever, headache and joint pains "
    "for 3 days. Pain score 6 out of 10 in the lower back. No vomiting or diarrhea."
)


def values(text):
    return {f: r["value"] for f, r in extract_intake(text)["vitals"].items()}


# ── normalisation ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("spoken,expected", [
    ("temperature thirty eight point five", "temperature 38.5"),
    ("BP one twenty over eighty", "BP 120/80"),
    ("pulse one hundred and ten", "pulse 110"),
    ("sats ninety four percent", "sats 94%"),
    ("no one else is sick", "no one else is sick"),
    ("temperature 37 point 2", "temperature 37.2"),
    ("pain score six out of ten", "pain score 6 out of 10"),
])
def test_spoken_numbers_and_units_normalise(spoken, expected):
    assert normalize_transcript(spoken) == expected


# ── vitals ────────────────────────────────────────────────────────────────────

def test_full_dictation_extracts_every_vital():
    v = values(DICTATION)
    assert v == {
        "temperature": 38.7,
        "temperature_location": "oral",
        "systolic_bp": 150,
        "diastolic_bp": 95,
        "pulse": 112,
        "respiratory_rate": 24,
        "oxygen_saturation": 94,
        "weight": 70,
        "height": 172,
        "random_blood_sugar": 7.8,
        "blood_sugar_unit": "mmol/L",
        "pain_score": 6,
        "pain_location": "lower back",
    }


def test_every_value_points_at_its_evidence():
    ex = extract_intake(DICTATION)
    for reading in ex["vitals"].values():
        s, e = reading["span"]
        assert ex["normalized_transcript"][s:e].strip() == reading["evidence"]


def test_fahrenheit_is_converted():
    ex = extract_intake("temperature 101.3 F")
    t = ex["vitals"]["temperature"]
    assert t["value"] == 38.5 and t["unit"] == "°C" and "°F" in t["note"]


def test_unlabelled_fahrenheit_range_is_converted():
    assert values("temp 100.4")["temperature"] == 38


def test_pounds_and_feet_are_converted():
    v = values("weighs 154 pounds and height 5 feet 7 inches")
    assert v["weight"] == 69.9
    assert v["height"] == 170.2


def test_height_in_metres():
    assert values("height 1.65 m")["height"] == 165


def test_neighbouring_vital_is_not_borrowed():
    # "temperature normal" must not bind to the pulse reading that follows.
    v = values("temperature normal, pulse 88")
    assert "temperature" not in v and v["pulse"] == 88


def test_unit_only_fallbacks():
    v = values("she is 38.2°C with 130/85 mmHg and 96 bpm, 92% on room air, 64 kg")
    assert v["temperature"] == 38.2
    assert (v["systolic_bp"], v["diastolic_bp"]) == (130, 85)
    assert v["pulse"] == 96
    assert v["oxygen_saturation"] == 92
    assert v["weight"] == 64


def test_pain_ratio_is_not_mistaken_for_blood_pressure():
    v = values("pain 8/10 in the chest")
    assert v["pain_score"] == 8 and "systolic_bp" not in v
    assert v["pain_location"] == "chest"


def test_blood_sugar_unit_inferred_and_fasting_detected():
    ex = extract_intake("fasting blood sugar 126")
    fbs = ex["vitals"]["fasting_blood_sugar"]
    assert fbs["value"] == 126 and fbs["unit"] == "mg/dL" and "inferred" in fbs["note"]
    assert ex["vitals"]["blood_sugar_unit"]["value"] == "mg/dL"


def test_implausible_reading_is_dropped_with_warning():
    ex = extract_intake("pulse 400, BP 80/120")
    assert "pulse" not in ex["vitals"] and "systolic_bp" not in ex["vitals"]
    assert len(ex["warnings"]) == 2


def test_correction_keeps_last_value_and_warns():
    ex = extract_intake("temperature 38.5, sorry temperature 37.5")
    assert ex["vitals"]["temperature"]["value"] == 37.5
    assert any("more than one" in w for w in ex["warnings"])


def test_paediatric_measurements():
    v = values("MUAC 11.5 cm, head circumference 44 cm, weight 3200 grams")
    assert v["muac"] == 11.5 and v["head_circumference"] == 44 and v["weight"] == 3.2


# ── complaints and duration ───────────────────────────────────────────────────

def test_symptoms_map_to_vocabulary_with_negation():
    ex = extract_intake(DICTATION)
    present = {s["term"] for s in ex["symptoms"] if not s["negated"]}
    denied = {s["term"] for s in ex["symptoms"] if s["negated"]}
    assert {"fever", "headache"} <= present
    assert any("arthralgia" in t or "joint pain" in t for t in present)
    assert {"vomiting", "diarrhoea"} <= denied


def test_lay_terms_fold_onto_canonical():
    ex = extract_intake("she has shortness of breath and body aches")
    terms = {s["term"] for s in ex["symptoms"]}
    assert "dyspnoea" in terms and "myalgia" in terms


def test_negation_scope_ends_at_positive_trigger():
    ex = extract_intake("no cough but has fever")
    by_term = {s["term"]: s["negated"] for s in ex["symptoms"]}
    assert by_term["fever"] is False
    assert any(neg for term, neg in by_term.items() if "cough" in term)


@pytest.mark.parametrize("text,days", [
    ("fever for 3 days", 3),
    ("cough for two weeks", 14),
    ("vomiting since yesterday", 1),
    ("headache for the past 12 hours", 0.5),
    ("rash for a few days", 3),
])
def test_duration(text, days):
    assert extract_intake(text)["duration"]["days"] == days


def test_onset_from_duration():
    ex = extract_intake("fever for 3 days")
    onset = onset_from_duration(ex, datetime(2026, 9, 29, tzinfo=timezone.utc))
    assert onset == datetime(2026, 9, 26, tzinfo=timezone.utc)


# ── HMIS output ───────────────────────────────────────────────────────────────

def test_hmis_payload_uses_hmis_field_names():
    payload = hmis_vitals_payload(extract_intake(DICTATION))
    assert payload["blood_pressure"] == "150/95"
    assert payload["temperature_location"] == "oral"
    assert payload["oxygen_saturation"] == 94
    assert payload["symptoms"].startswith("Fever, headache")
    assert "for 3 days" in payload["symptoms"] and "Denies vomiting" in payload["symptoms"]


def test_enriched_presentation_restates_vitals():
    text = enriched_presentation(extract_intake(DICTATION))
    assert "Recorded vital signs: Blood pressure 150/95 mmHg" in text
    assert "Duration of illness: 3 days." in text


def test_nurse_notes_with_assessment():
    assessment = {
        "leading_candidate": "Malaria (unspecified)",
        "candidates": [
            {"diagnosis": "Malaria (unspecified)", "confidence_level": "moderate"},
            {"diagnosis": "Typhoid fever", "confidence_level": "low"},
        ],
        "red_flags": ["Check for — altered consciousness. Not documented in the presentation."],
    }
    notes = nurse_notes(extract_intake(DICTATION), assessment)
    assert "CDS leading consideration: Malaria (unspecified) (moderate confidence)." in notes
    assert "Differentials: Typhoid fever (low)." in notes
    assert "Red flags:" not in notes
    assert "1 red flag to rule out (see CDS panel)." in notes


def test_undocumented_red_flag_is_downgraded():
    flags, downgraded = reconcile_red_flags(
        [
            "Documented — Altered consciousness or coma (cerebral malaria). Requires urgent attention.",
            "Documented — Severe anaemia (haemoglobin less than 7 g/dL in children). Requires urgent attention.",
            "Documented — Convulsions. Requires urgent attention.",
            "Check for — Neck stiffness. Not documented in the presentation.",
        ],
        normalize_transcript(DICTATION + " She had convulsions this morning."),
    )
    assert downgraded == 2
    assert flags[0] == "Check for — Altered consciousness or coma (cerebral malaria). Not documented in the presentation."
    assert flags[1].startswith("Check for — Severe anaemia")
    assert flags[2].startswith("Documented — Convulsions")
    assert flags[3].startswith("Check for — Neck stiffness")


def test_negated_feature_does_not_support_a_documented_flag():
    flags, downgraded = reconcile_red_flags(
        ["Documented — Altered consciousness. Requires urgent attention."],
        "fever, fully alert, no altered consciousness",
    )
    assert downgraded == 1 and flags[0].startswith("Check for")


def test_empty_dictation_is_safe():
    ex = extract_intake("   ")
    assert ex["vitals"] == {} and ex["symptoms"] == [] and ex["duration"] is None
    assert hmis_vitals_payload(ex) == {}
