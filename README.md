# CDS — Clinical Decision Support

Symptom-driven diagnostic RAG system for East Africa / Kenya primary care. Given a patient presentation, returns candidate diagnoses with differentials, discriminating features, and red flags.

---

## Stack

```
symptoms_dictionary/*.md          ← condition cards (source of truth)
        │
        ▼
    ingest.py                     ← dual-output ingestion pipeline
        │
        ├──► chunks.jsonl         ── prose chunks → Chroma vector store (Phase 4)
        │
        └──► graph_entities.jsonl ── structured graph → Neo4j AuraDB (done)
```

**Retrieval (Phase 5):** Cypher traversal (graph) + semantic search (vector) → LLM synthesis → ranked diagnoses + clinical reasoning.

---

## Directory

```
cds/
├── ingest.py                         pipeline — run after any card edit
├── report_unknowns.py                vocabulary gap analysis tool
├── symptoms_dictionary/
│   ├── index.md                      condition index (ICD-11 + filenames)
│   ├── glossary.md                   shared clinical term definitions
│   ├── symptom_vocabulary.md         canonical symptom/sign/risk term list
│   ├── conditions_vocabulary.md      canonical condition names (for differentials)
│   └── *.md                          10 condition cards
└── neo4j/
    ├── migrations/001_initial_schema.cypher
    ├── neo4j_loader.py               loads graph_entities.jsonl → AuraDB
    └── run_queries.py                dev verification queries
```

---

## Condition cards

Each card is a `.md` file with YAML frontmatter and 9 fixed prose sections.

**Frontmatter:**
```yaml
condition:       canonical condition name
icd11:           WHO ICD-11 code
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

## Running the pipeline

```bash
# Regenerate both output files after any card edit
python ingest.py

# Load graph into Neo4j (requires .env with AuraDB credentials)
python neo4j/neo4j_loader.py

# Run verification queries
python neo4j/run_queries.py

# Check vocabulary gaps after adding new cards
python report_unknowns.py
```

---

## Clinical governance

```
draft → under_review → clinician_verified
```

- `draft` — authored, not reviewed; blocked from production ingestion
- `clinician_verified` — reviewed and approved; production-ready

**Production gate:** `ingest.py` warns on draft cards. Only `clinician_verified` cards enter production. All 10 current cards are `draft` — dev proceeds freely.

---

## Current state

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Corpus — 10 condition cards | ✅ Done |
| 2 | Graph extraction + vocabulary normalization | ✅ Done |
| 3 | Neo4j load — 10 conditions in AuraDB | ✅ Done |
| 4 | Vector store — Chroma + prose chunks | ✅ Done |
| 5 | Hybrid RAG — graph + vector → LLM | 🟡 In progress |
| 6 | UI — real-time diagnosis suggestions | 🔴 Planned |

**Corpus:** East Africa / Kenya primary care. Conditions prioritised by burden: malaria, TB, pneumonia, UTI, anaemia, T2DM, hypertension, obesity, PUD, acute gastroenteritis.

**Sources:** WHO guidelines, Kenya MOH, Kenya NLTP, British Thoracic Society, ADA, ISH.
