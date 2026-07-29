.PHONY: help setup test data proxy model mclp mclp-bench pilot spotcheck opex-electricity crawl crawl-validate canonical official match-official landuse candidates landuse-national candidates-national covered0 covered0-national freeze verify-snapshot assess assess-occupancy t1 sizing dossier

CITY ?= hanoi
LABEL ?= sprint2-2026-07-28
SCOPE ?= vietnam
HOST ?= 127.0.0.1
PORT ?= 8000
MODE ?= brownfield
P ?= 100
PY = uv run python

help:  ## Show this help (list all commands)
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

setup:  ## Install env (uv sync) + Playwright browser for the crawl layer
	uv sync --group dev --group pilot
	uv run playwright install chromium

test:  ## Run unit tests
	uv run pytest -q

opex-electricity:  ## Build EV-charging electricity tariff (OpEx) -> data/external/
	$(PY) -m ev_siting.data.opex_electricity

freeze:  ## Freeze raw inputs -> data/raw/MANIFEST.json (checksums + read-only lock)  [E-DQ10]
	$(PY) -m ev_siting.data.provenance.freeze_snapshot

verify-snapshot:  ## Verify raw inputs match frozen snapshot (add HASHES=1 for full content check)  [E-DQ10]
	$(PY) -m ev_siting.data.provenance.freeze_snapshot --verify $(if $(HASHES),--hashes,)

freeze-processed:  ## Freeze current data/processed/ into an immutable sprint bundle (LABEL=...)
	$(PY) -m ev_siting.features.freeze_processed --label $(LABEL)

crawl:  ## Run full EVCS crawl pipeline (enum -> scrape -> split -> master -> QA)
	bash src/ev_siting/data/evcs/run_pipeline.sh

crawl-validate:  ## Re-run only the EVCS QA gate over existing data/interim
	$(PY) -m ev_siting.data.evcs.validate

match-official:  ## Match current master with official registry -> verified xref (F7)
	$(PY) -m ev_siting.data.vinfast_official.match_official

canonical: match-official ## Transform master CSV -> canonical parquet; xref current required (F7)
	$(PY) -m ev_siting.data.evcs.transform_canonical

official:  ## Fetch official VinFast source registry (verified cross-ref) -> data/interim/vinfast_official/
	$(PY) -m ev_siting.data.vinfast_official.fetch_locators bulk

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

assess-occupancy:  ## Build cache occupancy per-trạm duration-weighted (F19, cap 30') từ load_ts frozen
	$(PY) -m ev_siting.assess.cli build-occupancy

assess:  ## Chấm CSV điểm NPP nộp (IN=points.csv OUT=scored.csv) — assess() v0, cần cache occupancy
	$(PY) -m ev_siting.assess.cli score --in $(IN) --out $(OUT)

t1:  ## T1 retrodiction theo pre-reg B2 (chạy MỘT lần as-is; kết quả -> outputs/assess/t1/)
	$(PY) -m ev_siting.assess.cli t1

sizing:  ## Build benchmark định cỡ: utilization theo (loại trụ × mật độ × số cổng)
	$(PY) -m ev_siting.assess.cli sizing

dossier:  ## DELIVERABLE v1 — lập hồ sơ thẩm định từ CSV điểm (IN=points.csv)
	$(PY) -m ev_siting.assess.cli dossier --in $(IN)

spotcheck:  ## B8 — chấm 20 điểm bẫy + oracle độc lập; exit != 0 nếu có lỗi fact
	$(PY) -m ev_siting.assess.cli spotcheck

pilot:  ## B7 — chạy API pilot (POST /dossier · /dossier/markdown · /dossier/batch CSV→CSV)
	uv run uvicorn ev_siting.assess.api:app --host $(HOST) --port $(PORT)

proxy:  ## Build or refresh demand proxy  (TODO — build_demand_proxy còn là stub, xem F-register)
	@echo "TODO: demand proxy chưa được hiện thực (docs/known-issues.md §F)"

mclp:  ## Giải MCLP trên bundle frozen (SCOPE=vietnam MODE=brownfield P=100)
	$(PY) -m ev_siting.models.mclp --scope $(SCOPE) --mode $(MODE) --p $(P) --label $(LABEL)

mclp-bench:  ## B6 — bấm giờ solver thật: p ∈ {20,100,800} × {brownfield, greenfield}
	$(PY) -m ev_siting.models.mclp --bench --scope $(SCOPE)

.DEFAULT_GOAL := help
