// 003_comorbidity_schema.cypher — Comorbidity relationship schema
// Locked 2026-09-14. All statements are idempotent (IF NOT EXISTS). Safe to re-run.
//
// Node/relationship contract:
//   ASSOCIATED_WITH  (:Condition)     → (:Condition)       ICD-coded comorbid condition
//   COMPLICATED_BY   (:Condition)     → (:Condition)       ICD-coded complication
//   REQUIRES_CONTEXT (:Condition)     → (:ClinicalContext) clinical variable (not a diagnosis)
//
// :ClinicalContext properties: name (slug), label, prompt, icd_modifier (optional)
// ASSOCIATED_WITH properties:  effect_type, demographic_gate[], icd_note
// COMPLICATED_BY properties:   mechanism (direct|indirect), urgency (immediate|subacute|chronic)
// REQUIRES_CONTEXT properties: reason, demographic_gate[], priority (mandatory|important)
//
// See: docs/domain_contracts/acute_febrile_illness.md + STATUS.md Decisions Log

// ClinicalContext: unique constraint on name slug
CREATE CONSTRAINT clinical_context_name IF NOT EXISTS
  FOR (c:ClinicalContext) REQUIRE c.name IS UNIQUE;

// ClinicalContext: index on human-readable label
CREATE INDEX clinical_context_label IF NOT EXISTS
  FOR (c:ClinicalContext) ON (c.label);

// ASSOCIATED_WITH: index on effect_type for traversal queries
CREATE INDEX assoc_with_effect_type IF NOT EXISTS
  FOR ()-[r:ASSOCIATED_WITH]-()
  ON (r.effect_type);

// ASSOCIATED_WITH: index on demographic_gate for filtered queries
CREATE INDEX assoc_with_demographic IF NOT EXISTS
  FOR ()-[r:ASSOCIATED_WITH]-()
  ON (r.demographic_gate);

// COMPLICATED_BY: index on urgency for escalation queries
CREATE INDEX complicated_by_urgency IF NOT EXISTS
  FOR ()-[r:COMPLICATED_BY]-()
  ON (r.urgency);

// COMPLICATED_BY: index on mechanism
CREATE INDEX complicated_by_mechanism IF NOT EXISTS
  FOR ()-[r:COMPLICATED_BY]-()
  ON (r.mechanism);

// REQUIRES_CONTEXT: index on priority for mandatory-first ordering
CREATE INDEX req_context_priority IF NOT EXISTS
  FOR ()-[r:REQUIRES_CONTEXT]-()
  ON (r.priority);

// REQUIRES_CONTEXT: index on demographic_gate for filtered queries
CREATE INDEX req_context_demographic IF NOT EXISTS
  FOR ()-[r:REQUIRES_CONTEXT]-()
  ON (r.demographic_gate);
