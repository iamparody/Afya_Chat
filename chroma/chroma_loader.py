"""
Chroma vector store loader for CDS.

Reads chunks.jsonl, embeds each chunk via the selected backend,
upserts into a local Chroma collection. Idempotent — safe to re-run.

Run from the cds/ directory:
    python chroma/chroma_loader.py                   # Google (default)
    python chroma/chroma_loader.py --backend cohere
    python chroma/chroma_loader.py --backend pubmedbert
"""

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
import chromadb

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT / "phase5"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CHUNKS_JSONL = ROOT / "chunks.jsonl"
CHROMA_DIR   = ROOT / "chroma" / "db"


def load_chunks():
    with CHUNKS_JSONL.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--backend", default="cohere", choices=["google", "cohere", "pubmedbert"],
        help="Embedding backend (default: cohere)",
    )
    args = parser.parse_args()

    if not CHUNKS_JSONL.exists():
        raise SystemExit("Run ingest.py first — chunks.jsonl not found")

    from embed_provider import GoogleEmbedder, CohereEmbedder, PubMedBertEmbedder

    if args.backend == "google":
        print("Backend: Google gemini-embedding-001")
        embedder = GoogleEmbedder()
    elif args.backend == "cohere":
        print("Backend: Cohere embed-multilingual-v3.0")
        embedder = CohereEmbedder()
    else:
        print(f"Backend: PubMedBERT ({PubMedBertEmbedder._MODEL_NAME})")
        embedder = PubMedBertEmbedder()

    chunks = load_chunks()
    print(f"Chunks to embed: {len(chunks)}")
    print(f"Collection: {embedder.COLLECTION}")

    db = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = db.get_or_create_collection(embedder.COLLECTION)

    ids       = []
    documents = []
    metadatas = []
    embeddings = []

    for i, chunk in enumerate(chunks):
        meta = chunk["metadata"]
        ids.append(f"{meta['condition']}::{meta['section']}::{i}")
        documents.append(chunk["text"])
        metadatas.append({
            "condition":      meta.get("condition", ""),
            "section":        meta.get("section", ""),
            "category":       meta.get("category", ""),
            "icd11":          meta.get("icd11", ""),
            "review_status":  meta.get("review_status", ""),
            "corpus_version": str(meta.get("corpus_version", "")),
        })

        emb = embedder.embed_document(chunk["text"])
        embeddings.append(emb)

        if (i + 1) % 10 == 0 or (i + 1) == len(chunks):
            print(f"  Embedded {i + 1} / {len(chunks)}")

    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    print(f"\nDone. {len(chunks)} chunks loaded into '{embedder.COLLECTION}'.")
    print(f"Chroma DB: {CHROMA_DIR}")


if __name__ == "__main__":
    main()
