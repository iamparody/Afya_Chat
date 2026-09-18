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
- 2026-09-14: 8/8 after router seam refactor (RetrievalRouter in rag.py, behaviourally equivalent)
- 2026-09-14: 8/8 after presentation map integration (PresentationMapClassifier, 9 pathways, provenance labels)
- 2026-09-14: 8/8 after comorbidity context engine (comorbidity_engine.py wired; Fixture A pregnancy alert confirmed)
- 2026-09-14: 8/8 after YAML corpus pipeline batch migration complete (15/15 cards; production graph_entities.jsonl swapped; Fixture A + B confirmed)
- 2026-09-15: 7/8 GATE PASS after AFI expansion (Bacterial meningitis + Chikungunya, 22 conditions/198 chunks). Case 2b remains known ceiling. Coverage 2/2 (Case 7 Appendicitis, Case 8 Chikungunya).
- 2026-09-16: 8/8 GATE PASS after Brucellosis (23 conditions/207 chunks). Two-source pattern: WHO/FAO/OIE 2006 + PMC systematic review + Kenya pastoral data. Coverage 3/3 (Case 9 Brucellosis added).
- 2026-09-17: 8/8 GATE PASS after Leptospirosis (24 conditions/216 chunks). WHO 2003 + Medscape 2026 (two-source pattern; age-of-evidence caveat in sources.yaml). Coverage 4/4 (Case 10 Leptospirosis added).
- 2026-09-17: 7/8 GATE PASS after COPD (25 conditions/225 chunks). MOH Vol 2 2024 + Medscape 2025 (two-source pattern). Coverage 5/5 (Case 11 COPD added). Integrity gate implemented in corpus_pipeline/ingest_yaml.py (feat/corpus-integrity-gate, pending merge).
- 2026-09-18: 7/8 GATE PASS after Acute pyelonephritis (26 conditions/234 chunks) — **with a caveat, read before interpreting a future 6/8**. MOH Vol 2 §15.2.1 + EAU 2026 (two-source pattern). Coverage 6/6 (Case 12 Acute pyelonephritis added — leads correctly, 4/4 auto checks). Full suite 303/303 including integration. Gate measured on the identical corpus state as committed.
  - **Real regression, found and fixed.** First two runs scored 6/8 and 7/8 with Case 3 (UTI vs AGE) failing because the new card took the leading candidate. Cause was authoring beyond the source: `suprapubic discomfort` had been added to `graph.associated_symptoms` but is **not** in Vol 2's clinical features for pyelonephritis (fever, flank pain, nausea, vomiting, dysuria, frequency, urgency), and suprapubic pain is lower abdominal — it blurred the exact UTI/pyelonephritis boundary GU-MSP-01 exists to draw. Removed. Added `absence of loin pain` and `absent costovertebral angle tenderness` to `graph.argues_against`, which were genuinely missing. Case 3 primary diagnosis correct in all runs since.
  - ~~Residual: Case 3 intermittently trips the prohibited substring `'no dysuria'`~~ — **RESOLVED 2026-09-18 by the UTI enrichment pass** (see next entry). The hypothesis was correct: the new card had diluted UTI's share of the urinary semantic space, shifting Case 3's lead from UTI to AGE, after which the model argued against UTI by naming the absent symptom. Strengthening the UTI card restored its rank and the failure mode disappeared. Case 3 now passes 6/6.
  - **Case 5 (Hypertension) failed on the `end-organ` red flag in one run and passed in the next** — pre-existing stochastic red-flag retrieval, documented 2026-09-06. Not related to this card.
  - A reasoning-discipline paragraph ("absence of documentation is not a negative finding") was drafted into the card's `argues_against` and then **removed**: that rule belongs in the SEVEN RULES prompt, which already enforces it. Corpus cards describe the condition; duplicating prompt logic into card prose puts it into every retrieved chunk.

---

### 7f — New condition cards (Tier 1)

**GI domain — COMPLETE (2026-09-15):**
- [x] Cholera — commit (Gate 2 closure test, Method A, WHO-AFRO 2023)
- [x] Shigellosis (acute dysentery) — committed
- [x] Intestinal helminthiasis — committed
- [x] Appendicitis — committed (recognition-and-refer scope, MOH 2024)
- [x] Acute viral hepatitis A — committed (MOH 2024 + Medscape supplementary)

**AFI domain — in progress:**
- [x] Bacterial meningitis — committed (MOH 2024; MSP-01 + MSP-02 closed)
- [x] Chikungunya — committed (WHO 2025 fact sheet; RP-03 addressed)
- [x] Brucellosis — committed (WHO/FAO/OIE 2006; two-source pattern; 2026-09-16)
- [x] Leptospirosis — committed (WHO 2003 + Medscape 2026; age-of-evidence caveat in sources.yaml; 2026-09-17)
- [ ] Rickettsial illness — governance decision: C (deferred — no qualifying source; RP-06/RP-07 blocked)

**Respiratory domain — COMPLETE (2026-09-17):**
- [x] COPD — committed (MOH Vol 2 2024 + Medscape 2025; two-source pattern; 2026-09-17)

**Genitourinary domain — in progress (contract: `docs/domain_contracts/genitourinary.md`):**
> Source restricted to MOH Vol 2 Chapter 15 (Level 2-3). Vol 3 (Level 4-6) is deliberately excluded — mixed-tier authoring produces a retrieval corpus that surfaces investigations unavailable at the target level of care. Neither MOH volume carries differential or argues-against content for any Chapter 15 condition, so every card here uses the two-source pattern: EAU for the infective/urological group, KDIGO for the renal group.
- [x] Acute pyelonephritis — committed (MOH Vol 2 §15.2.1 + EAU 2026; ICD-11 GB51; 2026-09-18)
- [x] Urinary tract infection — enrichment pass committed 2026-09-18 (corpus_version 1.6 → 1.7). Added `Acute pyelonephritis` to `graph.differentials` — it was absent, despite upper-vs-lower being the card's most important distinction. Added the Vol 2 §15.1 referral trigger (fever ≥38 °C, flank pain, or vomiting — any one is sufficient) to `red_flags`. Strengthened the male-UTI rule to match the source: Vol 2 states UTI in a male is complicated in all cases, where the card had qualified it as "a man under 50 without a precipitating factor". MOH Vol 2 2024 §15.1 added to card sources. **Side effect: resolved the Case 3 `'no dysuria'` caveat from the pyelonephritis entry above.** `DIFFERENTIATED_FROM` edges still outstanding — require a `gu_pairs.yaml` and a domain argument on `neo4j/pairwise_loader.py`, which currently hardcodes `afi_pairs.yaml`
- [ ] UTI card carries 3 pre-existing compound-term warnings in `graph.argues_against` (`negative nitrite and negative leukocyte esterase on dipstick`, `external dysuria with vaginal discharge`, `normal urinalysis and negative culture`) — these violate the CLAUDE.md no-conjunctions rule and predate this domain. Not fixed in the enrichment pass to keep the retrieval-affecting change set small; fix separately and re-run the gate
- [ ] Acute bacterial prostatitis — Vol 2 §15.4.1 is the thinnest section in the chapter; EAU supplementation mandatory. ICD-11 needs an `icd_search_term` override — WHO API returns the imprecise `GA91.Y` for "acute prostatitis"
- [ ] Acute glomerulonephritis — one card (Vol 2 covers it at both §15.5 and §15.7.1); ICD-11 GB40
- [ ] Nephrotic syndrome — ICD-11 GB41. ⛔ Vol 2 §15.6 clinical features open with a verbatim duplicate of the §15.4.1 prostatitis bacteraemia line — a copy-paste defect in the source. Do not encode bacteraemia symptoms on this card
- [ ] Acute kidney injury — Vol 2 §15.8.1 + KDIGO 2012 (the 2026 AKI/AKD guideline is a public review draft and is not citable)
- [ ] Chronic kidney disease — Vol 2 §15.8.2 + KDIGO 2024. Vol 2 Table 15.5 (CKD criteria) is empty in the extracted text; take staging from KDIGO directly
- [ ] Nephrolithiasis — **deferred**: no Vol 2 chapter. Retained as a `differentials` term on the pyelonephritis, AKI and CKD cards. Consequence: pathway G6 (acute flank colic) has no owned card, and GU-MSP-05 / GU-RP-03 / GU-RP-05 have no evaluation fixtures

**Excluded:**
- Rift Valley fever — outbreak-only, not routine primary-care differential (AFI domain contract §3.4)

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

## Decision Layer Fix — IN PROGRESS
> Clinical testing of all 10 new conditions (Cholera → COPD) revealed systematic failures: 10/10 HIGH confidence returned, disambiguation gate never fires, argues-against shows "None documented" even when Neo4j graph evidence exists.
>
> **Asana:** GID 1218579291213545 — "CDS — Fix decision layer: confidence calibration, disambiguation gate, CandidateDecisionContext"

**Root cause:** Confidence is LLM-generated from absolute evidence strength, not from score gap between candidate #1 and #2. The disambiguation gate (`is_ambiguous()` in `phase8/disambiguate.py`) checks LLM confidence — so it never fires. Argues-against is also LLM-generated, not grounded from Neo4j `ARGUES_AGAINST` relationships.

**Work order:**
- [x] Step 1 — Instrument `rag.py`: log vector rank, graph score, fused position, supporting evidence, ARGUES_AGAINST, LLM confidence, disambiguation fired, final candidate — no behaviour change ✅ 2026-09-17
- [ ] Step 2 — Deterministic ranking: normalise vector + graph scores → single comparable score; compute margin between #1 and #2; thresholds derived from Step 1 distributions, not invented ✅ 2026-09-17
- [ ] Step 3 — Decouple confidence from ambiguity: confidence = evidence strength of #1; ambiguity = score margin (deterministic Python); HIGH + ambiguous is a valid state; disambiguation = ambiguity AND pairwise discriminator exists ✅ 2026-09-17
- [ ] Step 4 — Wire `CandidateDecisionContext`: Neo4j `ARGUES_AGAINST` → typed structured input → LLM explanation only; "None documented" structurally impossible when graph evidence exists ✅ 2026-09-17
- [ ] Step 5 — Rendering + grounding: red flag `documented` vs `check_for` labels; no regional priors or species names unless quoted from retrieved evidence ✅ 2026-09-17

**Files:** `phase5/rag.py`, `phase5/prompts.py`, `phase8/disambiguate.py`
**Gate:** confidence is auditable; ambiguity is independently determined; HIGH + ambiguous supported; appropriate cases trigger disambiguation; graph ARGUES_AGAINST evidence reaches final candidate; 8-case baseline ≥7/8

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

| Card | ICD-11 | ICD-10 | Category | Review Status | Reviewer | Last Reviewed |
|------|--------|--------|----------|--------------|----------|---------------|
| type_2_diabetes | 5A11 | E11 | endocrine | ✅ clinician_verified | Colleague | 2026-09-14 |
| hypertension | BA00 | I10 | cardiovascular | ✅ clinician_verified | Colleague | 2026-09-14 |
| obesity | 5B81 | E66 | endocrine | ✅ clinician_verified | Colleague | 2026-09-14 |
| malaria | 1F40 | B54 | infectious | ✅ clinician_verified | Colleague | 2026-09-14 |
| pulmonary_tb | 1B10 | A15 | respiratory | ✅ clinician_verified | Colleague | 2026-09-14 |
| pneumonia | CA40 | J18 | respiratory | ✅ clinician_verified | Colleague | 2026-09-14 |
| uti | GC08 | N39.0 | urological | ✅ clinician_verified | Colleague | 2026-09-14 |
| anaemia | 3A00 | D50 | haematological | ✅ clinician_verified | Colleague | 2026-09-14 |
| peptic_ulcer_disease | DA62 | K27 | gastroenterological | ✅ clinician_verified | Colleague | 2026-09-14 |
| acute_gastroenteritis | 1A09 | A09 | gastroenterological | ✅ clinician_verified | Colleague | 2026-09-14 |
| typhoid_fever | 1A07 | A01.0 | infectious | ✅ clinician_verified | Colleague | 2026-09-14 |
| functional_dyspepsia | DA94 | K30 | gastroenterological | ✅ clinician_verified | Colleague | 2026-09-14 |
| gerd | DA22 | K21 | gastroenterological | ✅ clinician_verified | Colleague | 2026-09-14 |
| asthma | CA23 | J45 | respiratory | ✅ clinician_verified | Colleague | 2026-09-14 |
| dengue_fever | 1D2Z | A90 | infectious | ✅ clinician_verified | Colleague | 2026-09-14 |
| cholera | — | A00.9 | infectious | 🟡 draft | — | — |
| shigellosis | — | A03.9 | infectious | 🟡 draft | — | — |
| intestinal_helminthiasis | — | B82.9 | infectious | 🟡 draft | — | — |
| appendicitis | DC92 | K37 | gastroenterological | 🟡 draft | — | — |
| acute_viral_hepatitis_a | 1E50.0 | B15.9 | infectious | 🟡 draft | — | — |
| bacterial_meningitis | 1C1Z | G00.9 | infectious | 🟡 draft | — | — |
| chikungunya | 1D67 | A92.0 | infectious | 🟡 draft | — | — |
| brucellosis | 1B96 | A23 | infectious | 🟡 draft | — | — |
| leptospirosis | 1C10 | A27.9 | infectious | 🟡 draft | — | — |
| copd | CA22 | J44 | respiratory | 🟡 draft | — | — |

**Legend:** 🟡 draft · 🔵 under_review · ✅ clinician_verified

**Production gate:** 15/25 cards clinician_verified. 10 cards authored after the 2026-09-14 review are draft — blocked from production ingest until a second review pass.
Outstanding: ICD code verification for comorbidity-specific codes (e.g. Malaria in pregnancy combinations) — flagged by reviewer.

---

## Pipeline Build Tracker

### Phase 1 — Corpus (Markdown Cards) ✅
- [x] Condition card schema designed (9 sections, YAML frontmatter)
- [x] 10 condition cards authored (draft quality)
- [x] Shared glossary — 24 terms defined ([[glossary]])
- [x] Machine-readable index created ([[index]])
- [x] `graph:` blocks added to all 10 cards (7 relationship keys per card)
- [x] [[symptom_vocabulary]] created — canonical term list, synonym blacklist
- [x] Clinician review — all 15 cards ✅ (2026-09-14); outstanding: ICD code verification for comorbidity-specific codes flagged by reviewer
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
- [x] **5b** PubMedBERT — 6/8, rejected. Code removed (chore commit 098e173). Cohere dense-only confirmed.
- [x] **5c** BM25 hybrid — 7/8 but 4a→4b regression, rejected. Code removed (098e173). Revisit only on measurable retrieval failure; corpus size alone is not a trigger.
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
- [ ] **7f** — Cholera card (new, Gate 2 closure test — Method A from WHO-AFRO 2023 guideline); Chikungunya card already exists and validated; Rift Valley fever excluded from AFI domain (outbreak-only, not routine primary-care differential — see domain contract §3.4)

### Phase 8 — Interactive Disambiguation Loop ✅ Done (2026-09-07)
See Phase 8 section above.

### Phase 8b — Reasoning Evaluation Harness ✅ Done (2026-09-10)
See Phase 8b section above.

### Corpus Pipeline Experiment — yaml-as-canonical (parallel, isolated) ✅ Batch migration complete (15/15) — 0 unexpected diffs — production graph_entities.jsonl swapped — 8/8 eval PASS
> Parallel experiment only. Existing Markdown pipeline untouched until all 4 acceptance criteria pass.
> Full spec: see memory/project_corpus_pipeline_experiment.md

**Build order:**
- [x] `corpus_pipeline/schema.py` — Pydantic models for `condition.yaml` (all frontmatter fields, 9 sections, graph block, environmental signals) ✅ 6c4735c
- [x] Migrate 2–3 cards to `condition.yaml` (malaria, pulmonary_tb, pneumonia) ✅ 6c4735c — finding: existing cards had `category: infectious / respiratory` (invalid vocab); schema caught it; fixed to single primary category
- [x] `corpus_pipeline/schema.py` — hedging vocabulary expanded (2026-09-14): "suggests", "argues", "some", "most", "common", "should", "considered" added; fixes false positives for legitimate clinical probability language; schema regression PASS (0 errors across 8 YAML cards after fix)
- [x] `corpus_pipeline/validator.py` — pre-review automated checks (vocabulary, ICD format, section completeness, graph terms, cross-card consistency) ✅ — 0 errors, 12 warnings across 8 cards; all warnings are pre-existing compound graph terms from source Markdown cards
- [x] `corpus_pipeline/ingest_yaml.py` — reads `condition.yaml` → identical `chunks.jsonl` + `graph_entities.jsonl` ✅ — 72 chunks, 8 graph records, 0 unknown terms; outputs to corpus_pipeline/output/
- [x] `corpus_pipeline/markdown_gen.py` — pure template rendering: `condition.yaml` → `.md` (no inference or logic) ✅ — 8/8 generated; known omission: intro paragraph not in schema, diff.py will flag
- [x] `corpus_pipeline/diff.py` — artifact diff: existing `.md` vs generated `.md`; flags missing content, polarity changes, silent omissions ✅ — Gate 1 PASS: 0 unexpected clinical differences; 8 accepted normalizations (symbol→words) in `accepted_diffs.json`; exact-hash matching + stale fixture detection
- [x] **Batch 2 migration (2026-09-14):** asthma, dengue_fever, type_2_diabetes, acute_gastroenteritis, hypertension — Gate 1 PASS (0 unexpected, 0 stale); Gate 3 PASS (0 prose diffs → trivially equivalent); category corrections: `endocrine / metabolic` → `endocrine`, `gastroenterological / infectious` → `gastroenterological` (invalid vocab, flagged CORRECTED not DIFFERS)
- [x] Equivalence gate: run `make eval` / `make eval-disam` / `make eval-reasoning` against yaml pipeline output ✅ — Gate 4 PASS (2026-09-14)

**Acceptance criteria (all 4 must pass before any migration decision):**
- [x] YAML represents existing cards without clinical content loss — verified by `diff.py` ✅ **Gate 1 PASS** (2026-09-14): 0 unexpected diffs, 0 stale fixture entries; 8 accepted normalizations (symbol→words) matched exactly via hash
- [~] Method A/B produce cleaner validated drafts than current Markdown authoring — **Gate 2: CONDITIONALLY PASS** (2026-09-14): 4/5 dimensions pass with strong evidence; author effort for new-card authoring (not migration) remains the sole unvalidated component
- [x] New front-end produces equivalent Chroma + Neo4j retrieval artifacts — verified at candidate level ✅ **Gate 3 PASS** (2026-09-14): graph entities identical; chunk embeddings 0.9957–0.9998 cosine similarity; embedding differences do not produce observed retrieval divergence
- [x] Existing eval gates hold: 8/8 RAG · 4/5 disambiguation · 90% reasoning ✅ **Gate 4 PASS** (2026-09-14): RAG 8/8 · Disambiguation 4/5 (d5 known corpus ceiling) · Reasoning 94% (55/58, deterministic subset, --no-judge; acceptance threshold ≥90%; not comparable to frozen 87/96 full 10-dim rubric)

**Gate 2 dimension record (2026-09-14):**
- Validation feedback: PASS — caught `category: infectious / respiratory` invisible for months in Markdown; diff.py found 2 genuine content errors in CAP before review
- Completeness: PASS — schema makes omission structurally visible; authors cannot miss a required field silently
- Editability: PASS — structured keys remove display-string memory requirement; known representation-boundary decision: intro paragraph is not in the YAML schema by design (YAML = structured clinical content; generated .md = document/presentation layer). This is sound provided the intro is generated or otherwise derived; if intro contains authoritative clinical content not captured elsewhere, add an `intro` field to the schema before scaling
- Provenance: PASS — enforced at schema level; improvement over Markdown
- Author effort: CONDITIONAL — migration of 3 cards demonstrated; new-card authoring from a source document (Method A or B) untested; clinician YAML friction unverified

**Gate 2 closure test** (first genuinely new card, not a migration): measure time to first valid draft; validator errors and causes; sections/fields the author struggles with; whether schema is understood without developer intervention; whether clinical content is lost or distorted; subjective comparison with old workflow. If this passes, Gate 2 becomes PASS.

**Final record (2026-09-14):** Gates 1, 3, and 4 PASS. Gate 2 CONDITIONALLY PASS. YAML migration and technical authoring are validated; clinician-led new-card authoring remains the sole unvalidated workflow component. Broader corpus equivalence to be established through batch migration and validation.

**Batch migration progress:** 15/15 cards migrated to YAML (all complete 2026-09-14). Batch 3: obesity, uti, anaemia, peptic_ulcer_disease, gerd, functional_dyspepsia, typhoid_fever. diff.py: 0 unexpected diffs, 0 stale across all 15 pairs. Production graph_entities.jsonl swapped to YAML-derived (15 conditions, corpus_version 1.3 for malaria). 8/8 eval gate passed post-swap. Fixture A + B confirmed: comorbidity semantic boundary holds.

**Next:** Gate 2 closure test — author Cholera as first genuinely new card from WHO/MOH PDF (Method A); measure validator friction, time to first valid draft, author effort.

**Excluded from this experiment:** WHO APIs, PostgreSQL, SNOMED CT, separate ingestion service, agentic authoring layer, PrimeKG mapper (separate task).

**Domain scaling:** `docs/domain_contracts/acute_febrile_illness.md` — domain contract for first production-grade domain; Section 2 (condition inventory) is the critical path before any new card is authored under this domain.

---

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

## Retrieval Architecture — Locked Direction (2026-09-14)

**Two locked principles — not to be revisited without a documented failure trigger:**
- The router refactor must preserve current retrieval behaviour exactly. Any evaluation change after the refactor is a regression until explained.
- The presentation map is a boost/prior and audit signal, never an exclusion gate. A condition absent from the map must not disappear from the candidate set.

**Build sequence:**
- [x] 1. Router seam refactor — `rag.py` retrieval abstracted behind `RetrievalRouter`; behaviourally equivalent; eval must hold at 8/8 RAG · 4/5 disam · 94% reasoning (2026-09-14, 8/8 confirmed)
- [x] 2. Presentation map integration — boost + provenance labels per candidate (`map-supported` / `retrieval-only` / `map+retrieval`) (2026-09-14, 8/8 confirmed)
- [x] 3. Neo4j pairwise-discrimination schema — DIFFERENTIATED_FROM relationship + indexes; afi_pairs.yaml (source of truth); pairwise_loader.py; all 17 pairs dry-run validated (2026-09-14)
- [x] 4. Section 4 pairwise matrix (domain contract) — 17 pairs complete (2026-09-14): 3 mandatory safety + 14 required; 5 pending governance decisions
- [x] 5. Graph relationship schema migration — ASSOCIATED_WITH / COMPLICATED_BY / REQUIRES_CONTEXT; neo4j/migrations/003_comorbidity_schema.cypher; :ClinicalContext node (constraint + label index); 6 relationship property indexes (2026-09-14)
- [x] 6. Comorbidity context engine — `phase7/comorbidity_engine.py`; `ComorbidityAlert` dataclass; `get_comorbidity_alerts()` reads YAML-pipeline output (schema 2.2); injected via `build_context()` as `## Comorbidity and clinical context alerts`; Fixture A verified: Malaria `missing_information` now includes pregnancy status (2026-09-14, 8/8 eval preserved)
- [ ] Future components (BM25, cross-encoder reranker, query expansion) — added only when a measured retrieval failure justifies them; corpus size alone is not a trigger

**Target retrieval stack:**
```
Presentation
    ↓
Pathway classifier → boost signal (not gate)
    ↓
RetrievalRouter [ Dense + Neo4j (today) | ↌ BM25 on failure evidence ]
    ↓
Candidates [ labelled: map-supported / retrieval-only / map+retrieval ]
    ↓
Reranker (passthrough initially — fusion slot)
    ↓
Evidence retrieval → Reasoning → Disambiguation → Safety
    ↓
Clinician decision → Encounters DB → (future) feedback signal
```

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
| 2026-09-14 | Retrieval architecture: router seam + boost model | Presentation map is a boost/prior, not an exclusion gate. RetrievalRouter abstracts retrieval behind a stable interface; future components (BM25, cross-encoder) plug in without touching outer pipeline logic. Trigger for new components: measured retrieval failure, not corpus size. |
| 2026-09-14 | Graph relationship taxonomy — four distinct clinical relationships | DIFFERENTIATED_FROM (competing diagnosis, built); ASSOCIATED_WITH (comorbidity/context — e.g. pregnancy, HIV); COMPLICATED_BY (complication — e.g. anaemia, AKI); REQUIRES_CONTEXT (clinically material missing information). Pregnancy is not a differential or complication — it is a context that changes management and coding. Schema migration for ASSOCIATED_WITH / COMPLICATED_BY / REQUIRES_CONTEXT to follow router seam refactor. |
| 2026-09-14 | Comorbidity graph node contract | ASSOCIATED_WITH → :Condition (ICD-coded comorbid condition, e.g. Malaria in pregnancy). COMPLICATED_BY → :Condition (ICD-coded complication). REQUIRES_CONTEXT → :ClinicalContext (clinical variable — a question, not a diagnosis: name slug, label, prompt, icd_modifier). Malaria-in-pregnancy has no standalone card (§3.4 exclusion) but IS modeled via ASSOCIATED_WITH + REQUIRES_CONTEXT. Three-tier corpus model: Disease corpus / Clinical contexts / Complications. Mature corpus target: 200–500 conditions; 60–80 is first validated tranche, not ceiling. |
| 2026-09-14 | Corpus scope bounded by domain contracts | Inclusion criterion: routine primary-care diagnostic relevance + Kenya primary-care treatment pathway + defensible authoritative source. Expansion domain-by-domain, not ad hoc. Hundreds of infectious diseases exist but most fail the inclusion criterion. |
| 2026-09-15 | Vector store migration intent — Supabase + pgvector | ChromaDB is local-per-collaborator. Intended migration: Supabase + pgvector as shared cloud vector store (same Postgres instance as encounters DB — unified data layer). Migrate when collaboration is active and sharing need is real. eval gate must hold post-migration. |
| 2026-09-14 | Comorbidity context engine — Phase 7 analogy | Same 3-layer pattern as environmental context: corpus cards declare comorbidity_signals (presentation_indicators, demographic gate, effect, missing_info_prompt); engine scans presentation text deterministically; injects labelled alert into LLM via build_context(). ICD is base code + alert note — system does not assert unconfirmed comorbidity. Builds after router seam + map integration. |

---

## Open Questions

- [ ] **Clinician review — 10 new cards** — schedule a second review pass for Cholera, Shigellosis, Helminthiasis, Appendicitis, Hepatitis A, Bacterial Meningitis, Chikungunya, Brucellosis, Leptospirosis, COPD before production ingest
- [ ] **AFI source governance** — Brucellosis ✅ Leptospirosis ✅ committed. Rickettsial illness → deferred (no qualifying source; revisit when WHO or regional guideline available)
- [ ] **Phase 9 historical baseline** — site/date range, years, storage format for ERA5-Land historical pull
- [ ] **Coast dry-season** — CHIRPS directly (ClimateSERV) or ERA5-Land bias correction for coast Jan–Feb threshold calibration
- [ ] **ICD code verification** — comorbidity-specific codes (Malaria in pregnancy combinations) flagged by reviewer; resolve before production ingest
