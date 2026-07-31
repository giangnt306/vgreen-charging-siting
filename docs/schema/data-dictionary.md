# Data Dictionary

Describe data sources, variable names, types, and meanings here.

## EVCS canonical and candidate-site contract

| Dataset | Canonical path | Keys | Fields whose meaning is easy to misuse |
| --- | --- | --- | --- |
| `stations` | `data/interim/canonical/stations/` | `station_id`; source key `station_code` | `lat/lng` are resolved coordinates; retain `lat_raw/lng_raw`, `coord_src` (`evcs`/`official`/`placeholder`), `coord_fix_dist_m`, `coord_resolved` for E-DQ1 audit — unresolved placeholder rows have `h3_r8=NULL`. **Since 31/07 the 5 LIVE columns (`current_type`, `max_power_kw`, `total_power_kw`, `num_connectors`, `connector_types`) no longer live here** — they were an exact copy of `connectors` and drifted after P7; derive them via `evcs.connector_rollup`. Use `current_type_asset` (ASSET layer, E-DQ4) for stratification — it is *not* derivable from `connectors`. Use only `is_primary=True`, `is_operational=True`, `access!=RESTRICTED`, `coord_resolved=True` for incumbent supply. |
| `connectors` | `data/interim/canonical/connectors/` | `connector_id`; FK `station_id` | `connector_standard` comes from the first-party registry where matched; otherwise `UNKNOWN` (no fallback exists for plug standard). `current_type` falls back to the 25 kW tier for evcs-only rows (Q5). `count_total` is connector count. |
| `candidate_sites` | `data/processed/candidate_sites.{parquet,geojson}` | `candidate_id`; one per `h3_r8` | Hard exclusions (WATER/WETLAND/`NOT_BUILT_UP`/legal OSM/`ROAD_ACCESS_ISOLATED`) are applied **before** this table — `exclusion_flags` is empty in the delivered set and exists for audit. Soft feasibility lives in `penalty` (per-flag detail in `buildable_h3.penalty_flags`, not exported here). `province_code` is the OLD 63-province code (null on non-station candidates) — admin labels come from `demand_h3` via `h3_r8` (E-DQ3). `is_existing=True` is incumbent / CapEx=0. |

`n_charging_snapshot` in the crawl-shaped master is a point-in-time API value (cars
charging right now); it is not a connector count and is intentionally not exported
as `num_ports`.

## OpEx - Electricity tariff for EV charging stations

**Pipeline:** [`src/ev_siting/data/opex_electricity.py`](../../src/ev_siting/data/opex_electricity.py)
· run with `make opex-electricity` (or `PYTHONPATH=src python -m ev_siting.data.opex_electricity`).

**Outputs** (to `data/external/`, gitignored — regenerate any time):

- `opex_electricity_tariff.csv` — tidy table, one row per (voltage group × time-of-use band).
- `opex_electricity_tariff.json` — same rows + provenance metadata (sources, base price, TOU windows).

### Sources

| Component                                              | Value                     | Source                                                                                                 |
| ------------------------------------------------------ | ------------------------- | ------------------------------------------------------------------------------------------------------ |
| Tariff structure (% of avg retail price)               | see matrix below          | **QĐ 14/2025/QĐ-TTg** (29/05/2025), mục 3.2 — giá bán điện cho trạm/trụ sạc xe điện |
| Base average retail price (`base_avg_price_vnd_kwh`) | **2,204.07 đ/kWh** | **QĐ 1279/QĐ-BCT** (09/05/2025), hiệu lực 10/05/2025                                         |

Only the **base average price** is volatile (changes when EVN adjusts the average
retail price); the % structure is fixed by decision. Refresh with
`python -m ev_siting.data.opex_electricity --base-price <new_value>`.
QĐ 14/2025 caps this tariff structure at 3 years from its implementation date.

### Tariff matrix (đ/kWh @ base 2,204.07)

| Voltage group                    | Bình thường (normal) | Thấp điểm (off-peak) | Cao điểm (peak) |
| -------------------------------- | ----------------------: | ----------------------: | ----------------: |
| Từ trung áp trở lên (> 1 kV) |        118% → 2,600.80 |         71% → 1,564.89 |  174% → 3,835.08 |
| Hạ áp (≤ 1 kV)                |        125% → 2,755.09 |         75% → 1,653.05 |  195% → 4,297.94 |

Range: **1,564.89 – 4,297.94 đ/kWh**.

### Time-of-use (TOU) windows

- **Cao điểm (peak):** Mon–Sat 09:30–11:30 & 17:00–20:00; no peak on Sundays.
- **Thấp điểm (off-peak):** every day 22:00–04:00.
- **Bình thường (normal):** all remaining hours.

### Fields (`opex_electricity_tariff.csv`)

| Column                  | Type  | Meaning                                                    |
| ----------------------- | ----- | ---------------------------------------------------------- |
| `voltage_group`       | str   | `tren_1kv` (> 1 kV) or `den_1kv` (≤ 1 kV)             |
| `voltage_group_label` | str   | Human-readable Vietnamese label                            |
| `tou_band`            | str   | `binh_thuong` / `thap_diem` / `cao_diem`             |
| `tou_band_label`      | str   | Human-readable Vietnamese label                            |
| `percent_of_avg`      | float | % of base average retail price (from the decision)         |
| `price_vnd_kwh`       | float | Computed price =`percent_of_avg / 100 × base_avg_price` |

### Using it in the model

The OpEx electricity term wants an **expected buy price per kWh** given how charging
demand is spread across TOU bands. Use `OpexElectricityTariff.blended_price_vnd_kwh( voltage_group, energy_share=...)` where `energy_share` is the fraction of kWh charged
in each band, e.g. `{"cao_diem": 0.2, "binh_thuong": 0.5, "thap_diem": 0.3}`. Without
a profile it falls back to clock-hour weights (assumes flat charging — usually
optimistic on peak share).
