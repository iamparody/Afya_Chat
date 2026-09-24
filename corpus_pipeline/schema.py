"""
Pydantic schema for condition.yaml — the canonical condition card representation.

condition.yaml is the single source of truth. Markdown and ingest artifacts are
generated from it; they are never edited directly.

Schema version: 2.2 — adds comorbidity_signals block
Schema version: 2.3 — adds retrieval_anchors.positive and confusable_with (optional)
                       See docs/domain_evaluation_protocol.md for authoring rules.
"""

from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, field_validator, model_validator


# ── Controlled vocabulary literals ───────────────────────────────────────────

VALID_CATEGORIES = {
    "gastroenterological", "respiratory", "cardiovascular", "endocrine",
    "haematological", "infectious", "urological", "obstetric",
    "neurological", "dermatological", "musculoskeletal",
}

VALID_ENDEMIC_REGIONS = {
    "nationwide", "coast", "lake_basin", "highland", "highland_margins",
    "arid_semi_arid", "northern_kenya", "urban_informal",
}

VALID_SIGNALS = {
    "post_long_rains", "post_short_rains", "flooding", "water_scarcity",
    "prolonged_drought", "dry_dusty_season", "cold_dry_season", "heat_dehydration",
}

VALID_PATHWAYS = {
    "vector_borne", "waterborne", "zoonotic",
    "respiratory_mucosal", "nutritional_vulnerability", "airborne",
}

VALID_EFFECT_TYPES    = {"transmission_opportunity", "severity_modifier"}
VALID_EFFECT_DIRS     = {"up", "neutral", "down"}
VALID_STRENGTH        = {"low", "moderate", "strong"}
VALID_CONFIDENCE      = {"low", "moderate", "high"}
VALID_CAUSAL_DISTANCE = {"direct", "indirect"}

VALID_EVIDENCE_TYPES = {
    "observed_outbreaks", "surveillance_data",
    "regional_epidemiological_evidence", "expert_estimate",
}

VALID_SEASONAL_BASIS = {
    "typical_long_rains", "typical_short_rains",
    "dry_season", "perennial", "outbreak_associated",
}

VALID_EXPOSURES = {
    "floodwater_contact", "livestock_contact", "occupational_dust",
    "unsafe_water", "mosquito_exposure_high", "pastoralist_mobility",
    "fishing_lakeshore",
}

VALID_REVIEW_STATUSES = {"draft", "under_review", "clinician_verified"}

# ── Comorbidity signal vocabularies (schema 2.2) ──────────────────────────────
VALID_COMORBIDITY_EFFECTS    = {"management_modifier"}
VALID_COMORBIDITY_PRIORITIES = {"mandatory", "important"}
VALID_DEMOGRAPHIC_SEX        = {"male", "female", "any"}

SECTION_KEYS = [
    "cardinal_symptoms",
    "associated_symptoms",
    "diagnostic_features",
    "predisposing_factors",
    "typical_presentation",
    "differential_diagnoses",
    "argues_against",
    "red_flags",
    "diagnostic_context",
]

GRAPH_KEYS = [
    "cardinal_symptoms",
    "associated_symptoms",
    "risk_factors",
    "differentials",
    "argues_against",
    "red_flags",
    "confirms",
]


# ── Sub-models ────────────────────────────────────────────────────────────────

class Source(BaseModel):
    organization: str = ""
    title: str = ""
    year: str = ""


class LagWeeks(BaseModel):
    min: int
    max: int

    @model_validator(mode="after")
    def check_order(self) -> LagWeeks:
        if self.min > self.max:
            raise ValueError(f"lag_weeks.min ({self.min}) must be ≤ max ({self.max})")
        return self


class Applicability(BaseModel):
    requires_exposure: list[str] = []
    amplifiers: list[str] = []

    @field_validator("requires_exposure", "amplifiers")
    @classmethod
    def check_exposures(cls, v: list[str]) -> list[str]:
        for e in v:
            if e not in VALID_EXPOSURES:
                raise ValueError(f"Unknown exposure '{e}' — valid: {sorted(VALID_EXPOSURES)}")
        return v


class EnvironmentalSignal(BaseModel):
    signal: str
    pathways: list[str]
    effect_type: str
    effect_direction: str
    lag_weeks: LagWeeks
    strength: str
    confidence: str
    causal_distance: str
    evidence_type: str
    regions: list[str]
    seasonal_basis: str
    applicability: Applicability = Applicability()

    @field_validator("signal")
    @classmethod
    def check_signal(cls, v: str) -> str:
        if v not in VALID_SIGNALS:
            raise ValueError(f"Unknown signal '{v}' — valid: {sorted(VALID_SIGNALS)}")
        return v

    @field_validator("pathways")
    @classmethod
    def check_pathways(cls, v: list[str]) -> list[str]:
        for p in v:
            if p not in VALID_PATHWAYS:
                raise ValueError(f"Unknown pathway '{p}' — valid: {sorted(VALID_PATHWAYS)}")
        return v

    @field_validator("effect_type")
    @classmethod
    def check_effect_type(cls, v: str) -> str:
        if v not in VALID_EFFECT_TYPES:
            raise ValueError(f"Unknown effect_type '{v}' — valid: {sorted(VALID_EFFECT_TYPES)}")
        return v

    @field_validator("effect_direction")
    @classmethod
    def check_effect_direction(cls, v: str) -> str:
        if v not in VALID_EFFECT_DIRS:
            raise ValueError(f"Unknown effect_direction '{v}' — valid: {sorted(VALID_EFFECT_DIRS)}")
        return v

    @field_validator("strength")
    @classmethod
    def check_strength(cls, v: str) -> str:
        if v not in VALID_STRENGTH:
            raise ValueError(f"Unknown strength '{v}' — valid: {sorted(VALID_STRENGTH)}")
        return v

    @field_validator("confidence")
    @classmethod
    def check_confidence(cls, v: str) -> str:
        if v not in VALID_CONFIDENCE:
            raise ValueError(f"Unknown confidence '{v}' — valid: {sorted(VALID_CONFIDENCE)}")
        return v

    @field_validator("causal_distance")
    @classmethod
    def check_causal_distance(cls, v: str) -> str:
        if v not in VALID_CAUSAL_DISTANCE:
            raise ValueError(f"Unknown causal_distance '{v}' — valid: {sorted(VALID_CAUSAL_DISTANCE)}")
        return v

    @field_validator("evidence_type")
    @classmethod
    def check_evidence_type(cls, v: str) -> str:
        if v not in VALID_EVIDENCE_TYPES:
            raise ValueError(f"Unknown evidence_type '{v}' — valid: {sorted(VALID_EVIDENCE_TYPES)}")
        return v

    @field_validator("regions")
    @classmethod
    def check_regions(cls, v: list[str]) -> list[str]:
        for r in v:
            if r not in VALID_ENDEMIC_REGIONS:
                raise ValueError(f"Unknown region '{r}' — valid: {sorted(VALID_ENDEMIC_REGIONS)}")
        return v

    @field_validator("seasonal_basis")
    @classmethod
    def check_seasonal_basis(cls, v: str) -> str:
        if v not in VALID_SEASONAL_BASIS:
            raise ValueError(f"Unknown seasonal_basis '{v}' — valid: {sorted(VALID_SEASONAL_BASIS)}")
        return v


class DemographicGate(BaseModel):
    sex: Optional[Literal["male", "female", "any"]] = None
    reproductive_age: Optional[bool] = None


class ComorbiditySignal(BaseModel):
    context: str
    triggers: list[str]
    demographic_gate: DemographicGate = DemographicGate()
    effect: str
    priority: str
    missing_info_prompt: str
    icd_note: Optional[str] = None

    @field_validator("effect")
    @classmethod
    def check_effect(cls, v: str) -> str:
        if v not in VALID_COMORBIDITY_EFFECTS:
            raise ValueError(f"Unknown effect '{v}' — valid: {sorted(VALID_COMORBIDITY_EFFECTS)}")
        return v

    @field_validator("priority")
    @classmethod
    def check_priority(cls, v: str) -> str:
        if v not in VALID_COMORBIDITY_PRIORITIES:
            raise ValueError(f"Unknown priority '{v}' — valid: {sorted(VALID_COMORBIDITY_PRIORITIES)}")
        return v


class RetrievalAnchors(BaseModel):
    positive: list[str] = []


class GraphBlock(BaseModel):
    cardinal_symptoms: list[str] = []
    associated_symptoms: list[str] = []
    risk_factors: list[str] = []
    differentials: list[str] = []
    argues_against: list[str] = []
    red_flags: list[str] = []
    confirms: list[str] = []


class ClinicalSections(BaseModel):
    cardinal_symptoms: str
    associated_symptoms: str
    diagnostic_features: str
    predisposing_factors: str
    typical_presentation: str
    differential_diagnoses: str
    argues_against: str
    red_flags: str
    diagnostic_context: str

    @model_validator(mode="after")
    def check_non_empty(self) -> ClinicalSections:
        for key in SECTION_KEYS:
            val = getattr(self, key, "")
            if not val or not val.strip():
                raise ValueError(f"Section '{key}' must not be empty")
        return self

    @model_validator(mode="after")
    def check_hedging_not_stripped(self) -> ClinicalSections:
        """Check that clinical probability sections preserve hedging language."""
        # Sections where stripping hedging language materially changes clinical meaning.
        # cardinal_symptoms/diagnostic_features are objective — no hedging expected.
        probability_sections = {
            "typical_presentation", "differential_diagnoses", "argues_against",
        }
        hedging = {"may", "usually", "commonly", "often", "typically", "can", "suggest",
                   "suggests", "suggested", "argues", "argue", "weakens", "weaken",
                   "some", "most", "frequently", "rarely", "common",
                   "should", "characteristically", "consistent", "considered",
                   "likely", "unlikely", "possible", "probable", "reduces", "cannot"}
        for key in probability_sections:
            val = getattr(self, key, "")
            words = set(val.lower().split())
            if len(val) > 200 and not words.intersection(hedging):
                raise ValueError(
                    f"Section '{key}' has no hedging language (may/usually/commonly) — "
                    f"check that clinical qualifiers were not stripped"
                )
        return self


# ── Root model ────────────────────────────────────────────────────────────────

class ConditionCard(BaseModel):
    # ── Identity ──────────────────────────────────────────────────────────────
    condition: str
    icd11: str
    icd10: str
    category: str
    corpus_version: str
    schema_version: Literal["2.2", "2.3"]
    review_status: str
    reviewed_by: Optional[str] = None
    last_reviewed: Optional[str] = None
    icd_verified: bool = False
    icd_title: Optional[str] = None
    icd_entity_uri: Optional[str] = None
    sources: list[Source] = []

    # ── Location ──────────────────────────────────────────────────────────────
    endemic_regions: list[str]

    # ── Environmental signals ─────────────────────────────────────────────────
    environmental_signals: list[EnvironmentalSignal] = []

    # ── Comorbidity signals ───────────────────────────────────────────────────
    comorbidity_signals: list[ComorbiditySignal] = []

    # ── Retrieval evaluation (schema 2.3, optional) ───────────────────────────
    retrieval_anchors: Optional[RetrievalAnchors] = None
    confusable_with: list[str] = []

    # ── Graph ─────────────────────────────────────────────────────────────────
    graph: GraphBlock

    # ── Clinical sections ─────────────────────────────────────────────────────
    sections: ClinicalSections

    @field_validator("category")
    @classmethod
    def check_category(cls, v: str) -> str:
        if v not in VALID_CATEGORIES:
            raise ValueError(f"Unknown category '{v}' — valid: {sorted(VALID_CATEGORIES)}")
        return v

    @field_validator("review_status")
    @classmethod
    def check_review_status(cls, v: str) -> str:
        if v not in VALID_REVIEW_STATUSES:
            raise ValueError(f"Unknown review_status '{v}' — valid: {sorted(VALID_REVIEW_STATUSES)}")
        return v

    @field_validator("endemic_regions")
    @classmethod
    def check_endemic_regions(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("endemic_regions must have at least one entry")
        for r in v:
            if r not in VALID_ENDEMIC_REGIONS:
                raise ValueError(f"Unknown endemic_region '{r}' — valid: {sorted(VALID_ENDEMIC_REGIONS)}")
        return v

    @field_validator("environmental_signals")
    @classmethod
    def check_signal_count(cls, v: list[EnvironmentalSignal]) -> list[EnvironmentalSignal]:
        if len(v) > 3:
            raise ValueError(f"Maximum 3 environmental_signals per card, got {len(v)}")
        return v

    @field_validator("reviewed_by", "last_reviewed", mode="before")
    @classmethod
    def empty_string_to_none(cls, v):
        if v == "":
            return None
        return v

    @field_validator("condition")
    @classmethod
    def check_condition_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("condition must not be empty")
        return v

    @field_validator("icd11", "icd10")
    @classmethod
    def check_icd_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("ICD codes must not be empty — verify at icd.who.int")
        return v


def load_card(path) -> ConditionCard:
    """Load and validate a condition.yaml file. Raises ValidationError on failure."""
    import yaml
    from pathlib import Path
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return ConditionCard.model_validate(data)
