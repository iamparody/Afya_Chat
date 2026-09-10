# CDS — Clinical Decision Support

Symptom-driven diagnostic RAG system for East Africa / Kenya primary care. Given a patient presentation, returns candidate diagnoses with differentials, discriminating features, and red flags — a reasoning aid, not a single-answer lookup.

---

## Current state

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Corpus — 15 condition cards authored | ✅ Done (all draft) |
| 2 | Clinician review — all 15 cards | 🔴 Not started — production gate |
| 3 | Ingestion pipeline → Chroma vector store | ✅ Done |
| 4 | Neo4j knowledge graph — 15 conditions | ✅ Done |
| 5 | RAG pipeline — Gemini + SEVEN RULES prompt | ✅ Done (8/8 eval) |
| 6 | Streamlit MVP + approval workflow + SQLite | ✅ Done |
| 6b | UI improvement (Step 7 — session history sidebar pending) | 🟡 In progress |
| 7 | Environmental context layer — static calendar + ENSO | ✅ Done |
| 8 | Interactive disambiguation loop — follow-up question generation | ✅ Done (CI-gated 4/5) |
| 8b | Reasoning evaluation harness — 10-dim rubric + CI | ✅ Done (87/96, 90%) |
| 9 | Live environmental feeds — CHIRPS / Kenya Met API | 🔴 Planned |

**Eval baseline:** 8/8 RAG cases. 87/96 (90%) reasoning evaluation. 4/5 disambiguation gate.

**Production gate:** All 15 cards remain `draft`. Clinician review required before production ingestion.

---

## Stack

```
symptoms_dictionary/*.md (15 condition cards, schema 2.1)
        │
        ▼
    ingest.py  ← section-level chunking + environmental signal validation
        │
        ├──► chunks.jsonl ──► chroma/chroma_loader.py ── Cohere embed → Chroma
        └──► graph_entities.jsonl ──► neo4j/neo4j_loader.py ── Cypher MERGE → Neo4j AuraDB

Patient presentation
    → Cohere embed → Chroma (top 6 candidate conditions)
    → Neo4j (symptom profiles + argues_against per candidate)
    → Cohere embed → Chroma (top 5 prose passages per candidate)
    → Environmental context engine (static calendar + ENSO flag → labelled prior evidence)
    → Gemini (SEVEN RULES, temperature=0, JSON schema enforced)
    → jsonschema validate → structured differential assessment
    → Disambiguation loop (tied candidates → discriminating questions → enriched re-run)
    → Streamlit UI (approval workflow → SQLite encounters)
```

**Embedding:** Cohere `embed-multilingual-v3.0`
**LLM:** Gemini `gemini-2.0-flash` (temperature=0)
**Graph:** Neo4j AuraDB free tier

---

## Directory

```
cds/
├── Makefile                          pipeline entry point (6 targets)
├── ingest.py                         dual-output ingestion pipeline (schema 2.1)
├── requirements.txt
├── symptoms_dictionary/
│   ├── index.md                      condition index (ICD-11 + ICD-10 + filenames)
│   ├── glossary.md                   shared clinical term definitions
│   ├── symptom_vocabulary.md         canonical symptom/sign/risk term list
│   ├── conditions_vocabulary.md      canonical condition names (for differentials)
│   └── *.md                          15 condition cards
├── neo4j/
│   ├── migrations/001_initial_schema.cypher
│   └── neo4j_loader.py               loads graph_entities.jsonl → AuraDB
├── chroma/
│   └── chroma_loader.py              embeds chunks.jsonl → Chroma
├── phase5/
│   ├── rag.py                        RAG orchestrator + environmental context injection
│   ├── prompts.py                    SEVEN RULES system prompt + OUTPUT_SCHEMA + build_context()
│   ├── providers.py                  GeminiProvider (retry) + AnthropicProvider fallback
│   └── evaluate.py                   8-case RAG evaluation harness (gate ≥7/8)
├── phase6/
│   ├── app.py                        Streamlit MVP — presentation → RAG → approval → SQLite
│   ├── db.py                         SQLite encounters persistence + analyst schema
│   └── cds_theme.py                  CSS design tokens + Phosphor icon helpers
├── phase7/
│   ├── context_engine.py             environmental context engine (static calendar + ENSO)
│   └── tests/                        context engine + prompt injection tests (22 pass)
├── phase8/
│   ├── disambiguate.py               is_ambiguous(), get_discriminating_questions(), enrich_presentation()
│   ├── evaluate_disambiguation.py    5-case disambiguation eval (gate ≥4/5)
│   ├── rubric.py                     10-dim reasoning rubric (deterministic + LLM judge)
│   └── evaluate_reasoning.py         reasoning eval harness (gate 90% deterministic, judge as artifact)
└── .github/workflows/
    └── cds_pipeline.yml              CI — ingest → Neo4j → embed → RAG eval → disam eval → reasoning eval
```

---

## Running the pipeline

```bash
# Full pipeline — ingest → Neo4j → embed → RAG eval → disam eval → reasoning eval
make pipeline

# Individual stages
make ingest           # parse cards → chunks.jsonl + graph_entities.jsonl
make load-neo4j       # load graph_entities.jsonl → Neo4j AuraDB
make embed            # embed chunks.jsonl → Chroma vector store
make eval             # 8-case RAG evaluation harness (gate ≥7/8)
make eval-disam       # 5-case disambiguation eval (gate ≥4/5)
make eval-reasoning   # 10-dim reasoning eval, deterministic gate 90% (judge output as CI artifact)

# Single query
python phase5/rag.py "45F, 3 weeks cough, night sweats, weight loss"

# Reasoning evaluation — specific cases, or with LLM judge
python phase8/evaluate_reasoning.py d1 d3
python phase8/evaluate_reasoning.py --no-judge   # deterministic dims only
```

Credentials are loaded from `.env` (local) or environment variables (CI). See `.env.example` if present.

---

## Condition cards

Each card is a `.md` file with YAML frontmatter and 9 fixed prose sections.

**Frontmatter (schema v2.1):**
```yaml
condition:       canonical condition name
icd11:           WHO ICD-11 code
icd10:           ICD-10 code
category:        disease category
corpus_version:  increment on clinical content change
schema_version:  increment on frontmatter structure change
review_status:   draft | under_review | clinician_verified
reviewed_by:     clinician name + credential
last_reviewed:   YYYY-MM-DD
sources:
  - organization: WHO
    title: Guidelines for Malaria
    year: "2023"
graph:
  cardinal_symptoms:   [fever, chills, rigors]
  associated_symptoms: [myalgia, splenomegaly]
  risk_factors:        [endemic area residence, pregnancy]
  differentials:       [typhoid fever, dengue fever]
  argues_against:      [no endemic area exposure]
  red_flags:           [altered consciousness, coma]
  confirms:            [positive malaria RDT, positive thick blood film]
```

**9 prose sections (fixed order — parser depends on it):**

| # | Section |
|---|---------|
| 1 | Cardinal symptoms |
| 2 | Associated symptoms and signs |
| 3 | Diagnostic features |
| 4 | Predisposing factors |
| 5 | Typical presentation |
| 6 | Important differential diagnoses |
| 7 | Features that argue against this diagnosis |
| 8 | Red flags |
| 9 | Diagnostic context |

---

## RAG output schema

Every query returns a validated JSON object:

```json
{
  "leading_candidate": "Malaria (unspecified)",
  "candidates": [
    {
      "diagnosis": "Malaria (unspecified)",
      "confidence_level": "high",
      "why_considered": "...",
      "supporting_features": ["fever", "chills", "Kisumu travel"],
      "arguing_against": [],
      "missing_information": ["RDT result", "blood film"]
    }
  ],
  "red_flags": [
    "Check for — altered consciousness. Not documented in the presentation."
  ],
  "relevant_comorbidities_or_context": []
}
```

Confidence levels: `high` / `moderate` / `low`. No numerical probabilities.

---

## Conditions (15 cards, all draft)

| Condition | ICD-11 | ICD-10 |
|-----------|--------|--------|
| Type 2 Diabetes Mellitus | 5A11 | E11 |
| Essential Hypertension | BA00 | I10 |
| Obesity | 5B81 | E66 |
| Malaria (unspecified) | 1F40 | B54 |
| Pulmonary Tuberculosis | 1B10 | A15 |
| Community-Acquired Pneumonia | CA40 | J18 |
| Urinary Tract Infection | GC08 | N39.0 |
| Iron Deficiency Anaemia | 3A00 | D50 |
| Peptic Ulcer Disease | DA62 | K27 |
| Acute Gastroenteritis (Infectious) | 1A09 | A09 |
| Typhoid Fever | 1A07 | A01.0 |
| Functional Dyspepsia | DA94 | K30 |
| Gastro-oesophageal Reflux Disease | DA22 | K21 |
| Asthma | CA23 | J45 |
| Dengue Fever | 1D2Z | A90 |

---

## Clinical governance

```
draft → under_review → clinician_verified
```

- `draft` — authored, not reviewed; blocked from production ingestion
- `under_review` — sent to clinician
- `clinician_verified` — reviewed and approved; production-ready

`ingest.py` warns on draft cards. Only `clinician_verified` cards enter production.

**Sources:** WHO guidelines, Kenya MOH, Kenya NLTP, British Thoracic Society, ADA, ISH.
**Regional orientation:** East Africa / Kenya primary care.
