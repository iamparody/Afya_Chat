# Diagnostic RAG — Knowledge Corpus

Structured diagnostic presentation cards for use as a RAG retrieval layer.

## Purpose

Each file is a self-contained diagnostic card covering one condition. The corpus is designed for symptom-based and presentation-based retrieval, not for management guidance. Treatment protocols are out of scope for this corpus and live in a separate `management/` corpus when built.

## Retrieval intent

A retrieval query should return candidate diagnoses plus their key differentials and discriminating features — not a single answer. The RAG layer is one step in a reasoning chain:

```
User presentation
    → symptom / presentation retrieval
    → candidate diagnoses
    → differential + discriminating features
    → guideline / diagnostic-criteria retrieval
    → clinical reasoning
```

## Directory structure

```
diagnostic_rag/
├── symptoms_dictionary/
│   ├── index.md                      machine-friendly index with ICD-11 and category
│   ├── type_2_diabetes.md
│   ├── hypertension.md
│   ├── obesity.md
│   ├── malaria.md
│   ├── pulmonary_tb.md
│   ├── pneumonia.md
│   ├── uti.md
│   ├── anaemia.md
│   ├── peptic_ulcer_disease.md
│   └── acute_gastroenteritis.md
└── README.md
```

## File format

Each condition file uses YAML frontmatter for structured metadata and clinical prose for semantic content.

**Frontmatter fields:**
```yaml
condition:        canonical condition name
icd11:            WHO ICD-11 code — verify before production
category:         disease category
corpus_version:   content batch version — changes when clinical content is updated
schema_version:   document format version — changes when frontmatter structure changes
review_status:    draft | clinician_reviewed | clinician_verified
reviewed_by:      clinician identifier (required for production ingestion)
last_reviewed:    YYYY-MM-DD
sources:
  - organization: source organisation name
    title:        exact guideline or document title
    year:         publication year (leave blank if unverified)
```

`corpus_version` and `schema_version` are distinct. Updating clinical content increments `corpus_version`. Changing the frontmatter structure (adding or renaming fields) increments `schema_version`. Never conflate the two.

**Production ingestion rule:** The ingestion pipeline must reject any card with `review_status: draft`. Only `clinician_verified` cards are permitted in production mode.

**Section order (all sections required):**

| Section | Purpose |
|---|---|
| Cardinal symptoms | Core presenting features with mechanism where useful |
| Associated symptoms and signs | Broader clinical picture and examination findings |
| Diagnostic features | Objective findings and criteria that support or establish the diagnosis |
| Predisposing factors | Epidemiological and patient-level risk — not diagnostic evidence |
| Typical presentation | What the patient looks like when they walk in |
| Important differential diagnoses | Competing diagnoses with discriminating features |
| Features that argue against this diagnosis | Findings that reduce the probability of this diagnosis |
| Red flags | Safety-critical features requiring urgent escalation |
| Diagnostic context | When to test, what test, confirmation criteria, limitations |

## Clinical governance workflow

```
Clinical source
      ↓
Draft condition card  (review_status: draft)
      ↓
Clinical review + corrections
      ↓
Clinical approval  (review_status: clinician_verified, reviewed_by: <ID>)
      ↓
Versioned corpus
      ↓
Ingestion  (rejects draft cards in production mode)
      ↓
Evaluation
      ↓
RAG
```

## ICD-11 codes

All ICD-11 codes should be verified against the current WHO ICD-11 browser before production use.
WHO ICD-11 browser: https://icd.who.int/browse/2024-01/mms/en

## Ingestion design

### Three-layer model

Every condition file produces three distinct outputs at ingestion time:

| Layer | Content | Purpose |
|---|---|---|
| Embedded text | Condition name + section context + clinical prose | Semantic retrieval |
| Metadata | ICD-11, category, section type, governance fields, provenance | Deterministic filtering |
| Source file | Original markdown, untouched | Human review and editing |

These layers are separate. Metadata must not contaminate embedded text. Embedded text must not be the raw markdown file.

### Pipeline flow

```
Markdown file
    │
    ├── Parse frontmatter ──────────────────→ metadata (condition, icd11, category,
    │                                          review_status, corpus_version, etc.)
    │
    ├── Parse H1 heading ───────────────────→ condition identifier (injected into
    │                                          every chunk's embedded text)
    │
    ├── Parse section heading + prose ──────→ chunk text (see format below)
    │                                          + section metadata
    │
    └── Parse source citation ─────────────→ provenance metadata (source_organization,
                                               source_title, source_year)
                                               NOT embedded text
```

Parse first, then route. Never embed the whole file and chunk afterward — that loses control over what each embedding represents.

### Embedded chunk format

Each chunk's embedded text should follow this structure:

```
{Condition name} — {Section name}

{Clinical prose, stripped of markdown syntax only}
```

Example:
```
Malaria — Cardinal symptoms

Fever is a common presenting feature and may be accompanied by chills,
rigors, headache, myalgia, and malaise...
```

The condition name and section name must appear in the embedded text, not only in metadata. Once a file is split into section chunks, the H1 heading no longer provides context — the condition anchor must be injected explicitly. This is useful redundancy: the same condition and section information lives in both the text (for semantic retrieval) and metadata (for filtering).

### What to strip vs preserve

**Strip from embedded text:**
- YAML frontmatter block (`---` ... `---`)
- Markdown syntax characters (`**`, `*`, `##`, `#`, `_`) — strip the formatting, keep the words
- Source citation line — move to provenance metadata
- Empty governance fields (`reviewed_by: ""`) — metadata only, never embedded

**Keep in embedded text:**
- All clinical prose
- Section context prefix (condition + section name, injected by the pipeline)
- Numeric thresholds, lab values, clinical criteria — these are semantic content

**Blank `year` in sources means "not specified in the source record,"** not "unknown publication year." Do not infer or fill in years from memory.

**Never strip clinical qualifiers.** The following carry clinical meaning that must survive ingestion:

> "usually" / "may" / "rarely" / "particularly in children" / "absence of X makes Y less likely" / "not sufficient to confirm the diagnosis"

`"Fever is common in malaria"` is not the same as `"Fever confirms malaria"`. Stripping hedging language converts probabilistic clinical reasoning into false certainty. The ingestion pipeline must be conservative about transforming prose.

### Metadata per chunk

```json
{
  "condition": "Malaria (unspecified)",
  "icd11": "1F40",
  "category": "infectious",
  "section": "cardinal_symptoms",
  "corpus_version": "1.1",
  "schema_version": "1.1",
  "review_status": "draft",
  "reviewed_by": null,
  "last_reviewed": null,
  "sources": [
    {"organization": "WHO", "title": "Guidelines for Malaria", "year": "2023"},
    {"organization": "WHO", "title": "Severe Malaria Treatment Guidelines", "year": "2023"}
  ]
}
```

Governance and provenance fields belong here. The application can use `source_organization` and `source_title` to attribute retrieved evidence without re-embedding citation text.

### Chunking strategy

Chunk by section header, not by fixed token window. Each section (`Cardinal symptoms`, `Diagnostic features`, `Red flags`, etc.) is one natural semantic unit and should produce one chunk in most cases.

If a section is long enough to require splitting, split at paragraph boundaries — never mid-sentence. Clinical prose paragraphs are complete reasoning units; breaking them mid-thought destroys the clinical relationship.

Conventional sliding-window overlap is not needed when chunking by section. If a section spans multiple paragraphs where the first establishes context and the second explains a discriminator, keep them in the same chunk rather than splitting for size uniformity.

**Semantic completeness is more important than equal chunk sizes.**

### Tables (future cards)

If future condition cards introduce tables, do not strip them. Convert to prose before embedding:

```markdown
| Finding     | Significance          |
| ----------- | --------------------- |
| Haemoptysis | Raises concern for TB |
```

becomes:

```
Finding: Haemoptysis. Significance: Raises concern for pulmonary tuberculosis.
```

The current prose-only format avoids this problem, but the rule applies as the corpus grows.

### Production gate

The ingestion pipeline must reject any card where `review_status` is not `clinician_verified` in production mode. Development and staging environments may ingest `draft` cards for testing. This enforcement belongs in the ingestion script, not in the markdown files.

---

## Scaling notes

**Current approach (v1, <50 conditions):** One markdown file per condition, hand-authored. The filesystem handles 2000 files without issue. The human curation bottleneck is the real constraint — you cannot hand-write 2000 condition cards. At that scale, files must be generated from a structured source (ICD-11 browser API, SNOMED CT, curated medical ontology) and the markdown becomes a rendered artifact, not the source of truth.

**Chunking strategy as the corpus grows:** Chunking by whole file breaks down when condition files become too long for a single embedding window. The correct approach at scale is to chunk by section header — `Cardinal symptoms`, `Differentials`, `Red flags`, etc. — producing approximately 7 chunks per condition. At 2000 conditions that yields ~14,000 chunks, which is well within the range of any production vector store. YAML frontmatter fields (`condition`, `icd11`, `category`) should be injected into each chunk's metadata so that deterministic filtering by category or ICD-11 code is possible without relying on embedding similarity alone.

**Embedding at scale:** 14,000 chunks embeds in minutes via a modern embedding API. Cold ingestion is a one-time cost. Incremental updates are cheap — updating one condition re-embeds approximately 7 chunks. Avoid full index rebuilds on individual file changes.

**Recommended architecture beyond 50 conditions:**
```
Structured database (Postgres / document store)
    → render to section-level text chunks on ingest
    → embed (OpenAI, Cohere, local model)
    → vector store (Chroma, Pinecone, Weaviate)
    → metadata filter + semantic retrieval at query time
```
The markdown files become a human-readable view layer. The database is the canonical store. This decouples curation, rendering, and retrieval so each can scale independently.

## Version notes

v1 — 10 conditions. East Africa / Kenya primary care oriented. Conditions prioritised by burden: NCDs, infectious disease, and common acute presentations. Expand to include asthma, COPD, heart failure, HIV, typhoid, sickle cell disease, STIs, and pregnancy-related conditions in v2.
