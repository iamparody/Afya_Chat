// CDS — Initial Neo4j Schema
// Idempotent: safe to re-run at any time.
// Run this before loading any data.

// ── Constraints (uniqueness + implicit index) ────────────────────────────────

CREATE CONSTRAINT condition_name IF NOT EXISTS
  FOR (c:Condition) REQUIRE c.name IS UNIQUE;

CREATE CONSTRAINT symptom_name IF NOT EXISTS
  FOR (s:Symptom) REQUIRE s.name IS UNIQUE;

CREATE CONSTRAINT risk_factor_name IF NOT EXISTS
  FOR (r:RiskFactor) REQUIRE r.name IS UNIQUE;

CREATE CONSTRAINT red_flag_name IF NOT EXISTS
  FOR (f:RedFlag) REQUIRE f.name IS UNIQUE;

CREATE CONSTRAINT diagnostic_test_name IF NOT EXISTS
  FOR (t:DiagnosticTest) REQUIRE t.name IS UNIQUE;

// ── Indexes (lookup performance) ─────────────────────────────────────────────

CREATE INDEX condition_icd11 IF NOT EXISTS
  FOR (c:Condition) ON (c.icd11);

CREATE INDEX condition_category IF NOT EXISTS
  FOR (c:Condition) ON (c.category);

CREATE INDEX condition_review_status IF NOT EXISTS
  FOR (c:Condition) ON (c.review_status);
