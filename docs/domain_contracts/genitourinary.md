# Genitourinary — Domain Contract

**Status:** Draft
**Domain owner:** SS
**Source:** Kenya MOH Clinical Guidelines for Management and Referral of Common Conditions at Level 2-3 (2024), Chapter 15
**Purpose:** Scope, condition inventory, evaluation requirements and completion gate for the Genitourinary clinical domain.

> **Domains own conditions. Presentations connect conditions across domains. Authoritative sources determine what is authored. Risk and clinical overlap determine what must be distinguished. Sequential validation determines when the domain is complete.**

---

## 1. Domain Scope

### 1.1 Clinical scope

Primary-care presentation and initial clinical decision support for patients presenting with **urinary tract symptoms, renal dysfunction, or renal syndromes**.

The domain addresses:

- common urinary tract infections encountered in Kenyan primary care;
- renal syndromes (nephritic, nephrotic) that present to primary care and require recognition and referral;
- acute and chronic renal failure recognition and referral thresholds;
- initial diagnostic discrimination and missing-information identification;
- red-flag recognition and escalation.

The domain does **not** provide:

- nephrology specialist management (immunosuppression, biopsy interpretation, dialysis initiation);
- urological operative management;
- definitive diagnostic confirmation where the required investigation is unavailable at Level 2-3;
- oncological management of genitourinary malignancy.

### 1.2 Level-of-care framing — recognition and referral

This domain is structurally different from Acute Febrile Illness, and card authoring must reflect it.

MOH Vol 2 terminates most Chapter 15 conditions with an explicit referral instruction rather than a management protocol:

| Condition | Vol 2 terminal instruction |
|-----------|----------------------------|
| Acute prostatitis | "Diagnosis: Refer to higher facility level. Treatment: Refer to higher level facility." |
| Haematuria | "Refer to higher level urgently for appropriate management." |
| Acute glomerulonephritis | "Refer to higher level for appropriate management." |
| Nephrotic syndrome | "Refer to higher level for definitive management." |
| Glomerulonephritis | "Refer for definitive treatment." |
| Chronic kidney disease | "Investigations: Refer to higher level facility." |

Only lower UTI and uncomplicated acute pyelonephritis carry a full primary-care treatment pathway.

**Authoring consequence:** for referral-terminal conditions the CDS value is *recognition, discrimination and correct escalation urgency* — not management. These cards are authored to **recognition-and-refer scope**, following the Appendicitis precedent in the Gastrointestinal domain. Section 9 (`diagnostic_context`) must state the level-of-care boundary explicitly.

### 1.3 Domain boundary

A condition has one canonical domain, determined by the primary Kenyan guideline responsible for its diagnosis at the target level of care. The Acute Febrile Illness contract assigns UTI to this domain:

```
UTI
  canonical domain → Genitourinary

acute fever pathway
  → UTI may participate
```

Genitourinary conditions participate in fever (AFI), abdominal-pain (GI) and chronic-disease (endocrine, cardiovascular) pathways without transferring ownership.

Electrolyte disturbances (hyperkalaemia, hypokalaemia) and anatomical findings (palpable renal masses) appear in MOH Chapter 15 but are not disease-domain conditions. They are modelled as red flags and escalation triggers on the parent condition cards.

---

## 2. Condition Inventory

### 2.1 Source hierarchy

1. **Kenya MOH Clinical Guidelines Vol 2 (2024) — Level 2-3** ← primary source for every condition in this domain
2. Kenya MOH disease-specific guideline
3. WHO guideline
4. Professional society guideline (EAU, KDIGO)

Where sources conflict, the higher-ranked Kenyan source takes precedence.

### 2.2 Two-source requirement — domain-wide

**Neither MOH volume contains differential-diagnosis or argues-against content for any Chapter 15 condition.** Card sections 5 (typical presentation), 6 (important differential diagnoses) and 7 (features that argue against) therefore require a supplementary source for **every card in this domain** — the two-source pattern used by Cholera, Brucellosis, Leptospirosis, COPD and Acute viral hepatitis A.

| Condition group | Supplementary source | Edition |
|-----------------|---------------------|---------|
| UTI, pyelonephritis, prostatitis | **EAU** — Guidelines on Urological Infections | **2026** (limited update of 2025) |
| Acute GN, nephrotic syndrome | **KDIGO** — Management of Glomerular Diseases | **2021** (base document; updated chapter-by-chapter) |
| Acute kidney injury | **KDIGO** — Acute Kidney Injury | **2012** ⚠ see below |
| Chronic kidney disease | **KDIGO** — Evaluation and Management of CKD | **2024** |

Kenya MOH Vol 2 remains `primary_source` for every condition; supplementary sources are recorded under `supplementary_sources` in `corpus/sources.yaml` with per-section coverage.

KDIGO is cited inside MOH Vol 2 itself — for the AKI definition (§15.8.1) and the CKD criteria table (§15.8.2) — so for the renal group the supplementary source is the one the primary source already defers to.

⚠ **AKI edition.** KDIGO 2012 is the current *published* AKI guideline. The KDIGO 2026 AKI/AKD guideline went to public review in March 2026 and remains in preparation, so it is **not citable**. The 2012 diagnostic criteria are unchanged and are those reproduced in MOH Vol 2. Revisit when 2026 is published.

**CKD edition.** KDIGO 2024 is used rather than the 2012 edition MOH Vol 2 cites — 2024 is current and supersedes it. This matters because Vol 2's own staging table is empty in the extracted text (§2.4).

**Nephrotic syndrome scope.** The card is adult-scoped, matching MOH Table 15.2 ("Clinical Definition of Adult Nephrotic Syndrome"). The separate KDIGO 2025 paediatric nephrotic syndrome guideline is out of scope.

### 2.3 Inventory

**Pathway codes** (defined in §3):
G1 lower urinary tract symptoms · G2 fever + flank pain · G3 haematuria · G4 oedema/proteinuria · G5 reduced urine output · G6 acute flank colic · G7 male perineal/pelvic pain · G8 chronic renal decline

| Condition | ICD-11 | Primary source | Supplementary | Pathways | Safety | Card status |
|-----------|--------|----------------|---------------|----------|--------|-------------|
| Urinary tract infection (lower / cystitis) | `GC08.Z` | Vol 2 §15.1 | EAU | G1, G3 | Important | **Enriched 2026-09-18** (`uti`, v1.9) |
| Acute pyelonephritis | `GB51` | Vol 2 §15.2.1 | EAU | G2, G1, G3 | High | **Committed 2026-09-18** |
| Acute bacterial prostatitis | `GA91.Y` see §2.4 | Vol 2 §15.4.1 | EAU | G7, G1, G2 | High | **Committed 2026-09-18** |
| Acute glomerulonephritis (acute nephritic syndrome) | `GB40` | Vol 2 §15.5 + §15.7.1 | KDIGO | G3, G4 | High | Not started |
| Nephrotic syndrome | `GB41` | Vol 2 §15.6 | KDIGO | G4 | High | Not started |
| Acute kidney injury | see §2.4 | Vol 2 §15.8.1 | KDIGO | G5, G2, G6 | High | Not started |
| Chronic kidney disease | `GB61.Z` | Vol 2 §15.8.2 | KDIGO | G8, G4, G5 | Important | **Committed 2026-09-22** |

**Not authored as condition cards** — findings, syndromes and biochemical states, modelled as pathway triggers, red flags or `graph.confirms` terms on parent cards:

| MOH section | Item | Modelled as |
|-------------|------|-------------|
| §15.3.1 | Haematuria | Pathway G3 trigger; `associated_symptoms` / red flag |
| §15.3.2 | Pyuria | `confirms` term on UTI/pyelonephritis; sterile pyuria → TB cross-domain link |
| §15.4.2 | Hyperkalaemia | Red flag on AKI and CKD cards |
| §15.4.3 | Hypokalaemia | Red flag on CKD card |
| §15.4.4 | Abdominally palpable renal masses | Red flag — immediate referral |
| — | Nephrolithiasis | `differentials` term on the pyelonephritis, AKI and CKD cards (named in Vol 2 §15.3.1, §15.8.1, §15.8.2 as a cause of haematuria, post-renal AKI and CKD). **Use the canonical form `renal colic`** — "nephrolithiasis" is a Do-Not-Use synonym in `conditions_vocabulary.md` |

### 2.4 Authoring notes

**UTI (existing card).** The existing `uti` card (ICD-11 `GC08.Z`, ICD-10 `N39.0`) predates this contract and is **not** re-authored. Enrichment pass only, adding: the complicated-UTI referral trigger (fever ≥38 °C, flank pain, vomiting), the "UTI in males is always complicated" rule, and `DIFFERENTIATED_FROM` edges to the new domain cards.

**Acute pyelonephritis.** The strongest Chapter 15 section — aetiology, complications, clinical features, investigations, outpatient vs inpatient criteria and an explicit referral trigger. ICD-11 `GB51`, clean WHO API match.

**Acute bacterial prostatitis.** ⚠ **Thinnest section in the chapter.** Vol 2 supplies aetiology, risk factors, clinical features, DRE findings and complications, then terminates at referral. EAU supplementation is mandatory for this card, not optional.

One safety instruction must be preserved close to verbatim: *"Avoid prostate massage due to severe tenderness and risk of inducing bacteremia/sepsis."*

⚠ **ICD-11 requires an override.** The WHO API returns `GA91.Y` ("Other specified inflammatory and other diseases of prostate") for "acute prostatitis" — an imprecise match. This card needs an `icd_search_term` with the exact WHO canonical title before `scripts/verify_icd.py` will set `icd_verified: true`.

**Acute glomerulonephritis.** Vol 2 covers this at both §15.5 (post-streptococcal framing, clinical features, referral) and §15.7.1 (RPGN typology: PSGN, IgA nephropathy, Henoch-Schönlein purpura, Wegener's granulomatosis, lupus nephritis). **One card**, scoped to acute nephritic syndrome with post-streptococcal GN as the dominant Kenya primary-care presentation. The RPGN typology enters `diagnostic_context` and `red_flags`. Chronic GN is folded into the CKD card as an aetiology. ICD-11 `GB40`.

**Nephrotic syndrome.** Vol 2 §15.6 provides a clinical definition table (proteinuria ≥3.5 g/day, serum albumin ≤30 mg/dl, oedema, dyslipidaemia), classification, clinical features, complications and supportive management. ICD-11 `GB41`, clean WHO API match.

> ⛔ **Known defect in the MOH source — do not encode.** Vol 2 §15.6 "Clinical Features" opens with *"Symptoms of bacteremia (fever, chill, joint pain, and muscle pain)"* — a verbatim duplicate of the first clinical-feature line in §15.4.1 Acute Bacterial Prostatitis. This is a copy-paste artefact, not a feature of nephrotic syndrome. Do **not** encode bacteraemia symptoms as cardinal or associated features on this card. Flag to the clinical reviewer at Step 7.

**Acute kidney injury.** Well developed in Vol 2: KDIGO diagnostic criteria, a three-part aetiology table (pre-renal 60%, intrinsic renal 35%, post-renal 5%), examination findings, investigations, management, and explicit referral criteria — **anuria >24 h, oliguria >48 h, or hyperkalaemia unresponsive to medical treatment**. These map directly to `graph.red_flags`.

Vol 2 states the core discrimination task outright: *"the history and physical exam should focus on determining the etiology of AKI and to differentiate AKI from CKD"* — which is why GU-MSP-02 is a mandatory safety pair.

**Chronic kidney disease.** Vol 2 defines CKD (creatinine elevated ≥3 months, eGFR <60), lists risk factors and aetiology, and gives clinical features grouped by system (biochemical, cardiovascular, skeletal, nervous, haematological, skin).

⚠ **Vol 2 Table 15.5 ("Criteria for Chronic Kidney Disease") is empty in the extracted text** — only its KDIGO 2012 citation survived extraction. Take CKD staging criteria from KDIGO directly, not from the extract.

**Genitourinary schistosomiasis — known gap.** Vol 2 §15.3.1 names schistosomiasis as a cause of haematuria. It has no card and no Chapter 15 section, and its canonical domain is not Genitourinary. In Kenya it is a clinically significant cause of visible haematuria in endemic areas (lake basin, coastal). Its absence weakens pathway G3 in those regions and must be stated as a known limitation at domain freeze.

---

## 3. Presentation and Differential Map

Presentation-first. Each pathway answers: *"A patient arrives with this cluster — what conditions must the system consider?"*

**Legend:** ● card exists · ○ card needed · ◑ cross-domain participant, card exists · ◌ differential term only, no card

---

**G1 — Lower urinary tract symptoms**
*Dysuria, frequency, urgency, suprapubic discomfort, without systemic features.*

| Candidate | Status | Safety | Notes |
|-----------|--------|--------|-------|
| Urinary tract infection (lower) | ● | Important | Most common cause; mostly a clinical diagnosis from history |
| Acute pyelonephritis | ○ | High | Early upper-tract disease may present with LUTS before fever or flank pain |
| Acute bacterial prostatitis | ○ | High | In men — LUTS plus perineal pain; UTI in males is always complicated |
| Nephrolithiasis | ◌ | Important | Distal ureteric stone produces frequency and urgency mimicking cystitis |

---

**G2 — Fever with flank or loin pain**
*Fever ≥38 °C with costovertebral angle tenderness or loin pain.*

| Candidate | Status | Safety | Notes |
|-----------|--------|--------|-------|
| Acute pyelonephritis | ○ | High | Primary candidate; Vol 2 referral trigger is fever + flank pain + vomiting |
| Acute bacterial prostatitis | ○ | High | Bacteraemic presentation in men — fever, chills, myalgia |
| Nephrolithiasis with infection | ◌ | High | Obstructed infected kidney is a urological emergency — highest urgency in this pathway; must appear in the pyelonephritis card's `differentials` and `red_flags` (§4.4 GU-MSP-05) |
| Malaria | ◑ | High | Endemic nationwide; fever without localising focus must not be anchored to UTI on urinalysis alone |
| Typhoid fever | ◑ | High | Fever with abdominal symptoms |

---

**G3 — Haematuria**
*Visible (gross) or microscopic blood in urine.*

| Candidate | Status | Safety | Notes |
|-----------|--------|--------|-------|
| Urinary tract infection | ● | Important | Vol 2 §15.3.1 lists infection first among haematuria causes |
| Acute glomerulonephritis | ○ | High | Tea-coloured urine; dysmorphic RBCs and RBC casts are pathognomonic of glomerular inflammation |
| Nephrolithiasis | ◌ | Important | Haematuria with colic |
| Pulmonary / genitourinary tuberculosis | ◑ | High | Vol 2 §15.3.2 — sterile pyuria is often due to TB |
| Genitourinary schistosomiasis | — | Important | Named in Vol 2 §15.3.1; endemic lake basin and coast; **no card — known gap (§2.4)** |

*Vol 2 §15.3.1 additionally names trauma, meatal ulcers, blood disorders (including sickle cell disease), tumours and congenital abnormalities. Outside domain scope, but they must appear in `differential_diagnoses` prose where clinically material.*

---

**G4 — Oedema, puffiness, or proteinuria**
*Periorbital or peripheral oedema, ascites, or proteinuria on urinalysis.*

| Candidate | Status | Safety | Notes |
|-----------|--------|--------|-------|
| Nephrotic syndrome | ○ | High | Oedema is the predominant symptom; starts at eyelids, progresses to lower limbs and sacrum, then anasarca |
| Acute glomerulonephritis | ○ | High | Puffiness of eyes more noticeable in the morning; oedema seldom severe or generalised — key discriminator from nephrotic syndrome |
| Chronic kidney disease | ○ | Important | Oedema with long-standing hypertension or diabetes |
| Anaemia | ◑ | Important | Oedema in severe anaemia |

---

**G5 — Reduced urine output or rising creatinine**
*Oliguria, anuria, or biochemical evidence of renal impairment.*

| Candidate | Status | Safety | Notes |
|-----------|--------|--------|-------|
| Acute kidney injury | ○ | High | KDIGO criteria; Vol 2 referral triggers — anuria >24 h, oliguria >48 h, refractory hyperkalaemia |
| Chronic kidney disease | ○ | Important | Must be distinguished from AKI — Vol 2 states this discrimination explicitly |
| Nephrolithiasis (obstructive) | ◌ | High | Post-renal AKI; named in Vol 2 §15.8.1 as an intrarenal obstructive cause — must appear in the AKI card's `differentials` |
| Acute glomerulonephritis | ○ | High | Oliguric phase followed by diuretic phase |

---

**G6 — Acute severe flank pain (colic)**
*Sudden severe loin-to-groin pain, often with restlessness, nausea, vomiting.*

| Candidate | Status | Safety | Notes |
|-----------|--------|--------|-------|
| Nephrolithiasis | ◌ | Important | Clinically the primary candidate |
| Acute pyelonephritis | ○ | High | Flank pain with fever; pain is typically constant rather than colicky |
| Appendicitis | ◑ | High | Retrocaecal appendicitis can present with right flank pain |

> ⚠ **G6 has no owned condition card.** A patient with classic uncomplicated renal colic — colicky loin-to-groin pain, restlessness, haematuria, no fever — has no card that fits, and the system will surface acute pyelonephritis as the nearest candidate. That is clinically wrong for this presentation.
>
> **Required mitigation, to be implemented during card authoring:** the pyelonephritis card's `argues_against` section must state that **colicky pain with restlessness and absent fever argues against pyelonephritis**, and nephrolithiasis must appear in its `differentials`. This is a stated limitation at domain freeze.

---

**G7 — Male perineal, pelvic, or rectal pain**
*Perineal, genital, or rectal pain with urinary symptoms in men.*

| Candidate | Status | Safety | Notes |
|-----------|--------|--------|-------|
| Acute bacterial prostatitis | ○ | High | Perineal, genital and rectal pain plus LUTS; DRE — soft, swollen, tense prostate with severe pressure pain |
| Urinary tract infection (complicated) | ● | Important | UTI in males is complicated by definition |
| Acute pyelonephritis | ○ | High | Ascending infection |

---

**G8 — Chronic renal decline**
*Fatigue, pruritus, anaemia, nausea, or long-standing hypertension/diabetes with renal impairment.*

| Candidate | Status | Safety | Notes |
|-----------|--------|--------|-------|
| Chronic kidney disease | ○ | Important | Vol 2 clinical features by system: biochemical, cardiovascular, skeletal, neurological, haematological, skin |
| Acute kidney injury | ○ | High | Acute-on-chronic is explicitly named as a third category in Vol 2 §15.8 |
| Anaemia | ◑ | Important | Anaemia of chronic kidney disease |
| Type 2 diabetes mellitus | ◑ | Important | Leading CKD aetiology |
| Essential hypertension | ◑ | Important | Both cause and consequence of CKD |

### 3.1 Cross-domain participation

| Condition | Canonical domain | Participates in |
|-----------|-----------------|------------------|
| Malaria | Acute Febrile Illness | G2 |
| Typhoid fever | Acute Febrile Illness | G2 |
| Pulmonary tuberculosis | NTLD-P | G3 (sterile pyuria / genitourinary TB) |
| Appendicitis | Gastrointestinal | G6 |
| Anaemia | Haematological | G4, G8 |
| Type 2 diabetes mellitus | Endocrine | G8 |
| Essential hypertension | Cardiovascular | G8 |

These appear because excluding them is clinically necessary. They do not require new cards under this contract.

### 3.2 Conditions not included

| Condition | Reason |
|-----------|--------|
| Benign prostatic hypertrophy | No Chapter 15 section; chronic urological management outside Level 2-3 diagnostic scope |
| Genitourinary malignancy (bladder, prostate, renal cell) | Recognition-only; MOH Chapter 9 (Neoplasms) is the correct domain |
| Polycystic kidney disease, horseshoe kidney, hydronephrosis | Structural/congenital, referral-only, no diagnostic discrimination value at Level 2-3 |
| Nephrolithiasis | No Vol 2 chapter; retained as a `differentials` term (§2.3) |
| Sexually transmitted infections | Separate MOH chapter and vertical programme; distinct domain |
| Conditions in pregnancy (including UTI in pregnancy) | MOH Chapter 11; obstetric domain overlay — flagged on the UTI card |
| Renal tubular acidosis, cystinuria | Specialist-diagnosed; no primary-care discrimination pathway |

Inclusion requires: routine primary-care diagnostic relevance + a plausible recognition/referral pathway at Level 2-3 + a defensible authoritative source.

---

## 4. Pairwise Disambiguation Matrix

### 4.1 Entry criteria

**Required pair:** both conditions are plausible in Kenyan primary care and share at least two clinically important features.

**Mandatory safety pair:** the presentations materially overlap, **or** failure to distinguish them could materially alter urgency, referral or immediate management.

### 4.2 Pair index

◌ marks a pair whose second condition has no card — the clinical content is authored into the card that does exist, but no evaluation fixture can be built. ↔ marks cross-domain pairs.

| ID | Pair | Pathways | Priority |
|----|------|----------|----------|
| GU-MSP-01 | Acute pyelonephritis vs Lower UTI | G1, G2 | Mandatory safety |
| GU-MSP-02 | Acute kidney injury vs Chronic kidney disease | G5, G8 | Mandatory safety |
| GU-MSP-03 | Acute glomerulonephritis vs Nephrotic syndrome | G3, G4 | Mandatory safety |
| GU-MSP-04 | Acute bacterial prostatitis vs Lower UTI (male) | G1, G7 | Mandatory safety |
| GU-MSP-05 | Nephrolithiasis (obstructed + infected) vs Acute pyelonephritis ◌ | G2, G6 | Mandatory safety — content authored into the pyelonephritis card |
| GU-RP-01 | Acute pyelonephritis vs Malaria ↔ | G2 | Required |
| GU-RP-02 | Acute glomerulonephritis vs Lower UTI | G3 | Required |
| GU-RP-03 | Nephrolithiasis vs Lower UTI ◌ | G1, G3, G6 | Required |
| GU-RP-04 | Nephrotic syndrome vs Chronic kidney disease | G4, G8 | Required |
| GU-RP-05 | Acute kidney injury vs Nephrolithiasis (post-renal) ◌ | G5, G6 | Required |
| GU-RP-06 | Chronic kidney disease vs Anaemia ↔ | G8 | Required |
| GU-RP-07 | Acute pyelonephritis vs Appendicitis ↔ | G2, G6 | Required |
| GU-RP-08 | Acute glomerulonephritis vs Essential hypertension ↔ | G4 | Required |
| GU-RP-09 | Lower UTI vs Genitourinary tuberculosis ↔ | G1, G3 | Required |
| GU-RP-10 | Acute pyelonephritis vs Typhoid fever ↔ | G2 | Required |

### 4.3 Mandatory safety pairs

#### GU-MSP-01: Acute pyelonephritis vs Lower UTI

**Pathways:** G1, G2
**Why mandatory:** Vol 2 treats lower UTI at primary care but instructs referral for complicated/upper-tract disease. Misclassifying pyelonephritis as cystitis delays referral and risks abscess formation, septic shock and kidney damage.

**Shared features:** Dysuria, frequency, urgency, pyuria on urinalysis.

**Discriminating evidence:**
- Fever ≥38 °C: pyelonephritis; typically absent in uncomplicated cystitis
- Flank pain / costovertebral angle tenderness: pyelonephritis; absent in cystitis
- Nausea and vomiting: pyelonephritis; uncommon in cystitis
- Suprapubic discomfort as the dominant localising symptom: cystitis
- Male sex: UTI in males is complicated by definition, raising the threshold for a simple-cystitis label

**Missing information required:** Temperature; flank pain and CVA tenderness on examination; vomiting; sex; pregnancy status; structural abnormality or catheter; diabetes or immunosuppression.

**Red flags:** Fever ≥38 °C + flank pain + vomiting (Vol 2 explicit referral trigger); inability to tolerate oral intake; pregnancy; signs of sepsis.

**Disambiguation questions:**
1. "Is there fever, and has the temperature been measured?"
2. "Is there pain in the flank or loin, or tenderness over the back below the ribs?"
3. "Has there been any vomiting, or inability to keep fluids down?"

**Escalation:** Complicated UTI or pyelonephritis with fever, flank pain or vomiting — refer. Uncomplicated cystitis — treat at primary care.

---

#### GU-MSP-02: Acute kidney injury vs Chronic kidney disease

**Pathways:** G5, G8
**Why mandatory:** Vol 2 states the task explicitly. AKI is often reversible and time-critical; CKD is a chronic-management pathway. Acute-on-chronic is a third state that must not be missed.

**Shared features:** Elevated creatinine, oedema, reduced urine output, hyperkalaemia, anaemia, hypertension, nausea.

**Discriminating evidence:**
- Time course: AKI = creatinine rise within 48 h, or ≥1.5× baseline within 7 days; CKD = abnormal creatinine sustained ≥3 months with eGFR <60
- Prior baseline creatinine: the single most useful discriminator — its absence is itself the key missing information
- Anaemia and renal bone disease: favour CKD (chronic erythropoietin deficiency); typically absent in pure AKI
- Skin changes — pruritus, darkening: CKD
- Kidney size on ultrasound: small, shrunken kidneys favour CKD (referral-level investigation)
- Identifiable acute precipitant — vomiting, diarrhoea, haemorrhage, sepsis, NSAIDs, aminoglycosides, contrast: favours AKI

**Missing information required:** Any previous creatinine result; symptom duration; known diabetes or hypertension duration; recent nephrotoxic drug exposure; recent volume loss or sepsis; urine output trend.

**Red flags:** Anuria >24 h; oliguria >48 h; hyperkalaemia not responding to medical treatment (all three are Vol 2 explicit referral criteria); pulmonary oedema; encephalopathy; pericarditis.

**Disambiguation questions:**
1. "Is there any previous kidney function or creatinine result to compare against?"
2. "Over what period have the symptoms developed — days, or months?"
3. "Has there been recent vomiting, diarrhoea, bleeding, or use of painkillers such as ibuprofen or diclofenac?"
4. "What has urine output been over the past 24–48 hours?"

**Escalation:** Meet any Vol 2 referral criterion — refer immediately. Avoid nephrotoxic drugs in both. Do not attribute a raised creatinine to CKD without a prior baseline.

---

#### GU-MSP-03: Acute glomerulonephritis vs Nephrotic syndrome

**Pathways:** G3, G4
**Why mandatory:** Both present with oedema and abnormal urinalysis and both are referral-terminal, but the syndromes are distinct, urgency differs, and the nephritic presentation carries hypertensive-encephalopathy risk. Vol 2 notes both can coexist ("nephritic nephrotic syndrome").

**Shared features:** Oedema, proteinuria, reduced renal function, referral required.

**Discriminating evidence:**
- Haematuria: acute GN — haematuria or tea-coloured urine is a cardinal feature; not a defining feature of nephrotic syndrome
- Oedema character and severity: acute GN — puffiness of the eyes, more noticeable in the morning, *"seldom severe or generalized"*; nephrotic syndrome — begins at eyelids then progresses to lower limbs, sacrum, and when severe becomes generalised with ascites and effusions (anasarca)
- Proteinuria magnitude: nephrotic = ≥3.5 g/day with serum albumin ≤30 mg/dl — both *indispensable prerequisites* per Vol 2 Table 15.2; acute GN proteinuria is typically sub-nephrotic
- Hypertension: prominent in acute GN — headaches, visual disturbance, vomiting, pulmonary oedema, convulsions and coma from encephalopathy
- Preceding streptococcal infection: acute GN — follicular tonsillitis with cervical adenitis 7–10 days prior, or impetigo 2–3 weeks prior
- Urine microscopy: dysmorphic RBCs and RBC casts are pathognomonic of glomerular inflammation (acute GN)

**Missing information required:** Urinalysis — blood and protein quantification; serum albumin; recent sore throat or skin infection and its timing; blood pressure; oedema distribution and diurnal pattern; urine colour.

**Red flags:** Hypertensive encephalopathy — convulsions, coma, visual disturbance; pulmonary oedema with dyspnoea; anuria; anasarca with respiratory compromise; venous thromboembolism (nephrotic syndrome complication from urinary loss of antithrombin III, protein C and protein S).

**Disambiguation questions:**
1. "What colour is the urine — is it tea-coloured, cola-coloured, or visibly bloody?"
2. "Where is the swelling, and is it worse in the morning around the eyes or worse in the legs later in the day?"
3. "Was there a sore throat or skin infection in the past few weeks?"
4. "What is the blood pressure?"

**Escalation:** Both refer. Acute GN with encephalopathy, convulsions or pulmonary oedema — emergency referral. Nephrotic syndrome with respiratory compromise or suspected thromboembolism — emergency referral.

---

#### GU-MSP-04: Acute bacterial prostatitis vs Lower UTI (male)

**Pathways:** G1, G7
**Why mandatory:** Male LUTS is never simple cystitis — Vol 2 classifies all male UTI as complicated. Acute bacterial prostatitis carries a specific procedural hazard: prostate massage can induce bacteraemia and sepsis. Failure to distinguish risks both an inappropriate examination and delayed referral.

**Shared features:** Dysuria, frequency, urgency in a male patient; pyuria.

**Discriminating evidence:**
- Perineal, genital or rectal pain: prostatitis; not a cystitis feature
- Systemic bacteraemic features — fever, chills, joint pain, muscle pain: prostatitis
- DRE findings: soft, swollen, tense prostate with severe pressure pain (prostatitis)
- Catheterisation or benign prostatic hypertrophy: prostatitis risk factors
- Acute urinary retention: suggests prostatitis with obstruction

**Missing information required:** Perineal or rectal pain; fever and rigors; DRE findings; catheter history; known BPH; ability to pass urine.

**Red flags:** ⛔ **Do not perform prostate massage** — Vol 2 explicit safety instruction: severe tenderness and risk of inducing bacteraemia/sepsis. Acute urinary retention; sepsis; prostatic abscess; epididymitis.

**Disambiguation questions:**
1. "Is there pain in the perineum, genitals, or rectum?"
2. "Is there fever with chills or shaking?"
3. "Is there difficulty passing urine, or complete inability to pass urine?"
4. "Is there a urinary catheter, or known prostate enlargement?"

**Escalation:** Vol 2 refers both diagnosis and treatment of acute bacterial prostatitis to a higher facility. Acute retention or sepsis — emergency referral.

---

#### GU-MSP-05: Nephrolithiasis (obstructed and infected) vs Acute pyelonephritis ◌

**Pathways:** G2, G6
**Why mandatory:** An obstructed, infected kidney is a urological emergency requiring decompression, not antibiotics alone. It is clinically indistinguishable from uncomplicated pyelonephritis on history without imaging, and it is the highest-urgency presentation in this domain.

**Authoring note:** nephrolithiasis has no card, so no evaluation fixture can be built for this pair. The discriminating evidence below must nonetheless be encoded into the **acute pyelonephritis card** — nephrolithiasis in `differentials`, colicky-pain-with-restlessness in `argues_against`, obstruction-with-fever in `red_flags`.

**Shared features:** Fever, flank pain, dysuria, nausea, vomiting, pyuria, haematuria.

**Discriminating evidence:**
- Pain character: stone — sudden onset, colicky, loin-to-groin radiation, patient restless and unable to lie still; pyelonephritis — constant dull flank pain, patient prefers to lie still
- Prior stone history or known renal calculi
- Anuria in a patient with a single functioning kidney, or bilateral obstruction — post-renal AKI
- Imaging: ultrasound showing hydronephrosis — referral-level investigation; a negative ultrasound does not exclude the pathology

**Missing information required:** Pain onset and character (colicky vs constant); radiation; previous stones; urine output; imaging access; fever.

**Red flags:** Fever + obstruction = emergency decompression; anuria; rapidly rising creatinine; sepsis. Any suspicion of an obstructed infected kidney is a same-day referral regardless of how well the patient appears.

**Disambiguation questions:**
1. "Did the pain come on suddenly in waves, and does it travel from the loin down towards the groin?"
2. "Can the patient lie still, or are they restless and unable to find a comfortable position?"
3. "Any previous kidney stones?"
4. "Has urine output fallen or stopped?"

**Escalation:** Suspected obstruction with fever — emergency referral for decompression. Do not treat as simple pyelonephritis.

---

### 4.4 Required pairs

Specifications for GU-RP-01 through GU-RP-10 are authored alongside their respective condition cards, in the §4.3 format: shared features, discriminating evidence, missing information, red flags, disambiguation questions, escalation implication.

**Authoring order** — a pair is specified as its second condition card is completed, so that no pair specification precedes the evidence base for both of its conditions.

---

## 5. Evaluation Architecture

One integrated domain evaluation suite with three scored dimensions: reasoning fixtures, pairwise disambiguation fixtures, safety fixtures. A fixture may cover more than one dimension; each has its own pass criterion.

### 5.1 Domain-specific evaluation constraint

This domain's cards are predominantly **recognition-and-refer** (§1.2). Fixtures must therefore score *referral urgency and red-flag recognition* at least as heavily as leading-candidate accuracy.

**A fixture that identifies the correct condition but fails to trigger referral is a failure, not a partial pass.**

This differs from AFI, where most conditions carry a primary-care treatment pathway, and must be reflected in fixture design before Stage 6.

### 5.2 Thresholds

To be set at inventory completion. Current baselines: 8/8 RAG regression gate (≥7/8 required per PR), 4/5 disambiguation, 90% reasoning deterministic gate.

> ⚠ The regression harness is stochastic. Measured over 9 runs on an unchanged corpus: 3, 6, 6, 6, 6, 7, 7, 7, 7.
> The variance originates in generation, not retrieval — with retrieval held byte-identical over 8 runs, one case
> returned three different leading diagnoses. A single run therefore cannot distinguish a real regression from a
> draw from this distribution. Set this domain's thresholds as k-of-N per case, not single-run.

---

## 6. Sequential Domain Pipeline

Stages 1–10, each gated, with the handoff rule that a stage cannot begin until the preceding stage has passed. A failed downstream stage returns the domain to the earliest affected upstream stage.

**Current gate dependencies:**

| Dependency | State |
|------------|-------|
| Kenya MOH Vol 2 source | ✅ In repo (`kenya_moh_vol2_2024.md`) |
| WHO ICD-11 API credentials (Steps 5–6) | ✅ Verified working |
| Supplementary sources (EAU, KDIGO) | ✅ Pinned in `corpus/sources.yaml` — see §2.2 |
| Cohere API key (Steps 10–11) | ❌ Trial quota exhausted — 1000 calls/month |

Cards can be authored and validated through Step 9. **Steps 10 (Chroma reload) and 11 (eval gate) cannot run**, and Step 14 forbids committing until Step 11 passes.

---

## 7. Domain Completion Criteria

The domain is complete only when all of the following are true **in sequence**:

1. Domain scope and boundary approved.
2. Condition inventory complete.
3. Every condition has an authoritative source and canonical domain owner.
4. Required cards authored and validated.
5. Retrieval/indexing meets the defined technical threshold.
6. Reasoning fixtures pass.
7. Every required pairwise distinction has evaluation coverage and passes.
8. Red-flag and escalation fixtures pass clinical safety review.
9. Clinician domain review complete.
10. Domain versioned/frozen with known limitations recorded.

A numerical condition count is not a completion criterion. The domain may be frozen with explicitly documented exclusions.

**Expected documented limitations at freeze:**
- Pathway G6 has no owned condition card (§3, G6).
- Genitourinary schistosomiasis has no card in any domain (§2.4).
- GU-MSP-05, GU-RP-03 and GU-RP-05 have no evaluation fixtures.

---

## 8. Existing Corpus Policy

The existing `uti` card remains in the corpus and is **not** re-authored under this contract. It receives an enrichment pass only (§2.4) and participates in AFI pathways without transferring ownership.

---

## 9. Freeze Principle

Once the domain satisfies the sequential completion gate it is versioned and frozen. Subsequent changes require an explicit card/version change, affected evaluation fixtures rerun, clinical review where clinically material, and a domain version increment.

The freeze creates a stable benchmark against which subsequent domain replication and system changes can be evaluated.
