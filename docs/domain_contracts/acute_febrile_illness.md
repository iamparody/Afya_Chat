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

Verified against Kenya source hierarchy (Pass 1 complete — 2026-09-14).

**Pathway codes used in this table:**
- AUF — acute undifferentiated fever
- FRS — fever with respiratory symptoms
- FGI — fever with gastrointestinal symptoms
- FNS — fever with neurological symptoms
- FRash — fever with rash or systemic features

**Ownership note:** conditions marked `canonical_domain ≠ Acute Febrile Illness` are owned by their respective domain but participate in AFI presentation pathways. They do not require new cards authored under this domain contract — their existing validated cards are used as-is.

| Condition | Canonical domain | Primary source | Source type | Presentation pathways | Safety priority | Existing card | Card status |
|-----------|-----------------|----------------|-------------|----------------------|----------------|---------------|-------------|
| Malaria (unspecified) | Acute Febrile Illness | Kenya NMCP Guidelines for the Diagnosis, Treatment and Prevention of Malaria, 6th ed. (2024) | Kenya MOH disease-specific guideline | AUF; FNS (cerebral malaria) | High | Yes | Validated |
| Typhoid fever | Acute Febrile Illness | Kenya MOH Clinical Guidelines Vol 2 — Level 2-3 Facilities (2025), Chapter: Salmonella Infections | Kenya MOH STG | AUF; FGI | High | Yes | Validated |
| Meningitis (bacterial) | Acute Febrile Illness | Kenya MOH Clinical Guidelines Vol 2 — Level 2-3 Facilities (2025), Chapter: Meningitis | Kenya MOH STG | FNS; AUF | High | No | Not started |
| Cholera | Acute Febrile Illness | WHO-AFRO Cholera Management Guidelines, 2023 Edition | WHO guideline | FGI | High | No | Not started |
| Dengue fever | Acute Febrile Illness | WHO Guidelines for Clinical Management of Arboviral Diseases (2025) | WHO guideline | AUF; FRash | High | Yes | Validated |
| Brucellosis | Acute Febrile Illness | KNPHI/ZDU Human Brucellosis Testing Guidelines (2024) — diagnostic only; ⚠ no Kenya MOH treatment protocol confirmed | Other ⚠ | AUF | Important | No | Not started |
| Leptospirosis | Acute Febrile Illness | WHO Human Leptospirosis: Guidance for Diagnosis, Surveillance and Control (WHO/ILS, 2003) — ⚠ 22 years old; no updated source confirmed | WHO guideline ⚠ | AUF; FRash | Important | No | Not started |
| Chikungunya | Acute Febrile Illness | WHO Guidelines for Clinical Management of Arboviral Diseases (2025) | WHO guideline | AUF; FRash | Important | Yes | Validated |
| Rickettsial illness | Acute Febrile Illness | ⛔ No Kenya MOH guideline. No dedicated WHO guideline. CDC/IDSA guidance + East Africa peer literature only. See governance note below. | Other ⛔ | AUF; FRash | Important | No | Not started |
| Pneumonia (CAP) | **Respiratory** ← cross-domain | Kenya MOH Clinical Guidelines Vol 2 — Level 2-3 Facilities (2025), Chapter: Pneumonia | Kenya MOH STG | FRS; AUF | High | Yes | Validated |
| Pulmonary tuberculosis | **NTLD-P** ← cross-domain | Kenya MOH NTLD-P Guideline for Integrated Tuberculosis, Leprosy and Lung Disease in Kenya (2017) | Kenya MOH disease-specific guideline | FRS; AUF | High | Yes | Validated |

### 2.4 Source verification notes

**Malaria:** Kenya NMCP guideline (2024) takes precedence over the general MOH Clinical Guidelines Vol 2/3 for all malaria-specific protocols. Vol 2/3 cross-references NMCP for detailed management. Use NMCP as primary source; Vol 2/3 provides facility-level context.

**Typhoid fever:** Full chapter in both Vol 2 (primary care) and Vol 3 (hospital) as "Salmonella Infections / Typhoid Fever." No separate stand-alone Kenya typhoid guideline confirmed. Vol 2 is the primary source for primary-care CDS scope.

**Meningitis:** Full chapter in Vol 2 (2025) with management flowcharts for primary-care triage and referral, and dedicated paediatric chapter in Vol 3. No separate Kenya meningitis-specific guideline. Vol 2 is the primary source for primary-care scope.

**Cholera:** Kenya MOH Vol 2/3 covers cholera only within diarrhoeal disease management tables — no standalone chapter. The treatment note in Vol 3 (doxycycline x 7 days) predates current WHO 2023 recommendations. WHO-AFRO Cholera Management Guidelines 2023 is the authoritative source. Published on the WHO-AFRO Kenya country page. This is the Gate 2 closure test condition — first new card authored in YAML (Method A).

**Dengue and Chikungunya:** Neither condition has a standalone chapter in any Kenya MOH Clinical Guidelines volume. Dengue appears only as a line-item within the Viral Haemorrhagic Fever differential group in Vol 3 (2009). The WHO 2025 arboviral guideline (Dengue, Chikungunya, Zika, Yellow Fever) is the primary source for both. Kenya-specific epidemiological context (endemic counties, seasonal patterns, co-circulation with malaria) must be authored separately — it is not in the WHO guideline.

**TB (cross-domain):** NTLD-P 2017 guideline takes precedence over general MOH Clinical Guidelines for all TB management. TB is owned by the NTLD-P domain. Its existing validated card participates in AFI pathways (FRS, prolonged fever differential) without requiring AFI domain ownership.

**Pneumonia (cross-domain):** Full chapter in both Vol 2 and Vol 3. Owned by the Respiratory domain. Existing validated card participates in AFI pathways (FRS, AUF) without requiring AFI domain ownership.

**Brucellosis ⚠ source gap:** No dedicated clinical management chapter in any confirmed Kenya MOH guideline. The KNPHI/ZDU 2024 policy brief covers diagnostic testing only. The 2021–2040 national strategy is epidemiological, not clinical. For treatment protocols, no Kenya-level source has been confirmed — practitioners currently rely on WHO/international references (WHO Manual on Brucellosis, Corbel 2006; IDSA guidance). Card authoring for brucellosis requires a clinical governance decision on acceptable source before work begins.

**Leptospirosis ⚠ outdated source:** The only formal WHO-level guidance is the 2003 WHO/ILS document, now 22 years old. No updated WHO guideline, no Kenya MOH protocol. The condition is documented as a significant cause of febrile illness in Kenya (zoonotic, leptospira borgpetersenii confirmed in Kenyan livestock populations) but lacks a current national or international management guideline. Card authoring requires a source decision — the 2003 document may be usable if the clinical content (diagnosis, treatment with doxycycline/penicillin) is verified against current clinical practice standards.

**Rickettsial illness ⛔ governance required:** No Kenya MOH guideline exists. No dedicated WHO guideline for rickettsial disease in East Africa exists. Multiple species are documented in Kenya (Rickettsia felis, spotted fever group, Q fever, scrub typhus) but national management protocols are absent. Available sources are: CDC/IDSA guidance (US-authored, not Kenya-specific); East Africa peer literature (Maina et al. 2012, Luce-Fedrow 2015). This falls below the source hierarchy floor. A governance decision is required before this condition can enter the card authoring pipeline: either accept CDC/IDSA as an explicitly labelled fallback source, or defer until a Kenya-relevant source is identified.

### 2.5 Inventory governance decisions required before card authoring

The following decisions must be made before any new card is authored for these conditions. They do not block completion of Sections 3 and 4.

| Condition | Decision required |
|-----------|------------------|
| Brucellosis | Accept WHO Manual on Brucellosis (Corbel 2006) or IDSA guidance as fallback source, explicitly labelled? Or defer card authoring? |
| Leptospirosis | Accept WHO 2003 guidance as source with explicit age-of-evidence caveat in frontmatter? Or defer? |
| Rickettsial illness | Accept CDC/IDSA guidance as fallback source with explicit non-Kenya label? Or defer until regional guideline exists? |

---

## 3. Presentation and Differential Map

### 3.1 Architecture

The map is **presentation-first**, not condition-first. Each row answers: *"A patient arrives with this cluster — what conditions must the system consider?"*

This is the inverse of a condition card. Condition cards are authored outward from a disease. The presentation map works inward from symptom clusters to candidate conditions. It is what makes the clinical reasoning auditable and what drives Section 4 (which pairs actually need formal disambiguation).

**Cross-domain participation rule:** conditions owned by other domains appear in this map without transferring ownership. TB (NTLD-P domain) and Pneumonia (Respiratory domain) appear as candidates in the pathways where they are clinically relevant. Their existing validated cards are used as-is.

**Source-governance flag:** conditions with `governance_pending` source status appear in the map so the cross-domain structure is visible. They must not enter card authoring until the governance decision in Section 2.5 is resolved.

```
Patient presentation cluster
        ↓
Candidate conditions (AFI-owned + cross-domain participants)
        ↓
Flags: safety_priority · source_status · canonical_domain
        ↓
Section 4: which pairs require formal disambiguation
```

### 3.2 Presentation matrix

**Legend:**
- ● AFI-owned condition, card exists
- ○ AFI-owned condition, card needed
- ◑ Cross-domain participant, card exists
- ⚠ governance_pending — source decision required before card authoring

---

**P1 — Acute undifferentiated fever**
*Fever without a localising focus at point of initial assessment.*

| Candidate | Status | Safety | Notes |
|-----------|--------|--------|-------|
| Malaria | ● | High | Must be first consideration in all endemic regions |
| Dengue | ● | High | Especially coast and lake basin; pre-rash phase indistinguishable from malaria |
| Typhoid | ● | High | Insidious onset; constipation or no GI symptoms in early phase |
| Chikungunya | ● | Important | Arthralgia may be subtle or absent in first 48h |
| Leptospirosis | ○ ⚠ | Important | Often missed; exposure history (floodwater, livestock) is key discriminator |
| Rickettsial illness | ○ ⚠ | Important | Eschar and rash often absent or unnoticed at first presentation |
| Brucellosis | ○ ⚠ | Important | Undulant fever pattern; livestock exposure is discriminating |
| Meningitis | ○ | High | Must be excluded before fever is labelled undifferentiated; neck stiffness may be absent early |

---

**P2 — Fever + headache / neurological features**
*Fever with prominent headache, altered consciousness, neck stiffness, photophobia, or focal neurology.*

| Candidate | Status | Safety | Notes |
|-----------|--------|--------|-------|
| Meningitis | ○ | High | Mandatory safety candidate whenever fever + headache + any neurological sign |
| Malaria (cerebral) | ● | High | Altered consciousness with fever = cerebral malaria until proven otherwise |
| Typhoid | ● | High | Typhoid encephalopathy; headache is a cardinal feature of early typhoid |
| Dengue | ● | High | Retro-orbital headache is discriminating; severe headache in dengue haemorrhagic fever |
| Rickettsial illness | ○ ⚠ | Important | Severe headache + fever + rash triad; meningeal involvement documented |
| Leptospirosis | ○ ⚠ | Important | Weil's disease can present with meningism |

---

**P3 — Fever + respiratory symptoms**
*Fever with cough, dyspnoea, chest pain, or abnormal respiratory examination.*

| Candidate | Status | Safety | Notes |
|-----------|--------|--------|-------|
| Pneumonia (CAP) | ◑ | High | Primary respiratory candidate; acute onset, productive cough, pleuritic pain |
| Malaria | ● | High | Cough is associated symptom in malaria; do not anchor on respiratory presentation alone |
| TB | ◑ | High | Subacute/chronic; duration >2 weeks, night sweats, weight loss distinguish from acute CAP |
| Leptospirosis | ○ ⚠ | Important | Pulmonary haemorrhage syndrome (Weil–Leptospirosis lung); rare but high mortality |
| Rickettsial illness | ○ ⚠ | Important | Interstitial pneumonitis documented in scrub typhus and spotted fever group |

---

**P4 — Fever + gastrointestinal symptoms**
*Fever with diarrhoea, vomiting, abdominal pain, or nausea.*

| Candidate | Status | Safety | Notes |
|-----------|--------|--------|-------|
| Typhoid | ● | High | Relative bradycardia, abdominal distension, rose spots; perforation is a red flag |
| Cholera | ○ | High | Rice-water diarrhoea, rapid severe dehydration; high mortality without prompt fluid replacement |
| Malaria | ● | High | GI symptoms common in malaria; do not dismiss malaria because GI features are present |
| Dengue | ● | High | Vomiting and abdominal pain are warning signs for dengue haemorrhagic fever |
| Leptospirosis | ○ ⚠ | Important | Nausea, vomiting, and abdominal pain in early phase |
| Acute gastroenteritis | ◑ | Routine–Important | Cross-domain participant (GI domain); cholera must be distinguished from other AGE |

---

**P5 — Fever + rash**
*Fever with any skin manifestation: maculopapular rash, petechiae, purpura, eschar, or erythema.*

| Candidate | Status | Safety | Notes |
|-----------|--------|--------|-------|
| Dengue | ● | High | Maculopapular rash day 3–5; petechiae/purpura = haemorrhagic dengue, high risk |
| Chikungunya | ● | Important | Maculopapular rash; often concurrent with dengue in co-endemic regions |
| Rickettsial illness | ○ ⚠ | Important | Eschar (inoculation site) is pathognomonic where present; maculopapular or petechial rash |
| Meningitis | ○ | High | Petechial or purpuric rash with fever = meningococcal septicaemia until proven otherwise; emergency |
| Malaria | ● | High | Rash is not a malaria feature; its presence should prompt consideration of an alternative or co-diagnosis |

---

**P6 — Fever + arthralgia / myalgia**
*Fever with joint pain, joint swelling, or severe muscle aches as a prominent feature.*

| Candidate | Status | Safety | Notes |
|-----------|--------|--------|-------|
| Chikungunya | ● | Important | Severe polyarthralgia is the defining feature; can persist weeks after fever resolves |
| Dengue | ● | High | Bone-break fever; severe myalgia and arthralgia, retro-orbital pain |
| Malaria | ● | High | Myalgia and arthralgia common; must not be displaced by a musculoskeletal label |
| Leptospirosis | ○ ⚠ | Important | Severe myalgia (especially calf muscles) is a discriminating feature |
| Rickettsial illness | ○ ⚠ | Important | Myalgia prominent; arthralgia less common than in chikungunya |
| Brucellosis | ○ ⚠ | Important | Arthritis (sacroiliac, large joints) in subacute brucellosis |

---

**P7 — Fever + jaundice**
*Fever with visible jaundice or laboratory evidence of hepatic or haemolytic dysfunction.*

| Candidate | Status | Safety | Notes |
|-----------|--------|--------|-------|
| Malaria | ● | High | Haemolytic jaundice; severe malaria — high urgency |
| Leptospirosis | ○ ⚠ | Important | Weil's disease: fever + jaundice + renal failure triad; high mortality |
| Typhoid | ● | High | Hepatomegaly and jaundice in complicated typhoid |
| Dengue | ● | High | Hepatitis in severe dengue; jaundice is a warning sign |

---

**P8 — Acute watery diarrhoea ± severe dehydration**
*Profuse watery diarrhoea with or without vomiting; dehydration as the dominant clinical problem.*

| Candidate | Status | Safety | Notes |
|-----------|--------|--------|-------|
| Cholera | ○ | High | Rice-water stools, absence of fever in many cases; suspect in outbreak context or known endemic area |
| Acute gastroenteritis | ◑ | Routine–Important | Cross-domain (GI domain); more common cause; distinguished from cholera by stool character and context |
| Typhoid | ● | High | Diarrhoea can occur in typhoid; not the dominant presentation — important safety differential |

*Note: P8 has deliberate overlap with P4. The distinction is that P8 is triggered when dehydration severity drives the clinical encounter rather than fever.*

---

**P9 — Prolonged or recurrent fever**
*Fever lasting >7 days, or fever that resolves and recurs without a confirmed diagnosis.*

| Candidate | Status | Safety | Notes |
|-----------|--------|--------|-------|
| TB | ◑ | High | Subacute systemic disease; the key differential when acute causes have been excluded |
| Brucellosis | ○ ⚠ | Important | Undulant fever is the classic pattern; livestock exposure history is essential |
| Typhoid | ● | High | Persistent fever with relative bradycardia; stepped fever pattern in classic presentation |
| Malaria | ● | High | Recurrent fever with periodicity (tertian/quartan); must be excluded by repeat RDT |
| Leptospirosis | ○ ⚠ | Important | Biphasic illness: leptospiraemic phase + immune phase separated by brief remission |

### 3.3 Cross-domain participation summary

| Condition | Canonical domain | Participates in AFI pathways |
|-----------|-----------------|------------------------------|
| Pneumonia (CAP) | Respiratory | P3, P1 (as differential) |
| Pulmonary tuberculosis | NTLD-P | P3, P9 |
| Acute gastroenteritis | Gastrointestinal | P4, P8 |

These conditions appear in the presentation matrix because excluding them is clinically necessary. They do not require new cards under this domain contract.

### 3.4 Conditions not included and why

The following conditions can cause fever but are **not included** in this domain's presentation map at this stage:

| Condition | Reason excluded |
|-----------|----------------|
| Yellow fever | Vaccine-preventable; limited Kenya primary-care diagnostic relevance outside outbreak; no endemic primary-care caseload |
| Rift Valley fever | Outbreak-associated; not a routine primary-care differential; surveillance-driven detection |
| Viral haemorrhagic fevers (Ebola, Marburg) | Outbreak-only; primary care role is recognition + immediate isolation/referral, not differential diagnosis; separate protocol required |
| Visceral leishmaniasis | Chronic rather than acute febrile presentation; distinct geographic restriction (Baringo, Turkana, Isiolo); separate domain |
| HIV primary infection | Seroconversion illness overlaps but HIV belongs to a distinct chronic-disease management domain |
| Malaria in pregnancy | Managed under an obstetric domain overlay; existing card flags this; not a separate AFI condition |

Mention in a reference guideline is not sufficient for inclusion. Inclusion requires: routine primary-care diagnostic relevance + a plausible treatment pathway at primary-care level + a defensible authoritative source.

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

- Section 2 inventory — Pass 1 complete (2026-09-14). Three governance decisions outstanding (Brucellosis, Leptospirosis, Rickettsial illness) before card authoring can begin for those conditions. Inventory is otherwise locked.
- Section 3 presentation map — not yet populated; depends on inventory (now unblocked).
- Section 4 pairwise matrix — not yet populated; depends on Section 3.
- Numerical thresholds for evaluation gates — not yet set; to be defined using current baselines (8/8 RAG, 4/5 disambiguation, 94% reasoning deterministic subset).
- Effort estimate: 3 new AFI-owned cards minimum before governance decisions (Meningitis, Cholera, Dengue/Chikungunya already validated); up to 6 if Brucellosis/Leptospirosis/Rickettsial are approved. ~15–25 pairwise fixtures estimated pending Section 3 completion.
