"""
Regression tests for Kenya location normalization.

Contracts:
  county_list  — matched from static table (high location confidence)
  nominatim    — Phase 9 addition; not tested here
  unresolved   — no match; ecological_region=None; no spatial signal fired
"""

import pytest
from phase7.kenya_locations import (
    normalize_county, COUNTIES, DISPLAY_LOCATIONS,
    PLACE_ALIASES, CROSS_COUNTY_PLACES,
)

VALID_ECOLOGICAL_REGIONS = {
    "coast", "lake_basin", "highland", "highland_margins",
    "arid_semi_arid", "northern_kenya", "urban_informal", "nationwide",
}


# ── County direct match ────────────────────────────────────────────────────────

def test_kisumu_resolves_lake_basin():
    r = normalize_county("Kisumu")
    assert r.county == "Kisumu"
    assert r.ecological_region == "lake_basin"
    assert r.resolution_status == "county_list"
    assert r.latitude == pytest.approx(-0.196, abs=0.01)
    assert r.longitude == pytest.approx(34.877, abs=0.01)

def test_nairobi_resolves_highland():
    r = normalize_county("Nairobi")
    assert r.county == "Nairobi"
    assert r.ecological_region == "highland"
    assert r.resolution_status == "county_list"

def test_mandera_resolves_northern_kenya():
    r = normalize_county("Mandera")
    assert r.ecological_region == "northern_kenya"
    assert r.resolution_status == "county_list"

def test_mombasa_resolves_coast():
    r = normalize_county("Mombasa")
    assert r.ecological_region == "coast"
    assert r.resolution_status == "county_list"


# ── Alias → county ─────────────────────────────────────────────────────────────

def test_eldoret_resolves_uasin_gishu_highland():
    r = normalize_county("Eldoret")
    assert r.county == "Uasin Gishu"
    assert r.ecological_region == "highland"
    assert r.resolution_status == "county_list"

def test_thika_is_cross_county_alias():
    """Thika straddles Murang'a/Kiambu — must return ambiguous, not silently assign."""
    r = normalize_county("Thika")
    assert r.resolution_status == "cross_county_ambiguous"
    assert r.county is None

def test_malindi_resolves_kilifi_coast():
    r = normalize_county("Malindi")
    assert r.county == "Kilifi"
    assert r.ecological_region == "coast"


# ── Case insensitivity ─────────────────────────────────────────────────────────

def test_county_case_insensitive():
    lower = normalize_county("kisumu")
    upper = normalize_county("KISUMU")
    mixed = normalize_county("KiSuMu")
    assert lower.county == upper.county == mixed.county == "Kisumu"
    assert lower.ecological_region == "lake_basin"

def test_alias_case_insensitive():
    lower = normalize_county("eldoret")
    upper = normalize_county("ELDORET")
    assert lower.county == upper.county == "Uasin Gishu"


# ── Unresolved path ────────────────────────────────────────────────────────────

def test_unknown_input_is_unresolved():
    r = normalize_county("Unknown Village XYZ")
    assert r.county is None
    assert r.ecological_region is None
    assert r.latitude is None
    assert r.longitude is None
    assert r.resolution_status == "unresolved"

def test_empty_string_is_unresolved():
    r = normalize_county("")
    assert r.resolution_status == "unresolved"
    assert r.ecological_region is None

def test_unresolved_does_not_inherit_previous_call():
    """Unresolved must return None ecological_region regardless of prior calls."""
    normalize_county("Kisumu")          # prior successful call
    r = normalize_county("Gibberish Place 999")
    assert r.ecological_region is None
    assert r.resolution_status == "unresolved"


# ── Table completeness ─────────────────────────────────────────────────────────

def test_all_47_counties_present():
    assert len(COUNTIES) == 47

def test_all_counties_have_required_fields():
    for name, entry in COUNTIES.items():
        assert "ecological_region" in entry, f"{name}: missing ecological_region"
        assert "latitude" in entry,          f"{name}: missing latitude"
        assert "longitude" in entry,         f"{name}: missing longitude"

def test_all_ecological_regions_are_valid():
    for name, entry in COUNTIES.items():
        assert entry["ecological_region"] in VALID_ECOLOGICAL_REGIONS, (
            f"{name}: invalid region '{entry['ecological_region']}'"
        )

def test_all_coordinates_within_kenya_bounds():
    """Kenya: approx 34°E–41.9°E, -4.7°N–5.0°N."""
    for name, entry in COUNTIES.items():
        lat, lon = entry["latitude"], entry["longitude"]
        assert -5.0 <= lat <= 5.5, f"{name}: latitude {lat} out of Kenya bounds"
        assert 33.5 <= lon <= 42.5, f"{name}: longitude {lon} out of Kenya bounds"


# ── Display list ───────────────────────────────────────────────────────────────

def test_display_locations_contains_all_counties():
    for county in COUNTIES:
        assert county in DISPLAY_LOCATIONS, f"{county} missing from DISPLAY_LOCATIONS"

def test_display_locations_contains_eldoret():
    assert "Eldoret" in DISPLAY_LOCATIONS

def test_display_locations_no_raw_vocab():
    """Raw ecological zone codes must not appear in the display list."""
    raw_vocab = {"coast", "lake_basin", "highland", "highland_margins",
                 "arid_semi_arid", "northern_kenya", "urban_informal"}
    for item in DISPLAY_LOCATIONS:
        assert item not in raw_vocab, f"Raw vocab term '{item}' in DISPLAY_LOCATIONS"


# ── KNBS source coverage ───────────────────────────────────────────────────────

def test_place_aliases_uses_knbs_source():
    """Eldoret and Malindi are canonical KNBS urban centres, not hand-curated."""
    assert PLACE_ALIASES.get("Eldoret") == "Uasin Gishu"
    assert PLACE_ALIASES.get("Malindi") == "Kilifi"

def test_place_aliases_count():
    """Expect 162 single-county KNBS aliases (>=5k filter)."""
    assert len(PLACE_ALIASES) == 162

def test_cross_county_places_count():
    """Expect 13 cross-county entries (>=5k filter, county-named places excluded)."""
    assert len(CROSS_COUNTY_PLACES) == 13


# ── Cross-county disambiguation ────────────────────────────────────────────────

def test_thika_is_cross_county_ambiguous():
    r = normalize_county("Thika")
    assert r.resolution_status == "cross_county_ambiguous"
    assert r.county is None
    assert r.ecological_region is None
    assert "Murang'a" in r.candidate_counties
    assert "Kiambu" in r.candidate_counties

def test_nanyuki_is_cross_county_ambiguous():
    r = normalize_county("Nanyuki")
    assert r.resolution_status == "cross_county_ambiguous"
    assert set(r.candidate_counties) == {"Nyeri", "Laikipia"}

def test_cross_county_case_insensitive():
    lower = normalize_county("thika")
    upper = normalize_county("THIKA")
    assert lower.resolution_status == upper.resolution_status == "cross_county_ambiguous"

def test_county_takes_precedence_over_cross_county():
    """Garissa and Kisii are county names — county lookup must win."""
    r = normalize_county("Garissa")
    assert r.resolution_status == "county_list"
    assert r.county == "Garissa"
    r2 = normalize_county("Kisii")
    assert r2.resolution_status == "county_list"
    assert r2.county == "Kisii"

def test_display_locations_contains_cross_county_places():
    """Cross-county places must appear so clinicians can select them."""
    assert "Thika" in DISPLAY_LOCATIONS
    assert "Nanyuki" in DISPLAY_LOCATIONS
