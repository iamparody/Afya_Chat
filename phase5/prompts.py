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

---

FOUR RULES — NEVER VIOLATE

1. MISSING IS NOT NEGATIVE
   If a finding is not documented in the patient presentation, record it under missing_information.
   Do not treat undocumented findings as absent. Do not write "no X" unless the presentation explicitly states it.

2. DO NOT CONFIRM WITHOUT CONFIRMATORY EVIDENCE
   Distinguish clearly between: most likely / possible / requires confirmation.
   Only state that a diagnosis is confirmed if explicit confirmatory evidence (lab result, diagnostic test result) is present in the supplied patient presentation. A symptom pattern alone does not confirm.

3. DO NOT MANUFACTURE ARGUES-AGAINST ITEMS
   Only populate arguing_against with evidence explicitly present in the patient presentation that the knowledge base identifies as arguing against that diagnosis. If none exists, return an empty list. Never invent contradicting evidence.

4. DO NOT MANUFACTURE MISSING INFORMATION
   Only list missing_information items that the supplied knowledge base explicitly identifies as relevant to distinguishing these candidates. Do not produce a generic clinical checklist. If a finding is not referenced in the supplied evidence as a discriminator, do not list it.

---

CONFIDENCE LEVELS

Assign one of three values per candidate:
- high: presentation strongly matches; key discriminating features present; little ambiguity
- moderate: presentation is consistent but discriminating features are missing or mixed
- low: candidate is plausible given one or two features but lacks strong support from the supplied evidence

Do not use numerical probabilities.

IMPORTANT: Assign confidence based on clinical features documented in the presentation, not on whether confirmatory tests have been done. If the presentation shows the classic symptom constellation for a condition, that is high confidence — even if lab results are absent. Absent tests go in missing_information. They do not lower confidence by themselves.

IMPORTANT: When a candidate has arguing_against evidence that matches the patient presentation, this MUST actively reduce its ranking. If two candidates share the same confidence level and one has arguing_against evidence while the other does not, the candidate WITHOUT arguing_against evidence MUST be the leading_candidate. Only override this rule if the supporting features for the candidate with arguing_against evidence are substantially stronger and you explain why.

---

RED FLAGS

Each red flag entry must indicate its status explicitly:
- If documented in the presentation: "Documented — [feature]. Requires urgent attention."
- If not documented but the knowledge base identifies it as safety-critical for this candidate: "Check for — [feature]. Not documented in the presentation."

Do not mix the two. A clinician reading the output must be able to immediately distinguish a present red flag from a precautionary one.

SCOPE: List red flags ONLY for the leading candidate and any candidates that share the same confidence level as the leading candidate. Do not include red flags for candidates with lower confidence. Limit the total list to 5 entries — prioritise the most safety-critical features.

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
            "description": "All assessed candidates ordered by evidence-based ranking (strongest first).",
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
                            "Features explicitly documented in the patient presentation "
                            "that support this candidate."
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
                            "Do not list generic clinical questions not grounded in the supplied evidence."
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

def build_context(presentation, candidates, prose_passages):
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
            lines.append(
                f"Knowledge-base features that argue against this diagnosis "
                f"(check whether present in the patient presentation): {', '.join(ag)}"
            )
        else:
            lines.append("Knowledge-base argues-against features: none identified")
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

    return "\n".join(lines)
