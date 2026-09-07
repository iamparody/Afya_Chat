"""
Phase 8 disambiguation evaluation harness.

Three checks per ambiguous case:
  A. is_ambiguous() fires on the initial result
  B. get_discriminating_questions() returns a non-empty list
  C. Enriched re-run shifts the leading candidate toward expected diagnosis

One negative case:
  D. is_ambiguous() correctly returns False for a high-confidence result

Gate: 3/4 ambiguous cases pass all three checks + negative case correct.

Usage:
    python phase8/evaluate_disambiguation.py           # all cases
    python phase8/evaluate_disambiguation.py d1 d3     # specific cases
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "phase5"))
sys.path.insert(0, str(ROOT / "phase8"))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import rag
from disambiguate import is_ambiguous, get_discriminating_questions, enrich_presentation


# ── Case definitions ──────────────────────────────────────────────────────────

CASES = [
    {
        "id": "d1",
        "label": "Upper GI overlap — PUD / GORD / Functional dyspepsia",
        "presentation": (
            "F/28. Epigastric discomfort x3/52, nausea, occasional retrosternal burning. "
            "No vomiting, no PR bleeding, no weight loss. No NSAID use reported."
        ),
        "expect_ambiguous": True,
        "enrichment": {
            "Heartburn or acid regurgitation": (
                "Present — heartburn and acid regurgitation, worse on lying flat and at night."
            ),
        },
        "expect_enriched_leads": ["gord", "reflux", "gastro-oesophageal"],
    },
    {
        "id": "d2",
        "label": "Lower abdominal overlap — UTI / AGE",
        "presentation": (
            "F/26. Fever x2/7, nausea, lower abdominal pain and cramping. "
            "Weakness. No urinary symptoms volunteered."
        ),
        "expect_ambiguous": True,
        "enrichment": {
            "Urinary symptoms": (
                "Dysuria and urinary frequency present on direct questioning. "
                "No diarrhoea. No vomiting."
            ),
        },
        "expect_enriched_leads": ["uti", "urinary"],
    },
    {
        "id": "d3",
        "label": "Early undifferentiated fever — Malaria / Dengue",
        "presentation": (
            "M/28. Fever x2/7, severe headache, malaise, myalgia. "
            "Lives in Mombasa coastal area. No rash. No cough. No abdominal pain."
        ),
        "expect_ambiguous": True,
        "enrichment": {
            "Retro-orbital pain and rash": (
                "Severe retro-orbital pain. Maculopapular rash appeared today. "
                "No rigors or chills. RDT negative."
            ),
        },
        "expect_enriched_leads": ["dengue"],
    },
    {
        "id": "d4",
        "label": "Negative — Diabetes full triad (disambiguation must not fire)",
        "presentation": (
            "51M, months of fatigue, very thirsty all the time, urinating a lot more "
            "than usual. Blurred vision sometimes. No fever, no acute illness."
        ),
        "expect_ambiguous": False,
        "enrichment": {},
        "expect_enriched_leads": [],
    },
    {
        "id": "d5",
        "label": "Fever in endemic area — Malaria / Typhoid",
        "presentation": (
            "M/32. Fever x4/7, headache, anorexia, mild abdominal discomfort. "
            "Lives in Kisumu. No rash. No rigors. No cough. No diarrhoea."
        ),
        "expect_ambiguous": True,
        "enrichment": {
            "Malaria RDT result": (
                "RDT negative. Step-wise fever pattern noted. Relative bradycardia present. "
                "No rigors or chills reported."
            ),
        },
        "expect_enriched_leads": ["typhoid"],
    },
]


# ── Scorer ────────────────────────────────────────────────────────────────────

PASS_SYM = "✓"
FAIL_SYM = "✗"
WARN_SYM = "⚠"

CONF_ORDER = {"low": 0, "moderate": 1, "high": 2}


def _leading(result: dict) -> str:
    return result.get("leading_candidate", "").lower()


def _leading_confidence(result: dict) -> str:
    lead = result.get("leading_candidate", "")
    for c in result.get("candidates", []):
        if c.get("diagnosis", "") == lead:
            return c.get("confidence_level", "")
    return ""


def score(case: dict, initial: dict, enriched: dict | None) -> dict:
    checks = []
    passed = 0
    failed = 0

    def record(label: str, ok: bool, detail: str = ""):
        nonlocal passed, failed
        passed += ok
        failed += (not ok)
        checks.append({"label": label, "pass": ok, "detail": detail})

    expect_ambiguous = case["expect_ambiguous"]

    # ── Check A: ambiguity trigger ────────────────────────────────────────────
    fired = is_ambiguous(initial)
    if expect_ambiguous:
        record(
            "A. is_ambiguous() fires",
            fired,
            f"leading={initial.get('leading_candidate', '?')} "
            f"conf={_leading_confidence(initial)}",
        )
    else:
        record(
            "A. is_ambiguous() correctly suppressed",
            not fired,
            f"leading={initial.get('leading_candidate', '?')} "
            f"conf={_leading_confidence(initial)}",
        )

    if not expect_ambiguous:
        return {"id": case["id"], "label": case["label"],
                "passed": passed, "failed": failed, "checks": checks,
                "initial": initial, "enriched": None}

    # ── Check B: discriminating questions generated ───────────────────────────
    questions = get_discriminating_questions(initial)
    record(
        "B. Discriminating questions generated",
        bool(questions),
        f"{len(questions)} questions: {questions[:2]}" if questions else "empty list returned",
    )

    # ── Check C: enriched result shifts toward expected lead ──────────────────
    if enriched is not None and case["expect_enriched_leads"]:
        new_lead = _leading(enriched)
        matched  = any(h in new_lead for h in case["expect_enriched_leads"])
        old_lead = _leading(initial)
        old_conf = _leading_confidence(initial)
        new_conf = _leading_confidence(enriched)
        record(
            f"C. Enriched lead → one of {case['expect_enriched_leads']}",
            matched,
            f"before='{old_lead}' ({old_conf}) → after='{new_lead}' ({new_conf})",
        )
    elif enriched is None:
        record("C. Enriched re-run skipped (ambiguity did not fire)", False,
               "Check A failed — enrichment not attempted")

    return {
        "id":      case["id"],
        "label":   case["label"],
        "passed":  passed,
        "failed":  failed,
        "checks":  checks,
        "initial": initial,
        "enriched": enriched,
    }


# ── Reporter ──────────────────────────────────────────────────────────────────

def print_case(scored: dict):
    auto  = scored["passed"] + scored["failed"]
    tag   = PASS_SYM if scored["failed"] == 0 else FAIL_SYM
    print(f"\n{'='*60}")
    print(f"Case {scored['id']}: {scored['label']}")
    print(f"{'='*60}")

    initial = scored["initial"]
    print(f"Initial lead:  {initial.get('leading_candidate', '?')} "
          f"({_leading_confidence(initial)})")
    qs = get_discriminating_questions(initial)
    print(f"Questions:     {qs if qs else '— none —'}")

    enriched = scored.get("enriched")
    if enriched:
        print(f"Enriched lead: {enriched.get('leading_candidate', '?')} "
              f"({_leading_confidence(enriched)})")
    print()

    for c in scored["checks"]:
        sym  = PASS_SYM if c["pass"] else FAIL_SYM
        line = f"  {sym}  {c['label']}"
        if c["detail"]:
            line += f"\n       {c['detail']}"
        print(line)

    print()
    status = "PASS" if scored["failed"] == 0 else "FAIL"
    print(f"  {tag}  {status} — {scored['passed']}/{auto} checks passed")


# ── Runner ────────────────────────────────────────────────────────────────────

def run_all(case_ids=None):
    cases_to_run = CASES
    if case_ids:
        cases_to_run = [c for c in CASES if c["id"] in case_ids]

    scored_list = []

    for case in cases_to_run:
        print(f"\nRunning {case['id']}: {case['label']} ...", flush=True)

        try:
            initial = rag.run(case["presentation"])
        except Exception as e:
            print(f"  {FAIL_SYM}  PIPELINE ERROR (initial run) — {e}")
            scored_list.append({
                "id": case["id"], "label": case["label"],
                "passed": 0, "failed": 1,
                "checks": [{"label": "Pipeline", "pass": False, "detail": str(e)}],
                "initial": {}, "enriched": None,
            })
            continue

        enriched_result = None
        if case["expect_ambiguous"] and is_ambiguous(initial) and case["enrichment"]:
            try:
                enriched_presentation = enrich_presentation(
                    case["presentation"], case["enrichment"]
                )
                enriched_result = rag.run(enriched_presentation)
            except Exception as e:
                print(f"  {WARN_SYM}  PIPELINE ERROR (enriched run) — {e}")

        scored = score(case, initial, enriched_result)
        scored_list.append(scored)
        print_case(scored)

    # ── Summary ───────────────────────────────────────────────────────────────
    total_pass  = sum(1 for s in scored_list if s["failed"] == 0)
    total_cases = len(scored_list)

    print(f"\n{'='*60}")
    print(f"SUMMARY: {total_pass}/{total_cases} cases fully passed")
    print(f"{'='*60}")

    if not case_ids:
        # Gate: 3/4 ambiguous + 1 negative = at minimum 4/5 total must pass
        THRESHOLD = 4
        if total_pass >= THRESHOLD:
            print(f"\nGATE PASS — {total_pass}/{total_cases} >= {THRESHOLD} required.")
        else:
            print(f"\nGATE FAIL — {total_pass}/{total_cases} < {THRESHOLD} required.")
            sys.exit(1)

    return scored_list


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("cases", nargs="*", help="Optional case IDs (e.g. d1 d3)")
    args = parser.parse_args()
    run_all(args.cases or None)
