"""
Integration test — live Open-Meteo API call.

Skipped by default; requires network access and is excluded from CI.
Run manually: pytest phase7/tests/test_rainfall_integration.py -m integration -v

Uses Kisumu county centroid (-0.196, 34.877) with a historical reference date
well inside the Open-Meteo archive (2024-07-01) to guarantee data availability.
"""

import pytest
from datetime import datetime, timezone

from phase7.rainfall_providers import OpenMeteoProvider, RainfallFeatures


@pytest.mark.integration
def test_open_meteo_live_kisumu_july_2024():
    """
    Live call against Open-Meteo Historical API for Kisumu, Kenya.
    Validates that the provider returns non-None RainfallFeatures with
    plausible values for a known-wet season (July 2024 = post-long-rains).
    """
    provider = OpenMeteoProvider()
    ref_date = datetime(2024, 7, 1, tzinfo=timezone.utc)

    features = provider.get_rainfall_features(
        lat=-0.196,
        lon=34.877,
        reference_date=ref_date,
    )

    assert features is not None, "OpenMeteoProvider returned None for a historical date"
    assert isinstance(features, RainfallFeatures)
    assert features.source == "open_meteo"
    assert features.rain_7d >= 0.0
    assert features.rain_30d >= features.rain_7d, "30-day sum must be >= 7-day sum"
    assert features.rain_60d >= features.rain_30d, "60-day sum must be >= 30-day sum"
    assert features.data_age >= 0.0
    # For a 2024 historical date, data should be well within staleness threshold
    assert features.data_age <= 5.0, (
        f"data_age={features.data_age} — unexpected gap for a 2024 archive date"
    )
    # Kisumu receives significant rainfall July 2024 (post-long-rains); expect > 0
    assert features.rain_30d > 0.0, "Expected non-zero rainfall for Kisumu in July 2024"
