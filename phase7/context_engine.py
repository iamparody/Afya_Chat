"""
Phase 7 -- Environmental Context Engine.

Produces EnvironmentalEvidence objects from condition card signals and
encounter context (location, date, exposures). Injected into the RAG
prompt as a labelled, source-attributed statement -- never as a bare
weather observation.

Architecture:
  get_environmental_evidence(candidates, ...) -> ContextResult | NO_RELEVANT_CONTEXT
      |- candidate has no environmental_signals -> skip
      +- signals present -> CHIRPSProvider (primary) or StaticCalendarProvider (fallback)
              -> EnvironmentalEvidence per qualifying candidate-signal pair
              -> ContextResult.evidence (passed gate) or .suppressed (low/low gated)

Return semantics:
  NO_RELEVANT_CONTEXT (str) -- no candidates had environmental_signals declared,
                               OR all signals failed region/exposure/seasonal gates
                               before reaching the strength/confidence gate
  ContextResult              -- at least one signal reached gate 4;
                               .evidence = inject into Gemini;
                               .suppressed = matched but strength/confidence filtered

Phases:
  7c -- StaticCalendarProvider + CHIRPSProvider stub + get_environmental_evidence()
  9  -- CHIRPSProvider live (replaces static calendar lookups)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from phase7.rainfall_providers import OpenMeteoProvider, RainfallFeatures

# Sentinel returned when no candidates have declared environmental_signals,
# OR when all signals fail region/exposure/seasonal gates before reaching
# the strength/confidence gate.  Distinguishable from ContextResult with
# empty .evidence (= signals matched but suppressed).
NO_RELEVANT_CONTEXT = "no_relevant_context"

# ---------------------------------------------------------------------------
# Static Kenya seasonal calendar
# ---------------------------------------------------------------------------
# Month numbers (1=January) when each signal's effects are clinically
# observable.  The ranges incorporate typical lag between the environmental
# event and peak clinical presentation (e.g. post_long_rains = 4-8 w after
# May end = June-August).  Per-card lag is preserved in temporal_window for
# explanation text; it does not gate signal activation here.
_SIGNAL_ACTIVE_MONTHS: dict[str, set[int]] = {
    "post_long_rains":   {6, 7, 8},           # June-August  (4-8 w after May end)
    "post_short_rains":  {12, 1, 2},          # December-February (4-8 w after November)
    "flooding":          {3, 4, 5, 10, 11},   # March-May, October-November (rain seasons)
    "water_scarcity":    {1, 2, 6, 7, 8, 9},  # January-February + June-September dry seasons
    "prolonged_drought": {6, 7, 8, 9, 10},    # JJAS dry season + transitions
    "dry_dusty_season":  {11, 12, 1, 2, 3},   # November-March (NE monsoon)
    "cold_dry_season":   {6, 7, 8},           # June-August (highland cold season)
    "heat_dehydration":  {1, 2, 3, 9, 10},    # January-March + September-October
}

# Strength/confidence combinations always suppressed -- locked from Phase 7c.
_SUPPRESS_COMBOS: set[tuple[str, str]] = {("low", "low")}


# ---------------------------------------------------------------------------
# EnvironmentalEvidence dataclass
# ---------------------------------------------------------------------------

@dataclass
class EnvironmentalEvidence:
    """
    One piece of environmental evidence for a single candidate-signal pair.

    Fields preserved verbatim from the condition card schema so the context
    engine can generate appropriately hedged, source-attributed language.
    causal_distance, effect_type, strength, and confidence jointly determine
    the wording and clinical weight -- do not flatten these into a single score.

    Clinical evidence always dominates.  EnvironmentalEvidence adjusts priors;
    it does not select diagnoses.

    suppression_reason is non-empty only for signals in ContextResult.suppressed.
    """
    signal: str
    causal_distance: str                     # "direct" | "indirect"
    effect_type: str                         # "transmission_opportunity" | "severity_modifier"
    effect_direction: str                    # "up" | "neutral" | "down"
    strength: str                            # "low" | "moderate" | "strong"
    confidence: str                          # "low" | "moderate" | "high"
    source: str = "static_calendar"          # "chirps" | "static_calendar"
    spatial_basis: str = ""                  # endemic_region matched
    temporal_window: dict = field(default_factory=dict)  # {"min": int, "max": int} weeks
    data_age: float = 0.0                    # hours since data was fetched
    data_status: str = "fresh"              # "fresh" | "stale"
    explanation: str = ""                    # human-readable, source-labelled statement
    condition: str = ""                      # condition this evidence belongs to
    suppression_reason: str = ""             # non-empty when in ContextResult.suppressed


# ---------------------------------------------------------------------------
# ContextResult
# ---------------------------------------------------------------------------

@dataclass
class ContextResult:
    """
    Return value from get_environmental_evidence() when at least one signal
    reached the strength/confidence gate.

    evidence   : signals that passed all 4 gates -- inject into Gemini
    suppressed : signals that matched region/exposure/seasonal but were
                 filtered by the strength/confidence gate.  Do NOT inject
                 into Gemini, but preserve for audit and Phase 8/9 calibration.

    Caller pattern:
        result = get_environmental_evidence(...)
        if result is NO_RELEVANT_CONTEXT:
            pass  # no environmental context at all
        elif result.has_evidence:
            inject(result.evidence)  # substantive or hedged evidence
        else:
            log_suppressed(result.suppressed)  # matched but gated -- audit only
    """
    evidence: list[EnvironmentalEvidence]
    suppressed: list[EnvironmentalEvidence]
    rainfall: RainfallFeatures | None = None   # raw features; None when lat/lon unavailable

    @property
    def has_evidence(self) -> bool:
        return bool(self.evidence)


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------

class StaticCalendarProvider:
    """
    Kenya rainfall calendar -- deterministic lookup by month.

    ENSO_PHASE is an annual modifier carried for future use in explanation
    text.  It does not currently gate signal activation (scope: Phase 9).
    Update ENSO_PHASE each year from NOAA / Kenya Meteorological Department.

    No network access or authentication required.
    """

    # Updated annually from NOAA / Kenya Meteorological Department
    ENSO_PHASE: str = "neutral"  # "neutral" | "el_nino" | "la_nina"

    def is_signal_active(self, signal_name: str, reference_date: datetime) -> bool:
        """True if signal's environmental condition is active during reference_date's month."""
        active_months = _SIGNAL_ACTIVE_MONTHS.get(signal_name, set())
        return reference_date.month in active_months

    @staticmethod
    def source_label() -> str:
        return "static_calendar"


class CHIRPSProvider:
    """
    Phase 9 stub -- CHIRPS observed-rainfall provider.

    Falls back to StaticCalendarProvider on every call in Phase 7.
    Phase 9 replaces is_signal_active() with a live API fetch;
    the method signature and source-label contract remain unchanged
    so rag.py and the test suite require no modification.
    """

    def __init__(self, static: Optional[StaticCalendarProvider] = None) -> None:
        self._static = static or StaticCalendarProvider()

    def is_signal_active(
        self,
        signal_name: str,
        reference_date: datetime,
        region: str = "",
    ) -> tuple[bool, str]:
        """
        Returns (is_active, source_label).

        Phase 7: always falls back to static calendar; source = "static_calendar".
        Phase 9: query CHIRPS API with (region -> bounding box -> grid cell),
                 compute rainfall last 7/30/60 days, flag if in signal's lag window;
                 source = "chirps" when observed data is used.
        """
        return self._static.is_signal_active(signal_name, reference_date), self._static.source_label()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_SIGNAL_CACHE: Optional[dict[str, list[dict]]] = None


def _load_environmental_signals() -> dict[str, list[dict]]:
    """Load environmental_signals from graph_entities.jsonl, indexed by condition name."""
    global _SIGNAL_CACHE
    if _SIGNAL_CACHE is not None:
        return _SIGNAL_CACHE
    path = Path(__file__).parent.parent / "graph_entities.jsonl"
    result: dict[str, list[dict]] = {}
    if path.exists():
        with path.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                r = json.loads(line)
                result[r["condition"]] = r.get("environmental_signals", [])
    _SIGNAL_CACHE = result
    return result


def _reset_signal_cache() -> None:
    """Clear the in-memory signal cache. For testing only."""
    global _SIGNAL_CACHE
    _SIGNAL_CACHE = None


def _inject_signal_data(data: dict[str, list[dict]]) -> None:
    """Override signal cache with test fixtures. For testing only."""
    global _SIGNAL_CACHE
    _SIGNAL_CACHE = data


def _passes_gate(strength: str, confidence: str, causal_distance: str) -> tuple[bool, str]:
    """
    Apply locked strength/confidence suppression rule.
    Returns (passes, hedging_level): hedging_level is "substantive" | "hedged" | "".

    Rules (locked from Phase 7c colleague review):
      low/low  -> always suppress (covers indirect+low/low -- same rule)
      strong or high -> substantive
      anything else  -> hedged
    """
    if (strength, confidence) in _SUPPRESS_COMBOS:
        return False, ""
    if strength == "strong" or confidence == "high":
        return True, "substantive"
    return True, "hedged"


def _build_explanation(
    condition: str,
    signal_name: str,
    causal_distance: str,
    effect_type: str,
    effect_direction: str,
    strength: str,
    confidence: str,
    source: str,
    hedging: str,
    temporal_window: dict,
    spatial_basis: str,
) -> str:
    lag_text = ""
    if temporal_window:
        mn = temporal_window.get("min", "?")
        mx = temporal_window.get("max", "?")
        lag_text = f"; lag {mn}-{mx} weeks"

    direction_word = {
        "up": "elevated", "down": "reduced", "neutral": "unchanged"
    }.get(effect_direction, effect_direction)

    effect_word = (
        "transmission opportunity"
        if effect_type == "transmission_opportunity"
        else "severity modifier"
    )

    source_label = (
        "static seasonal calendar" if source == "static_calendar" else "CHIRPS observed rainfall"
    )

    qualifier = ""
    if hedging == "hedged":
        qualifier = (
            " [indirect association]" if causal_distance == "indirect" else " [moderate evidence]"
        )

    return (
        f"{signal_name.replace('_', ' ').capitalize()} -- {direction_word} {effect_word}"
        f" for {condition} in {spatial_basis}{lag_text}{qualifier}."
        f" Source: {source_label}. Clinical findings take precedence."
    )


# ---------------------------------------------------------------------------
# Gate function
# ---------------------------------------------------------------------------

def get_environmental_evidence(
    candidates: list[str],
    encounter_date: datetime,
    patient_location: Optional[str] = None,
    patient_exposures: Optional[list[str]] = None,
    onset_date: Optional[datetime] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> ContextResult | str:
    """
    Evaluate environmental context for RAG candidates.

    Returns ContextResult or NO_RELEVANT_CONTEXT (str).

    NO_RELEVANT_CONTEXT is returned when:
      - no candidates have environmental_signals declared on their card, OR
      - all signals fail region/exposure/seasonal gates before reaching
        the strength/confidence gate

    ContextResult is returned when at least one signal passes gates 1-3:
      .evidence   = signals that also pass gate 4 (inject into Gemini)
      .suppressed = signals that failed gate 4 (audit trail; do NOT inject)

    Parameters
    ----------
    candidates        : condition names from RAG output
    encounter_date    : datetime of the clinical encounter
    patient_location  : endemic_region vocabulary value; if None, region gate is skipped
    patient_exposures : list of exposure vocabulary values
    onset_date        : symptom onset datetime; used as seasonal reference if provided,
                        otherwise encounter_date is used
    latitude          : county centroid latitude from LocationNormalization (optional)
    longitude         : county centroid longitude from LocationNormalization (optional)
                        When both are provided, OpenMeteoProvider fetches raw rainfall
                        features attached to ContextResult.rainfall for audit and future
                        threshold calibration.  Signal activation is still controlled by
                        StaticCalendarProvider regardless of whether rainfall data is present.

    Gate sequence (applied per signal):
      1. Region: if signal.regions is non-empty, patient_location must be in it
                 (signals with "nationwide" pass for any patient_location)
      2. Exposure: if requires_exposure is non-empty, patient must have >= 1
      3. Seasonal: signal must be active during reference_date
      4. Strength/confidence: low/low always suppressed (see _passes_gate)
    """
    patient_exposures = patient_exposures or []
    reference_date = onset_date if onset_date is not None else encounter_date

    env_signals = _load_environmental_signals()
    provider = CHIRPSProvider()

    # Fetch raw rainfall features when coordinates are available.
    # These are attached to ContextResult for audit; they do not gate signals.
    rainfall: RainfallFeatures | None = None
    if latitude is not None and longitude is not None:
        try:
            rainfall = OpenMeteoProvider().get_rainfall_features(latitude, longitude, reference_date)
        except Exception:
            rainfall = None

    passed: list[EnvironmentalEvidence] = []
    suppressed: list[EnvironmentalEvidence] = []
    any_reached_gate_4 = False

    for condition in candidates:
        signals = env_signals.get(condition, [])
        if not signals:
            continue

        for sig in signals:
            signal_name = sig.get("signal", "")

            # ── 1. Region gate ────────────────────────────────────────────────
            signal_regions: list[str] = sig.get("regions", [])
            if signal_regions and patient_location:
                if "nationwide" not in signal_regions and patient_location not in signal_regions:
                    continue

            # ── 2. Exposure gate ──────────────────────────────────────────────
            requires: list[str] = sig.get("applicability", {}).get("requires_exposure", [])
            if requires and not any(exp in patient_exposures for exp in requires):
                continue

            # ── 3. Seasonal gate ──────────────────────────────────────────────
            is_active, source = provider.is_signal_active(
                signal_name, reference_date, patient_location or ""
            )
            if not is_active:
                continue

            # Gates 1-3 passed -- signal is a real contextual match.
            # Now gate 4 determines inject vs suppress (not absent vs present).
            any_reached_gate_4 = True

            strength = sig.get("strength", "low")
            confidence = sig.get("confidence", "low")
            causal_distance = sig.get("causal_distance", "indirect")
            passes, hedging = _passes_gate(strength, confidence, causal_distance)

            # ── Resolve spatial_basis ─────────────────────────────────────────
            if patient_location:
                spatial_basis = patient_location
            elif "nationwide" in signal_regions:
                spatial_basis = "nationwide"
            else:
                spatial_basis = ", ".join(signal_regions) if signal_regions else "unspecified"

            # ── 4. Strength/confidence gate ───────────────────────────────────
            suppression_reason = ""
            if not passes:
                suppression_reason = f"strength:{strength}/confidence:{confidence} below emission threshold"

            explanation = _build_explanation(
                condition=condition,
                signal_name=signal_name,
                causal_distance=causal_distance,
                effect_type=sig.get("effect_type", ""),
                effect_direction=sig.get("effect_direction", "up"),
                strength=strength,
                confidence=confidence,
                source=source,
                hedging=hedging,
                temporal_window=sig.get("lag_weeks", {}),
                spatial_basis=spatial_basis,
            )

            ev = EnvironmentalEvidence(
                signal=signal_name,
                causal_distance=causal_distance,
                effect_type=sig.get("effect_type", ""),
                effect_direction=sig.get("effect_direction", "up"),
                strength=strength,
                confidence=confidence,
                source=source,
                spatial_basis=spatial_basis,
                temporal_window=sig.get("lag_weeks", {}),
                data_age=0.0,
                data_status="fresh",
                explanation=explanation,
                condition=condition,
                suppression_reason=suppression_reason,
            )

            if passes:
                passed.append(ev)
            else:
                suppressed.append(ev)

    if not any_reached_gate_4:
        return NO_RELEVANT_CONTEXT
    return ContextResult(evidence=passed, suppressed=suppressed, rainfall=rainfall)
