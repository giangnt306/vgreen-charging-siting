.PHONY: data proxy model

data:
	@echo "Prepare data directories and run ETL scripts"

proxy:
	@echo "Build or refresh demand proxy"

model:
	@echo "Run model training / optimization"
