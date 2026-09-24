# Domain Evaluation Protocol

**Purpose:** Ensure each condition domain is retrieval-valid and reasoning-valid before corpus expansion continues. Prevents card-by-card firefighting by treating the domain — not the individual card — as the unit of evaluation.

**First applied:** Cardiovascular domain, September 2026, after Case 5 (incidental hypertension) exposed that retrieval ranked Hypertensive Crisis above Essential Hypertension for an asymptomatic elevated BP presentation.

---

## Workflow: B → A → C → D → E

| Phase | Action | Card changes? |
|-------|--------|---------------|
| **B** | Map confusable pairs from existing corpus — observation only | No |
| **A** | Document protocol + define minimal schema + update ingestion | No |
| **C** | Capture Dense/BM25/RRF baseline for all confusable pairs | No |
| **D** | Author retrieval anchors for domain cards | Yes — first edits |
| **E** | Re-ingest, measure before/after, run both gates | Yes |

**Hard rule: Phase C must be completed and recorded before any card modifications (Phase D).** An agent must not "helpfully" fix cards while establishing the baseline.

---

## Phase B — Confusable-pair mapping

**Observation only.** Read existing corpus cards. Do not author anchors, suggest fixes, or edit anything.

**Output: confusable-pair matrix**

| Condition A | Condition B | Why retrieval can confuse them | What distinguishes them | Relationship type |
|-------------|-------------|-------------------------------|------------------------|-------------------|

**Relationship types:**
- **Direct** — same or similar presenting complaint; genuinely competing diagnosis at retrieval
- **Partial** — overlap exists but usually distinguishable by one strong discriminating feature
- **Contextual** — shared terminology at keyword level but not at presentation level

**Also capture:**
- Cross-domain confusable pairs (cardiovascular ↔ respiratory, etc.)
- Missing-card relationships — pairs that should be confusable but where no reciprocal card exists. Record as gaps; do not invent relationships.
- Topology sketch — text graph of edges labelled Direct/Partial/Contextual

**Important distinction:** Phase B identifies *clinical confusability*. Phase C establishes *retrieval confusability*. These are not the same. A clinically plausible pair only becomes a retrieval problem if the system demonstrates actual rank overlap.

---

## Phase A — Schema definition and documentation

**No card changes.** Define the minimal schema addition, update ingestion and validation, document the protocol.

**Schema version:** bump `schema_version` from `"2.2"` to `"2.3"` when adding retrieval_anchors to a card. Old `"2.2"` cards remain valid — fields are optional.

**Minimal schema addition (from Phase B findings):**

```yaml
retrieval_anchors:
  positive:
    - "<phrase a clinician would use in a presentation that should retrieve this card>"
    - "..."
confusable_with:
  - "<Condition Name as it appears in conditions_vocabulary.md>"
  - "..."
```

**`confusable_with` scope:** list only pairs that can participate in the current evaluation corpus. Future candidates belong in Phase B topology documentation, not in card frontmatter.

**Authoring principles for `positive` anchors (applied in Phase D):**

> "What language would a clinician realistically use in a presentation that should cause this card to be retrieved rather than its nearest confusable?"

Anchors must be:
- Phrased as presentation language, not diagnostic labels
- Specific enough to discriminate from confusables
- Not generic symptom names that appear in many conditions

Anchors must not be:
- Diagnostic conclusions ("confirmed hypertension")
- Synonyms of the condition name
- Compound criteria joined by AND/OR

---

## Phase C — Retrieval baseline

**No card changes.** Run the retrieval pipeline for each confusable pair and record Dense/BM25/RRF ranks and margins.

**Phase C presentations are evaluation fixtures.** They must not be added to `retrieval_anchors`, modified after the baseline is recorded, or replaced between Phase C and Phase E. The before/after comparison is only valid if both phases use identical presentation text. An agent must not "improve" a fixture presentation to make Phase E look better.

**Baseline procedure:**

For each confusable pair, author representative presentations that cover clinically distinct variants of the retrieval boundary. Store them in `experiments/retrieval_baselines/<domain>/presentations.md` before running any measurements. Use the Case 5 debug pattern:

```python
# From cds/phase5/ directory:
python -c "
from rag import _bm25_candidates, _rrf_candidates, get_vector_candidates
import chromadb, cohere, os
from dotenv import load_dotenv
load_dotenv('../.env')

presentation = '<presentation text>'
co = cohere.Client(os.environ['COHERE_API_KEY'])
chroma = chromadb.PersistentClient(path='../chroma/db')
col = chroma.get_collection('cds_conditions')
emb = co.embed(texts=[presentation], model='embed-english-v3.0', input_type='search_query').embeddings[0]
vec = get_vector_candidates(co, col, presentation, query_embedding=emb)
bm25 = _bm25_candidates(presentation)
rrf = _rrf_candidates(vec, bm25)
# Print top 10 for each
"
```

**Record format (per confusable pair, per presentation):**

```text
Pair: <Condition A> ↔ <Condition B>
Presentation: "<text>"

Before (Phase C baseline):
  Correct card (<Condition A>):
    Dense rank: N
    BM25 rank:  N
    RRF rank:   N
  Confusable (<Condition B>):
    Dense rank: N
    BM25 rank:  N
    RRF rank:   N
  RRF margin: correct_score - confusable_score = X
  Status: correct_leads | confusable_leads | tied
```

Store baseline records in `experiments/retrieval_baselines/<domain>/`.

---

## Phase D — Author retrieval anchors

**First card modifications.** Back-fill domain cards with `retrieval_anchors.positive` and `confusable_with` using Phase B topology and Phase C baseline as evidence.

**Authoring constraint:** Do not write anchors to make a specific test case pass. Answer the clinical question: what presentation language should retrieve this card over its confusable?

**Gate before beginning Phase D:** Phase C baseline file must exist and be recorded for all direct confusable pairs in the domain.

**After authoring each card:**
1. Run `corpus_pipeline/validator.py` — must be 0 errors
2. Run batch ingest: `python corpus_pipeline/ingest_yaml.py corpus/`
3. Reload Chroma: `python chroma/chroma_loader.py`
4. Reload Neo4j: `python neo4j/neo4j_loader.py`

---

## Phase E — Evaluation and before/after comparison

**Two gates, both required.**

### Gate 1 — Retrieval gate (per confusable pair)

Re-run the Phase C retrieval measurement for each pair. Record post-fix results using the same format. Report:

```text
Pair: <Condition A> ↔ <Condition B>
Presentation: "<text>"

Before → After:
  Correct card rank (RRF): N → N
  Confusable rank (RRF):   N → N
  RRF margin: X → X
  Result: improved | unchanged | regressed
```

A result is **improved** when either of these conditions holds, and the correct card does not regress in rank:

```
(rank_before > rank_after AND margin_after > margin_before)
OR
(rank_before == 1 AND rank_after == 1 AND margin_after > margin_before)
```

The second condition handles the ceiling case: if the correct card was already ranked 1, rank cannot improve, but a margin increase still represents a meaningful retrieval improvement (the system is more certain).

A rank improvement without margin increase is **ambiguous** — record it but do not count as improved.
A superficial rank change without margin improvement is **unchanged**.
A correct card that regresses in rank is **regressed** — blocks Phase E gate regardless of margin.

### Gate 2 — Reasoning regression gate

```
python phase5/evaluate.py
```

Must score ≥7/8. If Case 5 (or other boundary cases) now passes consistently (≥3/3 standalone runs), document the resolution explicitly.

**Domain commit is blocked until both gates pass.**

---

## Evaluation units

**Correct unit:** confusable pair + representative presentation.

**Wrong unit:** condition count (e.g. 8/28 conditions covered = 29% is misleading).

A condition may have multiple confusable pairs; another may have none. The evaluation denominator is:

```
number of direct confusable pairs × representative presentations per pair
```

Partial and contextual pairs are secondary — evaluate them after direct pairs pass.

---

## Retrieval constants (source locations)

| Constant | Value | Location |
|----------|-------|----------|
| `TOP_N_CANDIDATES` | 9 | `phase5/rag.py` |
| `RRF_K` | 60 | `phase5/rag.py` |
| `AMBIGUITY_MARGIN_THRESHOLD` | 0.20 | `phase5/rag.py` |
| Chroma collection | `cds_conditions` | `chroma/chroma_loader.py` |
| Embed model | `embed-english-v3.0` | `phase5/rag.py` |

---

## Cardiovascular domain — Phase B topology (September 2026)

**Conditions in corpus (4):** Essential Hypertension (BA00.Z, draft), Hypertensive Crisis (BA03, clinician_verified), Pulmonary Embolism (BB00.Z, draft), Deep Vein Thrombosis (BD71, clinician_verified).

**Direct confusable pairs (priority — Phase C/D/E targets):**
- Essential Hypertension ↔ Hypertensive Crisis
- Pulmonary Embolism ↔ Deep Vein Thrombosis

**Partial cross-domain pairs (documented, not Phase C targets yet):**
- PE ↔ Community-Acquired Pneumonia
- PE ↔ Asthma
- Hypertensive Crisis ↔ Bacterial Meningitis

**Missing-card gaps (one-way language only):**
- HC ↔ AMI (no AMI card)
- HC ↔ Pre-eclampsia (no pre-eclampsia card)
- DVT ↔ Cellulitis (no cellulitis card)
- DVT ↔ Superficial Thrombophlebitis (no card)
- Essential Hypertension ↔ Secondary hypertension forms (no cards)

**Key observation from Case 5 retrieval debug:**
Essential Hypertension Dense rank >9, BM25 rank 2, RRF rank 6 for presentation "47F, headache. BP 168/102 on arrival. No chest pain, no neurological symptoms, no visual changes, no shortness of breath." HC BM25 rank 1, RRF rank 2. Root cause: "headache + BP" keywords hit HC chunks hard; Essential Hypertension corpus underrepresents the incidental/asymptomatic discovery pattern.

**This is Phase C's pre-fix baseline for the Essential Hypertension ↔ HC pair (partial — Case 5 presentation only). Full Phase C baseline requires authoring additional representative presentations before Phase D begins.**
