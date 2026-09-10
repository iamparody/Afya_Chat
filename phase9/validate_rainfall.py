"""
Phase 9 validation: Open-Meteo/ERA5-Land vs NASA POWER/MERRA-2 for 5 Kenyan
reference sites across three seasonal regimes.

Not production code. Run manually to compare rainfall sources. Findings are written
to phase9/validation_findings.md as an auditable record.

Usage:
    python -m phase9.validate_rainfall
    python -m phase9.validate_rainfall --date 2024-07-01

Data sources
------------
Open-Meteo/ERA5-Land
    ERA5-Land reanalysis, ~11km grid, Africa/Nairobi timezone.
    This is the production path (ContextResult.rainfall). Not yet clinically validated.

NASA POWER/MERRA-2
    MERRA-2 reanalysis corrected precipitation (PRECTOTCORR), ~0.5-degree grid.
    Independent estimate used for comparison only. No API key. ~3–5s per request.

CHIRPS (not yet fetched)
    Satellite + gauge blend, ~5km grid. The intended third comparison source.
    Requires ClimateSERV registration or rasterio to access UCSB GeoTIFF files.
    Neither the IRI Data Library endpoint (requires auth) nor direct file download
    (requires rasterio) is available without additional setup. A ratio that looks
    acceptable between ERA5-Land and MERRA-2 does not substitute for CHIRPS comparison.

Validation status
-----------------
- Open-Meteo/ERA5-Land is not yet clinically validated as the rainfall source for CDS.
- Kisumu (lake_basin) shows a large wet-season discrepancy between ERA5-Land and
  MERRA-2. Which source is observationally correct is not established — CHIRPS
  adjudication is required before drawing conclusions about lake_basin rainfall.
- Mombasa Jan–Feb discrepancy (ERA5-Land ~130mm vs MERRA-2 ~28mm over 30d) is
  unresolved. One or both sources may be wrong for that season and site.
- No thresholds have been derived from these comparisons. The observations here
  establish discrepancy, not clinical or observational correctness of either source.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone, date, timedelta
from pathlib import Path
from typing import Optional

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from phase7.rainfall_providers import OpenMeteoProvider, RainfallFeatures


# ── Reference locations ──────────────────────────────────────────────────────

LOCATIONS = [
    {"name": "Kisumu",   "lat": -0.196, "lon": 34.877, "ecology": "lake_basin"},
    {"name": "Nairobi",  "lat": -1.286, "lon": 36.820, "ecology": "highland"},
    {"name": "Garissa",  "lat": -0.455, "lon": 39.646, "ecology": "arid_semi_arid"},
    {"name": "Mombasa",  "lat": -4.043, "lon": 39.668, "ecology": "coast"},
    {"name": "Turkana",  "lat":  3.116, "lon": 35.597, "ecology": "arid_semi_arid"},
]

# Three reference dates covering distinct seasonal regimes
DEFAULT_DATES = [
    datetime(2024, 7, 1,  tzinfo=timezone.utc),   # post-long-rains (Jun-Jul)
    datetime(2023, 12, 1, tzinfo=timezone.utc),   # short-rains onset (Oct-Nov)
    datetime(2024, 2, 1,  tzinfo=timezone.utc),   # dry season (Jan-Feb)
]


# ── NASA POWER (MERRA-2) fetcher ─────────────────────────────────────────────

_POWER_BASE = "https://power.larc.nasa.gov/api/temporal/daily/point"
_POWER_TIMEOUT = 30   # seconds


def _fetch_nasa_power(
    lat: float, lon: float, start_d: date, end_d: date
) -> tuple[Optional[list[float]], str]:
    """
    Fetch NASA POWER PRECTOTCORR (MERRA-2 daily precipitation, mm/day) for a
    date range. Returns (daily_values_chronological, diagnostic_note).
    """
    params = {
        "parameters": "PRECTOTCORR",
        "community": "AG",
        "longitude": round(lon, 4),
        "latitude": round(lat, 4),
        "start": start_d.strftime("%Y%m%d"),
        "end": end_d.strftime("%Y%m%d"),
        "format": "JSON",
        "header": "false",
    }
    try:
        resp = requests.get(_POWER_BASE, params=params, timeout=_POWER_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except requests.Timeout:
        return None, "timeout"
    except requests.HTTPError as e:
        return None, f"HTTP {e.response.status_code}"
    except Exception:
        return None, "connection error"

    precip: dict[str, float] = (
        data.get("properties", {}).get("parameter", {}).get("PRECTOTCORR", {})
    )
    if not precip:
        return None, "empty response"

    # Sort chronologically; exclude fill values (-999 and below)
    vals = [v for _, v in sorted(precip.items()) if v > -999]
    if not vals:
        return None, "all fill values"

    return vals, f"n={len(vals)}d"


def fetch_nasa_power_window(
    lat: float, lon: float, ref_date: datetime, window_days: int = 61
) -> tuple[Optional[tuple[float, float, float]], str]:
    """
    Fetch NASA POWER for the window_days window ending ref_date-1.
    Returns ((7d, 30d, 60d), note) or (None, note) on failure.
    """
    end_d = ref_date.date() - timedelta(days=1)
    start_d = end_d - timedelta(days=window_days - 1)

    vals, note = _fetch_nasa_power(lat, lon, start_d, end_d)
    if not vals or len(vals) < 7:
        return None, note

    def tail(n: int) -> float:
        return round(sum(vals[-n:] if len(vals) >= n else vals), 1)

    return (tail(7), tail(30), tail(60)), note


# ── Formatting helpers ───────────────────────────────────────────────────────

def _mm(v: Optional[float], width: int = 8) -> str:
    return f"{v:{width}.1f}" if v is not None else f"{'—':>{width}}"


def _ratio(a: Optional[float], b: Optional[float]) -> str:
    """Brief ratio label — only fires if both > 1mm (avoids near-zero noise)."""
    if a is None or b is None:
        return ""
    if a < 1.0 and b < 1.0:
        return "(both <1mm)"
    if b < 0.1:
        return f"(POWER≈0)"
    ratio = a / b
    if ratio > 2.0:
        return f"(OM {ratio:.1f}x POWER)"
    if ratio < 0.5:
        return f"(POWER {1/ratio:.1f}x OM)"
    return f"(ratio {ratio:.2f})"


# ── Main comparison ──────────────────────────────────────────────────────────

def run_comparison(ref_date: datetime) -> None:
    om_provider = OpenMeteoProvider()

    print(f"\n{'='*80}")
    print(f"  {ref_date.date().isoformat()}  |  window: 60 days ending {(ref_date.date() - timedelta(days=1)).isoformat()}")
    print(f"  Open-Meteo = ERA5-Land (~11km)      NASA POWER = MERRA-2 (~50km)")
    print(f"{'='*80}")
    print(f"{'Location':<12}  {'Source':<12}  {'7d mm':>7}  {'30d mm':>8}  {'60d mm':>8}  Notes")
    print(f"{'-'*80}")

    for loc in LOCATIONS:
        name, lat, lon = loc["name"], loc["lat"], loc["lon"]
        print()

        # Open-Meteo ─────────────────────────────────────────────────────────
        try:
            om = om_provider.get_rainfall_features(lat, lon, ref_date)
        except Exception:
            om = None

        if om:
            print(
                f"{name:<12}  {'Open-Meteo':<12}  {_mm(om.rain_7d)}  "
                f"{_mm(om.rain_30d)}  {_mm(om.rain_60d)}  "
                f"age={om.data_age:.0f}d  obs={om.observation_date}"
            )
        else:
            print(f"{name:<12}  {'Open-Meteo':<12}  {'—':>7}  {'—':>8}  {'—':>8}  stale or error")

        # NASA POWER (MERRA-2) ────────────────────────────────────────────────
        result, note = fetch_nasa_power_window(lat, lon, ref_date)

        if result is not None:
            pw_7, pw_30, pw_60 = result
            ratio = _ratio(om.rain_30d if om else None, pw_30)
            print(
                f"{name:<12}  {'NASA/MERRA-2':<12}  {_mm(pw_7)}  "
                f"{_mm(pw_30)}  {_mm(pw_60)}  {note}  {ratio}"
            )
        else:
            print(
                f"{name:<12}  {'NASA/MERRA-2':<12}  {'—':>7}  {'—':>8}  {'—':>8}  "
                f"FAILED ({note})"
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Open-Meteo vs NASA POWER rainfall for 5 Kenyan reference sites",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--date",
        metavar="YYYY-MM-DD",
        help="Single reference date (default: 3 standard dates — post-long-rains, short-rains, dry season)",
    )
    args = parser.parse_args()

    if args.date:
        try:
            dates = [datetime.fromisoformat(args.date).replace(tzinfo=timezone.utc)]
        except ValueError:
            print(f"ERROR: --date must be YYYY-MM-DD, got: {args.date!r}", file=sys.stderr)
            sys.exit(1)
    else:
        dates = DEFAULT_DATES

    for ref_date in dates:
        run_comparison(ref_date)

    print(f"\n{'='*80}")
    print("Notes on this comparison:")
    print("  Sources: Open-Meteo/ERA5-Land (~11km) vs NASA POWER/MERRA-2 (~50km).")
    print("  CHIRPS (satellite+gauge, the intended adjudicator) is not yet fetched.")
    print("  Discrepancy != one source is wrong. Both are reanalysis products.")
    print("  Kisumu/lake_basin: large wet-season gap (4–5x) between the two sources.")
    print("    Which is correct is not established without CHIRPS.")
    print("  Mombasa Jan–Feb: large gap in both directions — unresolved.")
    print("  Do not derive signal thresholds from this comparison alone.")
    print("  See phase9/validation_findings.md for the auditable raw table.")


if __name__ == "__main__":
    main()
