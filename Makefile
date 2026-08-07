.PHONY: help setup test settlement export-handoff data proxy model opex-electricity crawl crawl-validate match-official canonical discover-new resolve-config official landuse candidates landuse-national candidates-national covered0 covered0-national freeze verify-snapshot boundary osm demand poi-recall poi-timestamps overture-fetch overture overture-compare vnsdi reconcile-pop reallocate-roadless admin-stations admin-grid export-supply export-supply-check

CITY ?= hanoi
PY = uv run python

help:  ## Show this help (list all commands)
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

setup:  ## Install env (uv sync) + Playwright browser for the crawl layer
	uv sync --group dev
	uv run playwright install chromium

test:  ## Run unit tests
	uv run pytest -q

data:  ## Prepare data directories and run ETL scripts
	@echo "Prepare data directories and run ETL scripts"

opex-electricity:  ## Build EV-charging electricity tariff (OpEx) -> data/external/
	$(PY) -m ev_siting.data.opex_electricity

freeze:  ## Freeze raw inputs -> data/raw/MANIFEST.json (checksums + read-only lock)  [E-DQ10]
	$(PY) -m ev_siting.data.provenance.freeze_snapshot

verify-snapshot:  ## Verify raw inputs match frozen snapshot (add HASHES=1 for full content check)  [E-DQ10]
	$(PY) -m ev_siting.data.provenance.freeze_snapshot --verify $(if $(HASHES),--hashes,)

crawl:  ## Run full EVCS crawl pipeline (enum -> scrape -> split -> master -> QA)
	bash src/ev_siting/data/evcs/run_pipeline.sh

crawl-validate:  ## Re-run only the EVCS QA gate over existing data/interim
	$(PY) -m ev_siting.data.evcs.validate

match-official:  ## Match current master with official registry -> verified xref (F7)
	$(PY) -m ev_siting.data.vinfast_official.match_official

canonical: match-official ## Transform master CSV -> canonical parquet (stations/connectors, car-only); xref current required (F7)
	$(PY) -m ev_siting.data.evcs.transform_canonical

resolve-config:  ## Inspect installed-config resolution (ASSET vs LIVE layer, 8 gates)  [E-DQ4]
	$(PY) -m ev_siting.data.evcs.resolve_config --dump

export-supply:  ## Regenerate clean_supply.csv + excluded.csv from canonical (6 gates)
	$(PY) -m ev_siting.data.evcs.export_supply

export-handoff:  ## Bundle ban giao lien-repo (FX-05: can TELEMETRY=<run.csv> hoac env EVCS_TS_RUN neu TS_DIR khac 168h)
	$(PY) -m ev_siting.data.evcs.export_handoff $(if $(TELEMETRY),--telemetry $(TELEMETRY),)

export-supply-check:  ## Score the export gates without writing the CSVs
	$(PY) -m ev_siting.data.evcs.export_supply --check

official:  ## Fetch official VinFast source registry (verified cross-ref) -> data/interim/vinfast_official/
	$(PY) -m ev_siting.data.vinfast_official.fetch_locators bulk

discover-new:  ## Tim tram evcs MOI bang seed co dich tu registry official (can `make official` truoc)  [L10]
	$(PY) -m ev_siting.data.evcs.evcs_enumerate --seed-from-official \
		--enrich-from data/interim/evcs_catalog.csv \
		--out data/raw/evcs/catalog/evcs_stations_$(shell date +%Y-%m-%d)-new.csv

vnsdi:  ## Crawl VNSDI commune polygons + population (2025) -> data/interim/vnsdi/  [E-DQ7f]
	$(PY) -m ev_siting.data.vnsdi.fetch_communes crawl
	$(PY) -m ev_siting.data.vnsdi.fetch_communes parse

reconcile-pop:  ## Detect+repair dasymetric spike -> worldpop_pop_adj_h3 (needs `make vnsdi`)  [E-DQ7f]
	$(PY) -m ev_siting.data.worldpop.reconcile_dasymetric

admin-stations:  ## Inspect admin labels + coordinate arbitration on stations (7 gates)  [E-DQ3]
	$(PY) -m ev_siting.data.admin.enrich_stations --dump

admin-grid:  ## Label demand_h3 with commune/province + build demand_commune rollup  [E-DQ3]
	$(PY) -m ev_siting.data.admin.enrich_grid

boundary:  ## Extract VN territory + province polygons from the frozen .pbf  [E-DQ7a, unlocks E-DQ3]
	$(PY) -m ev_siting.data.osm.vn_boundary

osm:  ## Rebuild OSM demand components (POI clipped + classified + deduped)  [E-DQ7a, E-DQ7c]
	$(PY) -m ev_siting.data.osm.build_osm_h3

poi-recall:  ## Measure OSM POI coverage against EV stations sited at fuel/parking  [E-DQ7c]
	$(PY) -m ev_siting.data.osm.poi_recall

poi-timestamps:  ## Attach OSM last-edit dates to POI points (reads frozen .pbf)  [E-DQ7g]
	$(PY) -m ev_siting.data.osm.poi_timestamps

overture-fetch:  ## Scan Overture Places (S3, DuckDB) over VN_BBOX -> data/raw/overture/
	$(PY) -m ev_siting.data.overture.fetch_places $(if $(RELEASE),--release $(RELEASE),)

overture:  ## Build overture_poi_points/h3 from the raw scan (needs `make overture-fetch`)
	$(PY) -m ev_siting.data.overture.build_poi

overture-compare:  ## Compare OSM vs Overture POI layers -> osm_vs_overture.{json,md}
	$(PY) -m ev_siting.data.overture.compare_osm

reallocate-roadless:  ## Move pop out of cells with no road access -> worldpop_pop_acc_h3  [E-DQ8b]
	$(PY) -m ev_siting.data.worldpop.reallocate_roadless

demand:  ## Rebuild demand_h3 grid (cells classified/clipped to VN territory)  [E-DQ7a, E-DQ7f, E-DQ8, E-DQ3]
	$(PY) -m ev_siting.data.worldpop.reconcile_dasymetric
	$(PY) -m ev_siting.data.worldpop.reallocate_roadless
	$(PY) -m ev_siting.data.worldpop.build_demand_h3
	$(PY) -m ev_siting.data.admin.enrich_grid
	$(PY) -m ev_siting.data.osm.validate

settlement:  ## Settlement mask + pop_k1 (pop tho + pop_2025) — chay SAU demand  [P10]
	$(PY) -m ev_siting.data.worldpop.settlement

landuse:  ## Build buildable_h3 land-use filter for CITY (WorldCover + OSM + road)  [P5]
	$(PY) -m ev_siting.data.landuse.worldcover --city $(CITY)
	$(PY) -m ev_siting.data.landuse.osm_exclusion --city $(CITY)
	$(PY) -m ev_siting.data.landuse.build_buildable_h3 --city $(CITY)
	$(PY) -m ev_siting.data.landuse.validate

candidates:  ## Build MCLP candidate sites for CITY (needs `make landuse` first)  [P5]
	$(PY) -m ev_siting.features.build_candidates --city $(CITY)

covered0:  ## Build planning + operational-only sensitivity baselines for CITY  [P8/F5]
	$(PY) -m ev_siting.features.build_covered0 --city $(CITY)

covered0-national:  ## Build planning + operational-only sensitivity baselines for ALL Vietnam  [P8/F5]
	$(PY) -m ev_siting.features.build_covered0 --national

landuse-national:  ## Build buildable_h3 for ALL Vietnam (national grid, ~1.5GB WorldCover)  [P5]
	$(PY) -m ev_siting.data.landuse.worldcover --national
	$(PY) -m ev_siting.data.landuse.osm_exclusion --national
	$(PY) -m ev_siting.data.landuse.build_buildable_h3 --national
	$(PY) -m ev_siting.data.landuse.validate

candidates-national:  ## Build MCLP candidate sites for ALL Vietnam (needs `make landuse-national`)  [P5]
	$(PY) -m ev_siting.features.build_candidates --national

proxy:  ## Build or refresh demand proxy  (TODO — build_demand_proxy còn là stub, xem F-register)
	@echo "TODO: demand proxy chưa được hiện thực (docs/known-issues.md §F)"

model:  ## Run model training / optimization  (TODO — mclp.py còn là stub)
	@echo "TODO: MCLP solver chưa được hiện thực (docs/known-issues.md §F)"

.DEFAULT_GOAL := help
