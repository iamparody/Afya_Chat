# CDS — Clinical Decision Support (Diagnostic RAG + Knowledge Graph)

> [!NOTE]
> This is the primary governance file for the `cds` project. Open this vault in Obsidian from the `cds/` root for full wiki-link navigation.

---

## What This Project Is

A **symptom-driven clinical decision support system** for East Africa / Kenya primary care. Given a patient presentation, the system returns candidate diagnoses with differentials and discriminating features — it is a reasoning aid, not a single-answer lookup.

**Core stack (built):**
```
Markdown condition cards (symptoms_dictionary/)
    → ingest.py (section-level chunking)
        → chunks.jsonl + graph_entities.jsonl
            → Cohere embed → Chroma vector store (semantic retrieval)
                → Neo4j knowledge graph (symptom/argues-against traversal)
                    → Gemini RAG layer (FIVE RULES prompt, JSON schema output)
                        → Streamlit MVP (phase6/app.py) — approval + SQLite persistence
```

**Planned additions (Phase 7+):**
```
Environmental context layer (static calendar + ENSO flag + exposure tags)
    → Context engine (four-layer: Temporal / Environmental / Geographic / Exposure)
        → Contextual candidate re-ranking (before LLM reasoning)

Interactive disambiguation loop (Phase 8)
    → Follow-up question generation from missing_information
        → Multi-turn enriched presentation → re-rank → result

Live environmental feeds — CHIRPS / Kenya Met API (Phase 9)
```

**Key constraint:** Only `review_status: clinician_verified` cards are allowed into production ingestion. All 10 current cards are `draft`.

---

## Directory Map

```
cds/
├── CLAUDE.md                     ← you are here (governance)
├── STATUS.md                     ← build tracker (Obsidian)
├── README.md                     ← public-facing design documentation
├── ingest.py                     ← ingestion script (chunker + graph extractor)
├── requirements.txt
├── phase5/
│   ├── prompts.py                ← FIVE RULES system prompt + JSON schema
│   ├── rag.py                    ← retrieval pipeline (Cohere → Chroma → Neo4j → Gemini)
│   ├── providers.py              ← Gemini provider with retry
│   └── evaluate.py               ← 8-case eval suite
├── phase6/
│   ├── app.py                    ← Streamlit MVP entry point
│   ├── db.py                     ← SQLite encounters persistence
│   └── cds_theme.py              ← CSS + Phosphor icon helpers
├── neo4j/
│   └── neo4j_loader.py           ← loads graph_entities.jsonl → Neo4j Aura
└── symptoms_dictionary/
    ├── index.md                  ← machine-readable condition index (ICD-11 + filenames)
    ├── glossary.md               ← shared clinical term definitions
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

## Architecture

### Layer 1 — Markdown Corpus (`symptoms_dictionary/`)

Each condition card is a `.md` file with:
- **YAML frontmatter** — governance metadata + clinical metadata + environmental context (see Frontmatter Schema below)
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

Reads condition cards → chunks by section header → extracts graph entities → outputs:
- `chunks.jsonl` — one JSON object per section chunk; carries: `condition`, `section`, `category`, `icd11`, `icd10`, `review_status`, `sources`, `endemic_regions`, `text`
- `graph_entities.jsonl` — structured graph records per condition
- `chunks_inspect.txt` / `graph_inspect.txt` — human-readable validation previews

Run with: `python ingest.py` from `cds/` root. Always run after any card modification.

### Layer 3 — Retrieval Pipeline (`phase5/`)

Built and operational:
- **Cohere embed** → **Chroma vector store** — semantic retrieval, top 6 candidates
- **Neo4j knowledge graph** — symptom matching + argues-against traversal
- **Gemini RAG** — FIVE RULES prompt, temperature=0, JSON schema output, jsonschema validation
- **Eval baseline:** 7/8 correct leading diagnoses across 8 Kenya primary care test cases

### Layer 4 — Environmental Context Layer (`phase7/`) ← IN DESIGN

Four-layer context injected into the RAG pipeline before LLM reasoning:
```
Temporal     → encounter_date (auto), onset_date (optional), season_phase (derived)
Environmental → signals from static calendar + ENSO flag
Geographic   → region, ecology, altitude_band (from patient_location)
Exposure     → documented patient exposures (livestock, floodwater, occupation, etc.)
```

Context engine produces a **confidence-labelled natural language statement** naming the evidence source explicitly. The LLM receives this statement as supplied evidence — it does not infer epidemiology from the calendar itself.

**Design principles (non-negotiable):**
- Retrieval is seasonally aware; diagnosis is not seasonally determined
- The context engine is deterministic; the LLM receives a labelled statement, not raw environmental data
- Contextual signals can increase, decrease, or have no effect on a candidate (not only a boost mechanism)
- Static calendar for Phase 7; schema designed so Phase 9 can replace calendar with live feeds without structural changes

### Layer 5 — Streamlit MVP (`phase6/`)

Built and operational:
- `app.py` — clinical presentation input → RAG → structured output → approval workflow
- `db.py` — SQLite encounters table; analyst-queryable fields (corpus-controlled arrays, ISO timestamps, ICD codes, 0/1 agreement flag)
- CSS: editorial minimal, Phosphor icons, Montserrat

---

## Frontmatter Schema Reference

Every condition card frontmatter must include all fields below. Do not add fields without incrementing `schema_version` and updating `ingest.py`.

```yaml
# ── Governance ────────────────────────────────────────────────────────────────
condition: <string>
icd11: <ICD-11 code>            # verify at icd.who.int — must match icd10 equivalent
icd10: <ICD-10 code>            # must match icd11
category: <string>              # controlled — see Category Vocabulary below
corpus_version: "1.x"           # increment minor on content change; major on schema change
schema_version: "2.0"           # increment ONLY if frontmatter structure changes
review_status: draft            # draft | under_review | clinician_verified
reviewed_by: ""
last_reviewed: ""
sources:
  - organization: ""
    title: ""
    year: ""

# ── Location and ecology ──────────────────────────────────────────────────────
endemic_regions:                # controlled vocabulary — list all that apply
  - nationwide                  # present in all ecological zones
  - coast                       # coastal lowlands, Mombasa, Kilifi, etc.
  - lake_basin                  # Lake Victoria basin and shores
  - highland                    # >1500m — Nairobi, central highlands, Rift Valley rim
  - highland_margins            # 1000–1500m — transition zones
  - arid_semi_arid              # ASAL counties — Turkana, Marsabit, Garissa, etc.
  - northern_kenya              # northern border counties (overlaps arid_semi_arid)
  - urban_informal              # informal settlements in any region

# ── Environmental context signals ────────────────────────────────────────────
# Only include signals that have a clinically meaningful relationship with this condition.
# Use controlled vocabularies only. Do not invent new signal names.
# Maximum ~3 signals per card — if a condition has more, re-examine the evidence.
environmental_signals:
  - signal: <signal_name>       # controlled — see Signal Vocabulary below
    pathways:                   # controlled — see Pathway Vocabulary below
      - <pathway>
    effect_type: <type>         # transmission_opportunity | severity_modifier
    effect_direction: up        # up | neutral | down
    lag_weeks:
      min: <int>
      max: <int>
    strength: moderate          # low | moderate | strong
    confidence: moderate        # low | moderate | high
    evidence_type: expert_estimate  # see Evidence Type Vocabulary below
    regions:                    # subset of endemic_regions — where signal applies
      - <region>
    seasonal_basis: <string>    # typical_long_rains | typical_short_rains | dry_season | perennial | outbreak_associated
    applicability:
      requires_exposure: []     # signal only applies if patient has this exposure — see Exposure Vocabulary
      amplifiers: []            # signal is stronger if patient also has this exposure

# ── Graph structure (machine-read by ingest.py) ───────────────────────────────
graph:
  cardinal_symptoms: []
  associated_symptoms: []
  risk_factors: []
  argues_against: []
  red_flags: []
  differentials: []
  confirms: []
```

---

## Controlled Vocabularies

These are the only valid values for vocabulary-controlled fields. Do not use free text where a controlled value exists. Add new values only by updating this section AND incrementing `schema_version`.

### Category Vocabulary
`gastroenterological` | `respiratory` | `cardiovascular` | `endocrine` | `haematological` | `infectious` | `urological` | `obstetric` | `neurological` | `dermatological` | `musculoskeletal`

### Endemic Region Vocabulary
`nationwide` | `coast` | `lake_basin` | `highland` | `highland_margins` | `arid_semi_arid` | `northern_kenya` | `urban_informal`

### Signal Vocabulary (Phase 7 — 8 signals maximum)
| Signal | Description |
|--------|-------------|
| `post_long_rains` | 4–8 weeks after Kenya long rains (March–May) |
| `post_short_rains` | 4–8 weeks after Kenya short rains (October–November) |
| `flooding` | Active flooding or heavy localised rainfall causing water contamination |
| `water_scarcity` | Prolonged dry spell reducing safe water access |
| `prolonged_drought` | Multi-month drought causing nutritional vulnerability |
| `dry_dusty_season` | Northeast monsoon dry season (November–March); mucosal drying |
| `cold_dry_season` | Highland cold season (June–August); indoor crowding |
| `heat_dehydration` | Hot dry season causing dehydration stress |

### Pathway Vocabulary
`vector_borne` | `waterborne` | `zoonotic` | `respiratory_mucosal` | `nutritional_vulnerability` | `airborne`

### Effect Type Vocabulary
`transmission_opportunity` — environmental condition increases disease acquisition risk
`severity_modifier` — environmental condition worsens disease severity or complications (does not increase incidence)

### Evidence Type Vocabulary
`observed_outbreaks` | `surveillance_data` | `regional_epidemiological_evidence` | `expert_estimate`

### Exposure Vocabulary (patient-documented)
`floodwater_contact` | `livestock_contact` | `occupational_dust` | `unsafe_water` | `mosquito_exposure_high` | `pastoralist_mobility` | `fishing_lakeshore`

### Interannual Context (maintained annually — not per-card)
```yaml
# Maintained in phase7/context_engine.py — updated once per year from NOAA/KMD
interannual_context:
  enso_phase: neutral           # neutral | el_nino | la_nina
  effect: modifies_rainfall_prior
  confidence: moderate
  evidence_type: surveillance_data
```
ENSO acts as an amplifier on existing seasonal signals — it does not directly name a disease or override clinical evidence.

---

## Governance Rules

### Adding a New Condition Card

1. Copy an existing card (e.g., `malaria.md`) as the template — it has all current fields including `environmental_signals`
2. Fill all 9 clinical sections — no section may be omitted
3. Set frontmatter:
   - `review_status: draft`
   - `reviewed_by:` (leave blank)
   - `last_reviewed:` (leave blank)
   - `corpus_version: 1.0`
   - `schema_version: 2.0` (current schema version — do not change unless adding fields)
   - `icd11` and `icd10` — verify both at icd.who.int; confirm they map to the same condition
   - `endemic_regions` — use controlled vocabulary only
   - `environmental_signals` — only include signals with meaningful clinical evidence; leave empty list if none
4. Send to colleague for clinical review **before** running ingest
5. After colleague sign-off: add to `symptoms_dictionary/index.md`, define new terms in `glossary.md`, update [[STATUS]]
6. Run `python ingest.py` — confirm no chunk validation errors and no unknown graph terms
7. Run `python neo4j/neo4j_loader.py` — confirm condition loaded
8. Test with a representative clinical case via the Streamlit app

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

### Knowledge Graph (Neo4j) Rules

- Node types: `Condition`, `Symptom`, `Sign`, `RiskFactor`, `Differential`, `RedFlag`
- Relationship types: `HAS_CARDINAL_SYMPTOM`, `HAS_DIFFERENTIAL`, `ARGUES_AGAINST`, `ESCALATES_TO`
- Cypher scripts go in `neo4j/`
- Every `CREATE` or `MERGE` must be idempotent (safe to re-run)
- Schema migrations: numbered files `neo4j/migrations/001_initial_schema.cypher`
- **Do not build an environmental pathway graph in Neo4j.** Environmental signals live in corpus card frontmatter + `context_engine.py` as controlled vocabulary. A separate pathway ontology in Neo4j violates the Phase 7 scope constraint.

### Environmental Context Layer Rules (Phase 7)

- Environmental signals live in condition card frontmatter — not in a separate database or graph
- Signal names, pathways, effect types, and evidence types must come from Controlled Vocabularies above
- Maximum 3 `environmental_signals` entries per card — if a condition needs more, review the evidence
- The context engine (`phase7/context_engine.py`) is deterministic Python — it produces a labelled statement, not a probability
- The LLM must receive the evidence source label explicitly: "seasonal prior based on regional climatology, not observed rainfall"
- `effect_direction: down` is valid — a signal can reduce a candidate's relevance (e.g., dry year in malaria-endemic region reduces vector-borne prior)
- ENSO flag is maintained annually in `context_engine.py` — not per-card, not inferred by the LLM

---

## Current Phase

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Corpus build — 10 condition cards | ✅ Complete (all draft) |
| 2 | Clinician review — all 10 cards | 🔴 Not started |
| 3 | Ingestion → Cohere embed → Chroma vector store | ✅ Complete |
| 4 | Neo4j knowledge graph | ✅ Complete |
| 5 | RAG interface — Gemini + FIVE RULES prompt (7/8 eval) | ✅ Complete |
| 6 | Streamlit MVP + approval workflow + SQLite | ✅ Complete |
| 7 | Corpus expansion + environmental context layer | 🟡 In design |
| 8 | Interactive disambiguation loop (follow-up questions) | 🔴 Not started — needs ≥15 conditions |
| 9 | Live environmental feeds + empirical calibration | 🔴 Not started — needs Phase 8 validated |

See [[STATUS]] for granular task tracking.

---

## What Claude Should Know

### Do
- Read `symptoms_dictionary/index.md` first to find a condition without reading all files
- Read `symptoms_dictionary/glossary.md` before interpreting clinical terms in cards
- Run `python ingest.py` after any card modification — check for chunk validation errors and unknown graph terms
- Run `python neo4j/neo4j_loader.py` after ingest when graph fields changed
- Check `review_status` in frontmatter before treating card content as production-ready
- Use [[STATUS]] as the source of truth for what's built vs. planned
- Verify ICD-11 codes at icd.who.int — confirm icd11 and icd10 map to the same condition
- Use only controlled vocabularies for `endemic_regions`, `environmental_signals`, `pathways`, `effect_type`, `evidence_type`, `exposure`
- Send new condition cards to colleague for clinical review before ingesting
- **Graph block terms must be short canonical forms** — max ~4 words, no conditional phrases, no conjunctions (`with`, `or`, `and`, `without`, age qualifiers appended). Clinical nuance belongs in prose sections, not graph fields. Examples: `new onset dyspepsia` ✓ / `age over 55 with new dyspepsia` ✗; `male UTI` ✓ / `UTI in man under 50 without precipitating factor` ✗; `severe dehydration` ✓ / `severe dehydration in child under five` ✗
- Add new graph terms to `symptom_vocabulary.md` **before** using them in a card — prevents unknown-term warnings at ingest

### Don't
- Do not rename section headers in condition cards (breaks the parser)
- Do not skip sections when authoring a new card
- Do not add `clinician_verified` status without an actual clinician review
- Do not flatten or remove clinical hedging language ("may", "usually") in prose
- Do not add new frontmatter keys without updating `schema_version` and `ingest.py`
- Do not build an environmental pathway graph in Neo4j — environmental signals live in corpus card frontmatter
- Do not use free text where a controlled vocabulary value exists
- Do not encode more than 3 `environmental_signals` per card without strong evidence for each
- Do not let the context engine (or the LLM) make a diagnosis based on season alone — context adjusts priors, clinical evidence decides
- Do not use `effect_direction: up` as the only direction — signals can be neutral or down
- Do not use compound graph block terms with conjunctions or conditional clauses — break into shortest canonical matchable units

### Orientation (when new to session)
1. Read this file (`CLAUDE.md`) — especially Frontmatter Schema and Controlled Vocabularies
2. Read [[STATUS]] for current build state
3. Read `symptoms_dictionary/index.md` to navigate condition cards
4. Only read individual condition cards when working on that specific condition

---

## Sources and Standards

- ICD-11 codes: verified at https://icd.who.int/ — both icd11 and icd10 must be verified per card
- Clinical content anchored to: WHO guidelines, Kenya MOH, Kenya NLTP, British Thoracic Society, ADA, EAU, ISDA
- Environmental signals anchored to: Kenya Malaria Strategy 2023–2027, WHO outbreak reports, regional epidemiological literature
- ENSO data source: NOAA (updated annually) + Kenya Meteorological Department
- Regional orientation: East Africa / Kenya primary care (not generic global medicine)
- Target users: clinical officers, nurses, general practitioners in primary care settings

---

## Evolution Path — Environmental Context

| Phase | Environmental capability | Data source |
|-------|--------------------------|-------------|
| 7 | Static seasonal calendar + ENSO flag + exposure tags | Hard-coded Kenya rainfall calendar; NOAA annual ENSO |
| 8 | Validated contextual scoring from encounter data | SQLite encounters DB (system_clinician_agreement) |
| 9 | Live environmental feeds replacing calendar lookups | CHIRPS / Kenya Met API / NDVI / SPI |

**The schema is designed so Phase 9 replaces `seasonal_basis` with observed data without changing corpus cards, the graph structure, or the LLM interface.**
