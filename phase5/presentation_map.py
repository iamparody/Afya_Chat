"""
Presentation map classifier for the Acute Febrile Illness (AFI) domain.

Deterministic keyword-based pathway classification from
docs/domain_contracts/acute_febrile_illness.md §3.

Only conditions with existing corpus cards are included as candidates.
Conditions without cards (Chikungunya, Meningitis, Cholera, Leptospirosis,
Rickettsial illness, Brucellosis) are excluded — the LLM cannot reason from
candidates that have no supporting evidence passages.
"""

# ── Condition name constants ───────────────────────────────────────────────────
# Must match the `condition:` frontmatter field exactly.

_MALARIA = "Malaria (unspecified)"
_DENGUE  = "Dengue fever"
_TYPHOID = "Typhoid fever"
_CAP     = "Community-acquired pneumonia"
_TB      = "Pulmonary tuberculosis"
_AGE     = "Acute gastroenteritis (infectious)"

# ── Signal keyword sets ───────────────────────────────────────────────────────

FEVER_KEYWORDS: frozenset = frozenset([
    "fever", "febrile", "pyrexia", "pyrexial", "high temperature",
    "rigors", "chills",
])

# Explicit negation markers — if any are present, fever is absent.
# Checked before FEVER_KEYWORDS to handle "no fever", "afebrile", etc.
NO_FEVER_MARKERS: frozenset = frozenset([
    "no fever", "afebrile", "apyrexial", "apyrexic",
    "no temperature", "no high temperature",
])

# Presence of any of these + fever triggers P9 (prolonged/recurrent)
DURATION_KEYWORDS: frozenset = frozenset([
    "weeks", "month",
    "7 days", "10 days", "14 days", "21 days",
    "prolonged fever", "persistent fever", "recurrent fever",
])

_NEURO_KW: frozenset = frozenset([
    "headache", "head ache", "altered consciousness", "altered mental",
    "confusion", "confused", "neck stiffness", "photophobia",
    "seizure", "convuls", "unconscious", "drowsy", "meningism",
])

_RESP_KW: frozenset = frozenset([
    "cough", "dyspnoea", "breathless", "chest pain", "sputum",
    "respiratory", "wheez",
])

_GI_KW: frozenset = frozenset([
    "diarrhoea", "diarrhea", "vomiting", "abdominal pain", "nausea",
    "abdominal", "loose stool",
])

_RASH_KW: frozenset = frozenset([
    "rash", "petechiae", "purpura", "eschar", "erythema", "maculopapular",
])

_JOINT_KW: frozenset = frozenset([
    "arthralgia", "myalgia", "joint pain", "joint swelling",
    "muscle pain", "muscle ache", "arthritis",
])

_JAUNDICE_KW: frozenset = frozenset([
    "jaundice", "jaundiced", "yellow", "icterus",
])

_DIARRHOEA_KW: frozenset = frozenset([
    "diarrhoea", "diarrhea", "watery stool", "loose stool",
])

# ── Pathway definitions ───────────────────────────────────────────────────────
# Source: §3.2 Presentation matrix.
# Candidates ordered as in §3 (highest clinical priority first).
# P1 is the undifferentiated fallback — fires when fever is present but no
# localising pathway triggers.

PATHWAYS: dict = {
    "P1": {
        "label": "Acute undifferentiated fever",
        "candidates": [_MALARIA, _DENGUE, _TYPHOID],
        # Chikungunya excluded — no card. Governance-pending conditions excluded.
    },
    "P2": {
        "label": "Fever + headache / neurological features",
        "candidates": [_MALARIA, _TYPHOID, _DENGUE],
        # Meningitis excluded (no card). Rickettsial/Leptospirosis excluded.
        "localising": _NEURO_KW,
    },
    "P3": {
        "label": "Fever + respiratory symptoms",
        "candidates": [_CAP, _MALARIA, _TB],
        # Leptospirosis/Rickettsial excluded.
        "localising": _RESP_KW,
    },
    "P4": {
        "label": "Fever + gastrointestinal symptoms",
        "candidates": [_TYPHOID, _MALARIA, _DENGUE, _AGE],
        # Cholera excluded (no card). Leptospirosis excluded.
        "localising": _GI_KW,
    },
    "P5": {
        "label": "Fever + rash",
        "candidates": [_DENGUE, _MALARIA],
        # Chikungunya excluded (no card). Rickettsial/Meningitis excluded.
        "localising": _RASH_KW,
    },
    "P6": {
        "label": "Fever + arthralgia / myalgia",
        "candidates": [_DENGUE, _MALARIA],
        # Chikungunya excluded (no card). Leptospirosis/Rickettsial/Brucellosis excluded.
        "localising": _JOINT_KW,
    },
    "P7": {
        "label": "Fever + jaundice",
        "candidates": [_MALARIA, _TYPHOID, _DENGUE],
        # Leptospirosis excluded.
        "localising": _JAUNDICE_KW,
    },
    "P8": {
        "label": "Acute watery diarrhoea",
        "candidates": [_AGE, _TYPHOID],
        # Cholera excluded (no card). Fever may be absent — triggered by diarrhoea alone.
    },
    "P9": {
        "label": "Prolonged or recurrent fever",
        "candidates": [_TB, _TYPHOID, _MALARIA],
        # Brucellosis/Leptospirosis excluded.
    },
}


# ── Classifier ────────────────────────────────────────────────────────────────

def classify(presentation: str) -> list[str]:
    """
    Return matched AFI pathway IDs for this presentation.

    Deterministic substring match against §3 trigger definitions.
    Multiple pathways may fire simultaneously.

    Rules:
    - P2-P7: require fever indicator + localising keyword.
    - P8: fires on diarrhoea keyword alone (fever absent in cholera-like illness).
    - P9: requires fever + duration keyword (>= 7 days implied).
    - P1: fallback — fires only when fever is present but no other pathway triggered.
    """
    text = presentation.lower()
    has_fever = (
        any(kw in text for kw in FEVER_KEYWORDS)
        and not any(kw in text for kw in NO_FEVER_MARKERS)
    )

    matched: list[str] = []

    for pid in ("P2", "P3", "P4", "P5", "P6", "P7"):
        if has_fever and any(kw in text for kw in PATHWAYS[pid]["localising"]):
            matched.append(pid)

    if any(kw in text for kw in _DIARRHOEA_KW):
        matched.append("P8")

    if has_fever and any(kw in text for kw in DURATION_KEYWORDS):
        matched.append("P9")

    if has_fever and not matched:
        matched.append("P1")

    return matched


def get_map_candidates(pathway_ids: list[str]) -> list[str]:
    """
    Return deduplicated condition names from matched pathways.
    Preserves order: first occurrence wins (pathway priority order).
    """
    seen: dict[str, bool] = {}
    for pid in pathway_ids:
        for cond in PATHWAYS[pid]["candidates"]:
            if cond not in seen:
                seen[cond] = True
    return list(seen.keys())
