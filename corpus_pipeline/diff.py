#!/usr/bin/env python3
"""
corpus_pipeline/diff.py

Content equivalence check: hand-authored symptoms_dictionary/*.md
vs generated corpus_pipeline/output/*/generated.md

Compares at the semantic level (parsed sections and frontmatter fields),
not raw text -- avoids false positives from YAML formatting differences
(e.g. single vs double quotes, inline vs block lists).

For each matched pair reports:
  OK      -- content equivalent after normalisation
  DIFFERS -- section prose differs; shows first diverging excerpt
  MISSING -- content in original not representable from condition.yaml
             (intro paragraph is the expected case -- flagged explicitly)

Usage:
  python corpus_pipeline/diff.py               # all migrated cards
  python corpus_pipeline/diff.py malaria       # single condition by name
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))

from ingest import parse_frontmatter, split_sections, SECTION_RE

ORIG_DIR  = _ROOT / "symptoms_dictionary"
GEN_DIR   = Path(__file__).parent / "output"

# ── Accepted normalization differences ───────────────────────────────────────
# Key: (condition, section, orig_hash, gen_hash) — exact diff matching.
# Matching DIFFERS are tagged ACCEPTED and shown but excluded from failure count.
# Fixture entries that match no actual diff are reported as STALE (gate failure).
_ACCEPTED_PATH = Path(__file__).parent / "accepted_diffs.json"

# Tracks which accepted entries were hit during a run (stale detection).
_matched_accepted: set[tuple[str, str, str, str]] = set()


def _hash(text: str) -> str:
    return hashlib.sha256(_norm(text).encode("utf-8")).hexdigest()[:16]


def _load_accepted_pairs() -> dict[tuple[str, str, str, str], str]:
    if not _ACCEPTED_PATH.exists():
        return {}
    data = json.loads(_ACCEPTED_PATH.read_text(encoding="utf-8"))
    result = {}
    for entry in data:
        key = (
            entry["condition"],
            entry["section"],
            entry.get("orig_hash", ""),
            entry.get("gen_hash", ""),
        )
        result[key] = entry.get("description", "")
    return result


ACCEPTED_PAIRS: dict[tuple[str, str, str, str], str] = _load_accepted_pairs()

# Section display name -> metadata key (mirrors ingest.py SECTION_KEY)
SECTION_KEY = {
    "Cardinal symptoms":                          "cardinal_symptoms",
    "Associated symptoms and signs":              "associated_symptoms",
    "Diagnostic features":                        "diagnostic_features",
    "Predisposing factors":                       "predisposing_factors",
    "Typical presentation":                       "typical_presentation",
    "Important differential diagnoses":           "differentials",
    "Features that argue against this diagnosis": "against",
    "Red flags":                                  "red_flags",
    "Diagnostic context":                         "diagnostic_context",
}

# Graph fields to compare term-by-term
GRAPH_FIELDS = [
    "cardinal_symptoms", "associated_symptoms", "risk_factors",
    "differentials", "argues_against", "red_flags", "confirms",
]

# Metadata fields to compare directly
META_FIELDS = ["condition", "icd11", "icd10", "category",
               "corpus_version", "schema_version", "review_status",
               "endemic_regions"]


# ── Text normalisation ────────────────────────────────────────────────────────

def _norm(text: str) -> str:
    """
    Normalise prose for comparison.
    Joins within-paragraph line breaks with a space so that hard-wrapped YAML
    block scalars compare equal to single-line Markdown prose.
    Preserves paragraph breaks (blank lines).
    """
    paragraphs = re.split(r"\n\s*\n", text.strip())
    joined = []
    for para in paragraphs:
        line = " ".join(l.strip() for l in para.splitlines() if l.strip())
        if line:
            joined.append(line)
    return "\n\n".join(joined)


def _excerpt(text: str, n: int = 120) -> str:
    flat = " ".join(text.split())
    return flat[:n] + ("..." if len(flat) > n else "")


# ── Parsing helpers ───────────────────────────────────────────────────────────

def _extract_intro(body: str) -> str:
    """Return text between the H1 line and the first section header."""
    # Strip the H1 line (first line starting with #)
    lines = body.splitlines(keepends=True)
    start = 0
    for i, line in enumerate(lines):
        if line.startswith("#"):
            start = i + 1
            break
    remaining = "".join(lines[start:]).strip()
    # Find first section header
    m = SECTION_RE.search(remaining)
    intro = remaining[: m.start()].strip() if m else remaining
    return intro


def _parse_sections(body: str, condition: str) -> dict[str, str]:
    """Return {display_heading: prose_text} for each section found."""
    chunks = split_sections(body, condition)
    # split_sections returns (heading, full_chunk_text); extract prose only
    result = {}
    for heading, full_text in chunks:
        # full_text = "<condition> — <heading>\n\n<prose>"
        parts = full_text.split("\n\n", 1)
        prose = parts[1] if len(parts) > 1 else ""
        result[heading] = prose
    return result


def _parse_graph(meta: dict) -> dict[str, list[str]]:
    """Extract graph field as lists of raw term strings."""
    raw = meta.get("graph", {})
    result = {}
    for field_name in GRAPH_FIELDS:
        val = raw.get(field_name, [])
        # Hand-authored cards may have inline YAML lists (parsed as list by PyYAML)
        if isinstance(val, list):
            result[field_name] = [str(t).strip() for t in val]
        else:
            result[field_name] = []
    return result


# ── Diff result ───────────────────────────────────────────────────────────────

@dataclass
class DiffResult:
    condition: str
    orig_path: Path
    gen_path: Path
    issues: list[str] = field(default_factory=list)
    ok_count: int = 0

    def add_ok(self, label: str):
        self.ok_count += 1

    def add_issue(self, tag: str, location: str, msg: str):
        self.issues.append(f"  {tag} [{location}] {msg}")

    def print(self):
        print(f"\n=== {self.condition} ===")
        try:
            print(f"  original:  {self.orig_path.relative_to(_ROOT)}")
            print(f"  generated: {self.gen_path.relative_to(_ROOT)}")
        except ValueError:
            print(f"  original:  {self.orig_path}")
            print(f"  generated: {self.gen_path}")

        if not self.issues:
            print(f"  OK -- all {self.ok_count} checks passed")
        else:
            for line in self.issues:
                print(line)
            print(f"  ({self.ok_count} checks OK, {len(self.issues)} issue(s))")


# ── Core comparison ───────────────────────────────────────────────────────────

def diff_pair(orig_path: Path, gen_path: Path) -> DiffResult:
    orig_text = orig_path.read_text(encoding="utf-8")
    gen_text  = gen_path.read_text(encoding="utf-8")

    orig_meta, orig_body = parse_frontmatter(orig_text)
    gen_meta,  gen_body  = parse_frontmatter(gen_text)

    condition = orig_meta.get("condition", orig_path.stem)
    result = DiffResult(condition=condition, orig_path=orig_path, gen_path=gen_path)

    # ── Intro paragraph ──────────────────────────────────────────────────────
    intro = _extract_intro(orig_body)
    if intro:
        result.add_issue(
            "MISSING", "intro",
            f"Free-text intro paragraph not stored in condition.yaml "
            f"(expected gap) -- '{_excerpt(intro, 80)}'"
        )
    else:
        result.add_ok("intro")

    # ── Metadata fields ──────────────────────────────────────────────────────
    for f in META_FIELDS:
        orig_val = orig_meta.get(f)
        gen_val  = gen_meta.get(f)
        # Normalise empty string / None
        if orig_val == "":
            orig_val = None
        if gen_val == "":
            gen_val = None
        # Lists: order-sensitive for endemic_regions (fixed geography order)
        if orig_val == gen_val:
            result.add_ok(f"meta:{f}")
        elif f == "category" and "/" in str(orig_val or ""):
            # Hand-authored cards had invalid compound category values.
            # Migration corrected to single primary category — expected correction.
            result.add_issue(
                "CORRECTED", f"meta:{f}",
                f"original={orig_val!r} (invalid compound) -> generated={gen_val!r}"
            )
        else:
            result.add_issue(
                "DIFFERS", f"meta:{f}",
                f"original={orig_val!r}  generated={gen_val!r}"
            )

    # ── Environmental signals ────────────────────────────────────────────────
    orig_sigs = orig_meta.get("environmental_signals", [])
    gen_sigs  = gen_meta.get("environmental_signals", [])
    if len(orig_sigs) != len(gen_sigs):
        result.add_issue(
            "DIFFERS", "environmental_signals",
            f"signal count: original={len(orig_sigs)}  generated={len(gen_sigs)}"
        )
    else:
        for i, (o, g) in enumerate(zip(orig_sigs, gen_sigs)):
            sig_name = o.get("signal", f"[{i}]")
            # Compare each sub-field
            for sub in ("signal", "effect_type", "effect_direction",
                        "strength", "confidence", "causal_distance",
                        "evidence_type", "seasonal_basis"):
                if o.get(sub) != g.get(sub):
                    result.add_issue(
                        "DIFFERS", f"signal[{sig_name}].{sub}",
                        f"original={o.get(sub)!r}  generated={g.get(sub)!r}"
                    )
                else:
                    result.add_ok(f"signal:{sig_name}.{sub}")
            # Pathways and regions as sets (order not significant)
            for sub in ("pathways", "regions"):
                o_set = set(o.get(sub, []))
                g_set = set(g.get(sub, []))
                if o_set != g_set:
                    result.add_issue(
                        "DIFFERS", f"signal[{sig_name}].{sub}",
                        f"original={sorted(o_set)}  generated={sorted(g_set)}"
                    )
                else:
                    result.add_ok(f"signal:{sig_name}.{sub}")

    # ── Graph terms ──────────────────────────────────────────────────────────
    orig_graph = _parse_graph(orig_meta)
    gen_graph  = _parse_graph(gen_meta)

    for gf in GRAPH_FIELDS:
        orig_terms = orig_graph.get(gf, [])
        gen_terms  = gen_graph.get(gf, [])
        orig_set = {t.lower() for t in orig_terms}
        gen_set  = {t.lower() for t in gen_terms}
        if orig_set == gen_set:
            result.add_ok(f"graph:{gf}")
        else:
            missing = sorted(orig_set - gen_set)
            extra   = sorted(gen_set  - orig_set)
            msg = ""
            if missing:
                msg += f"missing from generated: {missing}  "
            if extra:
                msg += f"extra in generated: {extra}"
            result.add_issue("DIFFERS", f"graph:{gf}", msg.strip())

    # ── Section prose ────────────────────────────────────────────────────────
    orig_sections = _parse_sections(orig_body, condition)
    gen_sections  = _parse_sections(gen_body,  condition)

    for heading in SECTION_KEY:
        orig_prose = _norm(orig_sections.get(heading, ""))
        gen_prose  = _norm(gen_sections.get(heading, ""))

        if not orig_prose and not gen_prose:
            result.add_ok(f"section:{SECTION_KEY[heading]}")
        elif not gen_prose:
            result.add_issue(
                "MISSING", f"section:{SECTION_KEY[heading]}",
                f"Section present in original but empty in generated"
            )
        elif not orig_prose:
            result.add_issue(
                "EXTRA", f"section:{SECTION_KEY[heading]}",
                f"Section present in generated but empty in original"
            )
        elif orig_prose == gen_prose:
            result.add_ok(f"section:{SECTION_KEY[heading]}")
        else:
            # Find first differing line, then first differing character within that line
            o_lines = orig_prose.splitlines()
            g_lines = gen_prose.splitlines()
            diff_line = next(
                (i for i, (a, b) in enumerate(zip(o_lines, g_lines)) if a != b),
                min(len(o_lines), len(g_lines))
            )
            o_line = o_lines[diff_line] if diff_line < len(o_lines) else ""
            g_line = g_lines[diff_line] if diff_line < len(g_lines) else ""
            ml = min(len(o_line), len(g_line))
            char_pos = next((i for i in range(ml) if o_line[i] != g_line[i]), ml)
            start = max(0, char_pos - 20)
            orig_exc = _excerpt(o_line[start:], 100)
            gen_exc  = _excerpt(g_line[start:], 100)
            sec_key = SECTION_KEY[heading]
            oh = _hash(orig_prose)
            gh = _hash(gen_prose)
            accept_key = (condition, sec_key, oh, gh)
            if accept_key in ACCEPTED_PAIRS:
                tag = "ACCEPTED"
                _matched_accepted.add(accept_key)
            else:
                tag = "DIFFERS"
            result.add_issue(
                tag, f"section:{sec_key}",
                f"para {diff_line + 1} char ~{char_pos}:\n"
                f"    original:  {orig_exc}\n"
                f"    generated: {gen_exc}"
            )

    return result


# ── Pair discovery ────────────────────────────────────────────────────────────

def _find_pairs(name_filter: str | None = None) -> list[tuple[Path, Path]]:
    """
    Match corpus/<name>/condition.yaml -> generated.md + symptoms_dictionary/<name>.md
    Returns (orig_md, generated_md) pairs where both files exist.
    """
    pairs = []
    corpus_dir = _ROOT / "corpus"
    for yaml_path in sorted(corpus_dir.rglob("condition.yaml")):
        name = yaml_path.parent.name
        if name_filter and name != name_filter:
            continue
        orig_md = ORIG_DIR / f"{name}.md"
        gen_md  = GEN_DIR / name / "generated.md"
        if not orig_md.exists():
            print(f"  SKIP {name}: no matching {orig_md.name} in symptoms_dictionary/")
            continue
        if not gen_md.exists():
            print(f"  SKIP {name}: generated.md not found — run markdown_gen.py first")
            continue
        pairs.append((orig_md, gen_md))
    return pairs


# ── Fixture generation ────────────────────────────────────────────────────────

def _gen_fixture(pairs: list[tuple[Path, Path]]) -> int:
    """
    Regenerate accepted_diffs.json with orig_hash/gen_hash populated.
    Merges hashes into existing entries (matched by condition+section);
    adds new entries for any DIFFERS not already in the fixture.
    Run once after Gate 1 sign-off; re-run if condition.yaml prose changes.
    """
    existing: dict[tuple[str, str], dict] = {}
    if _ACCEPTED_PATH.exists():
        data = json.loads(_ACCEPTED_PATH.read_text(encoding="utf-8"))
        for entry in data:
            existing[(entry["condition"], entry["section"])] = entry

    new_entries = []
    for orig_md, gen_md in pairs:
        orig_text = orig_md.read_text(encoding="utf-8")
        gen_text  = gen_md.read_text(encoding="utf-8")
        orig_meta, orig_body = parse_frontmatter(orig_text)
        gen_meta,  gen_body  = parse_frontmatter(gen_text)
        condition = orig_meta.get("condition", orig_md.stem)
        orig_sections = _parse_sections(orig_body, condition)
        gen_sections  = _parse_sections(gen_body,  condition)

        for heading in SECTION_KEY:
            orig_prose = _norm(orig_sections.get(heading, ""))
            gen_prose  = _norm(gen_sections.get(heading, ""))
            if orig_prose and gen_prose and orig_prose != gen_prose:
                sec_key = SECTION_KEY[heading]
                oh = _hash(orig_prose)
                gh = _hash(gen_prose)
                base = dict(existing.get((condition, sec_key), {
                    "condition":   condition,
                    "section":     sec_key,
                    "category":    "unknown",
                    "description": "",
                }))
                base["condition"]  = condition
                base["section"]    = sec_key
                base["orig_hash"]  = oh
                base["gen_hash"]   = gh
                new_entries.append(base)

    _ACCEPTED_PATH.write_text(
        json.dumps(new_entries, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Written {_ACCEPTED_PATH.name} -- {len(new_entries)} entries with hashes.")
    return 0


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    args = sys.argv[1:]
    gen_fixture = "--gen-fixture" in args
    name_filter = next((a for a in args if not a.startswith("--")), None)

    pairs = _find_pairs(name_filter)
    if not pairs:
        print("No matched pairs found.")
        return 1

    if gen_fixture:
        return _gen_fixture(pairs)

    total_issues = 0
    results: list[DiffResult] = []

    for orig_md, gen_md in pairs:
        r = diff_pair(orig_md, gen_md)
        r.print()
        total_issues += len(r.issues)
        results.append(r)

    # Summary
    expected = sum(
        1 for r in results
        for i in r.issues
        if "MISSING [intro]" in i
        or i.strip().startswith("CORRECTED")
        or i.strip().startswith("ACCEPTED")
    )
    real_issues = total_issues - expected

    # Stale fixture detection — any accepted entry that matched no actual diff
    stale = set(ACCEPTED_PAIRS.keys()) - _matched_accepted
    stale_count = len(stale)
    if stale_count:
        print(f"\nSTALE fixture entries ({stale_count}) -- no matching diff found:")
        for cond, sec, oh, gh in sorted(stale):
            print(f"  {cond} / {sec}  (orig:{oh} gen:{gh})")
        print("  Run --gen-fixture to refresh, or remove the entry if the diff is resolved.")

    print(f"\nSummary: {len(pairs)} card(s)  "
          f"{total_issues} issue(s) total  "
          f"({expected} expected/corrected/accepted,  "
          f"{real_issues} unexpected,  "
          f"{stale_count} stale)")

    return 0 if (real_issues == 0 and stale_count == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
