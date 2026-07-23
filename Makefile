.PHONY: help data proxy model opex-electricity crawl crawl-validate canonical official

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

proxy:  ## Build or refresh demand proxy
	@echo "Build or refresh demand proxy"

model:  ## Run model training / optimization
	@echo "Run model training / optimization"

.DEFAULT_GOAL := help
