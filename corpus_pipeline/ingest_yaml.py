#!/usr/bin/env python3
"""
corpus_pipeline/ingest_yaml.py

Reads condition.yaml files and produces:
  corpus_pipeline/output/chunks.jsonl         -- same format as ingest.py
  corpus_pipeline/output/graph_entities.jsonl -- same format as ingest.py

Vocabulary loading and graph normalization are imported directly from ingest.py
so the normalization code path is byte-for-byte identical to the Markdown pipeline.
Only the data source changes: YAML structured fields instead of Markdown parsing.

Outputs go to corpus_pipeline/output/ -- never overwrites main pipeline artifacts.

Usage:
  python corpus_pipeline/ingest_yaml.py corpus/
  python corpus_pipeline/ingest_yaml.py corpus/malaria/condition.yaml
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from pydantic import ValidationError

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))

from corpus_pipeline.schema import load_card, ConditionCard

# Reuse vocabulary loading and graph normalization verbatim from ingest.py.
# This guarantees normalization is identical to the Markdown pipeline.
from ingest import (
    load_vocabulary,
    normalize_graph,
    build_graph_record,
    VOCAB_PATH,
    CONDITIONS_VOCAB_PATH,
)

OUTPUT_DIR = Path(__file__).parent / "output"

# ── Section mappings ──────────────────────────────────────────────────────────
# condition.yaml key → display heading used in chunk text (mirrors ingest.py SECTIONS)
SECTION_DISPLAY = {
    "cardinal_symptoms":      "Cardinal symptoms",
    "associated_symptoms":    "Associated symptoms and signs",
    "diagnostic_features":    "Diagnostic features",
    "predisposing_factors":   "Predisposing factors",
    "typical_presentation":   "Typical presentation",
    "differential_diagnoses": "Important differential diagnoses",
    "argues_against":         "Features that argue against this diagnosis",
    "red_flags":              "Red flags",
    "diagnostic_context":     "Diagnostic context",
}

# condition.yaml key → metadata section key (mirrors ingest.py SECTION_KEY)
SECTION_META_KEY = {
    "cardinal_symptoms":      "cardinal_symptoms",
    "associated_symptoms":    "associated_symptoms",
    "diagnostic_features":    "diagnostic_features",
    "predisposing_factors":   "predisposing_factors",
    "typical_presentation":   "typical_presentation",
    "differential_diagnoses": "differentials",  # ingest.py: "Important differential diagnoses" -> "differentials"
    "argues_against":         "against",        # ingest.py: "Features that argue against..." -> "against"
    "red_flags":              "red_flags",
    "diagnostic_context":     "diagnostic_context",
}

SECTION_ORDER = list(SECTION_DISPLAY.keys())  # fixed, mirrors ingest.py SECTIONS order


# ── Base metadata ─────────────────────────────────────────────────────────────

def _base_metadata(card: ConditionCard) -> dict:
    """Build the per-chunk metadata dict — mirrors ingest.py build_base_metadata."""
    return {
        "condition":             card.condition,
        "icd11":                 card.icd11,
        "icd10":                 card.icd10,
        "category":              card.category,
        "corpus_version":        card.corpus_version,
        "schema_version":        card.schema_version,
        "review_status":         card.review_status,
        "reviewed_by":           card.reviewed_by,   # None if empty (Pydantic coerces)
        "last_reviewed":         card.last_reviewed,
        "sources":               [s.model_dump() for s in card.sources],
        "endemic_regions":        list(card.endemic_regions),
        "environmental_signals":  [s.model_dump() for s in card.environmental_signals],
        "comorbidity_signals":    [s.model_dump() for s in card.comorbidity_signals],
    }


# ── Prose chunk building ──────────────────────────────────────────────────────

def _clean_prose(text: str) -> str:
    """Normalise section text to match ingest.py strip_markdown() output.
    YAML block scalars hard-wrap at ~80 chars; join within-paragraph lines
    with a space so chunk text matches single-line Markdown prose exactly."""
    paragraphs = re.split(r"\n\s*\n", text.strip())
    joined = []
    for para in paragraphs:
        line = " ".join(l.strip() for l in para.splitlines() if l.strip())
        if line:
            joined.append(line)
    return "\n\n".join(joined)


def build_chunks(card: ConditionCard) -> list[dict]:
    """
    One chunk per section in fixed order.
    Format: {"text": "<condition> — <heading>\\n\\n<prose>", "metadata": {...}}
    Exactly mirrors ingest.py split_sections() + process_file() output.
    """
    base = _base_metadata(card)
    chunks = []
    for yaml_key in SECTION_ORDER:
        prose = _clean_prose(getattr(card.sections, yaml_key))
        display = SECTION_DISPLAY[yaml_key]
        meta_key = SECTION_META_KEY[yaml_key]
        chunks.append({
            "text":     f"{card.condition} — {display}\n\n{prose}",
            "metadata": {**base, "section": meta_key},
        })
    return chunks


# ── Graph record building ─────────────────────────────────────────────────────

def _graph_as_raw(card: ConditionCard) -> dict:
    """Convert Pydantic GraphBlock to the raw list-of-strings dict normalize_graph() expects."""
    return {
        "cardinal_symptoms":   card.graph.cardinal_symptoms,
        "associated_symptoms": card.graph.associated_symptoms,
        "risk_factors":        card.graph.risk_factors,
        "differentials":       card.graph.differentials,
        "argues_against":      card.graph.argues_against,
        "red_flags":           card.graph.red_flags,
        "confirms":            card.graph.confirms,
    }


def _meta_for_graph(card: ConditionCard) -> dict:
    """Meta dict in the format build_graph_record() expects (mirrors raw frontmatter dict)."""
    return {
        "condition":             card.condition,
        "icd11":                 card.icd11,
        "category":              card.category,
        "corpus_version":        card.corpus_version,
        "schema_version":        card.schema_version,
        "review_status":         card.review_status,
        "reviewed_by":           card.reviewed_by,
        "last_reviewed":         card.last_reviewed,
        "sources":               [s.model_dump() for s in card.sources],
        "endemic_regions":        list(card.endemic_regions),
        "environmental_signals":  [s.model_dump() for s in card.environmental_signals],
        "comorbidity_signals":    [s.model_dump() for s in card.comorbidity_signals],
    }


def build_graph(card: ConditionCard, vocabularies: dict) -> tuple[dict, dict, list[str]]:
    """Return (record, stats, warnings) -- mirrors ingest.py process_graph_file()."""
    raw = _graph_as_raw(card)
    normalized, stats, warnings = normalize_graph(raw, vocabularies, card.condition)
    record = build_graph_record(_meta_for_graph(card), normalized)
    return record, stats, warnings


# ── Discovery ─────────────────────────────────────────────────────────────────

def _find_yaml_files(target: Path) -> list[Path]:
    if target.is_file() and target.name == "condition.yaml":
        return [target]
    return sorted(target.rglob("condition.yaml"))


# ── Integrity gate ────────────────────────────────────────────────────────────

def _integrity_check(incoming_yaml_files: list[Path], chunks_path: Path) -> None:
    """Fail fast if ingest would silently drop conditions that are currently indexed.

    Compares incoming source condition names against the existing chunks.jsonl.
    Validates by name, not count — a deleted condition plus a new one still equals
    the same count but is still a data-loss event.
    """
    if not chunks_path.exists():
        return  # no prior index — first run, nothing to protect

    indexed: set[str] = set()
    for line in chunks_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            indexed.add(json.loads(line)["metadata"]["condition"])

    incoming: set[str] = set()
    for yaml_path in incoming_yaml_files:
        try:
            card = load_card(yaml_path)
            incoming.add(card.condition)
        except Exception:
            pass  # load errors are reported in the main loop

    would_lose = indexed - incoming
    if would_lose:
        print("\n" + "=" * 60, file=sys.stderr)
        print("INTEGRITY ERROR — ingest aborted.", file=sys.stderr)
        print("The following conditions are indexed but missing from source:", file=sys.stderr)
        for name in sorted(would_lose):
            print(f"  - {name}", file=sys.stderr)
        print("\nLikely cause: wrong git branch. Verify corpus/ matches the", file=sys.stderr)
        print("currently deployed index before re-running ingest.", file=sys.stderr)
        print("=" * 60 + "\n", file=sys.stderr)
        sys.exit(1)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if len(sys.argv) < 2:
        print("Usage: python corpus_pipeline/ingest_yaml.py <corpus_dir_or_condition.yaml>")
        return 1

    target = Path(sys.argv[1])
    if not target.exists():
        print(f"Path not found: {target}", file=sys.stderr)
        return 1

    yaml_files = _find_yaml_files(target)
    if not yaml_files:
        print(f"No condition.yaml files found under {target}", file=sys.stderr)
        return 1

    OUTPUT_DIR.mkdir(exist_ok=True)
    chunks_path = OUTPUT_DIR / "chunks.jsonl"
    graph_path  = OUTPUT_DIR / "graph_entities.jsonl"

    # ── Integrity gate ───────────────────────────────────────────────────────
    # Prevent silent data loss: if the current indexed output contains conditions
    # not present in the incoming source files, hard-fail before writing anything.
    # This catches wrong-branch ingests (e.g. resetting a branch removes a card
    # but the previously indexed output still has it).
    _integrity_check(yaml_files, chunks_path)

    symptom_vocab    = load_vocabulary(VOCAB_PATH)
    conditions_vocab = load_vocabulary(CONDITIONS_VOCAB_PATH)
    vocabularies     = {"symptom": symptom_vocab, "condition": conditions_vocab}
    print(f"Symptom vocabulary:    {len(symptom_vocab)} terms")
    print(f"Conditions vocabulary: {len(conditions_vocab)} terms\n")

    # ── Prose chunks ────────────────────────────────────────────────────────
    print("-- Prose chunks ------------------------------------------")
    all_chunks: list[dict] = []
    failed: list[Path] = []

    for yaml_path in yaml_files:
        try:
            card = load_card(yaml_path)
        except ValidationError as exc:
            print(f"  ERROR {yaml_path.parent.name}: {exc.error_count()} validation error(s)")
            failed.append(yaml_path)
            continue
        except Exception as exc:
            print(f"  ERROR {yaml_path.parent.name}: {exc}")
            failed.append(yaml_path)
            continue

        chunks = build_chunks(card)
        all_chunks.extend(chunks)
        print(f"  {yaml_path.parent.name:30s}  {len(chunks)} chunks  ({card.condition})")

    print(f"\nTotal: {len(all_chunks)} chunks from {len(yaml_files) - len(failed)} files")
    if failed:
        print(f"Failed to load: {len(failed)} file(s)")

    with chunks_path.open("w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    print(f"Output: {chunks_path.relative_to(_ROOT)}")

    # ── Graph records ────────────────────────────────────────────────────────
    print("\n-- Graph records -----------------------------------------")
    all_graph: list[dict] = []
    all_warnings: list[str] = []
    total_stats = {"canonicalized": 0, "already_canonical": 0, "unknown": 0}

    for yaml_path in yaml_files:
        if yaml_path in failed:
            continue
        card = load_card(yaml_path)
        record, stats, warnings = build_graph(card, vocabularies)
        all_graph.append(record)
        all_warnings.extend(warnings)
        for k in total_stats:
            total_stats[k] += stats[k]
        term_count = sum(len(v) for v in record["graph"].values())
        print(f"  {yaml_path.parent.name:30s}  {term_count} terms  ({card.condition})")

    print(f"\nTotal: {len(all_graph)} graph records")
    print(f"Terms - already canonical: {total_stats['already_canonical']}  "
          f"canonicalized: {total_stats['canonicalized']}  "
          f"unknown: {total_stats['unknown']}")

    if all_warnings:
        print("\nGraph warnings:")
        for w in all_warnings:
            print(f"  {w}")
    else:
        print("Graph validation: no issues")

    with graph_path.open("w", encoding="utf-8") as f:
        for r in all_graph:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Output: {graph_path.relative_to(_ROOT)}")

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
