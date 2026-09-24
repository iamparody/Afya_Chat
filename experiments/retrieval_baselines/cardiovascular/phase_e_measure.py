#!/usr/bin/env python3
"""
Phase E retrieval measurement for cardiovascular domain frozen fixtures.

Run from cds/ root:
    python experiments/retrieval_baselines/cardiovascular/phase_e_measure.py

Prints Dense / BM25 / RRF rank for each frozen Phase C fixture and compares
against the Phase C baseline margin. Copy-paste the output into baseline.md
as the Phase E after column.
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_ROOT / "phase5"))
sys.path.insert(0, str(_ROOT))
# Fallback: relative paths work when invoked from cds/ root
sys.path.insert(0, "phase5")

import chromadb
import cohere
import os
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

from rag import _bm25_candidates, _rrf_candidates, get_vector_candidates

FIXTURES = [
    {
        "id": "C1a",
        "correct": "Essential hypertension",
        "confusable": "Hypertensive Crisis",
        "presentation": (
            "47F, headache. BP 168/102 on arrival. No chest pain, no neurological symptoms, "
            "no visual changes, no shortness of breath documented."
        ),
    },
    {
        "id": "C1b",
        "correct": "Essential hypertension",
        "confusable": "Hypertensive Crisis",
        "presentation": (
            "54M, known hypertensive on amlodipine for 3 years. Routine review. BP 158/96 today "
            "and 162/98 at last visit. No headache, no visual disturbance, no chest pain, no "
            "shortness of breath. No focal neurological symptoms. Feels well. Non-smoker. "
            "BMI 29. Fasting glucose normal last year."
        ),
    },
    {
        "id": "C1c",
        "correct": "Hypertensive Crisis",
        "confusable": "Essential hypertension",
        "presentation": (
            "61M, presents with sudden severe occipital headache for 2 hours. BP 210/128. "
            "Blurred vision. One episode of vomiting. Agitated and confused on examination. "
            "Known hypertensive, stopped medication 2 weeks ago. No fever. Fundoscopy: bilateral "
            "disc swelling."
        ),
    },
    {
        "id": "C2a",
        "correct": "Deep vein thrombosis",
        "confusable": "Pulmonary embolism",
        "presentation": (
            "33F, right leg swollen and painful for 3 days. Right calf noticeably larger than "
            "left — diameter difference approximately 2.5 cm measured from tibial tuberosity. "
            "Warmth and erythema over right calf. Cannot walk without limping. No fever. No "
            "cough, no chest pain, no breathlessness. Recently returned from a 10-hour flight."
        ),
    },
    {
        "id": "C2b",
        "correct": "Pulmonary embolism",
        "confusable": "Deep vein thrombosis",
        "presentation": (
            "41M, sudden breathlessness starting 1 hour ago. Sharp right-sided chest pain, "
            "worse on inspiration. Coughed up small amount of blood-stained sputum. Tachycardia "
            "on examination — pulse 112 bpm. Respiratory rate 22 per minute. Oxygen saturation "
            "93% on air. No fever. No sputum production. Admitted to hospital 2 weeks ago for "
            "elective knee surgery."
        ),
    },
    {
        "id": "C2c",
        "correct": "Pulmonary embolism",
        "confusable": "Deep vein thrombosis",
        "presentation": (
            "38F, 6 weeks post-partum, breastfeeding. Increasing breathlessness over 4 hours. "
            "Mild left-sided pleuritic chest pain. No productive cough. No fever. Pulse 108 bpm, "
            "respiratory rate 20 per minute. Oxygen saturation 94%. Left calf mildly tender on "
            "palpation — no visible swelling. BMI 32. No prior history of clots."
        ),
    },
]

# Phase C baseline RRF margins (correct_score - confusable_score)
BASELINE_MARGIN = {
    "C1a": -0.01566,
    "C1b": -0.00080,
    "C1c": +0.00152,
    "C2a": +0.00105,
    "C2b": +0.00054,
    "C2c": +0.00028,
}

BASELINE_STATUS = {
    "C1a": "confusable_leads",
    "C1b": "confusable_leads",
    "C1c": "correct_leads",
    "C2a": "correct_leads",
    "C2b": "correct_leads",
    "C2c": "correct_leads",
}


def rank_of(candidates, condition_name):
    """Return 1-based rank of condition in a list of condition-name strings."""
    name_lower = condition_name.lower()
    for i, c in enumerate(candidates[:10], 1):
        if c.lower() == name_lower:
            return i
    return ">10"


def rrf_score_of(rrf_ranked, rrf_scores_dict, condition_name):
    """Return RRF score for condition from the scores dict built in main()."""
    return rrf_scores_dict.get(condition_name.lower(), 0.0)


def main():
    co = cohere.Client(os.environ["COHERE_API_KEY"])
    chroma = chromadb.PersistentClient(path=str(_ROOT / "chroma" / "db"))
    col = chroma.get_collection("cds_conditions")

    print("=" * 70)
    print("Phase E — Cardiovascular retrieval measurement")
    print("=" * 70)
    print()

    for fx in FIXTURES:
        fid = fx["id"]
        correct = fx["correct"]
        confusable = fx["confusable"]
        presentation = fx["presentation"]

        emb = co.embed(
            texts=[presentation],
            model="embed-english-v3.0",
            input_type="search_query",
        ).embeddings[0]

        vec = get_vector_candidates(co, col, presentation, query_embedding=emb)
        bm25 = _bm25_candidates(presentation)
        rrf = _rrf_candidates(vec, bm25)

        # Anchor chunk Dense ranks — query raw Chroma results to find retrieval_context chunks
        raw = col.query(
            query_embeddings=[emb],
            n_results=min(200, col.count()),
            include=["metadatas"],
        )
        anchor_ranks = {}
        for i, meta in enumerate(raw["metadatas"][0], 1):
            if meta.get("section") == "retrieval_context":
                cond = meta["condition"]
                if cond not in anchor_ranks:
                    anchor_ranks[cond] = i

        # Reconstruct RRF scores from rank (RRF returns ranked strings, not scores)
        RRF_K = 60
        rrf_scores = {cond.lower(): 1.0 / (RRF_K + rank) for rank, cond in enumerate(rrf)}

        dense_correct = rank_of(vec, correct)
        dense_conf = rank_of(vec, confusable)
        bm25_correct = rank_of(bm25, correct)
        bm25_conf = rank_of(bm25, confusable)
        rrf_correct = rank_of(rrf, correct)
        rrf_conf = rank_of(rrf, confusable)

        correct_score = rrf_scores.get(correct.lower(), 0.0)
        conf_score = rrf_scores.get(confusable.lower(), 0.0)
        margin = correct_score - conf_score

        baseline_margin = BASELINE_MARGIN[fid]
        margin_delta = margin - baseline_margin
        status = "correct_leads" if margin > 0 else ("confusable_leads" if margin < 0 else "tied")

        if status == "correct_leads" and BASELINE_STATUS[fid] == "confusable_leads":
            result = "IMPROVED (flipped)"
        elif margin_delta > 0.00005:
            result = "IMPROVED (margin)"
        elif margin_delta < -0.00005:
            result = "REGRESSED"
        else:
            result = "unchanged"

        print(f"[{fid}] correct={correct!r}  confusable={confusable!r}")
        print(f"  Dense  : correct={dense_correct}  confusable={dense_conf}")
        print(f"  BM25   : correct={bm25_correct}  confusable={bm25_conf}")
        print(f"  RRF    : correct={rrf_correct}  confusable={rrf_conf}")
        print(f"  Margin : {margin:+.5f}  (baseline {baseline_margin:+.5f}  delta {margin_delta:+.5f})")
        print(f"  Status : {status}  →  {result}")
        # Anchor chunk ranks (retrieval_context section Dense rank — bleed diagnostic)
        correct_anchor = anchor_ranks.get(correct, ">200")
        conf_anchor = anchor_ranks.get(confusable, ">200")
        print(f"  Anchor chunks (Dense): correct={correct_anchor}  confusable={conf_anchor}")
        print()

    print("=" * 70)
    print("Done. Paste this output into baseline.md Phase E column.")
    print("=" * 70)


if __name__ == "__main__":
    main()
