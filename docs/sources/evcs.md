# EVCS — Crawl trạm sạc & time-series số xe đang sạc (Việt Nam)

> Gộp từ `README_evcs.md` + `STRUCTURE.md` (dataset gốc `30_gold`), cập nhật theo layout
> repo này sau khi tích hợp: script vào `src/ev_siting/data/evcs/`, dữ liệu thô vào
> `data/raw/evcs/`, dữ liệu đã làm sạch vào `data/interim/`.

Dataset **ĐỘC LẬP** tự crawl từ **evcs.vn**: danh mục trạm sạc EV toàn quốc + **time-series
số xe đang sạc** theo thời gian thực. Dùng để phân tích nhu cầu/độ phủ và tối ưu vị trí trạm.

- **28.625 trạm** trong catalog (VinFast_CS 19.427 / battery-swap 9.118 / other 80) — snapshot crawl **2026-07-21/22**.
  (Con số cũ **28.417** trong tài liệu là snapshot trước; chênh **+208** là do crawl lại tab `cs` — xem **P6** ở [known-issues.md](../known-issues.md).)
- **19.218 trạm có time-series** (~18,6M điểm, cửa sổ 7 ngày), lấy qua Socket.IO của evcs.vn.
- Bảng master `stations_master_evcs.csv` khóa theo `station_code` (mã evcs.vn), ghép **1-1**
  với các file time-series → **0 orphan**.

> ⚠️ **Quan hệ với [SCHEMA_CONTRACT.md](../schema/schema-contract.md):** đây là tầng **raw + interim**.
> Master khóa `station_code` (occupancy) **chưa phải** schema canonical `stations`/`connectors`
> parquet khóa `station_id`. Bước transform sang parquet đúng contract vẫn còn cần làm.

## Cấu trúc thư mục (trong repo này)

```
vgreen-charging-siting/
├── Makefile                                # `make crawl`, `make crawl-validate`
│
├── src/ev_siting/data/evcs/                # pipeline Python (package)
│   ├── __init__.py
│   ├── paths.py                            #   ★ đường dẫn canonical (anchor PROJECT_ROOT)
│   ├── run_pipeline.sh                     #   driver tuần tự (enum→merge→scrape→split→master→QA)
│   ├── evcs_enumerate.py                   #   quét POST /search -> danh mục trạm (Playwright/Cloudflare)
│   ├── merge_catalog.py                    #   gộp cs/bss/other -> evcs_catalog.csv
│   ├── evcs_scrape.py                      #   Socket.IO 'history' -> timeseries_runs/load_ts_<run-id>.csv
│   ├── split_timeseries.py                 #   merge + khử trùng + sort -> evcs_timeseries/<code>.csv
│   ├── build_master_evcs.py                #   ★ dựng master + tính cột QA (ghép 1-1 time-series)
│   ├── validate.py                         #   cổng QA: kiểm toàn vẹn + ghi quality_report.json
│   └── evcs_probe.py                       #   script dò/thử endpoint evcs.vn (standalone)
│
├── data/                                   # (gitignored)
│   ├── raw/evcs/                           # crawl thô, BẤT BIẾN
│   │   ├── catalog/                        #   evcs_catalog.csv (28.625 trạm) = gộp cs/bss/other
│   │   │                                   #   + evcs_{stations,bss,other}.csv (từng tab)
│   │   │                                   #   + *_codes.txt + *.ckpt.json (checkpoint resume)
│   │   ├── timeseries_runs/                #   raw run BẤT BIẾN: load_ts_<run-id>.csv + .done/.failed (F2)
│   │   └── load_ts.csv                     #   dump occupancy legacy (crawl 21-22/07, member frozen trong MANIFEST)
│   └── interim/                            # đã làm sạch / dẫn xuất
│       ├── evcs_timeseries/<code>.csv      #   19.218 file/trạm (timestamp epoch-ms, n_cars_charging)
│       ├── stations_master_evcs.csv        #   ★ BẢNG MASTER (khóa station_code + cột QA)
│       └── quality_report.json             #   run-manifest QA từ validate.py
│
└── db/                                     # nạp PostGIS (schema_postgis.sql + load_to_postgres.py)
```

Mọi script neo đường dẫn qua [`paths.py`](../../src/ev_siting/data/evcs/paths.py) (`PROJECT_ROOT` suy
từ vị trí file) nên chạy đúng bất kể thư mục hiện hành. RAM hạn chế → các bước xử lý `load_ts.csv`
theo kiểu **streaming**, không nạp cả file vào pandas.

## Luồng dữ liệu (pipeline)

```
  evcs_enumerate ── lưới VN + POST /search (Playwright qua Cloudflare) ──▶ raw/evcs/catalog/evcs_{stations,bss,other}.csv
        │
  merge_catalog     ──▶ interim/evcs_catalog.csv + evcs_all_codes.txt   (đường ghi theo evcs/paths bản hợp nhất)
        │
  evcs_scrape       ── Socket.IO 'history' ──▶ raw/evcs/timeseries_runs/load_ts_<run-id>.csv
                                               │       (bất biến, retry qua .done/.failed — F2/F3/F6)
  split_timeseries  ──▶ interim/evcs_timeseries/<code>.csv (merge-union + khử trùng + sort, 1 file/mã)
        │
  build_master_evcs ──▶ interim/stations_master_evcs.csv  ★ master + cột QA, 0 orphan
        │
  validate          ──▶ cổng QA: kiểm toàn vẹn + interim/quality_report.json (fail -> dừng)
```

## Cách chạy

```bash
# Toàn bộ pipeline (cần Playwright + mạng cho bước enum/scrape):
make crawl                       # = bash src/ev_siting/data/evcs/run_pipeline.sh
EVCS_FRESH=1 bash src/ev_siting/data/evcs/run_pipeline.sh   # crawl mới hoàn toàn (ghi đè catalog + telemetry)

# Bổ sung cột cung mới (num_connectors/power/current_type…) mà KHÔNG cào lại 4h time-series:
#   chế độ --enrich-from: truy vấn /search tại toạ độ từng trạm ĐÃ BIẾT, lấp evsePowers vào
#   đúng station_code cũ. Số query ~ mật độ trạm (bounded) nên nhanh hơn discovery nhiều;
#   telemetry giữ nguyên, master ghép lại theo station_code. Cần evcs_catalog.csv sẵn có.
EVCS_REENUM=1 bash src/ev_siting/data/evcs/run_pipeline.sh

# Chạy từng bước (từ repo root):
PYTHONPATH=src python -m ev_siting.data.evcs.split_timeseries
PYTHONPATH=src python -m ev_siting.data.evcs.build_master_evcs
PYTHONPATH=src python -m ev_siting.data.evcs.validate    # = make crawl-validate

# Nạp time-series vào Postgres (cần: pip install psycopg2-binary + DATABASE_URL)
DATABASE_URL=postgresql://user:pass@localhost/evcs python db/load_to_postgres.py
```

## Bảng master `stations_master_evcs.csv`

Khóa `station_code` = mã trạm evcs.vn. Ghép trực tiếp với `interim/evcs_timeseries/<station_code>.csv`
theo tên file → **ghép 1-1, không orphan**. Cột chính:

| Cột | Ý nghĩa |
| --- | --- |
| `station_code` | Mã trạm evcs.vn (khóa chính) |
| `station_type` | `VINFAST_CS` / `BATTERY_SWAP` / `OTHER` |
| `network` | Nhà mạng: VinFast, Honda, … |
| `name`, `address`, `lat`, `lng` | Thông tin trạm |
| `province_code` | Tiền tố tỉnh suy từ mã (chỉ trạm VinFast) |
| `num_connectors` | **Số súng ĐANG BÁO CÁO** = `sum(totalEvse)` của `evsePowers`. ⚠️ Cột này ở **master CSV**; từ 31/07 `stations` **không** giữ bản sao — tầng LIVE canonical suy từ bảng `connectors` (Σ`count_total`), xem `evcs/connector_rollup.py`. Số **LẮP ĐẶT** là `n_guns_installed` (E-DQ4) |
| `connector_types` | Nhãn tier công suất/dòng điện, `|`-joined, vd `DC-120kW\|AC-3.5kW`. ⚠️ evcs.vn **không lộ chuẩn cắm** (CCS2/Type2) — đây là nhãn công suất, không phải chuẩn cắm |
| `current_type` | `AC` / `DC` / `MIXED` (suy từ ngưỡng ≤25 kW = AC — **xấp xỉ tier**; canonical ghi đè bằng chuẩn cắm registry khi khớp official, **P7**/Q5) |
| `max_power_kw`, `total_power_kw` | Công suất súng cao nhất + tổng công suất lắp đặt (`Σ type·totalEvse`) |
| `n_charging_snapshot` | = `totalCharging` thô (tên cũ `num_ports` — đổi ở **F13**). ⚠️ Thực chất là **số xe đang sạc** (biến động), KHÔNG phải số cổng lắp đặt — dùng `num_connectors` cho cấu hình cung |
| `verified`, `status`, `working_time`, `is_public` | Cờ verified, trạng thái depot, giờ hoạt động, công khai |
| `evse_powers` | JSON thô `evsePowers` (giữ nguyên vẹn để audit/dẫn xuất lại) |
| `has_timeseries` | Có time-series hay không (19.218 = True) |
| `ts_n_rows`, `ts_time_start/end(_ms)` | Số điểm + mốc thời gian (epoch-ms + ISO giờ VN) |
| `ts_val_min/max`, `ts_n_null`, `ts_n_dup`, `ts_monotonic` | QA giá trị/thời gian |
| `quality_flag` | Cờ QA gộp: `NO_TS`/`DUP_TS`/`NONMONOTONIC`/`NEG_VALUE`/`NONNUMERIC`/`ALL_ZERO`/`SPARSE`/`COORD_INVALID` |

> 9.407 trạm `has_timeseries=False` = toàn bộ battery-swap/other (9.198) + 209 trạm VinFast_CS
> chưa có telemetry — nhóm này vốn **không có telemetry** trên evcs.vn (đúng thiết kế nguồn).

## Tình trạng hiện tại

- ✅ Crawl evcs.vn — catalog 28.625 trạm + time-series ~18,6M điểm (19.218 trạm VinFast).
- ✅ **Master độc lập** `stations_master_evcs.csv` — 28.625 trạm, ghép 1-1 time-series, **0 orphan**, **PK `station_code` unique** (cổng CRITICAL ở `validate.py`).
- ⬜ Transform master → parquet `stations`/`connectors` đúng [SCHEMA_CONTRACT.md](../schema/schema-contract.md).
- ⬜ Nạp vào PostgreSQL + PostGIS (`db/schema_postgis.sql` có thể cần chỉnh theo schema master).

## Ghi chú kỹ thuật crawl evcs.vn

- Trang sau **Cloudflare** (JS challenge) → phải mở bằng Playwright headful để lấy `cf_clearance`;
  **KHÔNG** chạy 2 trình duyệt headful cùng lúc (crash X display) → pipeline chạy tuần tự.
- Enumerate = `POST /search` (cap cứng 50 trạm gần nhất/truy vấn) → phủ đĩa tham lam trên lưới VN.
  Mỗi bản ghi `/search` đã kèm `evsePowers` (`[{type:<W>, totalEvse, numberOfAvailableEvse}]`) +
  `workingTimeDescription`/`isPublic`/`isFreeParking` (BSS: `numberBattery*`) → **toàn bộ cột cung
  của SCHEMA_CONTRACT (connector/power/current_type) lấy được ngay ở bước enumerate**, KHÔNG cần
  tải trang chi tiết từng trạm. Vì thế bổ sung schema chỉ cần lấp lại catalog (`EVCS_REENUM=1`),
  KHÔNG đụng 4h telemetry.
- **Discovery vs Enrich:** discovery (mặc định) append 1 seed force-query cho MỖI trạm phát hiện
  → số query ~ số trạm (chậm). `--enrich-from` chỉ truy vấn tại toạ độ trạm ĐÃ BIẾT và bỏ qua trạm
  đã lấy → số query ~ mật độ (nhanh), lý tưởng để backfill cột mới lên tập station_code cũ.
- Time-series = Socket.IO `emit('subscribe')` + `emit('history',{stationId,hours})`; chỉ trạm VinFast
  (`C.XXX`) có telemetry; bss/other không có. `timestamp` = epoch-ms, `value` = số xe đang sạc.

## Giao thức evcs.vn — đo lại 2026-07-29 (⚠️ 3 thay đổi PHÁ VỠ)

Bản crawl 07-21/22 chạy với giao thức CŨ; ngày 29/07 đo lại thấy server đã đổi và crawler cũ
**hỏng hoàn toàn** (không phải hỏng dần) — cả ba thay đổi đều **im lặng**: không exception, chỉ ra
0 dòng hoặc `AttributeError` muộn. Trước MỌI lần crawl mới: chạy probe xác minh
endpoint/payload/enum còn đúng; phần bootstrap dùng chung giữ ở
[`session.py`](../../src/ev_siting/data/evcs/session.py).

**Ba thay đổi phá vỡ:**

1. **Endpoint không còn same-origin.** Socket.IO phải mở `io("https://www2.evcs.vn/",
   {path:"/socket.io", auth:<fn>, …})` — `io('/')` → `websocket error`. Hàm `auth` sinh token
   `{t:"<epoch>.<chữ ký>"}` phải **mượn lại đối tượng opts của trang** (không tái tạo được từ Python).
2. **`history_data` đổi format:** `[{timestamp,value}]` → **`[[ts,value]]`**.
3. **`history` payload:** `{stationId, hours, token:"", detail:false}` — `token=""` vẫn chạy (80/80 trạm);
   `subscribe` KHÔNG cần cho history (bỏ để tránh nuốt stream `new_data`).

**Enum & tầng lấy mẫu:**

- `hours` là **ENUM {24, 168, 720}** khớp 3 nút UI (24 giờ / 7 ngày / 30 ngày). Ngoài enum → server
  **im lặng bỏ qua** → timeout. **720 = sâu nhất.**
- **Tầng lấy mẫu khác nhau theo `hours`**: 168h = theo sự kiện (gap trung vị ~1,5′); 720h = **lưới 5′**
  (chỉ phát khi đổi giá trị; p90 45′, có gap tới 13 ngày). Timestamp hai tầng **chồng khớp ~0**
  (2/483.808) ⇒ **không union mù** — tách thư mục theo tầng (`timeseries_runs/` mang run-id theo tầng).
  Giá trị vẫn là số nguyên thô nên so sánh được giữa hai tầng.

**Ràng buộc phiên & throughput:**

- **Cloudflare chỉ cho MỘT phiên/IP**: mở phiên thứ hai khi phiên đầu đang chạy → kẹt challenge vô hạn
  (5/5 lần thử). Mọi việc cần trình duyệt phải **tuần tự** (khớp ghi chú "không chạy 2 headful" ở trên).
- Profile Chromium bền vững (`launch_persistent_context`) cache `cf_clearance`: bootstrap 15s lần đầu
  → ~1s các lần sau.
- Throughput: socket **dùng chung** + huỷ-dựng-lại-khi-timeout = 0,37 s/trạm (~2h/19k trạm); socket
  **riêng mỗi trạm** = 1,24 s/trạm (chậm 3,3×). Cả hai an-toàn-danh-tính (F3).
