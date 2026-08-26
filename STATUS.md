# CDS Project Status Tracker

#status #tracker

← Back to [[CLAUDE]] | [[README]] | [[index]]

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

### Phase 2 — Graph Extraction + Normalization ← **current phase**
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

### Phase 3 — Neo4j Load
- [ ] Choose Neo4j hosting (AuraDB free tier vs. local Docker) ← **open question**
- [ ] Define node labels: `Condition`, `Symptom`, `Sign`, `RiskFactor`, `Differential`, `RedFlag`, `DiagnosticTest`
- [ ] Define relationship types: `HAS_CARDINAL_SYMPTOM`, `HAS_ASSOCIATED_SYMPTOM`, `HAS_RISK_FACTOR`, `HAS_DIFFERENTIAL`, `ARGUES_AGAINST`, `HAS_RED_FLAG`, `CONFIRMED_BY`
- [ ] Write Cypher MERGE loader (`neo4j/migrations/001_initial_schema.cypher`)
- [ ] Load all 10 conditions from `graph_entities.jsonl`
- [ ] Write and test retrieval Cypher — given symptom list, return ranked candidate conditions + differentials

### Phase 4 — Vector Store Integration
- [ ] Choose embedding model (OpenAI `text-embedding-3-small` or Cohere) ← **open question**
- [ ] Set up Chroma locally
- [ ] Connect `ingest.py` prose chunks output to Chroma upsert
- [ ] Test retrieval — sample symptom queries, inspect returned chunks
- [ ] Metadata filtering by category, ICD-11, review_status

### Phase 5 — Hybrid Retrieval + RAG
- [ ] Hybrid retrieval function — Cypher (graph candidates) + Chroma (prose chunks) → merged context
- [ ] Prompt template: patient presentation → hybrid context → candidate diagnoses + discriminators
- [ ] LLM integration (Claude API — `claude-sonnet-4-6`)
- [ ] Structured response format: diagnoses ranked, discriminating features, red flags, ICD codes
- [ ] Evaluation harness — benchmark test cases with known diagnoses

### Phase 6 — UI
- [ ] Real-time typing → streaming symptom query → ranked diagnosis suggestions
- [ ] Clinical documentation output — structured note with ICD-10/11, diagnosis, symptoms, red flags
- [ ] ICD-10 codes added to all cards (currently ICD-11 only) ← **needed before UI**

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

---

## Open Questions

- [ ] Neo4j hosting — AuraDB free tier vs. local Docker?
- [ ] Embedding model — OpenAI `text-embedding-3-small` vs. Cohere for East Africa clinical text?
- [ ] ICD-10 codes — add to frontmatter now or defer to UI phase?
- [ ] Management corpus — separate RAG index or unified with diagnostic corpus?
- [ ] RAG output format — structured JSON for UI consumption or free-text narrative?
