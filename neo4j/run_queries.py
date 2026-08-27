"""
Run test Cypher queries against the loaded CDS graph.

python neo4j/run_queries.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")

URI      = os.environ["NEO4J_URI"]
USERNAME = os.environ["NEO4J_USERNAME"]
PASSWORD = os.environ["NEO4J_PASSWORD"]

QUERIES = [
    ("Node counts by label",
     "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS total ORDER BY total DESC"),

    ("Symptom match: fever + headache + rigors -> ranked conditions",
     """MATCH (c:Condition)-[:HAS_CARDINAL_SYMPTOM|HAS_ASSOCIATED_SYMPTOM]->(s:Symptom)
        WHERE s.name IN ["fever", "headache", "rigors"]
        RETURN c.name AS condition, count(s) AS matched ORDER BY matched DESC"""),

    ("Differentials for Malaria",
     """MATCH (:Condition {name: "Malaria (unspecified)"})-[:HAS_DIFFERENTIAL]->(d:Condition)
        RETURN d.name AS differential"""),

    ("Red flags for Community-acquired pneumonia",
     """MATCH (:Condition {name: "Community-acquired pneumonia"})-[:HAS_RED_FLAG]->(f:RedFlag)
        RETURN f.name AS red_flag"""),

    ("Conditions sharing HIV infection as risk factor",
     """MATCH (c:Condition)-[:HAS_RISK_FACTOR]->(r:RiskFactor {name: "HIV infection"})
        RETURN c.name AS condition"""),
]


def main():
    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    driver.verify_connectivity()
    print(f"Connected: {URI}\n")

    with driver.session() as session:
        for title, query in QUERIES:
            print(f"-- {title} --")
            result = session.run(query)
            rows = result.data()
            if not rows:
                print("  (no results)")
            for row in rows:
                print(" ", row)
            print()

    driver.close()


if __name__ == "__main__":
    main()
