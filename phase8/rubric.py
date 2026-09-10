"""
Phase 8 reasoning evaluation rubric.

Two scorer families, uniform interface:
    scorer(result, expected, provider=None) -> {"score": int, "justification": str}

    deterministic_scorers  — pure Python; provider ignored
    judge_scorers          — Gemini-as-judge; provider required

Diagnostic shift is not in either dict — it requires both initial and enriched
results and is handled by evaluate_reasoning.py.

Scoring scale:
    2 = correct and clinically appropriate
    1 = partially correct or incomplete but not harmful
    0 = incorrect or clinically unsafe

EXPECTED is the reference standard. Judge scores are automated estimates;
run one manual calibration pass before trusting them in CI.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "phase5"))
sys.path.insert(0, str(ROOT / "phase8"))


# ── Reference standard ────────────────────────────────────────────────────────
#
# Keys used by scorers:
#   acceptable_leads              — list[str]  deterministic: leading_diagnosis
#   acceptable_differentials      — list[str]  deterministic: differential_relevance
#   acceptable_confidence_range   — list[str]  deterministic: confidence_range
#   documented_red_flags          — list[str]  deterministic: red_flags (must be marked present)
#   check_for_red_flags           — list[str]  deterministic: red_flags (must be mentioned)
#   required_supporting_features  — list[str]  judge: supporting_features (keyword match)
#   expected_arguing_against_kw   — list[str]  judge: arguing_against_accuracy (keyword match)
#   relevant_missing_information  — list[str]  judge: missing_information_relevance (keyword match)
#   acceptable_discriminating_q   — list[str]  judge: question_quality (keyword match)
#   expected_enriched_leads       — list[str]  special: diagnostic_shift (lowercase substring)
#   is_negative_case              — bool       skip disambiguation dimensions; expect no questions

EXPECTED = {
    "d1": {
        "label": "Upper GI overlap — PUD / GORD / Functional dyspepsia",
        "presentation": (
            "F/28. Epigastric discomfort x3/52, nausea, occasional retrosternal burning. "
            "No vomiting, no PR bleeding, no weight loss. No NSAID use reported."
        ),
        "acceptable_leads": [
            "Gastro-oesophageal reflux disease",
            "Peptic ulcer disease",
            "Functional dyspepsia",
        ],
        "acceptable_differentials": [
            "Gastro-oesophageal reflux disease",
            "Peptic ulcer disease",
            "Functional dyspepsia",
        ],
        "acceptable_confidence_range": ["moderate"],
        "documented_red_flags": [],
        "check_for_red_flags": ["PR bleeding", "haematemesis", "dysphagia", "weight loss"],
        "required_supporting_features": ["epigastric", "nausea", "burning", "retrosternal"],
        "expected_arguing_against_kw": ["nsaid", "bleed", "vomit"],
        "relevant_missing_information": [
            "heartburn", "acid", "antacid", "helicobacter", "H. pylori",
            "endoscopy", "postprandial", "lying", "nocturnal", "regurgitation",
        ],
        "acceptable_discriminating_q": [
            "heartburn", "acid", "regurgitation", "antacid", "lying",
            "nocturnal", "postprandial", "meal",
        ],
        "expected_enriched_leads": ["gord", "reflux", "gastro-oesophageal"],
        "is_negative_case": False,
    },
    "d2": {
        "label": "Lower abdominal overlap — UTI / AGE",
        "presentation": (
            "F/26. Fever x2/7, nausea, lower abdominal pain and cramping. "
            "Weakness. No urinary symptoms volunteered."
        ),
        "acceptable_leads": [
            "Urinary tract infection",
            "Acute gastroenteritis (infectious)",
        ],
        "acceptable_differentials": [
            "Urinary tract infection",
            "Acute gastroenteritis (infectious)",
        ],
        "acceptable_confidence_range": ["moderate"],
        "documented_red_flags": [],
        "check_for_red_flags": ["dehydration", "blood", "sepsis"],
        "required_supporting_features": ["fever", "abdominal", "nausea"],
        "expected_arguing_against_kw": [],
        "relevant_missing_information": [
            "dysuria", "frequency", "urinary", "diarrhoea", "vomiting",
            "dipstick", "urine", "culture", "MC&S", "haematuria",
        ],
        "acceptable_discriminating_q": [
            "dysuria", "frequency", "urinary", "diarrhoea", "vomiting", "stool",
        ],
        "expected_enriched_leads": ["uti", "urinary"],
        "is_negative_case": False,
    },
    "d3": {
        "label": "Early undifferentiated fever — Malaria / Dengue",
        "presentation": (
            "M/28. Fever x2/7, severe headache, malaise, myalgia. "
            "Lives in Mombasa coastal area. No rash. No cough. No abdominal pain."
        ),
        "acceptable_leads": [
            "Malaria (unspecified)",
            "Dengue fever",
        ],
        "acceptable_differentials": [
            "Malaria (unspecified)",
            "Dengue fever",
            "Typhoid fever",
        ],
        "acceptable_confidence_range": ["moderate", "high"],
        "documented_red_flags": [],
        "check_for_red_flags": ["consciousness", "anaemia", "cerebral", "respiratory"],
        "required_supporting_features": ["fever", "headache", "myalgia", "malaise"],
        "expected_arguing_against_kw": [],
        "relevant_missing_information": [
            "RDT", "rapid diagnostic", "retro-orbital", "retro orbital",
            "rigors", "chills", "platelet", "NS1", "rash",
        ],
        "acceptable_discriminating_q": [
            "retro-orbital", "retro orbital", "rigors", "chills",
            "rash", "RDT", "test", "diagnostic",
        ],
        "expected_enriched_leads": ["dengue"],
        "is_negative_case": False,
    },
    "d4": {
        "label": "Negative — Diabetes full triad (disambiguation must not fire)",
        "presentation": (
            "51M, months of fatigue, very thirsty all the time, urinating a lot more "
            "than usual. Blurred vision sometimes. No fever, no acute illness."
        ),
        "acceptable_leads": [
            "Type 2 diabetes mellitus",
        ],
        "acceptable_differentials": [
            "Type 2 diabetes mellitus",
        ],
        "acceptable_confidence_range": ["high"],
        "documented_red_flags": [],
        "check_for_red_flags": ["hyperglycaemic", "hyperosmolar"],
        "required_supporting_features": ["thirst", "polyuria", "fatigue", "blurred"],
        "expected_arguing_against_kw": [],
        "relevant_missing_information": [
            "glucose", "HbA1c", "fasting", "family history", "BMI", "weight",
        ],
        "acceptable_discriminating_q": [],  # negative case — no questions expected
        "expected_enriched_leads": [],
        "is_negative_case": True,
    },
    "d5": {
        "label": "Fever in endemic area — Malaria / Typhoid",
        "presentation": (
            "M/32. Fever x4/7, headache, anorexia, mild abdominal discomfort. "
            "Lives in Kisumu. No rash. No rigors. No cough. No diarrhoea."
        ),
        "acceptable_leads": [
            "Malaria (unspecified)",
            "Typhoid fever",
        ],
        "acceptable_differentials": [
            "Malaria (unspecified)",
            "Typhoid fever",
        ],
        "acceptable_confidence_range": ["moderate", "high"],
        "documented_red_flags": [],
        "check_for_red_flags": ["intestinal perforation", "haemorrhage", "encephalopathy", "sepsis"],
        "required_supporting_features": ["fever", "headache", "anorexia", "abdominal"],
        "expected_arguing_against_kw": ["diarrhoea", "diarrhea"],
        "relevant_missing_information": [
            "RDT", "blood culture", "step-wise", "stepwise", "bradycardia",
            "Widal", "rigors", "chills", "fever pattern",
        ],
        "acceptable_discriminating_q": [
            "RDT", "malaria test", "blood culture", "rigors", "chills",
            "step-wise", "bradycardia", "fever pattern",
        ],
        "expected_enriched_leads": ["typhoid"],
        "is_negative_case": False,
    },
}


# ── Helpers ───────────────────────────────────────────────────────────────────

_CONF_ORDER = {"low": 0, "moderate": 1, "high": 2}


def _get_leading_candidate(result):
    lead_name = result.get("leading_candidate", "")
    for c in result.get("candidates", []):
        if c.get("diagnosis") == lead_name:
            return c
    return {}


# ── Deterministic scorers ─────────────────────────────────────────────────────

def score_leading_diagnosis(result, expected, provider=None):
    lead = result.get("leading_candidate", "").strip()
    acceptable = [a.lower() for a in expected.get("acceptable_leads", [])]

    if any(a in lead.lower() or lead.lower() in a for a in acceptable):
        return {"score": 2, "justification": f"'{lead}' matches acceptable leads."}

    # Acceptable condition present somewhere in differential
    candidate_names = [c.get("diagnosis", "").lower() for c in result.get("candidates", [])]
    if any(any(a in n or n in a for a in acceptable) for n in candidate_names):
        return {
            "score": 1,
            "justification": f"'{lead}' not expected as lead; acceptable diagnoses present in differential.",
        }

    return {
        "score": 0,
        "justification": f"'{lead}' not expected; acceptable diagnoses absent from differential entirely.",
    }


def score_differential_relevance(result, expected, provider=None):
    candidate_names = [c.get("diagnosis", "").lower() for c in result.get("candidates", [])]
    acceptable = [a.lower() for a in expected.get("acceptable_differentials", [])]

    if not acceptable:
        return {"score": 2, "justification": "No expected differentials specified."}

    hits = sum(
        1 for a in acceptable
        if any(a in n or n in a for n in candidate_names)
    )

    if hits == len(acceptable):
        return {"score": 2, "justification": f"All {len(acceptable)} expected differentials present."}
    if hits >= max(1, len(acceptable) // 2):
        return {"score": 1, "justification": f"{hits}/{len(acceptable)} expected differentials present."}
    return {"score": 0, "justification": f"Only {hits}/{len(acceptable)} expected differentials in candidates."}


def score_confidence_range(result, expected, provider=None):
    lead = _get_leading_candidate(result)
    conf = lead.get("confidence_level", "")
    acceptable = expected.get("acceptable_confidence_range", [])

    if conf in acceptable:
        return {"score": 2, "justification": f"Confidence '{conf}' within acceptable range {acceptable}."}

    conf_idx = _CONF_ORDER.get(conf, -1)
    acceptable_idxs = [_CONF_ORDER.get(a, -1) for a in acceptable]
    if any(abs(conf_idx - ai) == 1 for ai in acceptable_idxs):
        return {
            "score": 1,
            "justification": f"Confidence '{conf}' adjacent to acceptable range {acceptable}.",
        }

    return {"score": 0, "justification": f"Confidence '{conf}' outside acceptable range {acceptable}."}


def score_red_flags(result, expected, provider=None):
    red_flags = result.get("red_flags", [])
    rf_text = " ".join(red_flags).lower()

    documented = expected.get("documented_red_flags", [])
    check_for  = expected.get("check_for_red_flags", [])

    if not documented and not check_for:
        return {"score": 2, "justification": "No required red flags for this case."}

    if not red_flags:
        return {"score": 0, "justification": "No red flags listed; at least one entry expected."}

    # Documented flags must appear as "Documented —" entries, not "Check for —"
    # Use startswith to avoid matching "Not documented in the presentation."
    documented_ok = all(
        any(d.lower() in rf.lower() and rf.lower().startswith("documented") for rf in red_flags)
        for d in documented
    ) if documented else True

    # Check-for flags: at least half must be mentioned
    cf_hits = sum(1 for cf in check_for if cf.lower() in rf_text)
    cf_ok = not check_for or cf_hits >= max(1, len(check_for) // 2)

    if documented_ok and cf_ok:
        return {
            "score": 2,
            "justification": f"Documented flags correct; {cf_hits}/{len(check_for)} check-for items present.",
        }
    if documented_ok or cf_hits > 0:
        return {
            "score": 1,
            "justification": f"Partial coverage — documented_ok={documented_ok}, {cf_hits}/{len(check_for)} check-for.",
        }
    return {"score": 0, "justification": "Red flags listed but none match required items."}


deterministic_scorers = {
    "leading_diagnosis":      score_leading_diagnosis,
    "differential_relevance": score_differential_relevance,
    "confidence_range":       score_confidence_range,
    "red_flags":              score_red_flags,
}


# ── LLM judge ─────────────────────────────────────────────────────────────────

JUDGE_SYSTEM_PROMPT = """You are a clinical accuracy scorer for a diagnostic AI evaluation.

Your role is to score model output against a reference standard. You are not the clinician — you score only what is present or absent relative to the expected answers provided.

Rules:
- Score 0, 1, or 2 only.
- 2 = correct and clinically appropriate relative to expected answers
- 1 = partially correct or incomplete but not harmful
- 0 = incorrect, clinically unsafe, or contradicts the expected answers
- Fail closed: if you cannot determine the score, return 0.
- Do not score on style, verbosity, or clinical knowledge beyond the expected-answer set.
- Do not penalise the model for including additional correct information beyond what is listed.
- Penalise 0 for: listing a denied finding as supporting evidence; manufacturing arguing-against items not in the presentation; confusing "not documented" with "absent".

Arguing-against semantics: arguing_against items should represent denied or absent findings from
the patient's presentation (e.g. "No rash" → rash argues against dengue). Epidemiological priors
or demographic patterns (e.g. "male sex argues against UTI") are clinically relevant but are NOT
denied findings — score these as 1 (partial), not 0 or 2.

Return JSON only: {"score": <0, 1, or 2>, "justification": "<one sentence citing specific evidence>"}"""


def _call_judge(prompt, provider):
    """Call provider with judge system prompt. Return scored dict. Fail closed on any error."""
    try:
        raw = provider.generate(JUDGE_SYSTEM_PROMPT, prompt)
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            parts = cleaned.split("```")
            cleaned = parts[1] if len(parts) > 1 else cleaned
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        data = json.loads(cleaned.strip())
        score = int(data["score"])
        if score not in (0, 1, 2):
            return {"score": 0, "justification": f"Judge returned invalid score {score}; failing closed."}
        return {"score": score, "justification": str(data.get("justification", ""))}
    except Exception as e:
        return {"score": 0, "justification": f"Judge call failed ({e}); failing closed."}


# ── Judge scorers ─────────────────────────────────────────────────────────────

def judge_supporting_features(result, expected, provider=None):
    if provider is None:
        return {"score": 0, "justification": "No provider; failing closed."}

    lead = _get_leading_candidate(result)
    lead_name = result.get("leading_candidate", "?")
    actual = lead.get("supporting_features", [])
    required_kw = expected.get("required_supporting_features", [])
    presentation = expected.get("presentation", "")

    prompt = f"""Score the supporting features for the leading candidate.

Patient presentation: {presentation}

Expected feature keywords (at least most should appear): {required_kw}
Leading candidate: {lead_name}
Model supporting features: {json.dumps(actual, ensure_ascii=False)}

Score 2 if most expected keywords are represented and no denied finding is listed.
Score 1 if some expected keywords are present but key ones are missing.
Score 0 if expected features are largely absent, or a finding denied in the presentation is listed as supporting evidence."""

    return _call_judge(prompt, provider)


def judge_arguing_against_accuracy(result, expected, provider=None):
    if provider is None:
        return {"score": 0, "justification": "No provider; failing closed."}

    lead_name = result.get("leading_candidate", "?")
    lead = _get_leading_candidate(result)
    actual_lead_aa = lead.get("arguing_against", [])
    all_aa = {c.get("diagnosis", ""): c.get("arguing_against", []) for c in result.get("candidates", [])}
    expected_kw = expected.get("expected_arguing_against_kw", [])
    presentation = expected.get("presentation", "")

    prompt = f"""Score the arguing-against accuracy across all candidates.

Patient presentation: {presentation}

Expected arguing-against keywords (denied or absent findings from the presentation that should appear in arguing_against lists): {expected_kw}
Leading candidate ({lead_name}) arguing_against: {json.dumps(actual_lead_aa, ensure_ascii=False)}
All candidates arguing_against: {json.dumps(all_aa, ensure_ascii=False)}

Score 2 if: arguing-against items reflect denied or absent findings from the patient presentation; expected keywords appear where clinically appropriate; no manufactured items.
Score 1 if: mostly correct but missing some expected items; OR the model uses epidemiological priors / demographic patterns instead of denied findings (e.g. 'male sex argues against UTI' — clinically relevant but not a denied finding from this presentation).
Score 0 if: items are manufactured (a finding not mentioned or denied in the presentation is claimed as evidence), or a finding present in the presentation is listed as arguing-against it."""

    return _call_judge(prompt, provider)


def judge_missing_information_relevance(result, expected, provider=None):
    if provider is None:
        return {"score": 0, "justification": "No provider; failing closed."}

    lead_name = result.get("leading_candidate", "?")
    # Assess discriminatory usefulness across ALL candidates — the union drives question quality
    all_missing = {
        c.get("diagnosis", "?"): c.get("missing_information", [])
        for c in result.get("candidates", [])
    }
    relevant_kw = expected.get("relevant_missing_information", [])

    prompt = f"""Score the missing information relevance across all candidates.

Expected clinically relevant keywords (items that help discriminate between the candidates): {relevant_kw}
Leading candidate: {lead_name}
Model missing information per candidate: {json.dumps(all_missing, ensure_ascii=False)}

Score 2 if: relevant discriminating items appear across the candidates' missing information lists; the model identifies what would help confirm or distinguish between the leading and differential diagnoses.
Score 1 if: some relevant items appear but key discriminators are missing, or only generic non-discriminating questions dominate.
Score 0 if: relevant discriminating items are absent across all candidates, or items are clinically inappropriate for this presentation."""

    return _call_judge(prompt, provider)


def judge_question_quality(result, expected, provider=None):
    """Extracts discriminating questions from result internally; scores their clinical usefulness."""
    from disambiguate import get_discriminating_questions, is_ambiguous

    if provider is None:
        return {"score": 0, "justification": "No provider; failing closed."}

    if expected.get("is_negative_case"):
        questions = get_discriminating_questions(result)
        if not questions:
            return {"score": 2, "justification": "Negative case: no questions expected; none generated."}
        return {"score": 0, "justification": f"Negative case: no questions expected; {len(questions)} generated."}

    questions = get_discriminating_questions(result)
    acceptable_kw = expected.get("acceptable_discriminating_q", [])

    if not questions:
        if not is_ambiguous(result):
            return {"score": None, "justification": "N/A — ambiguity did not fire; question quality not applicable."}
        return {"score": 0, "justification": "Ambiguity detected but no discriminating questions generated."}

    prompt = f"""Score the discriminating question quality for this case.

Acceptable discriminating question keywords (at least some should appear): {acceptable_kw}
Model discriminating questions (from missing_information set-difference across tied candidates): {json.dumps(questions, ensure_ascii=False)}

Score 2 if questions include key discriminators from the acceptable list and would clinically help narrow the differential.
Score 1 if questions are partially relevant but miss important discriminators or include non-discriminating items.
Score 0 if questions would not help distinguish the tied candidates, or are clinically irrelevant to this presentation."""

    return _call_judge(prompt, provider)


judge_scorers = {
    "supporting_features":           judge_supporting_features,
    "arguing_against_accuracy":       judge_arguing_against_accuracy,
    "missing_information_relevance":  judge_missing_information_relevance,
    "question_quality":               judge_question_quality,
}
