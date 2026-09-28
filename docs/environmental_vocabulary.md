# Environmental Signal Vocabulary

> Controlled values for `environmental_signals` blocks in condition cards.
> See `CLAUDE.md` → Frontmatter Schema Reference for field structure.

---

## Signal Vocabulary

| Signal | Description |
|--------|-------------|
| `post_long_rains` | 4–8 weeks after Kenya long rains (March–May) |
| `post_short_rains` | 4–8 weeks after Kenya short rains (October–November) |
| `flooding` | Active flooding or heavy localised rainfall causing water contamination |
| `water_scarcity` | Prolonged dry spell reducing safe water access |
| `prolonged_drought` | Multi-month drought causing nutritional vulnerability |
| `dry_dusty_season` | Northeast monsoon dry season (November–March); mucosal drying |
| `cold_dry_season` | Highland cold season (June–August); indoor crowding |
| `heat_dehydration` | Hot dry season causing dehydration stress |

## Pathway Vocabulary
`vector_borne` | `waterborne` | `zoonotic` | `respiratory_mucosal` | `nutritional_vulnerability` | `airborne`

## Effect Type Vocabulary
`transmission_opportunity` — environmental condition increases disease acquisition risk
`severity_modifier` — environmental condition worsens disease severity or complications (does not increase incidence)

## Causal Distance Vocabulary
`direct` — signal operates via ≤2 causal steps with established epidemiological evidence
`indirect` — signal operates via ≥3 steps or through a behavioral/physiological intermediate. Requires more hedged language in context engine output. Never overrides strong clinical evidence.

## Evidence Type Vocabulary
`observed_outbreaks` | `surveillance_data` | `regional_epidemiological_evidence` | `expert_estimate`

## Exposure Vocabulary (patient-documented)
`floodwater_contact` | `livestock_contact` | `occupational_dust` | `unsafe_water` | `mosquito_exposure_high` | `pastoralist_mobility` | `fishing_lakeshore`

## Seasonal Basis Values
`typical_long_rains` | `typical_short_rains` | `dry_season` | `perennial` | `outbreak_associated`
