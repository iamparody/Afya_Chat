"""
Phase 9 CHIRPS adjudication: Kisumu (lake_basin) and Mombasa (coast) discrepancies.

Adds CHIRPS v2.0 as the third source to the two cases left unresolved by the
initial Open-Meteo vs NASA POWER/MERRA-2 comparison (validation_findings.md):

  Kisumu   post-long-rains 2024-07-01: ERA5-Land 43mm vs MERRA-2 205mm / 30d
  Kisumu   short-rains     2023-12-01: ERA5-Land 131mm vs MERRA-2 683mm / 30d
  Mombasa  dry season      2024-02-01: ERA5-Land 130mm vs MERRA-2 28mm  / 30d

CHIRPS adjudicates by clustering: the source that agrees with CHIRPS is more
likely to be observationally correct for that site and season.

Downloads ~180 CHIRPS daily files on first run (~5-15 min depending on UCSB
server speed). Files are cached in phase9/chirps_cache/ for instant reuse.

Coordinate note:
    Mombasa county centroid (-4.043, 39.668) falls on a coastal fill pixel in
    CHIRPS. Adjusted to (-4.050, 39.650) — nearest valid CHIRPS land pixel.
    Open-Meteo uses the original centroid; this coordinate difference (~2km)
    is documented but is unlikely to explain the observed 4.6x discrepancy.

Usage:
    python -m phase9.compare_chirps
"""

from __future__ import annotations

import sys
from datetime import datetime, date, timedelta, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from phase7.rainfall_providers import OpenMeteoProvider
from phase9.chirps_fetcher import (
    fetch_series,
    window_sums,
    CHIRPS_COORDS,
    CHIRPS_VERSION,
    CHIRPS_BASE,
)

# ── Cases to adjudicate ──────────────────────────────────────────────────────
# merra2_30d values taken verbatim from phase9/validation_findings.md
CASES = [
    {
        "name":       "Kisumu",
        "ecology":    "lake_basin",
        "ref_dates":  ["2024-07-01", "2023-12-01"],
        "seasons":    ["post-long-rains", "short-rains onset"],
        "merra2_30d": {"2024-07-01": 205.2, "2023-12-01": 683.1},
    },
    {
        "name":       "Mombasa",
        "ecology":    "coast",
        "ref_dates":  ["2024-02-01"],
        "seasons":    ["dry season (Jan-Feb)"],
        "merra2_30d": {"2024-02-01": 28.3},
    },
]

# All unique sites required (one download covers all)
SITES_NEEDED = {c["name"]: CHIRPS_COORDS[c["name"]] for c in CASES}

WINDOW_DAYS = 60   # match OpenMeteoProvider


# ── Helpers ──────────────────────────────────────────────────────────────────

def _ref(date_str: str) -> datetime:
    return datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)


def _mm(v: Optional[float], w: int = 8) -> str:
    return f"{v:{w}.1f}" if v is not None else f"{'—':>{w}}"


def _adjudicate(name: str, date_str: str, om_30: Optional[float],
                ch_30: Optional[float], merra2_30: Optional[float]) -> str:
    """
    Determine which source is more credible by checking which pair of
    (ERA5-Land, MERRA-2, CHIRPS) cluster together for the 30d value.
    Returns a plain-text verdict.
    """
    if ch_30 is None:
        return "CHIRPS unavailable — adjudication deferred"

    threshold = 1.5   # ratio within this → "consistent"

    def agree(a: Optional[float], b: Optional[float]) -> bool:
        if a is None or b is None or b < 1.0:
            return False
        r = a / b
        return 1 / threshold <= r <= threshold

    em_agree = agree(om_30, merra2_30)   # ERA5-Land and MERRA-2
    ec_agree = agree(om_30, ch_30)       # ERA5-Land and CHIRPS
    mc_agree = agree(merra2_30, ch_30)   # MERRA-2 and CHIRPS

    if ec_agree and not mc_agree:
        return "CHIRPS aligns with ERA5-Land — ERA5-Land (Open-Meteo) is more credible for this site/season"
    if mc_agree and not ec_agree:
        return "CHIRPS aligns with MERRA-2 — ERA5-Land (Open-Meteo) is less credible for this site/season"
    if ec_agree and mc_agree:
        return "All three sources broadly consistent — no material discrepancy to adjudicate"
    if em_agree:
        return "ERA5-Land and MERRA-2 agree; CHIRPS diverges — investigate CHIRPS coverage for this pixel"
    return "All three sources disagree — further investigation needed (gauge data, station records)"


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"Phase 9 CHIRPS adjudication")
    print(f"Product: CHIRPS v{CHIRPS_VERSION}")
    print(f"Base:    {CHIRPS_BASE}")
    print()

    # ── Step 1: fetch CHIRPS per window (avoids downloading gap days) ─────
    # Each window is 60 days; the three windows span Oct 2023–Jun 2024 but
    # are not contiguous — fetching per window saves ~90 unnecessary files.
    all_series: dict[str, dict[str, list[Optional[float]]]] = {}  # {date_str: {site: vals}}
    total_files_estimate = sum(len(c["ref_dates"]) for c in CASES) * WINDOW_DAYS
    print(f"Fetching CHIRPS: {len(CASES)} cases x {WINDOW_DAYS} days = ~{total_files_estimate} files")
    print(f"  (files cached in phase9/chirps_cache/ — fast on repeat runs)")
    print()

    # ── Step 2: run Open-Meteo and compare ────────────────────────────────
    om_provider = OpenMeteoProvider()
    verdicts: list[dict] = []

    for case in CASES:
        name = case["name"]
        lat, lon = CHIRPS_COORDS[name]

        for date_str, season in zip(case["ref_dates"], case["seasons"]):
            ref_dt = _ref(date_str)
            ref_d  = date.fromisoformat(date_str)
            end_d  = ref_d - timedelta(days=1)
            start_d = end_d - timedelta(days=WINDOW_DAYS - 1)
            merra2_30 = case["merra2_30d"].get(date_str)

            # Fetch CHIRPS for this window only
            print(f"Fetching CHIRPS: {name} {date_str} ({start_d} to {end_d})")
            site_map = {name: (lat, lon)}
            site_series, _ = fetch_series(site_map, start_d, end_d, verbose=True)
            site_vals = site_series[name]

            ch_7, ch_30, ch_60 = window_sums(site_vals)
            n_ok = sum(1 for v in site_vals if v is not None)

            # Open-Meteo for this case
            try:
                om = om_provider.get_rainfall_features(lat, lon, ref_dt)
            except Exception:
                om = None
            om_7  = om.rain_7d  if om else None
            om_30 = om.rain_30d if om else None
            om_60 = om.rain_60d if om else None

            verdict = _adjudicate(name, date_str, om_30, ch_30, merra2_30)

            print(f"{'='*72}")
            print(f"{name} ({case['ecology']})  —  {date_str}  [{season}]")
            print(f"  Window: {start_d} to {end_d}  ({WINDOW_DAYS} days)")
            if name == "Mombasa":
                print(f"  CHIRPS coord: ({lat}, {lon})  [adjusted from centroid — see docstring]")
            print()
            print(f"  {'Source':<22}  {'7d mm':>7}  {'30d mm':>8}  {'60d mm':>8}")
            print(f"  {'-'*55}")
            print(f"  {'Open-Meteo / ERA5-Land':<22}  {_mm(om_7)}  {_mm(om_30)}  {_mm(om_60)}")
            print(f"  {'NASA POWER / MERRA-2':<22}  {'—':>7}  {_mm(merra2_30)}  {'—':>8}  (prior run)")
            print(f"  {'CHIRPS v2.0':<22}  {_mm(ch_7)}  {_mm(ch_30)}  {_mm(ch_60)}")
            print()
            print(f"  Verdict: {verdict}")
            print()

            verdicts.append({
                "name":      name,
                "ecology":   case["ecology"],
                "date":      date_str,
                "season":    season,
                "om_7":      om_7,  "om_30":  om_30,  "om_60":  om_60,
                "merra2_30": merra2_30,
                "ch_7":      ch_7,  "ch_30":  ch_30,  "ch_60":  ch_60,
                "verdict":   verdict,
            })

    # ── Step 4: summary ───────────────────────────────────────────────────
    print(f"{'='*72}")
    print("SUMMARY")
    print(f"{'='*72}")
    for v in verdicts:
        print(f"\n{v['name']} {v['date']} [{v['season']}]:")
        print(f"  ERA5-Land 30d:  {_mm(v['om_30'])}  mm")
        print(f"  MERRA-2 30d:    {_mm(v['merra2_30'])}  mm")
        print(f"  CHIRPS 30d:     {_mm(v['ch_30'])}  mm")
        print(f"  Verdict: {v['verdict']}")

    print(f"\nCHIRPS source: CHIRPS v{CHIRPS_VERSION} africa_daily/{CHIRPS_BASE.split('/')[-2]}")
    print(f"Cache: phase9/chirps_cache/  ({len(list(Path('phase9/chirps_cache').glob('*.tif.gz')))} files)")


if __name__ == "__main__":
    main()
