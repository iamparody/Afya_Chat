"""
Phase 8 reasoning evaluation harness.

Scores 10 dimensions per case using the rubric in rubric.py.

Dimensions:
    Deterministic (rubric.deterministic_scorers):
        leading_diagnosis, differential_relevance, confidence_range, red_flags,
        confidence_consistency
    LLM judge (rubric.judge_scorers):
        supporting_features, arguing_against_accuracy,
        missing_information_relevance, question_quality
    Special (requires initial + enriched):
        diagnostic_shift

Max score: 20 per case (10 dims x 2), 100 total (5 cases).
N/A dims are excluded from the denominator.

Usage:
    python phase8/evaluate_reasoning.py              # all 5 cases
    python phase8/evaluate_reasoning.py d1 d3        # specific cases
    python phase8/evaluate_reasoning.py --no-judge   # skip LLM judge (dry run)

Calibration note: run once with human review of judge scores before trusting
automated results in CI. The expected-answer set in rubric.py is the reference
standard — not the judge.
"""

import argparse
import concurrent.futures
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "phase5"))
sys.path.insert(0, str(ROOT / "phase8"))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import rag

# ── Eval-specific RAG call policy ─────────────────────────────────────────────
# Separate from providers.py production retry policy — do not merge.
_EVAL_CALL_TIMEOUT  = 60                # seconds per individual RAG call attempt
_EVAL_RETRY_DELAYS  = [5, 10, 20]      # seconds between retry attempts


def _timed_rag_run(presentation):
    """Run rag.run() with a hard per-call timeout. Raises TimeoutError if exceeded."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(rag.run, presentation)
        try:
            return future.result(timeout=_EVAL_CALL_TIMEOUT)
        except concurrent.futures.TimeoutError:
            raise TimeoutError(
                f"RAG call exceeded {_EVAL_CALL_TIMEOUT}s — "
                "thread may linger until provider gives up internally"
            )


def eval_rag_run(presentation):
    """
    Eval-specific wrapper around rag.run().

    Applies a per-call timeout and short retry delays. A failed call is an
    eval error — raises RuntimeError after all retries are exhausted.
    The caller decides whether to skip the case or abort the run.
    """
    last_exc = None
    n = len(_EVAL_RETRY_DELAYS)
    for attempt, delay in enumerate(_EVAL_RETRY_DELAYS, start=1):
        try:
            return _timed_rag_run(presentation)
        except Exception as e:
            last_exc = e
            if attempt < n:
                print(
                    f"  Eval RAG attempt {attempt}/{n} failed "
                    f"({type(e).__name__}: {e}) — retrying in {delay}s...",
                    flush=True,
                )
                time.sleep(delay)
            else:
                print(
                    f"  Eval RAG attempt {attempt}/{n} failed "
                    f"({type(e).__name__}: {e}) — all retries exhausted.",
                    flush=True,
                )
    raise RuntimeError(
        f"RAG call failed after {n} attempts. Last error: {last_exc}"
    ) from last_exc
from disambiguate import is_ambiguous, get_discriminating_questions, enrich_presentation
from evaluate_disambiguation import CASES
from rubric import EXPECTED, deterministic_scorers, judge_scorers

PASS_SYM  = "✓"   # ✓
PART_SYM  = "△"   # △
FAIL_SYM  = "✗"   # ✗
SKIP_SYM  = "○"   # ○  skipped (--no-judge)
NA_SYM    = "—"   # —  not applicable (ambiguity did not fire)

# Ordered dimension list — drives scoring and reporting
DIMENSIONS = [
    ("leading_diagnosis",             "deterministic"),
    ("differential_relevance",        "deterministic"),
    ("confidence_range",              "deterministic"),
    ("red_flags",                     "deterministic"),
    ("confidence_consistency",        "deterministic"),
    ("supporting_features",           "judge"),
    ("arguing_against_accuracy",      "judge"),
    ("missing_information_relevance", "judge"),
    ("question_quality",              "judge"),
    ("diagnostic_shift",              "special"),
]

MAX_DIM_SCORE = 2
# MAX_PER_CASE and MAX_TOTAL are now dynamic — N/A dims are excluded from the denominator.


# ── Special scorer ────────────────────────────────────────────────────────────

def score_diagnostic_shift(initial, enriched, expected):
    """
    Scores whether the enriched re-run shifts the leading candidate toward
    the expected diagnosis after clinician answers.

    Separate from other scorers because it requires both initial and enriched
    results rather than a single result dict.

    Returns score=None when is_ambiguous() legitimately did not fire — the
    dimension is N/A and must not be counted in the denominator.
    """
    if expected.get("is_negative_case"):
        return {"score": 2, "justification": "Negative case: no diagnostic shift expected or applicable."}

    if enriched is None:
        if not is_ambiguous(initial):
            return {
                "score": None,
                "justification": "N/A — ambiguity did not fire; diagnostic shift not applicable.",
            }
        return {
            "score": 0,
            "justification": "No enriched result available (pipeline error).",
        }

    new_lead  = enriched.get("leading_candidate", "").lower()
    old_lead  = initial.get("leading_candidate", "")
    expected_leads = [e.lower() for e in expected.get("expected_enriched_leads", [])]

    if any(e in new_lead or new_lead in e for e in expected_leads):
        return {
            "score": 2,
            "justification": (
                f"Lead shifted to '{enriched.get('leading_candidate')}' — matches expected "
                f"{expected.get('expected_enriched_leads')}."
            ),
        }

    if old_lead.lower() != new_lead:
        return {
            "score": 1,
            "justification": (
                f"Lead shifted from '{old_lead}' to '{enriched.get('leading_candidate')}' "
                f"but not toward expected {expected.get('expected_enriched_leads')}."
            ),
        }

    return {
        "score": 0,
        "justification": (
            f"Lead did not shift after enrichment (still '{enriched.get('leading_candidate')}'); "
            f"expected one of {expected.get('expected_enriched_leads')}."
        ),
    }


# ── Case scorer ───────────────────────────────────────────────────────────────

def score_case(initial, enriched, expected, provider, use_judge):
    """
    Score all 9 dimensions for one case.
    Returns dict mapping dimension_name -> {"score": int, "justification": str}.
    score=-1 means dimension was skipped (--no-judge or not applicable).
    """
    scores = {}

    for dim, family in DIMENSIONS:
        if family == "deterministic":
            scores[dim] = deterministic_scorers[dim](initial, expected)

        elif family == "special":
            scores[dim] = score_diagnostic_shift(initial, enriched, expected)

        elif family == "judge":
            if not use_judge:
                scores[dim] = {"score": -1, "justification": "Skipped (--no-judge)"}
                continue
            scores[dim] = judge_scorers[dim](initial, expected, provider)

    return scores


# ── Reporter ──────────────────────────────────────────────────────────────────

def _sym(score):
    if score is None: return NA_SYM
    if score < 0:     return SKIP_SYM
    if score == 2:    return PASS_SYM
    if score == 1:    return PART_SYM
    return FAIL_SYM


def print_case_report(case_id, label, dim_scores, initial, questions):
    # Exclude skipped (score=-1) and N/A (score=None) from denominator
    scored_dims = [v for v in dim_scores.values() if v.get("score") is not None and v["score"] >= 0]
    na_dims     = [k for k, v in dim_scores.items() if v.get("score") is None]
    total = sum(v["score"] for v in scored_dims)
    max_p = len(scored_dims) * MAX_DIM_SCORE
    na_str = f"  ({len(na_dims)} N/A: {', '.join(na_dims)})" if na_dims else ""

    print(f"\n{'=' * 62}")
    print(f"Case {case_id}: {label}")
    print(f"Lead: {initial.get('leading_candidate', '?')}  |  Score: {total}/{max_p}{na_str}")
    print(f"Questions: {questions if questions else '— none —'}")
    print(f"{'=' * 62}")

    for dim, _ in DIMENSIONS:
        r = dim_scores.get(dim, {"score": -1, "justification": "—"})
        s = r.get("score", -1)
        label_str = dim.replace("_", " ")
        if s is None:
            score_str = "N/A"
        elif s >= 0:
            score_str = f"{s}/2"
        else:
            score_str = "—"
        print(f"  {_sym(s)}  {label_str:<35} {score_str}")
        if r.get("justification") and r["justification"] not in ("—", ""):
            print(f"       {r['justification']}")

    return total, max_p


# ── Runner ────────────────────────────────────────────────────────────────────

def run_all(case_ids=None, use_judge=True):
    cases_to_run = CASES
    if case_ids:
        cases_to_run = [c for c in CASES if c["id"] in case_ids]

    provider = None
    if use_judge:
        from providers import get_provider
        provider = get_provider()

    grand_total     = 0
    grand_max       = 0
    all_results     = []
    pipeline_errors = []

    for case in cases_to_run:
        cid      = case["id"]
        expected = EXPECTED.get(cid)
        if not expected:
            print(f"\n{SKIP_SYM} Case {cid}: no EXPECTED entry — skipping")
            continue

        print(f"\nRunning {cid}: {case['label']} ...", flush=True)

        try:
            initial = eval_rag_run(case["presentation"])
        except Exception as e:
            print(f"  {FAIL_SYM} PIPELINE ERROR (initial) — {e}")
            pipeline_errors.append(f"{cid}:initial")
            continue

        enriched  = None
        questions = []

        if not expected.get("is_negative_case"):
            questions = get_discriminating_questions(initial)

            if is_ambiguous(initial) and case.get("enrichment"):
                try:
                    ep = enrich_presentation(case["presentation"], case["enrichment"])
                    enriched = eval_rag_run(ep)
                except Exception as e:
                    print(f"  {SKIP_SYM} PIPELINE ERROR (enriched) — {e}")
                    pipeline_errors.append(f"{cid}:enriched")

        dim_scores = score_case(initial, enriched, expected, provider, use_judge)

        case_total, case_max = print_case_report(
            cid, case["label"], dim_scores, initial, questions
        )
        grand_total += case_total
        grand_max   += case_max
        all_results.append({"id": cid, "total": case_total, "max": case_max, "scores": dim_scores})

    # ── Summary ───────────────────────────────────────────────────────────────
    pct = (100 * grand_total // grand_max) if grand_max else 0
    total_na = sum(
        1 for r in all_results
        for dim, _ in DIMENSIONS
        if dim in r["scores"] and r["scores"][dim].get("score") is None
    )
    na_note = f"  ({total_na} N/A across all cases)" if total_na else ""
    print(f"\n{'=' * 62}")
    print(f"BASELINE: {grand_total}/{grand_max} ({pct}%){na_note}")
    print(f"{'=' * 62}")
    print()
    print("Per-dimension summary:")
    for dim, _ in DIMENSIONS:
        dim_scores_all = [
            r["scores"][dim]["score"]
            for r in all_results
            if dim in r["scores"]
            and r["scores"][dim].get("score") is not None
            and r["scores"][dim]["score"] >= 0
        ]
        na_count = sum(
            1 for r in all_results
            if dim in r["scores"] and r["scores"][dim].get("score") is None
        )
        if dim_scores_all:
            total_dim = sum(dim_scores_all)
            max_dim   = len(dim_scores_all) * MAX_DIM_SCORE
            na_str    = f"  ({na_count} N/A)" if na_count else ""
            print(f"  {dim.replace('_', ' '):<35} {total_dim}/{max_dim}{na_str}")

    if pipeline_errors:
        print()
        print(f"PIPELINE ERRORS ({len(pipeline_errors)}): {', '.join(pipeline_errors)}")
        print("These calls failed after all eval retries — results for affected cases are incomplete.")

    if use_judge:
        print()
        print(
            "Calibration: compare these scores against your own clinical judgement "
            "before treating the automated judge as ground truth. "
            "EXPECTED in rubric.py is the reference standard."
        )

    return all_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 8 reasoning evaluation harness")
    parser.add_argument("cases", nargs="*", help="Case IDs to run (e.g. d1 d3); omit for all")
    parser.add_argument(
        "--no-judge",
        action="store_true",
        help="Skip LLM judge calls — scores deterministic dims only",
    )
    parser.add_argument(
        "--gate",
        type=int,
        default=None,
        metavar="PCT",
        help="Exit non-zero if overall score < PCT%% of applicable max (e.g. --gate 80)",
    )
    args = parser.parse_args()
    results = run_all(args.cases or None, use_judge=not args.no_judge)

    if args.gate is not None:
        grand_total = sum(r["total"] for r in results)
        grand_max   = sum(r["max"]   for r in results)
        pct = (100 * grand_total // grand_max) if grand_max else 0
        if pct < args.gate:
            print(f"\nGATE FAILED: {grand_total}/{grand_max} ({pct}%) < {args.gate}% threshold")
            sys.exit(1)
        print(f"\nGATE PASSED: {grand_total}/{grand_max} ({pct}%) >= {args.gate}% threshold")
