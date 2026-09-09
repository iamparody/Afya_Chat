"""
Phase 7 — Environmental Context Engine.

Produces EnvironmentalEvidence objects from condition card signals and
encounter context (location, date, exposures). Injected into the RAG
prompt as a labelled, source-attributed statement — never as a bare
weather observation.

Architecture:
  get_environmental_evidence(candidates, ...) → list[EnvironmentalEvidence] | NO_RELEVANT_CONTEXT
      ├── candidate has no environmental_signals → skip (no_relevant_context)
      └── signals present → CHIRPSProvider (primary) or StaticCalendarProvider (fallback)
              → EnvironmentalEvidence per qualifying candidate-signal pair

Phases:
  7c — StaticCalendarProvider + CHIRPSProvider stub + get_environmental_evidence()
  9  — CHIRPSProvider live (replaces static calendar lookups)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

# Sentinel returned when no candidates have declared environmental_signals.
# First-class result — not an edge case.
NO_RELEVANT_CONTEXT = "no_relevant_context"


@dataclass
class EnvironmentalEvidence:
    """
    One piece of environmental evidence for a single candidate-signal pair.

    Fields preserved verbatim from the condition card schema so the context
    engine can generate appropriately hedged, source-attributed language.
    The engine must NOT flatten these into a generic weather statement —
    causal_distance, effect_type, strength, and confidence jointly determine
    the wording and clinical weight.

    Clinical evidence always dominates. EnvironmentalEvidence adjusts priors;
    it does not select diagnoses.
    """
    signal: str
    causal_distance: str          # "direct" | "indirect"
    effect_type: str              # "transmission_opportunity" | "severity_modifier"
    effect_direction: str         # "up" | "neutral" | "down"
    strength: str                 # "low" | "moderate" | "strong"
    confidence: str               # "low" | "moderate" | "high"
    source: str = "static_calendar"          # "chirps" | "static_calendar"
    spatial_basis: str = ""                  # endemic_region matched
    temporal_window: dict = field(default_factory=dict)  # {"min": int, "max": int} weeks
    data_age: float = 0.0                    # hours since data was fetched
    data_status: str = "fresh"               # "fresh" | "stale"
    explanation: str = ""                    # human-readable, source-labelled statement
