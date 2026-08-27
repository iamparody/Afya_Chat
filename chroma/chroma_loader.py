"""
Chroma vector store loader for CDS.

Reads chunks.jsonl, embeds each chunk via Cohere, upserts into a local
Chroma collection. Idempotent — safe to re-run; existing chunks are updated.

Run from the cds/ directory:
    python chroma/chroma_loader.py
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
import cohere
import chromadb

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CHUNKS_JSONL    = ROOT / "chunks.jsonl"
CHROMA_DIR      = ROOT / "chroma" / "db"
COLLECTION_NAME = "cds_conditions"
EMBED_MODEL     = "embed-multilingual-v3.0"
BATCH_SIZE      = 48  # Cohere max per request is 96; 48 is safe


def load_chunks():
    with CHUNKS_JSONL.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def embed_batch(client, texts):
    response = client.embed(
        texts=texts,
        model=EMBED_MODEL,
        input_type="search_document",
    )
    return response.embeddings


def main():
    if not CHUNKS_JSONL.exists():
        raise SystemExit("Run ingest.py first — chunks.jsonl not found")

    api_key = os.environ.get("COHERE_API_KEY")
    if not api_key:
        raise SystemExit("COHERE_API_KEY not set in .env")

    chunks = load_chunks()
    print(f"Chunks to embed: {len(chunks)}")

    co = cohere.Client(api_key)
    db = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = db.get_or_create_collection(COLLECTION_NAME)

    ids       = []
    texts     = []
    metadatas = []

    for i, chunk in enumerate(chunks):
        meta = chunk["metadata"]
        ids.append(f"{meta['condition']}::{meta['section']}::{i}")
        texts.append(chunk["text"])
        metadatas.append({
            "condition":      meta.get("condition", ""),
            "section":        meta.get("section", ""),
            "category":       meta.get("category", ""),
            "icd11":          meta.get("icd11", ""),
            "review_status":  meta.get("review_status", ""),
            "corpus_version": str(meta.get("corpus_version", "")),
        })

    # Embed in batches
    all_embeddings = []
    for start in range(0, len(texts), BATCH_SIZE):
        batch = texts[start: start + BATCH_SIZE]
        embeddings = embed_batch(co, batch)
        all_embeddings.extend(embeddings)
        print(f"  Embedded {min(start + BATCH_SIZE, len(texts))} / {len(texts)}")

    collection.upsert(
        ids=ids,
        documents=texts,
        embeddings=all_embeddings,
        metadatas=metadatas,
    )

    print(f"\nDone. {len(chunks)} chunks loaded into '{COLLECTION_NAME}'.")
    print(f"Chroma DB: {CHROMA_DIR}")


if __name__ == "__main__":
    main()
