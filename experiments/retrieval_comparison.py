"""
Offline retrieval comparison: Dense vs BM25 vs RRF.

Reads chunks.jsonl and runs three retrieval modes against all 8 regression
eval presentations. No Gemini, no Neo4j, no rag.py changes.

Measures:
  - Recall@9: expected diagnosis in top-9 candidates
  - Rank: position of expected diagnosis (0-indexed; None if absent)
  - MRR: mean reciprocal rank across cases
  - BM25-only / Dense-only candidates: conditions found by one mode not the other
  - Candidate overlap between modes

Corpus-growth test: set GROWTH_MODE=True and point EXTRA_CHUNKS_PATH to a
second chunks.jsonl containing new cards. Compare ranks before/after.

Run from cds/ root:
    python experiments/retrieval_comparison.py
    python experiments/retrieval_comparison.py --growth
"""

import argparse
import json
import math
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "phase5"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Corpus ────────────────────────────────────────────────────────────────────

CHUNKS_PATH = ROOT / "corpus_pipeline" / "output" / "chunks.jsonl"
CHROMA_DIR  = ROOT / "chroma" / "db"
TOP_N       = 9     # match rag.py TOP_N_CANDIDATES
BM25_POOL   = 50    # chunks retrieved per BM25 query before condition-dedupe
DENSE_POOL  = 100   # chunks retrieved per dense query (rag.py uses 500; 100 sufficient here)
RRF_K       = 60    # standard default (Cormack et al. 2009)


def load_chunks(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


# ── BM25 index ────────────────────────────────────────────────────────────────

# Section-header boilerplate terms with near-zero IDF — suppress to reduce noise.
_STOPWORDS = frozenset([
    "the", "and", "for", "this", "that", "with", "from", "have", "are",
    "not", "may", "also", "more", "been", "when", "than", "they", "their",
    "which", "will", "its", "but", "was", "one", "can", "into", "other",
    "some", "such", "most", "each", "these", "those", "then", "thus",
    # corpus boilerplate — high-frequency, zero-discrimination
    "diagnosis", "diagnostic", "features", "cardinal", "associated",
    "against", "argue", "argues", "differential", "differentials",
    "typical", "signs", "signs", "context", "predisposing", "presentation",
    "condition", "patient", "clinical", "disease", "symptoms", "symptom",
])


def _tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9][a-z0-9'/\-]*", text.lower())
    return [t for t in tokens if t not in _STOPWORDS and len(t) > 2]


def build_bm25_index(chunks: list[dict]):
    from rank_bm25 import BM25Okapi
    corpus = [_tokenize(c["text"]) for c in chunks]
    return BM25Okapi(corpus)


# ── Dense retrieval ───────────────────────────────────────────────────────────

def dense_candidates(embedder, collection, presentation: str, n: int = TOP_N) -> list[str]:
    """Return top-N unique conditions by Chroma cosine rank."""
    emb = embedder.embed_query(presentation)
    results = collection.query(
        query_embeddings=[emb],
        n_results=min(DENSE_POOL, collection.count()),
        include=["metadatas"],
    )
    seen: dict[str, bool] = {}
    for meta in results["metadatas"][0]:
        cond = meta["condition"]
        if cond not in seen:
            seen[cond] = True
        if len(seen) >= n:
            break
    return list(seen.keys())


# ── BM25 retrieval ────────────────────────────────────────────────────────────

def bm25_candidates(bm25_index, chunks: list[dict], presentation: str, n: int = TOP_N) -> list[str]:
    """Return top-N unique conditions by BM25 rank."""
    tokens = _tokenize(presentation)
    scores = bm25_index.get_scores(tokens)

    # Pair (score, chunk) sorted descending
    ranked = sorted(enumerate(scores), key=lambda x: -x[1])

    seen: dict[str, bool] = {}
    for idx, _score in ranked:
        cond = chunks[idx]["metadata"]["condition"]
        if cond not in seen:
            seen[cond] = True
        if len(seen) >= n:
            break
    return list(seen.keys())


# ── RRF fusion ────────────────────────────────────────────────────────────────

def rrf_candidates(
    dense_list: list[str],
    bm25_list: list[str],
    n: int = TOP_N,
    k: int = RRF_K,
) -> list[str]:
    """Unweighted RRF over two condition rank lists. Returns top-N conditions."""
    scores: dict[str, float] = {}
    for rank, cond in enumerate(dense_list):
        scores[cond] = scores.get(cond, 0.0) + 1.0 / (k + rank)
    for rank, cond in enumerate(bm25_list):
        scores[cond] = scores.get(cond, 0.0) + 1.0 / (k + rank)
    ranked = sorted(scores.keys(), key=lambda c: -scores[c])
    return ranked[:n]


# ── Metrics ───────────────────────────────────────────────────────────────────

def rank_of(expected_terms: list[str], candidates: list[str]) -> int | None:
    """0-indexed rank of first candidate matching any expected term. None if absent."""
    for i, cond in enumerate(candidates):
        cond_lower = cond.lower()
        if any(t in cond_lower for t in expected_terms):
            return i
    return None


def mrr(ranks: list[int | None]) -> float:
    rr = [1.0 / (r + 1) if r is not None else 0.0 for r in ranks]
    return sum(rr) / len(rr) if rr else 0.0


# ── Eval cases ────────────────────────────────────────────────────────────────
# Trimmed to retrieval-relevant fields only.
# expected_terms: lowercase substrings — any match counts (mirrors evaluate.py primary_contains).

EVAL_CASES = [
    {
        "id": "1",
        "label": "Fever + resp (Malaria vs CAP)",
        "presentation": (
            "29M, sudden onset fever 3 days ago with rigors, severe headache, chills. "
            "Productive cough started yesterday. Weakness, not eating well. "
            "No known illness. Lives in Kisumu, lake-shore area."
        ),
        "expected_terms": ["malaria"],
    },
    {
        "id": "2a",
        "label": "TB vs CAP — 3-week cough",
        "presentation": (
            "42F. Cough 3 weeks now, getting worse. Very tired, lost maybe 3-4kg. "
            "Night sweats most nights. Appetite down. No known TB contact."
        ),
        "expected_terms": ["tuberculosis", "tb"],
    },
    {
        "id": "2b",
        "label": "TB vs CAP — 3-day cough",
        "presentation": (
            "42F. Cough 3 days, productive. Tired. Lost appetite. Slight fever. "
            "No weight loss mentioned. No night sweats."
        ),
        "expected_terms": ["pneumonia"],
    },
    {
        "id": "3",
        "label": "UTI vs AGE",
        "presentation": (
            "26F, 2 days fever, nausea, lower abdominal pain. Feeling weak. "
            "No urinary symptoms mentioned."
        ),
        "expected_terms": ["uti", "urinary", "gastroenteritis"],
    },
    {
        "id": "4a",
        "label": "Diabetes — full",
        "presentation": (
            "51M, months of fatigue, very thirsty all the time, urinating a lot more than usual. "
            "Blurred vision sometimes. No fever, no acute illness."
        ),
        "expected_terms": ["diabetes", "type 2"],
    },
    {
        "id": "4b",
        "label": "Diabetes — stripped",
        "presentation": "51M, fatigue and blurred vision. No other information provided.",
        "expected_terms": ["diabetes", "anaemia", "anemia"],
    },
    {
        "id": "5",
        "label": "Hypertension — incidental BP",
        "presentation": (
            "47F, headache. BP 168/102 on arrival. No chest pain, no neurological symptoms, "
            "no visual changes, no shortness of breath documented."
        ),
        "expected_terms": ["hypertension"],
    },
    {
        "id": "6",
        "label": "Anaemia — low-specificity",
        "presentation": (
            "34F, 3 months fatigue, dizzy when standing, can't exercise like before. "
            "Family noticed she looks pale. Nails look pale too. "
            "No fever, no cough, no urinary symptoms, no GI symptoms reported."
        ),
        "expected_terms": ["anaemia", "anemia", "iron"],
    },
]


# ── Runner ────────────────────────────────────────────────────────────────────

def run_comparison(chunks: list[dict], embedder, collection, label: str = ""):
    bm25_index = build_bm25_index(chunks)

    print(f"\n{'=' * 72}")
    if label:
        print(f"  CORPUS: {label}")
    print(f"  {len(chunks)} chunks | {len(set(c['metadata']['condition'] for c in chunks))} conditions")
    print(f"{'=' * 72}")
    print(f"{'ID':<4} {'Label':<32} {'Dense':>6} {'BM25':>6} {'RRF':>6}  BM25-only  Dense-only")
    print("-" * 72)

    dense_ranks, bm25_ranks, rrf_ranks = [], [], []
    per_case_detail = []

    for case in EVAL_CASES:
        d_cands = dense_candidates(embedder, collection, case["presentation"])
        b_cands = bm25_candidates(bm25_index, chunks, case["presentation"])
        r_cands = rrf_candidates(d_cands, b_cands)

        d_rank = rank_of(case["expected_terms"], d_cands)
        b_rank = rank_of(case["expected_terms"], b_cands)
        r_rank = rank_of(case["expected_terms"], r_cands)

        dense_ranks.append(d_rank)
        bm25_ranks.append(b_rank)
        rrf_ranks.append(r_rank)

        d_set = set(d_cands)
        b_set = set(b_cands)
        bm25_only = b_set - d_set
        dense_only = d_set - b_set

        def fmt_rank(r):
            return str(r) if r is not None else "—"

        print(
            f"{case['id']:<4} {case['label']:<32} "
            f"{fmt_rank(d_rank):>6} {fmt_rank(b_rank):>6} {fmt_rank(r_rank):>6}  "
            f"{len(bm25_only):>9}  {len(dense_only):>10}"
        )

        per_case_detail.append({
            "id": case["id"],
            "d_cands": d_cands,
            "b_cands": b_cands,
            "r_cands": r_cands,
            "bm25_only": sorted(bm25_only),
            "dense_only": sorted(dense_only),
        })

    print("-" * 72)

    def recall_at_9(ranks):
        return sum(1 for r in ranks if r is not None) / len(ranks)

    print(f"\nRecall@{TOP_N}:  Dense={recall_at_9(dense_ranks):.2f}  BM25={recall_at_9(bm25_ranks):.2f}  RRF={recall_at_9(rrf_ranks):.2f}")
    print(f"MRR:        Dense={mrr(dense_ranks):.3f}  BM25={mrr(bm25_ranks):.3f}  RRF={mrr(rrf_ranks):.3f}")

    # BM25-only and dense-only candidates across all cases
    all_bm25_only = set()
    all_dense_only = set()
    for d in per_case_detail:
        all_bm25_only.update(d["bm25_only"])
        all_dense_only.update(d["dense_only"])

    if all_bm25_only:
        print(f"\nConditions found by BM25 but not Dense (any case): {sorted(all_bm25_only)}")
    if all_dense_only:
        print(f"Conditions found by Dense but not BM25 (any case): {sorted(all_dense_only)}")

    # Per-case candidate lists (verbose)
    print(f"\n{'─' * 72}")
    print("Per-case candidate lists:")
    for d in per_case_detail:
        print(f"\n  Case {d['id']}:")
        print(f"    Dense: {d['d_cands']}")
        print(f"    BM25:  {d['b_cands']}")
        print(f"    RRF:   {d['r_cands']}")

    return dense_ranks, bm25_ranks, rrf_ranks


# ── Growth comparison ─────────────────────────────────────────────────────────

def run_growth_test(embedder, collection):
    """
    Compare retrieval stability before/after corpus expansion.
    Baseline: chunks_pre_dvt.jsonl (234 chunks, 26 conditions — pre-DVT snapshot).
    Expanded: chunks.jsonl (243 chunks, 27 conditions — current corpus with DVT).

    To regenerate baseline after a new card:
        python -c "
        import json, io, pathlib
        src = pathlib.Path('corpus_pipeline/output/chunks.jsonl')
        dst = pathlib.Path('corpus_pipeline/output/chunks_pre_dvt.jsonl')
        chunks = [json.loads(l) for l in io.open(src, encoding='utf-8')]
        pre = [c for c in chunks if c['metadata']['condition'] != '<new_condition>']
        [io.open(dst,'w',encoding='utf-8').write(json.dumps(c,ensure_ascii=False)+'\n') for c in pre]
        "
    """
    pre_dvt_path = ROOT / "corpus_pipeline" / "output" / "chunks_pre_dvt.jsonl"
    if not pre_dvt_path.exists():
        print("\nGrowth test: chunks_pre_dvt.jsonl not found. Skipping.")
        print("Generate with: filter chunks.jsonl to exclude the new condition → chunks_pre_dvt.jsonl")
        return

    base_chunks = load_chunks(pre_dvt_path)
    exp_chunks  = load_chunks(CHUNKS_PATH)

    print("\n\n" + "=" * 72)
    print("CORPUS GROWTH STABILITY TEST")
    print("=" * 72)

    d_base, b_base, r_base = run_comparison(base_chunks, embedder, collection, "BASELINE")
    d_exp,  b_exp,  r_exp  = run_comparison(exp_chunks,  embedder, collection, "EXPANDED")

    print("\n\nRank shift (expanded − baseline, lower = better):")
    print(f"{'ID':<6} {'Dense':>8} {'BM25':>8} {'RRF':>8}")
    for i, case in enumerate(EVAL_CASES):
        def delta(a, b):
            if a is None and b is None: return "—"
            if a is None: return f"+inf"
            if b is None: return f"-inf"
            d = b - a
            return f"{d:+d}"
        print(f"{case['id']:<6} {delta(d_base[i], d_exp[i]):>8} {delta(b_base[i], b_exp[i]):>8} {delta(r_base[i], r_exp[i]):>8}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--growth", action="store_true", help="Run corpus-growth stability test")
    args = parser.parse_args()

    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")

    from embed_provider import CohereEmbedder
    import chromadb

    embedder   = CohereEmbedder()
    db         = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = db.get_or_create_collection(embedder.COLLECTION)

    chunks = load_chunks(CHUNKS_PATH)

    if args.growth:
        run_growth_test(embedder, collection)
    else:
        run_comparison(chunks, embedder, collection, label="CURRENT CORPUS")


if __name__ == "__main__":
    main()
