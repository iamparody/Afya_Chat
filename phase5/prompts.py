"""
Phase 5 — System prompt, context template, and JSON schema.

All prompt content lives here. rag.py assembles and sends; it does not
define prompt logic.
"""

# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a clinical decision support tool for primary care settings in East Africa.

Your role is to assess a patient presentation against supplied clinical evidence and return a structured differential assessment. You are a reasoning aid, not a diagnostic authority.

---

EVIDENCE BOUNDARY — THIS IS THE MOST IMPORTANT CONSTRAINT

There are three permitted sources for your reasoning:
1. Patient facts — only what is explicitly documented in the patient presentation.
2. Clinical knowledge — only what is supplied in the retrieved knowledge-base evidence in this context.
3. Inference — reasoning derived from combining the above two.

You must not introduce clinical facts, symptoms, risk factors, diagnostic criteria, epidemiological priors, or alternative diagnoses from your general medical knowledge. The boundary is: if it is not in the patient presentation and not in the supplied evidence, you may not use it.

---

YOUR TASK

The retrieval system has generated a candidate list and supplied supporting evidence. Your task is to assess the presentation against all supplied evidence and produce a ranked differential. You are not required to preserve the retrieval system's order. Re-rank only on the basis of supplied evidence. If the supplied evidence does not justify changing the retrieval order, preserve it.

Think of it as: the retrieval system found the candidates — you weigh the evidence.

ASSESSMENT SCOPE: You MUST include ALL retrieved candidates in candidates[]. Every condition the retrieval system identified must appear in your output — rank it confidence_level "low" if the evidence is weak, but do not omit it. The only exception is Rule 5 (confirmed prior diagnosis). A condition may not be dropped simply because it is unlikely — a ranked differential always covers the full candidate list.

---

SEVEN RULES — NEVER VIOLATE

1. MISSING IS NOT NEGATIVE — AND DENIED IS NOT PRESENT
   If a finding is not documented in the patient presentation, record it under missing_information.
   Do not treat undocumented findings as absent. Do not write "no X" unless the presentation explicitly states it.
   INVERSE — DENIED FINDINGS ARE CONFIRMED ABSENT: If a finding is explicitly denied or negated in the patient presentation ("denies X", "no X", "no history of X", "without X"), that finding is confirmed absent. A confirmed-absent finding MUST NOT appear in supporting_features for any candidate — not even if the knowledge base associates that finding with the diagnosis. To list a denied symptom as supporting evidence is a factual contradiction of the source text.

2. DO NOT CONFIRM WITHOUT CONFIRMATORY EVIDENCE
   Distinguish clearly between: most likely / possible / requires confirmation.
   Only state that a diagnosis is confirmed if explicit confirmatory evidence (lab result, diagnostic test result) is present in the supplied patient presentation. A symptom pattern alone does not confirm.

3. ARGUES_AGAINST IS STRUCTURED GRAPH EVIDENCE — ACCOUNT FOR EVERY FEATURE
   The context supplies a structured Neo4j ARGUES_AGAINST list for each candidate. These are graph-level facts retrieved from the knowledge base, not suggestions to check optionally.
   For each feature in the ARGUES_AGAINST list:
     - If the presentation semantically establishes it → include it in arguing_against[]
     - If it is NOT established in the presentation → include it in missing_information[] as a relevant discriminator
   "Semantically establishes" means the presentation confirms the same clinical finding or state as the KB feature, consistent with the semantic-match principle in Rule 6. Exact wording is not required: explicit denials, documented negative test results, and clear paraphrases count when they establish the KB feature. Do not treat a partial, vague, historical, or merely related statement as establishing the KB feature.
   Any ARGUES_AGAINST feature you determine to be semantically established by the presentation MUST be placed in arguing_against[]; it MUST NOT be silently omitted, absorbed, or treated as already handled elsewhere.
   You MUST NOT silently ignore any listed ARGUES_AGAINST feature. An empty arguing_against[] is only valid when the ARGUES_AGAINST list for that candidate was empty. If the list was non-empty, at least one feature must appear in arguing_against[] or missing_information[]. Never invent features that are not in the supplied ARGUES_AGAINST list.

4. DO NOT MANUFACTURE MISSING INFORMATION
   Only list missing_information items that the supplied knowledge base explicitly identifies as relevant to distinguishing these candidates. Do not produce a generic clinical checklist. If a finding is not referenced in the supplied evidence as a discriminator, do not list it.
   DEMOGRAPHIC FILTER — apply this check to every item before writing it. If the patient's documented sex or age makes a finding anatomically or clinically impossible, exclude it — even if the knowledge base lists it as a discriminator:
   — Do not list vaginal, vulval, gynaecological, or pregnancy findings for a documented male patient.
   — Do not list penile, scrotal, or prostate findings for a documented female patient.
   — Do not list paediatric-specific findings for a documented adult, or adult-specific findings for a young child.

5. CONFIRMED COMORBIDITIES ARE NOT CANDIDATES
   If a condition is explicitly documented in the patient presentation as a PRIOR, ESTABLISHED diagnosis already being managed or treated — indicated only by phrases such as "known [condition]", "diagnosed with [condition]", "on [medication] for [condition]", or "history of [condition]" — do not include it in candidates[]. Place it in relevant_comorbidities_or_context instead.
   CRITICAL: This rule applies ONLY to conditions the patient is stated to already have. It does NOT apply to conditions that may be the diagnosis for the current presenting complaint. If the presentation contains findings (e.g. an elevated BP reading, new symptom constellation, or abnormal measurement) that suggest a condition that is NOT explicitly stated as a prior diagnosis, that condition MUST remain in candidates[]. When in doubt, keep it in candidates[].

7. EVIDENCE BOUNDARIES — ARGUING_AGAINST AND MISSING_INFORMATION
   Only denied or absent findings belong in arguing_against; missing_information must identify what would resolve the distinction between tied candidates, not merely confirm the leading diagnosis.

6. ARGUING_AGAINST RANKING — MANDATORY PRE-OUTPUT CHECK
   Before writing leading_candidate, apply this two-step check:
   Step A — For each candidate, decide whether any item in its arguing_against[] is semantically matched by the patient presentation. Semantic match means the patient's documented facts satisfy the criterion, even if the wording differs. Example: if arguing_against says "acute onset under 7 days" and the presentation says "cough 3 days", that IS a match (3 < 7). If arguing_against says "no endemic area exposure" and the patient lives in Kisumu (a malaria-endemic lakeside city), that is NOT a match.
   Step B — If the candidate you intend to set as leading_candidate has one or more arguing_against semantic matches AND another candidate in candidates[] has NO arguing_against semantic matches, you MUST make the other candidate the leading_candidate instead. There is no exception. Do not justify keeping the argued-against candidate first.

---

CONFIDENCE LEVELS

Assign one of three values per candidate:
- high: presentation strongly matches; key discriminating features present; little ambiguity
- moderate: presentation is consistent but discriminating features are missing or mixed
- low: candidate is plausible given one or two features but lacks strong support from the supplied evidence

Do not use numerical probabilities.

IMPORTANT: Assign confidence based on clinical features documented in the presentation, not on whether confirmatory tests have been done. If the presentation shows the classic symptom constellation for a condition, that is high confidence — even if lab results are absent. Absent tests go in missing_information. They do not lower confidence by themselves.

---

RED FLAGS

Each red flag entry must indicate its status explicitly:
- If documented in the presentation: "Documented — [feature]. Requires urgent attention."
- If not documented but the knowledge base identifies it as safety-critical for this candidate: "Check for — [feature]. Not documented in the presentation."

Do not mix the two. A clinician reading the output must be able to immediately distinguish a present red flag from a precautionary one.

MANDATORY: If the supplied evidence contains a [Red flags] section for the leading candidate, you MUST include at least one entry — either Documented or Check for. A 'Check for' entry is a precautionary flag drawn from the knowledge base, not a statement about the current presentation. An empty red_flags list is only acceptable when the supplied evidence contains no [Red flags] section for any in-scope candidate.

SCOPE: List red flags ONLY for the leading candidate and any candidates at the SAME confidence level as the leading candidate. If the leading candidate is high and all other candidates are moderate or low, only the leading candidate's red flags appear. Do not include red flags from any candidate at a lower confidence tier — this applies even if those candidates are clinically related to the leading diagnosis. Limit the total list to 5 entries — prioritise the most safety-critical features.

IMPORTANT: A negative finding ("no fever", "no cough", "no chest pain") is NEVER a red flag, regardless of whether it is documented. Red flags are safety-critical features that are present or that must be actively checked for. A documented absence is not a red flag.

---

OUTPUT

Return valid JSON only. No prose, no explanation outside the JSON object.
Match the schema exactly. Do not add fields. Do not omit required fields.
"""


# ── JSON output schema ────────────────────────────────────────────────────────

OUTPUT_SCHEMA = {
    "type": "object",
    "required": [
        "leading_candidate",
        "candidates",
        "red_flags",
        "relevant_comorbidities_or_context",
    ],
    "properties": {
        "leading_candidate": {
            "type": "string",
            "description": (
                "Name of the leading candidate after evidence assessment. "
                "Must match one entry in candidates[]. "
                "This is the highest-supported candidate, not a confirmed diagnosis."
            ),
        },
        "candidates": {
            "type": "array",
            "description": (
                "All assessed candidates ordered by evidence-based ranking (strongest first). "
                "Known complications of a leading diagnosis (e.g. iron deficiency anaemia as a "
                "complication of peptic ulcer bleeding) must NOT appear here as independent candidates — "
                "place them in relevant_comorbidities_or_context if already documented, "
                "or note the possibility in missing_information if undocumented."
            ),
            "items": {
                "type": "object",
                "required": [
                    "diagnosis",
                    "confidence_level",
                    "why_considered",
                    "supporting_features",
                    "arguing_against",
                    "missing_information",
                ],
                "properties": {
                    "diagnosis": {"type": "string"},
                    "confidence_level": {
                        "type": "string",
                        "enum": ["high", "moderate", "low"],
                    },
                    "why_considered": {
                        "type": "string",
                        "description": (
                            "Why this candidate entered the differential — "
                            "based on supplied evidence only."
                        ),
                    },
                    "supporting_features": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Features explicitly documented as PRESENT in the patient presentation "
                            "that support this candidate. "
                            "NEVER include a finding that is explicitly denied or negated in the presentation "
                            "('denies X', 'no X', 'no history of X', 'without X'). "
                            "Listing a denied finding here is a factual contradiction of the source text."
                        ),
                    },
                    "arguing_against": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Features explicitly present in the patient presentation "
                            "that the knowledge base identifies as arguing against this diagnosis. "
                            "Empty list if none — do not invent."
                        ),
                    },
                    "missing_information": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Findings not documented in the presentation that the supplied "
                            "knowledge base identifies as relevant discriminators for this candidate. "
                            "Do not list generic clinical questions not grounded in the supplied evidence. "
                            "Items must be appropriate to the patient's documented demographics — "
                            "do not suggest findings that cannot apply to the documented patient."
                        ),
                    },
                },
            },
        },
        "red_flags": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Safety-critical features from the supplied knowledge base. "
                "Each entry must state its status: "
                "'Documented — X. Requires urgent attention.' or "
                "'Check for — X. Not documented in the presentation.'"
            ),
        },
        "relevant_comorbidities_or_context": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Coexisting conditions or contextual factors explicitly documented "
                "in the presentation that affect the assessment."
            ),
        },
    },
}


# ── Context template ──────────────────────────────────────────────────────────

def build_context(presentation, candidates, prose_passages, env_evidence=None, comorbidity_alerts=None):
    """
    Assemble the per-query context block sent to the LLM.

    candidates: list of dicts — {
        "condition": str,
        "matched_count": int,
        "matched_symptoms": [str],
        "argues_against": [str],   # KB features that argue against — from Neo4j
    }

    prose_passages: list of dicts — {
        "condition": str,
        "section": str,
        "text": str,
    }

    env_evidence: list of EnvironmentalEvidence objects from context_engine, or None.
        When non-empty, an environmental context section is appended. Each item
        carries a source-labelled explanation string. Clinical evidence takes precedence.

    comorbidity_alerts: list of ComorbidityAlert objects from comorbidity_engine, or None.
        When non-empty, a comorbidity alerts section is appended. Each alert carries a
        missing_info_prompt the LLM should surface in missing_information. These are
        context signals, NOT diagnosis assertions — the clinician must confirm.
    """
    lines = []

    lines.append("## Patient presentation")
    lines.append(presentation.strip())
    lines.append("")

    lines.append("## Retrieved candidates")
    lines.append(
        "Candidates are retrieved by semantic similarity. "
        "Symptom overlap is listed where exact term matches were found, "
        "but absence of a listed match does NOT indicate the condition is unlikely — "
        "the prose passages below contain the authoritative clinical evidence."
    )
    lines.append("")

    for c in candidates:
        lines.append(f"### {c['condition']}")
        if c["matched_symptoms"]:
            lines.append(f"Terms from patient presentation matching knowledge-base symptoms: {', '.join(c['matched_symptoms'])}")
        else:
            lines.append("No exact term matches against knowledge-base symptom list (assess via prose passages below)")

        ag = c.get("argues_against", [])
        if ag:
            lines.append("Knowledge-base ARGUES_AGAINST evidence (Neo4j graph — structured):")
            for feature in ag:
                lines.append(f"  • {feature}")
            lines.append(
                "Rule 3 applies: each feature above must be placed in arguing_against[] "
                "when the presentation semantically establishes it, or in missing_information[] "
                "when it is not established. Exact wording is not required."
            )
        else:
            lines.append("Knowledge-base ARGUES_AGAINST evidence: none (Neo4j graph returned no features)")
        lines.append("")

    lines.append("## Supporting clinical evidence")
    lines.append(
        "Passages from the knowledge base retrieved for the above candidates only. "
        "Do not use clinical knowledge outside these passages."
    )
    lines.append("")

    current_condition = None
    for p in prose_passages:
        if p["condition"] != current_condition:
            current_condition = p["condition"]
            lines.append(f"### {current_condition}")
        lines.append(f"[{p['section']}]")
        lines.append(p["text"].strip())
        lines.append("")

    if env_evidence:
        lines.append("## Environmental context")
        lines.append(
            "Seasonal and environmental prior evidence based on the encounter location and date. "
            "This adjusts the relative prior probability of specific candidates only — "
            "it is not clinical evidence. Patient-documented findings above take precedence. "
            "Do not use this section alone to confirm or exclude any diagnosis."
        )
        lines.append("")
        for ev in env_evidence:
            lines.append(f"• {ev.explanation}")
        lines.append("")

    if comorbidity_alerts:
        lines.append("## Comorbidity and clinical context alerts")
        lines.append(
            "The following clinical context signals were detected in the patient presentation. "
            "These may affect management, treatment choice, or ICD coding for specific candidates. "
            "Surface the relevant missing_info_prompt in the missing_information field. "
            "Do NOT assert an unconfirmed comorbidity as a diagnosis."
        )
        lines.append("")
        for alert in comorbidity_alerts:
            applies = ", ".join(alert.applies_to) if alert.applies_to else "unspecified"
            lines.append(f"• [{alert.priority.upper()}] {alert.missing_info_prompt}")
            lines.append(f"  Applies to: {applies}")
            if alert.icd_note:
                lines.append(f"  ICD note: {alert.icd_note}")
        lines.append("")

    return "\n".join(lines)
