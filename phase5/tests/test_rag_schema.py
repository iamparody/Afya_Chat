"""
Step 5 — RAG pipeline output validation.

Runs rag.run() on a fixed presentation and validates the returned dict against:
- Required top-level keys
- leading_candidate membership in candidates[]
- Valid confidence_level on every candidate
- Required candidate fields
- Evidence-boundary rules (no confirmation language)

Requires live Cohere + Neo4j + Gemini. Mark: integration.
Run with:  pytest -m integration
Skip with: pytest -m "not integration"
"""

import json
import pytest

import rag
from prompts import OUTPUT_SCHEMA

pytestmark = pytest.mark.integration

VALID_CONFIDENCE    = {"high", "moderate", "low"}
REQUIRED_TOP_LEVEL  = ["leading_candidate", "candidates", "red_flags",
                        "relevant_comorbidities_or_context"]
REQUIRED_CANDIDATE  = ["diagnosis", "confidence_level", "why_considered",
                        "supporting_features", "arguing_against", "missing_information"]

# Fixed presentation — deterministic enough for schema checks
PRESENTATION = "35M, 5 days fever, chills, headache, weakness. Came from Kisumu 1 week ago."


@pytest.fixture(scope="module")
def result():
    return rag.run(PRESENTATION)


def test_output_is_dict(result):
    assert isinstance(result, dict), "rag.run() did not return a dict"


def test_top_level_keys_present(result):
    missing = [k for k in REQUIRED_TOP_LEVEL if k not in result]
    assert not missing, f"Output missing top-level keys: {missing}"


def test_leading_candidate_not_empty(result):
    assert result.get("leading_candidate"), "leading_candidate is empty"


def test_candidates_is_nonempty_list(result):
    assert isinstance(result.get("candidates"), list), "candidates is not a list"
    assert len(result["candidates"]) > 0, "candidates list is empty"


def test_leading_candidate_in_candidates(result):
    names = {c["diagnosis"] for c in result["candidates"]}
    assert result["leading_candidate"] in names, \
        f"leading_candidate '{result['leading_candidate']}' not found in candidates[]"


def test_candidate_fields_present(result):
    for c in result["candidates"]:
        missing = [f for f in REQUIRED_CANDIDATE if f not in c]
        assert not missing, \
            f"Candidate '{c.get('diagnosis')}' missing fields: {missing}"


def test_confidence_level_valid(result):
    for c in result["candidates"]:
        assert c["confidence_level"] in VALID_CONFIDENCE, \
            f"Invalid confidence_level '{c['confidence_level']}' for '{c['diagnosis']}'"


def test_red_flags_is_list(result):
    assert isinstance(result.get("red_flags"), list), "red_flags is not a list"


def test_arguing_against_is_list(result):
    for c in result["candidates"]:
        assert isinstance(c.get("arguing_against"), list), \
            f"arguing_against is not a list for '{c.get('diagnosis')}'"


def test_missing_information_is_list(result):
    for c in result["candidates"]:
        assert isinstance(c.get("missing_information"), list), \
            f"missing_information is not a list for '{c.get('diagnosis')}'"


def test_no_confirmation_language(result):
    flat = json.dumps(result).lower()
    prohibited = ["diagnosis confirmed", "confirmed diagnosis", "test confirmed"]
    hits = [p for p in prohibited if p in flat]
    assert not hits, f"Prohibited confirmation language found: {hits}"


def test_jsonschema_passes(result):
    import jsonschema
    try:
        jsonschema.validate(result, OUTPUT_SCHEMA)
    except jsonschema.ValidationError as e:
        pytest.fail(f"Output failed jsonschema validation: {e.message}")
