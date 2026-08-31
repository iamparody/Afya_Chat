"""
Chroma loader — PubMedBERT embeddings.

Reads chunks.jsonl, embeds via pritamdeka/S-PubMedBert-MS-MARCO (local,
no API key), upserts into collection 'cds_conditions_pubmedbert'.

The Cohere collection ('cds_conditions') is left untouched for A/B comparison.

Run from cds/ directory:
    python chroma/chroma_loader_pubmedbert.py
"""

import json
import sys
from pathlib import Path

from dotenv import load_dotenv
import chromadb
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CHUNKS_JSONL    = ROOT / "chunks.jsonl"
CHROMA_DIR      = ROOT / "chroma" / "db"
COLLECTION_NAME = "cds_conditions_pubmedbert"
MODEL_NAME      = "pritamdeka/S-PubMedBert-MS-MARCO"


def load_chunks():
    with CHUNKS_JSONL.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def main():
    if not CHUNKS_JSONL.exists():
        raise SystemExit("Run ingest.py first — chunks.jsonl not found")

    chunks = load_chunks()
    print(f"Chunks to embed: {len(chunks)}")

    print(f"Loading model: {MODEL_NAME} ...")
    model = SentenceTransformer(MODEL_NAME)
    print("Model loaded.\n")

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

    print(f"Embedding {len(texts)} chunks ...")
    embeddings = model.encode(texts, show_progress_bar=True).tolist()

    db = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = db.get_or_create_collection(COLLECTION_NAME)

    collection.upsert(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    print(f"\nDone. {len(chunks)} chunks loaded into '{COLLECTION_NAME}'.")
    print(f"Chroma DB: {CHROMA_DIR}")
    print(f"Embedding dim: {len(embeddings[0])}")


if __name__ == "__main__":
    main()
