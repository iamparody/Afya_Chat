# CDS — Clinical Decision Support (Diagnostic RAG + Knowledge Graph)

> [!NOTE]
> This is the primary governance file for the `cds` project. Open this vault in Obsidian from the `cds/` root for full wiki-link navigation.

---

## Session Orientation — Read This First

**What this project is:** A symptom-driven clinical decision support system for Kenya primary care. Given a patient presentation, it returns candidate diagnoses with differentials and discriminating features — a reasoning aid, not a single-answer lookup.

**Current state:**
- 32 condition cards in `corpus/` (YAML format), all `draft` pending clinician review
- Corpus pipeline: `corpus_pipeline/ingest_yaml.py` (current) — not the legacy `ingest.py`
- Regression gate: 7/8 (last run 2026-09-24)
- Active branch: `feat/cardiovascular_2` — HF, APO, AMI, ARF, RHD authored + validated; pending ingest/eval/commit

**Where to look:**
- [[STATUS]] — source of truth for what's built vs. planned, eval history, domain progress
- `corpus/` — all condition cards (YAML, one directory per condition)
- `symptoms_dictionary/index.md` — condition index with ICD codes (quick navigation)
- `symptoms_dictionary/symptom_vocabulary.md` — all valid graph block terms
- `symptoms_dictionary/glossary.md` — clinical term definitions
- `symptoms_dictionary/conditions_vocabulary.md` — valid condition names for `differentials` and `confusable_with`
- `corpus/sources.yaml` — source registry (validator checks this)
- `docs/domain_evaluation_protocol.md` — B→A→C→D→E retrieval evaluation workflow

---

## Card Authoring Quick-Start

**Template:** Copy `corpus/hypertension/condition.yaml` — it is the most recent card at schema_version 2.3 with retrieval anchors.

**Source workflow (three tools, always in this order):**
1. **Primary — MOH Vol 2 (local):** `kenya_moh_vol2_2024.md` in the project root. Read the relevant section for clinical content. This is the first and authoritative source for all Kenya cardiovascular cards.
2. **Supplementary — Medscape (Firecrawl):** When MOH is thin on differentials, argues_against, or clinical discriminators, scrape the relevant Medscape condition page via the Firecrawl API (key in `.env` as `FIRECRAWL_API_KEY`). Document as a two-source entry in `corpus/sources.yaml`.
3. **ICD verification — WHO API (script):** Run `python scripts/verify_icd.py corpus/<condition>/condition.yaml`. The script authenticates with the WHO ICD-11 API (credentials `WHO_ICD_CLIENT_ID` / `WHO_ICD_CLIENT_SECRET` in `.env`), finds the canonical code and title, and sets `icd_verified: true` automatically. If the condition name does not match WHO canonical exactly, add `icd_search_term: "<exact WHO title>"` to frontmatter and re-run.

**Pipeline scripts (run from `cds/` root in order):**

```bash
# 1. Validate the card (must be 0 errors before proceeding)
python corpus_pipeline/validator.py corpus/<condition>/condition.yaml

# 2. ICD verification via WHO API
python scripts/verify_icd.py corpus/<condition>/condition.yaml

# 3. Ingest into chunks + graph entities
python corpus_pipeline/ingest_yaml.py corpus/<condition>/condition.yaml

# 4. Reload Chroma vector store
python chroma/chroma_loader.py

# 5. Run eval gate (must be ≥7/8)
python phase5/evaluate.py 2>&1 | Select-Object -Last 20

# 6. Load Neo4j graph
python neo4j/neo4j_loader.py
```

**Pipeline distinction:**
- `corpus_pipeline/ingest_yaml.py` — current pipeline; processes YAML cards in `corpus/`
- `ingest.py` (root) — legacy pipeline for old markdown cards in `symptoms_dictionary/`; do not use for new cards

**Neo4j note:** Free-tier AuraDB pauses after inactivity. Resume the `afyachat` instance at console.neo4j.io before running `neo4j_loader.py`.

---

## Adding a New Condition Card — Mandatory Gate Checklist

Every step is a hard gate. Do not proceed to the next step until the current step is complete. Do not commit until all steps are checked.

**STEP 1 — Choose authoring method and source**
- **Method A (preferred):** Source a WHO guideline or Kenya MOH protocol PDF. Feed to LLM with the card schema as target format. Clinician reviews draft, not blank page. ~20 min review per card.
- **Method B:** Query PrimeKG for symptom/differential skeleton. Author Kenya-specific content (endemic regions, environmental signals, primary care framing) manually — PrimeKG has no regional epidemiology. Clinician reviews full card.
- Document the source in `sources:` frontmatter before writing any prose.
- ⛔ STOP if no qualifying source exists — do not author from memory or general knowledge alone.

**STEP 2 — Add new graph terms to `symptom_vocabulary.md` first**
- Grep `symptom_vocabulary.md` for each graph block term you intend to use. Add missing terms before writing the card.
- ⛔ STOP if vocabulary terms would need to be added after the card is written.

**STEP 3 — Define new clinical terms in `glossary.md`**
- Add definitions for any new condition-specific terms or abbreviations before the card is written.
- ⛔ STOP if a term appears in the card but has no glossary entry.

**STEP 4 — Write the card**
- Copy `corpus/hypertension/condition.yaml` as template (schema_version 2.3, has retrieval_anchors).
- Fill all 9 clinical sections in fixed order. No section may be omitted or left blank.
- Set frontmatter: `review_status: draft`, `reviewed_by: ""`, `last_reviewed: ""`, `icd_verified: false`, `corpus_version: "1.0"`, `schema_version: "2.3"`
- Use controlled vocabulary only for `endemic_regions`, `environmental_signals`, `category`.
- Leave `retrieval_anchors` and `confusable_with` empty (`[]`) — populated in Phase D of domain evaluation.

**STEP 5 — Verify ICD codes via WHO API**
```bash
python scripts/verify_icd.py corpus/<condition>/condition.yaml
```
- The script authenticates with the WHO ICD-11 API and sets `icd_verified: true`, `icd_title`, and `icd_entity_uri` automatically on a confirmed match.
- If no exact match: add `icd_search_term: "<exact WHO canonical title>"` to frontmatter and re-run.
- Verify `icd10` manually at icd.who.int — the API covers ICD-11 only. Confirm the ICD-10 code maps to the same condition.
- ⛔ STOP if the script does not confirm MATCH. The validator ERRORs on `icd_verified: false`.

**STEP 6 — Add to `corpus/sources.yaml` registry**
- Add the condition entry with `authority_tier`, `authority`, `title`, `year`, and `url`. The validator checks for this entry.

**STEP 7 — Run the validator — must be 0 errors**
```bash
python corpus_pipeline/validator.py corpus/<condition>/condition.yaml
```
- ⛔ STOP if any ERROR remains. Warnings should be addressed but do not block.

**STEP 8 — Send to colleague for clinical review**
- Clinical review is required before `review_status` changes from `draft`.
- ⛔ Do not set `review_status: clinician_verified` until a named clinician has reviewed and approved.
- This step runs in parallel with Steps 9–12 — the card is ingested as `draft` and blocked from production until clinician-verified.

**STEP 9 — Ingest**
```bash
python corpus_pipeline/ingest_yaml.py corpus/<condition>/condition.yaml
```
- Confirm: 9 chunks (+ 1 retrieval_context chunk if retrieval_anchors are populated), 0 unknown graph terms.

**STEP 10 — Chroma reload**
```bash
python chroma/chroma_loader.py
```

**STEP 11 — Add coverage case to `evaluate.py`**
- Add a case to `COVERAGE_CASES` in `phase5/evaluate.py` for the new condition.
- Run coverage case and confirm it passes.

**STEP 12 — Eval gate**
```bash
python phase5/evaluate.py 2>&1 | Select-Object -Last 20
```
- Regression must be ≥7/8. If it drops below 7, do not proceed.

**STEP 13 — Neo4j load**
```bash
python neo4j/neo4j_loader.py
```

**STEP 14 — Update `STATUS.md` and domain contract**
- Add eval history line: date, regression score, condition count, coverage case result.
- Mark the condition as committed in `docs/domain_contracts/<domain>.md`.

**STEP 15 — Commit**
- Commit only after Steps 7 and 12 pass (0 validator errors, regression ≥7/8).
- Commit message format: `feat(corpus): <Condition> card — <domain>, <source>`
- Do NOT add Co-Authored-By trailers to any commit message.

---

## Frontmatter Schema Reference

Every condition card frontmatter must include all fields below. Do not add fields without incrementing `schema_version`.

```yaml
# ── Governance ────────────────────────────────────────────────────────────────
condition: <string>
icd11: <ICD-11 code>            # verify at icd.who.int — must match icd10 equivalent
icd10: <ICD-10 code>            # must match icd11
category: <string>              # controlled — see Category Vocabulary below
corpus_version: "1.0"           # increment minor on content change; major on schema change
schema_version: "2.3"           # increment ONLY if frontmatter structure changes
review_status: draft            # draft | under_review | clinician_verified
reviewed_by: ""
last_reviewed: ""
icd_verified: false             # set to true only after manual verification at icd.who.int
sources:
  - organization: ""
    title: ""
    year: ""

# ── Location and ecology ──────────────────────────────────────────────────────
endemic_regions:                # controlled vocabulary — list all that apply
  - nationwide
  - coast
  - lake_basin
  - highland
  - highland_margins
  - arid_semi_arid
  - northern_kenya
  - urban_informal

# ── Environmental context signals ────────────────────────────────────────────
# Only include signals with clinically meaningful evidence. Max 3 per card.
environmental_signals:
  - signal: <signal_name>       # controlled — see docs/environmental_vocabulary.md
    pathways:
      - <pathway>               # controlled — see docs/environmental_vocabulary.md
    effect_type: <type>         # transmission_opportunity | severity_modifier
    effect_direction: up        # up | neutral | down
    lag_weeks:
      min: <int>
      max: <int>
    strength: moderate          # low | moderate | strong
    confidence: moderate        # low | moderate | high
    causal_distance: direct     # direct | indirect
    evidence_type: expert_estimate  # see Evidence Type Vocabulary below
    regions:
      - <region>                # subset of endemic_regions
    seasonal_basis: <string>    # typical_long_rains | typical_short_rains | dry_season | perennial | outbreak_associated
    applicability:
      requires_exposure: []
      amplifiers: []

# ── Graph structure (machine-read by ingest pipeline) ────────────────────────
graph:
  cardinal_symptoms: []
  associated_symptoms: []
  risk_factors: []
  argues_against: []
  red_flags: []
  differentials: []
  confirms: []

# ── Retrieval evaluation (schema 2.3 — populated in Phase D of domain eval) ──
# Leave as empty lists on new cards. Populated only after Phase C baseline is recorded.
# See docs/domain_evaluation_protocol.md for authoring rules.
retrieval_anchors:
  positive: []     # presentation phrases that should retrieve this card over confusables
confusable_with: []  # condition names (from conditions_vocabulary.md) this card competes with
```

---

## Controlled Vocabularies

These are the only valid values for vocabulary-controlled fields. Do not use free text where a controlled value exists.

### Category Vocabulary
`gastroenterological` | `respiratory` | `cardiovascular` | `endocrine` | `haematological` | `infectious` | `urological` | `obstetric` | `neurological` | `dermatological` | `musculoskeletal`

### Endemic Region Vocabulary
`nationwide` | `coast` | `lake_basin` | `highland` | `highland_margins` | `arid_semi_arid` | `northern_kenya` | `urban_informal`

### Environmental Signal / Pathway / Effect / Evidence / Exposure Vocabularies
→ See [[docs/environmental_vocabulary.md]] for all valid values.

---

## Graph Block Rules

- **Short canonical forms only** — max ~4 words, no conditional phrases, no conjunctions (`with`, `or`, `and`, `without`), no age qualifiers appended.
  - ✓ `new onset dyspepsia` | ✗ `age over 55 with new dyspepsia`
  - ✓ `male UTI` | ✗ `UTI in man under 50 without precipitating factor`
  - ✓ `severe dehydration` | ✗ `severe dehydration in child under five`
- **`argues_against` must be individually matchable** — each feature must be establishable by a single, direct clinical finding or explicit denial. No compound criteria joined by `and`. No umbrella absence categories.
  - ✓ `no dysuria`, `no urinary frequency` (separate entries)
  - ✗ `negative RDT and negative blood film` (compound — split)
  - ✗ `no urinary symptoms` (umbrella — use specific denials)
- Add new terms to `symptom_vocabulary.md` **before** using them in a card.

---

## Domain-Level Retrieval Evaluation

Before committing a domain, run the full evaluation workflow in `docs/domain_evaluation_protocol.md`.

**Workflow: B → A → C → D → E**

| Phase | Action | Card changes? |
|-------|--------|---------------|
| B | Map confusable pairs — observation only | No |
| A | Document protocol + schema + ingestion | No |
| C | Capture Dense/BM25/RRF baseline for all direct confusable pairs | No |
| D | Author `retrieval_anchors` for domain cards | Yes |
| E | Re-ingest, compare before/after, run both gates | Yes |

**Hard rule: Phase C must be completed and recorded before any card modifications (Phase D).**

Two gates required for domain commit:
1. **Retrieval gate** — correct card RRF rank improves and margin increases vs confusable
2. **Reasoning gate** — regression suite ≥7/8

---

## Governance Rules

### Clinical Review
```
draft → under_review → clinician_verified
```
- `draft` — authored but not reviewed; blocked from production ingestion
- `clinician_verified` — named clinician has reviewed and approved; may enter production
- Do not set `clinician_verified` without an actual named clinician review.

To update a card after clinician review:
1. Set `review_status: clinician_verified`, `reviewed_by: <name + credential>`, `last_reviewed: YYYY-MM-DD`
2. Increment `corpus_version` minor version
3. Re-run `corpus_pipeline/ingest_yaml.py`

### Knowledge Graph (Neo4j)
- Node types: `Condition`, `Symptom`, `Sign`, `RiskFactor`, `Differential`, `RedFlag`
- Relationship types: `HAS_CARDINAL_SYMPTOM`, `HAS_DIFFERENTIAL`, `ARGUES_AGAINST`, `ESCALATES_TO`
- Every `CREATE` or `MERGE` must be idempotent (safe to re-run)
- Do not build an environmental pathway graph in Neo4j — environmental signals live in corpus card frontmatter only.

### Environmental Context Layer (Phase 7)
- Environmental signals live in condition card frontmatter — not in a separate database or graph
- Signal names, pathways, effect types, and evidence types must come from [[docs/environmental_vocabulary.md]]
- Maximum 3 `environmental_signals` entries per card
- The context engine (`phase7/context_engine.py`) is deterministic Python — it produces a labelled statement, not a probability
- The LLM must receive the evidence source label explicitly: "seasonal prior based on regional climatology, not observed rainfall"
- `effect_direction: down` is valid — a signal can reduce a candidate's relevance
- ENSO flag is maintained annually in `context_engine.py` — not per-card, not inferred by the LLM

### Modifying Existing Cards
- Preserve hedging language ("may", "usually", "commonly") — do not flatten qualifiers
- Do not rename section headers — the parser matches exact strings
- Do not add new frontmatter keys without incrementing `schema_version`

### Commit Rules
- Commit only after validator 0 errors AND regression ≥7/8
- Format: `feat(corpus): <Condition> card — <domain>, <source>`
- Do NOT add Co-Authored-By trailers to any commit message
- Never commit directly to master

---

## Architecture Reference

**9 mandatory clinical sections (fixed order — do not reorder):**
1. Cardinal symptoms
2. Associated symptoms and signs
3. Diagnostic features
4. Predisposing factors
5. Typical presentation
6. Important differential diagnoses
7. Features that argue against this diagnosis
8. Red flags
9. Diagnostic context

**Retrieval:** Dense (Cohere) + BM25 + RRF (K=60), TOP_N=9. Post-retrieval: `_enforce_arguing_against_ranking()` in `phase5/rag.py` — swaps leading candidate if it has arguing_against features that hard-threshold-violate and a lower-ranked candidate has fewer such features.
