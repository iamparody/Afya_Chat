"""
Neo4j graph loader for CDS.

Reads graph_entities.jsonl and MERGEs all nodes and relationships into Neo4j.
Idempotent — safe to re-run; existing nodes are updated, not duplicated.

Relationship types loaded:
  HAS_CARDINAL_SYMPTOM    cardinal_symptoms
  HAS_ASSOCIATED_SYMPTOM  associated_symptoms
  HAS_RISK_FACTOR         risk_factors
  HAS_DIFFERENTIAL        differentials
  ARGUES_AGAINST          argues_against
  HAS_RED_FLAG            red_flags
  CONFIRMED_BY            confirms

Run from the cds/ directory:
    python neo4j/neo4j_loader.py
"""

import json
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    raise SystemExit("python-dotenv required: pip install python-dotenv")

try:
    from neo4j import GraphDatabase
except ImportError:
    raise SystemExit("neo4j driver required: pip install neo4j")

# ── Config ───────────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")

URI      = os.environ["NEO4J_URI"]
USERNAME = os.environ["NEO4J_USERNAME"]
PASSWORD = os.environ["NEO4J_PASSWORD"]

GRAPH_JSONL = ROOT / "graph_entities.jsonl"

# Maps graph: block keys → (relationship_type, target_node_label)
KEY_MAP = {
    "cardinal_symptoms":   ("HAS_CARDINAL_SYMPTOM",    "Symptom"),
    "associated_symptoms": ("HAS_ASSOCIATED_SYMPTOM",  "Symptom"),
    "risk_factors":        ("HAS_RISK_FACTOR",          "RiskFactor"),
    "differentials":       ("HAS_DIFFERENTIAL",         "Condition"),
    "argues_against":      ("ARGUES_AGAINST",           "Symptom"),
    "red_flags":           ("HAS_RED_FLAG",             "RedFlag"),
    "confirms":            ("CONFIRMED_BY",              "DiagnosticTest"),
}


# ── Schema migration ──────────────────────────────────────────────────────────

def run_schema(session):
    migration = (ROOT / "neo4j" / "migrations" / "001_initial_schema.cypher").read_text()
    # Execute each statement individually (driver doesn't support multi-statement strings)
    for stmt in migration.split(";"):
        stmt = stmt.strip()
        if stmt and not stmt.startswith("//"):
            session.run(stmt)
    print("Schema: constraints and indexes applied")


# ── Loaders ───────────────────────────────────────────────────────────────────

def merge_condition(tx, record):
    tx.run(
        """
        MERGE (c:Condition {name: $name})
        SET c.icd11          = $icd11,
            c.category       = $category,
            c.corpus_version = $corpus_version,
            c.review_status  = $review_status
        """,
        name=record["condition"],
        icd11=record.get("icd11"),
        category=record.get("category"),
        corpus_version=str(record.get("corpus_version", "")),
        review_status=record.get("review_status"),
    )


def merge_relationships(tx, condition_name, key, terms, rel_type, node_label):
    for term in terms:
        name = term.get("canonical") or term.get("raw")
        if not name:
            continue
        tx.run(
            f"""
            MERGE (t:{node_label} {{name: $name}})
            WITH t
            MATCH (c:Condition {{name: $condition}})
            MERGE (c)-[:{rel_type} {{source_key: $key}}]->(t)
            """,
            name=name,
            condition=condition_name,
            key=key,
        )


def load_record(session, record):
    condition = record["condition"]
    session.execute_write(merge_condition, record)

    for key, terms in record.get("graph", {}).items():
        if key not in KEY_MAP:
            continue
        rel_type, node_label = KEY_MAP[key]
        session.execute_write(merge_relationships, condition, key, terms, rel_type, node_label)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not GRAPH_JSONL.exists():
        raise SystemExit(f"Run ingest.py first — {GRAPH_JSONL.name} not found")

    records = []
    with GRAPH_JSONL.open(encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))

    print(f"Records to load: {len(records)}")

    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))

    try:
        driver.verify_connectivity()
        print(f"Connected: {URI}")
    except Exception as e:
        raise SystemExit(f"Connection failed: {e}")

    with driver.session() as session:
        run_schema(session)
        for record in records:
            load_record(session, record)
            print(f"  Loaded: {record['condition']}")

    driver.close()
    print(f"\nDone. {len(records)} conditions loaded.")


if __name__ == "__main__":
    main()
