"""
BM25 sparse index over chunks.jsonl.

Loaded lazily on first call and cached for the process lifetime.
Tokenisation: lowercase whitespace split — matches the clinical text granularity.
"""

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
CHUNKS_PATH = ROOT / "chunks.jsonl"

_bm25 = None
_chunks = None


def get_bm25_index():
    """Return (BM25Okapi, chunks_list). Builds on first call, cached thereafter."""
    global _bm25, _chunks
    if _bm25 is None:
        from rank_bm25 import BM25Okapi

        chunks = []
        with open(CHUNKS_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    chunks.append(json.loads(line))

        corpus = [chunk["text"].lower().split() for chunk in chunks]
        # chunks.jsonl structure: {"text": "...", "metadata": {"condition": ..., ...}}
        _bm25 = BM25Okapi(corpus)
        _chunks = chunks

    return _bm25, _chunks
