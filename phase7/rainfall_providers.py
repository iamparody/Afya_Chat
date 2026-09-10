"""
Phase 9 — Rainfall provider implementations.

RainfallProvider is a structural protocol defining the interface.
OpenMeteoProvider implements it using the Open-Meteo Historical Weather API
(ERA5-Land reanalysis, ~11 km resolution, free, no API key).

Signal activation is still controlled by StaticCalendarProvider in context_engine.py.
These providers supply raw rainfall features for audit and future threshold
calibration — they do not gate signals themselves.

Provider contract
-----------------
get_rainfall_features(lat, lon, reference_date) -> RainfallFeatures | None

Returns None when:
  - The HTTP call fails or times out
  - The API returns no precipitation data
  - The most recent available observation is older than STALE_THRESHOLD_DAYS

Fallback behaviour is the caller's responsibility (context_engine falls back
to StaticCalendarProvider signal gating when RainfallFeatures is None).

Future providers
----------------
CHIRPSProvider  -- UCSB CHIRPS satellite + station blend; validated against
                   Kenya malaria/outbreak literature; file-based access (Phase 9+)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Protocol

import requests


# Days from reference_date to latest available observation before data
# is considered too stale to use; falls back to static calendar.
STALE_THRESHOLD_DAYS: int = 14


# ---------------------------------------------------------------------------
# RainfallFeatures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RainfallFeatures:
    """
    Raw rainfall aggregates for a single location and reference date.

    rain_7d / rain_30d / rain_60d are cumulative precipitation (mm) ending
    at reference_date - 1 day (yesterday), covering the respective window.

    observation_date is the latest date for which the provider returned data.
    data_age is the number of days between reference_date and observation_date.

    These features are attached to ContextResult for audit and future
    threshold calibration.  They do not currently gate signal activation.
    """
    rain_7d: float           # mm — sum of daily precipitation, past 7 days
    rain_30d: float          # mm — past 30 days
    rain_60d: float          # mm — past 60 days
    observation_date: date   # latest date with data from the provider
    data_age: float          # days: reference_date - observation_date
    source: str              # "open_meteo" | "chirps"


# ---------------------------------------------------------------------------
# RainfallProvider protocol
# ---------------------------------------------------------------------------

class RainfallProvider(Protocol):
    def get_rainfall_features(
        self,
        lat: float,
        lon: float,
        reference_date: datetime,
    ) -> RainfallFeatures | None:
        """
        Return RainfallFeatures for the given coordinate and reference date.
        Return None if data is unavailable, incomplete, or too stale.
        """
        ...

    def source_label(self) -> str:
        ...


# ---------------------------------------------------------------------------
# OpenMeteoProvider
# ---------------------------------------------------------------------------

class OpenMeteoProvider:
    """
    Open-Meteo Historical Weather API — ERA5-Land reanalysis.

    Endpoint: https://archive-api.open-meteo.com/v1/archive
    No API key required. Rate limits apply; not suitable for batch calls.
    Timezone: Africa/Nairobi (UTC+3) for correct day boundaries.

    Fetches a 61-day daily precipitation window ending at reference_date - 1 day
    (most recent day with confirmed data) and aggregates into 7/30/60-day sums.
    Returns None on any HTTP error, JSON parse failure, empty response, or if
    the most-recent observation is older than STALE_THRESHOLD_DAYS.

    Spatial approximation: county centroids from LocationNormalization are
    adequate for county-level signal lookup (~11 km ERA5-Land grid).
    Phase 9 Nominatim-resolved coordinates improve this for specific towns.
    """

    BASE_URL = "https://archive-api.open-meteo.com/v1/archive"
    TIMEOUT: int = 10        # seconds
    STALE_DAYS: int = STALE_THRESHOLD_DAYS

    def get_rainfall_features(
        self,
        lat: float,
        lon: float,
        reference_date: datetime,
    ) -> RainfallFeatures | None:
        ref = reference_date.date() if isinstance(reference_date, datetime) else reference_date
        end_date = ref - timedelta(days=1)
        start_date = ref - timedelta(days=61)

        params = {
            "latitude":   round(lat, 4),
            "longitude":  round(lon, 4),
            "start_date": start_date.isoformat(),
            "end_date":   end_date.isoformat(),
            "daily":      "precipitation_sum",
            "timezone":   "Africa/Nairobi",
        }

        try:
            resp = requests.get(self.BASE_URL, params=params, timeout=self.TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return None

        daily = data.get("daily", {})
        times: list[str] = daily.get("time", [])
        precip: list[float | None] = daily.get("precipitation_sum", [])

        if not times or not precip or len(times) != len(precip):
            return None

        # date-string → mm; treat None (missing) as 0.0
        by_date: dict[str, float] = {
            t: (p if p is not None else 0.0)
            for t, p in zip(times, precip)
        }

        def _window(days: int) -> float:
            return round(
                sum(
                    by_date.get((ref - timedelta(days=i)).isoformat(), 0.0)
                    for i in range(1, days + 1)
                ),
                1,
            )

        latest = max(
            (datetime.strptime(t, "%Y-%m-%d").date() for t in times),
            default=None,
        )
        if latest is None:
            return None

        data_age = float((ref - latest).days)
        if data_age > self.STALE_DAYS:
            return None

        return RainfallFeatures(
            rain_7d=_window(7),
            rain_30d=_window(30),
            rain_60d=_window(60),
            observation_date=latest,
            data_age=data_age,
            source="open_meteo",
        )

    def source_label(self) -> str:
        return "open_meteo"
