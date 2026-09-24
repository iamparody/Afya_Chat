# Cardiovascular — Domain Contract

**Status:** Draft
**Purpose:** Define the scope, condition inventory, presentation pathways, and pairwise disambiguation requirements for the cardiovascular domain of the Kenya primary care CDS.

> **Domains own conditions. Presentations connect conditions across domains. Authoritative sources determine what is authored. Risk and clinical overlap determine what must be distinguished.**

---

## 1. Domain Scope

### 1.1 Clinical scope

The Cardiovascular domain covers **primary-care presentation and initial clinical decision support for patients presenting with symptoms referable to the heart, blood vessels, or blood pressure**.

The domain addresses:

- cardiovascular conditions encountered in Kenyan primary care;
- clinically important alternatives sharing cardiovascular presentations;
- safety diagnoses requiring recognition, stabilisation, and urgent referral;
- initial diagnostic discrimination and missing-information identification;
- red-flag recognition and escalation to Level 4 care.

The domain does **not** attempt to provide:

- ICU-level or cardiac intensive care management;
- specialist inpatient cardiac investigation (catheterisation, echocardiography, electrophysiology);
- chronic heart failure optimisation beyond primary care scope;
- comprehensive treatment protocols beyond the CDS scope defined by the authoritative source;
- surgical or interventional cardiology.

### 1.2 Domain boundary

A condition has **one canonical domain**, determined by the primary Kenyan guideline or programme responsible for its diagnosis and management at the target level of care.

A condition may nevertheless participate in multiple presentation pathways.

```
Pulmonary tuberculosis
  canonical domain → NTLD-P (infectious)

chest pain / dyspnoea pathway
  → PTB participates as a cross-domain safety candidate
```

This prevents duplicate condition cards while allowing cross-domain clinical reasoning.

**Scope boundary decisions:**

- **Blood pressure:** Essential hypertension and Hypertensive Crisis are canonical cardiovascular — blood pressure management is defined by cardiovascular guidelines at primary care.
- **Thromboembolism:** DVT and PE are canonical cardiovascular — vascular aetiology, managed under cardiovascular protocols at primary care level.
- **Structural and inflammatory heart disease:** Heart Failure, Pulmonary Oedema, AMI, Acute Rheumatic Fever, and Rheumatic Heart Disease are canonical cardiovascular.
- **Respiratory overlap:** Conditions presenting with dyspnoea (PE, Heart Failure, Pulmonary Oedema) participate in respiratory presentation pathways without transferring ownership to the Respiratory domain.
- **Renal overlap:** Hypertensive Crisis (with acute kidney injury) and Heart Failure (with fluid overload) may cross into nephrology presentation pathways without transferring ownership.
- **Infectious overlap:** Acute Rheumatic Fever follows streptococcal pharyngitis — the triggering infection is not cardiovascular-owned; the cardiac sequela (carditis, RHD) is.

---

## 2. Canonical Condition Inventory

### 2.1 Source hierarchy

Same hierarchy as AFI and GI domain contracts:

1. **Kenya MOH Standard Treatment Guidelines (STG)**
2. **Kenya MOH disease-specific guideline**
3. **WHO SMART DAK**
4. **WHO guideline**
5. **Other authoritative source**

Where sources conflict, the higher-ranked Kenyan source takes precedence.

### 2.2 Condition inventory

**Pathway codes used in this table:**
- BP — blood pressure abnormality (hypertension, crisis)
- CP — chest pain
- DYS — dyspnoea / breathlessness
- PED — peripheral oedema / leg swelling
- PAL — palpitations / arrhythmia
- SWL — unilateral limb swelling / pain (DVT)
- SYN — syncope / collapse

| Condition | Canonical domain | Primary source | Source type | Authoring method | Presentation pathways | Safety priority | Card status | Committed |
|-----------|-----------------|----------------|-------------|------------------|-----------------------|----------------|-------------|-----------|
| Essential hypertension | Cardiovascular | WHO HEARTS Technical Package (2023) | WHO guideline | Original corpus | BP | Routine | Draft | Yes — original card |
| Hypertensive Crisis | Cardiovascular | Kenya MOH Clinical Guidelines Vol 2 §3.2 (2024) | Kenya MOH STG | Method A (two-source: MOH §3.2 + Medscape 2024) | BP; SYN; DYS | High (safety) | Draft | Yes — 2026-09-21 |
| Deep vein thrombosis (DVT) | Cardiovascular | Kenya MOH Clinical Guidelines Vol 2 §3.3 (2024) + Medscape 2024 (two-source) | Kenya MOH STG | Method A | SWL; CP | Important | Draft | Yes — 2026-09-23 |
| Pulmonary embolism (PE) | Cardiovascular | Kenya MOH Clinical Guidelines Vol 2 §3.x (2024) — verify chapter | Kenya MOH STG ⚠ verify | Method A | DYS; CP; SYN | High (safety) | Not started | No |
| Heart Failure | Cardiovascular | Kenya MOH Clinical Guidelines Vol 2 §3.x (2024) — verify chapter | Kenya MOH STG ⚠ verify | Method A | DYS; PED; PAL | High (safety) | Not started | No |
| Acute pulmonary oedema | Cardiovascular | Kenya MOH Clinical Guidelines Vol 2 §3.x (2024) — verify chapter | Kenya MOH STG ⚠ verify | Method A | DYS; CP | High (safety) | Not started | No |
| Acute myocardial infarction (AMI) | Cardiovascular | Kenya MOH Clinical Guidelines Vol 2 §3.x (2024) — verify chapter | Kenya MOH STG ⚠ verify | Method A | CP; DYS; SYN | High (safety) | Not started | No |
| Acute rheumatic fever (ARF) | Cardiovascular | Kenya MOH Clinical Guidelines Vol 2 §3.x (2024) — verify chapter | Kenya MOH STG ⚠ verify | Method A | PAL; CP; PED | Important | Not started | No |
| Rheumatic heart disease (RHD) | Cardiovascular | Kenya MOH Clinical Guidelines Vol 2 §3.x (2024) — verify chapter | Kenya MOH STG ⚠ verify | Method A | DYS; PAL; PED | Important | Not started | No |
| Community-acquired pneumonia | **Respiratory** ← cross-domain | Kenya MOH Clinical Guidelines Vol 2 (2024) | Kenya MOH STG | — | DYS; CP | — | Draft | Yes |
| Pulmonary tuberculosis | **NTLD-P** ← cross-domain | Kenya NTLD-P Guidelines (2017) | Kenya MOH disease-specific | — | DYS; CP | — | Draft | Yes |
| Iron deficiency anaemia | **Haematological** ← cross-domain | WHO Haemoglobin Concentrations (2011) | WHO guideline | — | DYS; PAL | — | Draft | Yes |

### 2.3 Source verification notes

**Essential hypertension:** Original corpus card uses WHO HEARTS Technical Package (2023) as primary source. Kenya MOH Clinical Guidelines Vol 2 (2024) §3.1 likely covers hypertension management at primary care level — verify whether a Kenya-level source should take precedence and update `sources.yaml` if so.

**Hypertensive Crisis:** Kenya MOH Vol 2 §3.2 confirmed as primary source (accessed via PDF search). Section is thin (6 lines — management protocol only). Medscape 2024 used as supplementary source for clinical detail (emergency vs urgency distinction, target organ assessment criteria, differentials, argues-against). WHO 2023 Hypertension Fact Sheet used for epidemiological context. Two-source pattern documented in `corpus/sources.yaml`.

**DVT:** Kenya MOH Clinical Guidelines Vol 2 §3.3 confirmed as primary source. Section thin on clinical discriminators — Medscape 2024 used as supplementary (two-source pattern). Both documented in `corpus/sources.yaml`. Card committed 2026-09-23.

**PE, Heart Failure, Acute Pulmonary Oedema, AMI, ARF, RHD ⚠ verify:** Kenya MOH Clinical Guidelines Vol 2 (2024) Section 3 is the target source — chapter numbers require verification before authoring begins. If a chapter is absent or thin on clinical detail, the two-source pattern applies (MOH primary + Medscape supplementary). Verify chapter existence before opening an authoring branch.

### 2.4 Inventory governance decisions

| Condition | Decision required |
|-----------|------------------|
| DVT | Confirm Kenya MOH Vol 2 §3.x chapter exists and covers primary-care recognition criteria; if thin, identify Medscape / BSH supplementary |
| PE | Confirm Kenya MOH Vol 2 §3.x chapter; safety scope only (recognition + referral); if thin, apply two-source pattern |
| Heart Failure | Confirm Kenya MOH Vol 2 §3.x chapter; chronic vs acute failure scope decision |
| Acute pulmonary oedema | Confirm whether standalone chapter exists or is treated as a Heart Failure complication in MOH Vol 2 |
| AMI | Confirm Kenya MOH Vol 2 §3.x chapter; primary care scope = recognition + referral only |
| ARF | Confirm Kenya MOH Vol 2 §3.x chapter; Jones criteria coverage |
| RHD | Confirm Kenya MOH Vol 2 §3.x chapter; primary care scope = recognition + monitoring, not specialist management |
| Essential hypertension | Review whether WHO HEARTS or Kenya MOH Vol 2 §3.1 should be primary source in `sources.yaml` |

These governance decisions must be resolved before opening an authoring branch for each condition.

---

## 3. Presentation and Differential Map

### 3.1 Architecture

The map is **presentation-first**. Each row answers: *"A patient arrives with this symptom cluster — what conditions must the system consider?"*

Cross-domain participants (CAP, PTB, IDA) appear in the map without transferring ownership.

### 3.2 Presentation pathways

| Presentation cluster | Primary candidates (cardiovascular-owned) | Cross-domain candidates | Safety flags |
|---------------------|-------------------------------------------|------------------------|--------------|
| Severe headache + BP ≥180/120 | Hypertensive Crisis | Haemorrhagic stroke (AFI/neurological) | ⚠ High — immediate referral if end-organ signs |
| Hypertension incidental finding | Essential hypertension | White coat hypertension | — |
| Unilateral leg swelling + pain | DVT | Cellulitis, Baker's cyst | ⚠ Important — PE risk |
| Dyspnoea + pleuritic chest pain | PE | CAP, PTB, pneumothorax | ⚠ High — DVT source |
| Progressive dyspnoea + PED | Heart Failure | CAP, IDA, COPD | ⚠ High — acute decompensation |
| Acute breathlessness + frothy sputum | Acute pulmonary oedema | Severe asthma, CAP | ⚠ High — immediate referral |
| Chest pain ± radiation | AMI | PE, GERD, musculoskeletal | ⚠ High — ECG-based triage |
| Migratory joint pain + fever (post-pharyngitis) | ARF | Reactive arthritis, septic arthritis | ⚠ Important — carditis risk |
| Palpitations + dyspnoea (chronic) | RHD | Cardiomyopathy, IDA | ⚠ Important — AF risk |

---

## 4. Pairwise Discrimination Requirements

### 4.1 Safety-critical pairs

These pairs must be formally discriminated before the domain is considered clinically safe. A documented discrimination case and verified argues-against features are required for each.

| Pair | Primary risk | Discriminating feature(s) |
|------|-------------|--------------------------|
| Hypertensive Crisis vs Essential hypertension | Under-escalation of true emergency | BP ≥180/120 + end-organ signs vs elevated BP without end-organ damage |
| PE vs CAP | PE missed as pneumonia | Pleuritic pain + unilateral SWL vs productive cough + fever + consolidation |
| Acute pulmonary oedema vs Severe asthma | Treatment divergence (diuresis vs bronchodilation) | Pink frothy sputum + elevated JVP vs wheeze + prolonged expiration |
| AMI vs GERD/musculoskeletal | AMI missed | Radiation + diaphoresis + ECG changes vs positional/meal-related relief |
| ARF vs septic arthritis | Carditis consequence missed | Migratory large-joint + post-streptococcal vs single hot joint |

### 4.2 Governance note

Hypertensive Crisis vs Essential hypertension discrimination is partially implemented via:
- `_enforce_arguing_against_ranking()` post-hoc swap in `phase5/rag.py`
- HC argues_against graph block (5 features including BP below crisis threshold)
- EH red_flags section leading with end-organ damage language

Full pairwise DIFFERENTIATED_FROM Neo4j relationships for the cardiovascular domain are pending — follow the AFI/GI pattern when remaining cards are committed.

---

## 5. Authoring Sequence and Status

| Order | Condition | Branch | PR | Committed |
|-------|-----------|--------|----|-----------|
| 1 | Essential hypertension | original corpus | — | ✓ |
| 2 | Hypertensive Crisis | feat/cardiovascular-hypertensive-crisis | Open | ✓ 2026-09-21 |
| 3 | Deep vein thrombosis | feat/cardiovascular | — | ✓ 2026-09-23 |
| 4 | Pulmonary embolism | feat/cardiovascular-pe | Not opened | — |
| 5 | Heart Failure | feat/cardiovascular-heart-failure | Not opened | — |
| 6 | Acute pulmonary oedema | feat/cardiovascular-pulmonary-oedema | Not opened | — |
| 7 | Acute myocardial infarction | feat/cardiovascular-ami | Not opened | — |
| 8 | Acute rheumatic fever | feat/cardiovascular-arf | Not opened | — |
| 9 | Rheumatic heart disease | feat/cardiovascular-rhd | Not opened | — |

One branch per condition. Domain contract updated when each condition is committed.
