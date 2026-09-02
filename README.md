# CDS — Clinical Decision Support

Symptom-driven diagnostic RAG system for East Africa / Kenya primary care. Given a patient presentation, returns candidate diagnoses with differentials, discriminating features, and red flags — a reasoning aid, not a single-answer lookup.

---

## Current state

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Corpus — 10 condition cards authored | ✅ Done |
| 2 | Graph extraction + vocabulary normalization | ✅ Done |
| 3 | Neo4j load — 10 conditions in AuraDB | ✅ Done |
| 4 | Vector store — Chroma + Cohere embeddings | ✅ Done |
| 5 | RAG pipeline — graph + vector → Gemini | ✅ Done (7/8 eval) |
| 5e | Pipeline orchestration — Makefile + GitHub Actions | ✅ Done |
| 6 | UI — Streamlit MVP | ✅ Done |
| 6b | UI improvement + approval → database write | 🟡 In progress |
| 7 | Corpus v2 — expand to 20+ conditions | 🔴 Planned |
| ∞ | Longitudinal inference — patient history + second assessment | 🔴 Planned (Afya Chat 2.0) |

**Eval baseline:** 7/8 cases auto-pass. Case 2b (TB leads for 3-day cough) is a confirmed model reasoning limit, not a retrieval problem.

**Production gate:** All 10 cards remain `draft`. Clinician review required before production ingestion.

---

## Stack

```
symptoms_dictionary/*.md      ← condition cards (source of truth)
        │
        ▼
    ingest.py                 ← dual-output ingestion pipeline
        │
        ├──► chunks.jsonl     ── prose chunks (section-level)
        │         │
        │         ▼
        │    chroma/chroma_loader.py  ── Cohere embed → Chroma vector store
        │
        └──► graph_entities.jsonl ── normalized graph declarations
                  │
                  ▼
             neo4j/neo4j_loader.py  ── Cypher MERGE → Neo4j AuraDB

Patient presentation
    → Cohere embed → Chroma (top 6 candidate conditions)
    → Neo4j (symptom profiles + argues_against per candidate)
    → Cohere embed → Chroma (top 5 prose passages per candidate)
    → Gemini gemini-flash-lite (temperature=0, JSON schema enforced)
    → jsonschema validate → structured differential assessment
```

**Embedding:** Cohere `embed-multilingual-v3.0`
**LLM:** Gemini `gemini-flash-lite-latest` (Anthropic Claude fallback)
**Graph:** Neo4j AuraDB free tier

---

## Directory

```
cds/
├── Makefile                          pipeline entry point
├── ingest.py                         dual-output ingestion pipeline
├── report_unknowns.py                vocabulary gap analysis
├── requirements.txt
├── symptoms_dictionary/
│   ├── index.md                      condition index (ICD-11 + ICD-10 + filenames)
│   ├── glossary.md                   shared clinical term definitions (24 terms)
│   ├── symptom_vocabulary.md         canonical symptom/sign/risk term list
│   ├── conditions_vocabulary.md      canonical condition names (for differentials)
│   └── *.md                          10 condition cards
├── neo4j/
│   ├── migrations/001_initial_schema.cypher
│   ├── neo4j_loader.py               loads graph_entities.jsonl → AuraDB
│   └── run_queries.py                dev verification queries
├── chroma/
│   ├── chroma_loader.py              embeds chunks.jsonl → Chroma
│   ├── retrieval_baseline.md         baseline retrieval results (8 cases)
│   └── evaluation_contract.md        pass/fail criteria for all 8 eval cases
├── phase5/
│   ├── rag.py                        RAG orchestrator (5-step pipeline)
│   ├── prompts.py                    system prompt + OUTPUT_SCHEMA + build_context()
│   ├── providers.py                  GeminiProvider + AnthropicProvider
│   ├── evaluate.py                   8-case evaluation harness
│   ├── embed_provider.py             CohereEmbedder + PubMedBertEmbedder
│   ├── bm25_index.py                 BM25 sparse index (--hybrid flag, not default)
│   └── tests/                        pytest suite (100 tests)
└── .github/workflows/
    └── cds_pipeline.yml              CI — triggers on card/pipeline changes
```

---

## Running the pipeline

```bash
# Full pipeline — ingest → load Neo4j → embed → evaluate (gate: ≥ 7/8)
make pipeline

# Individual stages
make ingest        # parse cards → chunks.jsonl + graph_entities.jsonl
make load-neo4j    # load graph_entities.jsonl → Neo4j AuraDB
make embed         # embed chunks.jsonl → Chroma vector store
make eval          # run 8-case evaluation harness

# Single query
python phase5/rag.py "45F, 3 weeks cough, night sweats, weight loss"

# Evaluation — specific cases
python phase5/evaluate.py 2a 2b

# Vocabulary gap check (after adding new cards)
python report_unknowns.py
```

Credentials are loaded from `.env` (local) or environment variables (CI). See `.env.example` if present.

---

## Condition cards

Each card is a `.md` file with YAML frontmatter and 9 fixed prose sections.

**Frontmatter (schema v1.2):**
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

## Conditions (10 cards, corpus v1.2)

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
| Peptic Ulcer Disease | DA60 | K27 |
| Acute Gastroenteritis (Infectious) | 1A09 | A09 |

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
