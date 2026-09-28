#!/usr/bin/env python3
"""
scripts/source_gather.py

Parallel source acquisition for CDS condition card authoring.
Scrapes MOH Vol 2 (local) and four Medscape pages simultaneously,
gates on content quality, reports 9-section coverage, and writes
a structured source file ready for card authoring.

Usage:
    python scripts/source_gather.py "Heart Failure"           # auto-detect Medscape ID
    python scripts/source_gather.py "Heart Failure" 163062    # supply ID explicitly
    python scripts/source_gather.py "Heart Failure" --min-chars 800
    python scripts/source_gather.py "Heart Failure" --output corpus/heart_failure/sources_raw.md

Outputs:
    corpus/<slug>/sources_raw.md  — structured source file with gate log + coverage report

Gates:
    FAIL (exit 1) — Firecrawl page < min_chars, no H2 structure, MOH section missing, file not written
    WARN (continue) — MOH section thin (<300 chars), expected headings absent from a page
    REPORT — 9-section coverage: which sections have evidence vs require synthesis

Requires in .env:
    FIRECRAWL_API_KEY
"""

from __future__ import annotations

import argparse
import io
import os
import re
import sys
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

import requests
from dotenv import load_dotenv

# ── Paths ──────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent
MOH_PATH = ROOT / "kenya_moh_vol2_2024.md"

# ── Medscape config ────────────────────────────────────────────────────────────

MEDSCAPE_BASE = "https://emedicine.medscape.com/article/{id}-{page}"
FIRECRAWL_SEARCH = "https://api.firecrawl.dev/v1/search"
MEDSCAPE_PAGES = ["overview", "clinical", "differential", "workup"]
_ARTICLE_ID_RE = re.compile(r"/article/(\d{5,7})-(?:overview|clinical|differential|workup)")

# Headings expected on each page — any one match confirms structure
EXPECTED_HEADINGS = {
    "overview":     ["Background", "Etiology", "Epidemiology", "Pathophysiology"],
    "clinical":     ["History", "Physical Examination", "Chief Complaint", "Presentation"],
    "differential": ["Differential", "Diagnoses", "Overview"],
    "workup":       ["Approach", "Lab", "Imaging", "Studies", "Considerations"],
}

DEFAULT_MIN_CHARS = 1000

# ── Card section → source mapping ─────────────────────────────────────────────

# Which Medscape page feeds which card sections (for dynamic coverage reporting)
MEDSCAPE_PAGE_SECTIONS: dict[str, list[str]] = {
    "clinical":     ["cardinal_symptoms", "associated_symptoms"],
    "overview":     ["predisposing_factors"],
    "differential": ["differentials"],
    "workup":       ["diagnostic_features", "confirms"],
}

# Source labels shown in coverage report
_SECTION_LABEL_FULL: dict[str, str] = {
    "cardinal_symptoms":    "Medscape clinical (History) + MOH",
    "associated_symptoms":  "Medscape clinical (Physical Examination) + MOH",
    "diagnostic_features":  "Medscape workup (Lab/Imaging) + MOH",
    "predisposing_factors": "Medscape overview (Etiology) + MOH",
    "differentials":        "Medscape differential + MOH",
    "confirms":             "Medscape workup",
}
_SECTION_LABEL_NO_MOH: dict[str, str] = {
    "cardinal_symptoms":    "Medscape clinical (History) — MOH missing",
    "associated_symptoms":  "Medscape clinical (Physical Examination) — MOH missing",
    "diagnostic_features":  "Medscape workup (Lab/Imaging) — MOH missing",
    "predisposing_factors": "Medscape overview (Etiology) — MOH missing",
    "differentials":        "Medscape differential — MOH missing",
    "confirms":             "Medscape workup — MOH missing",
}

# Sections that always require synthesis regardless of source quality
SYNTHESIS_SECTIONS: list[str] = [
    "typical_presentation",
    "argues_against",
    "red_flags",
    "diagnostic_context",
]

# Fixed display order matches the 9-section card schema
CARD_SECTION_ORDER: list[str] = [
    "cardinal_symptoms",
    "associated_symptoms",
    "diagnostic_features",
    "predisposing_factors",
    "typical_presentation",
    "differentials",
    "argues_against",
    "red_flags",
    "diagnostic_context",
    "confirms",
]

# ── MOH condition aliases ──────────────────────────────────────────────────────

MOH_ALIASES: dict[str, list[str]] = {
    "heart failure":                ["cardiac failure", "congestive heart failure", "chf"],
    "acute pulmonary oedema":       ["pulmonary oedema", "pulmonary edema", "apo"],
    "acute myocardial infarction":  ["myocardial infarction", "ami", "heart attack", "acs"],
    "acute rheumatic fever":        ["rheumatic fever", "arf"],
    "rheumatic heart disease":      ["rhd", "rheumatic valvular disease"],
    "deep vein thrombosis":         ["dvt", "venous thrombosis"],
    "pulmonary embolism":           ["pe", "pulmonary thromboembolism"],
    "hypertensive crisis":          ["hypertensive emergency", "hypertensive urgency"],
}


# ── Gate machinery ─────────────────────────────────────────────────────────────

class GateError(Exception):
    """Hard gate failure — triggers exit 1."""


_gate_log: list[tuple[str, str]] = []  # (level, message)


def _gate(level: str, msg: str) -> None:
    _gate_log.append((level, msg))


def gate_pass(msg: str) -> None:
    _gate(("PASS"), msg)


def gate_warn(msg: str) -> None:
    _gate("WARN", msg)


def gate_fail(msg: str) -> None:
    _gate("FAIL", msg)
    raise GateError(msg)


def print_gate_log() -> bool:
    """Print all gate results. Returns True if any FAIL present."""
    has_fail = False
    for level, msg in _gate_log:
        tag = {"PASS": "[PASS]", "WARN": "[WARN]", "FAIL": "[FAIL]"}[level]
        print(f"  {tag} {msg}")
        if level == "FAIL":
            has_fail = True
    return has_fail


# ── MOH extraction ─────────────────────────────────────────────────────────────

_NUMBERED_HEADING = re.compile(r"^(\d+(?:\.\d+)*)\s+\S")
_TOC_LINE = re.compile(r"\.{3,}")  # dotted leaders indicate a table-of-contents entry


def _is_moh_heading(line: str) -> bool:
    """True for markdown headings (#) and MOH plain-text numbered sections (3.5 ...)."""
    return line.startswith("#") or bool(_NUMBERED_HEADING.match(line))


def _moh_heading_depth(line: str) -> int:
    """Return depth: # → 1, ## → 2, 3.5 → 2, 3.5.1 → 3, 38.1 → 2."""
    if line.startswith("#"):
        return len(line) - len(line.lstrip("#"))
    m = _NUMBERED_HEADING.match(line)
    if m:
        return m.group(1).count(".") + 1
    return 0


def extract_moh_section(condition_name: str) -> tuple[str, str]:
    """
    Find condition section in MOH Vol 2 and extract full text.
    Returns (section_text, section_heading). Raises GateError if not found.

    MOH Vol 2 uses plain-text numbered sections (e.g. "3.5 Heart Failure"),
    not markdown headings — both formats are handled.
    """
    if not MOH_PATH.exists():
        gate_fail(f"MOH file not found: {MOH_PATH}")

    lines = MOH_PATH.read_text(encoding="utf-8").splitlines(keepends=True)

    canonical = condition_name.lower()
    aliases = MOH_ALIASES.get(canonical, [])
    search_terms = [canonical] + aliases

    # Pass 1: heading line (markdown or numbered, not TOC) containing a search term
    match_line: int | None = None
    for i, line in enumerate(lines):
        if not _is_moh_heading(line) or _TOC_LINE.search(line):
            continue
        for term in search_terms:
            if term in line.lower():
                match_line = i
                break
        if match_line is not None:
            break

    # Pass 2: any non-TOC line with a search term — walk back to nearest heading
    if match_line is None:
        for i, line in enumerate(lines):
            if _TOC_LINE.search(line):
                continue
            for term in search_terms:
                if term in line.lower():
                    for j in range(i, max(0, i - 150), -1):
                        if _is_moh_heading(lines[j]) and not _TOC_LINE.search(lines[j]):
                            match_line = j
                            break
                    break
            if match_line is not None:
                break

    if match_line is None:
        gate_fail(
            f"MOH: no section found for '{condition_name}'. "
            f"Tried aliases: {search_terms}. "
            f"Add an entry to MOH_ALIASES in source_gather.py or verify the condition name."
        )

    # Extract to next heading at same or higher level
    depth = _moh_heading_depth(lines[match_line])
    end_line = len(lines)
    for i in range(match_line + 1, len(lines)):
        if _is_moh_heading(lines[i]) and _moh_heading_depth(lines[i]) <= depth:
            end_line = i
            break

    section = "".join(lines[match_line:end_line])
    section_heading = lines[match_line].strip().lstrip("#").strip()
    char_count = len(section)

    if char_count < 300:
        gate_warn(
            f"MOH §'{section_heading}' — {char_count} chars. "
            f"Section is thin; Medscape becomes primary clinical source."
        )
    else:
        gate_pass(f"MOH §'{section_heading}' — {char_count:,} chars")

    return section, section_heading


# ── Medscape ID detection ──────────────────────────────────────────────────────

def detect_article_id(condition_name: str, api_key: str) -> int:
    """
    Use Firecrawl's native /v1/search to find the Medscape eMedicine article
    for the condition and extract the article ID from the first result URL.

    Returns the integer article ID. Raises GateError if none found.
    """
    query = f"site:emedicine.medscape.com {condition_name} overview"

    try:
        resp = requests.post(
            FIRECRAWL_SEARCH,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={"query": query, "limit": 5},
            timeout=60,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        gate_fail(f"Medscape search: HTTP error — {exc}")

    results: list[dict] = resp.json().get("data", [])

    for result in results:
        url = result.get("url", "")
        m = _ARTICLE_ID_RE.search(url)
        if m:
            article_id = int(m.group(1))
            gate_pass(
                f"Medscape search: detected article ID {article_id} "
                f"for '{condition_name}' ({url})"
            )
            return article_id

    gate_fail(
        f"Medscape search: no article ID found for '{condition_name}'. "
        f"Supply the ID manually as the second argument."
    )


# ── Medscape scraping ──────────────────────────────────────────────────────────

def _scrape_one(article_id: int, page: str, api_key: str, min_chars: int) -> tuple[str, str]:
    """
    Scrape a single Medscape page via Firecrawl.
    Retries up to 3 times on 429 with exponential backoff.
    Returns (page, markdown). Raises GateError on hard failure.
    """
    import time

    url = MEDSCAPE_BASE.format(id=article_id, page=page)
    last_exc: Exception | None = None

    for attempt in range(3):
        try:
            resp = requests.post(
                "https://api.firecrawl.dev/v1/scrape",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "url": url,
                    "formats": ["markdown"],
                    "onlyMainContent": True,
                },
                timeout=60,
            )
            if resp.status_code == 429:
                wait = 2 ** (attempt + 1)  # 2s, 4s, 8s
                time.sleep(wait)
                last_exc = requests.HTTPError(f"429 Too Many Requests (attempt {attempt + 1})")
                continue
            resp.raise_for_status()
            last_exc = None
            break
        except requests.RequestException as exc:
            last_exc = exc
            break  # non-429 errors don't benefit from retry

    if last_exc is not None:
        gate_fail(f"Medscape {page}: HTTP error — {last_exc}")

    md: str = resp.json().get("data", {}).get("markdown", "")

    # Hard gate: minimum content volume
    if len(md) < min_chars:
        gate_fail(
            f"Medscape {page}: {len(md)} chars received (threshold: {min_chars}). "
            f"Likely blocked or nav-only response. URL: {url}"
        )

    # Soft gate: expected heading structure
    expected = EXPECTED_HEADINGS.get(page, [])
    found = [h for h in expected if h.lower() in md.lower()]
    if not found:
        gate_warn(
            f"Medscape {page}: none of {expected} found in content. "
            f"Section mapping for this page may be incomplete."
        )
    else:
        gate_pass(f"Medscape {page}: {len(md):,} chars — headings found: {found}")

    return page, md


def scrape_medscape(article_id: int, api_key: str, min_chars: int) -> dict[str, str]:
    """
    Fire all 4 Medscape page requests in parallel.
    Returns {page: markdown} for pages that succeeded.
    Failed pages are recorded in _gate_log but do not abort the run —
    partial results are preserved so coverage report reflects reality.
    """
    results: dict[str, str] = {}

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(_scrape_one, article_id, page, api_key, min_chars): page
            for page in MEDSCAPE_PAGES
        }
        for future in as_completed(futures):
            try:
                page_name, md = future.result()
                results[page_name] = md
            except GateError:
                pass  # already recorded in _gate_log; coverage report will show ✗

    return results


# ── Output builders ────────────────────────────────────────────────────────────

def build_coverage_report(moh_ok: bool, scraped_pages: set[str]) -> str:
    """
    Dynamic coverage report — reflects which sources actually passed gates.
    Shows ✓ only when the contributing source succeeded; ✗ otherwise.
    """
    lines = ["## COVERAGE REPORT", ""]
    label_map = _SECTION_LABEL_FULL if moh_ok else _SECTION_LABEL_NO_MOH

    for section in CARD_SECTION_ORDER:
        if section in SYNTHESIS_SECTIONS:
            lines.append(f"  ✗  {section:<28} ← synthesis required")
            continue

        # Determine which Medscape page feeds this section
        contributing_page = next(
            (pg for pg, secs in MEDSCAPE_PAGE_SECTIONS.items() if section in secs),
            None,
        )
        page_ok = contributing_page in scraped_pages

        if page_ok:
            label = label_map.get(section, f"Medscape {contributing_page}")
            lines.append(f"  ✓  {section:<28} ← {label}")
        else:
            reason = (
                f"Medscape {contributing_page} failed — source missing"
                if contributing_page
                else "no source mapped"
            )
            lines.append(f"  ✗  {section:<28} ← {reason}")

    lines.append("")
    return "\n".join(lines)


def build_output(
    condition_name: str,
    article_id: int,
    moh_section: str,
    moh_heading: str,
    medscape: dict[str, str],
    coverage: str,
) -> str:
    today = date.today().isoformat()
    gate_summary = "\n".join(
        f"  {'[PASS]' if lvl == 'PASS' else '[WARN]' if lvl == 'WARN' else '[FAIL]'} {msg}"
        for lvl, msg in _gate_log
    )

    header = f"""# Source Gather: {condition_name}
Generated: {today}
Medscape Article ID: {article_id}
MOH Source: kenya_moh_vol2_2024.md

---

## GATE LOG

{gate_summary}

---

{coverage}
---

## MOH SOURCE — §{moh_heading}

{moh_section}

---

"""
    page_blocks: list[str] = []
    for page in MEDSCAPE_PAGES:
        md = medscape.get(page, "[NOT SCRAPED — see gate log]")
        url = MEDSCAPE_BASE.format(id=article_id, page=page)
        page_blocks.append(
            f"## MEDSCAPE — {page.upper()}\n\nSource: {url}\n\n{md}"
        )

    return header + "\n\n---\n\n".join(page_blocks)


# ── Helpers ────────────────────────────────────────────────────────────────────

def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    # Reconfigure stdout to UTF-8 so coverage symbols (✓ ✗) don't crash on Windows cp1252
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Gather and gate-check sources for a CDS condition card."
    )
    parser.add_argument("condition", help='Condition name, e.g. "Heart Failure"')
    parser.add_argument(
        "article_id",
        type=int,
        nargs="?",
        default=None,
        help="Medscape article ID (optional — auto-detected via search if omitted)",
    )
    parser.add_argument(
        "--min-chars",
        type=int,
        default=DEFAULT_MIN_CHARS,
        metavar="N",
        help=f"Minimum chars per Medscape page before hard fail (default: {DEFAULT_MIN_CHARS})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        metavar="PATH",
        help="Output path (default: corpus/<slug>/sources_raw.md)",
    )
    args = parser.parse_args()

    slug = slugify(args.condition)
    output_path: Path = args.output or (ROOT / "corpus" / slug / "sources_raw.md")

    load_dotenv(ROOT / ".env")
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        print("FAIL: FIRECRAWL_API_KEY not set in .env", file=sys.stderr)
        sys.exit(1)

    print(f"\nSource Gather: {args.condition}")
    print(f"Output:        {output_path}")
    print(f"Min chars:     {args.min_chars}\n")

    moh_section = ""
    moh_heading = ""
    medscape: dict[str, str] = {}
    hard_failed = False
    article_id: int | None = args.article_id

    # Auto-detect Medscape article ID if not supplied
    if article_id is None:
        print("=== MEDSCAPE ID DETECTION ===")
        try:
            article_id = detect_article_id(args.condition, api_key)
            print(f"  [PASS] Article ID: {article_id}\n")
        except GateError:
            hard_failed = True
            print(f"  [FAIL] Could not detect article ID — supply manually\n")

    # MOH extraction and Medscape scrape run concurrently
    # MOH is local so we run it in the main thread while Medscape scrapes in the pool
    try:
        moh_section, moh_heading = extract_moh_section(args.condition)
    except GateError:
        hard_failed = True

    if article_id is not None:
        try:
            medscape = scrape_medscape(article_id, api_key, args.min_chars)
        except GateError:
            hard_failed = True

    # Print gate log
    print("=== GATE RESULTS ===")
    has_fail = print_gate_log()
    if has_fail:
        hard_failed = True

    # Dynamic coverage report — reflects actual gate outcomes
    moh_ok = bool(moh_section)
    scraped_pages = set(medscape.keys())
    coverage = build_coverage_report(moh_ok, scraped_pages)
    print(f"\n{coverage}")

    # Write output — even on partial failure, write what was gathered
    if moh_section or medscape:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        content = build_output(
            args.condition, article_id or 0,
            moh_section, moh_heading,
            medscape, coverage,
        )
        output_path.write_text(content, encoding="utf-8")
        print(f"Written: {output_path}")
    else:
        print("Nothing written — all sources failed.")  # stdout, after gate log
        hard_failed = True

    sys.exit(1 if hard_failed else 0)


if __name__ == "__main__":
    main()
