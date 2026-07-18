.PHONY: help data proxy model opex-electricity

help:  ## Show this help (list all commands)
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

data:  ## Prepare data directories and run ETL scripts
	@echo "Prepare data directories and run ETL scripts"

opex-electricity:  ## Build EV-charging electricity tariff (OpEx) -> data/external/
	PYTHONPATH=src python -m ev_siting.data.opex_electricity

proxy:  ## Build or refresh demand proxy
	@echo "Build or refresh demand proxy"

model:  ## Run model training / optimization
	@echo "Run model training / optimization"

.DEFAULT_GOAL := help
