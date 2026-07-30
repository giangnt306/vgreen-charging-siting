#!/bin/bash
# EVCS crawl pipeline — chạy TUẦN TỰ (mỗi lúc chỉ 1 trình duyệt headful) để tránh
# crash do 2 Chromium cùng lúc. Chạy: `make crawl` hoặc
#   bash src/ev_siting/data/evcs/run_pipeline.sh   (chạy được từ thư mục bất kỳ)
# Cờ crawl. Mỗi lần crawl telemetry tạo raw run mới, sau đó merge vào canonical;
# retry một run dang dở: EVCS_TS_RUN=<run-id> bash ... (dùng lại .done cùng run).
#   EVCS_FRESH=1   -> crawl mới HOÀN TOÀN cho catalog discovery.
#   EVCS_REENUM=1  -> BỔ SUNG cột cung mới (evsePowers -> num_connectors/power/current_type…)
#                     cho các trạm ĐÃ BIẾT bằng chế độ --enrich-from (bounded, truy vấn /search
#                     tại toạ độ từng trạm, số query ~ mật độ nên nhanh — KHÔNG phải discovery
#                     bùng nổ 1-query-mỗi-trạm). Time-series GIỮ NGUYÊN (STEP 3 resume theo .done),
#                     master ghép lại theo station_code. Đây là cách "map dữ liệu mới vào bản ghi
#                     cũ" mà KHÔNG cào lại 4h telemetry. Yêu cầu: $CAT/evcs_catalog.csv đã tồn tại.
set -euo pipefail
# evcs/ -> data -> ev_siting -> src -> repo root
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$ROOT"

# Chạy các bước dưới dạng module ev_siting.data.evcs.* (giống `make opex-electricity`).
export PYTHONPATH=src
PY="${PY:-python3}"
M="$PY -u -m ev_siting.data.evcs"
CAT=data/raw/evcs/catalog
MERGED_CAT=data/interim/evcs_catalog.csv
MERGED_CODES=data/interim/evcs_all_codes.txt

TS_RUN_ID="${EVCS_TS_RUN:-$(date +%Y-%m-%dT%H-%M-%S)-$$}"
TS_RAW="data/raw/evcs/timeseries_runs/load_ts_${TS_RUN_ID}.csv"
mkdir -p "$(dirname "$TS_RAW")"

if [[ "${EVCS_REENUM:-0}" == "1" ]]; then
  echo "======== STEP 1 (REENUM): bổ sung cột cung cho trạm đã biết $(date) ========"
  if [[ ! -s "$MERGED_CAT" ]]; then
    echo "!! REENUM cần $MERGED_CAT (chạy 1 lần crawl thường trước). Dừng."; exit 3
  fi
  # enrich-from lấy toạ độ trạm đã biết trong catalog cũ, lấp evsePowers vào đúng station_code.
  $M.evcs_enumerate --type cs    --out $CAT/evcs_stations.csv --enrich-from "$MERGED_CAT" --sleep 0.3
  $M.evcs_enumerate --type other --out $CAT/evcs_other.csv    --enrich-from "$MERGED_CAT" --sleep 0.3
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
fi

echo "======== STEP 2: merge catalog $(date) ========"
$M.merge_catalog

# hours là ENUM server {24,168,720} (3 nút UI "24 giờ/7 ngày/30 ngày"); ngoài enum -> timeout 100%.
# 720 = cửa sổ sâu nhất lấy được -> mỗi lần chạy tự lấp mọi gap ngắn hơn 30 ngày.
echo "======== STEP 3: history ${EVCS_HOURS:-720}h over ALL codes -> $TS_RAW $(date) ========"
$M.evcs_scrape --codes-file "$MERGED_CODES" --hours "${EVCS_HOURS:-720}" --out "$TS_RAW"

echo "======== STEP 4: merge $TS_RAW -> data/interim/evcs_timeseries/ $(date) ========"
$M.split_timeseries --input "$TS_RAW"

echo "======== STEP 5: dựng master ĐỘC LẬP (khóa station_code) $(date) ========"
$M.build_master_evcs

echo "======== STEP 6: QA validation (cổng chặn) $(date) ========"
$M.validate

echo "======== ALL DONE $(date) ========"
