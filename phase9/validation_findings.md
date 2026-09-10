# Phase 9 Rainfall Validation Findings

**Last updated:** 2026-09-10  
**Scripts:** `phase9/validate_rainfall.py`, `phase9/compare_chirps.py`

---

## Validation status

**Updated after CHIRPS adjudication (2026-09-10):**

- Open-Meteo/ERA5-Land is **acceptable as the Phase 9 audit-trail rainfall source** for Kisumu (lake_basin), Nairobi (highland), Garissa (arid_semi_arid), and Turkana (arid_semi_arid).
- Open-Meteo/ERA5-Land **over-estimates rainfall at Mombasa (coast) in the Jan–Feb dry season** (~6.7x). CHIRPS and MERRA-2 agree on a much lower value (~19–28mm/30d vs ERA5-Land's 131mm). This is a known bias for ERA5-Land in the northeast monsoon transition period.
- The prior Kisumu discrepancy (ERA5-Land vs MERRA-2) is resolved: MERRA-2 was over-estimating. CHIRPS confirms ERA5-Land at Kisumu within 1.15–1.45x.
- **No signal thresholds have been derived.** This finding establishes source acceptability, not calibrated thresholds.
- The Mombasa Jan–Feb bias does not currently affect signal activation (StaticCalendarProvider still gates all signals). It must be addressed before any `water_scarcity` or low-rainfall signal threshold is set for coast ecology.

---

## Data sources

| Label | Product | Grid | Access |
|-------|---------|------|--------|
| Open-Meteo/ERA5-Land | ERA5-Land reanalysis | ~11 km | Open-Meteo Historical API (production path) |
| NASA POWER/MERRA-2 | MERRA-2 corrected precipitation (PRECTOTCORR) | ~50 km | NASA POWER API (comparison, initial run only) |
| CHIRPS v2.0 | Satellite + gauge blend | ~5 km | UCSB GeoTIFF via rasterio (adjudication run) |

**CHIRPS product pin:** `CHIRPS-2.0/africa_daily/tifs/p05`  
**CHIRPS base URL:** `https://data.chc.ucsb.edu/products/CHIRPS-2.0/africa_daily/tifs/p05`  
**CHIRPS files used:** 180 daily `.tif.gz` files across three windows (cached in `phase9/chirps_cache/`)  
**Mombasa CHIRPS coordinate:** (-4.050, 39.650) — county centroid (-4.043, 39.668) falls on a coastal fill pixel in the CHIRPS land mask; adjusted ~2km to nearest valid land pixel.

---

## CHIRPS adjudication results

Script: `python -m phase9.compare_chirps`  
CHIRPS files downloaded: 180 (3 windows x 60 days). All 60 files valid per window (0 missing).

| Site | Ecology | Reference date | Season | ERA5-Land 30d | MERRA-2 30d | CHIRPS 30d | Verdict |
|------|---------|---------------|--------|-------------:|------------:|-----------:|---------|
| Kisumu | lake_basin | 2024-07-01 | post-long-rains | 43.0 mm | 205.2 mm | **48.8 mm** | CHIRPS aligns with ERA5-Land |
| Kisumu | lake_basin | 2023-12-01 | short-rains onset | 131.3 mm | 683.1 mm | **189.9 mm** | CHIRPS aligns with ERA5-Land |
| Mombasa | coast | 2024-02-01 | dry season (Jan-Feb) | 130.9 mm | 28.3 mm | **19.4 mm** | CHIRPS aligns with MERRA-2 |

**7d and 60d values for completeness:**

| Site | Date | Source | 7d mm | 30d mm | 60d mm |
|------|------|--------|------:|-------:|-------:|
| Kisumu | 2024-07-01 | Open-Meteo/ERA5-Land | 4.1 | 43.0 | 112.4 |
| Kisumu | 2024-07-01 | NASA POWER/MERRA-2 | 20.2 | 205.2 | 629.3 |
| Kisumu | 2024-07-01 | CHIRPS v2.0 | 8.7 | 48.8 | 190.4 |
| Kisumu | 2023-12-01 | Open-Meteo/ERA5-Land | 28.1 | 131.3 | 208.7 |
| Kisumu | 2023-12-01 | NASA POWER/MERRA-2 | 113.5 | 683.1 | 972.0 |
| Kisumu | 2023-12-01 | CHIRPS v2.0 | 53.1 | 189.9 | 354.9 |
| Mombasa | 2024-02-01 | Open-Meteo/ERA5-Land | 13.1 | 130.9 | 296.2 |
| Mombasa | 2024-02-01 | NASA POWER/MERRA-2 | 1.3 | 28.3 | 120.3 |
| Mombasa | 2024-02-01 | CHIRPS v2.0 | 3.3 | 19.4 | 153.7 |

---

## Initial ERA5-Land vs MERRA-2 comparison (all 5 sites, 3 dates)

Script: `python -m phase9.validate_rainfall`  
Run date: 2026-09-10. All values are 30d cumulative precipitation (mm) for the window ending one day before the reference date.

### Reference date 2024-07-01 — post-long-rains (window: 60d ending 2024-06-30)

| Location | Ecology | Source | 7d mm | 30d mm | 60d mm |
|----------|---------|--------|------:|-------:|-------:|
| Kisumu | lake_basin | Open-Meteo/ERA5-Land | 4.1 | 43.0 | 112.4 |
| Kisumu | lake_basin | NASA POWER/MERRA-2 | 20.2 | 205.2 | 629.3 |
| Nairobi | highland | Open-Meteo/ERA5-Land | 0.7 | 25.7 | 93.6 |
| Nairobi | highland | NASA POWER/MERRA-2 | 0.8 | 17.3 | 66.6 |
| Garissa | arid_semi_arid | Open-Meteo/ERA5-Land | 1.4 | 6.7 | 19.6 |
| Garissa | arid_semi_arid | NASA POWER/MERRA-2 | 1.6 | 9.8 | 49.3 |
| Mombasa | coast | Open-Meteo/ERA5-Land | 21.7 | 76.9 | 183.1 |
| Mombasa | coast | NASA POWER/MERRA-2 | 10.5 | 87.2 | 216.4 |
| Turkana | arid_semi_arid | Open-Meteo/ERA5-Land | 0.0 | 0.8 | 74.0 |
| Turkana | arid_semi_arid | NASA POWER/MERRA-2 | 0.2 | 6.1 | 37.1 |

### Reference date 2023-12-01 — short-rains onset (window: 60d ending 2023-11-30)

| Location | Ecology | Source | 7d mm | 30d mm | 60d mm |
|----------|---------|--------|------:|-------:|-------:|
| Kisumu | lake_basin | Open-Meteo/ERA5-Land | 28.1 | 131.3 | 208.7 |
| Kisumu | lake_basin | NASA POWER/MERRA-2 | 113.5 | 683.1 | 972.0 |
| Nairobi | highland | Open-Meteo/ERA5-Land | 27.8 | 183.9 | 240.6 |
| Nairobi | highland | NASA POWER/MERRA-2 | 31.9 | 158.1 | 202.9 |
| Garissa | arid_semi_arid | Open-Meteo/ERA5-Land | 53.8 | 286.7 | 304.1 |
| Garissa | arid_semi_arid | NASA POWER/MERRA-2 | 29.3 | 319.1 | 377.6 |
| Mombasa | coast | Open-Meteo/ERA5-Land | 57.4 | 364.3 | 464.1 |
| Mombasa | coast | NASA POWER/MERRA-2 | 57.8 | 387.4 | 502.4 |
| Turkana | arid_semi_arid | Open-Meteo/ERA5-Land | 4.2 | 96.3 | 279.6 |
| Turkana | arid_semi_arid | NASA POWER/MERRA-2 | 3.4 | 77.0 | 96.6 |

### Reference date 2024-02-01 — dry season (window: 60d ending 2024-01-31)

| Location | Ecology | Source | 7d mm | 30d mm | 60d mm |
|----------|---------|--------|------:|-------:|-------:|
| Kisumu | lake_basin | Open-Meteo/ERA5-Land | 3.5 | 122.4 | 172.2 |
| Kisumu | lake_basin | NASA POWER/MERRA-2 | 8.4 | 151.1 | 264.5 |
| Nairobi | highland | Open-Meteo/ERA5-Land | 3.9 | 82.1 | 118.7 |
| Nairobi | highland | NASA POWER/MERRA-2 | 3.2 | 79.1 | 106.1 |
| Garissa | arid_semi_arid | Open-Meteo/ERA5-Land | 0.7 | 10.7 | 30.7 |
| Garissa | arid_semi_arid | NASA POWER/MERRA-2 | 0.7 | 11.9 | 52.4 |
| Mombasa | coast | Open-Meteo/ERA5-Land | 13.1 | 130.9 | 296.2 |
| Mombasa | coast | NASA POWER/MERRA-2 | 1.3 | 28.3 | 120.3 |
| Turkana | arid_semi_arid | Open-Meteo/ERA5-Land | 0.7 | 7.5 | 41.3 |
| Turkana | arid_semi_arid | NASA POWER/MERRA-2 | 0.0 | 42.0 | 50.5 |

---

## Source decision

**Open-Meteo/ERA5-Land is the Phase 9 live source, with one known limitation:**

| Ecology | ERA5-Land acceptability | Basis |
|---------|------------------------|-------|
| lake_basin (Kisumu) | Acceptable | CHIRPS confirms ERA5-Land within 1.15–1.45x across two wet-season windows. MERRA-2 was over-estimating ~4–5x. |
| highland (Nairobi) | Acceptable | ERA5-Land and MERRA-2 agree within 1.5x across all three dates. No CHIRPS check performed (not flagged as discrepant). |
| arid_semi_arid (Garissa, Turkana) | Acceptable for dry-period signal suppression | Both sources show low/near-zero in dry periods. CHIRPS check not performed; ASAL gauge density is low but directional agreement is sufficient for suppression. |
| coast (Mombasa) | **Acceptable in wet season; biased in dry season** | ERA5-Land over-estimates ~6.7x during Jan–Feb (northeast monsoon transition). CHIRPS and MERRA-2 agree on lower values. Do not use ERA5-Land for coast dry-season thresholds without adjustment. |

**Implication for signal thresholds (when defined):**  
Coast (`dry_dusty_season`, `water_scarcity`) thresholds must not be calibrated from ERA5-Land Jan–Feb data. Use CHIRPS or a corrected product for coast dry-season calibration. All other ecologies and seasons: ERA5-Land is acceptable as the calibration source.

**No code changes required.** The `OpenMeteoProvider` interface is correct. The coast dry-season bias is a data quality constraint on future threshold calibration, not a provider architecture issue.

---

## What remains to be done before activating rainfall signals

1. Establish multi-year historical baseline for each ecology and signal window (minimum 5 years of ERA5-Land data per site, before defining anomaly thresholds).
2. Define signal activation thresholds for each ecology except coast dry-season (requires CHIRPS or corrected source for that specific window).
3. Replace `StaticCalendarProvider` signal gating with observed-rainfall thresholds per signal, once thresholds are validated against encounter data.
4. For coast ecology Jan–Feb: decide whether to use CHIRPS directly or apply a bias correction to ERA5-Land (ClimateSERV would provide CHIRPS for this use case).
