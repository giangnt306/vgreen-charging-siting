#!/bin/bash
# EVCS crawl pipeline — chạy TUẦN TỰ (mỗi lúc chỉ 1 trình duyệt headful) để tránh
# crash do 2 Chromium cùng lúc. Chạy: `make crawl` hoặc
#   bash src/ev_siting/data/evcs/run_pipeline.sh   (chạy được từ thư mục bất kỳ)
# Cờ crawl. Time-series (STEP 3) tốn ~4h nên tách riêng để KHÔNG mất oan:
#   EVCS_FRESH=1   -> crawl mới HOÀN TOÀN: discovery lại catalog + ghi đè time-series.
#   EVCS_REENUM=1  -> BỔ SUNG cột cung mới (evsePowers -> num_connectors/power/current_type…)
#                     cho các trạm ĐÃ BIẾT bằng chế độ --enrich-from (bounded, truy vấn /search
#                     tại toạ độ từng trạm, số query ~ mật độ nên nhanh — KHÔNG phải discovery
#                     bùng nổ 1-query-mỗi-trạm). Time-series GIỮ NGUYÊN (STEP 3 resume theo .done),
#                     master ghép lại theo station_code. Đây là cách "map dữ liệu mới vào bản ghi
#                     cũ" mà KHÔNG cào lại 4h telemetry. Yêu cầu: $CAT/evcs_catalog.csv đã tồn tại.
set -u
# evcs/ -> data -> ev_siting -> src -> repo root
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$ROOT"

# Chạy các bước dưới dạng module ev_siting.data.evcs.* (giống `make opex-electricity`).
export PYTHONPATH=src
PY="${PY:-python3}"
M="$PY -u -m ev_siting.data.evcs"
CAT=data/raw/evcs/catalog

# Time-series (STEP 3) chỉ ghi đè nếu FRESH (bảo vệ 4h telemetry).
TS_ARGS=()
if [[ "${EVCS_FRESH:-0}" == "1" ]]; then
  TS_ARGS=(--overwrite)
fi

if [[ "${EVCS_REENUM:-0}" == "1" ]]; then
  echo "======== STEP 1 (REENUM): bổ sung cột cung cho trạm đã biết $(date) ========"
  if [[ ! -s "$CAT/evcs_catalog.csv" ]]; then
    echo "!! REENUM cần $CAT/evcs_catalog.csv (chạy 1 lần crawl thường trước). Dừng."; exit 3
  fi
  # enrich-from lấy toạ độ trạm đã biết trong catalog cũ, lấp evsePowers vào đúng station_code.
  $M.evcs_enumerate --type cs    --out $CAT/evcs_stations.csv --enrich-from $CAT/evcs_catalog.csv --sleep 0.3
  $M.evcs_enumerate --type other --out $CAT/evcs_other.csv    --enrich-from $CAT/evcs_catalog.csv --sleep 0.3
  echo "step1 exit=$?"
else
  # Catalog discovery ghi đè nếu FRESH; ngược lại resume.
  ENUM_ARGS=()
  if [[ "${EVCS_FRESH:-0}" == "1" ]]; then
    ENUM_ARGS=(--overwrite)
  fi
  echo "======== STEP 1: EVCS enum (cs, other, bss; resume) $(date) ========"
  $M.evcs_enumerate --type cs    --out $CAT/evcs_stations.csv --sleep 1.2 "${ENUM_ARGS[@]}"
  $M.evcs_enumerate --type other --out $CAT/evcs_other.csv    --sleep 1.2 "${ENUM_ARGS[@]}"
  $M.evcs_enumerate --type bss   --out $CAT/evcs_bss.csv      --sleep 1.2 "${ENUM_ARGS[@]}"
  echo "step1 exit=$?"
fi

echo "======== STEP 2: merge catalog $(date) ========"
$M.merge_catalog
echo "step2 exit=$?"

echo "======== STEP 3: history 168h over ALL codes (resume) $(date) ========"
$M.evcs_scrape --codes-file $CAT/evcs_all_codes.txt --hours 168 --out data/raw/evcs/load_ts.csv "${TS_ARGS[@]}"
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
