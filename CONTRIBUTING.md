# Contributing to CDS

This document is the entry point for all collaborators. It covers what the system is, how each phase works, how to add a condition card, how we work in parallel, and how the shared infrastructure is connected.

---

## What this system is

A symptom-driven clinical decision support system for Kenya primary care (Level 2–3). Given a patient presentation — free text, as a clinician would write it — the system returns:

- A leading candidate diagnosis with confidence level
- Differentials with discriminating features
- Red flags that must not be missed
- Missing information that would sharpen the assessment

It is a **reasoning aid**, not a diagnostic oracle. The clinician makes the decision. The system reduces the chance of a differential being overlooked.

**Target users:** Clinical officers, nurses, general practitioners in primary care settings across Kenya.

---

## System phases — what is built and what is not

| Phase | What it does | Status |
|-------|--------------|--------|
| 1 | Corpus — condition cards in YAML | ✅ Done — 22 conditions |
| 2 | Clinician review | ✅ 15 cards verified · 7 new cards await review |
| 3 | Ingestion → Chroma vector store | ✅ Done |
| 4 | Neo4j knowledge graph | ✅ Done |
| 5 | RAG pipeline — Gemini reasoning | ✅ Done |
| 6 | Streamlit app — input → result → approval → SQLite | ✅ Done |
| 7 | Environmental context (seasonal signals, ENSO, exposures) | ✅ Done |
| 8 | Disambiguation loop — follow-up questions when tied | ✅ Done |
| 8b | Reasoning evaluation harness (10-dimension rubric) | ✅ Done |
| 9 | Live rainfall data replacing static calendar | 🟡 Partial — provider built; thresholds not calibrated |

**What is not built yet:**
- Signal activation thresholds for live rainfall (Phase 9 completion)
- 3 AFI conditions pending a governance decision (Brucellosis, Leptospirosis, Rickettsial illness)
- COPD, Heart failure, HIV, Sickle cell, PID, Malaria in pregnancy (Tier 2 — after 30+ conditions)

---

## How the pipeline works

```
corpus/<condition>/condition.yaml
        ↓
corpus_pipeline/ingest_yaml.py
        ↓
corpus_pipeline/output/chunks.jsonl          → Cohere embed → Chroma (vector store)
corpus_pipeline/output/graph_entities.jsonl  → Cypher MERGE → Neo4j AuraDB

Patient presentation (free text)
    → Dense vector search → top 6 candidate conditions (Chroma)
    → Graph profiles + argues_against per candidate (Neo4j)
    → Prose passages per candidate (Chroma)
    → Environmental context engine (seasonal signals, exposures)
    → Comorbidity alert engine (pregnancy, HIV, etc.)
    → Gemini LLM (SEVEN RULES, JSON schema output)
    → Disambiguation loop (if tied candidates)
    → Streamlit UI → clinician approval → SQLite
```

---

## Corpus structure

Every condition is a single file: `corpus/<condition_name>/condition.yaml`

The file has two parts:
1. **YAML frontmatter** — governance metadata, ICD codes, endemic regions, environmental signals, graph block
2. **9 prose sections** — the clinical content, in fixed order

**The 9 sections (order is fixed — the parser depends on it):**

| # | Section name |
|---|-------------|
| 1 | Cardinal symptoms |
| 2 | Associated symptoms and signs |
| 3 | Diagnostic features |
| 4 | Predisposing factors |
| 5 | Typical presentation |
| 6 | Important differential diagnoses |
| 7 | Features that argue against this diagnosis |
| 8 | Red flags |
| 9 | Diagnostic context |

**Key rules:**
- Never rename section headers — the parser matches exact strings
- Never omit a section — all 9 are mandatory
- Always preserve clinical hedging language: "may", "usually", "commonly" — "fever is common" ≠ "fever confirms"
- Graph block terms must be short canonical forms — max ~4 words, no conjunctions or conditional clauses

---

## How to add a condition card

### Step 0 — Before you start

Read `CLAUDE.md` in full. It contains the schema, all controlled vocabularies, and the authoring rules. Do not use free text where a controlled vocabulary value exists.

Check `symptoms_dictionary/symptom_vocabulary.md` and `symptoms_dictionary/conditions_vocabulary.md`. Any graph block term you intend to use must already be in the relevant vocabulary file. **Add new terms to the vocabulary files before writing the card.**

### Step 1 — Verify sources

Every card needs an authoritative source. Priority order:

```
Kenya MOH > WHO-AFRO > WHO Global > Professional society
```

Check `corpus/sources.yaml` — there must be an entry for your condition before the validator will pass.

For conditions where no Kenya MOH guideline exists, a governance decision is required before authoring. Do not author a card based solely on a general web reference.

### Step 2 — Choose authoring method

**Method A (preferred):** LLM-assisted drafting from a WHO/MOH guideline PDF. Feed the PDF to an LLM with the card schema as the target format. The LLM produces a draft — the clinician reviews and corrects, not a blank page.

**Method B:** PrimeKG scaffold + clinical authorship. Query PrimeKG for disease-symptom-differential relationships, use as a skeleton for the graph block and first two prose sections, author Kenya-specific content manually.

### Step 3 — Author the card

Create the directory and file:
```
corpus/<condition_name>/condition.yaml
```

Copy an existing card (e.g. `corpus/bacterial_meningitis/condition.yaml`) as a template. Fill all 9 sections and all frontmatter fields.

Set:
- `review_status: draft`
- `schema_version: "2.2"` (current — do not change unless adding new frontmatter fields)
- `corpus_version: "1.0"`
- `reviewed_by:` (leave blank)
- `last_reviewed:` (leave blank)

Verify ICD codes at `icd.who.int` — both `icd11` and `icd10` must be confirmed as mapping to the same condition.

Add an entry to `corpus/sources.yaml`.

### Step 4 — Run the validator

```bash
python corpus_pipeline/validator.py corpus/<condition>/condition.yaml
```

Fix all errors before proceeding. Warnings about pre-existing compound graph terms in other cards are non-blocking for your card; warnings about your card must be resolved.

### Step 5 — Ingest and reload

```bash
python corpus_pipeline/ingest_yaml.py corpus/
python chroma/chroma_loader.py
```

Check ingest output: your condition should show `N chunks` and `M terms` with **0 unknown graph term warnings**.

### Step 6 — Run evaluation

```bash
python phase5/evaluate.py
```

Expected result: Regression ≥7/8 GATE PASS. Add a new entry to `COVERAGE_CASES` in `evaluate.py` for your condition — give it a representative clinical case and write the checks. Coverage cases do not move the gate threshold.

### Step 7 — Load Neo4j

```bash
python neo4j/neo4j_loader.py
```

Confirm your condition appears in the "Done. N conditions loaded." output.

### Step 8 — Commit

Commit all of: the `condition.yaml`, the `sources.yaml` entry, any new vocabulary terms added, and the updated `evaluate.py` coverage case. One commit per card.

Commit message format:
```
feat(corpus): <Condition name> — <domain>, <source>
```

---

## Domain assignments — using the MOH document structure

The Kenya MOH Clinical Guidelines Vol 2 (2024) is organised by clinical domain. Use this structure to divide corpus work between collaborators. Each collaborator takes a chapter:

| MOH Chapter | Clinical domain | Example conditions |
|-------------|-----------------|-------------------|
| 9 | Neoplasms | Cancer presentations (recognition only) |
| 10 | Haematologic | Sickle cell disease, haemolytic anaemias |
| 11 | Conditions in Pregnancy | Malaria in pregnancy, gestational diabetes |
| 12 | Lower Respiratory | COPD, TB in children |
| 13 | Other Common Conditions | Coma, jaundice, fever, lymphadenopathy |
| 14 | Skin Diseases | Eczema, fungal infections, parasitic infestations |
| 15 | Genito-Urinary | Glomerulonephritis, nephrotic syndrome, prostatitis |

**Before starting a domain:** create a domain contract document at `docs/domain_contracts/<domain>.md`. See `docs/domain_contracts/acute_febrile_illness.md` as the reference template. The contract defines the condition inventory, the MOH source reference for each condition, and the pairwise discrimination matrix.

---

## Working in parallel — branch strategy

Each collaborator works in their own branch. Branch naming:

```
feat/<domain>-<your-initials>
```

Examples:
```
feat/gi-ak          # Antony working on GI domain
feat/respiratory-jm # James working on respiratory domain
feat/haematology-sk # Sarah working on haematology domain
```

**Rules:**
- One domain per branch per person
- Never commit directly to `master`
- Raise a PR to `master` when your domain batch is complete (all cards validated, eval gate passes)
- All PRs must pass the eval gate: regression ≥7/8

**Before branching:**
1. Pull the latest `master`
2. Create your branch from `master`
3. Confirm `python phase5/evaluate.py` passes before adding your first card

**When merging:**
- Merge `master` into your branch and resolve conflicts before raising a PR
- The `evaluate.py` gate must pass on the merged branch before the PR is approved

---

## Shared infrastructure

### Neo4j AuraDB

The graph database is already cloud-hosted. All collaborators write to the same AuraDB instance.

**How to connect:** The connection credentials are in `.env`:
```
NEO4J_URI=neo4j+ssc://...
NEO4J_USER=neo4j
NEO4J_PASSWORD=...
```

Share the `.env` file securely (not through git — it is gitignored). Each collaborator adds it to their local `cds/` root. Do not commit `.env` to any branch.

**Conflict handling:** `neo4j_loader.py` uses Cypher `MERGE` throughout — it is idempotent. Running the loader from two branches targeting the same AuraDB instance is safe. The last writer wins for node properties; relationships are not duplicated.

### ChromaDB

ChromaDB runs locally at `chroma/db/` and is not shared across machines. Each collaborator maintains their own local Chroma instance.

**How this works in practice:**
- Each collaborator runs `python chroma/chroma_loader.py` after any corpus change on their branch
- When a branch is merged to `master`, every collaborator pulls `master` and re-runs `chroma_loader.py` to sync their local Chroma with the merged corpus
- The eval gate (`make eval`) also re-embeds, so the gate itself is self-consistent

**Why not a shared cloud Chroma?** ChromaDB Cloud or a self-hosted endpoint would allow true sharing. This is straightforward to set up when the collaboration scales — the `chroma_loader.py` connection string would change from local `chroma/db/` to a cloud endpoint, and no other code changes. For now, local-per-collaborator is the simpler path.

### API keys

Each collaborator needs their own keys for:

| Service | Used for | Get it at |
|---------|----------|-----------|
| Cohere | Embedding (embed-multilingual-v3.0) | dashboard.cohere.com |
| Gemini | RAG reasoning (gemini-2.0-flash) | aistudio.google.com |
| Firecrawl | Source acquisition (scraping Medscape, WHO) | firecrawl.dev |

Add all keys to your local `.env`:
```
COHERE_API_KEY=...
GEMINI_API_KEY=...
FC_API_KEY=...
```

The AuraDB credentials are shared (one instance). All other keys are per-collaborator.

---

## Key files to read before contributing

| File | Why |
|------|-----|
| `CLAUDE.md` | Schema reference, controlled vocabularies, authoring rules |
| `corpus/sources.yaml` | Provenance registry — your condition must have an entry here |
| `symptoms_dictionary/symptom_vocabulary.md` | Add new terms here before using them in a graph block |
| `symptoms_dictionary/conditions_vocabulary.md` | Add new condition names before using them in differentials |
| `docs/domain_contracts/acute_febrile_illness.md` | Reference domain contract — template for new domains |
| `corpus/bacterial_meningitis/condition.yaml` | Reference card — copy as template for new cards |

---

## Governance rules that must not be broken

- Never set `review_status: clinician_verified` without an actual clinician review
- Never commit `.env` to any branch
- Never change `providers.py`
- Never add a new frontmatter field without incrementing `schema_version` and updating `ingest_yaml.py`
- Never use free text where a controlled vocabulary value exists
- Never encode more than 3 `environmental_signals` per card without strong clinical evidence for each
- Never invent signal names — use only the 8 signals defined in `CLAUDE.md`
- Graph block terms: max ~4 words, no conjunctions (`and`, `or`, `with`, `without`), no conditional clauses

---

## Getting the environment running

```bash
# Clone and install
git clone <repo-url>
cd cds
pip install -r requirements.txt

# Add your credentials
cp .env.example .env   # then fill in your keys + AuraDB credentials

# Validate the corpus
python corpus_pipeline/validator.py corpus/

# Build local Chroma
python chroma/chroma_loader.py

# Load Neo4j (uses shared AuraDB)
python neo4j/neo4j_loader.py

# Run all evals to confirm baseline
python phase5/evaluate.py
python phase8/evaluate_disambiguation.py

# Run the app
streamlit run phase6/app.py
```

---

## Asking for help

- Questions about the schema or controlled vocabularies: read `CLAUDE.md` first
- Questions about a specific condition's clinical content: the domain contract for that domain has pairwise discrimination notes
- Questions about the pipeline: `make pipeline --dry-run` shows the command sequence
- Questions about a failing eval case: read the case definition in `phase5/evaluate.py` — the checks are self-documenting
