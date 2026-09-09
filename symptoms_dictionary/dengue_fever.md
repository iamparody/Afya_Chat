---
condition: Dengue fever
icd11: 1D2Z
icd10: A90
category: infectious
corpus_version: "1.0"
schema_version: "2.1"
review_status: draft
reviewed_by: ""
last_reviewed: ""
sources:
  - organization: "WHO"
    title: "Dengue: Guidelines for Diagnosis, Treatment, Prevention and Control"
    year: "2009"
  - organization: "WHO"
    title: "Comprehensive Guidelines for Prevention and Control of Dengue and Dengue Haemorrhagic Fever"
    year: "2011"
  - organization: "Kenya MoH / KEMRI"
    title: "Integrated Vector Management Strategy Kenya"
    year: "2023"
endemic_regions:
  - coast
environmental_signals:
  - signal: post_long_rains
    pathways:
      - vector_borne
    effect_type: transmission_opportunity
    effect_direction: up
    lag_weeks:
      min: 4
      max: 8
    strength: moderate
    confidence: moderate
    causal_distance: direct
    evidence_type: regional_epidemiological_evidence
    regions:
      - coast
    seasonal_basis: typical_long_rains
    applicability:
      requires_exposure: []
      amplifiers:
        - mosquito_exposure_high
graph:
  cardinal_symptoms: [fever, severe myalgia, headache]
  associated_symptoms: [retro-orbital headache, arthralgia, nausea, vomiting, anorexia, maculopapular rash, thrombocytopenia, leukopenia]
  risk_factors: [endemic area residence, travel to endemic area, no acquired immunity]
  differentials: [malaria, typhoid fever, influenza, chikungunya, leptospirosis]
  argues_against: [no endemic area exposure, gradual insidious onset, normal platelet count]
  red_flags: [plasma leakage, haemodynamic instability, severe bleeding, altered consciousness]
  confirms: [positive dengue NS1 antigen, positive dengue IgM serology, positive tourniquet test]
---

# Dengue Fever

Dengue fever is a mosquito-borne viral illness caused by one of four antigenically distinct serotypes (DENV-1 to DENV-4) of the dengue virus, transmitted principally by Aedes aegypti and, to a lesser extent, Aedes albopictus. In Kenya, dengue is endemic along the coast (Mombasa, Kilifi, Lamu) and has been reported in urban informal settlements where Aedes mosquitoes breed in peri-domestic water containers.

**Cardinal symptoms:** The cardinal features are acute high-grade fever — typically 39–40°C — severe myalgia described as "break-bone fever" due to its intensity, and headache. Onset is characteristically abrupt over one to two days, which distinguishes dengue from the insidious febrile illnesses in the differential diagnosis.

**Associated symptoms and signs:** Retro-orbital headache — pain behind the eyes, often worsened by eye movement — is a diagnostically useful feature when present. Marked arthralgia accompanies the myalgia. Nausea, vomiting, and anorexia are common in the early febrile phase. A maculopapular rash typically appears on days 3–5, described classically as "islands of white in a sea of red." Thrombocytopenia (platelet count below 100,000/μL) and leukopenia (white cell count below 5,000/μL) develop characteristically by day 3–5 and provide important supporting laboratory evidence. Minor mucosal bleeding — gum bleeding, epistaxis — may occur and reflects platelet dysfunction.

**Diagnostic features:** Positive dengue NS1 antigen test is the preferred early diagnostic test, detectable from day 1 and reliable for days 1–5 of illness; it is increasingly available at district hospital level in Kenya. Positive dengue IgM serology becomes detectable from approximately day 5 and is the standard serological confirmation, persisting for months. A positive tourniquet test — defined as ≥20 petechiae per square centimetre after inflating the blood pressure cuff to the mean arterial pressure for five minutes — demonstrates capillary fragility and is a useful bedside screening tool in resource-limited settings. Dengue PCR is the gold standard for acute-phase confirmation but is rarely available at primary care level in Kenya.

**Predisposing factors:** Residence in or recent travel to a dengue-endemic area is the necessary condition for exposure. In Kenya, coastal regions (Mombasa, Kilifi, Malindi, Lamu) and urban informal settlements in Nairobi — where Aedes mosquitoes breed prolifically in discarded tyres, uncovered water storage containers, and flower pots — are the principal risk environments. Non-immune individuals are at risk of dengue fever. Secondary infection with a different dengue serotype carries substantially elevated risk of severe dengue through antibody-dependent enhancement; a prior dengue history is therefore a risk factor for severe disease rather than protection.

**Typical presentation:** A patient presenting from coastal Kenya — Mombasa, Kilifi, Malindi — or from a Nairobi informal settlement with acute-onset high fever, severe headache with retro-orbital pain, marked myalgia and arthralgia, and nausea in the first few days of illness represents the typical dengue presentation. A maculopapular rash appearing around days 3–5 adds diagnostic certainty. The critical period is defervescence (days 3–7 of illness): some patients undergo spontaneous recovery, while those developing dengue haemorrhagic fever manifest plasma leakage, haemoconcentration, and risk of shock. Warning signs of severe dengue — abdominal pain, persistent vomiting, mucosal bleeding, rapid clinical deterioration around defervescence — must be actively monitored regardless of initial clinical stability.

**Important differential diagnoses:** Malaria produces fever, headache, and myalgia in the same endemic geography as coastal dengue; rigors (shaking chills), splenomegaly, and a positive malaria rapid diagnostic test distinguish it; co-infection is possible and has been documented in coastal Kenya, warranting testing for both when presentations are atypical. Typhoid fever has insidious onset over 7–14 days with relative bradycardia, abdominal pain, constipation or diarrhoea, and rose spots; severe myalgia and thrombocytopenia are less pronounced than in dengue. Influenza produces fever, headache, and myalgia with prominent upper respiratory catarrhal symptoms; retro-orbital pain and thrombocytopenia are absent. Chikungunya shares the same Aedes vector and the same coastal and urban ecology; clinically, severe and prolonged arthralgia is more dominant in chikungunya, fever is shorter in duration, and thrombocytopenia is milder or absent. Leptospirosis occurs in flooded and peri-fluvial environments; conjunctival suffusion, jaundice, and renal failure in Weil disease distinguish severe leptospirosis from dengue.

**Features that argue against this diagnosis:** No history of exposure to a dengue-endemic area — specifically no residence in or travel to coastal Kenya or urban informal settlements within the relevant exposure period — makes locally acquired dengue very unlikely. A gradual and insidious onset with symptoms developing over more than a week argues against dengue, which is characteristically acute with abrupt onset over one to two days. A normal platelet count maintained throughout the febrile illness, particularly from day 3 onward, substantially reduces dengue probability; thrombocytopenia is a near-universal finding in dengue by the mid-febrile phase.

**Red flags (severe dengue — dengue haemorrhagic fever):** Plasma leakage — evidenced by a rising haematocrit (≥20% increase from baseline), pleural effusion, or ascites — marks the transition from dengue fever to dengue haemorrhagic fever and requires immediate fluid management. Haemodynamic instability with hypotension, tachycardia, and cold or clammy extremities indicates dengue shock syndrome, a clinical emergency. Severe bleeding — haematemesis, melaena, heavy menstrual loss, or evidence of intracranial haemorrhage — is an absolute red flag requiring urgent referral. Altered consciousness may reflect dengue encephalopathy or intracranial haemorrhage. Rapid clinical deterioration in a patient who appeared stable around the time of defervescence (days 3–7) warrants immediate reassessment even when initial severity appeared mild.

**Diagnostic context:** Dengue diagnosis in Kenya primary care is primarily clinical during the febrile phase, supported by NS1 antigen testing where available. IgM serology is the standard confirmation from day 5. Full blood count demonstrating thrombocytopenia with leukopenia provides strong supporting evidence; serial platelet counts are essential for monitoring disease course and anticipating haemorrhagic complications. The tourniquet test provides useful bedside evidence of capillary fragility before formal laboratory testing is available. In coastal Kenya, dengue should be considered in all febrile patients who do not respond to antimalarial treatment or whose malaria RDT is negative. The defervescence period must be identified and the patient monitored closely for warning signs, since clinical deterioration typically occurs at this point rather than during the early febrile phase.
