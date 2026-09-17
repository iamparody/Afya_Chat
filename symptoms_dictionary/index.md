# Diagnostic RAG — Conditions Index

Machine-friendly index. One row per condition. Fields: condition, ICD-11 code, ICD-10 code, category, source file.

> ICD-11 codes are verified via `scripts/verify_icd.py` (WHO ICD-11 API). Do not edit codes manually — re-run the script if a code needs updating.

| Condition | ICD-11 | ICD-10 | Category | File |
|---|---|---|---|---|
| Type 2 Diabetes Mellitus | 5A11 | E11 | Endocrine | corpus/type_2_diabetes/condition.yaml |
| Essential Hypertension | BA00.Z | I10 | Cardiovascular | corpus/hypertension/condition.yaml |
| Obesity | 5B81.Z | E66 | Endocrine | corpus/obesity/condition.yaml |
| Malaria (unspecified) | 1F4Z | B54 | Infectious | corpus/malaria/condition.yaml |
| Pulmonary Tuberculosis | 1B10.0 | A15 | Infectious | corpus/pulmonary_tb/condition.yaml |
| Community-Acquired Pneumonia | CA40.Z | J18 | Respiratory | corpus/pneumonia/condition.yaml |
| Urinary Tract Infection | GC08.Z | N39.0 | Urological | corpus/uti/condition.yaml |
| Iron Deficiency Anaemia | 3A00.Z | D50 | Haematological | corpus/anaemia/condition.yaml |
| Peptic Ulcer Disease | DA61 | K27 | Gastroenterological | corpus/peptic_ulcer_disease/condition.yaml |
| Gastro-oesophageal Reflux Disease | DA22.Z | K21 | Gastroenterological | corpus/gerd/condition.yaml |
| Acute Gastroenteritis (Infectious) | 1A40.Z | A09 | Gastroenterological | corpus/acute_gastroenteritis/condition.yaml |
| Typhoid Fever | 1A07.Z | A01.0 | Infectious | corpus/typhoid_fever/condition.yaml |
| Functional Dyspepsia | DD90.3 | K30 | Gastroenterological | corpus/functional_dyspepsia/condition.yaml |
| Asthma | CA23 | J45 | Respiratory | corpus/asthma/condition.yaml |
| Dengue Fever | 1D2Z | A90 | Infectious | corpus/dengue_fever/condition.yaml |
| Cholera | 1A00 | A00 | Infectious | corpus/cholera/condition.yaml |
| Shigellosis (acute dysentery) | 1A02 | A03.9 | Infectious | corpus/shigellosis/condition.yaml |
| Intestinal Helminthiasis | 1F90.2 | B82.0 | Infectious | corpus/intestinal_helminthiasis/condition.yaml |
| Appendicitis | DB10.0 | K37 | Gastroenterological | corpus/appendicitis/condition.yaml |
| Acute Viral Hepatitis A | 1E50.0 | B15.9 | Infectious | corpus/acute_viral_hepatitis_a/condition.yaml |
| Bacterial Meningitis | 1D01.0Z | G00.9 | Infectious / Neurological | corpus/bacterial_meningitis/condition.yaml |
| Chikungunya | 1D40 | A92.0 | Infectious | corpus/chikungunya/condition.yaml |
| Brucellosis | 1B95 | A23.9 | Infectious | corpus/brucellosis/condition.yaml |
| Leptospirosis | 1B91 | A27.9 | Infectious | corpus/leptospirosis/condition.yaml |
