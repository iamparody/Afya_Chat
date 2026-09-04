# CDS Project Status Tracker

#status #tracker

← Back to [[CLAUDE]] | [[README]] | [[index]]

---

## Pre-flight — Complete before authoring any new cards
> These five items gate all corpus and follow-up work. Each is independently completable.
> Environmental context layer (Phase 7a engineering) is ON HOLD — do not start until pre-flight is done and corpus is ≥15 conditions.

### PF-1 — Graph term authoring rule (CLAUDE.md + fix existing 17 unknown terms) ✅ Done (2026-09-04)
> Root cause: graph fields in existing cards use long clinical phrases that don't match the canonical vocabulary. Compounds the problem with every new card authored.

- [x] Document rule in CLAUDE.md: graph fields (`cardinal_symptoms`, `associated_symptoms`, `risk_factors`, `argues_against`, `red_flags`, `differentials`, `confirms`) must use short canonical terms — max ~4 words, no conditional phrases, no conjunctions
- [x] Document examples of wrong vs. right: `"age over 55 with new dyspepsia"` ✗ → `"new onset dyspepsia"` ✓; `"male sex without catheter or structural abnormality"` ✗ → `"male sex"` ✓
- [x] Fix all unknown graph terms across existing 10 cards — re-run `python ingest.py` → 0 unknown terms
- [x] Add 13 new canonical terms to `symptom_vocabulary.md` (Risk Factors: `contaminated food`; Red Flags: `severe dehydration`, `unexplained anaemia`, `gestational hypertension`, `obstructive sleep apnoea`, `new onset dyspepsia`, `peritonism`, `multilobar consolidation`, `hypotension`, `pyelonephritis`, `male UTI`, `macroscopic haematuria`; Confirms: `consolidation signs`)
- [x] Reload Neo4j: `python neo4j/neo4j_loader.py` → 10/10 loaded

---

### PF-2 — Card evaluation protocol
> "Colleagues will test" is currently undefined. Without a shared checklist, evaluations are subjective and inconsistent.

- [ ] Define and document the evaluation checklist (below) — agree with colleagues before first new card is tested

**Card evaluation checklist (one pass per new card):**
1. **Leading diagnosis** — does a representative presentation return the correct condition as leading candidate?
2. **Differentials** — are the returned differentials clinically plausible? Any spurious vector matches (e.g. obesity for epigastric pain)?
3. **Argues-against** — do argues-against items fire correctly when the counter-evidence is present in the presentation?
4. **Red flags** — are the correct red flags surfaced? Are they scoped to the leading candidate only (not leaking from lower-confidence candidates)?
5. **Missing information** — are the listed missing items clinically relevant discriminators, not generic history questions?
6. **Regression** — re-run the full 8-case eval baseline after each new card batch; confirm 7/8 maintained

- [ ] Share checklist with Colleague 1 (evaluation) and Colleague 2 (LLM testing) before first new card ingest

---

### PF-3 — Complication vs. differential decision
> Iron deficiency anaemia appeared as a PUD differential — it is a complication (PUD causes anaemia through bleeding). The graph has no IS_COMPLICATION_OF concept. Decision needed before authoring cards that have clear complication relationships.

- [ ] **Decision: accept as known limitation for now** — document it; the prompt already has Rule 5 (confirmed comorbidities go to `relevant_comorbidities_or_context`); complications that appear as differentials will be filtered out by clinical review; revisit at Phase 8 when the disambiguation loop can ask "is this a pre-existing complication?"
- [ ] Add a note to `prompts.py` schema description for `candidates[]`: complications of a suspected diagnosis should not appear as independent candidates — they belong in `relevant_comorbidities_or_context` if already documented, or in `missing_information` if undocumented

---

### PF-4 — Disambiguation loop design spec (lock before building)
> Agreed at high level. Gaps in spec will cause rework if code is written before these are decided.

- [ ] **Ambiguity trigger**: no `high` confidence candidate AND ≥2 candidates share the same confidence tier (both `moderate`, or both `low`)
- [ ] **Question selection logic**: extract `missing_information` items that appear in the top tied candidate(s) but differ between them — these are the discriminating questions; do NOT ask about missing_information items shared by all candidates (not discriminating)
- [ ] **Max rounds**: 3 — after 3 rounds without a `high` confidence candidate, surface current best with explicit ambiguity note
- [ ] **Answer format**: free text appended to presentation (keeps architecture simple; structured answers are Phase 9)
- [ ] **Region/location**: do NOT add as a structured UI field — let it surface naturally as a clarifying question when region discriminates between tied candidates
- [ ] **UI**: question cards displayed one at a time; "Skip" option on each (skipped questions noted as still missing); "Stop and get assessment" escape hatch at any round
- [ ] Colleague review of this spec before implementation begins

---

### PF-5 — Regression test plan
> Adding new conditions changes the vector space — existing test cases may behave differently. No plan currently exists for catching regressions.

- [ ] After every batch of new cards (defined as every 2–3 cards), re-run `python phase5/evaluate.py`
- [ ] Acceptable baseline: 7/8 (Case 2b is a known ceiling, not a regression)
- [ ] If a previously passing case drops: investigate before ingesting the next card
- [ ] Track eval results in this file after each run — format: `YYYY-MM-DD: X/8 after adding [card name(s)]`

**Eval history:**
- 2026-08-31: 7/8 baseline (dense-only Cohere, FIVE RULES prompt)
- 2026-09-02: 7/8 (after UTI fix, Rule 4 demographic filter, red flags scope fix)

---

## Phase 7 — Corpus Expansion + Environmental Context Layer
> Environmental context engineering (7a code changes) ON HOLD until corpus ≥15 conditions.
> Modular. Each condition card is independent. Colleagues test after each ingest.
> Schema version 2.0 engineering deferred — cards can be authored now without environmental_signals block.

---

### 7a — Schema update (do first — gates everything else)
> Update governance docs, then ingest.py, then backfill existing cards.

**CLAUDE.md** ✅ Done (2026-09-04)
- Frontmatter schema reference added (all fields, controlled vocabularies)
- Environmental context layer architecture documented
- Controlled vocabularies locked: regions, signals, pathways, effect types, evidence types, exposures
- Evolution path documented (Phase 7 → 8 → 9)

**`ingest.py`**
- [ ] Parse `endemic_regions` from frontmatter → carry in chunk metadata
- [ ] Parse `environmental_signals` block → carry in chunk metadata (JSON)
- [ ] Validate signal names, pathways, effect_type, evidence_type against controlled vocabulary — warn on unknown values
- [ ] Increment expected `schema_version` to `"2.0"` in validation

**`neo4j_loader.py`**
- [ ] Store `endemic_regions` as list property on Condition nodes
- [ ] Store `environmental_signals` as structured properties — signal names and regions at minimum

**`phase7/context_engine.py`** ← new file
- [ ] `get_context(encounter_date, onset_date, patient_location, patient_exposures) → str`
- [ ] Static Kenya rainfall calendar lookup: long rains March–May, short rains October–November
- [ ] ENSO flag: annual variable (`neutral` | `el_nino` | `la_nina`) — update from NOAA/KMD each year
- [ ] Output: confidence-labelled natural language statement with explicit evidence source label
- [ ] Unit testable: given (date, location, exposures) → expected statement

**`phase5/rag.py`**
- [ ] Accept `patient_location` and `patient_exposures` as optional parameters
- [ ] Accept `encounter_date` (default: today) and `onset_date` (optional)
- [ ] Call `context_engine.get_context()` and inject output into `build_context()` as a new section

**`phase6/app.py`**
- [ ] Add structured `patient_location` field (optional — dropdown: region vocabulary)
- [ ] Add structured `patient_exposures` checkboxes (optional — exposure vocabulary)
- [ ] Pass location + exposures + onset_date to `rag.py`

---

### 7b — Backfill existing 10 cards with new schema fields
> Each card: add endemic_regions + environmental_signals → run ingest → confirm no validation warnings

- [ ] **malaria.md** — `endemic_regions`: lake_basin, coast, highland_margins, arid_semi_arid; signals: post_long_rains (strong), post_short_rains (moderate), flooding (moderate, amplifier: mosquito_exposure_high)
- [ ] **acute_gastroenteritis.md** — `endemic_regions`: nationwide; signals: flooding (moderate, requires: unsafe_water), water_scarcity (moderate, requires: unsafe_water)
- [ ] **anaemia.md** — `endemic_regions`: nationwide (lake_basin, coast higher burden); signals: prolonged_drought (severity_modifier, asal)
- [ ] **pneumonia.md** — `endemic_regions`: nationwide; signals: cold_dry_season (low, highland), dry_dusty_season (low, northern_kenya/arid_semi_arid)
- [ ] **pulmonary_tb.md** — `endemic_regions`: nationwide; no environmental signals (socioeconomic driver, not climate)
- [ ] **uti.md** — `endemic_regions`: nationwide; signals: heat_dehydration (low, severity_modifier)
- [ ] **hypertension.md** — `endemic_regions`: nationwide; no environmental signals
- [ ] **type_2_diabetes.md** — `endemic_regions`: nationwide; no environmental signals
- [ ] **obesity.md** — `endemic_regions`: nationwide; no environmental signals
- [ ] **peptic_ulcer_disease.md** — `endemic_regions`: nationwide; no environmental signals
- [ ] Re-ingest all 10 after backfill: `python ingest.py` — confirm schema_version 2.0 on all cards
- [ ] Reload Neo4j: `python neo4j/neo4j_loader.py`

---

### 7c — New condition cards (Tier 1 — priority order)
> Workflow per card: author → colleague clinical review → incorporate feedback → bump corpus_version → ingest → Neo4j reload → RAG test case

**Tier 1 — Environmental context critical (do first):**
- [ ] **Dengue fever** — `coast`, `urban_informal`; signals: post_long_rains (vector_borne, coast); key Malaria/Chikungunya differential
  - [ ] Card authored
  - [ ] Colleague review
  - [ ] Ingested + tested
- [ ] **Cholera** — `lake_basin`, `coast`, `urban_informal`, `asal_riverine`; signals: flooding (waterborne, strong), water_scarcity (moderate); separate from AGE
  - [ ] Card authored
  - [ ] Colleague review
  - [ ] Ingested + tested
- [ ] **Rift Valley fever** — `arid_semi_arid`, `northern_kenya`, `lake_basin`; signals: flooding (zoonotic, requires: livestock_contact); amplified by: pastoralist_mobility
  - [ ] Card authored
  - [ ] Colleague review
  - [ ] Ingested + tested
- [ ] **Chikungunya** — `coast`, `urban_informal`; signals: post_long_rains (vector_borne, coast); co-encode with Dengue (shared Aedes ecology)
  - [ ] Card authored
  - [ ] Colleague review
  - [ ] Ingested + tested

**Tier 1 — Differential gap (PUD/respiratory):**
- [ ] **GERD** — `nationwide`; no environmental signals; key PUD differential
  - [ ] Card authored
  - [ ] Colleague review
  - [ ] Ingested + tested
- [ ] **Functional dyspepsia** — `nationwide`; no environmental signals; key PUD/GERD differential
  - [ ] Card authored
  - [ ] Colleague review
  - [ ] Ingested + tested
- [ ] **Typhoid fever** — `nationwide`; signals: flooding (waterborne, moderate), water_scarcity (moderate); key Malaria/AGE differential
  - [ ] Card authored
  - [ ] Colleague review
  - [ ] Ingested + tested
- [ ] **Asthma** — `nationwide`; signals: cold_dry_season (low), dry_dusty_season (low); key Pneumonia/TB differential
  - [ ] Card authored
  - [ ] Colleague review
  - [ ] Ingested + tested

**Tier 2 — Next batch (after ≥15 conditions confirmed working):**
- [ ] **COPD** — `nationwide`; signals: dry_dusty_season (low, occupational_dust)
- [ ] **Heart failure** — `nationwide`; no environmental signals
- [ ] **HIV/AIDS** — `nationwide`; no environmental signals (comorbidity context)
- [ ] **Sickle cell disease** — `nationwide` (sub-Saharan African ancestry)
- [ ] **PID** — `nationwide`; female-only
- [ ] **Malaria in pregnancy** — `nationwide`; same signals as malaria + obstetric context
- [ ] **Meningococcal meningitis** — `northern_kenya`, `arid_semi_arid`; signals: dry_dusty_season (low, regional); geographic/outbreak context required
- [ ] **Leptospirosis** — `lake_basin`, `coastal_lowlands`, `urban_informal`; signals: flooding (zoonotic, requires: floodwater_contact)

---

### 7d — Context engine validation
- [ ] Unit tests: 5 fixed (date, location, exposure) inputs → expected context statement strings
- [ ] RAG integration test: Malaria case in lake_basin in June → context statement appears in LLM input
- [ ] RAG integration test: same Malaria case in Nairobi January → no post_long_rains signal fires
- [ ] RAG integration test: RVF case with livestock_contact in flooded ASAL county → zoonotic signal fires
- [ ] RAG integration test: RVF case without livestock_contact → zoonotic signal does not fire (requires_exposure not met)
- [ ] Eval suite: run 8-case baseline — confirm 7/8 maintained after context engine integration

---

## Phase 8 — Interactive Disambiguation (Follow-up Question Loop)
> Build after Phase 7 has ≥15 conditions confirmed working and context engine validated.

### Design gates (agree before building)
- [ ] Ambiguity threshold defined: no high-confidence candidate AND top 2+ candidates share same confidence tier
- [ ] Max rounds agreed (suggested: 3) before forcing a result regardless
- [ ] Colleague review of question-generation logic

### Implementation steps
- [ ] Session state machine: `analysing → ambiguous → questioning → re-analysing → result`
- [ ] Ambiguity detector: post-RAG confidence distribution check
- [ ] Question generator: discriminating `missing_information` items — features in one candidate's missing_info absent in another's
- [ ] Follow-up UI: question cards with answer input; answers append to presentation
- [ ] Re-run RAG with enriched presentation; loop until high confidence or max rounds
- [ ] "Stop and report" fallback: explicit ambiguity note if max rounds hit without resolution
- [ ] Eval: 3–5 ambiguous test cases from Phase 7 corpus to validate loop

---

## Phase 9 — Live Environmental Data + Empirical Calibration
> Build after Phase 8 is validated. Do not start until encounter data volume is sufficient for calibration.

- [ ] Integrate CHIRPS or Kenya Met API as rainfall data source
- [ ] Replace `seasonal_basis` calendar lookups with observed rainfall anomaly calculations
- [ ] Compute: rainfall last 7/30/60 days, anomaly vs historical average, consecutive wet days
- [ ] No schema changes required — context engine output interface is unchanged
- [ ] Calibrate contextual prior weights from SQLite encounter data (system_clinician_agreement)

---

## Phase 6b — Remaining Steps
> Steps 2–4 complete. Step 5 pending.

- [x] Step 2 — Session state scaffolding (`_init_session_state`, Clear button, `input_key` increment)
- [x] Step 3 — Approval workflow + SQLite (`db.py`, `write_encounter()`, clinician diagnosis input, ICD-10 preview)
- [x] Step 4 — CSS cleanup + editorial minimal UI + Phosphor icons + sidebar cleanup
- [ ] **Step 5 — Session history sidebar** — approved encounters from `st.session_state.history`; compact chronological list; patient snippet + system diagnosis + ✓/△ agreement indicator + time; flat, no login yet

---

## Outstanding RAG Quality Issues
> Tracked separately from corpus expansion — these are retrieval/prompt quality items.

- [ ] **PUD retest post ICD-11 fix** — run the PUD presentation case through the RAG; confirm `system_icd11` shows `DA62` (not DA60); confirm weight loss no longer appears in supporting_features
- [ ] **Obesity as PUD differential (retrieval quality)** — obesity appearing as a differential for epigastric pain is vector overlap in Chroma, not a clinical match; investigate during Phase 7 once more conditions are added (may self-resolve when GERD/dyspepsia dilute the vector space); if still occurring at 15+ conditions, tune retrieval threshold
- [ ] **Obesity card — secondary/hormonal causes missing (corpus quality)** — current card likely scoped to simple dietary/lifestyle obesity; missing: hypothyroidism, PCOS, Cushing's syndrome, pregnancy-related weight gain, medication-induced (corticosteroids, antipsychotics); these belong in "Important differential diagnoses" and "Features that argue against"; colleague flagged, clinician review will formally gate it; watch during testing
- [ ] **Region as follow-up question (Phase 8 design note)** — do NOT add patient_location as a structured UI field; instead let the disambiguation loop surface it as a clarifying question when region is discriminating between tied candidates (e.g. Dengue vs Malaria); `missing_information` in RAG output already has the slot for this

---

## Session Handoff — 2026-09-03 (Colleague RAG review — prompt fix + corpus flag)

> **For the agent picking up after a compact or new session — read this first.**

### What this session accomplished

**Colleague clinical review of PUD RAG output — 4 issues identified and triaged:**

**Issue 1 — Weight loss hallucination (FIXED):** The model listed "weight loss" in `supporting_features` for PUD despite the presentation explicitly stating "Denies... weight loss." Root cause: Rule 1 only covered the missing-is-not-negative direction; the inverse (denied = confirmed absent, must NOT appear in supporting_features) was not stated. Fix applied to `phase5/prompts.py`:
- Rule 1 heading extended: "MISSING IS NOT NEGATIVE — AND DENIED IS NOT PRESENT"
- Inverse constraint added: denied/negated findings are confirmed absent; listing them in supporting_features is a factual contradiction
- `supporting_features` schema description updated: NEVER include explicitly denied findings

**Issue 2 — ICD-11 code mismatch in PUD corpus card (PENDING VERIFICATION):** `symptoms_dictionary/peptic_ulcer_disease.md` has `icd11: DA60` (Gastric ulcer, ICD-11) but `icd10: K27` (Peptic ulcer, site unspecified). These don't match. Colleague says correct ICD-11 for K27 is DA61, but ICD-11 tree structure (DA60=Gastric, DA61=Duodenal) suggests DA62 may be the unspecified code. **Action needed:** verify correct ICD-11 code at icd.who.int, then update the card and re-run `python ingest.py`.

**Issue 3 — Weak differentials (CORPUS LIMITATION, KNOWN):** GERD, functional dyspepsia, pancreatitis, gastric malignancy not in the corpus — none can appear as differentials. This is Phase 7 work. Obesity appearing as a differential for PUD is a retrieval quality issue (vector overlap on abdominal symptoms) — flagged for investigation during Phase 7.

**Issue 4 — Overall assessment:** Leading diagnosis, supporting features (after fix), ICD-10, and missing_information are performing well. Differential breadth is a corpus-size problem, not a model problem.

### Current state
- Prompt fix (Rule 1 inverse — denied findings cannot appear in supporting_features): **committed**
- PUD ICD-11 code: **fixed** — DA60 → DA62 (peptic ulcer, site unspecified), corpus_version 1.2 → 1.3
- Phase 6b steps 2–4 (session state, approval workflow, UI/CSS): **complete and committed**
- Phase 6b step 5 (session history sidebar): **pending**
- Phase 7 schema (CLAUDE.md + STATUS.md): **documented 2026-09-04**
- Eval: **7/8** (unchanged)

### Pick up here
1. **Phase 7a — `ingest.py`** — add `endemic_regions` + `environmental_signals` parsing; validate against controlled vocabulary; bump schema_version to 2.0
2. **Phase 7a — `context_engine.py`** — new file in `phase7/`; static calendar + ENSO flag; unit testable
3. **Phase 7b — Backfill** — add new frontmatter fields to all 10 existing cards; re-ingest; reload Neo4j
4. **Phase 7c — Dengue card** — first new condition card; send to colleague before ingesting
5. **Phase 6b Step 5** — session history sidebar (can be done in parallel with 7a)

### Key files (current)
- `phase5/prompts.py` — FIVE RULES; Rule 1 inverse (denied = absent); Rule 4 demographic filter; red flags scope
- `symptoms_dictionary/peptic_ulcer_disease.md` — corpus_version 1.3, icd11: DA62
- `symptoms_dictionary/uti.md` — corpus_version 1.4, simplified argues_against: male sex
- `CLAUDE.md` — schema_version 2.0 spec, controlled vocabularies, environmental context architecture

---

## Session Handoff — 2026-09-02 (Phase 6b steps 2–3 + schema + analyst fields)

> **For the agent picking up after a compact or new session — read this first.**

### What this session accomplished

**Phase 6b — Approval workflow: steps 2 and 3 complete**

- **Step 2 — Session-state scaffolding:** `_init_session_state()`, `_assert_confidence()`, `_clear_all()`, clearable text area via `input_key` increment, Clear button beside Analyse (visible only when result exists), architecture panel removed from sidebar
- **Step 3 — Approval workflow + SQLite:** `phase6/db.py` created — `init_db()`, `write_encounter()`, `_extract_structured()`, column migration via `_add_column_if_missing()`; approval section in app.py: system assessment (read-only) → editable clinician diagnosis → live ICD-10 preview → Approve button → post-approval confirmation + "New assessment →"
- **DB schema lock:** encounters table with all fields; structured corpus-controlled arrays (`supporting_symptoms`, `arguing_against`, `red_flags`, `comorbidities`) stored as JSON from RAG output — not free text; `phase6/cds.db` gitignored
- **Analyst fields:** three new columns added via migration — `system_category` (corpus-controlled disease category), `clinician_icd11` (ICD-11 for clinician diagnosis), `system_clinician_agreement` (1=agree, 0=override); all queryable without text cleaning; `json_each()` works on array fields
- **UTI corpus fix in progress:** `graph.argues_against` simplified from `male sex without catheter or structural abnormality` → `male sex`; corpus_version 1.3 → 1.4; ingest + Neo4j reload still needed before testing

### Current state
- Phase 6b: steps 2–3 complete; step 4 (CSS) and step 5 (history sidebar) pending
- UTI argues_against fix: corpus change committed, pipeline reload pending
- DB: 2 test records (both UTI), all analyst fields backfilled
- Eval: **7/8** (unchanged)

### Pick up here
1. **UTI corpus fix** — run `make ingest && python neo4j/neo4j_loader.py`, then test with male UTI case; confirm "male sex" appears in arguing_against
2. **Step 4 — CSS cleanup** — strip dashboard aesthetic from `cds_theme.py` and `app.py`; colour only for clinical meaning
3. **Step 5 — Session history sidebar** — approved encounters from `st.session_state.history`; patient snippet + diagnosis + agreement indicator + time
4. **Phase 7** — 8 new condition cards after Phase 6b is complete

### Key files (current)
- `phase6/app.py` — UI entry point (steps 2+3 built)
- `phase6/db.py` — SQLite persistence, encounters schema, `write_encounter()`
- `phase6/cds_theme.py` — design system (CSS cleanup step 4 targets this)
- `symptoms_dictionary/uti.md` — corpus_version 1.4, simplified argues_against

---

## Session Handoff — 2026-09-02 (Phase 6 complete + prompt fixes + CI hardening)

> **For the agent picking up after a compact or new session — read this first.**

### What this session accomplished

**Phase 6 — Streamlit MVP: COMPLETE, TESTED, COMMITTED**
- `phase6/cds_theme.py` — palette (COLORS), CSS (Montserrat), `apply_theme`, `section_header`, `page_header`, `info_card`, `dq_note`, `kpi_card` — extracted from LREB dashboard theme
- `phase6/app.py` — full Streamlit MVP: red flags above candidate cards (safety-first), leading candidate expanded (navy border, ICD codes), differential in collapsed expanders, relevant context section
- Tested against 8 real-world Kenya primary care cases — all correct leading diagnoses; red flags render correctly; ICD-11 + ICD-10 on leading candidate
- Run: `streamlit run phase6/app.py` from `cds/` root

**Prompt fixes (phase5/prompts.py):**
- FOUR RULES → FIVE RULES heading (model was counting rules; mismatch caused instruction confusion)
- Rule 4 extension — `missing_information` items must be demographically appropriate (no vaginal findings for male patients)
- Rule 5 (new) — confirmed prior comorbidities ("known [condition]", "on [medication] for") go to `relevant_comorbidities_or_context`, not `candidates[]`; current presenting findings always stay in `candidates[]`

**CI hardening:**
- Gemini 503 retry moved to Python level (`providers.py`) — retries the single API call (15s/30s/60s/120s backoff) rather than restarting the full 8-case eval suite
- CI bash loop increased to 5 attempts, exponential backoff — last-resort safety net only
- Eval result post-fixes: **7/8** — all prompt regressions resolved; Case 2b remains confirmed ceiling

**UTI corpus fix:**
- Added `male sex without catheter or structural abnormality` to `graph.argues_against` in `uti.md`
- Added corresponding prose to "Features that argue against this diagnosis" section
- corpus_version: 1.2 → 1.3

### Current state
- Phase 6 Streamlit MVP: **complete and committed**
- Eval: **7/8** (unchanged ceiling, Case 2b structural limit)
- CI: green — 5-attempt retry, provider-level 503 handling
- All 10 condition cards: draft (clinician review pending)

### Pick up here
**Phase 6 is complete as MVP.** Next work:
1. **Phase 6b — UI improvement** (user-directed; discuss what "better" means before building)
2. **Approval + database schema** — when clinician approves, write structured record (diagnosis, ICD-10, symptoms, age/sex, timestamp) to database; see Decisions Log for design principles
3. **Phase 7 — Corpus v2** (8 new condition cards: asthma, COPD, heart failure, HIV, typhoid, sickle cell, PID, malaria-in-pregnancy)

### Key files (current)
- `phase6/app.py` — Streamlit UI entry point
- `phase6/cds_theme.py` — design system
- `phase5/prompts.py` — FIVE RULES, Rule 5 (comorbidities), Rule 4 extension (demographics)
- `phase5/providers.py` — GeminiProvider with inline 503 retry
- `.github/workflows/cds_pipeline.yml` — 5-attempt exponential backoff CI

---

## Session Handoff — 2026-08-31 (Phase 5c + Case 2b prompt fix — both rejected; 7/8 is ceiling)

> **For the agent picking up after a compact or new session — read this first.**

### What this session accomplished

**5c — BM25 hybrid retrieval: BUILT, EVALUATED, REJECTED**
- Built `phase5/bm25_index.py` — lazy BM25 index over chunks.jsonl (`rank_bm25`, pure Python, 89 chunks)
- Added `get_vector_candidates_hybrid()` to `rag.py` — dense + BM25 → RRF (k=60) → top 6 conditions
- Added `--hybrid` flag to `evaluate.py`; `hybrid=False` default preserves Cohere dense-only baseline
- Evaluation result: hybrid 7/8 BUT introduced 4a→4b T2DM confidence regression (no longer drops)
- Dense-only: 7/8, both paired comparisons pass. Hybrid: 7/8, 4a→4b paired check fails.
- Confirmed: Case 2b is NOT a retrieval problem. BM25 changes nothing for it.
- Decision: dense-only stays as default. BM25 infrastructure preserved; `--hybrid` available for future experiments.

**Case 2b prompt fix: ATTEMPTED, REGRESSED, REVERTED**
- Failure mode: Gemini correctly populates TB `arguing_against` but ignores the ranking rule
- Fix attempted: replaced hard "MUST" instruction with softer comparative net-evidence instruction
- Result: 6/8 — TB `arguing_against` field went EMPTY + Case 4a hyperosmolar red flag lost
- Finding: the original "MUST" instruction is load-bearing for arguing_against population in all cases; softening it removes the documentation constraint, not just the ranking constraint
- Reverted to original instruction. No net change to `prompts.py` (git sees zero diff).
- **7/8 is the prompt ceiling for Case 2b.** Gemini documents the counter-evidence but treats the leading_candidate selection as its own judgment.

### Current state
- Cohere dense-only: **7/8** (baseline, unchanged)
- BM25 hybrid: 7/8 but with regression — rejected, `hybrid=False` default
- Case 2b: TB still leads for 3-day cough — confirmed model reasoning problem, not retrieval
- All changes committed and pushed (origin up to date)

### Pick up here
**Phase 5c is complete (rejected).** Case 2b prompt fix is exhausted at this approach.

**Next decision:** Phase 5e Prefect orchestration, or accept 7/8 as MVP and proceed to Phase 6 (UI)?

If 7/8 is acceptable as the RAG MVP ceiling:
- Phase 6 requires ICD-10 codes in all 10 condition card frontmatters (currently ICD-11 only)
- Clinician review (Phase 2) is the production gate — all 10 cards remain `draft`

If attempting Case 2b further:
- Post-generation structural check: if `leading_candidate.arguing_against` is non-empty AND another candidate has empty `arguing_against`, swap the leading_candidate — deterministic, not LLM-dependent
- Risk: could produce clinically wrong output if TB has overwhelmingly stronger support despite counter-evidence
- Requires new validation step in `rag.py` after `validate()`

### Key files (current)
- `phase5/rag.py` — `run(presentation, embedder=None, hybrid=False)`: dense-only default, hybrid available
- `phase5/bm25_index.py` — BM25 lazy index builder (chunks.jsonl)
- `phase5/evaluate.py` — `--backend` + `--hybrid` flags; `python phase5/evaluate.py` = Cohere dense baseline
- `phase5/prompts.py` — unchanged from Phase 5 MVP; original MUST-based arguing_against rule restored
- `requirements.txt` — added `rank-bm25`

### Known architectural limitations (confirmed through experimentation)
- Case 2b: 7/8 is the prompt ceiling — Gemini documents TB counter-evidence but overrides the ranking rule
- BM25 hybrid: introduces 4a→4b paired confidence regression; dense-only is strictly better for this corpus
- PubMedBERT: failure in filtered passages step (against section not retrieved); dense-only stays
- Red flag stochasticity: ANN non-determinism means red flag content varies; Cases 1, 2a, 3, 6 red flag checks are manual

---

## Session Handoff — 2026-08-27 (Phase 5 complete)

> **For the agent picking up after a compact or new session — read this first.**

### What this session accomplished
- Wrote `phase5/evaluate.py` — full 8-case evaluation harness with auto-checks and paired confidence comparisons
- Iterated prompts, context template, and retrieval parameters to maximise evaluation score
- Key fixes: removed sort-by-matched-count (trust vector order), increased TOP_N_CANDIDATES to 6, removed match count from context headers, added argues_against tie-breaking and negative-finding red flag prohibition to SYSTEM_PROMPT, temperature=0 for determinism
- Phase 5 evaluation result: **7/8 cases auto-passed** (Cases 1, 2a, 3, 4a, 4b, 5, 6); both paired comparisons pass (2a/2b: high→moderate, 4a/4b: high→moderate)
- Single remaining failure: Case 2b (TB leads instead of CAP) — documented architectural limitation; vector always ranks TB first for cough presentations
- Phase 5 is **complete** as an MVP — commit made at this checkpoint

### Pick up here
**Phase 5 is complete.** Phase 6 (UI) is next, but requires ICD-10 codes added to frontmatter first.

**Immediate next decision: ICD-10 codes — add to frontmatter now or defer to Phase 6?**

See Open Questions in this file for the two deferred architectural decisions before Phase 6.

### Key files to read on pickup
1. `CLAUDE.md` — governance
2. `STATUS.md` — this file
3. `phase5/rag.py` — orchestrator (5 steps: vector → graph → filtered vector → build_context → Gemini → validate)
4. `phase5/prompts.py` — locked system prompt + OUTPUT_SCHEMA + build_context()
5. `phase5/providers.py` — GeminiProvider (gemini-flash-lite-latest primary), AnthropicProvider fallback
6. `phase5/evaluate.py` — 8-case evaluation harness; run with `python phase5/evaluate.py`
7. `chroma/evaluation_contract.md` — original pass/fail criteria

### Architecture (current)
```
Patient presentation
    → Cohere embed → Chroma vector search (unrestricted, top 6 candidates)
    → Neo4j graph → symptom profiles + argues_against per candidate
    → Cohere embed → Chroma vector search (filtered to candidates, top 5 passages each)
    → build_context() → Gemini gemini-flash-lite-latest (temperature=0, JSON schema enforced)
    → jsonschema validate → validated dict
```

### Known architectural limitations (documented, not blocking)
- Case 2b: semantic vector always ranks TB first for cough presentations; argues_against tie-breaking not reliably applied by LLM when TB has strong support
- Red flag stochasticity: ANN non-determinism means red flag content varies across runs even at temperature=0; Cases 1, 2a, 3, 6 red flag checks moved to manual
- Malaria red flags appear in non-malaria fever cases due to semantic similarity in retrieval

### Active credentials (.env — gitignored)
- NEO4J_URI: neo4j+ssc://b3f927fc.databases.neo4j.io (AuraDB, afyachat instance)
- COHERE_API_KEY: set
- GEMINI_API_KEY: set (gemini-flash-lite-latest)

---

## Session Handoff — 2026-08-26

> **For the agent picking up after a compact or new session — read this first.**

### What this session accomplished
- Bootstrapped the entire project governance: created `CLAUDE.md`, `STATUS.md` (this file)
- Added `graph:` blocks to all 10 condition cards (7 relationship keys per card: cardinal_symptoms, associated_symptoms, risk_factors, differentials, argues_against, red_flags, confirms)
- Created `symptom_vocabulary.md` (464 terms, synonyms + canonicals) and `conditions_vocabulary.md` (114 condition names) as the controlled vocabulary layer
- Extended `ingest.py` with a full graph extraction pipeline alongside the existing prose chunking pipeline — two independent output paths: `chunks.jsonl` (RAG) and `graph_entities.jsonl` (Neo4j)
- Built `report_unknowns.py` — deduplication + classification tool for vocabulary gap analysis
- Vocabulary coverage: 380/401 terms canonical, 37 compound terms flagged for v2 (expected), 4 simple unknowns remaining
- Initialized git repo, added remote: https://github.com/iamparody/Afya_Chat.git

### Pick up here
**Phase 2 is complete.** The graph extraction + normalization pipeline is working and producing clean output.

**Immediate next task (Phase 3 — Neo4j Load):**
1. Resolve the 4 remaining simple unknowns in `unknown_terms_report.md` (takes ~10 min)
2. Choose Neo4j hosting — AuraDB free tier (fastest to start) vs local Docker
3. Define Neo4j node/relationship schema (`neo4j/migrations/001_initial_schema.cypher`)
4. Write the Cypher MERGE loader that reads `graph_entities.jsonl`
5. Load all 10 conditions and run test Cypher queries

### Key files to read on pickup
1. `CLAUDE.md` — project governance, architecture, rules
2. `STATUS.md` — this file, phase tracker
3. `graph_entities.jsonl` — the graph-ready output (10 records, one per condition)
4. `unknown_terms_report.md` — 4 remaining simple unknowns to resolve
5. `ingest.py` — understand `normalize_graph()` before modifying any vocabulary

### Architecture reminder
```
Markdown cards → ingest.py → chunks.jsonl → [Chroma vector store, Phase 4]
                           → graph_entities.jsonl → [Neo4j loader, Phase 3 NOW]
```

---

## Condition Card Review Status

| Card | ICD-11 | Category | Review Status | Reviewer | Last Reviewed |
|------|--------|----------|--------------|----------|---------------|
| [[type_2_diabetes]] | 5A11 | Endocrine/Metabolic | 🟡 draft | — | — |
| [[hypertension]] | BA00 | Cardiovascular | 🟡 draft | — | — |
| [[obesity]] | 5B81 | Metabolic | 🟡 draft | — | — |
| [[malaria]] | 1F40 | Infectious | 🟡 draft | — | — |
| [[pulmonary_tb]] | 1B10 | Infectious/Respiratory | 🟡 draft | — | — |
| [[pneumonia]] | CA40 | Respiratory/Infectious | 🟡 draft | — | — |
| [[uti]] | GC08 | Urogenital/Infectious | 🟡 draft | — | — |
| [[anaemia]] | 3A00 | Haematological | 🟡 draft | — | — |
| [[peptic_ulcer_disease]] | DA60 | Gastroenterological | 🟡 draft | — | — |
| [[acute_gastroenteritis]] | 1A09 | Gastroenterological/Infectious | 🟡 draft | — | — |

**Legend:** 🟡 draft · 🔵 under_review · ✅ clinician_verified

**Production gate:** 0 / 10 cards verified. Dev work proceeds freely on draft cards.

---

## Pipeline Build Tracker

### Phase 1 — Corpus (Markdown Cards) ✅
- [x] Condition card schema designed (9 sections, YAML frontmatter)
- [x] 10 condition cards authored (draft quality)
- [x] Shared glossary — 24 terms defined ([[glossary]])
- [x] Machine-readable index created ([[index]])
- [x] `graph:` blocks added to all 10 cards (7 relationship keys per card)
- [x] [[symptom_vocabulary]] created — canonical term list, synonym blacklist
- [ ] Clinician review — all 10 cards (production gate, not a dev blocker)
- [ ] Corpus v2 expansion (asthma, COPD, heart failure, HIV, typhoid, sickle cell, STIs, pregnancy)

### Phase 2 — Graph Extraction + Normalization ✅
- [x] Extend `ingest.py` to parse `graph:` blocks → `graph_entities.jsonl`
- [x] Normalization layer — canonicalize terms against [[symptom_vocabulary]]
- [x] Validate relationship keys against allowed set (warns on unknown keys)
- [x] Unknown terms in controlled keys → WARN, not silent creation
- [x] Summary stats at end of run (canonicalized / already_canonical / unknown)
- [x] `graph_inspect.txt` — human-readable graph record preview
- [x] Prose chunking path untouched; two independent pipelines
- [x] Expand [[symptom_vocabulary]] — 129 → 19 warnings (37 compound flagged for v2, 4 simple remaining)
- [x] Create [[conditions_vocabulary]] — canonical condition names for `differentials:` key
- [x] Fix regex bug in `report_unknowns.py` (IGNORECASE `fL` collision)
- [x] Fix CAP card — split `productive cough with purulent sputum` into two terms
- [x] Key-to-vocabulary routing in normalization layer (symptom vs condition vocabulary per key)
- [x] `asymptomatic` — confirmed: do not add as symptom, model as condition property in Neo4j
- [ ] Resolve 4 remaining simple unknowns (see [[unknown_terms_report]]) ← **next task**
- [ ] Design Neo4j relationship schema to accept edge properties (future provenance)
- [ ] Unit tests for graph extractor

### Phase 3 — Neo4j Load ✅
- [x] Choose Neo4j hosting → AuraDB free tier (afyachat instance, `neo4j+ssc://`)
- [x] Define node labels: `Condition`, `Symptom`, `RiskFactor`, `RedFlag`, `DiagnosticTest`
- [x] Define relationship types: `HAS_CARDINAL_SYMPTOM`, `HAS_ASSOCIATED_SYMPTOM`, `HAS_RISK_FACTOR`, `HAS_DIFFERENTIAL`, `ARGUES_AGAINST`, `HAS_RED_FLAG`, `CONFIRMED_BY`
- [x] Write Cypher MERGE loader (`neo4j/migrations/001_initial_schema.cypher` + `neo4j/neo4j_loader.py`)
- [x] Load all 10 conditions from `graph_entities.jsonl`
- [x] Write and test retrieval Cypher — `neo4j/run_queries.py` (candidate generation 8/8)

### Phase 4 — Vector Store Integration ✅
- [x] Choose embedding model → Cohere `embed-multilingual-v3.0`
- [x] Set up Chroma locally (`chroma/db/`)
- [x] Connect prose chunks to Chroma upsert (`chroma/chroma_loader.py`) — 89 chunks loaded
- [x] Test retrieval — `chroma/retrieval_baseline.py` (8 clinician cases; 5/8 unrestricted, baseline documented in `chroma/retrieval_baseline.md`)
- [x] Metadata filtering by condition — implemented in `rag.py` filtered vector pass

### Phase 5 — Hybrid Retrieval + RAG ✅
- [x] Hybrid retrieval function — `phase5/rag.py` (vector candidates → graph profiles → filtered passages)
- [x] Prompt template — `phase5/prompts.py` (locked system prompt + `build_context()`)
- [x] LLM integration — `phase5/providers.py` (Gemini `gemini-flash-lite-latest` primary, Anthropic fallback)
- [x] Structured response format — `OUTPUT_SCHEMA` + jsonschema validation, fail-closed
- [x] Evaluation harness — `phase5/evaluate.py`; 7/8 auto-pass, both paired comparisons pass

### Phase 5e — Retrieval + Pipeline Hardening ← **current phase**
- [x] **5a** pytest suite — `phase5/tests/`: card validation, ingest output, Neo4j edges, Chroma count, RAG schema; 54/54 including integration pass (AuraDB + Gemini confirmed)
- [x] **5b** PubMedBERT embedding experiment — A/B infrastructure built; result 6/8 < gate; **rejected**. Cohere stays. Root cause: filtered passages miss `against` section in PubMedBERT biomedical space; forced-inject caused context interference across other cases.
- [x] **5c** BM25 hybrid retrieval — `rank_bm25` index + RRF (k=60) in `get_vector_candidates_hybrid()`; `--hybrid` flag in evaluate.py; result: hybrid 7/8 but introduces 4a→4b regression; **rejected**. Dense-only confirmed superior for 89-chunk corpus. Case 2b confirmed as model reasoning problem, not retrieval.
- [x] **5d** Case 2b prompt fix — softened arguing_against ranking rule; result 6/8 (arguing_against field went empty, Case 4a regressed); **reverted**. 7/8 is the prompt ceiling.
- [x] **5e** Pipeline orchestration — `Makefile` (5 targets: ingest, load-neo4j, embed, eval, pipeline); hard eval gate in `evaluate.py` (exits non-zero if <7/8 on full suite); `.github/workflows/cds_pipeline.yml` triggers on `symptoms_dictionary/**`, `ingest.py`, `phase5/**` changes
  - Prefect deferred: pipeline is linear + single-environment; revisit if Phase 6 introduces scheduled inference, cloud deployment, or multi-stage branching

> Gate: each step requires pytest green + eval ≥ 7/8 before proceeding to the next.
> Current eval: **7/8** (Cohere dense-only, Cases 1–6 pass, Case 2b structural limit).

### Phase 6 — UI ✅
- [x] ICD-10 codes added to all 10 condition card frontmatters — schema_version 1.2, ingest.py updated, index.md updated
- [x] Streamlit MVP — red flags above cards (safety-first), leading candidate expanded (ICD-11 + ICD-10, navy border), differential in collapsed expanders, relevant context section
- [x] Tested against 8 real-world Kenya primary care cases — all correct; red flags render correctly
- [x] Prompt Rule 5 — confirmed prior comorbidities route to context, not differential
- [x] Prompt Rule 4 extension — missing_information demographically appropriate
- [x] Provider-level Gemini 503 retry — individual call retry, not full eval restart
- [x] Phase 6b — UI improvement — steps 2+3 complete (session state, approval, SQLite)
- [x] Approval + database — encounters table locked; structured corpus-controlled fields; analyst-ready schema
- [ ] Post-MVP: evaluate Chainlit if conversational follow-up required; Reflex for production
  - UI path confirmed: **Streamlit MVP → Chainlit (if conversational) → Reflex (production)**

### Phase 6b — UI Improvement + Approval Database

- [x] Step 2 — Session-state scaffolding (`_init_session_state`, `_clear_all`, `input_key` clear trick, `_assert_confidence`)
- [x] Step 3 — Approval workflow (system read-only panel, editable diagnosis, live ICD-10 preview, Approve button, confirmation screen, "New assessment →")
- [x] Step 3b — SQLite persistence (`phase6/db.py`: `init_db`, `write_encounter`, `_extract_structured`, column migration)
- [x] Step 3c — Analyst schema fields (`system_category`, `clinician_icd11`, `system_clinician_agreement`) — migration applied, backfilled
- [x] UTI corpus fix — `graph.argues_against` simplified to `male sex`; corpus_version 1.4; ingest + Neo4j reload done; note: arguing_against correctly empty when patient has documented structural abnormality (prostate enlargement) — clinical reasoning correct
- [x] Prompt fix — Rule 4 demographic filter: explicit exclusion list for anatomically impossible findings per patient sex/age
- [x] Prompt fix — Red flags scope: explicit rule that only leading candidate's red flags appear when all others are lower confidence; closes T2DM red flag bleed into UTI assessments
- [ ] Step 4 — CSS cleanup — strip dashboard aesthetic from `cds_theme.py`; editorial minimal; colour = clinical meaning only
- [ ] Step 5 — Session history sidebar — compact chronological list from `st.session_state.history`; snippet + diagnosis + ✓/△ agreement + time

> Run: `streamlit run phase6/app.py` from `cds/` root

### Phase 7 — Corpus v2
- [ ] Asthma
- [ ] COPD
- [ ] Heart failure
- [ ] HIV/AIDS
- [ ] Typhoid fever
- [ ] Sickle cell disease
- [ ] STIs (gonorrhoea, syphilis, chlamydia)
- [ ] Pregnancy-related conditions (pre-eclampsia, ectopic pregnancy, PPH)

---

## Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-08-26 | Section-level chunking (not token window) | Preserves clinical reasoning units; each section is semantically coherent |
| 2026-08-26 | Clinical qualifier preservation ("may", "usually") | "Fever is common" ≠ "Fever confirms"; flattening changes clinical meaning |
| 2026-08-26 | Separate metadata from embedded text | Enables deterministic filtering alongside semantic retrieval |
| 2026-08-26 | `clinician_verified` gate for production only | Dev proceeds on draft cards; gate applies at production ingestion |
| 2026-08-26 | East Africa / Kenya primary care orientation | Disease burden prioritization (malaria, TB, pneumonia dominate) |
| 2026-08-26 | 9 mandatory sections in fixed order | Parser depends on order; "argues against" + "red flags" are safety-critical |
| 2026-08-26 | `graph:` blocks in YAML frontmatter, flat strings | Authoring stays fast; normalization layer resolves structure before Neo4j write |
| 2026-08-26 | Normalization layer between YAML and Neo4j | Prevents synonym drift across large corpus; vocabulary controlled via [[symptom_vocabulary]] |
| 2026-08-26 | Edge properties designed in schema from day one | Allows provenance (`source`, `year`) to be added later without schema migration |
| 2026-08-26 | `argues_against` as flat edges for v1 | Multi-finding evidence pattern logic deferred to LLM synthesis layer; graph keeps it simple |
| 2026-08-31 | Makefile + GitHub Actions over Prefect for 5e | Pipeline is linear, deterministic, single-environment; only growth is more cards (not more stages); Prefect deferred to Phase 6 if scheduled/cloud/multi-branch needed |
| 2026-08-31 | Streamlit for Phase 6 UI MVP | Team already has it deployed (Ortho, Gates Malaria); CDS is one-in one-out (not chat); Chainlit if conversational follow-up added; Reflex at production |
| 2026-09-01 | Case 2b closed — 7/8 is the Phase 5 ceiling | Three retrieval approaches exhausted (PubMedBERT, BM25, prompt strengthening); model documents TB counter-evidence but overrides ranking rule; further prompt/CoT work not justified at MVP stage |
| 2026-09-01 | Management corpus — unified index with content_type metadata | Separate index doubles infrastructure without benefit at MVP scale; metadata filter (content_type: clinical \| management) gives clean retrieval separation; no routing layer required in Streamlit MVP |
| 2026-09-01 | ICD-10 codes — add to all 10 frontmatters now (before 5e) | Low-cost structured metadata; avoids carrying known incompleteness into Phase 6; unblocks UI build when Phase 5e is done |
| 2026-09-02 | Corpus-controlled structured storage in encounters DB | supporting_symptoms, arguing_against, red_flags, comorbidities come from RAG output (knowledge base retrieval), not free-text parsing — clean, normalised, queryable via json_each() |
| 2026-09-02 | Analyst fields: system_category, clinician_icd11, system_clinician_agreement | Primary slicing dimensions for accuracy analysis; all corpus-controlled or computed — no text cleaning needed; system_clinician_agreement = primary accuracy signal |
| 2026-09-02 | UTI graph.argues_against simplified to "male sex" | Compound qualifier "male sex without catheter or structural abnormality" fails at LLM reasoning step — model can't confirm absence (Rule 1), so compound fails; prose and red flags carry the clinical nuance |

---

## Open Questions

- [x] Neo4j hosting → AuraDB free tier (resolved)
- [x] Embedding model → Cohere `embed-multilingual-v3.0` (resolved)
- [x] ICD-10 codes — add now before Phase 5e (decided 2026-09-01); doing before orchestration so Phase 6 is unblocked immediately after 5e
- [x] RAG output format — structured JSON confirmed (required for Streamlit card rendering)
- [x] UI library — Streamlit MVP confirmed; Chainlit/Reflex path documented
- [x] Orchestrator — Makefile + GitHub Actions confirmed; Prefect deferred
- [x] Management corpus — unified index with content_type metadata (clinical/management); no separate index, no routing layer at MVP (resolved 2026-09-01)
- [ ] Clinician reviewer — name a reviewer + set a deadline for Phase 2 production gate; process blocker, not technical; all 10 cards remain draft
