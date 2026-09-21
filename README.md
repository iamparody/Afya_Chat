# CDS — Clinical Decision Support

Symptom-driven diagnostic RAG system for East Africa / Kenya primary care. Given a patient presentation, returns candidate diagnoses with differentials, discriminating features, and red flags — a reasoning aid, not a single-answer lookup.

---

## Current state

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Corpus — 25 condition cards (YAML) | ✅ Done |
| 2 | Clinician review — 15 original cards verified | ✅ Done (10 new cards remain draft) |
| 3 | Ingestion pipeline → Chroma vector store | ✅ Done |
| 4 | Neo4j knowledge graph — 25 conditions | ✅ Done |
| 5 | RAG pipeline — Gemini + SEVEN RULES prompt | ✅ Done |
| 6 | Streamlit MVP + approval workflow + SQLite | ✅ Done |
| 7 | Environmental context layer — static calendar + ENSO + exposure gating | ✅ Done |
| 8 | Interactive disambiguation loop | ✅ Done (CI-gated 4/5) |
| 8b | Reasoning evaluation harness — 10-dim rubric + CI | ✅ Done (87/96, 90%) |
| 9 | Live rainfall — Open-Meteo provider + source validation | 🟡 Partial |

**Eval:** Regression 7/8 GATE PASS · Coverage 5/5 · 87/96 (90%) reasoning · 4/5 disambiguation.

**Production gate:** 15 original cards `clinician_verified`. 10 cards added post-review are `draft`. All `draft` cards are blocked from production ingestion.

---

## Stack

```
corpus/<condition>/condition.yaml  (22 condition cards, schema 2.2)
        │
        ▼
corpus_pipeline/ingest_yaml.py  ← chunking + graph extraction + vocab validation
        │
        ├──► chunks.jsonl ──► chroma/chroma_loader.py ── Cohere embed → Chroma (local)
        └──► graph_entities.jsonl ──► neo4j/neo4j_loader.py ── Cypher MERGE → Neo4j AuraDB

Patient presentation
    → Cohere embed → Chroma (top 6 candidate conditions)
    → Neo4j (symptom profiles + argues_against per candidate)
    → Cohere embed → Chroma (top 5 prose passages per candidate)
    → Environmental context engine
        ├── StaticCalendarProvider (signal activation — Kenya rainfall calendar)
        └── OpenMeteoProvider → RainfallFeatures (7/30/60d mm) → audit trail
    → Comorbidity engine (ASSOCIATED_WITH / COMPLICATED_BY / REQUIRES_CONTEXT alerts)
    → Gemini (SEVEN RULES, temperature=0, JSON schema enforced)
    → jsonschema validate → structured differential assessment
    → Disambiguation loop (tied candidates → discriminating questions → re-run)
    → Streamlit UI → approval → SQLite encounters
```

**Embedding:** Cohere `embed-multilingual-v3.0`
**LLM:** Gemini `gemini-2.0-flash` (temperature=0)
**Graph:** Neo4j AuraDB free tier
**Rainfall:** Open-Meteo Historical API (ERA5-Land, ~11km, no key required)

---

## Directory

```
cds/
├── Makefile                              pipeline entry point (6 targets)
├── CLAUDE.md                             governance + schema reference + controlled vocabularies
├── STATUS.md                             build tracker
├── corpus/                               22 condition cards (YAML)
│   ├── <condition>/condition.yaml        one file per condition
│   └── sources.yaml                      provenance registry (one entry per condition)
├── corpus_pipeline/
│   ├── ingest_yaml.py                    YAML ingestion → chunks.jsonl + graph_entities.jsonl
│   ├── validator.py                      pre-review automated checks (vocab, ICD, sections, graph)
│   ├── schema.py                         Pydantic models for condition.yaml
│   ├── diff.py                           artifact diff against reference outputs
│   └── output/                           chunks.jsonl + graph_entities.jsonl (build artifacts)
├── symptoms_dictionary/
│   ├── symptom_vocabulary.md             canonical symptom/sign/risk term list
│   ├── conditions_vocabulary.md          canonical condition names (for differentials)
│   ├── glossary.md                       shared clinical term definitions
│   └── index.md                          condition index (ICD-11 + ICD-10)
├── neo4j/
│   ├── migrations/                       numbered Cypher schema migrations
│   └── neo4j_loader.py                   loads graph_entities.jsonl → AuraDB
├── chroma/
│   └── chroma_loader.py                  embeds chunks.jsonl → Chroma
├── phase5/
│   ├── rag.py                            RAG orchestrator
│   ├── prompts.py                        SEVEN RULES prompt + OUTPUT_SCHEMA + build_context()
│   ├── providers.py                      GeminiProvider (retry) + AnthropicProvider fallback
│   └── evaluate.py                       RAG evaluation harness (regression + coverage cases)
├── phase6/
│   ├── app.py                            Streamlit MVP
│   ├── db.py                             SQLite encounters persistence
│   └── cds_theme.py                      CSS design tokens + Phosphor icons
├── phase7/
│   ├── context_engine.py                 environmental context engine
│   ├── comorbidity_engine.py             comorbidity alert engine
│   ├── kenya_locations.py                KNBS location normalization
│   └── rainfall_providers.py            RainfallProvider + OpenMeteoProvider
├── phase8/
│   ├── disambiguate.py                   disambiguation loop
│   ├── evaluate_disambiguation.py        5-case disambiguation eval
│   ├── rubric.py                         10-dim reasoning rubric
│   └── evaluate_reasoning.py            reasoning eval harness
├── phase9/
│   └── validation_findings.md           ERA5-Land vs CHIRPS source decision
├── docs/
│   └── domain_contracts/
│       └── acute_febrile_illness.md     AFI domain — condition inventory + pairwise matrix
└── .github/workflows/
    └── cds_pipeline.yml                  CI — ingest → Neo4j → embed → eval
```

---

## Running the pipeline

```bash
# Full pipeline — ingest → Neo4j → embed → RAG eval → disam eval → reasoning eval
make pipeline

# Individual stages
make ingest           # parse corpus/ → chunks.jsonl + graph_entities.jsonl
make load-neo4j       # load graph_entities.jsonl → Neo4j AuraDB
make embed            # embed chunks.jsonl → Chroma
make eval             # RAG evaluation (regression + coverage; gate ≥7/8 regression)
make eval-disam       # 5-case disambiguation eval (gate ≥4/5)
make eval-reasoning   # 10-dim reasoning eval, deterministic gate 90%

# Single query
python phase5/rag.py "45F, 3 weeks cough, night sweats, weight loss"

# Validate a new card before ingesting
python corpus_pipeline/validator.py corpus/<condition>/condition.yaml

# Run Streamlit app
streamlit run phase6/app.py
```

Credentials loaded from `.env` (local) or environment variables (CI).

---

## Condition cards

Each condition is a `condition.yaml` file with YAML frontmatter (schema 2.2) and 9 fixed prose sections.

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

## Corpus (25 conditions)

| Condition | ICD-11 | ICD-10 | Review |
|-----------|--------|--------|--------|
| Type 2 Diabetes Mellitus | 5A11 | E11 | ✅ verified |
| Essential Hypertension | BA00 | I10 | ✅ verified |
| Obesity | 5B81 | E66 | ✅ verified |
| Malaria (unspecified) | 1F40 | B54 | ✅ verified |
| Pulmonary Tuberculosis | 1B10 | A15 | ✅ verified |
| Community-Acquired Pneumonia | CA40 | J18 | ✅ verified |
| Urinary Tract Infection | GC08 | N39.0 | ✅ verified |
| Iron Deficiency Anaemia | 3A00 | D50 | ✅ verified |
| Peptic Ulcer Disease | DA61 | K27 | ✅ verified |
| Acute Gastroenteritis (Infectious) | 1A09 | A09 | ✅ verified |
| Typhoid Fever | 1A07 | A01.0 | ✅ verified |
| Functional Dyspepsia | DA94 | K30 | ✅ verified |
| Gastro-oesophageal Reflux Disease | DA22 | K21 | ✅ verified |
| Asthma | CA23 | J45 | ✅ verified |
| Dengue Fever | 1D2Z | A90 | ✅ verified |
| Cholera | — | A00.9 | 🟡 draft |
| Shigellosis (acute dysentery) | — | A03.9 | 🟡 draft |
| Intestinal Helminthiasis | — | B82.9 | 🟡 draft |
| Appendicitis | DC92 | K37 | 🟡 draft |
| Acute Viral Hepatitis A | 1E50.0 | B15.9 | 🟡 draft |
| Bacterial Meningitis | 1C1Z | G00.9 | 🟡 draft |
| Chikungunya | 1D67 | A92.0 | 🟡 draft |
| Brucellosis | 1B95 | A23.9 | 🟡 draft |
| Leptospirosis | 1B91 | A27.9 | 🟡 draft |
| Chronic Obstructive Pulmonary Disease | CA22.Z | J44.1 | 🟡 draft |

---

## Clinical governance

```
draft → under_review → clinician_verified
```

- `draft` — authored, not reviewed; blocked from production ingestion
- `under_review` — sent to clinician
- `clinician_verified` — reviewed and approved; production-ready

The validator (`corpus_pipeline/validator.py`) checks vocabulary, ICD format, section completeness, and graph terms before any card is ingested.

**Sources:** WHO guidelines, Kenya MOH Clinical Guidelines (2024), Kenya NLTP, WHO-AFRO.
**Regional orientation:** East Africa / Kenya primary care (Level 2–3).

---

## What remains

**Corpus expansion (AFI domain):**
- Brucellosis, Leptospirosis, Rickettsial illness — governance decision on acceptable sources required before authoring (see `docs/domain_contracts/acute_febrile_illness.md` §2.5)

**Phase 9 — rainfall thresholds:**
1. Historical ERA5-Land baseline per ecology (≥5 years)
2. Signal activation thresholds per ecology
3. Replace `StaticCalendarProvider` with observed-rainfall gating

**Clinician review:** 7 cards added after the 2026-09-14 review are `draft`. These need a second review pass before production ingestion.
