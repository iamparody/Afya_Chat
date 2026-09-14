#!/usr/bin/env python3
"""
corpus_pipeline/markdown_gen.py

Pure template rendering: condition.yaml -> generated.md

No inference, enrichment, or logic. Structured data to presentation only.
Output mirrors the hand-authored symptoms_dictionary/*.md format so that
diff.py can compare section-by-section.

Known omission by design:
  The hand-authored .md files contain a free-text introductory paragraph
  after the H1 heading that is NOT stored in condition.yaml (no 'introduction'
  field in the schema). generated.md omits it. diff.py will flag this gap.
  Resolution: add an 'introduction:' field to condition.yaml schema if full
  content equivalence is required.

Outputs go to corpus_pipeline/output/<condition_dir>/generated.md

Usage:
  python corpus_pipeline/markdown_gen.py corpus/
  python corpus_pipeline/markdown_gen.py corpus/malaria/condition.yaml
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml
from pydantic import ValidationError

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))

from corpus_pipeline.schema import load_card, ConditionCard, EnvironmentalSignal, Source

OUTPUT_DIR = Path(__file__).parent / "output"

# Section display headers — must match ingest.py SECTIONS exactly
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

SECTION_ORDER = list(SECTION_DISPLAY.keys())


# ── Frontmatter rendering ─────────────────────────────────────────────────────

def _render_source(s: Source) -> dict:
    return {
        "organization": s.organization,
        "title": s.title,
        "year": str(s.year) if s.year else "",
    }


def _render_signal(sig: EnvironmentalSignal) -> dict:
    """Render one environmental signal as a plain dict for yaml.dump()."""
    return {
        "signal": sig.signal,
        "pathways": sig.pathways,
        "effect_type": sig.effect_type,
        "effect_direction": sig.effect_direction,
        "lag_weeks": {"min": sig.lag_weeks.min, "max": sig.lag_weeks.max},
        "strength": sig.strength,
        "confidence": sig.confidence,
        "causal_distance": sig.causal_distance,
        "evidence_type": sig.evidence_type,
        "regions": sig.regions,
        "seasonal_basis": sig.seasonal_basis,
        "applicability": {
            "requires_exposure": sig.applicability.requires_exposure,
            "amplifiers": sig.applicability.amplifiers,
        },
    }


def _graph_dict(card: ConditionCard) -> dict:
    """Graph block as plain dict — field order matches ingest.py ALLOWED_GRAPH_KEYS."""
    return {
        "cardinal_symptoms":   card.graph.cardinal_symptoms,
        "associated_symptoms": card.graph.associated_symptoms,
        "risk_factors":        card.graph.risk_factors,
        "differentials":       card.graph.differentials,
        "argues_against":      card.graph.argues_against,
        "red_flags":           card.graph.red_flags,
        "confirms":            card.graph.confirms,
    }


def render_frontmatter(card: ConditionCard) -> str:
    """
    Render YAML frontmatter block.
    reviewed_by and last_reviewed render as empty string (matching hand-authored format).
    yaml.dump() produces block-style lists; this is a known cosmetic difference from
    the inline-list format in hand-authored cards — diff.py handles this semantically.
    """
    data = {
        "condition":      card.condition,
        "icd11":          card.icd11,
        "icd10":          card.icd10,
        "category":       card.category,
        "corpus_version": card.corpus_version,
        "schema_version": card.schema_version,
        "review_status":  card.review_status,
        "reviewed_by":    card.reviewed_by if card.reviewed_by is not None else "",
        "last_reviewed":  card.last_reviewed if card.last_reviewed is not None else "",
        "sources":        [_render_source(s) for s in card.sources],
        "endemic_regions":       list(card.endemic_regions),
        "environmental_signals": [_render_signal(s) for s in card.environmental_signals],
        "graph":                 _graph_dict(card),
    }
    return yaml.dump(
        data,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    )


# ── Section rendering ─────────────────────────────────────────────────────────

def render_section(heading: str, prose: str) -> str:
    """Render one clinical section — bold header followed by prose paragraph."""
    return f"**{heading}:** {prose.strip()}\n"


# ── Full document ─────────────────────────────────────────────────────────────

def render_card(card: ConditionCard) -> str:
    """Render the complete Markdown document for a card."""
    parts: list[str] = []

    # Frontmatter
    parts.append("---\n")
    parts.append(render_frontmatter(card))
    parts.append("---\n")
    parts.append("\n")

    # H1 — use condition name as written (matches hand-authored style)
    parts.append(f"# {card.condition}\n")
    parts.append("\n")

    # Note: intro paragraph omitted — not stored in condition.yaml
    # diff.py will flag this as expected missing content

    # 9 clinical sections
    for yaml_key in SECTION_ORDER:
        heading = SECTION_DISPLAY[yaml_key]
        prose = getattr(card.sections, yaml_key, "")
        parts.append(render_section(heading, prose))
        parts.append("\n")

    return "".join(parts)


# ── Discovery ─────────────────────────────────────────────────────────────────

def _find_yaml_files(target: Path) -> list[Path]:
    if target.is_file() and target.name == "condition.yaml":
        return [target]
    return sorted(target.rglob("condition.yaml"))


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if len(sys.argv) < 2:
        print("Usage: python corpus_pipeline/markdown_gen.py <corpus_dir_or_condition.yaml>")
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
    failed = 0

    for yaml_path in yaml_files:
        try:
            card = load_card(yaml_path)
        except ValidationError as exc:
            print(f"  ERROR {yaml_path.parent.name}: {exc.error_count()} validation error(s)")
            failed += 1
            continue
        except Exception as exc:
            print(f"  ERROR {yaml_path.parent.name}: {exc}")
            failed += 1
            continue

        md_text = render_card(card)

        out_dir = OUTPUT_DIR / yaml_path.parent.name
        out_dir.mkdir(exist_ok=True)
        out_path = out_dir / "generated.md"
        out_path.write_text(md_text, encoding="utf-8")

        print(f"  {yaml_path.parent.name:30s}  -> {out_path.relative_to(_ROOT)}")

    total = len(yaml_files)
    print(f"\nGenerated: {total - failed}/{total} cards")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
