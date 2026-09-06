"""
RAG smoke tests for the three new condition cards:
  GERD, Functional dyspepsia, Typhoid fever

Run from cds/ root:
    python phase5/test_new_cards.py
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

CASES = [
    {
        "id": "GERD",
        "label": "GERD — classic heartburn + regurgitation",
        "presentation": (
            "44F, 8 months of burning in the chest after meals, worse when lying flat at night. "
            "Sour taste in the mouth, especially on bending. Partially relieved by antacids. "
            "Bloating after large meals. No weight loss. No difficulty swallowing. No vomiting of blood."
        ),
        "expect_leading": ["gerd", "gastro-oesoph", "reflux"],
        "expect_in_candidates": ["peptic ulcer", "dyspepsia"],
        "expect_not_leading": ["peptic ulcer", "typhoid", "malaria"],
    },
    {
        "id": "FD",
        "label": "Functional dyspepsia — epigastric discomfort + postprandial fullness",
        "presentation": (
            "31F, 6 months of recurrent epigastric discomfort, feels uncomfortably full after "
            "small meals, sometimes cannot finish eating. Nausea most mornings. Bloating and "
            "belching. No heartburn. No weight loss. No blood in stool. Stressful work situation. "
            "Endoscopy 3 months ago was reported as normal."
        ),
        "expect_leading": ["functional dyspepsia", "dyspepsia"],
        "expect_in_candidates": ["peptic ulcer", "gerd", "gastro-oesoph"],
        "expect_not_leading": ["peptic ulcer", "gastric cancer", "malaria"],
    },
    {
        "id": "TF",
        "label": "Typhoid fever — insidious fever, no diarrhoea",
        "presentation": (
            "22M, 9 days of gradually worsening fever and headache. Appetite gone, very weak. "
            "Mild abdominal discomfort, more constipated than usual. No rigors. No diarrhoea. "
            "Malaria RDT negative. Came from Nairobi but lives in Nakuru. "
            "No improvement on paracetamol."
        ),
        "expect_leading": ["typhoid"],
        "expect_in_candidates": ["malaria", "gastroenteritis"],
        "expect_not_leading": ["malaria", "pneumonia", "tuberculosis"],
    },
]

PASS = "✓"
FAIL = "✗"

def run_case(case):
    print(f"\n{'='*64}")
    print(f"Case {case['id']}: {case['label']}")
    print(f"{'='*64}")

    result = rag.run(case["presentation"])
    leading = result.get("leading_candidate", "").lower()
    candidates = [c.get("diagnosis", "").lower() for c in result.get("candidates", [])]

    print(f"Leading candidate : {result.get('leading_candidate', '?')}")
    print(f"All candidates    : {[c.get('diagnosis','?') for c in result.get('candidates', [])]}")
    print()

    checks = []

    # Leading diagnosis check
    ok = any(h in leading for h in case["expect_leading"])
    checks.append(ok)
    sym = PASS if ok else FAIL
    print(f"  {sym}  Leading is one of {case['expect_leading']!r}  →  got '{result.get('leading_candidate','?')}'")

    # Expected candidates present
    for term in case["expect_in_candidates"]:
        found = any(term in c for c in candidates)
        checks.append(found)
        sym = PASS if found else FAIL
        print(f"  {sym}  '{term}' in candidate list  →  {'yes' if found else 'NOT FOUND'}")

    # Unwanted leading
    bad_leading = any(h in leading for h in case["expect_not_leading"])
    checks.append(not bad_leading)
    sym = PASS if not bad_leading else FAIL
    print(f"  {sym}  Leading is NOT one of {case['expect_not_leading']!r}")

    # Red flags
    red_flags = result.get("red_flags", [])
    print(f"\n  Red flags ({len(red_flags)}):")
    for rf in red_flags:
        print(f"    - {rf}")

    # Missing info (leading candidate)
    cands = result.get("candidates", [])
    if cands:
        mi = cands[0].get("missing_information", [])
        print(f"\n  Missing info — leading candidate ({len(mi)}):")
        for m in mi:
            print(f"    - {m}")

    passed = sum(checks)
    total  = len(checks)
    tag    = PASS if passed == total else FAIL
    print(f"\n  {tag}  {passed}/{total} auto checks passed")

    return passed, total, result


if __name__ == "__main__":
    overall_pass = 0
    overall_total = 0

    for case in CASES:
        p, t, _ = run_case(case)
        overall_pass += p
        overall_total += t

    print(f"\n{'='*64}")
    print(f"TOTAL: {overall_pass}/{overall_total} checks passed across {len(CASES)} new-card tests")
    print(f"{'='*64}")
