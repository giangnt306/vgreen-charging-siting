#!/bin/bash
# EVCS crawl pipeline — chạy TUẦN TỰ (mỗi lúc chỉ 1 trình duyệt headful) để tránh
# crash do 2 Chromium cùng lúc. Chạy: `make crawl` hoặc
#   bash src/ev_siting/data/evcs/run_pipeline.sh   (chạy được từ thư mục bất kỳ)
# Đặt EVCS_FRESH=1 để crawl mới hoàn toàn (ghi đè catalog + telemetry cũ).
set -u
# evcs/ -> data -> ev_siting -> src -> repo root
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$ROOT"

# Chạy các bước dưới dạng module ev_siting.data.evcs.* (giống `make opex-electricity`).
export PYTHONPATH=src
PY="${PY:-python3}"
M="$PY -u -m ev_siting.data.evcs"
CAT=data/raw/evcs/catalog

FRESH_ARGS=()
if [[ "${EVCS_FRESH:-0}" == "1" ]]; then
  FRESH_ARGS=(--overwrite)
fi

echo "======== STEP 1: EVCS enum (cs, other, bss; resume) $(date) ========"
$M.evcs_enumerate --type cs    --out $CAT/evcs_stations.csv --sleep 1.2 "${FRESH_ARGS[@]}"
$M.evcs_enumerate --type other --out $CAT/evcs_other.csv    --sleep 1.2 "${FRESH_ARGS[@]}"
$M.evcs_enumerate --type bss   --out $CAT/evcs_bss.csv      --sleep 1.2 "${FRESH_ARGS[@]}"
echo "step1 exit=$?"

echo "======== STEP 2: merge catalog $(date) ========"
$M.merge_catalog
echo "step2 exit=$?"

echo "======== STEP 3: history 168h over ALL codes (resume) $(date) ========"
$M.evcs_scrape --codes-file $CAT/evcs_all_codes.txt --hours 168 --out data/raw/evcs/load_ts.csv "${FRESH_ARGS[@]}"
echo "step3 exit=$?"

echo "======== STEP 4: tách load_ts.csv -> data/interim/evcs_timeseries/ $(date) ========"
$M.split_timeseries
echo "step4 exit=$?"

echo "======== STEP 5: dựng master ĐỘC LẬP (khóa station_code) $(date) ========"
$M.build_master_evcs
echo "step5 exit=$?"

echo "======== STEP 6: QA validation (cổng chặn) $(date) ========"
$M.validate
qa=$?
echo "step6 exit=$qa"
if [[ $qa -ne 0 ]]; then
  echo "!! QA FAIL (CRITICAL) — xem data/interim/quality_report.json. Dừng pipeline."
  exit $qa
fi

echo "======== ALL DONE $(date) ========"
