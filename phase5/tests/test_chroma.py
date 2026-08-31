"""
Step 4 — Chroma vector store verification.

Checks that the local Chroma collection has been loaded with:
- Expected minimum chunk count
- All conditions represented
- Required metadata fields on every chunk

Chroma is local — no API key required. Always runs (no integration mark).
"""

import pytest
from pathlib import Path

from helpers import ROOT, get_condition_names_from_graph

CHROMA_DIR      = ROOT / "chroma" / "db"
COLLECTION_NAME = "cds_conditions"
EXPECTED_MIN_CHUNKS = 89
REQUIRED_META_FIELDS = ["condition", "section", "review_status"]


@pytest.fixture(scope="module")
def collection():
    import chromadb
    assert CHROMA_DIR.exists(), \
        f"Chroma DB not found at {CHROMA_DIR} — run chroma/chroma_loader.py first"
    db = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return db.get_or_create_collection(COLLECTION_NAME)


def test_chroma_dir_exists():
    assert CHROMA_DIR.exists(), \
        f"Chroma DB directory missing: {CHROMA_DIR}"


def test_collection_min_chunk_count(collection):
    count = collection.count()
    assert count >= EXPECTED_MIN_CHUNKS, \
        f"Expected >= {EXPECTED_MIN_CHUNKS} chunks in Chroma, got {count}"


def test_all_conditions_represented(collection):
    expected = get_condition_names_from_graph()
    results = collection.get(include=["metadatas"])
    indexed = {m["condition"] for m in results["metadatas"]}
    missing = [c for c in expected if c not in indexed]
    assert not missing, f"Conditions not indexed in Chroma: {missing}"


def test_metadata_fields_on_chunks(collection):
    results = collection.get(limit=20, include=["metadatas"])
    for meta in results["metadatas"]:
        missing = [f for f in REQUIRED_META_FIELDS if f not in meta]
        assert not missing, \
            f"Chunk metadata missing fields {missing} for {meta.get('condition')}"


def test_no_empty_condition_in_metadata(collection):
    results = collection.get(include=["metadatas"])
    empty = [m for m in results["metadatas"] if not m.get("condition")]
    assert not empty, f"{len(empty)} chunks have empty condition in metadata"
