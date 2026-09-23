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
    pool = min(max(DENSE_POOL, n * 10), collection.count())
    results = collection.query(
        query_embeddings=[emb],
        n_results=pool,
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
    {
        "id": "13",
        "label": "DVT — post-partum calf swelling",
        "presentation": (
            "28F, 10 days post-partum after caesarean section. Right calf swelling and "
            "tenderness for 3 days, worse on walking. Right calf circumference 3cm larger "
            "than left. No fever. No chest pain or breathlessness."
        ),
        "expected_terms": ["thrombosis", "dvt", "deep vein"],
    },
]


# ── Metrics helpers ───────────────────────────────────────────────────────────

def recall_at_k(ranks: list, k: int) -> float:
    return sum(1 for r in ranks if r is not None and r < k) / len(ranks)


# ── Runner ────────────────────────────────────────────────────────────────────

def run_comparison(chunks: list[dict], embedder, collection, label: str = "", baseline: bool = False):
    bm25_index = build_bm25_index(chunks)
    cases = EVAL_CASES

    W = 80
    print(f"\n{'=' * W}")
    if label:
        print(f"  CORPUS: {label}")
    print(f"  {len(chunks)} chunks | {len(set(c['metadata']['condition'] for c in chunks))} conditions")
    print(f"{'=' * W}")

    # At baseline we also measure Recall@30 and Recall@50 — need larger candidate pools
    ks = [9, 30, 50] if baseline else [9]
    n_main = ks[-1] if baseline else TOP_N   # retrieve up to the largest k needed

    hdr = f"{'ID':<5} {'Label':<30} {'Dense':>6} {'BM25':>6} {'RRF':>6}  {'Provenance':<14}"
    print(hdr)
    print("-" * W)

    ranks_by_mode: dict = {"dense": [], "bm25": [], "rrf": []}
    per_case_detail = []

    for case in cases:
        d_cands = dense_candidates(embedder, collection, case["presentation"], n=n_main)
        b_cands = bm25_candidates(bm25_index, chunks, case["presentation"], n=n_main)
        r_cands = rrf_candidates(d_cands, b_cands, n=n_main)

        d_rank = rank_of(case["expected_terms"], d_cands)
        b_rank = rank_of(case["expected_terms"], b_cands)
        r_rank = rank_of(case["expected_terms"], r_cands)

        ranks_by_mode["dense"].append(d_rank)
        ranks_by_mode["bm25"].append(b_rank)
        ranks_by_mode["rrf"].append(r_rank)

        # Provenance at TOP_N=9 (the live retrieval window)
        d9 = set(d_cands[:TOP_N])
        b9 = set(b_cands[:TOP_N])
        in_d = case["expected_terms"] and any(
            t in c.lower() for c in d9 for t in case["expected_terms"]
        )
        in_b = case["expected_terms"] and any(
            t in c.lower() for c in b9 for t in case["expected_terms"]
        )
        if in_d and in_b:
            prov = "Both"
        elif in_d:
            prov = "Dense-only"
        elif in_b:
            prov = "BM25-only"
        else:
            prov = "Neither@9"

        def fmt_rank(r):
            return str(r) if r is not None else "—"

        print(
            f"{case['id']:<5} {case['label']:<30} "
            f"{fmt_rank(d_rank):>6} {fmt_rank(b_rank):>6} {fmt_rank(r_rank):>6}  {prov:<14}"
        )

        per_case_detail.append({
            "id": case["id"],
            "d_cands": d_cands[:TOP_N],
            "b_cands": b_cands[:TOP_N],
            "r_cands": r_cands[:TOP_N],
            "bm25_only": sorted(set(b_cands[:TOP_N]) - set(d_cands[:TOP_N])),
            "dense_only": sorted(set(d_cands[:TOP_N]) - set(b_cands[:TOP_N])),
        })

    print("-" * W)

    # Summary metrics
    for k in ks:
        dr = recall_at_k(ranks_by_mode["dense"], k)
        br = recall_at_k(ranks_by_mode["bm25"], k)
        rr = recall_at_k(ranks_by_mode["rrf"], k)
        print(f"Recall@{k:<3}: Dense={dr:.2f}  BM25={br:.2f}  RRF={rr:.2f}")

    dmrr = mrr(ranks_by_mode["dense"])
    bmrr = mrr(ranks_by_mode["bm25"])
    rmrr = mrr(ranks_by_mode["rrf"])
    print(f"MRR:        Dense={dmrr:.3f}  BM25={bmrr:.3f}  RRF={rmrr:.3f}")

    # Per-case candidate lists (verbose)
    print(f"\n{'─' * W}")
    print("Per-case candidate lists (top 9):")
    for d in per_case_detail:
        print(f"\n  Case {d['id']}:")
        print(f"    Dense: {d['d_cands']}")
        print(f"    BM25:  {d['b_cands']}")
        print(f"    RRF:   {d['r_cands']}")
        if d["bm25_only"]:
            print(f"    BM25-only: {d['bm25_only']}")
        if d["dense_only"]:
            print(f"    Dense-only: {d['dense_only']}")

    return ranks_by_mode["dense"], ranks_by_mode["bm25"], ranks_by_mode["rrf"]


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
    parser.add_argument("--growth",    action="store_true", help="Run corpus-growth stability test")
    parser.add_argument("--baseline",  action="store_true", help="27-condition retrieval baseline: Recall@9/30/50 + MRR + provenance")
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
    elif args.baseline:
        print("\n27-CONDITION RETRIEVAL BASELINE — Phase 5b-1")
        print(f"Corpus: {len(chunks)} chunks | RRF_K={RRF_K} | TOP_N={TOP_N}")
        run_comparison(chunks, embedder, collection, label="27-CONDITION CORPUS", baseline=True)
    else:
        run_comparison(chunks, embedder, collection, label="CURRENT CORPUS")


if __name__ == "__main__":
    main()
