"""
Phase 5 RAG — orchestrator.

Four responsibilities only:
1. Receive patient presentation
2. Run retrieval (vector candidates → graph profiles → filtered vector passages)
3. Build context and call LLM via provider
4. Validate returned JSON against OUTPUT_SCHEMA — fail closed

Clinical logic lives in prompts.py. Provider logic lives in providers.py.
This file orchestrates only.
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
import cohere
import chromadb
import jsonschema
from neo4j import GraphDatabase

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from prompts import SYSTEM_PROMPT, OUTPUT_SCHEMA, build_context
from providers import get_provider

CHROMA_DIR      = ROOT / "chroma" / "db"
COLLECTION_NAME = "cds_conditions"
EMBED_MODEL     = "embed-multilingual-v3.0"
TOP_N_CANDIDATES = 6
TOP_N_PASSAGES   = 5  # per candidate — wider window to ensure red flag + diagnostic sections are included


# ── Retrieval: vector candidate generation ────────────────────────────────────

def get_vector_candidates(co, collection, presentation, n=TOP_N_CANDIDATES):
    """Unrestricted semantic search → top N unique conditions."""
    emb = co.embed(
        texts=[presentation],
        model=EMBED_MODEL,
        input_type="search_query",
    ).embeddings[0]

    results = collection.query(
        query_embeddings=[emb],
        n_results=n * 3,
        include=["metadatas"],
    )

    seen = {}
    for meta in results["metadatas"][0]:
        condition = meta["condition"]
        if condition not in seen:
            seen[condition] = True
        if len(seen) >= n:
            break

    return list(seen.keys())


# ── Retrieval: graph profiles ─────────────────────────────────────────────────

SYMPTOMS_QUERY = """
MATCH (c:Condition {name: $condition})-[:HAS_CARDINAL_SYMPTOM|HAS_ASSOCIATED_SYMPTOM]->(s:Symptom)
RETURN s.name AS symptom
"""

ARGUES_AGAINST_QUERY = """
MATCH (c:Condition {name: $condition})-[:ARGUES_AGAINST]->(s:Symptom)
RETURN s.name AS feature
"""

def get_graph_profile(session, condition):
    symptoms       = [r["symptom"]  for r in session.run(SYMPTOMS_QUERY, condition=condition)]
    argues_against = [r["feature"]  for r in session.run(ARGUES_AGAINST_QUERY, condition=condition)]
    return symptoms, argues_against


def count_overlap(presentation_lower, terms):
    return [t for t in terms if t.lower() in presentation_lower]


# ── Retrieval: filtered vector passages ───────────────────────────────────────

def get_filtered_passages(co, collection, presentation, conditions):
    """Semantic search restricted to the graph's top candidates."""
    emb = co.embed(
        texts=[presentation],
        model=EMBED_MODEL,
        input_type="search_query",
    ).embeddings[0]

    passages = []
    for condition in conditions:
        results = collection.query(
            query_embeddings=[emb],
            n_results=TOP_N_PASSAGES,
            where={"condition": condition},
            include=["documents", "metadatas"],
        )
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            passages.append({
                "condition": meta["condition"],
                "section":   meta["section"],
                "text":      doc,
            })

    return passages


# ── Validation ────────────────────────────────────────────────────────────────

def validate(raw_text: str) -> dict:
    """
    Parse and validate LLM response. Fail closed — no repair attempts.
    Raises ValueError on any failure.
    """
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")

    try:
        jsonschema.validate(data, OUTPUT_SCHEMA)
    except jsonschema.ValidationError as e:
        raise ValueError(f"Schema violation: {e.message}")

    candidate_names = {c["diagnosis"] for c in data["candidates"]}
    if data["leading_candidate"] not in candidate_names:
        raise ValueError(
            f"leading_candidate '{data['leading_candidate']}' not in candidates[]"
        )

    return data


# ── Main pipeline ─────────────────────────────────────────────────────────────

def run(presentation: str) -> dict:
    """
    Full RAG pipeline for a patient presentation.
    Returns validated dict or raises ValueError on failure.
    """
    co       = cohere.Client(os.environ["COHERE_API_KEY"])
    db       = chromadb.PersistentClient(path=str(CHROMA_DIR))
    col      = db.get_or_create_collection(COLLECTION_NAME)
    driver   = GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"]),
    )
    provider = get_provider()

    try:
        # Step 1 — Vector: candidate generation (unrestricted)
        candidate_conditions = get_vector_candidates(co, col, presentation)

        # Step 2 — Graph: symptom profiles + argues_against per candidate
        presentation_lower = presentation.lower()
        candidates = []

        with driver.session() as session:
            for condition in candidate_conditions:
                symptoms, argues_against = get_graph_profile(session, condition)
                matched = count_overlap(presentation_lower, symptoms)
                candidates.append({
                    "condition":       condition,
                    "matched_count":   len(matched),
                    "matched_symptoms": matched,
                    "argues_against":  argues_against,
                })

        # Do not sort by matched_count — vector order is the primary semantic ranking.
        # Graph data (matched_symptoms, argues_against) is supplemental evidence for the LLM to use.

        # Step 3 — Vector: prose passages filtered to candidates only
        top_conditions = [c["condition"] for c in candidates]
        passages = get_filtered_passages(co, col, presentation, top_conditions)

        # Step 4 — Build context and call LLM
        context = build_context(presentation, candidates, passages)
        if hasattr(provider, "set_schema"):
            provider.set_schema(OUTPUT_SCHEMA)
        raw     = provider.generate(SYSTEM_PROMPT, context)

        # Step 5 — Validate (fail closed)
        return validate(raw)

    finally:
        driver.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        presentation = " ".join(sys.argv[1:])
    else:
        presentation = (
            "29M, 4 days fever, chills, headache. Productive cough started yesterday. "
            "Weakness, not eating well. No known illness. Came from Kisumu 10 days ago."
        )

    print(f"Presentation: {presentation}\n")

    try:
        result = run(presentation)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except ValueError as e:
        print(f"FAIL — {e}", file=sys.stderr)
        sys.exit(1)
