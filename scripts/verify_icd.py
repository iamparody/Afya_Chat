#!/usr/bin/env python3
"""
scripts/verify_icd.py

Deterministic ICD-11 verification via WHO ICD-11 API.
Reads condition.yaml, queries the WHO API by condition name,
resolves the official code and title, updates the card in-place,
and sets icd_verified: true.

The script — not the author, not the LLM — is the authority on ICD-11 codes.

Usage:
  python scripts/verify_icd.py corpus/leptospirosis/condition.yaml
  python scripts/verify_icd.py corpus/leptospirosis/condition.yaml --search "Leptospirosis"
  python scripts/verify_icd.py corpus/   # all cards

Requires in .env:
  WHO_ICD_CLIENT_ID
  WHO_ICD_CLIENT_SECRET
"""

from __future__ import annotations

import argparse
import html
import os
import re
import sys
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv

# Force UTF-8 output on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_ROOT = Path(__file__).parent.parent
load_dotenv(_ROOT / ".env")

CLIENT_ID     = os.getenv("WHO_ICD_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("WHO_ICD_CLIENT_SECRET", "")

TOKEN_URL  = "https://icdaccessmanagement.who.int/connect/token"
SEARCH_URL = "https://id.who.int/icd/release/11/2024-01/mms/search"

_API_HEADERS = {
    "Accept":          "application/json",
    "Accept-Language": "en",
    "API-Version":     "v2",
}


# ── WHO API ───────────────────────────────────────────────────────────────────

def get_token() -> str:
    resp = requests.post(TOKEN_URL, data={
        "grant_type":    "client_credentials",
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope":         "icdapi_access",
    }, timeout=30)
    resp.raise_for_status()
    return resp.json()["access_token"]


def search_icd(term: str, token: str) -> list[dict]:
    headers = {**_API_HEADERS, "Authorization": f"Bearer {token}"}
    resp = requests.get(
        SEARCH_URL,
        params={"q": term, "subtreeFilterUsage": "includedChildren"},
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("error"):
        raise RuntimeError(f"WHO API error: {data.get('errorMessage')}")
    return data.get("destinationEntities") or []


# ── Match rule ────────────────────────────────────────────────────────────────

def _clean_title(raw: str) -> str:
    """Strip HTML tags and decode entities from WHO API title strings."""
    cleaned = re.sub(r"<[^>]+>", "", raw)
    return html.unescape(cleaned).strip()


def pick_exact(entities: list[dict], term: str) -> dict | None:
    """
    Return the single entity whose title exactly matches term (case-insensitive).
    Extension/postcoordination codes (containing & or starting with X) are excluded.
    Returns None if zero or >1 exact matches.
    """
    def is_base_code(code: str) -> bool:
        return "&" not in code and not code.startswith("X")

    exact = [
        e for e in entities
        if _clean_title(e.get("title", "")).lower() == term.strip().lower()
        and is_base_code(str(e.get("theCode", "")))
    ]
    return exact[0] if len(exact) == 1 else None


# ── YAML in-place update ──────────────────────────────────────────────────────

def update_card(path: Path, code: str, title: str, uri: str) -> None:
    """
    Update icd11, icd_title, icd_entity_uri, and icd_verified in-place.
    Uses regex line replacement to preserve all other formatting and comments.
    """
    text = path.read_text(encoding="utf-8")

    # Update icd11 code
    text = re.sub(r"^icd11:.*$", f"icd11: {code}", text, flags=re.MULTILINE)

    # Add or update icd_title (after icd11 line)
    if re.search(r"^icd_title:", text, re.MULTILINE):
        text = re.sub(r"^icd_title:.*$", f'icd_title: "{title}"', text, flags=re.MULTILINE)
    else:
        text = re.sub(
            r"^(icd11:.*\n)",
            lambda m: m.group(0) + f'icd_title: "{title}"\n',
            text, flags=re.MULTILINE, count=1,
        )

    # Add or update icd_entity_uri (after icd_title line)
    if re.search(r"^icd_entity_uri:", text, re.MULTILINE):
        text = re.sub(r"^icd_entity_uri:.*$", f'icd_entity_uri: "{uri}"', text, flags=re.MULTILINE)
    else:
        text = re.sub(
            r"^(icd_title:.*\n)",
            lambda m: m.group(0) + f'icd_entity_uri: "{uri}"\n',
            text, flags=re.MULTILINE, count=1,
        )

    # Set icd_verified: true
    text = re.sub(r"^icd_verified:.*$", "icd_verified: true", text, flags=re.MULTILINE)

    path.write_text(text, encoding="utf-8")


# ── Per-card verification ─────────────────────────────────────────────────────

def verify_card(
    yaml_path: Path,
    token: str,
    search_term: str | None = None,
) -> tuple[bool, str]:
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    condition = data.get("condition", "")
    # Priority: CLI --search > card's icd_search_term field > condition name
    term = search_term or data.get("icd_search_term") or condition

    term_display = f"'{term}'" + (f" (card: '{condition}')" if term != condition else "")
    print(f"  Search: {term_display} ... ", end="", flush=True)

    entities = search_icd(term, token)

    if not entities:
        print("NO RESULTS")
        return False, f"No WHO API results for '{term}'"

    entity = pick_exact(entities, term)

    if entity is None:
        candidates = [
            f"    {e.get('theCode','?'):12}  {_clean_title(e.get('title','?'))}"
            for e in entities[:8]
            if "&" not in str(e.get("theCode", ""))
        ]
        print(f"NO EXACT MATCH  ({len(entities)} results)")
        print("  Candidates:")
        print("\n".join(candidates))
        return False, f"No exact title match for '{term}' — re-run with --search <exact_who_title>"

    code  = entity["theCode"]
    title = _clean_title(entity["title"])
    uri   = entity["id"]

    print(f"MATCH → {code}  {title}")
    update_card(yaml_path, code, title, uri)
    return True, f"{code} — {title}"


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    if not CLIENT_ID or not CLIENT_SECRET:
        print(
            "ERROR: WHO_ICD_CLIENT_ID and WHO_ICD_CLIENT_SECRET must be set in .env",
            file=sys.stderr,
        )
        return 1

    parser = argparse.ArgumentParser(description="WHO ICD-11 verification utility")
    parser.add_argument("target", help="Path to condition.yaml or corpus/ directory")
    parser.add_argument("--search", metavar="TERM",
                        help="Override search term (default: condition name from YAML)")
    args = parser.parse_args()

    target = Path(args.target)
    if not target.exists():
        print(f"Path not found: {target}", file=sys.stderr)
        return 1

    yaml_files = [target] if target.is_file() else sorted(target.rglob("condition.yaml"))
    if not yaml_files:
        print("No condition.yaml files found.", file=sys.stderr)
        return 1

    # --search only valid for single-card runs
    if args.search and len(yaml_files) > 1:
        print("ERROR: --search can only be used with a single card path.", file=sys.stderr)
        return 1

    print("Authenticating with WHO ICD-11 API ... ", end="", flush=True)
    try:
        token = get_token()
    except Exception as exc:
        print(f"FAILED\n{exc}", file=sys.stderr)
        return 1
    print("OK\n")

    failures: list[tuple[str, str]] = []

    for yaml_path in yaml_files:
        try:
            rel = yaml_path.relative_to(_ROOT)
        except ValueError:
            rel = yaml_path
        print(f"{rel}")
        ok, msg = verify_card(yaml_path, token, args.search if len(yaml_files) == 1 else None)
        if not ok:
            failures.append((str(rel), msg))
        print()

    print("-" * 60)
    print(f"Verified: {len(yaml_files) - len(failures)}/{len(yaml_files)}")
    if failures:
        print(f"\nFailed ({len(failures)}) — resolve manually with --search <term>:")
        for path, msg in failures:
            print(f"  {path}")
            print(f"    {msg}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
