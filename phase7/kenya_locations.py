"""
Kenya county location normalization — Phase 7 / Phase 9 foundation.

Provides a static 47-county lookup table with:
  - Primary ecological zone (for Phase 7 context engine)
  - County centroid lat/lon (for Phase 9 CHIRPS spatial lookup)
  - zone_note for counties spanning multiple ecological zones

Centroids: bounding-box midpoints derived from geoBoundaries KEN-ADM1
(RCMRD GeoPortal / geoboundaries.org, Public Domain licence).
Bbox midpoints are adequate for county-level spatial signal lookup;
Phase 9 should prefer Nominatim-resolved coordinates when the clinician
enters a specific town or facility.

Resolution status:
  county_list  — matched from this static table (high location confidence)
  nominatim    — resolved via geocoder (lower confidence; Phase 9 addition)
  unresolved   — no match; spatial environmental inference suppressed
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class LocationNormalization:
    location_raw: str
    county: str | None
    latitude: float | None
    longitude: float | None
    ecological_region: str | None
    resolution_status: str        # "county_list" | "nominatim" | "unresolved"
    zone_note: str | None = None
    candidate_counties: tuple[str, ...] | None = None  # set when resolution_status == "cross_county_ambiguous"


# ---------------------------------------------------------------------------
# 47-county static table
# Ecological regions use CLAUDE.md controlled vocabulary.
# zone_note is present only when the primary zone is an approximation.
# ---------------------------------------------------------------------------

COUNTIES: dict[str, dict] = {

    # ── Coast ────────────────────────────────────────────────────────────────
    "Mombasa": {
        "ecological_region": "coast",
        "latitude": -4.037,
        "longitude": 39.665,
    },
    "Kwale": {
        "ecological_region": "coast",
        "latitude": -4.133,
        "longitude": 39.044,
    },
    "Kilifi": {
        "ecological_region": "coast",
        "latitude": -3.151,
        "longitude": 39.667,
    },
    "Tana River": {
        "ecological_region": "arid_semi_arid",
        "latitude": -1.544,
        "longitude": 39.582,
        "zone_note": "Majority of county is semi-arid river corridor; Tana delta reaches coast. arid_semi_arid reflects dominant disease ecology.",
    },
    "Lamu": {
        "ecological_region": "coast",
        "latitude": -2.063,
        "longitude": 40.885,
    },
    "Taita-Taveta": {
        "ecological_region": "highland_margins",
        "latitude": -3.409,
        "longitude": 38.401,
        "zone_note": "Taita Hills reach ~2200m (highland); Tsavo lowlands are arid_semi_arid. highland_margins reflects dominant habitation zone.",
    },

    # ── North Eastern ─────────────────────────────────────────────────────────
    "Garissa": {
        "ecological_region": "arid_semi_arid",
        "latitude": -0.519,
        "longitude": 40.112,
        "zone_note": "Overlaps northern_kenya classification; arid_semi_arid is primary epidemiological zone.",
    },
    "Wajir": {
        "ecological_region": "arid_semi_arid",
        "latitude": 1.926,
        "longitude": 39.941,
        "zone_note": "Overlaps northern_kenya; arid_semi_arid primary.",
    },
    "Mandera": {
        "ecological_region": "northern_kenya",
        "latitude": 3.230,
        "longitude": 40.841,
        "zone_note": "Extreme north, Ethiopia/Somalia border. Also arid_semi_arid. northern_kenya assigned for border-zone disease surveillance.",
    },

    # ── Eastern ───────────────────────────────────────────────────────────────
    "Marsabit": {
        "ecological_region": "arid_semi_arid",
        "latitude": 2.860,
        "longitude": 37.698,
        "zone_note": "Also northern_kenya. Marsabit highlands form an island of highland_margins within a predominantly arid county.",
    },
    "Isiolo": {
        "ecological_region": "arid_semi_arid",
        "latitude": 1.006,
        "longitude": 38.163,
    },
    "Meru": {
        "ecological_region": "highland",
        "latitude": 0.225,
        "longitude": 37.754,
        "zone_note": "Mt Kenya slopes are highland; eastern lowlands trend to highland_margins. highland primary for health facility catchment.",
    },
    "Tharaka-Nithi": {
        "ecological_region": "highland_margins",
        "latitude": -0.191,
        "longitude": 37.808,
        "zone_note": "Transitional zone between central highlands and eastern semi-arid lowlands.",
    },
    "Embu": {
        "ecological_region": "highland",
        "latitude": -0.533,
        "longitude": 37.601,
    },
    "Kitui": {
        "ecological_region": "arid_semi_arid",
        "latitude": -1.560,
        "longitude": 38.335,
        "zone_note": "Northern Kitui has highland_margins; southern majority is arid_semi_arid.",
    },
    "Machakos": {
        "ecological_region": "highland_margins",
        "latitude": -1.277,
        "longitude": 37.372,
        "zone_note": "Machakos Hills are highland_margins; lower areas approach arid_semi_arid.",
    },
    "Makueni": {
        "ecological_region": "arid_semi_arid",
        "latitude": -2.254,
        "longitude": 37.830,
    },

    # ── Central ───────────────────────────────────────────────────────────────
    "Nyandarua": {
        "ecological_region": "highland",
        "latitude": -0.390,
        "longitude": 36.466,
    },
    "Nyeri": {
        "ecological_region": "highland",
        "latitude": -0.317,
        "longitude": 36.954,
    },
    "Kirinyaga": {
        "ecological_region": "highland",
        "latitude": -0.468,
        "longitude": 37.320,
    },
    "Murang'a": {
        "ecological_region": "highland",
        "latitude": -0.831,
        "longitude": 37.061,
    },
    "Kiambu": {
        "ecological_region": "highland",
        "latitude": -1.037,
        "longitude": 36.926,
    },

    # ── Rift Valley ───────────────────────────────────────────────────────────
    "Turkana": {
        "ecological_region": "arid_semi_arid",
        "latitude": 3.175,
        "longitude": 35.358,
        "zone_note": "Also northern_kenya. Largest county by area; predominantly arid.",
    },
    "West Pokot": {
        "ecological_region": "highland_margins",
        "latitude": 1.884,
        "longitude": 35.291,
        "zone_note": "Cherangani Hills slopes are highland; northeast portions arid_semi_arid.",
    },
    "Samburu": {
        "ecological_region": "arid_semi_arid",
        "latitude": 1.541,
        "longitude": 37.184,
    },
    "Trans-Nzoia": {
        "ecological_region": "highland",
        "latitude": 1.044,
        "longitude": 34.970,
    },
    "Uasin Gishu": {
        "ecological_region": "highland",
        "latitude": 0.476,
        "longitude": 35.220,
    },
    "Elgeyo-Marakwet": {
        "ecological_region": "highland",
        "latitude": 0.744,
        "longitude": 35.437,
        "zone_note": "Escarpment top and Cherangani range are highland; Kerio Valley floor is highland_margins/semi-arid.",
    },
    "Nandi": {
        "ecological_region": "highland",
        "latitude": 0.226,
        "longitude": 35.088,
    },
    "Baringo": {
        "ecological_region": "highland_margins",
        "latitude": 0.719,
        "longitude": 36.006,
        "zone_note": "Tugen Hills are highland; Lake Baringo floor and northeast portions are arid_semi_arid.",
    },
    "Laikipia": {
        "ecological_region": "highland_margins",
        "latitude": 0.287,
        "longitude": 36.790,
    },
    "Nakuru": {
        "ecological_region": "highland",
        "latitude": -0.461,
        "longitude": 36.004,
    },
    "Narok": {
        "ecological_region": "highland_margins",
        "latitude": -1.280,
        "longitude": 35.468,
        "zone_note": "Mau escarpment is highland; Maasai Mara plains are highland_margins to arid_semi_arid.",
    },
    "Kajiado": {
        "ecological_region": "arid_semi_arid",
        "latitude": -2.118,
        "longitude": 36.970,
        "zone_note": "Northern Kajiado (Ngong area) is highland_margins; majority of county is arid_semi_arid Maasai plains.",
    },
    "Kericho": {
        "ecological_region": "highland",
        "latitude": -0.236,
        "longitude": 35.340,
    },
    "Bomet": {
        "ecological_region": "highland",
        "latitude": -0.700,
        "longitude": 35.299,
    },

    # ── Western ───────────────────────────────────────────────────────────────
    "Kakamega": {
        "ecological_region": "lake_basin",
        "latitude": 0.497,
        "longitude": 34.749,
    },
    "Vihiga": {
        "ecological_region": "lake_basin",
        "latitude": 0.083,
        "longitude": 34.730,
    },
    "Bungoma": {
        "ecological_region": "lake_basin",
        "latitude": 0.785,
        "longitude": 34.713,
        "zone_note": "Mt Elgon eastern slopes reach highland_margins; main county population is lake_basin.",
    },
    "Busia": {
        "ecological_region": "lake_basin",
        "latitude": 0.376,
        "longitude": 34.173,
    },

    # ── Nyanza ────────────────────────────────────────────────────────────────
    "Siaya": {
        "ecological_region": "lake_basin",
        "latitude": -0.055,
        "longitude": 34.254,
    },
    "Kisumu": {
        "ecological_region": "lake_basin",
        "latitude": -0.196,
        "longitude": 34.877,
    },
    "Homa Bay": {
        "ecological_region": "lake_basin",
        "latitude": -0.562,
        "longitude": 34.471,
    },
    "Migori": {
        "ecological_region": "lake_basin",
        "latitude": -1.020,
        "longitude": 34.329,
    },
    "Kisii": {
        "ecological_region": "lake_basin",
        "latitude": -0.737,
        "longitude": 34.816,
        "zone_note": "Kisii highlands reach 2400m but county is classified lake_basin for regional disease-corridor purposes.",
    },
    "Nyamira": {
        "ecological_region": "lake_basin",
        "latitude": -0.651,
        "longitude": 34.939,
        "zone_note": "Tea-growing highland zone; lake_basin for disease corridor consistency with adjacent Kisii and Kisumu.",
    },

    # ── Nairobi ───────────────────────────────────────────────────────────────
    "Nairobi": {
        "ecological_region": "highland",
        "latitude": -1.302,
        "longitude": 36.882,
        "zone_note": "Urban highland. urban_informal applies at subcounty/ward level — not inferred from county selection.",
    },
}


# ---------------------------------------------------------------------------
# Urban centre → county lookups
# Source: KNBS 2019 Population and Housing Census — Population in Urban Centres
# Filtered to ≥5,000 population (206 centres). County names normalised to
# canonical COUNTIES keys. Cross-county centres stored separately.
# ---------------------------------------------------------------------------

# Single-county urban centres whose name differs from the county name.
# key: display name (title case)  value: canonical county name
PLACE_ALIASES: dict[str, str] = {
    "Ahero":              "Kisumu",
    "Athi River":         "Machakos",
    "Awasi":              "Kisumu",
    "Awendo":             "Migori",
    "Banisa":             "Mandera",
    "Bondo":              "Siaya",
    "Brooke Bond":        "Kericho",
    "Bura":               "Tana River",
    "Bura East":          "Garissa",
    "Bute":               "Wajir",
    "Butere":             "Kakamega",
    "Chaka":              "Nyeri",
    "Chavakali":          "Vihiga",
    "Chogoria":           "Tharaka-Nithi",
    "Chuka":              "Tharaka-Nithi",
    "Chwele":             "Bungoma",
    "Dadaab":             "Garissa",
    "El Wak":             "Mandera",
    "Elburgon":           "Nakuru",
    "Eldama Ravine":      "Baringo",
    "Eldas":              "Wajir",
    "Eldoret":            "Uasin Gishu",
    "Engineer":           "Nyandarua",
    "Gar-Batula":         "Isiolo",
    "Garsen":             "Tana River",
    "Gatundu":            "Kiambu",
    "Gilgil":             "Nakuru",
    "Giriftu":            "Wajir",
    "Githiga":            "Kiambu",
    "Githunguri":         "Kiambu",
    "Gongoni":            "Kilifi",
    "Habaswein":          "Wajir",
    "Hola":               "Tana River",
    "Ijara":              "Garissa",
    "Il Bissil":          "Kajiado",
    "Isebania":           "Migori",
    "Isinya":             "Kajiado",
    "Iten":               "Elgeyo-Marakwet",
    "Juja":               "Kiambu",
    "Kabarnet":           "Baringo",
    "Kagio":              "Kirinyaga",
    "Kainuk":             "Turkana",
    "Kakuma":             "Turkana",
    "Kaloleni":           "Kilifi",
    "Kangema":            "Murang'a",
    "Kangundo":           "Machakos",
    "Kapsabet":           "Nandi",
    "Kapsokwony":         "Bungoma",
    "Karatina":           "Nyeri",
    "Karuri":             "Kiambu",
    "Katito":             "Kisumu",
    "Kawaida":            "Kiambu",
    "Kehancha":           "Migori",
    "Kendu Bay":          "Homa Bay",
    "Kenol":              "Murang'a",
    "Kerugoya":           "Kirinyaga",
    "Kibwezi":            "Makueni",
    "Kijauri":            "Nyamira",
    "Kikuyu":             "Kiambu",
    "Kilgoris":           "Narok",
    "Kimana":             "Kajiado",
    "Kimbimbi":           "Kirinyaga",
    "Kimilili":           "Bungoma",
    "Kiminini":           "Trans-Nzoia",
    "Kinango":            "Kwale",
    "Kinna":              "Isiolo",
    "Kiserian":           "Kajiado",
    "Kitale":             "Trans-Nzoia",
    "Kitengela":          "Kajiado",
    "Kutus":              "Kirinyaga",
    "Laare":              "Meru",
    "Lafey":              "Mandera",
    "Laisamis":           "Marsabit",
    "Limuru":             "Kiambu",
    "Litein":             "Kericho",
    "Lodwar":             "Turkana",
    "Loitoktok":          "Kajiado",
    "Loiyangalani":       "Marsabit",
    "Lokichar":           "Turkana",
    "Lokichoggio":        "Turkana",
    "Lolgorian":          "Narok",
    "Luanda":             "Vihiga",
    "Mai Mahiu":          "Nakuru",
    "Mairo Inya":         "Nyandarua",
    "Majengo":            "Vihiga",
    "Maji Mazuri":        "Baringo",
    "Makindu":            "Makueni",
    "Makutano":           "West Pokot",
    "Makutano (Kyumbi)":  "Machakos",
    "Malaba":             "Busia",
    "Malava":             "Kakamega",
    "Malindi":            "Kilifi",
    "Maragua":            "Murang'a",
    "Maralal":            "Samburu",
    "Marereni":           "Kilifi",
    "Marigat":            "Baringo",
    "Masalani":           "Garissa",
    "Maseno":             "Kisumu",
    "Matuu":              "Machakos",
    "Mau Narok":          "Nakuru",
    "Maua":               "Meru",
    "Mbale":              "Vihiga",
    "Mbita":              "Homa Bay",
    "Merti":              "Isiolo",
    "Mlolongo":           "Machakos",
    "Moi's Bridge":       "Uasin Gishu",
    "Moyale":             "Marsabit",
    "Mpeketoni":          "Lamu",
    "Msambweni":          "Kwale",
    "Mtito Andei":        "Makueni",
    "Mtwapa":             "Kilifi",
    "Muhoroni":           "Kisumu",
    "Mukurweini":         "Nyeri",
    "Mumias":             "Kakamega",
    "Mwatate":            "Taita-Taveta",
    "Mwingi":             "Kitui",
    "Mwisho Wa Rami":     "Nakuru",
    "Nairobi City":       "Nairobi",
    "Naivasha":           "Nakuru",
    "Namanga":            "Kajiado",
    "Nandi Hills":        "Nandi",
    "Ndundori":           "Nakuru",
    "Ngong":              "Kajiado",
    "Njoro":              "Nakuru",
    "Nkubu":              "Meru",
    "North Horr":         "Marsabit",
    "Nyahururu":          "Laikipia",
    "Ol Kalou":           "Nyandarua",
    "Ololunga":           "Narok",
    "Ongata Rongai":      "Kajiado",
    "Othaya":             "Nyeri",
    "Oyugis":             "Homa Bay",
    "Port Victoria":      "Busia",
    "Rhamu":              "Mandera",
    "Rironi":             "Kiambu",
    "Rodi Kopany":        "Homa Bay",
    "Rongo":              "Migori",
    "Ruiru":              "Kiambu",
    "Rumuruti":           "Laikipia",
    "Sagana":             "Kirinyaga",
    "Salgaa":             "Nakuru",
    "Shianda":            "Kakamega",
    "Sindo":              "Homa Bay",
    "Sololo":             "Marsabit",
    "Sori":               "Migori",
    "Subukia":            "Nakuru",
    "Suneka":             "Kisii",
    "Takaba":             "Mandera",
    "Tala":               "Machakos",
    "Taveta":             "Taita-Taveta",
    "Timau":              "Meru",
    "Ting'ang'a":         "Kiambu",
    "Turi":               "Nakuru",
    "Ugunja":             "Siaya",
    "Ukunda":             "Kwale",
    "Usenge":             "Siaya",
    "Vipingo":            "Kilifi",
    "Voi":                "Taita-Taveta",
    "Wanguru":            "Kirinyaga",
    "Watamu":             "Kilifi",
    "Webuye":             "Bungoma",
    "Wote":               "Makueni",
}

# Urban centres that sit on a county boundary (KNBS 2019, ≥5,000 population).
# These require clinician disambiguation before a county can be assigned.
# value: ordered list of candidate canonical county names.
CROSS_COUNTY_PLACES: dict[str, list[str]] = {
    "Chebilat":     ["Bomet", "Nyamira"],
    "Emali":        ["Makueni", "Kajiado"],
    "Keroka":       ["Nyamira", "Kisii"],
    "Mariakani":    ["Kwale", "Kilifi"],
    "Matunda":      ["Uasin Gishu", "Kakamega"],
    "Mazeras":      ["Kwale", "Kilifi"],
    "Modogashe":    ["Isiolo", "Garissa"],
    "Mogotio":      ["Nakuru", "Baringo"],
    "Nanyuki":      ["Nyeri", "Laikipia"],
    "Naro Moru":    ["Nyeri", "Laikipia"],
    "Sondu":        ["Kisumu", "Kericho"],
    "Sultan Hamud": ["Makueni", "Kajiado"],
    "Thika":        ["Murang'a", "Kiambu"],
}


# ---------------------------------------------------------------------------
# Lookup indexes (built once at import time)
# ---------------------------------------------------------------------------

_COUNTY_INDEX: dict[str, str] = {name.lower(): name for name in COUNTIES}
_ALIAS_INDEX: dict[str, str] = {k.lower(): v for k, v in PLACE_ALIASES.items()}
_CROSS_COUNTY_INDEX: dict[str, tuple[str, ...]] = {
    k.lower(): tuple(v) for k, v in CROSS_COUNTY_PLACES.items()
}


def normalize_county(location_raw: str) -> LocationNormalization:
    """
    Resolve a clinician-entered location string to a LocationNormalization.

    Lookup order:
      1. Exact county name (case-insensitive) → county_list
      2. Single-county urban centre (KNBS ≥5k) → county_list
      3. Cross-county urban centre → cross_county_ambiguous (candidate_counties set)
      4. Unresolved — no spatial inference

    Phase 9 addition (not yet implemented):
      Between steps 3 and 4, attempt Nominatim geocoding for free-text inputs.
    """
    key = location_raw.strip().lower()

    # 1. County name
    canonical = _COUNTY_INDEX.get(key)
    if canonical:
        entry = COUNTIES[canonical]
        return LocationNormalization(
            location_raw=location_raw,
            county=canonical,
            latitude=entry["latitude"],
            longitude=entry["longitude"],
            ecological_region=entry["ecological_region"],
            resolution_status="county_list",
            zone_note=entry.get("zone_note"),
        )

    # 2. Single-county urban centre
    county_name = _ALIAS_INDEX.get(key)
    if county_name:
        entry = COUNTIES[county_name]
        return LocationNormalization(
            location_raw=location_raw,
            county=county_name,
            latitude=entry["latitude"],
            longitude=entry["longitude"],
            ecological_region=entry["ecological_region"],
            resolution_status="county_list",
            zone_note=entry.get("zone_note"),
        )

    # 3. Cross-county urban centre — clinician disambiguation required
    candidates = _CROSS_COUNTY_INDEX.get(key)
    if candidates:
        return LocationNormalization(
            location_raw=location_raw,
            county=None,
            latitude=None,
            longitude=None,
            ecological_region=None,
            resolution_status="cross_county_ambiguous",
            candidate_counties=candidates,
        )

    # 4. Unresolved — Phase 9 will insert Nominatim here
    return LocationNormalization(
        location_raw=location_raw,
        county=None,
        latitude=None,
        longitude=None,
        ecological_region=None,
        resolution_status="unresolved",
    )


# Sorted display list for UI dropdowns.
# 47 counties + single-county PLACE_ALIASES + cross-county CROSS_COUNTY_PLACES.
# Cross-county entries trigger a disambiguation step in app.py.
DISPLAY_LOCATIONS: list[str] = (
    sorted(COUNTIES.keys())
    + sorted(PLACE_ALIASES.keys())
    + sorted(CROSS_COUNTY_PLACES.keys())
)
