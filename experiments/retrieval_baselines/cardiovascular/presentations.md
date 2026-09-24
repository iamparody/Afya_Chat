# Cardiovascular Domain — Phase C Evaluation Fixtures

**Status: FROZEN after Phase C baseline is recorded. Do not modify presentations before Phase E.**

Corpus version at fixture authoring: 28 conditions, 252 chunks, schema_version 2.2/2.3.
Retrieval config: Dense (Cohere embed-english-v3.0), BM25, RRF (K=60), TOP_N=9.

---

## Pair 1: Essential Hypertension ↔ Hypertensive Crisis

Three presentations covering clinically distinct variants of the retrieval boundary.

### C1a — Incidental elevated BP, no acute symptoms (correct: Essential Hypertension)

```
47F, headache. BP 168/102 on arrival. No chest pain, no neurological symptoms,
no visual changes, no shortness of breath documented.
```

*Source: evaluate.py Case 5 — preserved verbatim as the founding fixture for this pair.*

### C1b — Persistent hypertension, stable, no end-organ features (correct: Essential Hypertension)

```
54M, known hypertensive on amlodipine for 3 years. Routine review. BP 158/96 today
and 162/98 at last visit. No headache, no visual disturbance, no chest pain, no
shortness of breath. No focal neurological symptoms. Feels well. Non-smoker.
BMI 29. Fasting glucose normal last year.
```

### C1c — Severe acute BP elevation with end-organ involvement (correct: Hypertensive Crisis)

```
61M, presents with sudden severe occipital headache for 2 hours. BP 210/128.
Blurred vision. One episode of vomiting. Agitated and confused on examination.
Known hypertensive, stopped medication 2 weeks ago. No fever. Fundoscopy: bilateral
disc swelling.
```

---

## Pair 2: Pulmonary Embolism ↔ Deep Vein Thrombosis

Three presentations covering clinically distinct variants of the retrieval boundary.

### C2a — Unilateral limb presentation (correct: DVT)

```
33F, right leg swollen and painful for 3 days. Right calf noticeably larger than
left — diameter difference approximately 2.5 cm measured from tibial tuberosity.
Warmth and erythema over right calf. Cannot walk without limping. No fever. No
cough, no chest pain, no breathlessness. Recently returned from a 10-hour flight.
```

### C2b — Acute pulmonary presentation (correct: PE)

```
41M, sudden breathlessness starting 1 hour ago. Sharp right-sided chest pain,
worse on inspiration. Coughed up small amount of blood-stained sputum. Tachycardia
on examination — pulse 112 bpm. Respiratory rate 22 per minute. Oxygen saturation
93% on air. No fever. No sputum production. Admitted to hospital 2 weeks ago for
elective knee surgery.
```

### C2c — Shared thromboembolic risk language, acute pulmonary (correct: PE)

```
38F, 6 weeks post-partum, breastfeeding. Increasing breathlessness over 4 hours.
Mild left-sided pleuritic chest pain. No productive cough. No fever. Pulse 108 bpm,
respiratory rate 20 per minute. Oxygen saturation 94%. Left calf mildly tender on
palpation — no visible swelling. BMI 32. No prior history of clots.
```

*C2c tests shared risk-factor vocabulary (post-partum, obesity, immobility) without
naming the diagnosis, and without obvious limb swelling to trivially resolve DVT vs PE.*
