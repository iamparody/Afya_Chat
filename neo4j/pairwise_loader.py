"""
Neo4j pairwise disambiguation loader for the AFI domain.

Reads docs/domain_contracts/afi_pairs.yaml and MERGEs all DIFFERENTIATED_FROM
relationships into Neo4j. Idempotent — keyed on pair_id; safe to re-run.

If a Condition node for a not-yet-authored card does not exist, it is created as
a minimal node (name only). neo4j_loader.py will populate all properties when the
card is authored and ingested.

Run from the cds/ directory:
    python neo4j/pairwise_loader.py

Optional flags:
    --dry-run   Print pairs that would be loaded; make no graph changes.
    --pair MSP-01 RP-01   Load only the specified pair IDs.
"""

import argparse
import os
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    raise SystemExit("pyyaml required: pip install pyyaml")

try:
    from dotenv import load_dotenv
except ImportError:
    raise SystemExit("python-dotenv required: pip install python-dotenv")

try:
    from neo4j import GraphDatabase
except ImportError:
    raise SystemExit("neo4j driver required: pip install neo4j")

# ── Config ────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")

URI      = os.environ["NEO4J_URI"]
USERNAME = os.environ["NEO4J_USERNAME"]
PASSWORD = os.environ["NEO4J_PASSWORD"]

PAIRS_YAML = ROOT / "docs" / "domain_contracts" / "afi_pairs.yaml"
MIGRATION  = ROOT / "neo4j" / "migrations" / "002_pairwise_schema.cypher"


# ── Schema ────────────────────────────────────────────────────────────────────

def run_schema(session):
    sql = MIGRATION.read_text(encoding="utf-8")
    for stmt in sql.split(";"):
        stmt = stmt.strip()
        if stmt and not stmt.startswith("//"):
            session.run(stmt)
    print("Schema: pairwise indexes applied")


# ── Loaders ───────────────────────────────────────────────────────────────────

def ensure_condition(tx, name: str):
    """MERGE a Condition node by name. Creates a minimal node if it does not exist."""
    tx.run(
        "MERGE (:Condition {name: $name})",
        name=name,
    )


def upsert_pair(tx, pair: dict):
    """
    MERGE the DIFFERENTIATED_FROM relationship keyed on pair_id.
    ON CREATE and ON MATCH both set all properties so re-runs stay current.
    Relationship is stored in one direction; queries use undirected MATCH.
    """
    tx.run(
        """
        MATCH (a:Condition {name: $condition_a}), (b:Condition {name: $condition_b})
        MERGE (a)-[r:DIFFERENTIATED_FROM {pair_id: $pair_id}]->(b)
        SET r.priority               = $priority,
            r.pathways               = $pathways,
            r.governance_pending     = $governance_pending,
            r.cross_domain           = $cross_domain,
            r.shared_features        = $shared_features,
            r.discriminating_evidence = $discriminating_evidence,
            r.missing_information    = $missing_information,
            r.red_flags              = $red_flags
        """,
        condition_a=pair["condition_a"],
        condition_b=pair["condition_b"],
        pair_id=pair["pair_id"],
        priority=pair["priority"],
        pathways=pair.get("pathways", []),
        governance_pending=pair.get("governance_pending", False),
        cross_domain=pair.get("cross_domain", False),
        shared_features=pair.get("shared_features", []),
        discriminating_evidence=pair.get("discriminating_evidence", []),
        missing_information=pair.get("missing_information", []),
        red_flags=pair.get("red_flags", []),
    )


def load_pair(session, pair: dict):
    session.execute_write(ensure_condition, pair["condition_a"])
    session.execute_write(ensure_condition, pair["condition_b"])
    session.execute_write(upsert_pair, pair)


# ── Validation ────────────────────────────────────────────────────────────────

def validate_pair(pair: dict) -> list[str]:
    """Return a list of validation error strings (empty = valid)."""
    errors = []
    required = ["pair_id", "priority", "condition_a", "condition_b",
                "pathways", "shared_features", "discriminating_evidence",
                "missing_information", "red_flags"]
    for field in required:
        if field not in pair:
            errors.append(f"{pair.get('pair_id', '?')}: missing field '{field}'")
    if pair.get("priority") not in ("required", "mandatory_safety"):
        errors.append(f"{pair.get('pair_id', '?')}: invalid priority '{pair.get('priority')}'")
    if pair.get("condition_a") == pair.get("condition_b"):
        errors.append(f"{pair.get('pair_id', '?')}: condition_a and condition_b are identical")
    return errors


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Load AFI pairwise pairs into Neo4j")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print pairs without making graph changes")
    parser.add_argument("--pair", nargs="+", metavar="PAIR_ID",
                        help="Load only these pair IDs (e.g. MSP-01 RP-03)")
    args = parser.parse_args()

    if not PAIRS_YAML.exists():
        raise SystemExit(f"Pairs file not found: {PAIRS_YAML}")

    with PAIRS_YAML.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    pairs = data.get("pairs", [])

    if args.pair:
        requested = set(args.pair)
        pairs = [p for p in pairs if p.get("pair_id") in requested]
        missing = requested - {p["pair_id"] for p in pairs}
        if missing:
            print(f"Warning: pair IDs not found in YAML: {', '.join(sorted(missing))}")

    # Validate all pairs before touching the graph
    all_errors = []
    for pair in pairs:
        all_errors.extend(validate_pair(pair))
    if all_errors:
        for err in all_errors:
            print(f"VALIDATION ERROR: {err}", file=sys.stderr)
        raise SystemExit("Fix validation errors before loading.")

    print(f"Pairs to load: {len(pairs)}")

    if args.dry_run:
        print("\n[dry-run] Would load:")
        for p in pairs:
            gp = " [governance_pending]" if p.get("governance_pending") else ""
            xd = " [cross_domain]" if p.get("cross_domain") else ""
            print(f"  {p['pair_id']} ({p['priority']}){gp}{xd}: "
                  f"{p['condition_a']} vs {p['condition_b']} "
                  f"[{', '.join(p.get('pathways', []))}]")
        return

    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    try:
        driver.verify_connectivity()
        print(f"Connected: {URI}")
    except Exception as e:
        raise SystemExit(f"Connection failed: {e}")

    with driver.session() as session:
        run_schema(session)
        for pair in pairs:
            load_pair(session, pair)
            gp = " [governance_pending]" if pair.get("governance_pending") else ""
            xd = " [cross_domain]" if pair.get("cross_domain") else ""
            print(f"  Loaded: {pair['pair_id']}{gp}{xd} — "
                  f"{pair['condition_a']} vs {pair['condition_b']}")

    driver.close()

    mandatory = sum(1 for p in pairs if p["priority"] == "mandatory_safety")
    required  = sum(1 for p in pairs if p["priority"] == "required")
    pending   = sum(1 for p in pairs if p.get("governance_pending"))
    xdomain   = sum(1 for p in pairs if p.get("cross_domain"))
    print(f"\nDone. {len(pairs)} pairs loaded "
          f"({mandatory} mandatory_safety, {required} required, "
          f"{pending} governance_pending, {xdomain} cross_domain).")


if __name__ == "__main__":
    main()
