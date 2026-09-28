"""
Check whether terms exist in symptom_vocabulary.md or conditions_vocabulary.md.

Usage:
    python scripts/vocab_check.py "term1" "term2" "term3"

Exit code 0 if all terms found, 1 if any missing.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SYMPTOM_VOC = ROOT / "symptoms_dictionary" / "symptom_vocabulary.md"
CONDITION_VOC = ROOT / "symptoms_dictionary" / "conditions_vocabulary.md"


def load_terms(path: Path) -> set[str]:
    terms = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("|") or stripped.startswith("-"):
            # Table rows and list items: extract the first cell / first token
            if stripped.startswith("|"):
                cell = stripped.split("|")[1].strip().lower()
                if cell and cell != "term" and cell != "---":
                    terms.add(cell)
            elif stripped.startswith("- "):
                terms.add(stripped[2:].strip().lower())
        else:
            terms.add(stripped.lower())
    return terms


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/vocab_check.py \"term1\" \"term2\"")
        sys.exit(1)

    symptom_terms = load_terms(SYMPTOM_VOC)
    condition_terms = load_terms(CONDITION_VOC)
    all_terms = symptom_terms | condition_terms

    missing = False
    for term in sys.argv[1:]:
        if term.lower() in all_terms:
            print(f"  OK  {term}")
        else:
            print(f"  XX  {term}  <- NOT FOUND")
            missing = True

    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()
