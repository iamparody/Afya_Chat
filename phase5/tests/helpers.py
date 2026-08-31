"""Shared constants and helpers for the CDS test suite."""

import json
import sys
from pathlib import Path

ROOT       = Path(__file__).parent.parent.parent  # cds/
CORPUS_DIR = ROOT / "symptoms_dictionary"
SKIP_FILES = {"index.md", "glossary.md", "symptom_vocabulary.md", "conditions_vocabulary.md"}

# Make cds/ and phase5/ importable
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "phase5"))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")


def get_condition_cards():
    return sorted(f for f in CORPUS_DIR.glob("*.md") if f.name not in SKIP_FILES)


def get_condition_names_from_graph():
    jsonl = ROOT / "graph_entities.jsonl"
    if not jsonl.exists():
        return []
    return [
        json.loads(line)["condition"]
        for line in jsonl.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
