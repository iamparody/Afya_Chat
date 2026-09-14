# Acute Febrile Illness — Domain Contract

**Status:** Draft
**Purpose:** Define the scope, condition inventory, evaluation requirements, and completion gate for the first production-grade CDS clinical domain.

> **Domains own conditions. Presentations connect conditions across domains. Authoritative sources determine what is authored. Risk and clinical overlap determine what must be distinguished. Sequential validation determines when the domain is complete.**

---

## 1. Domain Scope

### 1.1 Clinical scope

The Acute Febrile Illness domain covers **primary-care presentation and initial clinical decision support for patients presenting with acute or subacute fever or a febrile syndrome**.

The domain addresses:

- common infectious causes of fever encountered in Kenyan primary care;
- important alternative diagnoses that present with overlapping symptoms;
- clinically important dangerous alternatives requiring escalation or referral;
- initial diagnostic discrimination and missing-information identification;
- environmental/contextual evidence where clinically relevant;
- red-flag recognition and escalation.

The domain does **not** attempt to provide:

- ICU-level management;
- specialist inpatient management;
- exhaustive rare-disease coverage;
- definitive diagnostic confirmation where the required investigation is unavailable at the target level of care;
- comprehensive treatment protocols beyond the CDS scope defined by the authoritative source.

### 1.2 Domain boundary

A condition has **one canonical domain**, determined by the primary Kenyan guideline or programme responsible for its diagnosis and management at the target level of care.

A condition may nevertheless participate in multiple presentation pathways.

```
UTI
  canonical domain → Genitourinary

acute fever pathway
  → UTI may participate
```

This prevents duplicate condition cards while allowing cross-domain clinical reasoning.

Cross-cutting syndromes such as **sepsis** are treated as safety/escalation constructs rather than ordinary disease-domain ownership.

---

## 2. Canonical Condition Inventory

The inventory is condition-first. The initial condition list must be established before presentation pathways or pairwise evaluation matrices are finalized.

Each condition must have:

| Field | Requirement |
|-------|-------------|
| `condition` | Canonical condition name |
| `canonical_domain` | Single owning domain |
| `primary_source` | Specific authoritative source |
| `source_type` | Source hierarchy category |
| `presentation_pathways` | Pathways in which the condition participates |
| `safety_priority` | Routine / Important / High-risk |
| `existing_card` | Whether an existing validated card exists |
| `card_status` | Not started / Draft / Validated / Frozen |

### 2.1 Source hierarchy

Authoritative sources are applied in the following order:

1. **Kenya MOH Standard Treatment Guidelines (STG)**
2. **Kenya MOH disease-specific guideline**
3. **WHO SMART DAK**
4. **WHO guideline**
5. **Other authoritative source**

Where sources conflict, the higher-ranked Kenyan source takes precedence.

A condition supported only by WHO or another non-Kenyan source must trigger a review question:

> **Does a Kenya-specific guideline or MOH source exist that should take precedence?**

The lower-ranked source may supplement a higher-ranked source but does not silently override it.

### 2.2 Canonical ownership rule

Canonical ownership follows **primary Kenyan guideline/programme responsibility**, not symptom presentation.

Therefore:

- TB remains under the domain owned by the Kenya National TB and Leprosy Programme;
- pneumonia remains under the appropriate respiratory guideline ownership;
- UTI remains Genitourinary;
- a condition appearing in an acute-febrile presentation does not thereby transfer domain ownership.

### 2.3 Condition inventory

**To be populated.** Populate before authoring any new card.

Open items: named condition list, source per condition, safety priority per condition, existing vs new card status.

Known existing cards that participate in this domain: malaria, dengue fever, typhoid fever, community-acquired pneumonia, pulmonary tuberculosis.

---

## 3. Presentation and Differential Map

The map is constructed **condition-first**, not presentation-first.

For each condition:

```
Condition
    ↓
Primary-care presentations it explains
    ↓
Important alternative presentations
    ↓
Dangerous alternatives
    ↓
Presentation pathways in which it participates
```

Only after this mapping is established are presentation pathways aggregated.

Candidate pathways include:

- acute undifferentiated fever;
- fever with respiratory symptoms;
- fever with gastrointestinal symptoms;
- fever with urinary symptoms;
- fever with neurological symptoms;
- fever with rash or other systemic features.

These are **not assumed to have equal scope or complexity**. Their content is determined by the conditions that legitimately participate in each pathway.

Every condition appearing in a pathway must have an explicit card-level justification.

**To be populated** after inventory is complete.

---

## 4. Pairwise Disambiguation Matrix

### 4.1 Required pair

A pair enters the standard disambiguation matrix when:

1. both conditions are epidemiologically plausible in Kenyan primary care — meaning both are encountered in primary care in Kenya within the same broad patient population, not necessarily co-endemic in the same region or season; and
2. they share at least two clinically important features.

### 4.2 Mandatory safety pair

A pair is mandatory regardless of the epidemiological filter when:

- the presentations materially overlap; **or**
- failure to distinguish them could materially alter urgency, referral, or immediate management.

This captures high-consequence alternatives even where prevalence differs substantially.

### 4.3 Matrix requirements

Each required pair must specify:

- shared presentation/features;
- discriminating evidence;
- missing information required;
- relevant red flags;
- expected disambiguation question(s);
- escalation/referral implication where applicable.

**To be populated** after inventory and presentation map are complete.

---

## 5. Evaluation Architecture

Stages 6–8 use **one integrated domain evaluation suite** with three explicitly scored dimensions.

```
                DOMAIN EVAL SUITE
                       │
      ┌────────────────┼────────────────┐
      ↓                ↓                ↓
Reasoning          Pairwise          Safety
 fixtures        disambiguation      fixtures
                   fixtures
```

A fixture may cover more than one dimension. Each dimension has its own pass criterion.

### 5.1 Reasoning evaluation

Tests whether the system:

- retrieves relevant candidates;
- distinguishes supporting from missing evidence;
- preserves the patient-fact / knowledge / inference boundary;
- produces an appropriate differential;
- identifies the leading candidate without presenting it as a confirmed diagnosis;
- respects source-grounded evidence.

**Threshold:** to be set at inventory completion. Baseline reference: 8/8 RAG, 94% reasoning (deterministic subset).

### 5.2 Pairwise disambiguation evaluation

Tests every required pair with fixture coverage sufficient to demonstrate that the system can:

- recognize the competing diagnoses;
- identify discriminating evidence;
- ask for relevant missing information;
- avoid treating missing information as negative evidence;
- change or preserve the differential appropriately when the discriminating evidence changes.

**Threshold:** to be set at inventory completion. Baseline reference: 4/5 disambiguation.

### 5.3 Red-flag evaluation

Tests:

- recognition of documented red flags;
- appropriate escalation;
- correct distinction between documented and "check for" red flags;
- avoidance of invented red flags;
- correct behaviour when a dangerous alternative is plausible but not established.

**Threshold:** to be set at inventory completion.

---

## 6. Sequential Domain Pipeline

| Stage | Deliverable | Gate | Sign-off |
|-------|-------------|------|----------|
| 1 | Domain definition | Scope approved | Clinical + product |
| 2 | Condition inventory | Conditions, ownership, sources, safety priority complete | Clinical |
| 3 | Card authoring | All required cards drafted | Content/technical |
| 4 | Card validation | Schema + automated validation pass | Automated gate + clinical spot-check |
| 5 | Ingestion/retrieval | Cards indexed; retrieval meets threshold | Automated gate |
| 6 | Reasoning evaluation | Reasoning fixture subset passes | Automated gate + clinical review |
| 7 | Pairwise evaluation | All mandatory pairs covered and pass | Automated gate + clinical review |
| 8 | Safety evaluation | Red-flag/escalation subset passes | Automated gate + clinical sign-off |
| 9 | Clinician review | Domain-level review accepted; gaps closed or documented | Clinical domain owner |
| 10 | Freeze/version | Domain version released; results and known limitations recorded | Technical + clinical |

**Handoff rule:** a stage cannot begin until the preceding stage has passed its gate. A failed downstream stage returns the domain to the earliest affected upstream stage.

---

## 7. Domain Completion Criteria

The Acute Febrile Illness domain is complete only when all of the following are true **in sequence**:

1. Domain scope and boundary are approved.
2. Required condition inventory is complete.
3. Every condition has an authoritative source and canonical domain owner.
4. Required cards are authored and validated.
5. Retrieval/indexing meets the defined technical threshold.
6. Reasoning fixtures pass.
7. Every required pairwise distinction has evaluation coverage and passes.
8. Red-flag and escalation fixtures pass clinical safety review.
9. Clinician domain review is complete.
10. The domain is versioned/frozen with known limitations recorded.

A numerical condition count is **not** a completion criterion.

A domain may be frozen with explicitly documented exclusions where those exclusions are outside the agreed primary-care scope.

---

## 8. Existing Corpus Policy

Existing validated cards remain in the corpus. They do not need to be discarded or rewritten because they belong to domains not yet completed.

Current cards have one of three statuses:

- **Completed-domain card** — belongs to a frozen domain;
- **Existing validated card / incomplete domain** — clinically usable but not evidence that its wider domain is complete;
- **New domain card** — authored under the relevant domain contract.

Existing cards such as UTI can participate in acute-febrile evaluation pathways without becoming part of the Acute Febrile Illness domain's canonical ownership.

The existing NCD and GI cards remain available and provide a foundation for subsequent domain completion.

---

## 9. Freeze Principle

Once the domain satisfies the sequential completion gate, it is **versioned and frozen**.

Subsequent changes require:

- explicit card/version change;
- affected evaluation fixtures rerun;
- clinical review where clinically material;
- domain version increment.

The freeze creates a stable benchmark against which subsequent domain replication and system changes can be evaluated.

---

## Known gaps at time of drafting

- Section 2 inventory not yet populated — critical path before any new card is authored.
- Section 3 presentation map not yet populated — depends on inventory.
- Section 4 pairwise matrix not yet populated — depends on presentation map.
- Numerical thresholds for evaluation gates not yet set — to be defined at inventory completion based on current system baselines.
- Effort estimate not yet determined — rough estimate possible after inventory is complete (~5–6 new cards, ~15–20 pairwise fixtures, clinician review).
