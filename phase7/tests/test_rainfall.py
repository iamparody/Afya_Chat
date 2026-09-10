"""
Unit tests for OpenMeteoProvider.
All HTTP calls are mocked — no network dependency.

Contracts verified:
  - Successful response → correct 7/30/60-day sums, data_age, source label
  - HTTP error → None returned
  - JSON missing daily block → None returned
  - Precipitation list contains None values → treated as 0.0
  - Data too stale (> STALE_THRESHOLD_DAYS) → None returned
  - data_age calculated correctly from reference_date − latest_observation
  - lat/lon rounded to 4 d.p. in request params
  - Timezone is Africa/Nairobi in request params
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest

from phase7.rainfall_providers import (
    OpenMeteoProvider,
    RainfallFeatures,
    STALE_THRESHOLD_DAYS,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REF_DATE = datetime(2026, 7, 15, tzinfo=timezone.utc)
REF = REF_DATE.date()  # 2026-07-15

# Build a fake Open-Meteo response covering the last 61 days.
# Day -1 to -7: 5.0 mm/day  → rain_7d  = 35.0
# Day -8 to -30: 2.0 mm/day → rain_30d = 35 + 23*2 = 81.0
# Day -31 to -60: 0.0 mm/day→ rain_60d = 81.0
def _make_response(days: int = 61, latest_offset: int = 1) -> dict:
    """
    latest_offset: how many days before REF the latest available date is.
    days: total number of daily records (ending at REF - latest_offset).
    """
    latest = REF - timedelta(days=latest_offset)
    times = [(latest - timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]
    precip = []
    for t in times:
        d = datetime.strptime(t, "%Y-%m-%d").date()
        delta = (REF - d).days
        if 1 <= delta <= 7:
            precip.append(5.0)
        elif 8 <= delta <= 30:
            precip.append(2.0)
        else:
            precip.append(0.0)
    return {"daily": {"time": times, "precipitation_sum": precip}}


def _mock_get(response_dict: dict, status_code: int = 200):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = response_dict
    if status_code >= 400:
        mock_resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    else:
        mock_resp.raise_for_status.return_value = None
    return MagicMock(return_value=mock_resp)


# ---------------------------------------------------------------------------
# Successful response
# ---------------------------------------------------------------------------

def test_returns_features_on_success():
    provider = OpenMeteoProvider()
    with patch("phase7.rainfall_providers.requests.get", _mock_get(_make_response())):
        f = provider.get_rainfall_features(-0.196, 34.877, REF_DATE)
    assert f is not None
    assert isinstance(f, RainfallFeatures)
    assert f.source == "open_meteo"
    assert f.rain_7d == pytest.approx(35.0, abs=0.1)
    assert f.rain_30d == pytest.approx(81.0, abs=0.1)
    assert f.rain_60d == pytest.approx(81.0, abs=0.1)
    assert f.data_age == pytest.approx(1.0)
    assert f.observation_date == REF - timedelta(days=1)


def test_request_params_include_timezone_and_rounded_coords():
    provider = OpenMeteoProvider()
    with patch("phase7.rainfall_providers.requests.get", _mock_get(_make_response())) as mock_get:
        provider.get_rainfall_features(-0.19612, 34.87734, REF_DATE)
    call_kwargs = mock_get.call_args
    params = call_kwargs[1]["params"] if "params" in call_kwargs[1] else call_kwargs[0][1]
    assert params["timezone"] == "Africa/Nairobi"
    assert params["latitude"] == round(-0.19612, 4)
    assert params["longitude"] == round(34.87734, 4)


def test_source_label():
    assert OpenMeteoProvider().source_label() == "open_meteo"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

def test_returns_none_on_http_error():
    provider = OpenMeteoProvider()
    with patch("phase7.rainfall_providers.requests.get", _mock_get({}, status_code=503)):
        f = provider.get_rainfall_features(-0.196, 34.877, REF_DATE)
    assert f is None


def test_returns_none_on_request_exception():
    provider = OpenMeteoProvider()
    with patch("phase7.rainfall_providers.requests.get", side_effect=ConnectionError("timeout")):
        f = provider.get_rainfall_features(-0.196, 34.877, REF_DATE)
    assert f is None


def test_returns_none_when_daily_block_missing():
    provider = OpenMeteoProvider()
    with patch("phase7.rainfall_providers.requests.get", _mock_get({"latitude": -0.196})):
        f = provider.get_rainfall_features(-0.196, 34.877, REF_DATE)
    assert f is None


def test_returns_none_when_time_and_precip_empty():
    provider = OpenMeteoProvider()
    with patch("phase7.rainfall_providers.requests.get", _mock_get({"daily": {"time": [], "precipitation_sum": []}})):
        f = provider.get_rainfall_features(-0.196, 34.877, REF_DATE)
    assert f is None


# ---------------------------------------------------------------------------
# Missing precipitation values
# ---------------------------------------------------------------------------

def test_none_precipitation_treated_as_zero():
    """API may return null for days without data; must not raise."""
    resp = _make_response()
    # Inject None into a few entries
    precip = resp["daily"]["precipitation_sum"]
    precip[0] = None
    precip[5] = None
    provider = OpenMeteoProvider()
    with patch("phase7.rainfall_providers.requests.get", _mock_get(resp)):
        f = provider.get_rainfall_features(-0.196, 34.877, REF_DATE)
    assert f is not None
    assert f.rain_7d >= 0.0


# ---------------------------------------------------------------------------
# Staleness
# ---------------------------------------------------------------------------

def test_returns_none_when_data_too_stale():
    """Latest observation older than STALE_THRESHOLD_DAYS → None."""
    stale_offset = STALE_THRESHOLD_DAYS + 1
    provider = OpenMeteoProvider()
    with patch("phase7.rainfall_providers.requests.get", _mock_get(_make_response(latest_offset=stale_offset))):
        f = provider.get_rainfall_features(-0.196, 34.877, REF_DATE)
    assert f is None


def test_returns_features_at_staleness_boundary():
    """Latest observation exactly at STALE_THRESHOLD_DAYS → still returned."""
    provider = OpenMeteoProvider()
    with patch("phase7.rainfall_providers.requests.get", _mock_get(_make_response(latest_offset=STALE_THRESHOLD_DAYS))):
        f = provider.get_rainfall_features(-0.196, 34.877, REF_DATE)
    assert f is not None
    assert f.data_age == pytest.approx(float(STALE_THRESHOLD_DAYS))


# ---------------------------------------------------------------------------
# data_age calculation
# ---------------------------------------------------------------------------

def test_data_age_reflects_gap_from_reference_date():
    offset = 3
    provider = OpenMeteoProvider()
    with patch("phase7.rainfall_providers.requests.get", _mock_get(_make_response(latest_offset=offset))):
        f = provider.get_rainfall_features(-0.196, 34.877, REF_DATE)
    assert f is not None
    assert f.data_age == pytest.approx(float(offset))
    assert f.observation_date == REF - timedelta(days=offset)
