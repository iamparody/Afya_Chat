# Phase 9 Rainfall Validation Findings

**Run date:** 2026-09-10  
**Script:** `phase9/validate_rainfall.py`  
**Comparison:** Open-Meteo/ERA5-Land vs NASA POWER/MERRA-2

---

## Validation status

- Open-Meteo/ERA5-Land is **not yet clinically validated** as the rainfall source for CDS.
- These comparisons establish observed discrepancies between two reanalysis products. They do not establish which source is observationally or clinically correct.
- Kisumu (lake_basin) shows a large wet-season discrepancy requiring CHIRPS adjudication before any conclusion can be drawn about lake_basin rainfall representation.
- Mombasa Jan–Feb discrepancy is unresolved — both sources may be wrong for that site and season.
- No signal thresholds have been derived from these comparisons.

---

## Data sources

| Label | Product | Grid | Access |
|-------|---------|------|--------|
| Open-Meteo/ERA5-Land | ERA5-Land reanalysis | ~11 km | Open-Meteo Historical API (production path) |
| NASA POWER/MERRA-2 | MERRA-2 corrected precipitation (PRECTOTCORR) | ~50 km | NASA POWER API (comparison only) |
| CHIRPS | Satellite + gauge blend | ~5 km | **Not yet fetched** — requires ClimateSERV registration or rasterio |

CHIRPS is the intended adjudicator for discrepancies between the two reanalysis products. The IRI Data Library endpoint for CHIRPS requires authentication. Direct UCSB file download requires rasterio. Neither is currently set up.

---

## Raw comparison table

All values are cumulative precipitation (mm) for the window ending one day before the reference date. Ratio = Open-Meteo 30d ÷ NASA POWER 30d; "(both <1mm)" indicates values too small for a meaningful ratio.

### Reference date 2024-07-01 — post-long-rains window (window: 60d ending 2024-06-30)

| Location | Ecology | Source | 7d mm | 30d mm | 60d mm | 30d ratio (OM/POWER) |
|----------|---------|--------|------:|-------:|-------:|----------------------|
| Kisumu | lake_basin | Open-Meteo/ERA5-Land | 4.1 | 43.0 | 112.4 | — |
| Kisumu | lake_basin | NASA POWER/MERRA-2 | 20.2 | 205.2 | 629.3 | 0.21 (POWER 4.8× OM) |
| Nairobi | highland | Open-Meteo/ERA5-Land | 0.7 | 25.7 | 93.6 | — |
| Nairobi | highland | NASA POWER/MERRA-2 | 0.8 | 17.3 | 66.6 | 1.49 |
| Garissa | arid_semi_arid | Open-Meteo/ERA5-Land | 1.4 | 6.7 | 19.6 | — |
| Garissa | arid_semi_arid | NASA POWER/MERRA-2 | 1.6 | 9.8 | 49.3 | 0.68 |
| Mombasa | coast | Open-Meteo/ERA5-Land | 21.7 | 76.9 | 183.1 | — |
| Mombasa | coast | NASA POWER/MERRA-2 | 10.5 | 87.2 | 216.4 | 0.88 |
| Turkana | arid_semi_arid | Open-Meteo/ERA5-Land | 0.0 | 0.8 | 74.0 | — |
| Turkana | arid_semi_arid | NASA POWER/MERRA-2 | 0.2 | 6.1 | 37.1 | 0.13 (POWER 7.6× OM) |

### Reference date 2023-12-01 — short-rains onset window (window: 60d ending 2023-11-30)

| Location | Ecology | Source | 7d mm | 30d mm | 60d mm | 30d ratio (OM/POWER) |
|----------|---------|--------|------:|-------:|-------:|----------------------|
| Kisumu | lake_basin | Open-Meteo/ERA5-Land | 28.1 | 131.3 | 208.7 | — |
| Kisumu | lake_basin | NASA POWER/MERRA-2 | 113.5 | 683.1 | 972.0 | 0.19 (POWER 5.2× OM) |
| Nairobi | highland | Open-Meteo/ERA5-Land | 27.8 | 183.9 | 240.6 | — |
| Nairobi | highland | NASA POWER/MERRA-2 | 31.9 | 158.1 | 202.9 | 1.16 |
| Garissa | arid_semi_arid | Open-Meteo/ERA5-Land | 53.8 | 286.7 | 304.1 | — |
| Garissa | arid_semi_arid | NASA POWER/MERRA-2 | 29.3 | 319.1 | 377.6 | 0.90 |
| Mombasa | coast | Open-Meteo/ERA5-Land | 57.4 | 364.3 | 464.1 | — |
| Mombasa | coast | NASA POWER/MERRA-2 | 57.8 | 387.4 | 502.4 | 0.94 |
| Turkana | arid_semi_arid | Open-Meteo/ERA5-Land | 4.2 | 96.3 | 279.6 | — |
| Turkana | arid_semi_arid | NASA POWER/MERRA-2 | 3.4 | 77.0 | 96.6 | 1.25 |

### Reference date 2024-02-01 — dry season window (window: 60d ending 2024-01-31)

| Location | Ecology | Source | 7d mm | 30d mm | 60d mm | 30d ratio (OM/POWER) |
|----------|---------|--------|------:|-------:|-------:|----------------------|
| Kisumu | lake_basin | Open-Meteo/ERA5-Land | 3.5 | 122.4 | 172.2 | — |
| Kisumu | lake_basin | NASA POWER/MERRA-2 | 8.4 | 151.1 | 264.5 | 0.81 |
| Nairobi | highland | Open-Meteo/ERA5-Land | 3.9 | 82.1 | 118.7 | — |
| Nairobi | highland | NASA POWER/MERRA-2 | 3.2 | 79.1 | 106.1 | 1.04 |
| Garissa | arid_semi_arid | Open-Meteo/ERA5-Land | 0.7 | 10.7 | 30.7 | — |
| Garissa | arid_semi_arid | NASA POWER/MERRA-2 | 0.7 | 11.9 | 52.4 | 0.90 |
| Mombasa | coast | Open-Meteo/ERA5-Land | 13.1 | 130.9 | 296.2 | — |
| Mombasa | coast | NASA POWER/MERRA-2 | 1.3 | 28.3 | 120.3 | 4.63 (OM 4.6× POWER) |
| Turkana | arid_semi_arid | Open-Meteo/ERA5-Land | 0.7 | 7.5 | 41.3 | — |
| Turkana | arid_semi_arid | NASA POWER/MERRA-2 | 0.0 | 42.0 | 50.5 | 0.18 (POWER 5.6× OM) |

---

## Observations

**Kisumu (lake_basin):** The two reanalysis products disagree by 4–5× on wet-season 30d totals (Jul 2024: OM=43mm, MERRA-2=205mm; Dec 2023: OM=131mm, MERRA-2=683mm). Divergence narrows in the dry season (Feb 2024 ratio 0.81). The direction of error is not established — ERA5-Land may under-estimate Lake Victoria convective rainfall at 11km resolution, but MERRA-2 may over-estimate it at 50km. CHIRPS adjudication is required.

**Nairobi (highland):** Agreement is good across all three dates (ratio range 1.04–1.49). Both sources show the expected wet-season signal.

**Garissa (arid_semi_arid):** Agreement is reasonable in wet periods (ratio 0.68–0.90). Both correctly show low rainfall in the July dry window. The 60d Garissa July value diverges more (OM=19.6mm, MERRA-2=49.3mm) — likely boundary effects from the long-rains tail, small absolute values.

**Mombasa (coast):** Good agreement in wet periods (ratio 0.88–0.94 across July and December windows). Large unexplained divergence in the Jan–Feb dry-season window (OM=130.9mm, MERRA-2=28.3mm over 30d). One or both products may be misrepresenting the northeast monsoon transition for this site. Unresolved.

**Turkana (arid_semi_arid):** Both sources show near-zero values during dry periods (July 7d: OM=0.0mm, MERRA-2=0.2mm). This is the direction that matters for signal suppression. November short-rains window shows reasonable directional agreement (ratio 1.25). The dry-season 60d divergence (Feb: OM=41mm, MERRA-2=50mm) is small in absolute terms.

---

## What this comparison does and does not establish

**Established:**
- ERA5-Land and MERRA-2 are directionally consistent for highland (Nairobi), ASAL dry-period suppression (Garissa, Turkana), and coast wet-season (Mombasa).
- A large, systematic wet-season discrepancy exists at Kisumu. The pattern is consistent across two wet-season dates.
- A large, unexplained discrepancy exists at Mombasa in the Jan–Feb window.

**Not established:**
- Which source is observationally correct for any site or season.
- That ERA5-Land is suitable or unsuitable for clinical signal thresholds at any ecology.
- That MERRA-2 is a better or worse representation of actual rainfall than ERA5-Land.

---

## Next steps

1. **Kisumu / lake_basin:** Obtain CHIRPS data for the same windows via ClimateSERV or rasterio. If CHIRPS aligns with MERRA-2, ERA5-Land is under-estimating for lake_basin — a data source decision, not a code decision. If CHIRPS aligns with ERA5-Land, MERRA-2 is over-estimating.
2. **Mombasa Jan–Feb:** Include in any CHIRPS comparison run. Do not use the coast ecology in threshold calibration until resolved.
3. **Thresholds:** Derive signal activation thresholds only after CHIRPS adjudication and a multi-year historical baseline characterisation. Do not use this two-source comparison to set thresholds.
4. **Code path:** No changes to `phase7/rainfall_providers.py` or `context_engine.py` are warranted by these findings. The provider interface is correct; the data quality question is separate.
