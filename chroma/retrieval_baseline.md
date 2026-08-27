# Retrieval Baseline — Phase 5 Pre-work

Graph = Neo4j Cypher symptom match | Vector = Chroma semantic search

---

## Case 1 — Fever + respiratory overlap (Malaria vs CAP)

> **Input:** 29M, 4 days fever, chills, headache. Productive cough started yesterday. Weakness, not eating well. No known illness. Came from Kisumu 10 days ago.

**Expected:** Malaria (unspecified)

| | Graph top 3 | Vector top 3 |
|---|---|---|
| Results | Malaria (unspecified) (5 match) · Community-acquired pneumonia (3 match) · Urinary tract infection (1 match) | Malaria (unspecified) / differentials [0.916] · Malaria (unspecified) / typical_presentation [0.919] · Malaria (unspecified) / associated_symptoms [0.941] |
| Correct retrieved? | Yes | Yes |

**Contradicting evidence note:** Productive cough argues toward CAP — system should surface both

---

## Case 2a — TB vs CAP — 3-week cough

> **Input:** 42F. Cough 3 weeks now, getting worse. Very tired, lost maybe 3-4kg. Night sweats most nights. Appetite down. No known TB contact.

**Expected:** Pulmonary tuberculosis

| | Graph top 3 | Vector top 3 |
|---|---|---|
| Results | Community-acquired pneumonia (3 match) · Pulmonary tuberculosis (3 match) · Type 2 diabetes mellitus (1 match) | Pulmonary tuberculosis / typical_presentation [0.63] · Pulmonary tuberculosis / cardinal_symptoms [0.69] · Pulmonary tuberculosis / differentials [0.751] |
| Correct retrieved? | Yes | Yes |

**Contradicting evidence note:** No TB contact argues slightly against — should still surface TB

---

## Case 2b — TB vs CAP — 3-day cough (same patient, one variable changed)

> **Input:** 42F. Cough 3 days, productive. Tired. Lost appetite. Slight fever. No weight loss mentioned. No night sweats.

**Expected:** Community-acquired pneumonia

| | Graph top 3 | Vector top 3 |
|---|---|---|
| Results | Community-acquired pneumonia (4 match) · Malaria (unspecified) (2 match) · Pulmonary tuberculosis (1 match) | Pulmonary tuberculosis / cardinal_symptoms [0.732] · Pulmonary tuberculosis / typical_presentation [0.766] · Pulmonary tuberculosis / differentials [0.848] |
| Correct retrieved? | Yes | No |

**Contradicting evidence note:** Short duration argues against TB — CAP should rank higher than 2a

---

## Case 3 — UTI vs gastroenteritis — incomplete (no urinary symptoms documented)

> **Input:** 26F, 2 days fever, nausea, lower abdominal pain. Feeling weak. No urinary symptoms mentioned.

**Expected:** Urinary tract infection

| | Graph top 3 | Vector top 3 |
|---|---|---|
| Results | Malaria (unspecified) (3 match) · Urinary tract infection (3 match) · Acute gastroenteritis (infectious) (2 match) | Acute gastroenteritis (infectious) / cardinal_symptoms [0.812] · Urinary tract infection / associated_symptoms [0.815] · Urinary tract infection / cardinal_symptoms [0.842] |
| Correct retrieved? | Yes | Yes |

**Contradicting evidence note:** Absent urinary symptoms — system must not invent dysuria or frequency

---

## Case 4a — Diabetes — full presentation

> **Input:** 51M, months of fatigue, very thirsty all the time, urinating a lot more than usual. Blurred vision sometimes. No fever, no acute illness.

**Expected:** Type 2 diabetes mellitus

| | Graph top 3 | Vector top 3 |
|---|---|---|
| Results | Type 2 diabetes mellitus (4 match) · Iron deficiency anaemia (1 match) · Pulmonary tuberculosis (1 match) | Urinary tract infection / associated_symptoms [0.875] · Urinary tract infection / typical_presentation [0.875] · Urinary tract infection / cardinal_symptoms [0.887] |
| Correct retrieved? | Yes | No |

**Contradicting evidence note:** No fever/acute illness argues against infectious causes

---

## Case 4b — Diabetes — stripped (no thirst/urination mentioned)

> **Input:** 51M, fatigue and blurred vision. No other information provided.

**Expected:** Type 2 diabetes mellitus

| | Graph top 3 | Vector top 3 |
|---|---|---|
| Results | Type 2 diabetes mellitus (2 match) · Iron deficiency anaemia (1 match) · Pulmonary tuberculosis (1 match) | Iron deficiency anaemia / cardinal_symptoms [0.953] · Type 2 diabetes mellitus / associated_symptoms [1.018] · Iron deficiency anaemia / typical_presentation [1.051] |
| Correct retrieved? | Yes | Yes |

**Contradicting evidence note:** System should be less confident — missing key features

---

## Case 5 — Hypertension as incidental finding

> **Input:** 47F, headache. BP 168/102 on arrival. No chest pain, no neurological symptoms, no visual changes, no shortness of breath documented.

**Expected:** Essential hypertension

| | Graph top 3 | Vector top 3 |
|---|---|---|
| Results | Malaria (unspecified) (1 match) · Essential hypertension (1 match) | Essential hypertension / associated_symptoms [0.777] · Essential hypertension / red_flags [0.866] · Essential hypertension / typical_presentation [0.943] |
| Correct retrieved? | Yes | Yes |

**Contradicting evidence note:** No end-organ symptoms — system should not confirm hypertensive emergency

---

## Case 6 — Anaemia — low-specificity presentation

> **Input:** 34F, 3 months fatigue, dizzy when standing, can't exercise like before. No fever, no cough, no urinary symptoms, no GI symptoms reported.

**Expected:** Iron deficiency anaemia

| | Graph top 3 | Vector top 3 |
|---|---|---|
| Results | Iron deficiency anaemia (2 match) · Type 2 diabetes mellitus (1 match) · Community-acquired pneumonia (1 match) | Urinary tract infection / typical_presentation [0.953] · Pulmonary tuberculosis / cardinal_symptoms [0.961] · Type 2 diabetes mellitus / typical_presentation [0.965] |
| Correct retrieved? | Yes | No |

**Contradicting evidence note:** No GI symptoms — should note absence doesn't exclude all causes

---
