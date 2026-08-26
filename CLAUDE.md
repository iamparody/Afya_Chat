# CDS — Clinical Decision Support (Diagnostic RAG + Knowledge Graph)

> [!NOTE]
> This is the primary governance file for the `cds` project. Open this vault in Obsidian from the `cds/` root for full wiki-link navigation.

---

## What This Project Is

A **symptom-driven clinical decision support system** for East Africa / Kenya primary care. Given a patient presentation, the system returns candidate diagnoses with differentials and discriminating features — it is a reasoning aid, not a single-answer lookup.

**Core stack (current → planned):**
```
Markdown condition cards
    → ingest.py (section-level chunking)
        → chunks.jsonl (embedded text + metadata)
            → Vector store (semantic retrieval)          ← TODO
                → Neo4j knowledge graph (structured traversal)  ← TODO
                    → RAG layer (LLM reasoning over retrieved context)  ← TODO
```

**Key constraint:** Only `review_status: clinician_verified` cards are allowed into production ingestion. All 10 current cards are `draft`.

---

## Directory Map

```
cds/
├── CLAUDE.md               ← you are here (governance)
├── STATUS.md               ← condition card + pipeline tracker (Obsidian)
├── README.md               ← public-facing design documentation
├── ingest.py               ← Python ingestion script (section chunker)
└── symptoms_dictionary/
    ├── index.md            ← machine-readable condition index (ICD-11 + filenames)
    ├── glossary.md         ← shared clinical term definitions (24 terms)
    ├── type_2_diabetes.md
    ├── hypertension.md
    ├── obesity.md
    ├── malaria.md
    ├── pulmonary_tb.md
    ├── pneumonia.md
    ├── uti.md
    ├── anaemia.md
    ├── peptic_ulcer_disease.md
    └── acute_gastroenteritis.md
```

**Obsidian quick-jump:**
- [[STATUS]] — review tracker for all cards + pipeline phases
- [[README]] — full architecture spec and design decisions
- [[index]] — machine-readable condition index
- [[glossary]] — shared clinical terminology

---

## Architecture: Three Layers

### Layer 1 — Markdown Corpus (`symptoms_dictionary/`)

Each condition card is a `.md` file with:
- **YAML frontmatter** — governance metadata (`review_status`, `icd11`, `corpus_version`, `sources`)
- **9 mandatory clinical sections** (in fixed order):
  1. Cardinal symptoms
  2. Associated symptoms and signs
  3. Diagnostic features
  4. Predisposing factors
  5. Typical presentation
  6. Important differential diagnoses
  7. Features that argue against this diagnosis
  8. Red flags
  9. Diagnostic context

Section order is **fixed** — do not reorder. The ingestion parser depends on it.

### Layer 2 — Ingestion Pipeline (`ingest.py`)

Reads condition cards → chunks by section header (one chunk per section, not token window) → outputs:
- `chunks.jsonl` — machine-readable, one JSON object per chunk
- `chunks_inspect.txt` — human-readable preview for validation

Each chunk carries: `condition`, `section`, `category`, `icd11`, `review_status`, `sources`, `text`.

Run with: `python ingest.py` from the `cds/` root.

### Layer 3 — Retrieval (TODO)

Planned:
- **Vector store** (Chroma for local dev / Pinecone or Weaviate for production)
- **Embedding API** (OpenAI `text-embedding-3-small` or Cohere)
- **Neo4j knowledge graph** — structured relationships between conditions, symptoms, and differentials (Cypher queries alongside vector retrieval)
- **RAG interface** — LLM reasoning layer over retrieved chunks + graph context

See [[STATUS]] for build phase tracking.

---

## Governance Rules

### Adding a New Condition Card

1. Copy an existing card (e.g., `hypertension.md`) as the template
2. Fill all 9 sections — no section may be omitted
3. Set frontmatter:
   - `review_status: draft`
   - `reviewed_by:` (leave blank)
   - `last_reviewed:` (leave blank)
   - `corpus_version: 1.1` (increment minor if content change, major if schema change)
   - `schema_version: 1.1` (only increment if frontmatter structure changes)
4. Add the condition to `symptoms_dictionary/index.md`
5. Define any new clinical terms in `symptoms_dictionary/glossary.md`
6. Update [[STATUS]] — add a row for the new card

### Clinical Review Workflow

```
draft → under_review → clinician_verified
```

- `draft` — authored but not reviewed; blocked from production ingestion
- `under_review` — sent to clinician for review
- `clinician_verified` — reviewed and approved; may enter production

To update a card after clinician review:
1. Set `review_status: clinician_verified`
2. Set `reviewed_by: <name + credential>`
3. Set `last_reviewed: YYYY-MM-DD`
4. Increment `corpus_version` minor version
5. Re-run `ingest.py` to regenerate chunks

### Running Ingestion

```bash
python ingest.py
```

- Only runs cleanly when called from `cds/` root
- Validates `review_status` and warns on `draft` cards
- Outputs `chunks.jsonl` and `chunks_inspect.txt` (both gitignored or committed depending on workflow)
- Do NOT commit `chunks.jsonl` if downstream pipeline reads directly from disk — treat as build artifact

### Modifying Condition Cards

- **Clinical prose** — always preserve hedging language ("may", "usually", "commonly"). Do not flatten qualifiers.
- **Section headers** — do not rename; the parser matches exact strings
- **Frontmatter keys** — do not add new keys without updating `ingest.py` and `schema_version`
- **Glossary** — if a new term appears in a card, define it in `glossary.md` before submitting

### Knowledge Graph (Neo4j) Rules (when building)

- Node types: `Condition`, `Symptom`, `Sign`, `RiskFactor`, `Differential`, `RedFlag`
- Relationship types: `HAS_CARDINAL_SYMPTOM`, `HAS_DIFFERENTIAL`, `ARGUES_AGAINST`, `ESCALATES_TO`
- Cypher scripts go in `neo4j/` (create this directory when starting Neo4j work)
- Every Cypher `CREATE` or `MERGE` script must be idempotent (safe to re-run)
- Schema migrations go in numbered files: `neo4j/migrations/001_initial_schema.cypher`

---

## Current Phase

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Corpus build — 10 condition cards authored | ✅ Complete (all draft) |
| 2 | Clinician review — verify all 10 cards | 🔴 Not started |
| 3 | Ingestion integration — connect to vector store | 🔴 Not started |
| 4 | Neo4j graph build — schema + Cypher import | 🔴 Not started |
| 5 | RAG interface — LLM + retrieval layer | 🔴 Not started |
| 6 | Corpus v2 — expand to 20+ conditions | 🔴 Not started |

See [[STATUS]] for granular task tracking.

---

## What Claude Should Know

### Do
- Read `symptoms_dictionary/index.md` first to find a condition without reading all files
- Read `symptoms_dictionary/glossary.md` before interpreting clinical terms in cards
- Run `python ingest.py` after any card modification to validate chunks
- Check `review_status` in frontmatter before treating card content as production-ready
- Use [[STATUS]] as the source of truth for what's built vs. planned

### Don't
- Do not rename section headers in condition cards (breaks the parser)
- Do not skip sections when authoring a new card
- Do not add `clinician_verified` status without an actual clinician review
- Do not flatten or remove clinical hedging language ("may", "usually") in prose
- Do not add new frontmatter keys without updating `schema_version` and `ingest.py`
- Do not create the Neo4j layer without first completing the ingestion pipeline

### Orientation (when new to session)
1. Read this file (`CLAUDE.md`)
2. Read [[STATUS]] for current build state
3. Read `symptoms_dictionary/index.md` to navigate condition cards
4. Only read individual condition cards when working on that specific condition

---

## Sources and Standards

- ICD-11 codes: verified at https://icd.who.int/
- Clinical content anchored to: WHO guidelines, Kenya MOH, Kenya NLTP, British Thoracic Society, ADA, EAU, ISDA
- Regional orientation: East Africa / Kenya primary care (not generic global medicine)
- Target users: clinical officers, nurses, general practitioners in primary care settings
