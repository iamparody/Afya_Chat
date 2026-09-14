// CDS — Pairwise Disambiguation Schema
// Adds DIFFERENTIATED_FROM relationship indexes for pairwise pair queries.
// Idempotent: safe to re-run at any time.
// Run after 001_initial_schema.cypher.

// ── Relationship property indexes ────────────────────────────────────────────
// Enables fast lookup by pair_id, priority, and governance status.

CREATE INDEX diff_from_pair_id IF NOT EXISTS
  FOR ()-[r:DIFFERENTIATED_FROM]-()
  ON (r.pair_id);

CREATE INDEX diff_from_priority IF NOT EXISTS
  FOR ()-[r:DIFFERENTIATED_FROM]-()
  ON (r.priority);

CREATE INDEX diff_from_governance IF NOT EXISTS
  FOR ()-[r:DIFFERENTIATED_FROM]-()
  ON (r.governance_pending);
