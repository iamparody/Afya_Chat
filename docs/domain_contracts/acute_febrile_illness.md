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

### 4.4 Pair index

All required pairs derived from the Section 3 presentation matrix. Pairs involving conditions with `governance_pending` source status are flagged ⚠ — evaluation fixtures for these pairs cannot be authored until the governance decision in §2.5 is resolved. Cross-domain pairs are flagged ↔.

| ID | Pair | Pathways | Priority |
|----|------|----------|----------|
| MSP-01 | Malaria (cerebral) vs Meningitis (bacterial) | P2, P1 | Mandatory safety |
| MSP-02 | Meningitis (bacterial) vs Dengue (haemorrhagic) | P5, P2 | Mandatory safety |
| MSP-03 | Cholera vs Acute gastroenteritis | P8 | Mandatory safety |
| RP-01 | Malaria vs Dengue fever | P1, P6 | Required |
| RP-02 | Malaria vs Typhoid fever | P1, P4, P9 | Required |
| RP-03 | Dengue vs Chikungunya | P1, P5, P6 | Required |
| RP-04 | Typhoid vs Cholera | P4, P8 | Required |
| RP-05 | Malaria vs Leptospirosis ⚠ | P7, P6 | Required |
| RP-06 | Malaria vs Rickettsial illness ⚠ | P1, P2 | Required |
| RP-07 | Dengue vs Rickettsial illness ⚠ | P5 | Required |
| RP-08 | Chikungunya vs Brucellosis ⚠ | P6, P9 | Required |
| RP-09 | Typhoid vs Brucellosis ⚠ | P9 | Required |
| RP-10 | Malaria vs Pneumonia ↔ | P3 | Required |
| RP-11 | Dengue vs Typhoid | P4 | Required |
| RP-12 | Leptospirosis ⚠ vs Dengue | P6, P7 | Required |
| RP-13 | TB vs Pneumonia ↔ | P3, P9 | Required |
| RP-14 | Typhoid vs Acute gastroenteritis ↔ | P4 | Required |

---

### 4.5 Mandatory safety pairs

#### MSP-01: Malaria (cerebral) vs Meningitis (bacterial)

**Pathways:** P2, P1
**Why mandatory:** Both present with fever and impaired consciousness. Failure to distinguish materially alters immediate management and referral route. Empirical treatment for one does not cover the other.

**Shared features:** Fever, impaired or altered consciousness, headache, seizures (especially in children).

**Discriminating evidence:**
- Malaria RDT positive: supports cerebral malaria; negative significantly increases meningitis likelihood (do not exclude malaria on RDT alone in high-transmission areas)
- Neck stiffness / meningism: present in meningitis; typically absent in cerebral malaria (may also be absent in infants even with bacterial meningitis)
- Purpuric or petechial rash: present in meningococcaemia; absent in malaria
- CSF (lumbar puncture): turbid, raised white cells and protein = bacterial meningitis; normal = increases probability of cerebral malaria if RDT positive
- Focal neurological signs: more consistent with meningitis or cerebral abscess than cerebral malaria

**Missing information required:** RDT result; neck stiffness on examination; photophobia; presence and character of any rash; seizure history and type; GCS trend.

**Red flags:** GCS ≤ 12 and falling; purpuric or petechial rash; papilloedema (contra-indicates LP until imaging); respiratory compromise.

**Disambiguation questions:**
1. "Is there neck stiffness or does the patient resist having their neck flexed?"
2. "What is the current GCS or level of consciousness, and is it changing?"
3. "What did the malaria RDT show?"
4. "Is there any rash — petechiae or purpura?"

**Escalation:** Both require immediate hospital referral. Do not delay empirical antibiotics for bacterial meningitis if LP is unavailable or delayed. If RDT is negative and meningism is present: treat empirically for bacterial meningitis. Purpuric rash + fever = meningococcaemia — give IV benzylpenicillin before transfer without waiting for LP.

---

#### MSP-02: Meningitis (bacterial) vs Dengue (haemorrhagic) — Fever + Petechiae/Purpura

**Pathways:** P5, P2
**Why mandatory:** Petechial or purpuric rash with fever is the sentinel presentation for meningococcaemia. Dengue haemorrhagic fever can also produce petechiae. Failure to recognise meningococcaemia causes preventable death within hours.

**Shared features:** Fever, petechiae or purpuric rash, headache, vomiting, malaise.

**Discriminating evidence:**
- Rash spread and character: meningococcaemia rash spreads rapidly (hours), is non-blanching, may coalesce into purpura; dengue petechiae are typically less rapidly progressive and non-coalescing
- Meningism (neck stiffness, Kernig's sign): present in meningococcal meningitis; absent in dengue haemorrhagic fever
- Tourniquet test: positive (≥20 petechiae per 2.5 cm²) in dengue thrombocytopenia; negative in meningococcaemia
- Dengue clinical warning signs: vomiting + severe abdominal pain + mucosal bleeding without meningism — not features of meningitis
- FBC: thrombocytopenia in dengue; leucocytosis or very low count in meningococcaemia

**Missing information required:** Rash onset timing and spread rate; whether rash is blanching; meningism on examination; tourniquet test; FBC (platelet count); fever duration and pattern.

**Red flags:** Non-blanching purpura that is spreading rapidly = meningococcaemia emergency — act before other results are available.

**Disambiguation questions:**
1. "How quickly did the rash appear and spread — within hours or over days?"
2. "Does the rash fade when pressed firmly?"
3. "Is there neck stiffness?"
4. "Is there abdominal pain or bleeding from the gums or nose?"

**Escalation:** Non-blanching spreading purpura = treat as meningococcaemia immediately — IV benzylpenicillin and transfer. DHF with warning signs = same-day referral for IV access and monitoring. Do not delay meningococcaemia treatment for tourniquet test or FBC results.

---

#### MSP-03: Cholera vs Acute gastroenteritis — Severe dehydration emergency

**Pathways:** P8
**Why mandatory:** Both present with acute watery diarrhoea and dehydration. Cholera requires antibiotic therapy and is a notifiable disease requiring immediate public health response. The immediate management of dehydration is shared; the subsequent response pathways diverge critically.

**Shared features:** Profuse watery diarrhoea, vomiting, dehydration, abdominal cramping.

**Discriminating evidence:**
- Stool character: rice-water, colourless, odourless or fishy-odour stools = cholera; non-specific watery or mucoid = AGE
- Fever: cholera is often afebrile or low-grade; fever suggests AGE or co-pathology
- Volume and rate: cholera = very rapid and voluminous purging leading to severe dehydration within hours
- Outbreak context: cholera clusters rapidly in households or community around a shared water source; AGE may cluster but less dramatically
- Geographic and seasonal context: cholera risk highest in lake basin, coastal areas, informal settlements with limited sanitation; highest during and after flooding

**Missing information required:** Stool character; presence or absence of fever; other household or community members affected; geographic and sanitation context.

**Red flags (both — act immediately on either):** Severe dehydration (sunken eyes, skin turgor ≥2 seconds, unable to drink), shock (rapid weak pulse, cold extremities), altered consciousness, reduced urine output.

**Disambiguation questions:**
1. "Are the stools profuse, watery, and colourless — 'rice water' in appearance?"
2. "Is there fever?"
3. "Are other people in the household or nearby community ill with the same symptoms?"

**Escalation:** Begin ORS immediately for any dehydration; IV fluids for severe dehydration (both). Cholera: doxycycline single dose (adult), tetracycline alternatives; notify public health authority; isolate and apply infection control. AGE: antibiotic only for bloody stool, immunocompromised patient, or systemic features.

---

### 4.6 Required pairs

#### RP-01: Malaria vs Dengue fever

**Pathways:** P1, P6
**Shared features:** Acute fever, severe myalgia, arthralgia, headache. Pre-rash dengue (days 1–3) is clinically indistinguishable from malaria. Both high-safety priority.

**Discriminating evidence:**
- Malaria RDT positive: strongly favours malaria; negative increases dengue probability
- Retro-orbital pain: pathognomonic for dengue; absent in malaria
- Dengue rash: maculopapular, appears day 3–5, typically spares palms and soles; not a malaria feature
- Geographic context: dengue endemic in coast and lake basin; malaria endemic nationwide with highest transmission in lake basin, coast, and lowlands
- Dengue warning signs: vomiting + severe abdominal pain + clinical deterioration = plasma leakage; not a malaria feature

**Missing information required:** RDT result; retro-orbital pain; rash (presence, day of illness); geographic exposure; tourniquet test.

**Red flags:** Dengue: warning signs (severe vomiting, abdominal pain, clinical deterioration, mucosal bleeding); Malaria: prostration, inability to sit unaided, jaundice, impaired consciousness.

**Disambiguation questions:**
1. "Is there pain behind or around the eyes that is worse with eye movement?"
2. "What did the malaria RDT show?"
3. "Has the patient been on the coast or in the lake basin recently?"

**Escalation:** Dengue with warning signs = same-day referral for monitoring and IV access. Malaria = immediate ACT. Co-infection is possible — treat malaria if RDT positive even when dengue is also suspected.

---

#### RP-02: Malaria vs Typhoid fever

**Pathways:** P1, P4, P9
**Shared features:** Fever, headache, malaise, GI symptoms (nausea, vomiting, diarrhoea or constipation). Cannot be separated clinically without testing.

**Discriminating evidence:**
- Malaria RDT positive: favours malaria; negative raises typhoid probability substantially
- Onset pattern: malaria = acute onset (hours to 72 hours); typhoid = insidious step-wise fever rising over 5–7 days
- Relative bradycardia (Faget's sign): heart rate inappropriately low relative to fever height — strongly suggests typhoid
- Rose spots: faint pink maculae on abdomen (typhoid) — pathognomonic but subtle and often missed
- Bowel pattern: early typhoid commonly causes constipation, not diarrhoea; malaria does not cause constipation
- Splenomegaly: both; more prominent in prolonged typhoid

**Missing information required:** RDT result; onset pattern (acute vs step-wise over days); bowel pattern (constipation or diarrhoea); pulse-temperature dissociation on examination; blood culture access.

**Red flags:** Typhoid: acute abdomen (intestinal perforation), gastrointestinal haemorrhage, hepatomegaly, peritonism; Malaria: cerebral features, prostration.

**Disambiguation questions:**
1. "Has the fever been building gradually over several days, or did it start suddenly?"
2. "Is the patient constipated or having diarrhoea?"
3. "What did the malaria RDT show?"
4. "Has any blood culture been collected?"

**Escalation:** Typhoid perforation = immediate surgical referral. Do not delay antibiotic treatment if one diagnosis is strongly suspected. Co-treat if both are plausible and patient is deteriorating without diagnostic access.

---

#### RP-03: Dengue vs Chikungunya

**Pathways:** P1, P5, P6
**Shared features:** Acute fever, maculopapular rash, arthralgia and myalgia, both arboviral, co-endemic in coast and lake basin with documented co-circulation in Kenya.

**Discriminating evidence:**
- Arthralgia severity and pattern: chikungunya = severe symmetric polyarthralgia (small joints: MCP, wrist, ankle, MTP); can incapacitate and persist weeks post-fever; dengue = prominent myalgia and bone-break pain, but arthralgia less incapacitating
- Dengue warning signs: abdominal pain, vomiting, mucosal bleeding, clinical deterioration = plasma leakage; chikungunya does not produce plasma leakage
- Retro-orbital pain: specific for dengue; absent in chikungunya
- Haemorrhagic features: dengue (petechiae, positive tourniquet test, mucosal bleeding); uncommon in chikungunya

**Missing information required:** Whether joint pain or muscle/bone pain is more severe; haemorrhagic features; tourniquet test; retro-orbital pain; rash timing.

**Red flags:** Dengue warning signs (vomiting + abdominal pain + clinical deterioration + mucosal bleeding) = immediate referral. Chikungunya rarely life-threatening acutely; watch for dehydration in elderly.

**Disambiguation questions:**
1. "Is the joint pain or the bone and muscle pain more severe?"
2. "Is there pain behind or around the eyes?"
3. "Any bleeding from the gums, nose, or visible blood in stool or vomit?"

**Escalation:** Dengue with warning signs = same-day referral for IV access. Chikungunya = symptomatic management; paracetamol preferred over NSAIDs during acute fever phase.

---

#### RP-04: Typhoid vs Cholera

**Pathways:** P4, P8
**Shared features:** Fever + diarrhoea, gastrointestinal illness, both waterborne or food-borne in similar settings.

**Discriminating evidence:**
- Stool character: cholera = profuse rice-water stools; typhoid = looser stool in early disease, blood or mucus in complications
- Fever: high and sustained in typhoid; often low-grade or absent in cholera
- Onset: cholera = explosive, hours after exposure; typhoid = insidious, step-wise over 5–7 days
- Dehydration rate: cholera causes rapid severe dehydration within hours; typhoid does not cause this severity of early fluid loss

**Missing information required:** Stool character and volume; fever degree; onset timing; dehydration severity.

**Red flags:** Cholera: severe dehydration, shock; Typhoid: perforation signs (peritonism, acute abdomen, rebound tenderness).

**Disambiguation questions:**
1. "How severe is the diarrhoea — is the stool colourless and watery like water, or does it contain blood or mucus?"
2. "Did the illness start suddenly within hours, or build up gradually over several days?"
3. "Is there high sustained fever or just low-grade or no fever?"

**Escalation:** Cholera: aggressive ORS/IV hydration + doxycycline + immediate notification. Typhoid: antibiotics (resistance-guided) + monitor for complications. Antibiotic choice and public health response differ — distinguish before treatment where possible.

---

#### RP-05: Malaria vs Leptospirosis

**Pathways:** P7 (fever + jaundice), P6 (fever + myalgia)
**Note:** Leptospirosis = governance_pending ⚠ — evaluation fixtures for this pair cannot be authored until source decision in §2.5 is made and card is authored.

**Shared features:** Acute fever, severe myalgia, headache, jaundice in severe presentations.

**Discriminating evidence:**
- Malaria RDT positive: confirms malaria; consider co-infection in high-exposure settings
- Calf muscle tenderness: severe, on compression of gastrocnemius — highly specific for leptospirosis; absent in malaria
- Conjunctival suffusion: bilateral redness without discharge or follicles — specific for leptospirosis; not a malaria feature
- Jaundice type: haemolytic (indirect bilirubin) in malaria; hepatocellular + cholestatic in Weil's disease
- Renal involvement: oliguria, haematuria — leptospirosis (Weil's disease); uncommon in malaria outside severe disease
- Exposure history: floodwater contact, livestock handling, occupational water exposure — discriminating for leptospirosis

**Missing information required:** RDT result; calf muscle tenderness on examination; conjunctival appearance; renal function indicators (urine output, haematuria); floodwater or livestock exposure in past 2 weeks.

**Red flags:** Weil's disease triad (fever + jaundice + renal failure) = high mortality — immediate referral. Severe malaria with jaundice = also high-risk.

**Disambiguation questions:**
1. "Any contact with floodwater, livestock, or muddy water in the past 2 weeks?"
2. "Is there severe pain in the calf muscles, specifically on squeezing the back of the lower leg?"
3. "What did the malaria RDT show?"
4. "Is there any reduction in urine output or blood in the urine?"

**Escalation:** Weil's disease = immediate referral for IV penicillin or doxycycline + fluid management + renal monitoring. Severe malaria = immediate artemisinin treatment + referral. Empirically co-treat both if patient is deteriorating without diagnostic access.

---

#### RP-06: Malaria vs Rickettsial illness

**Pathways:** P1, P2
**Note:** Rickettsial illness = governance_pending ⚠ — evaluation fixtures for this pair cannot be authored until source decision in §2.5 is made and card is authored.

**Shared features:** Acute fever, severe headache, myalgia, malaise.

**Discriminating evidence:**
- Malaria RDT positive: confirms malaria; negative raises rickettsial suspicion in tick-exposed patients
- Eschar (inoculation site): a small dark necrotic skin lesion — pathognomonic for spotted fever group rickettsiae and scrub typhus; must examine scalp, axillae, groin and waistband areas that are frequently missed
- Tick exposure history: specific for rickettsial illness; mosquito exposure: malaria
- Rash: malaria does not cause rash; rickettsial illness produces maculopapular or petechial rash, typically appearing day 3–5
- Treatment response: doxycycline produces rapid clinical improvement (24–48 hours) in rickettsial illness; ACT improves malaria within 24–48 hours

**Missing information required:** RDT result; tick bite or tick exposure history; full skin examination for eschar (including hidden areas); rash presence and timing.

**Red flags:** Rickettsial meningoencephalitis — severe headache + fever + neurological signs without meningism; high mortality without prompt doxycycline.

**Disambiguation questions:**
1. "Any tick bite, or exposure to livestock, bush, or long grass in the past 2 weeks?"
2. "Is there any small dark scab or skin mark — like a cigarette burn — anywhere on the body, including under clothing?"
3. "What did the malaria RDT show?"

**Escalation:** Suspected rickettsial illness = empirical doxycycline without waiting for laboratory confirmation (treatment delay increases mortality substantially). Malaria = ACT. Do not withhold doxycycline pending RDT if eschar is found or tick exposure is documented.

---

#### RP-07: Dengue vs Rickettsial illness

**Pathways:** P5
**Note:** Rickettsial illness = governance_pending ⚠.

**Shared features:** Fever + rash, headache, myalgia, generalised malaise.

**Discriminating evidence:**
- Eschar: pathognomonic for rickettsial illness when present; absent in dengue
- Tick exposure history: specific for rickettsial; dengue requires mosquito vector in endemic area
- Rash character: rickettsial = maculopapular beginning on trunk or extremities, may become petechial; dengue = maculopapular with islands of normal-appearing skin, appears day 3–5
- Tourniquet test: positive in dengue (thrombocytopenia); negative in rickettsial illness
- Dengue warning signs: abdominal pain + vomiting + mucosal bleeding; not features of rickettsial illness

**Missing information required:** Eschar examination (full skin including hidden sites); tick exposure; tourniquet test; rash character and distribution; abdominal pain.

**Red flags:** Rickettsial neurological involvement (meningoencephalitis); dengue haemorrhagic features (mucosal bleeding, rapid deterioration).

**Disambiguation questions:**
1. "Is there any eschar — a small dark skin scab at a possible bite site?"
2. "Any tick bite or exposure to tick habitat?"
3. "Any abdominal pain, bleeding from the gums, or visible blood in stool?"

**Escalation:** Rickettsial illness: empirical doxycycline — do not delay for laboratory confirmation. Dengue with haemorrhagic features: same-day referral.

---

#### RP-08: Chikungunya vs Brucellosis

**Pathways:** P6, P9
**Note:** Brucellosis = governance_pending ⚠.

**Shared features:** Fever + arthralgia, systemic illness; both can produce prolonged or relapsing fever.

**Discriminating evidence:**
- Joint pattern: chikungunya = symmetric small-joint polyarthralgia (MCP, wrist, ankle, MTP); brucellosis = sacroiliac, hip, or knee (large-joint monoarthritis or oligoarthritis)
- Livestock exposure: brucellosis is discriminating — cattle, goats, camels in Kenya; raw milk consumption; abattoir or farm work
- Fever pattern: brucellosis = undulant (fever resolves and recurs over weeks, may persist months); chikungunya = acute fever resolves within 7–10 days, arthralgia may persist
- Rash: chikungunya may produce maculopapular rash during febrile phase; brucellosis does not
- Mosquito exposure (vector): chikungunya requires Aedes bite

**Missing information required:** Joint distribution (small peripheral vs large/sacroiliac); livestock or raw milk exposure; fever pattern over time (continuous vs relapsing); rash during febrile phase.

**Red flags:** Brucellosis with vertebral involvement (spondylitis) or endocarditis; chikungunya rarely life-threatening acutely.

**Disambiguation questions:**
1. "Which joints are most affected — small joints of the fingers, toes, or wrists, or larger joints like the hips, knees, or lower back?"
2. "Any contact with livestock (cattle, goats, camels) or consumption of raw milk or soft cheese?"
3. "Has the fever been continuous since it started, or does it resolve and then return over days or weeks?"

**Escalation:** Brucellosis: combination antibiotics (doxycycline + rifampicin for 6 weeks minimum); monotherapy leads to relapse. Chikungunya: symptomatic management; NSAIDs for arthralgia after acute febrile phase.

---

#### RP-09: Typhoid vs Brucellosis

**Pathways:** P9
**Note:** Brucellosis = governance_pending ⚠.

**Shared features:** Prolonged fever, malaise, systemic illness; both can produce splenomegaly, hepatomegaly, and GI overlap.

**Discriminating evidence:**
- Fever pattern: typhoid = stepwise rising fever (Wunderlich curve, increases daily for first week then plateaus); brucellosis = undulant (remitting-relapsing pattern over weeks)
- Relative bradycardia: typhoid (pulse-temperature dissociation); not a brucellosis feature
- Rose spots: faint pink abdominal maculae — typhoid (rare, often missed, pathognomonic when present)
- Livestock exposure: brucellosis discriminating
- Blood culture: positive for Salmonella typhi in ~50–75% of typhoid cases (early blood culture most sensitive); Brucella requires extended incubation and special media — cannot be excluded on standard blood culture

**Missing information required:** Fever pattern over days (step-wise rising vs relapsing); livestock or raw milk exposure; blood culture result; bowel pattern.

**Red flags:** Typhoid intestinal perforation (acute abdomen, rebound tenderness); brucellosis spondylitis (back pain, focal spinal tenderness) or endocarditis.

**Disambiguation questions:**
1. "Has the fever been rising steadily each day, or does it come and go — improving for a few days then returning?"
2. "Any contact with livestock or raw milk consumption?"
3. "Has a blood culture been collected and sent?"

**Escalation:** Typhoid perforation = immediate surgical referral. Brucellosis = prolonged combination antibiotic course; do not give monotherapy.

---

#### RP-10: Malaria vs Pneumonia — Fever + Respiratory

**Pathways:** P3 (cross-domain — Pneumonia owned by Respiratory domain)
**Shared features:** Fever + cough; both common in Kenya primary care and can co-occur.

**Discriminating evidence:**
- Malaria RDT positive: confirms malaria; cough is an associated symptom in malaria and should not anchor the diagnosis to a respiratory condition
- Focal respiratory signs: pneumonia = productive cough, pleuritic chest pain, focal crackles or bronchial breathing, reduced air entry; malaria does not produce focal respiratory signs
- Oxygen saturation: reduced SpO2 suggests respiratory pathology; not a malaria feature unless severe disease
- Sputum character: purulent sputum = pneumonia; absent or clear in malaria
- Co-infection: malaria and pneumonia can coexist — a positive RDT does not exclude concurrent focal pneumonia if respiratory signs are present

**Missing information required:** RDT result; respiratory examination findings (auscultation, percussion); sputum character; oxygen saturation; chest X-ray access.

**Red flags:** Hypoxia (SpO2 < 94%); multilobar involvement; inability to maintain oral intake; features of severe malaria (cerebral, jaundice, prostration) with respiratory compromise.

**Disambiguation questions:**
1. "What did the malaria RDT show?"
2. "Is the cough productive — does it produce phlegm or sputum?"
3. "Are there focal findings on chest auscultation?"

**Escalation:** Do not allow a positive RDT to preclude treating focal pneumonia if respiratory signs are present — treat both if both are diagnosed. Severe pneumonia (hypoxia, multilobar) = referral. Severe malaria = immediate treatment + referral.

---

#### RP-11: Dengue vs Typhoid — Fever + GI

**Pathways:** P4
**Shared features:** Fever, nausea, vomiting, abdominal pain or discomfort; both can present to primary care at an undifferentiated early stage.

**Discriminating evidence:**
- Onset pattern: dengue = acute (2–5 days); typhoid = insidious step-wise fever over 5–7 days
- Dengue warning signs: severe abdominal pain + vomiting + clinical deterioration = plasma leakage; typhoid does not produce this pattern of acute deterioration
- Relative bradycardia: typhoid (pulse-temperature dissociation); not a feature of dengue
- Thrombocytopenia on FBC: dengue; leucopenia with normal or low platelets in typhoid
- Dengue rash: maculopapular, day 3–5; absent in typhoid

**Missing information required:** Onset timeline; abdominal pain severity, character, and progression; haemorrhagic features; pulse rate relative to temperature height.

**Red flags:** Dengue: warning signs (abdominal pain + vomiting + clinical deterioration, mucosal bleeding); Typhoid: peritonism, perforation signs.

**Disambiguation questions:**
1. "Did the illness start suddenly or build up gradually over several days?"
2. "How severe is the abdominal pain, and is it getting worse rapidly?"
3. "Any skin rash?"

**Escalation:** Dengue with warning signs = same-day referral. Typhoid with peritonism = immediate surgical referral.

---

#### RP-12: Leptospirosis vs Dengue — Fever + Myalgia

**Pathways:** P6, P7
**Note:** Leptospirosis = governance_pending ⚠.

**Shared features:** Acute fever, severe myalgia, headache, malaise; both produce marked constitutional symptoms that can mask the diagnosis.

**Discriminating evidence:**
- Calf muscle tenderness: severe tenderness on palpation or compression of gastrocnemius — specific for leptospirosis; absent in dengue
- Conjunctival suffusion: bilateral periorbital redness without discharge — specific for leptospirosis; dengue may have conjunctival injection but less pronounced
- Retro-orbital pain: dengue (pathognomonic); absent in leptospirosis
- Tourniquet test: positive in dengue (thrombocytopenia); negative in leptospirosis
- Renal involvement: oliguria, haematuria — leptospirosis (Weil's disease); uncommon in dengue except in severe disease
- Exposure: floodwater or livestock = leptospirosis; mosquito bite in endemic area = dengue

**Missing information required:** Calf tenderness on examination; retro-orbital pain; tourniquet test; renal function (urine output, haematuria); floodwater or livestock exposure.

**Red flags:** Weil's disease (fever + jaundice + renal failure) = immediate referral. Dengue haemorrhagic features = same-day referral.

**Disambiguation questions:**
1. "Is there severe pain in the calf muscles — specifically in the back of the lower leg, on squeezing?"
2. "Is there pain behind or around the eyes?"
3. "Any exposure to floodwater, livestock, or occupational water contact in the past 2 weeks?"
4. "Any reduction in urine output?"

**Escalation:** Weil's disease = immediate referral for IV penicillin/doxycycline + fluid management. Dengue with haemorrhagic features = same-day referral.

---

#### RP-13: TB vs Pneumonia — Fever + Respiratory (Subacute)

**Pathways:** P3, P9 (cross-domain — TB owned by NTLD-P domain; Pneumonia by Respiratory domain)
**Shared features:** Fever, cough, respiratory symptoms; both common in Kenya primary care.

**Discriminating evidence:**
- Symptom duration: cough for ≥2 weeks = TB until proven otherwise (Kenya NTLD-P guideline); CAP = acute onset over days
- Night sweats: profuse night sweats = TB (systemic); not a CAP feature
- Weight loss: documented weight loss = TB; not CAP
- Haemoptysis: TB; uncommon in CAP except complicated cases
- Antibiotic response: CAP should substantially improve within 5–7 days of standard antibiotics; persistent fever and cough after treatment = urgent TB consideration
- HIV status: significantly increases TB risk and alters clinical presentation; HIV-positive patient with respiratory illness has high prior probability for TB

**Missing information required:** Cough duration (days vs weeks); weight loss; night sweats; haemoptysis; HIV status; close contacts with known TB; GeneXpert or AFB access.

**Red flags:** Haemoptysis; significant weight loss; HIV-positive patient with respiratory illness; failure to respond to standard antibiotics at 5–7 days.

**Disambiguation questions:**
1. "How long has the cough been present — days or weeks?"
2. "Any weight loss over the past weeks or months?"
3. "Night sweats?"
4. "Any blood in the sputum or when coughing?"
5. "Known HIV status, or any close contacts with known or suspected TB?"

**Escalation:** Suspected TB = do not treat empirically as CAP (risk of masking drug-susceptibility testing, delay in appropriate regimen); refer for sputum GeneXpert. CAP = standard antibiotic course. If both are suspected: treat CAP empirically and initiate TB investigation concurrently without delay.

---

#### RP-14: Typhoid vs Acute gastroenteritis — Fever + Diarrhoea

**Pathways:** P4 (cross-domain — AGE owned by Gastrointestinal domain)
**Shared features:** Fever + diarrhoea, vomiting, abdominal pain; both waterborne or food-borne in similar settings.

**Discriminating evidence:**
- Onset pattern: AGE = acute, typically hours after a specific food or water exposure; typhoid = insidious step-wise onset over days
- Fever degree and pattern: typhoid = high, sustained, rising; AGE = low-grade or absent, resolving within 24–72 hours
- Bowel pattern: early typhoid commonly causes constipation, not diarrhoea; AGE is characterised by diarrhoea
- Relative bradycardia: typhoid (pulse-temperature dissociation); not AGE
- Duration: AGE is self-limiting (3–7 days typical); typhoid worsens without antibiotics

**Missing information required:** Fever duration and pattern; onset timing relative to food or water exposure; bowel pattern (constipation or diarrhoea in early illness); fever severity.

**Red flags:** Typhoid: perforation (acute abdomen, rebound tenderness, peritonism); sustained fever beyond 5–7 days without improvement on supportive care.

**Disambiguation questions:**
1. "How long has the fever been present, and is it getting worse each day or starting to improve?"
2. "Did the symptoms start suddenly after a specific meal or drink, or come on gradually over several days?"
3. "In the early part of the illness, was there more constipation or more diarrhoea?"

**Escalation:** Typhoid = antibiotics guided by local resistance patterns; monitor for complications. AGE = ORS and supportive care; antibiotics only for bloody stool, high-risk host, or systemic features.

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
- Section 3 presentation map — complete (2026-09-14). 9 pathways, 17 candidates, cross-domain participants and exclusions documented.
- Section 4 pairwise matrix — complete (2026-09-14). 17 pairs: 3 mandatory safety pairs + 14 required pairs. 5 pairs blocked on governance decisions (governance_pending conditions); 2 cross-domain pairs.
- Numerical thresholds for evaluation gates — not yet set; to be defined using current baselines (8/8 RAG, 4/5 disambiguation, 94% reasoning deterministic subset).
- Effort estimate: 2 new AFI-owned cards required before governance decisions (Meningitis, Cholera); Dengue and Chikungunya cards already validated. Up to 5 additional if Brucellosis/Leptospirosis/Rickettsial are approved. 17 pairwise evaluation fixtures required; 5 blocked pending governance decisions.
