# CLAUDE.md

## Commands

```bash
make setup                  # uv sync --group dev + playwright install chromium
make test                   # uv run pytest -q
make help                   # list every pipeline target (this is .DEFAULT_GOAL)
uv run pytest tests/test_admin.py::test_name -q     # run a single test
uv run ruff check .         # lint (there is NO make target; config lives in pyproject [tool.ruff])
```

- Every module runs as `uv run python -m ev_siting.<package>.<module>`. Each `paths.py` anchors `PROJECT_ROOT` from its own file location, so modules work from any working directory.
- City-scoped targets take a `CITY` variable (default `hanoi`): `make landuse CITY=hcm`. Nationwide runs are separate targets with a `-national` suffix.
- `make verify-snapshot HASHES=1` is the only form that actually compares content; without `HASHES` it only checks metadata.
- `.github/workflows/ci.yml` **is not a real gate**: it runs `pip install -r requirements.txt || true` (that file does not exist) and `pytest -q || true`. Never trust a green CI here — run `make test` locally..

## Documentation hierarchy (important — docs contradict each other on purpose)

| Role                                                   | File                                                                                                    |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------- |
| **Current problem statement**                    | `docs/de-bai-v2.md` (29 Jul) — supersedes the *problem definition* part of `problem-analysis.md` |
| **Issue register — source of truth for status** | `docs/known-issues.md` (P1–P11 · E-DQ1–12 · F · G)                                               |
| Per-issue detail                                       | `docs/issues/<group>/<id>.md` — one file per issue                                                   |
| Data-layer architecture                                | `docs/data-layer/overview.md`                                                                         |
| Data↔Model schema contract                            | `docs/schema/schema-contract.md`                                                                      |

## Architecture

Six public sources, self-crawled, converging into **two output groups**:

- **Supply (canonical):** `stations` (key `station_id`) + `connectors` (FK `station_id`), Parquet, Hive-partitioned by `province_code`.
- **Demand:** `demand_h3` (key `h3_r8`, H3 res 8) + `admin/cell_commune` → rolled up into `admin/demand_commune`.

Each source is a sub-package under `src/ev_siting/data/` (`evcs`, `vinfast_official`, `osm`, `overture`, `worldpop`, `vnsdi`, `admin`, `landuse`, `provenance`), and each owns a `paths.py` holding its paths and constants (bbox, H3 res, URLs). Outside `data/`: `aoi.py`, `features/`, `models/`, `viz/`.

`overture` is a **verification** source, not a demand input (E-DQ7g): it scans Overture Places off S3 with DuckDB (`make overture-fetch` → `make overture` → `make overture-compare`) and stops at `data/interim/overture/`. Nothing under `demand_h3` reads it — merging the two POI layers into one feature is E-DQ7d's call.

**Minimum reproduction order:**

- Supply: `freeze` → `crawl` → `official` → `match-official` → `canonical` → `admin-stations`
- Demand: `boundary` → `osm` + WorldPop → `vnsdi` → `reconcile-pop` → `reallocate-roadless` → `demand` → `admin-grid`

`aoi.py` provides a **duck-typed** AOI: `AOI` (centre + radius, from city presets) and `NationalAOI` (reads the national `demand_h3` grid directly) expose the same `bbox()/contains()/in_core()/cells()/to_dict()` interface. CLIs wire it up with `add_aoi_args(parser)` + `aoi_from_args(args)`, so consuming modules never need to know whether they are running city-scoped or nationwide.

## Invariants and traps (read before touching the data)

The following are **settled decisions**; breaking them corrupts everything downstream:

- **The supply set used for T0/coverage** is `is_operational & access == 'PUBLIC' & is_primary & coord_resolved` — not all of `stations`. `clean_supply.csv` is merely an export produced by `export_supply.py`; the truth is `canonical/stations` plus this formula.
- **H3 res 8, centre-to-centre `d` = 0.98 km. The service radius `R` must be > `d`** (baseline R = 3 km). If `R < d`, MCLP degenerates into `sort top-p` (P4). Assert `R > d` before computing coverage.
- **`connectors` is the single source of truth for the LIVE layer.** Since 31 Jul, `stations` no longer carries `current_type` / `max_power_kw` / `total_power_kw` / `num_connectors` / `connector_types` — roll them up via `evcs.connector_rollup.attach()`. The ASSET (installed) layer is a separate set of columns: `n_guns_installed`, `site_power_kw`, `current_type_asset`, … The two layers **coexist; neither replaces the other** (E-DQ4).
- **`province_code` (the OLD 63-province system) ≠ `admin_l1_code` (the 34-province system, VNSDI 2025-06-16).** Both are kept; the crosswalk is at `data/interim/admin/province_crosswalk.csv`. Any province-level report must state which system it uses.
- **`pop` vs `pop_adj` — two columns, two jobs.** `pop` is for ABSOLUTE statements (`coverage_pop`, reconciliation against GSO) and is bit-for-bit invariant. `pop_adj` is for RANKING consumers (demand_weight, gap-fill). Never swap them.
- **A cell's commune label is not its allocation unit.** `commune_code` on `demand_h3` is the **argmax** by area weight; allocating mass must go through `cell_commune` (Σw = 1 per cell) — about 39.8% of the population sits in cells straddling ≥ 2 communes. Do not `groupby(commune_name)`.
- **`demand_h3` is not a tessellation** — it is the union of cells that *have features*, so operational stations exist that have no row in any grid table (E-DQ8c, still open).
- **Two parallel keys:** `station_code` (evcs.vn) and `station_id` (canonical). Keep both for traceability. Joining against the official registry uses `station_code == store_id` (exact).
- **Status/access resolution is official-first**; coordinate resolution is deliberately **inverted** (E-DQ1). Only `OUT_OF_SERVICE` is hard-filtered.
- `n_poi` / `n_parking` / `road_len_mt_m` are **retired** (E-DQ7b/7c). `osm_poi_points` is **fail-closed**: it contains only `in_vn=True` rows.
- **A missing POI class looks exactly like a sparse one.** `PARK` read as "OSM has almost no parks" for weeks while the real cause was that `overpass_poi.CATEGORIES` had no group producing it — every QA gate loops over `CLASSES`, so a class that does not exist is never measured (E-DQ7g). Adding a class is additive: append to `poi_semantics.CLASSES`, and leave `DERIVED_COLUMNS` alone unless E-DQ7d asks for the feature.
- **Overture: a bigger count is not better coverage.** Its `shopping_center` outnumbers OSM's malls 22×, but only 8.4% of those names carry a mall noun — it is a business directory, and only `FUEL` survives the label-noise check (93.6%). Overture also has **no object-level edit date** in VN (`update_time` is the provider's batch-drop date, one distinct value for 99% of points); OSM does, read from the frozen `.pbf` via `poi_timestamps.py` since the Overpass raw carries no `meta`.
- **Cross-source spatial matching must not use `poi_semantics.neighbour_pairs` above ~185 m** — it buckets at H3 res 9, so wider radii silently miss real pairs. `compare_osm._cross_pairs` buckets at res 8 (guaranteed to ~490 m) and refuses anything beyond.
- Supply scope is **car charging stations only**; `BATTERY_SWAP` is dropped by default (keep it with `--keep-bss`). `current_type` is derived from the official connector standard, **not** from a kW threshold (P7).

## Pipeline safety gates

- **F7 — xref gate:** `transform_canonical.join_xref()` fails fast when `official_xref.parquet` is missing or stale (it compares `source_master_sha256` byte-for-byte against the master). Recovery must be explicit via `--allow-missing-xref`. This is why the `canonical` target depends on `match-official`.
- **F12 — atomic write:** `_write_partitioned_atomically()` builds both datasets off-path and then swaps a whole generation. Never write directly into `canonical/`.
- **E-DQ10 — provenance:** `make freeze` produces `MANIFEST.json` and applies the read-only lock; `make verify-snapshot` must PASS before trusting any measurement.
- Several modules expose `--dump` / `--check` to score their QA gates without writing files (`resolve-config`, `admin-stations`, `export-supply-check`).

## Hard-won pipeline lessons

- `fetch_locators parse` must run **after** `detail` completes (check `details.done`), otherwise the official Parquet ends up with only ~202 of 23,240 rows.
- Overpass times out on large bboxes → `overpass_poi.py` splits the bbox with a quadtree.
- The 318 MB `.pbf` does not fit in RAM → stream it way-by-way with osmium, accumulating per H3 cell.
- Telemetry exists in **two sampling generations** (168h and 720h) whose timestamps almost never overlap — **never blindly union them**. Select with the `EVCS_TS_DIR` env var (defaults to 720h).

## Not yet implemented (stubs)

`features/build_demand_proxy.py` (`demand_weight` — E-DQ7d), `models/mclp.py`, `viz/export_geojson.py`, and the PostGIS load (`config/db/migrations` and `seeds` are empty). The `make proxy` / `make model` targets only print a TODO.

Ownership: **Giang** owns the data layer; **Kỳ** owns the demand proxy and MCLP. The handoff points are defined in `docs/schema/schema-contract.md`.

## Licensing and data handling

evcs.vn/tramev sources are ToS-restricted, and tables blended with OSM are ODbL-derived. Read item **F1** in `docs/known-issues.md` before publishing any data.
