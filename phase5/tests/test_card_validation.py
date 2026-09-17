"""
Step 1 — Card validation.

Delegates to corpus_pipeline/validator.py — the authoritative schema gate.
Every condition.yaml in corpus/ must pass with 0 ERRORs.

Run from cds/ root:
  pytest phase5/tests/test_card_validation.py
"""

import pytest

from helpers import get_condition_cards, ROOT
from corpus_pipeline.validator import validate_card, load_vocabularies, load_source_registry
from corpus_pipeline.schema import load_card

_vocab    = load_vocabularies()
_registry = load_source_registry()

REQUIRED_GRAPH_KEYS = [
    "cardinal_symptoms",
    "associated_symptoms",
    "risk_factors",
    "differentials",
    "argues_against",
    "red_flags",
    "confirms",
]


@pytest.mark.parametrize("card_path", get_condition_cards(), ids=lambda p: p.parent.name)
class TestCardValidation:

    def test_passes_validator_with_no_errors(self, card_path):
        """validator.py must report 0 ERRORs — this is the hard gate before ingest."""
        _, issues = validate_card(card_path, _vocab, _registry)
        errors = [str(i) for i in issues if i.level == "ERROR"]
        assert not errors, "\n".join(errors)

    def test_icd_verified(self, card_path):
        """icd_verified: true required — set by scripts/verify_icd.py (WHO API)."""
        card = load_card(card_path)
        assert card.icd_verified, \
            f"{card_path.parent.name}: icd_verified is false — run scripts/verify_icd.py"

    def test_cardinal_symptoms_not_empty(self, card_path):
        """Cardinal symptoms must always be present — the primary retrieval signal."""
        card = load_card(card_path)
        assert card.graph.cardinal_symptoms, \
            f"{card_path.parent.name}: graph.cardinal_symptoms is empty"

    def test_all_nine_sections_non_empty(self, card_path):
        """All 9 clinical sections must have content — enforced by ClinicalSections model."""
        card = load_card(card_path)
        for key in [
            "cardinal_symptoms", "associated_symptoms", "diagnostic_features",
            "predisposing_factors", "typical_presentation", "differential_diagnoses",
            "argues_against", "red_flags", "diagnostic_context",
        ]:
            assert getattr(card.sections, key, "").strip(), \
                f"{card_path.parent.name}: sections.{key} is empty"
