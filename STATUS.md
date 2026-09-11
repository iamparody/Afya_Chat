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

- [x] Define and document the evaluation checklist (below) — documented in STATUS.md

**Card evaluation checklist (one pass per new card):**
1. **Leading diagnosis** — does a representative presentation return the correct condition as leading candidate?
2. **Differentials** — are the returned differentials clinically plausible? Any spurious vector matches (e.g. obesity for epigastric pain)?
3. **Argues-against** — do argues-against items fire correctly when the counter-evidence is present in the presentation?
4. **Red flags** — are the correct red flags surfaced? Are they scoped to the leading candidate only (not leaking from lower-confidence candidates)?
5. **Missing information** — are the listed missing items clinically relevant discriminators, not generic history questions?
6. **Regression** — re-run the full 8-case eval baseline after each new card batch; confirm 7/8 maintained

- [ ] **Pending human action** — share checklist with Colleague 1 (evaluation) and Colleague 2 (LLM testing) before first new card ingest

---

### PF-3 — Complication vs. differential decision ✅ Done (2026-09-04)
> Iron deficiency anaemia appeared as a PUD differential — it is a complication (PUD causes anaemia through bleeding). The graph has no IS_COMPLICATION_OF concept. Decision needed before authoring cards that have clear complication relationships.

- [x] **Decision: accept as known limitation for now** — complications appearing as differentials filtered by clinical review; revisit at Phase 8 (disambiguation loop)
- [x] Added note to `prompts.py` `candidates[]` schema description: complications of a suspected diagnosis must not appear as candidates — place in `relevant_comorbidities_or_context` or `missing_information`

---

### PF-4 — Disambiguation loop design spec (lock before building)
> Agreed at high level. Gaps in spec will cause rework if code is written before these are decided.

- [x] **Ambiguity trigger**: no `high` confidence candidate AND ≥2 candidates share the same confidence tier (both `moderate`, or both `low`)
- [x] **Question selection logic**: extract `missing_information` items that appear in the top tied candidate(s) but differ between them — these are the discriminating questions; do NOT ask about missing_information items shared by all candidates (not discriminating)
- [x] **Max rounds**: 3 — after 3 rounds without a `high` confidence candidate, surface current best with explicit ambiguity note
- [x] **Answer format**: free text appended to presentation (keeps architecture simple; structured answers are Phase 9)
- [x] **Region/location**: do NOT add as a structured UI field — let it surface naturally as a clarifying question when region discriminates between tied candidates
- [x] **UI**: question cards displayed one at a time; "Skip" option on each (skipped questions noted as still missing); "Stop and get assessment" escape hatch at any round
- [ ] **Pending human action** — colleague review of this spec before implementation begins

---

### PF-5 — Regression test plan ✅ Documented (2026-09-04)
> Adding new conditions changes the vector space — existing test cases may behave differently. No plan currently exists for catching regressions.

- [x] After every batch of new cards (defined as every 2–3 cards), re-run `python phase5/evaluate.py`
- [x] Acceptable baseline: 7/8 (Case 2b is a known ceiling, not a regression)
- [x] If a previously passing case drops: investigate before ingesting the next card
- [x] Track eval results in this file after each run — format: `YYYY-MM-DD: X/8 after adding [card name(s)]`

**Eval history:**
- 2026-08-31: 7/8 baseline (dense-only Cohere, FIVE RULES prompt)
- 2026-09-02: 7/8 (after UTI fix, Rule 4 demographic filter, red flags scope fix)
- 2026-09-06: 6/8 measured (Cohere, TOP_N=9) after adding GERD, FD, Typhoid. Investigated Case 4a red flags inconsistency (empty vs populated across runs): root cause = Red flags section retrieved at variable position in context (ANN non-determinism), plus missing mandatory language in prompt. Fix: Red flags section now force-retrieved FIRST per condition (positional primacy) + prompt mandates non-empty red flags when [Red flags] section is present. Check strings reverted to corpus terms ["hyperglycaemic","hyperosmolar"]. PubMedBERT health check 3/8 (expected — different embedding space, not baseline). Cohere baseline rerun pending API reset (October 1). Projected ≥7/8.
- 2026-09-07: 7/8 restored after Asthma + Dengue (15 conditions, 134 chunks).
- 2026-09-09: 8/8 after Phase 7d environmental context integration (within stochastic bounds; Case 5 hypertension has no environmental signals). Three bugs fixed: (1) Chroma collection pollution from multiple runs — stable IDs (condition::section::j) prevent growth; (2) RED_FLAG_SECTION "Red flags" → "red_flags" — force-retrieve was silently failing; (3) n_results=n*3 too small for 134-chunk corpus — changed to min(500, count()). Added _enforce_arguing_against_ranking() post-hoc code-level swap. SIX RULES prompt (Rule 6 arguing-against). Case 2b known ceiling now addressed by code-level swap. 3 consecutive runs all 7/8.

---

## Phase 7 — Corpus Expansion + Environmental Context Layer

**Locked architecture (updated 2026-09-10):**
```
Patient presentation → RAG differential → Candidate-level gate
    ├── No environmental_signals on card → no_relevant_context (first-class result)
    └── Signals present → StaticCalendarProvider (signal gating, Phase 7 + Phase 9 MVP)
                    ↓
            EnvironmentalEvidence { signal, causal_distance, effect_type,
              effect_direction, strength, confidence, source, spatial_basis,
              temporal_window, data_age, data_status, explanation, condition }
                    ↓
                  Gemini

Independently (Phase 9 MVP):
    OpenMeteoProvider → RainfallFeatures (7/30/60d mm) → ContextResult.rainfall
    (audit trail only — does not gate signal activation until thresholds are calibrated)
```

**Locked principles:**
- Post-RAG gating — engine runs only for candidates with declared `environmental_signals`
- `no_relevant_context` is a valid first-class result, not an edge case
- Freshness (data_age/data_status) is separate from signal_confidence
- `StaticCalendarProvider` gates all signals in Phase 7 and Phase 9 MVP — CHIRPSProvider stub always falls back to it; source label = `static_calendar`
- `OpenMeteoProvider` provides ERA5-Land rainfall features attached to `ContextResult.rainfall` as audit trail; does NOT activate signals until thresholds are defined
- Lag-aware temporal matching using onset_date when available; falls back to encounter_date
- Location approximation in Phase 7: `patient_location → endemic_region → static calendar window`
- Card-level `strength`/`confidence` fields gate signal emission — no separate global threshold
- Outbreak detection is out of scope (separate surveillance layer, not part of diagnosis reasoning)

---

### 7a — Schema + ingestion (gates everything else)

**CLAUDE.md** ✅ Done (2026-09-04, updated 2026-09-09)

**`ingest.py`** ✅ Done (2026-09-09)
- [x] Parse `endemic_regions` from frontmatter → carry in chunk metadata
- [x] Parse `environmental_signals` block → carry in chunk metadata (JSON)
- [x] Validate signal names, pathways, effect_type, evidence_type, causal_distance against controlled vocabulary — warn on unknown or missing values
- [x] Increment expected `schema_version` to `"2.1"` in validation

**`neo4j_loader.py`** ✅ Done (2026-09-09)
- [x] Store `endemic_regions` as list property on Condition nodes
- [x] Store `environmental_signals` as structured properties — signal names and regions at minimum

**`causal_distance` field** ✅ Done (2026-09-09)
- Added `causal_distance: direct | indirect` to CLAUDE.md Controlled Vocabularies and frontmatter schema (schema_version 2.0 → 2.1)
- Colleague review: anaemia/prolonged_drought is indirect (drought → nutritional_vulnerability → iron deficiency); wording must reflect causal chain, not flatten to weather statement
- Backfilled all 7 signal cards: 6 direct (malaria ×3, AGE flooding, typhoid flooding, dengue), 6 indirect (AGE water_scarcity, typhoid water_scarcity, pneumonia ×2, anaemia, UTI)
- `phase7/context_engine.py`: minimal `EnvironmentalEvidence` dataclass with `causal_distance` field
- `phase7/tests/test_causal_distance.py`: 4/4 tests pass (direct + indirect schema validation + dataclass construction)

---

### 7b — Backfill existing cards with schema 2.0 fields
> Run after ingest.py is updated. Each card: add endemic_regions + environmental_signals → ingest → confirm 0 warnings.

- [x] **malaria.md** — signals: post_long_rains (strong), post_short_rains (moderate), flooding (moderate, requires: mosquito_exposure_high)
- [x] **acute_gastroenteritis.md** — signals: flooding (moderate, requires: unsafe_water), water_scarcity (moderate, requires: unsafe_water)
- [x] **typhoid_fever.md** — signals: flooding (waterborne, moderate), water_scarcity (moderate)
- [x] **dengue_fever.md** — signals: post_long_rains (vector_borne, coast)
- [x] **pneumonia.md** — signals: cold_dry_season (low, highland), dry_dusty_season (low, northern_kenya)
- [x] **anaemia.md** — signals: prolonged_drought (severity_modifier, asal)
- [x] **uti.md** — signals: heat_dehydration (low, severity_modifier)
- [x] **pulmonary_tb.md** — no environmental signals (socioeconomic driver)
- [x] **hypertension.md / type_2_diabetes.md / obesity.md / peptic_ulcer_disease.md / gerd.md / functional_dyspepsia.md / asthma.md** — no environmental signals; endemic_regions: nationwide
- [x] Re-ingest all after backfill: `python ingest.py` — 0 warnings, schema_version 2.0 on all cards (2026-09-09)
- [x] Reload Neo4j: `python neo4j/neo4j_loader.py`

---

### 7c — Context engine (`phase7/context_engine.py`) ✅ Done (2026-09-09)

**`EnvironmentalEvidence` dataclass**
- [x] Fields: `signal`, `causal_distance`, `effect_type`, `effect_direction`, `strength`, `confidence`, `source` (chirps|static_calendar), `spatial_basis` (endemic_region), `temporal_window` (lag min/max weeks), `data_age` (hours), `data_status` (fresh|stale), `explanation` (str), `condition` (str)
- [x] `no_relevant_context` sentinel result — returned when no candidates have signals OR all signals suppressed

**`StaticCalendarProvider`**
- [x] Kenya rainfall calendar: `_SIGNAL_ACTIVE_MONTHS` — 8 signals mapped to active month sets (June-August for post_long_rains, December-February for post_short_rains, etc.)
- [x] ENSO flag: `StaticCalendarProvider.ENSO_PHASE = "neutral"` — update annually from NOAA/KMD
- [x] Onset-date aware: `get_environmental_evidence()` uses onset_date as reference if provided, else encounter_date

**`CHIRPSProvider`**
- [x] Phase 9 stub — always falls back to StaticCalendarProvider; source label = "static_calendar"
- [x] Interface stable: `is_signal_active(signal_name, reference_date, region) -> (bool, str)` — Phase 9 fills in the body without changing rag.py or tests

**`get_environmental_evidence(candidates, encounter_date, patient_location, patient_exposures, onset_date) → list[EnvironmentalEvidence] | NO_RELEVANT_CONTEXT`**
- [x] Candidate-level gate: skip conditions with no `environmental_signals` on card
- [x] 4 sequential gates per signal: (1) region match — "nationwide" passes for any location; (2) exposure requirements; (3) seasonal activation via CHIRPSProvider; (4) strength/confidence
- [x] **Strength/confidence gate (locked rule from colleague review):**
  - `strength: low` + `confidence: low` → always suppress (covers indirect + low/low)
  - `strength: moderate` + `confidence: moderate` → pass with hedged explanation
  - `strength: strong` or `confidence: high` → pass as substantive evidence
- [x] `_passes_gate()` returns `(passes: bool, hedging_level: str)` — hedging_level feeds `_build_explanation()`
- [x] `_build_explanation()` — source-labelled, causal_distance-aware, hedged or substantive per gate result
- [x] Helper functions for testing: `_inject_signal_data()`, `_reset_signal_cache()`

**`ContextResult` dataclass (colleague design review)**
- [x] Return type: `ContextResult | str` — not `list | str`
- [x] `ContextResult.evidence` — signals that passed all 4 gates; inject into Gemini
- [x] `ContextResult.suppressed` — signals that matched gates 1-3 but failed strength/confidence gate; audit trail preserved, do NOT inject
- [x] `NO_RELEVANT_CONTEXT` returned only when nothing reaches gate 4 (no signals declared, or all fail region/exposure/seasonal)
- [x] `EnvironmentalEvidence.suppression_reason` — non-empty on suppressed signals; e.g. "strength:low/confidence:low below emission threshold"
- [x] Rationale: "matched but suppressed" != "no signal declared" — Phase 8/9 calibration needs the distinction

**Tests:** `phase7/tests/test_context_engine.py` — 10/10 pass (2026-09-09)
1. Asthma: NO_RELEVANT_CONTEXT (no signals)
2. AGE + April + unsafe_water: flooding fires
3. AGE + April + no exposure: NO_RELEVANT_CONTEXT (gate 2, before gate 4)
4. CAP low/low: ContextResult.suppressed not NO_RELEVANT_CONTEXT -- audit trail
5. IDA + drought: indirect, lag {4,16} in temporal_window, hedged explanation
6. onset_date overrides encounter_date -- baseline NO_RELEVANT_CONTEXT without it
7. Region mismatch: NO_RELEVANT_CONTEXT (gate 1)
8. nationwide region: passes for all patient_location values
9. CHIRPSProvider fallback: source_label = static_calendar in Phase 7
10. Multiple candidates: both signals preserved in result.evidence

---

### 7d — RAG + app integration ✅ Done (2026-09-09)

**`phase5/rag.py`**
- [x] `run()` accepts `patient_location`, `patient_exposures`, `encounter_date`, `onset_date` as optional params (all default None; backward-compatible)
- [x] Step 3b added after filtered passages: calls `get_environmental_evidence(top_conditions, enc_date, location, exposures, onset_date)`
- [x] `env_evidence = result.evidence if isinstance(result, ContextResult) else []` — no injection when NO_RELEVANT_CONTEXT or all suppressed
- [x] `build_context()` called with `env_evidence=env_evidence`
- [x] `sys.path.insert(0, str(ROOT))` added — ensures `phase7` importable from any calling context (evaluate.py, rag.py standalone)

**`phase5/prompts.py`**
- [x] `build_context()` accepts optional `env_evidence=None`
- [x] When non-empty, appends `## Environmental context` section after clinical evidence — source-labelled, framed as prior adjustment not clinical evidence, explicitly states clinical findings take precedence

**`phase6/app.py`**
- [x] `_ENDEMIC_REGIONS` and `_EXPOSURES` constants from controlled vocabulary
- [x] `patient_location` and `patient_exposures` added to session state defaults and `_clear_all()`
- [x] `st.expander("Patient context (optional)")` below presentation textarea: `st.selectbox` for location, `st.multiselect` for exposures; keyed to `input_key` so they reset on Clear
- [x] Both `rag.run()` calls (initial analysis + disambiguation refinement) pass `patient_location`, `patient_exposures`, `encounter_date=datetime.now()`
- [x] `onset_date` not exposed as UI field in Phase 7 (free-text presentation carries onset; structured onset_date deferred to Phase 9)

**Eval note:** No system prompt changes — env context injected as a labelled section in build_context() only, framed as prior evidence.

---

### 7e — Validation ✅ Done (2026-09-09)

**Context engine unit tests** — `phase7/tests/test_context_engine.py`: 10/10 pass (see 7c)

**Prompt injection contract tests** — `phase7/tests/test_7d_integration.py`: 6/6 pass (2026-09-09)
- env_evidence=None -> no section in prompt
- env_evidence=[] -> no section in prompt (empty list is a no-op)
- ContextResult(evidence=[], suppressed=[...]) -> suppressed signals do NOT reach Gemini
- Active evidence -> ## Environmental context section present with source label
- 3-arg build_context() call backward-compatible (evaluate.py unaffected)
- patient_location=None -> region gate skipped -> signal fires (benefit of doubt)

**RAG eval:** `python phase5/evaluate.py` → **8/8** (2026-09-09)
- All 8 cases auto-pass; paired confidence comparisons pass (2a→2b, 4a→4b)
- Gate: PASS (≥7/8)
- Result: baseline preserved; 8/8 vs prior 7/8 is within stochastic variation (Case 5 hypertension is the known stochastic case; has no environmental signals so env context was not injected)
- No leading-candidate changes from environmental context addition
- No confidence regressions

**Eval history update:**
- 2026-09-09: 8/8 after Phase 7d environmental context integration

---

### 7f — New condition cards (Tier 1 — pending clinician review)
> Workflow: author → colleague clinical review → ingest → Neo4j reload → RAG test

- [ ] **Cholera** — signals: flooding (waterborne, strong), water_scarcity (moderate)
- [ ] **Rift Valley fever** — signals: flooding (zoonotic, requires: livestock_contact)
- [ ] **Chikungunya** — signals: post_long_rains (vector_borne, coast)

**Already authored (awaiting review):**
- [x] GERD — authored, RAG tested ✅
- [x] Functional dyspepsia — authored, RAG tested ✅
- [x] Typhoid fever — authored, RAG tested ✅
- [ ] Asthma — signals: cold_dry_season (low), dry_dusty_season (low)

**Tier 2 (after ≥18 conditions):**
COPD, Heart failure, HIV/AIDS, Sickle cell, PID, Malaria in pregnancy, Meningococcal meningitis, Leptospirosis

---

## Phase 8 — Interactive Disambiguation (Follow-up Question Loop)
> Build after Phase 7 has ≥15 conditions confirmed working and context engine validated.

### Design gates ✅ All resolved
- [x] Ambiguity threshold: no high-confidence candidate AND ≥2 candidates share same confidence tier
- [x] Max rounds: 3 — forces result on round 4 regardless
- [x] Question generation: discriminating `missing_information` items (SOME but not ALL tied candidates)

### Implementation steps
- [x] `phase8/disambiguate.py` — `is_ambiguous()`, `get_discriminating_questions()`, `enrich_presentation()`
- [x] Session state machine wired into `phase6/app.py` — disam_round, disam_questions, base_presentation, disam_skip_to_result
- [x] `_render_disambiguation()` — question text inputs, "Refine assessment" (disabled if no questions), "Stop" escape hatch
- [x] Auto-exit when no discriminating questions generated after enrichment (empty-questions edge case)
- [x] Enrichment loop: `enrich_presentation → rag.run → advance round or exit`
- [x] `phase8/evaluate_disambiguation.py` — 5-case eval suite, gate 4/5 ✅ PASS (2026-09-07)
  - d1 Upper GI (PUD/GORD/FD) ✓ — enrichment shifts GORD to high
  - d2 Lower abdominal (UTI/AGE) ✓ — enrichment shifts to UTI
  - d3 Early fever (Malaria/Dengue coastal) ✓ — enrichment confirms Dengue high
  - d4 Negative (Diabetes full triad) ✓ — correctly suppressed
  - d5 Kisumu fever (Malaria/Typhoid) ✗ — Typhoid high confidence, corpus-knowledge ceiling not a loop defect

### Known ceiling
- Symptom-chip UX (clickable discriminating features from corpus graph instead of free-text inputs) deferred — requires corpus lookup at app layer; implement after Phase 9 data is in place or if disambiguation loop shows low clinical uptake

---

## Phase 8b — Reasoning Evaluation Harness ✅ Done (2026-09-10)

**Commits:**
- `7d30a0a` — initial harness (rubric.py + evaluate_reasoning.py), dry-run 48/50
- `7e4d238` — frozen 9-dim baseline 78/86 (90%); N/A logic + rubric semantics fixes
- `eca05af` — Rule 7 added to prompts.py (SIX → SEVEN RULES)
- `bee6358` — confidence_consistency scorer (10th dim); 10-dim baseline 87/96 (90%)
- `a247974` — CI integration: deterministic gate 90%, full judge run as artifact

**Frozen baselines (never collapse):**
- Deterministic: 48/50 (96%) — `--no-judge`, 5 dims × 5 cases
- Judge 10-dim: 87/96 (90%) — 5 cases, 2 N/A — commit `bee6358`

**10-dim rubric:**
- Deterministic: leading_diagnosis, differential_relevance, confidence_range, red_flags, confidence_consistency
- LLM judge: supporting_features, arguing_against_accuracy, missing_information_relevance, question_quality
- Special: diagnostic_shift (requires initial + enriched result)

**CI gate:** `make eval-reasoning` → `--no-judge --gate 90` (hard gate); full judge run non-blocking artifact per SHA.

**Evidence-boundary intervention sequence:**
- Baseline arguing_against 5/10, missing_information 7/10
- Rule 7 (minimal): missing_information → 10/10; arguing_against → 4/10
- Rule 7b (explicit prohibition list): arguing_against → 3/10; reverted
- confidence_consistency: 10/10 — no intervention needed

**Deferred:** arguing_against positive-construction wording — next prompt experiment when eval set expands.

---

## Phase 9 — Live Environmental Data + Empirical Calibration

### Phase 9 MVP ✅ Done (2026-09-10)

**Commits:**
- `37f8e43` — `OpenMeteoProvider` (ERA5-Land via Open-Meteo Historical API); `RainfallFeatures` frozen dataclass; `RainfallProvider` protocol; wired into `get_environmental_evidence()` → `ContextResult.rainfall`
- Source validation: `phase9/validate_rainfall.py` — Open-Meteo/ERA5-Land vs NASA POWER/MERRA-2, 5 sites × 3 reference dates
- CHIRPS adjudication: `phase9/compare_chirps.py` + `phase9/chirps_fetcher.py` — UCSB GeoTIFF via rasterio; 180 files over 3 windows; Kisumu and Mombasa discrepancies adjudicated
- Findings: `phase9/validation_findings.md` — source decision table, raw comparison, CHIRPS pin

**Source decision (2026-09-10):**

| Ecology | ERA5-Land acceptability | Basis |
|---------|------------------------|-------|
| lake_basin (Kisumu) | Acceptable | CHIRPS confirms ERA5-Land within 1.15–1.45x; MERRA-2 was over-estimating ~4–5x |
| highland (Nairobi) | Acceptable | ERA5-Land and MERRA-2 agree within 1.5x across all three dates |
| arid_semi_arid | Acceptable | Both sources agree on low/near-zero in dry periods |
| coast (Mombasa) | **Acceptable in wet season; biased in dry season** | ERA5-Land over-estimates ~6.7x in Jan–Feb; CHIRPS and MERRA-2 agree on lower value |

**What remains — in order:**
- [ ] Establish multi-year historical ERA5-Land baseline per ecology (≥5 years) — prerequisite for thresholds
- [ ] Define signal activation thresholds per signal per ecology (coast Jan–Feb requires CHIRPS, not ERA5-Land)
- [ ] Replace `StaticCalendarProvider` signal gating with observed-rainfall thresholds per signal
- [ ] For coast ecology Jan–Feb: decide CHIRPS direct (ClimateSERV) or ERA5-Land bias correction

---

## Phase 6b — Remaining Steps
> Steps 2–6 complete. Step 7 pending.

- [x] Step 2 — Session state scaffolding (`_init_session_state`, Clear button, `input_key` increment)
- [x] Step 3 — Approval workflow + SQLite (`db.py`, `write_encounter()`, clinician diagnosis input, ICD-10 preview)
- [x] Step 4 — CSS cleanup + editorial minimal UI + Phosphor icons + sidebar cleanup
- [x] **Step 6 — Full HTML/CSS presentation layer rewrite (2026-09-08)**
  - `phase6/cds_theme.py`: complete rewrite — CSS design tokens (`--c-*`), 30+ `.cds-*` component classes, inline Phosphor SVG icons, `--max-w: 860px` content constraint
  - `phase6/app.py`: all renderer functions replaced — `_render_draft_banner`, `_render_presentation_collapsed`, `_badge`, `_feature_list`, `_render_leading_candidate`, `_render_red_flags`, `_render_differential` (`<details>/<summary>` rows), `_render_relevant_context`, `_render_disambiguation` (radio chips), `_render_approval`, `_render_approval_confirmed`
  - Settled layout hierarchy: draft banner → collapsed presentation → red flags → leading candidate → uncertainty/disambiguation → differential → clinical context → approval
  - High confidence uses blue (`#1D6FA4`) not green — draft data must not imply validated certainty
- [x] **Step 7 — Session history sidebar** ✅ Done (6962ba5) — approved encounters from `st.session_state.history`; compact chronological list; patient snippet + system diagnosis + ✓/△ agreement indicator + time; KNBS location normalization (162 PLACE_ALIASES, 13 CROSS_COUNTY_PLACES)

---

## Outstanding Corpus Quality Issues
> Clinical content verification required before any card moves to `clinician_verified`.

- [ ] **anaemia.md — WHO Hb threshold update:** card cites WHO 2011 haemoglobin cutoff document; WHO published revised guidance in 2024. Reconcile thresholds before clinical validation. Ref: WHO 2024 haemoglobin cutoffs publication.
- [ ] **anaemia.md — ferritin language:** `serum ferritin <30 μg/L` as uncomplicated threshold is too broad. WHO 2020 guidance explicitly changes ferritin interpretation in inflammation/infection, including higher deficiency thresholds. Card wording must distinguish uncomplicated from inflammatory states before ingestion. Ref: WHO 2020 ferritin guideline.
- [ ] **type_2_diabetes.md — ethnicity risk factor:** `East African ethnicity` in `risk_factors` is too broad a population category for individual diagnostic reasoning. Replace with specific, evidence-based risk factors (e.g. higher T2DM prevalence in urban East African populations, dietary pattern associations) before clinical validation. Colleague flagged risk of becoming an inappropriate diagnostic shortcut.

---

## Outstanding RAG Quality Issues
> Tracked separately from corpus expansion — these are retrieval/prompt quality items.

- [ ] **PUD retest post ICD-11 fix** — run the PUD presentation case through the RAG; confirm `system_icd11` shows `DA62` (not DA60); confirm weight loss no longer appears in supporting_features
- [ ] **Obesity as PUD differential (retrieval quality)** — obesity appearing as a differential for epigastric pain is vector overlap in Chroma, not a clinical match; investigate during Phase 7 once more conditions are added (may self-resolve when GERD/dyspepsia dilute the vector space); if still occurring at 15+ conditions, tune retrieval threshold
- [ ] **Obesity card — secondary/hormonal causes missing (corpus quality)** — current card likely scoped to simple dietary/lifestyle obesity; missing: hypothyroidism, PCOS, Cushing's syndrome, pregnancy-related weight gain, medication-induced (corticosteroids, antipsychotics); these belong in "Important differential diagnoses" and "Features that argue against"; colleague flagged, clinician review will formally gate it; watch during testing
- [ ] **Region as follow-up question (Phase 8 design note)** — do NOT add patient_location as a structured UI field; instead let the disambiguation loop surface it as a clarifying question when region is discriminating between tied candidates (e.g. Dengue vs Malaria); `missing_information` in RAG output already has the slot for this

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
| [[peptic_ulcer_disease]] | DA62 | Gastroenterological | 🟡 draft | — | — |
| [[acute_gastroenteritis]] | 1A09 | Gastroenterological/Infectious | 🟡 draft | — | — |
| [[typhoid_fever]] | 1A07 | Infectious | 🟡 draft | — | — |
| [[functional_dyspepsia]] | DA94 | Gastroenterological | 🟡 draft | — | — |
| [[gerd]] | DA22 | Gastroenterological | 🟡 draft | — | — |
| [[asthma]] | CA23 | Respiratory | 🟡 draft | — | — |
| [[dengue_fever]] | 1D2Z | Infectious | 🟡 draft | — | — |

**Legend:** 🟡 draft · 🔵 under_review · ✅ clinician_verified

**Production gate:** 0 / 15 cards verified. Dev work proceeds freely on draft cards.

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

### Phase 5e — Retrieval + Pipeline Hardening ✅
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
- [x] **Step 4 — CSS cleanup** — editorial minimal; Phosphor icons; sidebar cleanup
- [x] **Step 6 — Full HTML/CSS presentation layer rewrite (2026-09-08)** — design tokens, 30+ component classes, settled layout hierarchy (draft banner → presentation → red flags → leading → disambiguation → differential → context → approval)
- [x] **Step 7 — Session history sidebar** ✅ Done (6962ba5) — KNBS location normalization (162 PLACE_ALIASES, 13 CROSS_COUNTY_PLACES, cross-county disambiguation); session history; compact chronological list; snippet + diagnosis + ✓/△ agreement + time

> Run: `streamlit run phase6/app.py` from `cds/` root

### Phase 7 — Environmental Context Layer ✅ Done (2026-09-09)
See full detail in Phase 7 section above (steps 7a–7e complete).
- [x] Schema 2.1, context engine, ContextResult audit trail
- [x] rag.py + prompts.py + app.py wired; 22 tests pass; eval 8/8
- [ ] **7f** — 3 new condition cards (Cholera, Rift Valley fever, Chikungunya) — blocked on clinician review

### Phase 8 — Interactive Disambiguation Loop ✅ Done (2026-09-07)
See Phase 8 section above.

### Phase 8b — Reasoning Evaluation Harness ✅ Done (2026-09-10)
See Phase 8b section above.

### Phase 9 — Live Rainfall Provider 🟡 Partial

- [x] `phase7/rainfall_providers.py` — `RainfallProvider` protocol, `OpenMeteoProvider` (ERA5-Land via Open-Meteo Historical API), `RainfallFeatures` frozen dataclass
- [x] Wired into `get_environmental_evidence()` → `ContextResult.rainfall` (audit trail; does not gate signals)
- [x] Source validation: `phase9/validate_rainfall.py` — 5 sites × 3 reference dates vs NASA POWER/MERRA-2
- [x] CHIRPS adjudication: `phase9/compare_chirps.py` + `phase9/chirps_fetcher.py` — 180 files, Kisumu + Mombasa discrepancies resolved; source decision = ERA5-Land accepted (coast Jan–Feb bias documented)
- [x] Findings: `phase9/validation_findings.md` — auditable table + source decision per ecology
- [ ] Historical ERA5-Land baseline per ecology (≥5 years) — prerequisite for threshold calibration
- [ ] Signal activation thresholds per ecology (coast Jan–Feb: CHIRPS; others: ERA5-Land)
- [ ] Replace `StaticCalendarProvider` signal gating with observed-rainfall thresholds

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
| 2026-09-10 | Open-Meteo/ERA5-Land accepted as Phase 9 live rainfall source | CHIRPS adjudication confirms ERA5-Land within 1.15–1.45x at Kisumu (lake_basin); MERRA-2 was over-estimating. Sole exception: Mombasa coast Jan–Feb dry season (~6.7x over-estimate); CHIRPS must be used for coast dry-season threshold calibration. No architecture changes required. |
| 2026-09-10 | OpenMeteoProvider feeds audit trail only (does not gate signals) | Thresholds are not yet calibrated; activating rainfall gating without a characterised baseline would introduce uncalibrated priors. StaticCalendarProvider remains the gating mechanism until thresholds are derived from ≥5-year historical baseline. |
| 2026-09-11 | Two approved card authoring methods: LLM-assisted drafting from WHO/MOH PDFs (preferred) and PrimeKG scaffold + clinical authorship | LLM drafting cuts authoring time from hours to ~20 min of clinician review; PrimeKG provides disease-symptom-differential scaffolds for conditions with clear global data but limited Kenya guidelines. Neither removes clinician review gate. Documented in CLAUDE.md Governance Rules. |

---

## Open Questions

- [x] Neo4j hosting → AuraDB free tier (resolved)
- [x] Embedding model → Cohere `embed-multilingual-v3.0` (resolved)
- [x] RAG output format → structured JSON confirmed
- [x] UI library → Streamlit MVP confirmed; Chainlit/Reflex path documented
- [x] Orchestrator → Makefile + GitHub Actions confirmed; Prefect deferred
- [x] Phase 9 source — Open-Meteo/ERA5-Land accepted; CHIRPS required for coast Jan–Feb calibration only (resolved 2026-09-10)
- [ ] Clinician reviewer — name a reviewer + set a deadline for Phase 2 production gate; process blocker, not technical; all 15 cards remain draft
- [ ] Phase 9 historical baseline — which site/date range, how many years, storage format for ERA5-Land historical pull
- [ ] Coast dry-season — CHIRPS directly (ClimateSERV) or ERA5-Land bias correction for coast Jan–Feb threshold calibration
