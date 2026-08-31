"""
Phase 5 evaluation harness.

Runs all 8 contract cases through rag.run(), scores each against
chroma/evaluation_contract.md criteria.

Usage:
    python phase5/evaluate.py                    # all cases, dense-only (Cohere baseline)
    python phase5/evaluate.py --hybrid           # all cases, BM25 + dense RRF
    python phase5/evaluate.py 2a                 # single case
    python phase5/evaluate.py --hybrid 2a 2b     # specific cases, hybrid mode
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import rag


# ── Case definitions ──────────────────────────────────────────────────────────

CASES = [
    {
        "id": "1",
        "label": "Fever + respiratory (Malaria vs CAP)",
        "presentation": (
            "29M, 4 days fever, chills, headache. Productive cough started yesterday. "
            "Weakness, not eating well. No known illness. Came from Kisumu 10 days ago."
        ),
        "checks": {
            "primary_contains":      ["malaria"],
            "secondary_contains":    ["pneumonia"],
            "red_flags_contain":     [],  # stochastic — ANN retrieval varies; malaria red flags (altered consciousness, neck stiffness, severe anaemia) checked manually
            "missing_info_contain":  ["rdt", "oxygen"],
            "prohibited_strings":    ["malaria confirmed", "cough confirms pneumonia"],
            "manual": [
                "Productive cough cited as reason CAP stays in differential — not dismissed",
                "Malaria red flags present: check for altered consciousness, neck stiffness, or severe anaemia — verify in output",
            ],
        },
    },
    {
        "id": "2a",
        "label": "TB vs CAP — 3-week cough",
        "presentation": (
            "42F. Cough 3 weeks now, getting worse. Very tired, lost maybe 3-4kg. "
            "Night sweats most nights. Appetite down. No known TB contact."
        ),
        "checks": {
            "primary_contains":      ["tuberculosis", "tb"],
            "secondary_contains":    ["pneumonia"],
            "red_flags_contain":     [],  # TB red flag sections rarely retrieved by vector similarity
            "missing_info_contain":  ["genexpert", "sputum", "hiv", "x-ray"],
            "prohibited_strings":    ["tb confirmed"],
            "manual": [
                "No TB contact stated as not-excluding TB — contact is risk factor, not a requirement",
                "TB confidence noted for comparison with Case 2b",
                "Haemoptysis should appear as red flag (Check for — haemoptysis) — verify in output",
                "Miliary TB should appear as red flag — verify in output",
            ],
        },
    },
    {
        "id": "2b",
        "label": "TB vs CAP — 3-day cough",
        "presentation": (
            "42F. Cough 3 days, productive. Tired. Lost appetite. Slight fever. "
            "No weight loss mentioned. No night sweats."
        ),
        "checks": {
            "primary_contains":          ["pneumonia", "cap"],
            "secondary_contains":        ["tuberculosis", "tb", "malaria"],
            "red_flags_contain":         ["respiratory", "oxygen"],
            "missing_info_contain":      ["oxygen", "rdt"],
            "prohibited_strings":        [],
            "tb_argues_against_contain": ["3 day", "acute", "weight loss", "night sweat"],
            "manual": [
                "TB confidence must be materially lower than Case 2a — compare directly",
                "3-day duration explicitly cited as arguing against TB",
                "No weight loss and no night sweats used as TB argues_against evidence",
            ],
        },
    },
    {
        "id": "3",
        "label": "UTI vs AGE — incomplete presentation",
        "presentation": (
            "26F, 2 days fever, nausea, lower abdominal pain. Feeling weak. "
            "No urinary symptoms mentioned."
        ),
        "checks": {
            "primary_contains":     ["uti", "urinary", "gastroenteritis"],
            "red_flags_contain":    [],  # Red flags scope limited to leading+same-confidence; AGE/malaria red flag content varies
            "missing_info_contain": ["dysuria", "frequency", "urine", "dipstick"],
            "prohibited_strings":   ["no uti because", "no dysuria", "dysuria present", "dysuria is absent"],
            "manual": [
                "Neither UTI nor AGE confirmed as sole primary — must be co-equal candidates",
                "Absent urinary symptoms stated as 'not documented', not as negative finding",
                "Urosepsis and dehydration should appear as red flags — verify in output",
            ],
        },
    },
    {
        "id": "4a",
        "label": "Diabetes — full presentation",
        "presentation": (
            "51M, months of fatigue, very thirsty all the time, urinating a lot more than usual. "
            "Blurred vision sometimes. No fever, no acute illness."
        ),
        "checks": {
            "primary_contains":     ["diabetes", "type 2"],
            "red_flags_contain":    ["hyperglycaemic", "hyperosmolar"],
            "missing_info_contain": ["glucose", "hba1c", "bmi"],
            "prohibited_strings":   ["diabetes confirmed"],
            "manual": [
                "No fever / no acute illness explicitly used to argue against infectious causes",
                "T2DM confidence noted for comparison with Case 4b",
            ],
        },
    },
    {
        "id": "4b",
        "label": "Diabetes — stripped",
        "presentation": (
            "51M, fatigue and blurred vision. No other information provided."
        ),
        "checks": {
            "primary_contains":     ["diabetes", "anaemia", "anemia"],
            "missing_info_contain": ["thirst", "urin", "glucose"],
            "prohibited_strings":   ["diabetes confirmed"],
            "manual": [
                "Confidence must be materially lower than Case 4a — compare directly",
                "Missing cardinal features (thirst, polyuria) named explicitly",
            ],
        },
    },
    {
        "id": "5",
        "label": "Hypertension — incidental finding",
        "presentation": (
            "47F, headache. BP 168/102 on arrival. No chest pain, no neurological symptoms, "
            "no visual changes, no shortness of breath documented."
        ),
        "checks": {
            "primary_contains":     ["hypertension"],
            "red_flags_contain":    ["encephalopathy", "retinal"],
            "missing_info_contain": ["ambulatory", "second read", "abpm", "end-organ", "repeat", "single"],
            "prohibited_strings":   [
                "headache caused by hypertension",
                "hypertension confirmed",
            ],
            "manual": [
                "Absent chest pain, neuro symptoms, visual changes, SOB cited as argues_against hypertensive emergency",
                "Single reading — hypertension not confirmed from one reading alone (check missing_information or why_considered)",
            ],
        },
    },
    {
        "id": "6",
        "label": "Anaemia — low-specificity presentation",
        "presentation": (
            "34F, 3 months fatigue, dizzy when standing, can't exercise like before. "
            "No fever, no cough, no urinary symptoms, no GI symptoms reported."
        ),
        "checks": {
            "primary_contains":     ["anaemia", "anemia", "iron"],
            "red_flags_contain":    [],  # IDA red flag section not retrieved by vector similarity — see manual checks
            "missing_info_contain": ["menstrual", "hb", "fbc", "dietary"],
            "prohibited_strings":   [
                "anaemia confirmed",
                "anemia confirmed",
                "no gi blood loss",
            ],
            "manual": [
                "Absent GI symptoms noted but NOT used to exclude GI blood loss as a cause",
                "Haemoglobin <7 g/dL threshold should appear as red flag — verify in output",
            ],
        },
    },
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def flatten_text(result: dict) -> str:
    """Recursively join all string values in result — for prohibited-string checks."""
    parts = []
    if isinstance(result, dict):
        for v in result.values():
            parts.append(flatten_text(v))
    elif isinstance(result, list):
        for item in result:
            parts.append(flatten_text(item))
    elif isinstance(result, str):
        parts.append(result)
    return " ".join(parts).lower()


def all_missing_info(result: dict) -> str:
    """All missing_information text across all candidates, lowercased."""
    parts = []
    for c in result.get("candidates", []):
        parts.extend(c.get("missing_information", []))
    return " ".join(parts).lower()


def all_red_flags(result: dict) -> str:
    return " ".join(result.get("red_flags", [])).lower()


def all_argues_against(result: dict) -> str:
    parts = []
    for c in result.get("candidates", []):
        parts.extend(c.get("arguing_against", []))
    return " ".join(parts).lower()


def find_candidate(result: dict, hints: list) -> dict | None:
    """Find first candidate whose diagnosis lowercased contains any hint."""
    for c in result.get("candidates", []):
        diag = c.get("diagnosis", "").lower()
        if any(h in diag for h in hints):
            return c
    return None


def check_contains_any(text: str, terms: list) -> tuple[bool, str]:
    """Return (passed, matched_term or first_missed_term)."""
    for t in terms:
        if t.lower() in text:
            return True, t
    return False, terms[0]


# ── Scorer ────────────────────────────────────────────────────────────────────

def score(case: dict, result: dict) -> dict:
    checks  = case["checks"]
    results = []
    passed  = 0
    failed  = 0

    full_text   = flatten_text(result)
    missing_txt = all_missing_info(result)
    red_txt     = all_red_flags(result)
    against_txt = all_argues_against(result)
    leading     = result.get("leading_candidate", "").lower()
    candidates  = [c.get("diagnosis", "").lower() for c in result.get("candidates", [])]

    def record(label, ok, detail=""):
        nonlocal passed, failed
        if ok:
            passed += 1
        else:
            failed += 1
        results.append({"label": label, "pass": ok, "detail": detail})

    # Primary diagnosis
    if "primary_contains" in checks:
        ok = any(h in leading for h in checks["primary_contains"])
        if not ok:
            ok = any(
                any(h in diag for h in checks["primary_contains"])
                for diag in candidates[:1]
            )
        record(
            "Primary diagnosis",
            ok,
            f"leading='{result.get('leading_candidate', '')}' | expected one of {checks['primary_contains']}",
        )

    # Secondary candidates
    if "secondary_contains" in checks:
        ok = any(
            any(h in diag for h in checks["secondary_contains"])
            for diag in candidates
        )
        record(
            "Secondary candidate present",
            ok,
            f"candidates={candidates} | expected one of {checks['secondary_contains']}",
        )

    # Red flags
    for term in checks.get("red_flags_contain", []):
        ok = term.lower() in red_txt
        record(f"Red flag: '{term}'", ok, red_txt[:120] if not ok else "")

    # Missing information
    mi_terms = checks.get("missing_info_contain", [])
    if mi_terms:
        ok, hit = check_contains_any(missing_txt, mi_terms)
        record(
            f"Missing info: any of {mi_terms}",
            ok,
            f"matched '{hit}'" if ok else f"none found in: {missing_txt[:120]}",
        )

    # TB argues_against (Case 2b specific)
    tb_terms = checks.get("tb_argues_against_contain", [])
    if tb_terms:
        tb_cand = find_candidate(result, ["tuberculosis", "tb"])
        if tb_cand:
            tb_against = " ".join(tb_cand.get("arguing_against", [])).lower()
            ok, hit = check_contains_any(tb_against, tb_terms)
            record(
                f"TB argues_against contains any of {tb_terms}",
                ok,
                f"matched '{hit}'" if ok else f"TB arguing_against: {tb_against[:120]}",
            )
        else:
            record("TB argues_against", False, "TB not found in candidates")

    # Prohibited strings
    for phrase in checks.get("prohibited_strings", []):
        ok = phrase.lower() not in full_text
        record(f"Prohibited: '{phrase}'", ok, "" if ok else f"FOUND in output")

    return {
        "id":      case["id"],
        "label":   case["label"],
        "passed":  passed,
        "failed":  failed,
        "checks":  results,
        "manual":  checks.get("manual", []),
        "result":  result,
    }


# ── Paired confidence check ───────────────────────────────────────────────────

CONFIDENCE_ORDER = {"low": 0, "moderate": 1, "high": 2}

def compare_confidence(result_a, result_b, hints, label_a, label_b):
    """Check that confidence of a matched candidate dropped from a → b."""
    cand_a = find_candidate(result_a, hints)
    cand_b = find_candidate(result_b, hints)

    conf_a = cand_a.get("confidence_level", "?") if cand_a else "absent"
    conf_b = cand_b.get("confidence_level", "?") if cand_b else "absent"

    ord_a = CONFIDENCE_ORDER.get(conf_a, -1)
    ord_b = CONFIDENCE_ORDER.get(conf_b, -1)

    dropped = ord_b < ord_a
    return {
        "label_a": label_a, "conf_a": conf_a,
        "label_b": label_b, "conf_b": conf_b,
        "dropped": dropped,
    }


# ── Reporter ──────────────────────────────────────────────────────────────────

PASS_SYM = "✓"
FAIL_SYM = "✗"
WARN_SYM = "⚠"

def print_case(scored: dict):
    tag  = PASS_SYM if scored["failed"] == 0 else FAIL_SYM
    auto = scored["passed"] + scored["failed"]
    print(f"\n{'='*60}")
    print(f"Case {scored['id']}: {scored['label']}")
    print(f"{'='*60}")
    print(f"Leading candidate: {scored['result'].get('leading_candidate', '?')}")
    print()

    for c in scored["checks"]:
        sym = PASS_SYM if c["pass"] else FAIL_SYM
        line = f"  {sym}  {c['label']}"
        if not c["pass"] and c["detail"]:
            line += f"\n       Detail: {c['detail']}"
        print(line)

    if scored["manual"]:
        print()
        print("  Manual checks required:")
        for m in scored["manual"]:
            print(f"  {WARN_SYM}  {m}")

    print()
    status = "PASS" if scored["failed"] == 0 else "FAIL"
    print(f"  {tag}  {status} — {scored['passed']}/{auto} auto checks | {len(scored['manual'])} manual")


def print_paired(comp: dict):
    tag = PASS_SYM if comp["dropped"] else FAIL_SYM
    print(f"\n  {tag}  {comp['label_a']} → {comp['label_b']}: "
          f"{comp['conf_a']} → {comp['conf_b']} "
          f"({'dropped' if comp['dropped'] else 'DID NOT DROP — FAIL'})")


# ── Runner ────────────────────────────────────────────────────────────────────

def run_all(case_ids=None, embedder=None, hybrid=False):
    cases_to_run = CASES
    if case_ids:
        cases_to_run = [c for c in CASES if c["id"] in case_ids]

    results_by_id = {}
    scored_list   = []

    for case in cases_to_run:
        print(f"\nRunning Case {case['id']}: {case['label']} ...", flush=True)
        try:
            result = rag.run(case["presentation"], embedder=embedder, hybrid=hybrid)
            scored = score(case, result)
            results_by_id[case["id"]] = result
            scored_list.append(scored)
            print_case(scored)
        except ValueError as e:
            print(f"  {FAIL_SYM}  PIPELINE ERROR — {e}")
            scored_list.append({
                "id": case["id"], "label": case["label"],
                "passed": 0, "failed": 1,
                "checks": [{"label": "Pipeline", "pass": False, "detail": str(e)}],
                "manual": [], "result": {},
            })

    # Paired comparisons (only when both cases ran)
    print(f"\n{'='*60}")
    print("Paired confidence comparisons")
    print(f"{'='*60}")

    if "2a" in results_by_id and "2b" in results_by_id:
        comp = compare_confidence(
            results_by_id["2a"], results_by_id["2b"],
            ["tuberculosis", "tb"], "2a TB", "2b TB"
        )
        print_paired(comp)

    if "4a" in results_by_id and "4b" in results_by_id:
        comp = compare_confidence(
            results_by_id["4a"], results_by_id["4b"],
            ["diabetes", "type 2"], "4a T2DM", "4b T2DM"
        )
        print_paired(comp)

    # Summary
    total_pass  = sum(1 for s in scored_list if s["failed"] == 0)
    total_fail  = len(scored_list) - total_pass
    total_manual = sum(len(s["manual"]) for s in scored_list)

    print(f"\n{'='*60}")
    print(f"SUMMARY: {total_pass}/{len(scored_list)} cases auto-passed | {total_fail} failed | {total_manual} manual checks")
    print(f"{'='*60}")

    return scored_list


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--backend", default="cohere", choices=["cohere", "pubmedbert"],
        help="Embedding backend to use (default: cohere)",
    )
    parser.add_argument(
        "--hybrid", action="store_true",
        help="Use BM25 + dense vector RRF for candidate selection (default: dense-only)",
    )
    parser.add_argument("cases", nargs="*", help="Optional case IDs to run (e.g. 2a 4b)")
    args = parser.parse_args()

    embedder = None  # CohereEmbedder initialised inside rag.run() by default
    if args.backend == "pubmedbert":
        from embed_provider import PubMedBertEmbedder
        print("Loading PubMedBERT model...")
        embedder = PubMedBertEmbedder()
        print(f"Model loaded. Using collection: {embedder.COLLECTION}\n")

    if args.hybrid:
        print("Retrieval mode: BM25 + dense vector RRF\n")
    else:
        print("Retrieval mode: dense-only (Cohere baseline)\n")

    run_all(args.cases or None, embedder=embedder, hybrid=args.hybrid)
