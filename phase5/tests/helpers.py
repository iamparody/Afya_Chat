"""Shared constants and helpers for the CDS test suite."""

import json
import sys
from pathlib import Path

ROOT       = Path(__file__).parent.parent.parent  # cds/
CORPUS_DIR = ROOT / "corpus"
INGEST_OUT = ROOT / "corpus_pipeline" / "output"

# Make cds/ and phase5/ importable
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "phase5"))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")


def get_condition_cards():
    """Return all condition.yaml paths in corpus/, sorted."""
    return sorted(CORPUS_DIR.rglob("condition.yaml"))


def get_condition_names_from_graph():
    """Return condition names from corpus_pipeline/output/graph_entities.jsonl."""
    jsonl = INGEST_OUT / "graph_entities.jsonl"
    if not jsonl.exists():
        return []
    return [
        json.loads(line)["condition"]
        for line in jsonl.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
