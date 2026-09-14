"""
phase7/comorbidity_engine.py

Deterministic comorbidity context scanner.

Reads comorbidity_signals declared on corpus cards (via graph_entities.jsonl)
and scans the presentation text for declared trigger keywords.
When a trigger matches, raises a ComorbidityAlert carrying the missing_info_prompt.

Pattern mirrors get_environmental_evidence() in context_engine.py:
  corpus card declares the trigger/context contract
      → engine scans presentation deterministically
          → ComorbidityAlert injected into build_context()

The engine does NOT assert an unconfirmed comorbidity — it surfaces what needs
to be asked. The clinician confirms or denies in the approval workflow.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


_COMORBIDITY_CACHE: dict[str, list[dict]] | None = None


def _load_comorbidity_signals() -> dict[str, list[dict]]:
    """
    Load comorbidity_signals from the YAML-pipeline output, indexed by condition name.

    comorbidity_signals is a schema 2.2 field that only exists in YAML corpus cards
    (corpus/*/condition.yaml → corpus_pipeline/output/graph_entities.jsonl).
    context_engine.py reads the Markdown-pipeline graph_entities.jsonl (cds/ root)
    which carries environmental_signals but not comorbidity_signals.
    When all cards are migrated to YAML, both engines will read the same file.
    """
    global _COMORBIDITY_CACHE
    if _COMORBIDITY_CACHE is not None:
        return _COMORBIDITY_CACHE
    path = Path(__file__).parent.parent / "corpus_pipeline" / "output" / "graph_entities.jsonl"
    result: dict[str, list[dict]] = {}
    if path.exists():
        with path.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                r = json.loads(line)
                cond = r.get("condition", "")
                if cond:
                    result[cond] = r.get("comorbidity_signals", [])
    _COMORBIDITY_CACHE = result
    return result


def _reset_cache() -> None:
    """Clear the in-memory cache. For testing only."""
    global _COMORBIDITY_CACHE
    _COMORBIDITY_CACHE = None


def _inject_signal_data(data: dict[str, list[dict]]) -> None:
    """Override cache with test fixtures. For testing only."""
    global _COMORBIDITY_CACHE
    _COMORBIDITY_CACHE = data


@dataclass
class ComorbidityAlert:
    context: str              # slug, e.g. "pregnancy_status"
    matched_trigger: str      # the specific trigger keyword that matched
    missing_info_prompt: str  # text to surface in missing_information guidance
    icd_note: Optional[str]   # semantic ICD note — NOT a hardcoded code
    priority: str             # "mandatory" | "important"
    effect: str               # "management_modifier"
    applies_to: list[str] = field(default_factory=list)  # conditions that declared this context


def get_comorbidity_alerts(
    candidates: list[str],
    presentation: str,
) -> list[ComorbidityAlert]:
    """
    Return ComorbidityAlert objects for any declared signals that match the presentation.

    candidates: list of condition names (str) — from RetrievalRouter
    presentation: raw patient presentation text

    One alert per unique context slug. If multiple candidates declare the same context
    and the same trigger fires, all applicable conditions are listed on a single alert.

    Returns an empty list when no triggers match — caller should treat this as a no-op,
    not an error.
    """
    signals_by_condition = _load_comorbidity_signals()
    text = presentation.lower()

    seen: dict[str, ComorbidityAlert] = {}  # keyed by context slug

    for condition in candidates:
        declared = signals_by_condition.get(condition, [])
        for sig in declared:
            ctx = sig.get("context", "")
            if not ctx:
                continue
            triggers = sig.get("triggers", [])
            matched = next((t for t in triggers if t.lower() in text), None)
            if matched is None:
                continue
            if ctx in seen:
                if condition not in seen[ctx].applies_to:
                    seen[ctx].applies_to.append(condition)
            else:
                seen[ctx] = ComorbidityAlert(
                    context=ctx,
                    matched_trigger=matched,
                    missing_info_prompt=sig.get("missing_info_prompt", "").strip(),
                    icd_note=sig.get("icd_note"),
                    priority=sig.get("priority", "important"),
                    effect=sig.get("effect", ""),
                    applies_to=[condition],
                )

    return list(seen.values())
