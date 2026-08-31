"""
Case 3 pipeline debugger.

Traces every step for the UTI vs AGE presentation under both embedding backends:
  1. Vector candidates selected
  2. Graph profiles (matched symptoms + argues_against per candidate)
  3. Filtered passages passed to Gemini (condition, section, text)
  4. Full context string sent to Gemini
  5. Gemini structured output (leading candidate + reasoning fields)

Usage (from cds/ root):
    python phase5/debug_case3.py
    python phase5/debug_case3.py pubmedbert   # PubMedBERT only
    python phase5/debug_case3.py cohere       # Cohere only
"""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "phase5"))
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

import chromadb
from neo4j import GraphDatabase
from embed_provider import CohereEmbedder, PubMedBertEmbedder
from rag import get_vector_candidates, get_graph_profile, get_filtered_passages, validate
from prompts import SYSTEM_PROMPT, OUTPUT_SCHEMA, build_context
from providers import get_provider

CHROMA_DIR = ROOT / "chroma" / "db"

PRESENTATION = (
    "26F, 2 days fever, nausea, lower abdominal pain. "
    "Feeling weak. No urinary symptoms mentioned."
)

TOP_N_CANDIDATES = 6
TOP_N_PASSAGES   = 5


def sep(title=""):
    line = "=" * 60
    if title:
        print(f"\n{line}\n{title}\n{line}")
    else:
        print(f"\n{line}")


def run_debug(embedder, label):
    sep(f"BACKEND: {label}  |  collection: {embedder.COLLECTION}")
    print(f"Presentation: {PRESENTATION}\n")

    db  = chromadb.PersistentClient(path=str(CHROMA_DIR))
    col = db.get_or_create_collection(embedder.COLLECTION)

    driver = GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"]),
    )

    try:
        # ── Step 1: vector candidates ─────────────────────────────────────────
        sep("STEP 1 — Vector candidates")
        candidate_conditions = get_vector_candidates(embedder, col, PRESENTATION,
                                                     n=TOP_N_CANDIDATES)
        for i, c in enumerate(candidate_conditions, 1):
            print(f"  {i}. {c}")

        # ── Step 2: graph profiles ────────────────────────────────────────────
        sep("STEP 2 — Graph profiles per candidate")
        presentation_lower = PRESENTATION.lower()
        candidates = []

        with driver.session() as session:
            for condition in candidate_conditions:
                symptoms, argues_against = get_graph_profile(session, condition)
                matched = [t for t in symptoms if t.lower() in presentation_lower]
                candidates.append({
                    "condition":        condition,
                    "matched_count":    len(matched),
                    "matched_symptoms": matched,
                    "argues_against":   argues_against,
                })
                print(f"\n  {condition}")
                print(f"    Graph symptoms   : {symptoms[:6]}{'...' if len(symptoms)>6 else ''}")
                print(f"    Matched in pres. : {matched}")
                print(f"    Argues against   : {argues_against[:4]}{'...' if len(argues_against)>4 else ''}")

        # ── Step 3: filtered passages ─────────────────────────────────────────
        sep("STEP 3 — Filtered passages sent to Gemini")
        top_conditions = [c["condition"] for c in candidates]
        passages = get_filtered_passages(embedder, col, PRESENTATION, top_conditions)

        current_cond = None
        for p in passages:
            if p["condition"] != current_cond:
                current_cond = p["condition"]
                print(f"\n  [{current_cond}]")
            preview = p["text"][:120].replace("\n", " ").strip()
            print(f"    section={p['section']:<30}  text={preview!r}")

        print(f"\n  Total passages: {len(passages)} "
              f"({len(top_conditions)} conditions × up to {TOP_N_PASSAGES} each)")

        # ── Step 4: full context ──────────────────────────────────────────────
        sep("STEP 4 — Full context sent to Gemini")
        context = build_context(PRESENTATION, candidates, passages)
        print(context)

        # ── Step 5: Gemini output ─────────────────────────────────────────────
        sep("STEP 5 — Gemini structured output")
        provider = get_provider()
        if hasattr(provider, "set_schema"):
            provider.set_schema(OUTPUT_SCHEMA)
        raw = provider.generate(SYSTEM_PROMPT, context)

        result = validate(raw)
        print(f"\n  leading_candidate : {result['leading_candidate']}")
        print(f"\n  candidates:")
        for c in result.get("candidates", []):
            print(f"\n    {c['diagnosis']}  [{c.get('confidence_level','?')}]")
            print(f"      why_considered   : {c.get('why_considered','')[:100]}")
            print(f"      arguing_against  : {c.get('arguing_against',[])}")
            print(f"      missing_info     : {c.get('missing_information',[])}")
        print(f"\n  red_flags: {result.get('red_flags', [])}")

    finally:
        driver.close()


if __name__ == "__main__":
    backend = sys.argv[1].lower() if len(sys.argv) > 1 else "both"

    if backend in ("cohere", "both"):
        run_debug(CohereEmbedder(), "COHERE")

    if backend in ("pubmedbert", "both"):
        print("\nLoading PubMedBERT model...")
        run_debug(PubMedBertEmbedder(), "PubMedBERT")
