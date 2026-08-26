"""
Unknown terms report.

Reads graph_entities.jsonl, finds all terms where canonical is null,
deduplicates across conditions, classifies each term, and writes
unknown_terms_report.md for review before vocabulary expansion.

Classification rules (auto-applied, manual override expected):
  compound  — contains ' with ', ' and ', ' or ' joining clinical concepts
  threshold — contains a numeric threshold (≥, ≤, <, >, %, g/dL, mmol, etc.)
  simple    — single clinical concept, ready to add to vocabulary

Run from the cds/ directory:
    python report_unknowns.py
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GRAPH_JSONL = Path(__file__).parent / "graph_entities.jsonl"
REPORT_OUT  = Path(__file__).parent / "unknown_terms_report.md"

THRESHOLD_RE = re.compile(
    # Clinical units and thresholds — NOT case-insensitive to avoid fL matching "fl" in words
    r"[≥≤<>%]|g/dL|\bmmol\b|\bCFU\b|μg|\bmmHg\b|\bSpO\b|\bCD4\b|\d+\s*(mg|kg|cm)\b"
    r"|\bfL\b|\bpg\b|\bmL\b",
)

COMPOUND_MARKERS = [" with ", " and ", " or ", " in ", " without "]


def classify(term):
    if THRESHOLD_RE.search(term):
        return "threshold"
    if any(m in term.lower() for m in COMPOUND_MARKERS):
        return "compound"
    return "simple"


def main():
    if not GRAPH_JSONL.exists():
        raise SystemExit(f"Run ingest.py first — {GRAPH_JSONL.name} not found")

    # {key: {term: [conditions]}}
    unknowns = defaultdict(lambda: defaultdict(list))

    with GRAPH_JSONL.open(encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)
            condition = record["condition"]
            for key, terms in record.get("graph", {}).items():
                for t in terms:
                    if t["canonical"] is None:
                        unknowns[key][t["raw"]].append(condition)

    # Ordered by relationship key — differentials use conditions_vocabulary so shown separately
    KEY_ORDER = [
        "cardinal_symptoms",
        "associated_symptoms",
        "risk_factors",
        "red_flags",
        "confirms",
        "argues_against",
        "differentials",
    ]

    total = sum(len(terms) for terms in unknowns.values())
    simple_count    = sum(1 for terms in unknowns.values()
                          for t in terms if classify(t) == "simple")
    threshold_count = sum(1 for terms in unknowns.values()
                          for t in terms if classify(t) == "threshold")
    compound_count  = sum(1 for terms in unknowns.values()
                          for t in terms if classify(t) == "compound")

    lines = [
        "# Unknown Terms Report",
        "",
        "#review #vocabulary",
        "",
        f"> Auto-generated from `graph_entities.jsonl`. "
        f"Review each term before adding to [[symptom_vocabulary]].",
        "",
        "## Summary",
        "",
        f"| Class | Count | Action |",
        f"|-------|-------|--------|",
        f"| simple | {simple_count} | Add to vocabulary after naming review |",
        f"| threshold | {threshold_count} | Add as-is — numeric criteria are already precise |",
        f"| compound | {compound_count} | **Do not add** — flag for structured parsing in v2 |",
        f"| **Total** | **{total}** | |",
        "",
        "---",
        "",
    ]

    for key in KEY_ORDER:
        if key not in unknowns:
            continue

        terms_by_class = {"simple": [], "threshold": [], "compound": []}
        for term, conditions in sorted(unknowns[key].items()):
            cls = classify(term)
            terms_by_class[cls].append((term, conditions))

        lines.append(f"## `{key}`")
        lines.append("")

        for cls in ("simple", "threshold", "compound"):
            items = terms_by_class[cls]
            if not items:
                continue

            if cls == "simple":
                action = "Add to vocabulary"
            elif cls == "threshold":
                action = "Add as-is (numeric criterion)"
            else:
                action = "Do not add — compound finding, flag for v2"

            lines.append(f"### {cls.capitalize()} — {action}")
            lines.append("")
            lines.append("| Term | Appears in |")
            lines.append("|------|-----------|")
            for term, conditions in items:
                cond_list = ", ".join(sorted(set(conditions)))
                lines.append(f"| `{term}` | {cond_list} |")
            lines.append("")

    REPORT_OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report written: {REPORT_OUT.name}")
    print(f"  simple: {simple_count}  threshold: {threshold_count}  compound: {compound_count}  total: {total}")
    print(f"\nReview {REPORT_OUT.name}, then update symptom_vocabulary.md and rerun ingest.py")


if __name__ == "__main__":
    main()
