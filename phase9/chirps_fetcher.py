"""
CHIRPS v2.0 Africa daily GeoTIFF fetcher — validation use only.

Product  : CHIRPS v2.0, africa_daily, p05 (0.05-degree resolution)
Source   : https://data.chc.ucsb.edu/products/CHIRPS-2.0/africa_daily/tifs/p05/
Fill     : -9999.0 (no nodata tag in file; must be detected numerically)
Cache    : phase9/chirps_cache/  (gitignored)

Each daily file covers all of Africa (~612 KB compressed). Download it once per
day and extract values for any number of sites — avoids re-downloading per site.

Important: some coastal pixels are fill-value even on land. Use CHIRPS_COORDS
(below) rather than county centroids to ensure a valid land pixel is read.

Do not use this module in the production context engine.
"""

from __future__ import annotations

import gzip
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import requests
import rasterio
from rasterio.io import MemoryFile

# ── Product constants ────────────────────────────────────────────────────────
CHIRPS_VERSION = "2.0"
CHIRPS_RESOLUTION = "p05"
CHIRPS_BASE = (
    f"https://data.chc.ucsb.edu/products/CHIRPS-{CHIRPS_VERSION}"
    f"/africa_daily/tifs/{CHIRPS_RESOLUTION}"
)
FILL = -9999.0
TIMEOUT = 90   # seconds — UCSB can be slow on first hit

# ── Cache location ───────────────────────────────────────────────────────────
CACHE_DIR = Path(__file__).parent / "chirps_cache"

# ── CHIRPS-specific coordinates ──────────────────────────────────────────────
# Some county centroids fall on coastal fill pixels in the CHIRPS land mask.
# These coordinates are the nearest valid CHIRPS grid cell verified by inspection.
# Documented in validation_findings.md.
CHIRPS_COORDS: dict[str, tuple[float, float]] = {
    "Kisumu":  (-0.196, 34.877),   # same as county centroid — valid pixel confirmed
    "Nairobi": (-1.286, 36.820),
    "Garissa": (-0.455, 39.646),
    "Mombasa": (-4.050, 39.650),   # adjusted: centroid (-4.043, 39.668) is coastal fill
    "Turkana": ( 3.116, 35.597),
}


# ── File management ──────────────────────────────────────────────────────────

def _url(d: date) -> str:
    return f"{CHIRPS_BASE}/{d.year}/chirps-v2.0.{d.year}.{d.month:02d}.{d.day:02d}.tif.gz"


def _cache_path(d: date) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"chirps-v2.0.{d.year}.{d.month:02d}.{d.day:02d}.tif.gz"


def download_day(d: date) -> Optional[bytes]:
    """Return .tif.gz bytes for date d; downloads and caches on first call."""
    p = _cache_path(d)
    if p.exists() and p.stat().st_size > 0:
        return p.read_bytes()
    try:
        resp = requests.get(_url(d), timeout=TIMEOUT, stream=True)
        resp.raise_for_status()
        data = resp.content
    except requests.RequestException:
        return None
    p.write_bytes(data)
    return data


# ── Pixel extraction ─────────────────────────────────────────────────────────

def read_pixels(
    gz_bytes: bytes,
    sites: dict[str, tuple[float, float]],
) -> dict[str, Optional[float]]:
    """
    Extract precipitation values (mm) for multiple sites from one CHIRPS file.

    sites: {name: (lat, lon)} — use CHIRPS_COORDS to avoid coastal fill pixels.
    Returns {name: mm | None}. None means fill value or read error for that site.
    """
    results: dict[str, Optional[float]] = {}
    try:
        raw = gzip.decompress(gz_bytes)
        with MemoryFile(raw) as mf:
            with mf.open() as ds:
                band = ds.read(1)
                for name, (lat, lon) in sites.items():
                    try:
                        row, col = ds.index(lon, lat)
                        val = float(band[row, col])
                        results[name] = None if val < FILL + 1 else max(0.0, val)
                    except Exception:
                        results[name] = None
    except Exception:
        for name in sites:
            results[name] = None
    return results


# ── Window fetch ─────────────────────────────────────────────────────────────

def fetch_series(
    sites: dict[str, tuple[float, float]],
    start_d: date,
    end_d: date,
    verbose: bool = True,
) -> tuple[dict[str, list[Optional[float]]], dict[str, int]]:
    """
    Fetch daily CHIRPS precipitation for multiple sites over a date range.

    Downloads each day's Africa-wide file once and extracts all sites from it.
    Caches files in CACHE_DIR for reuse.

    Returns:
        series  — {site_name: [daily_mm | None, ...]}  (index = day from start_d)
        n_files — {site_name: number of days with non-fill data}
    """
    series: dict[str, list[Optional[float]]] = {n: [] for n in sites}
    n_files: dict[str, int] = {n: 0 for n in sites}

    total = (end_d - start_d).days + 1
    current = start_d
    i = 0
    while current <= end_d:
        i += 1
        gz = download_day(current)
        if gz is not None:
            pixels = read_pixels(gz, sites)
        else:
            pixels = {n: None for n in sites}

        for name, val in pixels.items():
            series[name].append(val)
            if val is not None:
                n_files[name] += 1

        if verbose and (i % 15 == 0 or i == total):
            cached = sum(
                1 for d_i in range(total)
                if _cache_path(start_d + timedelta(days=d_i)).exists()
            )
            print(f"    {i}/{total} days  ({current})  cache: {cached} files", flush=True)

        current += timedelta(days=1)

    return series, n_files


def window_sums(
    values: list[Optional[float]],
    fill_missing: float = 0.0,
) -> tuple[float, float, float]:
    """
    7d / 30d / 60d sums from the tail of a daily series.
    None values are replaced with fill_missing (default 0.0 — conservative).
    """
    filled = [v if v is not None else fill_missing for v in values]

    def tail(n: int) -> float:
        return round(sum(filled[-n:] if len(filled) >= n else filled), 1)

    return tail(7), tail(30), tail(60)
