"""
Retrieval inspector — shows top-k chunks retrieved for a given presentation
under both Cohere and PubMedBERT backends.

Usage (from cds/ root):
    python phase5/inspect_retrieval.py
    python phase5/inspect_retrieval.py "custom presentation text"
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "phase5"))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

import chromadb
from embed_provider import CohereEmbedder, PubMedBertEmbedder

CHROMA_DIR = ROOT / "chroma" / "db"
TOP_K = 18  # n_results for unrestricted search (matches get_vector_candidates n*3)


def inspect(embedder, label, presentation):
    db  = chromadb.PersistentClient(path=str(CHROMA_DIR))
    col = db.get_collection(embedder.COLLECTION)

    emb = embedder.embed_query(presentation)
    results = col.query(
        query_embeddings=[emb],
        n_results=TOP_K,
        include=["metadatas", "distances"],
    )

    print(f"\n{'='*60}")
    print(f"{label} — top {TOP_K} chunks")
    print(f"Collection: {embedder.COLLECTION}")
    print(f"{'='*60}")
    print(f"{'Rank':<5} {'Distance':>8}  {'Condition':<40} {'Section'}")
    print(f"{'-'*5} {'-'*8}  {'-'*40} {'-'*25}")

    seen_conditions = {}
    for rank, (meta, dist) in enumerate(
        zip(results["metadatas"][0], results["distances"][0]), start=1
    ):
        cond = meta["condition"]
        sec  = meta["section"]
        first = "*" if cond not in seen_conditions else " "
        seen_conditions[cond] = seen_conditions.get(cond, 0) + 1
        print(f"{rank:<5} {dist:>8.4f}  {cond:<40} {sec}")

    print(f"\nUnique conditions in top {TOP_K}:")
    for cond, count in sorted(seen_conditions.items(), key=lambda x: -x[1]):
        print(f"  {count:>2}x  {cond}")


if __name__ == "__main__":
    presentation = (
        " ".join(sys.argv[1:])
        if len(sys.argv) > 1
        else "26F, 2 days fever, nausea, lower abdominal pain. Feeling weak. No urinary symptoms mentioned."
    )

    print(f"Presentation: {presentation}\n")

    cohere_embedder = CohereEmbedder()
    inspect(cohere_embedder, "COHERE", presentation)

    print("\nLoading PubMedBERT model...")
    pubmed_embedder = PubMedBertEmbedder()
    inspect(pubmed_embedder, "PubMedBERT", presentation)
