"""
Diagnostic RAG ingestion prototype.

Reads each condition card from symptoms_dictionary/, splits into section-level
chunks, extracts and normalizes graph declarations, and writes four output files:

  chunks.jsonl           — one JSON object per chunk (text + metadata)
  chunks_inspect.txt     — human-readable preview of prose chunks
  graph_entities.jsonl   — one JSON object per condition (normalized graph declarations)
  graph_inspect.txt      — human-readable preview of graph records

Run from the cds/ directory:
    python ingest.py
"""

import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    raise SystemExit("PyYAML required: pip install pyyaml")

CORPUS_DIR        = Path(__file__).parent / "symptoms_dictionary"
OUTPUT_JSONL      = Path(__file__).parent / "chunks.jsonl"
OUTPUT_INSPECT    = Path(__file__).parent / "chunks_inspect.txt"
GRAPH_OUTPUT_JSONL   = Path(__file__).parent / "graph_entities.jsonl"
GRAPH_OUTPUT_INSPECT = Path(__file__).parent / "graph_inspect.txt"
VOCAB_PATH       = CORPUS_DIR / "symptom_vocabulary.md"
CONDITIONS_VOCAB_PATH = CORPUS_DIR / "conditions_vocabulary.md"

SKIP_FILES = {"index.md", "glossary.md", "symptom_vocabulary.md", "conditions_vocabulary.md"}

# Valid keys in a card's graph: block
ALLOWED_GRAPH_KEYS = {
    "cardinal_symptoms",
    "associated_symptoms",
    "risk_factors",
    "differentials",
    "argues_against",
    "red_flags",
    "confirms",
}

# Maps each graph key to which vocabulary it should be checked against
# "symptom" → symptom_vocabulary.md, "condition" → conditions_vocabulary.md, None → pass-through
GRAPH_KEY_VOCAB = {
    "cardinal_symptoms":   "symptom",
    "associated_symptoms": "symptom",
    "risk_factors":        "symptom",
    "red_flags":           "symptom",
    "confirms":            "symptom",
    "argues_against":      "symptom",   # simple findings go here; compound pass-through silently
    "differentials":       "condition",
}

# Keys where unknowns trigger warnings (vs. silent pass-through for compound patterns)
VOCAB_CONTROLLED_KEYS = {
    "cardinal_symptoms",
    "associated_symptoms",
    "risk_factors",
    "red_flags",
    "confirms",
}

# Canonical section names in display order.
SECTIONS = [
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

SECTION_KEY = {
    "Cardinal symptoms":                          "cardinal_symptoms",
    "Associated symptoms and signs":              "associated_symptoms",
    "Diagnostic features":                        "diagnostic_features",
    "Predisposing factors":                       "predisposing_factors",
    "Typical presentation":                       "typical_presentation",
    "Important differential diagnoses":           "differentials",
    "Features that argue against this diagnosis": "against",
    "Red flags":                                  "red_flags",
    "Diagnostic context":                         "diagnostic_context",
}

_section_alts = "|".join(re.escape(s) for s in SECTIONS)
SECTION_RE = re.compile(
    r"\*\*(" + _section_alts + r")(?:\s*\([^)]*\))?\s*:\*\*",
    re.IGNORECASE,
)


# ─── Shared helpers ────────────────────────────────────────────────────────

def parse_frontmatter(text):
    """Return (metadata dict, body text). Raises if frontmatter is malformed."""
    if not text.startswith("---"):
        return {}, text
    close = text.index("---", 3)
    meta = yaml.safe_load(text[3:close].strip())
    body = text[close + 3:].strip()
    return meta, body


def build_base_metadata(meta):
    """Extract frontmatter fields into the metadata dict for each chunk."""
    def blank_to_none(v):
        return None if v == "" else v

    return {
        "condition":      meta.get("condition"),
        "icd11":          meta.get("icd11"),
        "category":       meta.get("category"),
        "corpus_version": meta.get("corpus_version"),
        "schema_version": meta.get("schema_version"),
        "review_status":  meta.get("review_status"),
        "reviewed_by":    blank_to_none(meta.get("reviewed_by", "")),
        "last_reviewed":  blank_to_none(meta.get("last_reviewed", "")),
        "sources":        meta.get("sources", []),
    }


# ─── Prose chunking pipeline (unchanged) ───────────────────────────────────

def strip_markdown(text):
    """Remove formatting characters; preserve all words and clinical qualifiers."""
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*",     r"\1", text)
    text = re.sub(r"_([^_]+)_",       r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_sections(body, condition):
    """
    Split body into (section_heading, clean_prose) pairs.
    The intro paragraph before the first section is discarded.
    """
    matches = list(SECTION_RE.finditer(body))
    if not matches:
        return []

    chunks = []
    for i, m in enumerate(matches):
        heading    = m.group(1)
        prose_start = m.end()
        prose_end   = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        prose = strip_markdown(body[prose_start:prose_end].strip())
        chunks.append((heading, f"{condition} — {heading}\n\n{prose}"))

    return chunks


def process_file(path):
    """Return list of prose chunk records for a condition card."""
    text = path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(text)

    condition = meta.get("condition", path.stem)
    base      = build_base_metadata(meta)

    body = re.sub(r"^#\s+.+\n", "", body, count=1).strip()

    records = []
    for heading, chunk_text in split_sections(body, condition):
        records.append({
            "text":     chunk_text,
            "metadata": {**base, "section": SECTION_KEY.get(heading, heading.lower().replace(" ", "_"))},
        })
    return records


def validate(records):
    """Warn about common ingestion problems before writing output."""
    issues = []
    for r in records:
        cond = r["metadata"]["condition"]
        sec  = r["metadata"]["section"]
        text = r["text"]

        if not text.startswith(cond):
            issues.append(f"WARN condition name not injected: {cond} / {sec}")
        if "**" in text or "##" in text:
            issues.append(f"WARN markdown syntax leaked into text: {cond} / {sec}")
        if len(text) < 80:
            issues.append(f"WARN suspiciously short chunk ({len(text)} chars): {cond} / {sec}")
        if r["metadata"].get("review_status") not in ("draft", "clinician_reviewed", "clinician_verified"):
            issues.append(f"WARN unexpected review_status: {cond}")

    return issues


# ─── Graph extraction pipeline ─────────────────────────────────────────────

def load_vocabulary(path):
    """
    Parse symptom_vocabulary.md tables into a reverse-lookup dict.

    Only processes tables where the second column header is 'Do Not Use'
    (skips the Investigations/Confirms table whose second column is 'Notes').

    Returns: {lowercase_term: canonical_display_term}
    """
    vocab = {}
    in_synonym_table = False

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()

        if stripped.startswith("| Canonical Term"):
            in_synonym_table = "Do Not Use" in stripped
            continue

        if re.match(r"^\|[-| ]+\|$", stripped):
            continue

        if stripped.startswith("|"):
            cols = [c.strip() for c in stripped.split("|")[1:-1]]
            if not cols or not cols[0]:
                continue
            canonical = cols[0]
            vocab[canonical.lower()] = canonical  # always map canonical → itself
            if in_synonym_table and len(cols) >= 2 and cols[1]:
                for synonym in cols[1].split(","):
                    s = synonym.strip()
                    if s:
                        vocab[s.lower()] = canonical

    return vocab


def extract_graph(meta):
    """Return raw graph block from frontmatter, or empty dict."""
    return meta.get("graph", {})


def normalize_graph(raw_graph, vocabularies, condition):
    """
    vocabularies — dict: {"symptom": vocab_dict, "condition": vocab_dict}
    """
    """
    Resolve raw graph terms to canonical concepts.

    Returns:
        normalized  — dict of {key: [{raw, canonical, concept_id}]}
        stats       — {"canonicalized": int, "already_canonical": int, "unknown": int}
        warnings    — list of warning strings
    """
    normalized = {}
    stats      = {"canonicalized": 0, "already_canonical": 0, "unknown": 0}
    warnings   = []

    for key, terms in raw_graph.items():
        if key not in ALLOWED_GRAPH_KEYS:
            warnings.append(
                f"WARN unknown graph key '{key}' in '{condition}' "
                f"— allowed: {sorted(ALLOWED_GRAPH_KEYS)}"
            )
            continue

        if not isinstance(terms, list):
            warnings.append(
                f"WARN graph key '{key}' in '{condition}' must be a list, "
                f"got {type(terms).__name__}"
            )
            continue

        vocab_type = GRAPH_KEY_VOCAB.get(key)
        vocabulary = vocabularies.get(vocab_type, {})

        normalized_terms = []
        for term in terms:
            term_str = str(term).strip()
            canonical = vocabulary.get(term_str.lower())

            if canonical is None:
                if key in VOCAB_CONTROLLED_KEYS:
                    warnings.append(
                        f"WARN unknown graph term — condition='{condition}' "
                        f"key='{key}' term='{term_str}'"
                    )
                    stats["unknown"] += 1
                # differentials and argues_against pass through without warning
                normalized_terms.append(
                    {"raw": term_str, "canonical": None, "concept_id": None}
                )
            elif canonical.lower() == term_str.lower():
                stats["already_canonical"] += 1
                normalized_terms.append(
                    {"raw": term_str, "canonical": canonical, "concept_id": None}
                )
            else:
                stats["canonicalized"] += 1
                normalized_terms.append(
                    {"raw": term_str, "canonical": canonical, "concept_id": None}
                )

        normalized[key] = normalized_terms

    return normalized, stats, warnings


def build_graph_record(meta, normalized_graph):
    """Assemble one JSON-serialisable graph record for a condition."""
    def blank_to_none(v):
        return None if v == "" else v

    return {
        "condition":      meta.get("condition"),
        "icd11":          meta.get("icd11"),
        "category":       meta.get("category"),
        "corpus_version": meta.get("corpus_version"),
        "schema_version": meta.get("schema_version"),
        "review_status":  meta.get("review_status"),
        "reviewed_by":    blank_to_none(meta.get("reviewed_by", "")),
        "last_reviewed":  blank_to_none(meta.get("last_reviewed", "")),
        "sources":        meta.get("sources", []),
        "graph":          normalized_graph,
    }


def process_graph_file(path, vocabularies):
    """
    Return (graph_record, stats, warnings) for one condition card.
    graph_record is None if the card has no graph: block.
    """
    text = path.read_text(encoding="utf-8")
    meta, _ = parse_frontmatter(text)

    raw_graph = extract_graph(meta)
    if not raw_graph:
        condition = meta.get("condition", path.stem)
        return None, {"canonicalized": 0, "already_canonical": 0, "unknown": 0}, [
            f"WARN no graph: block found in '{condition}'"
        ]

    condition = meta.get("condition", path.stem)
    normalized, stats, warnings = normalize_graph(raw_graph, vocabularies, condition)
    record = build_graph_record(meta, normalized)
    return record, stats, warnings


# ─── Main ──────────────────────────────────────────────────────────────────

def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    files = sorted(f for f in CORPUS_DIR.glob("*.md") if f.name not in SKIP_FILES)

    if not files:
        raise SystemExit(f"No condition files found in {CORPUS_DIR}")

    if not VOCAB_PATH.exists():
        raise SystemExit(f"Vocabulary file not found: {VOCAB_PATH}")
    if not CONDITIONS_VOCAB_PATH.exists():
        raise SystemExit(f"Conditions vocabulary not found: {CONDITIONS_VOCAB_PATH}")

    symptom_vocab    = load_vocabulary(VOCAB_PATH)
    conditions_vocab = load_vocabulary(CONDITIONS_VOCAB_PATH)
    vocabularies     = {"symptom": symptom_vocab, "condition": conditions_vocab}
    print(f"Symptom vocabulary:    {len(symptom_vocab)} terms")
    print(f"Conditions vocabulary: {len(conditions_vocab)} terms\n")

    # ── Prose chunks ────────────────────────────────────────────────────────
    print("-- Prose chunks ------------------------------------------")
    all_records = []
    for path in files:
        records = process_file(path)
        all_records.extend(records)
        print(f"  {path.name:45s}  {len(records)} chunks")

    print(f"\nTotal: {len(all_records)} chunks from {len(files)} files")

    issues = validate(all_records)
    if issues:
        print("\nChunk validation warnings:")
        for w in issues:
            print(f"  {w}")
    else:
        print("Chunk validation: no issues")

    with OUTPUT_JSONL.open("w", encoding="utf-8") as f:
        for r in all_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    with OUTPUT_INSPECT.open("w", encoding="utf-8") as f:
        for i, r in enumerate(all_records, 1):
            cond   = r["metadata"]["condition"]
            sec    = r["metadata"]["section"]
            text   = r["text"]
            sources = r["metadata"].get("sources", [])
            source_summary = "; ".join(
                f"{s.get('organization', '')} {s.get('year', '')}".strip()
                for s in sources
            )
            f.write(f"{'=' * 70}\n")
            f.write(f"Chunk {i:03d} | {cond} / {sec}\n")
            f.write(f"Length: {len(text)} chars | Sources: {source_summary or 'none'}\n\n")
            preview = text[:500]
            f.write(preview)
            if len(text) > 500:
                f.write(f"\n... [{len(text) - 500} chars truncated]")
            f.write("\n\n")

    print(f"Output:  {OUTPUT_JSONL.name}")
    print(f"Inspect: {OUTPUT_INSPECT.name}")

    # ── Graph records ────────────────────────────────────────────────────────
    print("\n-- Graph records -----------------------------------------")
    all_graph_records  = []
    all_graph_warnings = []
    total_stats = {"canonicalized": 0, "already_canonical": 0, "unknown": 0}

    for path in files:
        record, stats, warnings = process_graph_file(path, vocabularies)
        if record:
            all_graph_records.append(record)
            condition = record["condition"]
            term_count = sum(len(v) for v in record["graph"].values())
            print(f"  {path.name:45s}  {term_count} terms")
        all_graph_warnings.extend(warnings)
        for k in total_stats:
            total_stats[k] += stats[k]

    print(f"\nTotal: {len(all_graph_records)} graph records")
    print(f"Terms — already canonical: {total_stats['already_canonical']}  "
          f"canonicalized: {total_stats['canonicalized']}  "
          f"unknown: {total_stats['unknown']}")

    if all_graph_warnings:
        print("\nGraph warnings:")
        for w in all_graph_warnings:
            print(f"  {w}")
    else:
        print("Graph validation: no issues")

    with GRAPH_OUTPUT_JSONL.open("w", encoding="utf-8") as f:
        for r in all_graph_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    with GRAPH_OUTPUT_INSPECT.open("w", encoding="utf-8") as f:
        for r in all_graph_records:
            f.write(f"{'=' * 70}\n")
            f.write(f"{r['condition']}  |  ICD-11: {r['icd11']}  |  {r['review_status']}\n\n")
            for key, terms in r["graph"].items():
                f.write(f"  {key}:\n")
                for t in terms:
                    canonical_label = t["canonical"] or "⚠ unknown"
                    if t["canonical"] and t["canonical"] != t["raw"]:
                        f.write(f"    '{t['raw']}' → '{canonical_label}'\n")
                    else:
                        f.write(f"    '{canonical_label}'\n")
            f.write("\n")

    print(f"Output:  {GRAPH_OUTPUT_JSONL.name}")
    print(f"Inspect: {GRAPH_OUTPUT_INSPECT.name}")


if __name__ == "__main__":
    main()
