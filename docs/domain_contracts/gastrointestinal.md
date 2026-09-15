# Gastrointestinal — Domain Contract

**Status:** Draft
**Purpose:** Define the scope, condition inventory, presentation pathways, and pairwise disambiguation requirements for the gastrointestinal domain of the Kenya primary care CDS.

> **Domains own conditions. Presentations connect conditions across domains. Authoritative sources determine what is authored. Risk and clinical overlap determine what must be distinguished.**

---

## 1. Domain Scope

### 1.1 Clinical scope

The Gastrointestinal domain covers **primary-care presentation and initial clinical decision support for patients presenting with symptoms referable to the upper or lower gastrointestinal tract**.

The domain addresses:

- common GI conditions encountered in Kenyan primary care;
- clinically important alternatives that share GI presentations;
- safety diagnoses requiring recognition and urgent referral;
- initial diagnostic discrimination and missing-information identification;
- red-flag recognition and escalation.

The domain does **not** attempt to provide:

- surgical management of GI emergencies beyond recognition and referral;
- specialist inpatient GI investigation or endoscopy;
- chronic liver disease management;
- colorectal or GI oncology;
- inflammatory bowel disease management;
- comprehensive treatment protocols beyond the CDS scope defined by the authoritative source.

### 1.2 Domain boundary

A condition has **one canonical domain**, determined by the primary Kenyan guideline or programme responsible for its diagnosis and management at the target level of care.

A condition may nevertheless participate in multiple presentation pathways.

```
Cholera
  canonical domain → Acute Febrile Illness (infectious aetiology, notifiable disease response)

acute watery diarrhoea pathway
  → Cholera participates as a cross-domain safety candidate
```

This prevents duplicate condition cards while allowing cross-domain clinical reasoning.

**Scope boundary decisions:**

- **Upper GI boundary:** Conditions with a primary upper GI presentation (epigastric pain, heartburn, dyspepsia, reflux) are GI-owned.
- **Lower GI boundary:** Conditions where diarrhoea or lower abdominal pain is the primary presentation are GI-owned, unless the primary aetiology is systemic-infectious (owned by AFI or Infectious domain) or surgical beyond primary care.
- **Hepatic:** Acute viral hepatitis presenting with jaundice and GI symptoms is within primary care recognition scope. Chronic liver disease management is excluded.
- **Systemic diseases with GI manifestations:** Malaria (vomiting, GI overlap), Typhoid (diarrhoea), Cholera (watery diarrhoea) are owned by the Acute Febrile Illness domain. They participate as cross-domain candidates in GI presentation pathways without transferring ownership.
- **Surgical emergencies:** Appendicitis and PUD perforation are included as safety recognition diagnoses only — the CDS role is recognition and referral, not surgical management.

---

## 2. Canonical Condition Inventory

### 2.1 Source hierarchy

Same hierarchy as AFI domain contract:

1. **Kenya MOH Standard Treatment Guidelines (STG)**
2. **Kenya MOH disease-specific guideline**
3. **WHO SMART DAK**
4. **WHO guideline**
5. **Other authoritative source**

Where sources conflict, the higher-ranked Kenyan source takes precedence.

### 2.2 Condition inventory

**Pathway codes used in this table:**
- UGI — upper GI symptoms (epigastric pain, heartburn, bloating, dyspepsia)
- AWD — acute watery diarrhoea
- BD — bloody / inflammatory diarrhoea (dysentery)
- LAP — lower abdominal pain
- JAU — jaundice (acute)

| Condition | Canonical domain | Primary source | Source type | Presentation pathways | Safety priority | Existing card | Card status |
|-----------|-----------------|----------------|-------------|----------------------|----------------|---------------|-------------|
| Peptic ulcer disease | Gastrointestinal | American College of Gastroenterology — Management of H. pylori Infection (2021) | Other authoritative source | UGI | Important | Yes | Draft |
| Gastro-oesophageal reflux disease | Gastrointestinal | Kenya MOH Clinical Guidelines (2022) | Kenya MOH STG | UGI | Routine | Yes | Draft |
| Functional dyspepsia | Gastrointestinal | Rome IV Criteria (2016) | Other authoritative source | UGI | Routine | Yes | Draft |
| Acute gastroenteritis (infectious) | Gastrointestinal | WHO Diarrhoeal Disease Fact Sheet (2017) | WHO guideline | AWD | Routine–Important | Yes | Draft |
| Acute dysentery (Shigellosis) | Gastrointestinal | Kenya MOH Clinical Guidelines Vol 2 (2022) — confirm chapter | Kenya MOH STG ⚠ verify | BD | Important | No | Not started |
| Intestinal helminthiasis | Gastrointestinal | Kenya MOH / WHO deworming guidelines — source to confirm | Other authoritative source ⚠ source gap | UGI; AWD | Routine | No | Not started |
| Appendicitis | Gastrointestinal | Kenya MOH Clinical Guidelines Vol 2 (2022) — confirm chapter | Kenya MOH STG ⚠ verify | LAP | High (safety) | No | Not started |
| Acute viral hepatitis A | Gastrointestinal | Kenya MOH Clinical Guidelines / WHO — source to confirm | Kenya MOH STG ⚠ source gap | JAU; UGI | Important | No | Not started |
| Pneumonia (CAP) | **Respiratory** ← cross-domain | Kenya MOH Clinical Guidelines Vol 2 (2025) | Kenya MOH STG | — | — | Yes | Draft |
| Cholera | **Acute Febrile Illness** ← cross-domain | WHO-AFRO Cholera Management Guidelines (2023) | WHO guideline | AWD | High | Yes | Draft |
| Typhoid fever | **Acute Febrile Illness** ← cross-domain | Kenya MOH Clinical Guidelines Vol 2 (2025) | Kenya MOH STG | BD; AWD | High | Yes | Draft |
| Malaria (unspecified) | **Acute Febrile Illness** ← cross-domain | Kenya NMCP Guidelines (2024) | Kenya MOH disease-specific guideline | AWD; UGI | High | Yes | Draft |

### 2.3 Source verification notes

**PUD:** The current card uses ACG 2021 as the primary source. Kenya MOH Clinical Guidelines Vol 2 (2022) likely has a relevant chapter — verify whether a Kenya-level source should take precedence.

**GERD and Functional dyspepsia:** Kenya MOH Clinical Guidelines (2022) referenced in sources.yaml. Verify specific chapter coverage, particularly for dyspepsia, where Kenya guidance may be limited and Rome IV may remain the primary functional reference.

**AGE:** Current card uses WHO Diarrhoeal Disease Fact Sheet (2017). Kenya MOH Clinical Guidelines Vol 2 likely covers diarrhoeal management at primary care level — assess whether Kenya MOH source should be primary.

**Acute dysentery (Shigellosis) ⚠ verify:** Kenya MOH Clinical Guidelines Vol 2 almost certainly has a chapter on dysentery / bloody diarrhoea management. Confirm chapter title and content before card authoring begins. If coverage is limited, WHO Shigellosis guidelines or regional guidance applies.

**Intestinal helminthiasis ⚠ source gap:** Kenya has established national deworming programmes (school-age children, pregnant women). Kenya MOH / KEMRI programme documents likely serve as the primary source. Confirm whether a clinical management chapter (vs. a public health programme document) exists for primary care. WHO's soil-transmitted helminthiasis guidance is the fallback.

**Appendicitis ⚠ verify:** Kenya MOH Clinical Guidelines Vol 2 likely addresses appendicitis at primary care level (recognition + referral criteria). The CDS card scope is limited to recognition and escalation, not surgical management. Confirm chapter coverage before authoring.

**Acute viral hepatitis A ⚠ source gap:** No dedicated standalone Kenya MOH hepatitis A guideline confirmed. Kenya MOH Clinical Guidelines Vol 2 or the Kenya National Viral Hepatitis Control Programme documents are the likely source. WHO hepatitis A guidance is the fallback. Confirm before card authoring.

### 2.4 Inventory governance decisions required before card authoring

| Condition | Decision required |
|-----------|------------------|
| Acute dysentery (Shigellosis) | Confirm Kenya MOH Vol 2 chapter existence and adequacy; if absent, identify WHO/international fallback and explicitly label |
| Intestinal helminthiasis | Confirm whether a primary-care clinical management source exists vs. programme-only documents; define acceptable source |
| Appendicitis | Confirm Kenya MOH Vol 2 chapter exists with recognition/referral criteria adequate for primary care CDS scope |
| Acute viral hepatitis A | Confirm primary source (Kenya MOH vs. WHO); assess whether the card is within primary care scope or recognition-only |

These governance decisions do not block §3 or §4.

---

## 3. Presentation and Differential Map

### 3.1 Architecture

The map is **presentation-first**, not condition-first. Each row answers: *"A patient arrives with this symptom cluster — what conditions must the system consider?"*

Cross-domain participants (Cholera, Typhoid, Malaria) appear in the map without transferring ownership. Their existing validated cards are used as-is.

```
Patient presentation cluster
        ↓
Candidate conditions (GI-owned + cross-domain participants)
        ↓
Flags: safety_priority · source_status · canonical_domain
        ↓
Section 4: which pairs require formal disambiguation
```

### 3.2 Presentation matrix

**Legend:**
- ● GI-owned condition, card exists
- ○ GI-owned condition, card needed
- ◑ Cross-domain participant, card exists
- ⚠ source_gap — source decision required before card authoring

---

**P1 — Upper GI symptoms**
*Epigastric pain, heartburn, bloating, early satiety, nausea, or dyspepsia as the dominant presentation without fever as the primary feature.*

| Candidate | Status | Safety | Notes |
|-----------|--------|--------|-------|
| Functional dyspepsia | ● | Routine | No structural lesion; symptom-based diagnosis; exclude organic causes first |
| GERD | ● | Routine | Heartburn / regurgitation dominant; worse on lying flat or after meals |
| Peptic ulcer disease | ● | Important | Epigastric pain with meals (DU — relieved by food; GU — worsened); H. pylori association |
| Intestinal helminthiasis | ○ ⚠ | Routine | Abdominal discomfort, bloating, nausea; often subclinical; consider in appropriate epidemiological context |
| Acute viral hepatitis A | ○ ⚠ | Important | Anorexia, nausea, and RUQ discomfort precede jaundice; may present at pre-icteric phase |

---

**P2 — Acute watery diarrhoea**
*Three or more loose or watery stools in 24 hours, without blood or mucus, with or without vomiting.*

| Candidate | Status | Safety | Notes |
|-----------|--------|--------|-------|
| Acute gastroenteritis | ● | Routine–Important | Most common cause; viral or bacterial; self-limiting in most cases |
| Cholera | ◑ | High | Rice-water stools, rapid severe dehydration, often afebrile; suspect in outbreak context, post-flood, or known endemic area; AFI-owned |
| Typhoid | ◑ | High | Diarrhoea can occur; fever and step-wise onset distinguish from primary GI AWD; AFI-owned |
| Intestinal helminthiasis | ○ ⚠ | Routine | Heavy infestation can produce diarrhoea; usually associated with other GI features |

*Note: Cholera is the mandatory safety candidate in any acute watery diarrhoea presenting with severe dehydration, regardless of fever. See MSP-03 in AFI pairwise matrix.*

---

**P3 — Bloody / inflammatory diarrhoea (dysentery)**
*Diarrhoea with blood, mucus, or both, with or without fever and tenesmus.*

| Candidate | Status | Safety | Notes |
|-----------|--------|--------|-------|
| Acute dysentery (Shigellosis) | ○ ⚠ | Important | Bloody mucoid diarrhoea, fever, tenesmus; most common bacterial cause of dysentery in Kenya primary care |
| Typhoid (complicated) | ◑ | High | Bloody diarrhoea in typhoid is a complication (intestinal haemorrhage); insidious onset distinguishes from primary dysentery; AFI-owned |
| Malaria | ◑ | High | GI symptoms including diarrhoea common in malaria; blood in stool is not a malaria feature — presence of blood should prompt dysentery evaluation alongside malaria RDT; AFI-owned |
| Acute gastroenteritis | ● | Routine–Important | Some bacterial AGE (EPEC, EAEC) produces mucoid or mildly bloody stool; Shigellosis is the more dangerous dysentery diagnosis to exclude |

---

**P4 — Lower abdominal pain**
*Pain in the lower abdomen, with or without associated GI symptoms, without fever as the presenting feature.*

| Candidate | Status | Safety | Notes |
|-----------|--------|--------|-------|
| Appendicitis | ○ ⚠ | High (safety) | Right iliac fossa pain, migration from periumbilical, low-grade fever, anorexia, rebound tenderness; recognition-and-refer scope |
| Acute gastroenteritis | ● | Routine–Important | Colicky lower abdominal pain is common in AGE; appendicitis must be excluded before labelling as AGE |
| Acute dysentery | ○ ⚠ | Important | Crampy lower abdominal pain with tenesmus; distinguish from appendicitis by stool character and absence of right iliac fossa rebound |
| Intestinal helminthiasis | ○ ⚠ | Routine | Colicky pain in heavy infestation; Ascaris bolus can cause right-sided pain mimicking appendicitis |

---

**P5 — Acute jaundice**
*New-onset visible jaundice with or without systemic symptoms.*

| Candidate | Status | Safety | Notes |
|-----------|--------|--------|-------|
| Acute viral hepatitis A | ○ ⚠ | Important | Jaundice preceded by anorexia, nausea, malaise, low-grade fever; waterborne transmission; more severe in adults |
| Malaria | ◑ | High | Haemolytic jaundice in malaria — severity indicates severe malaria; AFI-owned; RDT is the first-line discriminating test |

*Note: Other causes of jaundice (hepatitis B, gallstones, pancreatic obstruction) are outside primary care primary diagnosis scope in this domain — recognition and referral only.*

### 3.3 Cross-domain participation summary

| Condition | Canonical domain | Participates in GI pathways |
|-----------|-----------------|------------------------------|
| Cholera | Acute Febrile Illness | P2 (AWD — mandatory safety candidate) |
| Typhoid fever | Acute Febrile Illness | P2 (AWD), P3 (BD — complicated typhoid) |
| Malaria (unspecified) | Acute Febrile Illness | P3 (BD — GI overlap), P5 (JAU — haemolytic jaundice) |

### 3.4 Conditions not included and why

| Condition | Reason excluded |
|-----------|----------------|
| Colorectal cancer | Not a primary-care diagnostic domain; recognition and referral only; no primary-care treatment pathway |
| Inflammatory bowel disease (Crohn's, UC) | Low documented prevalence in Kenya primary care; specialist diagnosis requiring colonoscopy; excluded from scope |
| Chronic hepatitis B / C | Chronic management domain; not a primary-care primary-diagnosis CDS use case |
| Pancreatitis | Requires secondary-care investigation (lipase, imaging); recognition-and-refer; outside primary diagnostic scope |
| Irritable bowel syndrome | Diagnosis of exclusion requiring specialist evaluation; not a Kenya primary-care first-encounter diagnosis |
| Amoebic colitis | Clinically overlaps with Shigellosis but less common in Kenya than bacterial dysentery; assess for inclusion after Shigellosis card is validated |

*Inclusion requires: routine primary-care diagnostic relevance + a plausible treatment pathway at primary-care level + a defensible authoritative source.*

---

## 4. Pairwise Disambiguation Matrix

### 4.1 Required pair criteria

A pair enters the disambiguation matrix when:

1. both conditions are epidemiologically plausible in Kenyan primary care; and
2. they share at least two clinically important features.

### 4.2 Mandatory safety pair criteria

A pair is mandatory regardless of epidemiological filter when:

- the presentations materially overlap; **or**
- failure to distinguish them could materially alter urgency, referral, or immediate management.

### 4.3 Pair index

| ID | Pair | Pathways | Priority |
|----|------|----------|----------|
| GI-MSP-01 | Appendicitis vs Acute gastroenteritis | P4 | Mandatory safety |
| GI-MSP-02 | PUD (perforation) vs Acute gastroenteritis | P4, P1 | Mandatory safety |
| GI-RP-01 | PUD vs Functional dyspepsia | P1 | Required |
| GI-RP-02 | PUD vs GERD | P1 | Required |
| GI-RP-03 | GERD vs Functional dyspepsia | P1 | Required |
| GI-RP-04 | Acute dysentery (Shigellosis) vs AGE | P3, P2 | Required |
| GI-RP-05 | Acute dysentery vs Typhoid (complicated) ↔ | P3 | Required |
| GI-RP-06 | Appendicitis vs Acute dysentery | P4, P3 | Required |
| GI-RP-07 | AGE vs Cholera ↔ | P2 | Required — covered by AFI MSP-03; cross-reference only |
| GI-RP-08 | Acute hepatitis A vs Malaria (jaundice) ↔ ⚠ | P5 | Required — pending hepatitis A card |

### 4.4 Mandatory safety pairs

#### GI-MSP-01: Appendicitis vs Acute gastroenteritis

**Pathways:** P4
**Why mandatory:** Both present with abdominal pain, nausea, vomiting, and may produce low-grade fever. Appendicitis is frequently misdiagnosed as gastroenteritis at primary care level, with delayed referral leading to perforation and peritonitis.

**Shared features:** Abdominal pain, nausea, vomiting, anorexia, low-grade fever.

**Discriminating evidence:**
- Pain migration: appendicitis = classically periumbilical pain migrating to right iliac fossa (RIF); AGE = diffuse colicky pain without localisation
- RIF rebound tenderness: appendicitis = present on release of pressure at RIF (Blumberg's sign); AGE = absent
- Anorexia: appendicitis = profound and early; AGE = usually less prominent
- Diarrhoea: AGE = prominent; appendicitis = diarrhoea uncommon (may have loose stools but not the dominant feature)
- Progression: appendicitis = pain worsens over hours without relief; AGE = colicky, waxes and wanes, often partially resolves with stool passage

**Missing information required:** Location and migration of pain; presence of RIF tenderness and rebound; diarrhoea (volume and character); anorexia; duration and trajectory of pain (worsening or intermittent).

**Red flags:** Rebound tenderness; board-like rigidity (perforation); high fever >38.5°C; inability to walk upright; pain that has been worsening continuously for >6 hours.

**Disambiguation questions:**
1. "Where does the pain start — around the belly button — and has it moved to the lower right side?"
2. "Does the pain get worse when you release pressure from the lower right abdomen?"
3. "Has the pain been getting steadily worse since it started, or does it come and go?"
4. "Is there diarrhoea, or just nausea and vomiting without loose stools?"

**Escalation:** Suspected appendicitis = immediate referral to surgical facility. Do not administer analgesics that could mask peritoneal signs before transfer. AGE = supportive management with ORS; reassess at 24–48 hours; immediate referral if peritoneal signs develop.

---

#### GI-MSP-02: PUD perforation (red flag) vs Acute gastroenteritis

**Pathways:** P4, P1
**Why mandatory:** PUD perforation presents with acute abdominal pain that can be confused with severe AGE or appendicitis at primary care level. Missing perforation leads to preventable mortality.

**Shared features:** Sudden severe abdominal pain, nausea, vomiting, anorexia.

**Discriminating evidence:**
- Onset: PUD perforation = sudden, severe, onset within minutes ("knife-like" or "tearing" pain); AGE = colicky, building over hours
- Pain character: perforation = constant, severe, generalised peritoneal pain — patient lies still; AGE = crampy, patient writhing or moving
- Peritonism: perforation = board-like rigidity, guarding, rebound tenderness; AGE = soft abdomen between cramps
- Prior history: known PUD, NSAID use, H. pylori history — increases perforation prior
- Shoulder-tip pain: referred diaphragmatic irritation from free air = perforation

**Missing information required:** Onset speed; pain character (colicky vs constant); abdominal rigidity on examination; prior PUD or NSAID history; shoulder-tip pain.

**Red flags:** Sudden-onset severe constant abdominal pain; board-like rigidity; referred shoulder-tip pain; haemodynamic instability.

**Disambiguation questions:**
1. "Did the pain come on suddenly and severely within minutes, or build up gradually?"
2. "Is the abdomen rigid when examined, or soft?"
3. "Is there a history of peptic ulcer or regular use of ibuprofen or aspirin?"

**Escalation:** Suspected perforation = immediate emergency referral. Do not give oral fluids or food. Insert IV access if possible before transfer.

---

### 4.5 Required pairs

#### GI-RP-01: PUD vs Functional dyspepsia

**Pathways:** P1
**Shared features:** Epigastric pain or discomfort, bloating, nausea, post-meal symptoms. Both are common in Kenya primary care; cannot be reliably distinguished without endoscopy.

**Discriminating evidence:**
- Pain character: PUD = more localised epigastric pain, sometimes with meal timing pattern (DU — hunger pain, relieved by food; GU — worsened by food); functional dyspepsia = more diffuse discomfort, fullness, early satiety
- Night pain: PUD (duodenal) — waking at night with epigastric pain is a discriminating feature; functional dyspepsia — uncommon at night
- Weight loss: alarm feature for PUD or upper GI malignancy; absent in functional dyspepsia
- NSAID or aspirin use: precipitating or worsening factor for PUD specifically
- H. pylori: strongly associated with PUD; less certain association with functional dyspepsia

**Missing information required:** Night-waking pain; meal relationship (relieves or worsens); NSAID or aspirin use; weight loss; prior H. pylori test or treatment; age (>45 with new dyspepsia = alarm feature).

**Red flags:** New dyspepsia in patient ≥45 years; weight loss; haematemesis; melaena; progressive dysphagia; anaemia.

**Disambiguation questions:**
1. "Does the pain wake you from sleep at night?"
2. "Does eating make the pain better, worse, or no difference?"
3. "Any regular use of ibuprofen, aspirin, or similar painkillers?"
4. "Any weight loss, or blood in vomit or black stools?"

**Escalation:** Alarm features in any patient with dyspepsia = urgent referral for endoscopy. New dyspepsia ≥45 years = investigate before empirical treatment. H. pylori test-and-treat is appropriate for non-alarm dyspepsia at primary care level.

---

#### GI-RP-02: PUD vs GERD

**Pathways:** P1
**Shared features:** Epigastric discomfort, nausea, post-meal symptoms, worsened by specific foods.

**Discriminating evidence:**
- Heartburn / regurgitation: GERD = dominant symptom; PUD = less prominent
- Positional relationship: GERD = worse lying flat, bending forward, after large meals; PUD = not position-dependent
- Night pain: PUD (DU) — night-waking hunger pain; GERD — reflux symptoms on lying down
- Response to antacids: both may respond; GERD response is typically more rapid and complete
- Meal timing: DU pain classically relieved by food then returns 2–3 hours later; GERD typically worsens after large meals

**Missing information required:** Heartburn and regurgitation as symptoms; positional worsening (lying flat); night symptoms (hungry pain vs reflux); food triggers; NSAID use.

**Red flags (for both):** Dysphagia, odynophagia, haematemesis, weight loss, new symptoms ≥45 years — all require investigation.

**Disambiguation questions:**
1. "Is there a burning feeling rising from the stomach into the chest or throat?"
2. "Does lying down or bending forward bring on or worsen the discomfort?"
3. "Does the pain wake you at night feeling hungry, or does it come on when lying down?"

---

#### GI-RP-03: GERD vs Functional dyspepsia

**Pathways:** P1
**Shared features:** Upper GI discomfort, post-meal symptoms, nausea, bloating. Overlap is common; patients may have both conditions simultaneously.

**Discriminating evidence:**
- Heartburn: GERD = prominent; functional dyspepsia = may have mild heartburn but not dominant
- Regurgitation: GERD = characteristic; absent in functional dyspepsia
- Postprandial fullness and early satiety: functional dyspepsia cardinal features (Rome IV epigastric pain syndrome or postprandial distress syndrome); less prominent in GERD
- Response to PPI: GERD symptoms respond well to PPI; functional dyspepsia — PPI may help but response is partial

**Missing information required:** Heartburn (retrosternal burning); regurgitation; postprandial fullness and early satiety; whether a PPI trial has been tried and the degree of response.

**Disambiguation questions:**
1. "Is there a burning sensation rising from the stomach into the chest or throat after eating?"
2. "Do you feel full very quickly even after a small meal, or uncomfortably full after a normal meal?"

---

#### GI-RP-04: Acute dysentery (Shigellosis) vs AGE

**Pathways:** P3, P2
**Note:** Shigellosis card is not yet authored ⚠ — evaluation fixtures for this pair cannot be authored until the card exists.

**Shared features:** Acute diarrhoea, vomiting, abdominal cramps, fever, malaise.

**Discriminating evidence:**
- Stool character: dysentery = blood and mucus; AGE = watery, no blood
- Tenesmus: dysentery = prominent (painful, ineffectual straining to defaecate); AGE = absent
- Fever: dysentery = typically higher and more sustained; AGE = often mild or absent
- Stool frequency vs volume: dysentery = frequent, small-volume, mucoid; AGE = less frequent, larger-volume, watery

**Missing information required:** Blood or mucus in stool; tenesmus; fever degree; stool character (watery vs mucoid); volume per episode.

**Red flags:** Bloody diarrhoea in children under 5 or in immunocompromised patients; haemolytic uraemic syndrome features (pallor, oliguria, bruising) — Shiga toxin-producing E. coli (STEC); high fever with systemic toxicity.

**Disambiguation questions:**
1. "Is there blood or mucus visible in the stool?"
2. "Is there a constant urge to pass stool even when nothing comes — painful straining?"
3. "Is the stool profuse and watery, or small amounts with blood and slime?"

**Escalation:** Bloody diarrhoea in young children = assess for HUS. Antibiotics for dysentery (ciprofloxacin or azithromycin) — avoid anti-motility agents in bloody diarrhoea.

---

#### GI-RP-05: Acute dysentery vs Typhoid (complicated) ↔

**Pathways:** P3
**Note:** Shigellosis card not yet authored ⚠. Cross-domain — Typhoid is AFI-owned.

**Shared features:** Fever + diarrhoea, abdominal pain, malaise.

**Discriminating evidence:**
- Onset: dysentery = acute (hours to 1–2 days); typhoid = insidious step-wise onset over 5–7 days
- Blood in stool: bloody diarrhoea in typhoid = a complication (intestinal haemorrhage), not the initial presentation; dysentery = blood and mucus from onset
- Relative bradycardia: typhoid (pulse-temperature dissociation); not dysentery
- Tenesmus: dysentery = prominent; typhoid = not a feature
- Rose spots: typhoid (rare but pathognomonic)

**Missing information required:** Fever duration and pattern; onset timing (acute vs insidious); tenesmus; relative bradycardia on examination; blood in stool from day 1 vs onset later in illness.

**Disambiguation questions:**
1. "How long has the fever been present — did it start suddenly or build up over several days?"
2. "Did the blood in the stool appear from the very start of the illness, or did it come later?"
3. "Is there a constant painful urge to pass stool?"

---

#### GI-RP-06: Appendicitis vs Acute dysentery

**Pathways:** P4, P3
**Note:** Shigellosis card not yet authored ⚠.

**Shared features:** Lower abdominal pain, fever, nausea.

**Discriminating evidence:**
- Pain location: appendicitis = RIF localisation with rebound; dysentery = diffuse, crampy, without localised rebound
- Tenesmus: dysentery = prominent; appendicitis = absent
- Stool character: dysentery = bloody mucoid; appendicitis = may have loose stool but not bloody mucoid
- Diarrhoea prominence: dysentery = dominant; appendicitis = diarrhoea uncommon

**Missing information required:** RIF tenderness and rebound; tenesmus; stool character; diarrhoea prominence.

**Red flags:** RIF rebound tenderness in any patient with lower abdominal pain = must exclude appendicitis before treating as dysentery.

**Disambiguation questions:**
1. "Is the pain worse specifically in the lower right side of the abdomen?"
2. "Is there a constant urge to pass stool with blood or mucus?"
3. "Is the pain getting steadily worse, or does it come and go?"

**Escalation:** Localised RIF rebound tenderness = immediate referral regardless of stool character.

---

#### GI-RP-07: AGE vs Cholera ↔ (cross-reference)

**Pathways:** P2
**Note:** This pair is already fully documented in the AFI domain contract as MSP-03. Cross-reference only — do not duplicate. GI presentation map must flag Cholera as a mandatory safety candidate in P2 (acute watery diarrhoea with severe dehydration) and direct to AFI MSP-03 for full pairwise content.

---

#### GI-RP-08: Acute viral hepatitis A vs Malaria (jaundice) ↔

**Pathways:** P5
**Note:** Hepatitis A card not yet authored ⚠. Cross-domain — Malaria is AFI-owned. Evaluation fixtures cannot be authored until Hepatitis A card exists.

**Shared features:** Jaundice, fever (early), malaise, nausea, anorexia.

**Discriminating evidence:**
- Malaria RDT positive: confirms malaria as the cause of jaundice; haemolytic in nature
- Jaundice type: malaria = haemolytic (indirect hyperbilirubinaemia); hepatitis A = hepatocellular (raised transaminases, direct bilirubinaemia, dark urine, pale stools)
- Dark urine / pale stools: hepatitis A = characteristic (biliary excretion); malaria jaundice = urine may be dark from haemoglobin but stools normal colour
- Pre-icteric symptoms: hepatitis A = anorexia, nausea, right upper quadrant discomfort for 1–2 weeks before jaundice appears; malaria = fever and systemic illness come first
- Waterborne exposure: hepatitis A = faecal-oral, contaminated water or food; malaria = mosquito bite

**Missing information required:** RDT result; dark urine and pale stools; pre-icteric symptom timeline; mosquito exposure; waterborne exposure history; transaminases where available.

**Disambiguation questions:**
1. "What did the malaria RDT show?"
2. "Is the urine dark and are the stools pale-coloured?"
3. "Did the nausea and loss of appetite start before the yellowing, or did the yellowing come first?"

**Escalation:** Malaria with jaundice = severe malaria; immediate treatment and referral. Hepatitis A = supportive care; referral for clinical deterioration (fulminant hepatitis), coagulopathy, or encephalopathy.
