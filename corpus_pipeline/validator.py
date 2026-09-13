#!/usr/bin/env python3
"""
corpus_pipeline/validator.py

Pre-review automated checks for condition.yaml cards.
Runs checks beyond Pydantic: vocabulary coverage, ICD format, compound graph terms,
signal region coherence, source completeness, cross-card differential consistency.

Usage:
  python corpus_pipeline/validator.py corpus/
  python corpus_pipeline/validator.py corpus/malaria/condition.yaml
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))
from corpus_pipeline.schema import load_card, ConditionCard


# ── Issue ─────────────────────────────────────────────────────────────────────

@dataclass
class Issue:
    level: str    # "ERROR" | "WARNING"
    location: str
    message: str

    def __str__(self) -> str:
        return f"  {self.level} [{self.location}] {self.message}"


# ── Vocabulary loading ────────────────────────────────────────────────────────

def _parse_vocab_table(md_text: str) -> set[str]:
    """Return canonical terms (first column) from all Markdown pipe tables in md_text."""
    terms: set[str] = set()
    for line in md_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        parts = [p.strip() for p in stripped.split("|") if p.strip()]
        if not parts:
            continue
        first = parts[0]
        if re.match(r"^-+$", first) or first.lower() == "canonical term":
            continue
        terms.add(first.lower())
    return terms


def load_vocabularies() -> dict[str, set[str]]:
    """Load symptom_vocabulary.md and conditions_vocabulary.md."""
    vocab_dir = _ROOT / "symptoms_dictionary"
    return {
        "symptom_terms": _parse_vocab_table(
            (vocab_dir / "symptom_vocabulary.md").read_text(encoding="utf-8")
        ),
        "condition_terms": _parse_vocab_table(
            (vocab_dir / "conditions_vocabulary.md").read_text(encoding="utf-8")
        ),
    }


# ── ICD format ────────────────────────────────────────────────────────────────

_ICD11_RE = re.compile(r"^[A-Z0-9]{2,8}(\.[A-Z0-9]+)?$")
_ICD10_RE = re.compile(r"^[A-Z]\d{2,4}(\.\d+)?$")


def _check_icd(card: ConditionCard) -> list[Issue]:
    issues: list[Issue] = []
    if not _ICD11_RE.match(card.icd11):
        issues.append(Issue(
            "ERROR", "icd11",
            f"'{card.icd11}' does not match ICD-11 format - verify at icd.who.int",
        ))
    if not _ICD10_RE.match(card.icd10):
        issues.append(Issue(
            "ERROR", "icd10",
            f"'{card.icd10}' does not match ICD-10 format (e.g. J18, K27.9)",
        ))
    return issues


# ── Corpus version format ─────────────────────────────────────────────────────

_CORPUS_VERSION_RE = re.compile(r"^\d+\.\d+$")


def _check_corpus_version(card: ConditionCard) -> list[Issue]:
    if not _CORPUS_VERSION_RE.match(card.corpus_version):
        return [Issue(
            "ERROR", "corpus_version",
            f"'{card.corpus_version}' - expected format X.Y (e.g. 1.0, 1.3)",
        )]
    return []


# ── Sources completeness ──────────────────────────────────────────────────────

def _check_sources(card: ConditionCard) -> list[Issue]:
    if not card.sources:
        return [Issue("WARNING", "sources", "No sources listed - add at least one source")]
    if all(not s.title.strip() for s in card.sources):
        return [Issue("WARNING", "sources", "All sources have empty titles - fill in source documentation")]
    return []


# ── Environmental signal region coherence ─────────────────────────────────────

def _check_signal_regions(card: ConditionCard) -> list[Issue]:
    """Signal regions must be a subset of the card's endemic_regions.
    Cards with 'nationwide' are valid for all signal regions."""
    issues: list[Issue] = []
    endemic = set(card.endemic_regions)
    if "nationwide" in endemic:
        return []
    for i, sig in enumerate(card.environmental_signals):
        for r in sig.regions:
            if r not in endemic:
                issues.append(Issue(
                    "WARNING", f"environmental_signals[{i}].regions",
                    f"Region '{r}' not in card endemic_regions {sorted(endemic)} - "
                    f"signal applies to a region the condition is not listed for",
                ))
    return issues


# ── Graph term vocabulary checks ──────────────────────────────────────────────

_GRAPH_VOCAB: dict[str, str] = {
    "cardinal_symptoms":   "symptom_terms",
    "associated_symptoms": "symptom_terms",
    "risk_factors":        "symptom_terms",
    "differentials":       "condition_terms",
    "argues_against":      "symptom_terms",
    "red_flags":           "symptom_terms",
    "confirms":            "symptom_terms",
}

# Conjunctions that turn a graph term into a compound phrase.
# Only checked for terms NOT already in the vocabulary (vocab terms may legitimately contain these).
_CONJUNCTION_RE = re.compile(r"\b(and|or|without|with)\b", re.IGNORECASE)
_WORD_COUNT_WARN = 6  # flag unknown terms >= this many words


def _check_graph_terms(card: ConditionCard, vocab: dict[str, set[str]]) -> list[Issue]:
    issues: list[Issue] = []

    for field_name, vocab_key in _GRAPH_VOCAB.items():
        terms: list[str] = getattr(card.graph, field_name, [])
        known = vocab[vocab_key]
        seen: set[str] = set()

        for term in terms:
            key = term.lower().strip()

            if key in seen:
                issues.append(Issue(
                    "WARNING", f"graph.{field_name}",
                    f"Duplicate term: '{term}'",
                ))
                continue
            seen.add(key)

            if key in known:
                continue

            # Term not in vocabulary - annotate with hints
            hints: list[str] = []
            if _CONJUNCTION_RE.search(term):
                hints.append("compound - split into atomic terms")
            word_count = len(term.split())
            if word_count >= _WORD_COUNT_WARN:
                hints.append(f"{word_count} words - shorten to <=5")

            vocab_name = (
                "conditions_vocabulary" if vocab_key == "condition_terms"
                else "symptom_vocabulary"
            )
            hint_str = f" [{'; '.join(hints)}]" if hints else ""
            issues.append(Issue(
                "WARNING", f"graph.{field_name}",
                f"'{term}' - not in {vocab_name}.md{hint_str}; add before use",
            ))

    return issues


# ── Self-reference check ──────────────────────────────────────────────────────

def _check_self_reference(card: ConditionCard) -> list[Issue]:
    own = card.condition.lower()
    for diff in card.graph.differentials:
        if diff.lower() == own:
            return [Issue(
                "WARNING", "graph.differentials",
                f"Card lists its own condition ('{card.condition}') as a differential - remove",
            )]
    return []


# ── Per-card orchestration ────────────────────────────────────────────────────

def validate_card(
    yaml_path: Path,
    vocab: dict[str, set[str]],
) -> tuple[Optional[ConditionCard], list[Issue]]:
    issues: list[Issue] = []

    try:
        card = load_card(yaml_path)
    except ValidationError as exc:
        for e in exc.errors():
            loc = ".".join(str(p) for p in e["loc"])
            issues.append(Issue("ERROR", loc, e["msg"]))
        return None, issues
    except Exception as exc:
        issues.append(Issue("ERROR", "load", str(exc)))
        return None, issues

    issues.extend(_check_icd(card))
    issues.extend(_check_corpus_version(card))
    issues.extend(_check_sources(card))
    issues.extend(_check_signal_regions(card))
    issues.extend(_check_graph_terms(card, vocab))
    issues.extend(_check_self_reference(card))
    return card, issues


# ── Cross-card checks ─────────────────────────────────────────────────────────

def _cross_card_checks(cards: list[tuple[Path, ConditionCard]]) -> list[Issue]:
    """
    Detect the same condition referenced with inconsistent names across cards.
    Normalises hyphens and whitespace before comparing - catches 'community-acquired pneumonia'
    vs 'community acquired pneumonia' style drift.
    """
    issues: list[Issue] = []

    # normalised_key → set of raw lowercase forms seen
    diff_forms: dict[str, set[str]] = {}
    for _, card in cards:
        for diff in card.graph.differentials:
            norm = re.sub(r"[-\s]+", " ", diff.lower().strip())
            diff_forms.setdefault(norm, set()).add(diff.lower().strip())

    for _key, forms in diff_forms.items():
        if len(forms) > 1:
            quoted = ", ".join(f"'{f}'" for f in sorted(forms))
            issues.append(Issue(
                "WARNING", "cross_card.differentials",
                f"Same condition with inconsistent names across cards: {quoted} - "
                f"standardise to the canonical form in conditions_vocabulary.md",
            ))

    return issues


# ── Discovery ─────────────────────────────────────────────────────────────────

def _find_yaml_files(target: Path) -> list[Path]:
    if target.is_file() and target.name == "condition.yaml":
        return [target]
    return sorted(target.rglob("condition.yaml"))


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python corpus_pipeline/validator.py <corpus_dir_or_condition.yaml>")
        return 1

    target = Path(sys.argv[1])
    if not target.exists():
        print(f"Path not found: {target}", file=sys.stderr)
        return 1

    yaml_files = _find_yaml_files(target)
    if not yaml_files:
        print(f"No condition.yaml files found under {target}", file=sys.stderr)
        return 1

    vocab = load_vocabularies()
    total_errors = 0
    total_warnings = 0
    loaded: list[tuple[Path, ConditionCard]] = []

    for yaml_path in yaml_files:
        try:
            rel = yaml_path.relative_to(_ROOT)
        except ValueError:
            rel = yaml_path

        card, issues = validate_card(yaml_path, vocab)

        label = str(rel)
        if card is not None:
            label += f"  ({card.condition}, {card.review_status})"
        print(f"\n=== {label} ===")

        errors = [i for i in issues if i.level == "ERROR"]
        warnings = [i for i in issues if i.level == "WARNING"]

        if not issues:
            print("  OK - no issues found")
        else:
            for issue in errors + warnings:
                print(issue)

        total_errors += len(errors)
        total_warnings += len(warnings)
        if card is not None:
            loaded.append((yaml_path, card))

    if len(loaded) > 1:
        print("\n=== Cross-card checks ===")
        cross = _cross_card_checks(loaded)
        if not cross:
            print("  OK - no cross-card inconsistencies")
        else:
            for issue in cross:
                print(issue)
                if issue.level == "ERROR":
                    total_errors += 1
                else:
                    total_warnings += 1

    print(
        f"\nSummary: {total_errors} error(s), {total_warnings} warning(s) "
        f"across {len(yaml_files)} card(s)"
    )
    return 1 if total_errors > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
