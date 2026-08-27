"""
Retrieval baseline — Phase 5 pre-work.

Runs 6 clinician-style test cases through both retrieval paths:
  - Graph (Neo4j): symptom term matching via Cypher
  - Vector (Chroma): semantic similarity via Cohere embeddings

Outputs a structured baseline table to retrieval_baseline.md.

Run from the cds/ directory:
    python chroma/retrieval_baseline.py
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
import cohere
import chromadb
from neo4j import GraphDatabase

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CHROMA_DIR      = ROOT / "chroma" / "db"
COLLECTION_NAME = "cds_conditions"
EMBED_MODEL     = "embed-multilingual-v3.0"
OUTPUT          = ROOT / "chroma" / "retrieval_baseline.md"

# ── Test cases ────────────────────────────────────────────────────────────────
# Clinician-style inputs — messy, incomplete, as written at point of care.
# graph_terms: exact node names from symptom_vocabulary for Cypher matching.
# expected: correct diagnosis the system should surface.
# contradicting_terms: argues_against node names relevant to this case.

CASES = [
    {
        "id": 1,
        "label": "Fever + respiratory overlap (Malaria vs CAP)",
        "query": (
            "29M, 4 days fever, chills, headache. Productive cough started yesterday. "
            "Weakness, not eating well. No known illness. Came from Kisumu 10 days ago."
        ),
        "graph_terms": ["fever", "chills", "headache", "productive cough", "malaise", "anorexia"],
        "expected": "Malaria (unspecified)",
        "contradicting_note": "Productive cough argues toward CAP — system should surface both",
    },
    {
        "id": "2a",
        "label": "TB vs CAP — 3-week cough",
        "query": (
            "42F. Cough 3 weeks now, getting worse. Very tired, lost maybe 3-4kg. "
            "Night sweats most nights. Appetite down. No known TB contact."
        ),
        "graph_terms": ["productive cough", "fatigue", "weight loss", "night sweats", "anorexia"],
        "expected": "Pulmonary tuberculosis",
        "contradicting_note": "No TB contact argues slightly against — should still surface TB",
    },
    {
        "id": "2b",
        "label": "TB vs CAP — 3-day cough (same patient, one variable changed)",
        "query": (
            "42F. Cough 3 days, productive. Tired. Lost appetite. Slight fever. "
            "No weight loss mentioned. No night sweats."
        ),
        "graph_terms": ["productive cough", "fatigue", "fever", "anorexia"],
        "expected": "Community-acquired pneumonia",
        "contradicting_note": "Short duration argues against TB — CAP should rank higher than 2a",
    },
    {
        "id": 3,
        "label": "UTI vs gastroenteritis — incomplete (no urinary symptoms documented)",
        "query": (
            "26F, 2 days fever, nausea, lower abdominal pain. Feeling weak. "
            "No urinary symptoms mentioned."
        ),
        "graph_terms": ["fever", "nausea", "suprapubic discomfort", "malaise"],
        "expected": "Urinary tract infection",
        "contradicting_note": "Absent urinary symptoms — system must not invent dysuria or frequency",
    },
    {
        "id": "4a",
        "label": "Diabetes — full presentation",
        "query": (
            "51M, months of fatigue, very thirsty all the time, urinating a lot more than usual. "
            "Blurred vision sometimes. No fever, no acute illness."
        ),
        "graph_terms": ["fatigue", "polydipsia", "polyuria", "blurred vision"],
        "expected": "Type 2 diabetes mellitus",
        "contradicting_note": "No fever/acute illness argues against infectious causes",
    },
    {
        "id": "4b",
        "label": "Diabetes — stripped (no thirst/urination mentioned)",
        "query": (
            "51M, fatigue and blurred vision. No other information provided."
        ),
        "graph_terms": ["fatigue", "blurred vision"],
        "expected": "Type 2 diabetes mellitus",
        "contradicting_note": "System should be less confident — missing key features",
    },
    {
        "id": 5,
        "label": "Hypertension as incidental finding",
        "query": (
            "47F, headache. BP 168/102 on arrival. No chest pain, no neurological symptoms, "
            "no visual changes, no shortness of breath documented."
        ),
        "graph_terms": ["headache", "epistaxis"],
        "expected": "Essential hypertension",
        "contradicting_note": "No end-organ symptoms — system should not confirm hypertensive emergency",
    },
    {
        "id": 6,
        "label": "Anaemia — low-specificity presentation",
        "query": (
            "34F, 3 months fatigue, dizzy when standing, can't exercise like before. "
            "No fever, no cough, no urinary symptoms, no GI symptoms reported."
        ),
        "graph_terms": ["fatigue", "lightheadedness", "reduced exercise tolerance"],
        "expected": "Iron deficiency anaemia",
        "contradicting_note": "No GI symptoms — should note absence doesn't exclude all causes",
    },
]


# ── Graph retrieval ───────────────────────────────────────────────────────────

GRAPH_CYPHER = """
MATCH (c:Condition)-[:HAS_CARDINAL_SYMPTOM|HAS_ASSOCIATED_SYMPTOM]->(s:Symptom)
WHERE s.name IN $terms
RETURN c.name AS condition, count(s) AS matched
ORDER BY matched DESC
LIMIT 4
"""

ARGUES_CYPHER = """
MATCH (c:Condition)-[:ARGUES_AGAINST]->(s:Symptom)
WHERE s.name IN $terms
RETURN c.name AS condition, collect(s.name) AS contradicting
"""

def graph_retrieve(session, terms):
    result = session.run(GRAPH_CYPHER, terms=terms)
    return [(r["condition"], r["matched"]) for r in result]


# ── Vector retrieval ──────────────────────────────────────────────────────────

def vector_retrieve(co, collection, query, n=3):
    emb = co.embed(
        texts=[query],
        model=EMBED_MODEL,
        input_type="search_query",
    ).embeddings[0]
    res = collection.query(
        query_embeddings=[emb],
        n_results=n,
        include=["metadatas", "distances"],
    )
    return [
        (m["condition"], m["section"], round(d, 3))
        for m, d in zip(res["metadatas"][0], res["distances"][0])
    ]


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    co     = cohere.Client(os.environ["COHERE_API_KEY"])
    db     = chromadb.PersistentClient(path=str(CHROMA_DIR))
    col    = db.get_or_create_collection(COLLECTION_NAME)
    driver = GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"]),
    )
    driver.verify_connectivity()

    lines = [
        "# Retrieval Baseline — Phase 5 Pre-work",
        "",
        "Graph = Neo4j Cypher symptom match | Vector = Chroma semantic search",
        "",
        "---",
        "",
    ]

    with driver.session() as session:
        for case in CASES:
            print(f"Case {case['id']}: {case['label']}")

            graph_hits  = graph_retrieve(session, case["graph_terms"])
            vector_hits = vector_retrieve(co, col, case["query"])

            graph_top3  = [f"{c} ({n} match)" for c, n in graph_hits[:3]]
            vector_top3 = [f"{c} / {s} [{d}]" for c, s, d in vector_hits]

            graph_conditions  = [c for c, _ in graph_hits[:4]]
            vector_conditions = [c for c, _, _ in vector_hits]

            correct_in_graph  = case["expected"] in graph_conditions
            correct_in_vector = case["expected"] in vector_conditions

            lines += [
                f"## Case {case['id']} — {case['label']}",
                "",
                f"> **Input:** {case['query']}",
                "",
                f"**Expected:** {case['expected']}",
                "",
                "| | Graph top 3 | Vector top 3 |",
                "|---|---|---|",
                f"| Results | {' · '.join(graph_top3) or '—'} | {' · '.join(vector_top3)} |",
                f"| Correct retrieved? | {'Yes' if correct_in_graph else 'No'} | {'Yes' if correct_in_vector else 'No'} |",
                "",
                f"**Contradicting evidence note:** {case['contradicting_note']}",
                "",
                "---",
                "",
            ]

    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    driver.close()

    print(f"\nBaseline written: {OUTPUT.name}")


if __name__ == "__main__":
    main()
