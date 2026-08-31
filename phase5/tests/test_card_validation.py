"""
Step 1 — Card validation.

Every condition card must have:
- All required frontmatter keys
- Valid review_status
- All 9 sections in the body (exact header strings the parser depends on)
- graph: block with all 7 required keys, each a non-empty list
"""

import pytest
import yaml

from helpers import get_condition_cards

REQUIRED_FRONTMATTER_KEYS = ["condition", "icd11", "category", "review_status", "sources", "graph"]
VALID_REVIEW_STATUSES     = {"draft", "under_review", "clinician_verified"}

REQUIRED_SECTIONS = [
    "Cardinal symptoms",
    "Associated symptoms and signs",
    "Diagnostic features",
    "Predisposing factors",
    "Typical presentation",
    "Important differential diagnoses",
    "Features that argue against this diagnosis",
    "Red flags",
    "Diagnostic context",
]

REQUIRED_GRAPH_KEYS = [
    "cardinal_symptoms",
    "associated_symptoms",
    "risk_factors",
    "differentials",
    "argues_against",
    "red_flags",
    "confirms",
]


def _parse(path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}, text
    close = text.index("---", 3)
    meta = yaml.safe_load(text[3:close].strip())
    body = text[close + 3:].strip()
    return meta, body


@pytest.mark.parametrize("card", get_condition_cards(), ids=lambda p: p.stem)
class TestCardValidation:

    def test_frontmatter_keys_present(self, card):
        meta, _ = _parse(card)
        missing = [k for k in REQUIRED_FRONTMATTER_KEYS if k not in meta]
        assert not missing, f"{card.name}: missing frontmatter keys {missing}"

    def test_condition_name_not_empty(self, card):
        meta, _ = _parse(card)
        assert meta.get("condition"), f"{card.name}: condition name is empty"

    def test_icd11_not_empty(self, card):
        meta, _ = _parse(card)
        assert meta.get("icd11"), f"{card.name}: icd11 code is empty"

    def test_review_status_valid(self, card):
        meta, _ = _parse(card)
        assert meta.get("review_status") in VALID_REVIEW_STATUSES, \
            f"{card.name}: invalid review_status '{meta.get('review_status')}'"

    def test_all_nine_sections_present(self, card):
        _, body = _parse(card)
        body_lower = body.lower()
        missing = [s for s in REQUIRED_SECTIONS if s.lower() not in body_lower]
        assert not missing, f"{card.name}: missing sections {missing}"

    def test_graph_block_exists(self, card):
        meta, _ = _parse(card)
        assert "graph" in meta, f"{card.name}: no graph: block in frontmatter"

    def test_graph_has_all_keys(self, card):
        meta, _ = _parse(card)
        graph = meta.get("graph", {})
        missing = [k for k in REQUIRED_GRAPH_KEYS if k not in graph]
        assert not missing, f"{card.name}: graph: missing keys {missing}"

    def test_graph_keys_are_nonempty_lists(self, card):
        meta, _ = _parse(card)
        graph = meta.get("graph", {})
        for key in REQUIRED_GRAPH_KEYS:
            if key not in graph:
                continue  # caught by test_graph_has_all_keys
            assert isinstance(graph[key], list), \
                f"{card.name}: graph['{key}'] is not a list"
            assert len(graph[key]) > 0, \
                f"{card.name}: graph['{key}'] is an empty list"
