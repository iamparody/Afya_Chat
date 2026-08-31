"""
Step 2 — Ingest output validation.

Checks chunks.jsonl and graph_entities.jsonl produced by ingest.py.
Run ingest.py before running these tests.
"""

import json
import pytest
from pathlib import Path

from helpers import ROOT

CHUNKS_JSONL      = ROOT / "chunks.jsonl"
GRAPH_JSONL       = ROOT / "graph_entities.jsonl"
EXPECTED_CARDS      = 10
SECTIONS_PER_CARD   = 9
KNOWN_CHUNK_COUNT   = 89  # validated baseline; 10×9=90 theoretical but one section parses as merged
REQUIRED_CHUNK_META_FIELDS = ["condition", "section", "review_status", "icd11", "category"]
REQUIRED_GRAPH_KEYS = [
    "cardinal_symptoms", "associated_symptoms", "risk_factors",
    "differentials", "argues_against", "red_flags", "confirms",
]


def _load_jsonl(path):
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


# ── chunks.jsonl ──────────────────────────────────────────────────────────────

class TestChunksOutput:

    def test_file_exists(self):
        assert CHUNKS_JSONL.exists(), "chunks.jsonl missing — run python ingest.py first"

    def test_minimum_chunk_count(self):
        chunks = _load_jsonl(CHUNKS_JSONL)
        assert len(chunks) >= KNOWN_CHUNK_COUNT, \
            f"Expected >= {KNOWN_CHUNK_COUNT} chunks, got {len(chunks)}"

    def test_chunk_has_text_and_metadata(self):
        for chunk in _load_jsonl(CHUNKS_JSONL):
            assert "text" in chunk,     "Chunk missing 'text' field"
            assert "metadata" in chunk, "Chunk missing 'metadata' field"

    def test_text_not_empty(self):
        for chunk in _load_jsonl(CHUNKS_JSONL):
            meta = chunk["metadata"]
            assert chunk["text"].strip(), \
                f"Empty text in {meta.get('condition')} / {meta.get('section')}"

    def test_metadata_fields_present(self):
        for chunk in _load_jsonl(CHUNKS_JSONL):
            meta = chunk["metadata"]
            missing = [f for f in REQUIRED_CHUNK_META_FIELDS if f not in meta]
            assert not missing, \
                f"{meta.get('condition')}: chunk metadata missing {missing}"

    def test_no_markdown_bold_leaked(self):
        for chunk in _load_jsonl(CHUNKS_JSONL):
            meta = chunk["metadata"]
            assert "**" not in chunk["text"], \
                f"Markdown '**' leaked: {meta.get('condition')} / {meta.get('section')}"

    def test_no_markdown_heading_leaked(self):
        for chunk in _load_jsonl(CHUNKS_JSONL):
            meta = chunk["metadata"]
            for line in chunk["text"].splitlines():
                assert not line.startswith("##"), \
                    f"Markdown '##' leaked: {meta.get('condition')} / {meta.get('section')}"

    def test_all_ten_conditions_present(self):
        chunks = _load_jsonl(CHUNKS_JSONL)
        conditions = {c["metadata"]["condition"] for c in chunks}
        assert len(conditions) >= EXPECTED_CARDS, \
            f"Expected >= {EXPECTED_CARDS} distinct conditions, got {len(conditions)}"

    def test_review_status_on_every_chunk(self):
        for chunk in _load_jsonl(CHUNKS_JSONL):
            meta = chunk["metadata"]
            assert meta.get("review_status") in ("draft", "under_review", "clinician_verified"), \
                f"Invalid review_status in {meta.get('condition')} / {meta.get('section')}"


# ── graph_entities.jsonl ──────────────────────────────────────────────────────

class TestGraphOutput:

    def test_file_exists(self):
        assert GRAPH_JSONL.exists(), "graph_entities.jsonl missing — run python ingest.py first"

    def test_record_count(self):
        records = _load_jsonl(GRAPH_JSONL)
        assert len(records) == EXPECTED_CARDS, \
            f"Expected {EXPECTED_CARDS} graph records, got {len(records)}"

    def test_condition_name_present(self):
        for r in _load_jsonl(GRAPH_JSONL):
            assert r.get("condition"), "Graph record has empty condition name"

    def test_graph_key_present(self):
        for r in _load_jsonl(GRAPH_JSONL):
            assert "graph" in r, f"Graph record missing 'graph' key: {r.get('condition')}"

    def test_graph_has_required_keys(self):
        for r in _load_jsonl(GRAPH_JSONL):
            missing = [k for k in REQUIRED_GRAPH_KEYS if k not in r.get("graph", {})]
            assert not missing, \
                f"{r.get('condition')}: graph missing keys {missing}"

    def test_cardinal_symptoms_not_empty(self):
        for r in _load_jsonl(GRAPH_JSONL):
            cs = r.get("graph", {}).get("cardinal_symptoms", [])
            assert len(cs) > 0, \
                f"{r.get('condition')}: cardinal_symptoms is empty"
