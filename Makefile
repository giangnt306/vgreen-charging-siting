.PHONY: help data proxy model opex-electricity crawl crawl-validate canonical official landuse candidates landuse-national candidates-national

CITY ?= hanoi

help:  ## Show this help (list all commands)
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

data:  ## Prepare data directories and run ETL scripts
	@echo "Prepare data directories and run ETL scripts"

opex-electricity:  ## Build EV-charging electricity tariff (OpEx) -> data/external/
	PYTHONPATH=src python -m ev_siting.data.opex_electricity

crawl:  ## Run full EVCS crawl pipeline (enum -> scrape -> split -> master -> QA)
	bash src/ev_siting/data/evcs/run_pipeline.sh

crawl-validate:  ## Re-run only the EVCS QA gate over existing data/interim
	PYTHONPATH=src python -m ev_siting.data.evcs.validate

canonical:  ## Transform master CSV -> canonical parquet (stations/connectors, car-only)
	PYTHONPATH=src python -m ev_siting.data.evcs.transform_canonical

official:  ## Fetch official VinFast source registry (verified cross-ref) -> data/interim/vinfast_official/
	PYTHONPATH=src python -m ev_siting.data.vinfast_official.fetch_locators bulk

landuse:  ## Build buildable_h3 land-use filter for CITY (WorldCover + OSM + road)  [P5]
	PYTHONPATH=src python -m ev_siting.data.landuse.worldcover --city $(CITY)
	PYTHONPATH=src python -m ev_siting.data.landuse.osm_exclusion --city $(CITY)
	PYTHONPATH=src python -m ev_siting.data.landuse.build_buildable_h3 --city $(CITY)
	PYTHONPATH=src python -m ev_siting.data.landuse.validate

candidates:  ## Build MCLP candidate sites for CITY (needs `make landuse` first)  [P5]
	PYTHONPATH=src python -m ev_siting.features.build_candidates --city $(CITY)

landuse-national:  ## Build buildable_h3 for ALL Vietnam (national grid, ~1.5GB WorldCover)  [P5]
	PYTHONPATH=src python -m ev_siting.data.landuse.worldcover --national
	PYTHONPATH=src python -m ev_siting.data.landuse.osm_exclusion --national
	PYTHONPATH=src python -m ev_siting.data.landuse.build_buildable_h3 --national
	PYTHONPATH=src python -m ev_siting.data.landuse.validate

candidates-national:  ## Build MCLP candidate sites for ALL Vietnam (needs `make landuse-national`)  [P5]
	PYTHONPATH=src python -m ev_siting.features.build_candidates --national

proxy:  ## Build or refresh demand proxy
	@echo "Build or refresh demand proxy"

model:  ## Run model training / optimization
	@echo "Run model training / optimization"

.DEFAULT_GOAL := help
