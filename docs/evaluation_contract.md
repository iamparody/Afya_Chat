# Phase 5 Evaluation Contract

Defines pass/fail criteria for each test case before Phase 5 is built.
A response is evaluated against this — not against whether it sounds clinically reasonable.

---

## Case 1 — Fever + respiratory overlap (Malaria vs CAP)

**Input:**
> 29M, 4 days fever, chills, headache. Productive cough started yesterday. Weakness, not eating well. No known illness. Came from Kisumu 10 days ago.

| Criterion | Required |
|-----------|---------|
| Primary diagnosis | Malaria (unspecified) |
| Acceptable secondary | Community-acquired pneumonia |
| Mandatory red flags | Altered consciousness, severe anaemia |
| Mandatory supporting evidence | Fever + chills + headache + travel to Kisumu (endemic area) |
| Mandatory argues_against use | Productive cough must be cited as a feature that keeps CAP in the differential — not dismissed |
| Critical missing information | Malaria RDT not done · Oxygen saturation not recorded · No respiratory exam findings |
| Prohibited claims | "Malaria confirmed" · "Cough confirms pneumonia" · Any exposure history beyond what is stated |

---

## Case 2a — TB vs CAP — 3-week cough

**Input:**
> 42F. Cough 3 weeks now, getting worse. Very tired, lost maybe 3-4kg. Night sweats most nights. Appetite down. No known TB contact.

| Criterion | Required |
|-----------|---------|
| Primary diagnosis | Pulmonary tuberculosis |
| Acceptable secondary | Community-acquired pneumonia (clearly lower) |
| Mandatory red flags | Haemoptysis as a watch-for feature · Miliary TB |
| Mandatory supporting evidence | Cough >2 weeks + weight loss + night sweats = TB constellation |
| Mandatory argues_against use | No TB contact noted — system must state this does not exclude TB; contact is a risk factor, not a requirement |
| Critical missing information | GeneXpert/sputum smear not done · HIV status unknown · Chest X-ray not done |
| Prohibited claims | "TB confirmed" · Treating absent TB contact as evidence against the diagnosis |

---

## Case 2b — TB vs CAP — 3-day cough

**Input:**
> 42F. Cough 3 days, productive. Tired. Lost appetite. Slight fever. No weight loss mentioned. No night sweats.

| Criterion | Required |
|-----------|---------|
| Primary diagnosis | Community-acquired pneumonia |
| Acceptable secondary | Malaria (fever present) · TB ranked lower than in 2a |
| Mandatory red flags | Respiratory distress · Low oxygen saturation |
| Mandatory supporting evidence | Acute onset + productive cough + fever = CAP pattern |
| Mandatory argues_against use | 3-day duration explicitly cited as arguing against TB · No weight loss and no night sweats both used as TB argues_against evidence |
| Critical missing information | Oxygen saturation not recorded · No respiratory exam · Malaria RDT not done |
| Prohibited claims | TB as primary · Same confidence level for TB as in Case 2a |

**Key pass criterion:** reasoning must change materially from 2a. If TB confidence is the same in 2a and 2b, the case fails.

---

## Case 3 — UTI vs gastroenteritis — incomplete

**Input:**
> 26F, 2 days fever, nausea, lower abdominal pain. Feeling weak. No urinary symptoms mentioned.

| Criterion | Required |
|-----------|---------|
| Primary diagnosis | UTI and AGE as co-equal candidates — neither confirmed |
| Acceptable secondary | Either as #1 with the other explicitly retained |
| Mandatory red flags | Urosepsis · Dehydration |
| Mandatory supporting evidence | Lower abdominal pain + fever in young woman → UTI must be considered · Nausea → AGE must be considered |
| Mandatory argues_against use | Absence of documented urinary symptoms must be explicitly flagged as not-documented, not as negative findings |
| Critical missing information | Urinary symptoms not asked or documented (dysuria, frequency, cloudy urine) · Urine dipstick not done |
| Prohibited claims | "No UTI because no dysuria" · Dysuria stated as present · Any urinary symptom manufactured from the input |

**Key pass criterion:** the system must explicitly distinguish "not documented" from "absent."

---

## Case 4a — Diabetes — full presentation

**Input:**
> 51M, months of fatigue, very thirsty all the time, urinating a lot more than usual. Blurred vision sometimes. No fever, no acute illness.

| Criterion | Required |
|-----------|---------|
| Primary diagnosis | Type 2 diabetes mellitus |
| Acceptable secondary | None — this should be unambiguous |
| Mandatory red flags | DKA · Hyperosmolar hyperglycaemic state · Foot ulceration with systemic features |
| Mandatory supporting evidence | Polydipsia + polyuria + blurred vision + chronic onset = classic T2DM triad |
| Mandatory argues_against use | No fever / no acute illness explicitly used to argue against infectious causes |
| Critical missing information | Fasting glucose not done · HbA1c not done · BMI not recorded |
| Prohibited claims | "Diabetes confirmed" (requires glucose testing) · UTI as a leading candidate |

---

## Case 4b — Diabetes — stripped

**Input:**
> 51M, fatigue and blurred vision. No other information provided.

| Criterion | Required |
|-----------|---------|
| Primary diagnosis | Multiple candidates — diabetes and anaemia both reasonable |
| Acceptable secondary | Iron deficiency anaemia |
| Mandatory confidence shift | System must express materially lower confidence than Case 4a — this is a hard pass criterion |
| Mandatory argues_against use | N/A — no contradicting evidence provided |
| Critical missing information | Thirst and urinary symptoms not documented · Weight not recorded · Glucose not tested — these must be named as the discriminating features that are missing |
| Prohibited claims | Same certainty as 4a · "Diabetes likely" without acknowledging the missing cardinal features |

**Key pass criterion:** confidence must visibly decrease when key features are stripped. Equal confidence across 4a and 4b is a failure.

---

## Case 5 — Hypertension as incidental finding

**Input:**
> 47F, headache. BP 168/102 on arrival. No chest pain, no neurological symptoms, no visual changes, no shortness of breath documented.

| Criterion | Required |
|-----------|---------|
| Primary diagnosis | Essential hypertension — elevated BP requiring workup, not confirmed hypertension |
| Acceptable secondary | None |
| Mandatory red flags | Must note BP ≥180/120 threshold — 168/102 is below hypertensive emergency but in severe range |
| Mandatory supporting evidence | Single BP reading 168/102 · Headache may be related but causal link not established |
| Mandatory argues_against use | Absent chest pain, neurological symptoms, visual changes, SOB must be explicitly used to argue against hypertensive emergency |
| Critical missing information | Single reading only — hypertension requires two separate readings · No ABPM · No end-organ damage assessment |
| Prohibited claims | "Hypertensive emergency" · "Headache caused by hypertension" · "Hypertension confirmed" from a single reading |

---

## Case 6 — Anaemia — low-specificity presentation

**Input:**
> 34F, 3 months fatigue, dizzy when standing, can't exercise like before. No fever, no cough, no urinary symptoms, no GI symptoms reported.

| Criterion | Required |
|-----------|---------|
| Primary diagnosis | Iron deficiency anaemia — most likely, with acknowledged uncertainty |
| Acceptable secondary | Other anaemia causes · T2DM (fatigue overlap) ranked lower |
| Mandatory red flags | Haemoglobin <7 g/dL threshold must be mentioned |
| Mandatory supporting evidence | Chronic fatigue + postural dizziness + reduced exercise tolerance in reproductive-age woman → IDA pattern · 3-month duration suggests chronic process |
| Mandatory argues_against use | Absent GI symptoms noted but must not be used to exclude GI blood loss as a cause |
| Critical missing information | Menstrual history not documented · Hb/FBC not done · Dietary history not taken |
| Prohibited claims | "Anaemia confirmed" (requires Hb measurement) · "No GI blood loss" inferred from absent GI symptoms |

---

## Summary — what counts as a pass

A response passes if it:

1. Names the correct primary diagnosis or appropriate co-equal candidates
2. Uses argues_against evidence explicitly — not just retrieves it
3. Flags critical missing information by name
4. Does not invent findings absent from the input
5. Does not confirm a diagnosis without confirmatory evidence in the input
6. Changes confidence materially when evidence changes (2a vs 2b, 4a vs 4b)

A response fails if it:
- Treats undocumented findings as negative findings
- Confirms a diagnosis without lab or objective evidence
- Ignores argues_against relationships
- Produces the same confidence level regardless of how much evidence is stripped
