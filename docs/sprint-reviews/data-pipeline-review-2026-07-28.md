# Chẩn đoán vòng đời dữ liệu EVCS — 2026-07-28

> Review bởi Data Team Lead (Kỳ + Claude), 2026-07-28, trên `devky/review-dataset` (= `data/giang`, HEAD `495b0c3`).
> Phương pháp: 4 luồng review song song (crawl / xây dựng dataset / feature engineering / phía tiêu thụ evcs-dataset + EDA),
> mọi phát hiện High trở lên được xác minh chéo trực tiếp trên code; phần dữ liệu đo trực tiếp bằng duckdb trên bản bàn giao
> trong `../evcs-dataset` (catalog 28.417 + load_ts 18,63M điểm). Ưu tiên vòng này: **tính đúng đắn dữ liệu/pipeline**, chưa đào sâu phân tích.
> Checklist xử lý: các finding đã được đăng ký thành nhóm **F** trong [`docs/known-issues.md`](../known-issues.md).

---

## 1. Tóm tắt

Chất lượng kỹ thuật của pipeline aGiang đã tiến bộ thật sự: các fix P6/P7/P8/E-DQ2/E-DQ10 mà known-issues đánh dấu ☑ đều **có thật trong code** (đã verify từng cái). Nhưng ba vấn đề cấu trúc đang làm mọi con số hạ nguồn không đáng tin:

1. Hai bug chặn từ review 24/07 (bộ lọc toạ độ bẩn chết, `split_timeseries` ghi đè khi resume) **vẫn chưa fix**, cộng thêm một bug crawl mới nghiêm trọng hơn — race listener Socket.IO có thể **gán time-series sang nhầm trạm**.
2. Bản dữ liệu Kỳ đang dùng trong `evcs-dataset` là snapshot mồ côi ngày 21/07 — **khác hash với snapshot frozen của Giang, mang cùng nhãn "2026-07-20"**, và không chứa bất kỳ fix nào từ 24–27/07 → ground truth cho T1 retrodiction (deadline 30–31/07) đang nhiễm trùng lặp và trạm chết.
3. Repo HuggingFace **vẫn public, license Unknown, và vừa được push bản mới ngày 28/07** — rủi ro pháp lý số 1 không những chưa xử lý mà còn nặng thêm.

EDA hiện chưa đủ để tin dữ liệu: notebook EDA của Giang là placeholder rỗng; phần audit danh tính của Kỳ rất tốt nhưng thiếu 3 sanity check tối thiểu (toạ độ placeholder, độ đầy telemetry per-trạm, dedup nội tập new-supply).

## 2. Bảng phát hiện

### 2a. Thu thập (crawling) — `aGiang-evcs`

| Vấn đề | Vị trí | Bằng chứng | Mức | Ảnh hưởng nếu bỏ qua | Hướng xử lý |
|---|---|---|---|---|---|
| `split_timeseries` ghi đè khi resume | `split_timeseries.py:26,48-51` | `flush()` mở mode `"w"`, reset buffer khi đổi code; trạm bị emit lại ở khối sau (crash-resume của scrape) ghi đè file trước. Docstring tuyên bố miễn nhiễm — sai | **Critical** | Mất telemetry vĩnh viễn (cửa sổ server chỉ 168h, không crawl lại được) | Gom buffer theo dict toàn cục hoặc merge-union với file cũ khi flush |
| Race listener Socket.IO → time-series gán nhầm trạm | `evcs_scrape.py:53-60` | Trạm A timeout 8s nhưng listener `once('history_data')` của A **không được gỡ**; reply muộn của A fire vào promise của trạm B; payload không kiểm `stationId` | **High** (mới) | Occupancy gắn sai danh tính, **không thể phát hiện hậu kiểm** — đầu độc chính dataset 18,6M điểm là tài sản lớn nhất | `socket.off()` ở nhánh timeout + validate stationId trong payload |
| Timeout → null → `.done` không retry | `evcs_scrape.py:59,189-197` | `setTimeout(() => res(null), 8000)`; `for pt in (series or [])` ghi 0 dòng nhưng vẫn `done_f.write(sid)` "kể cả rỗng" | **High** (còn từ 24/07) | "Lỗi fetch" ≡ "trạm không có dữ liệu" → `NO_TS` giả, thiếu telemetry hệ thống không đo được | Chỉ ghi `.done` khi `series is not None`; danh sách null vào `.failed` để retry |
| Resume mất force-seed → thiếu phủ vùng dày đặc | `evcs_enumerate.py:296-299,364-377` | Resume nạp `found` từ CSV nhưng `record()` chỉ tạo force-seed cho trạm *mới* → cụm >50 trạm phát hiện trước crash không được mở rộng tiếp | **High** (mới) | Under-coverage đô thị im lặng nếu run discovery từng crash | Khi resume, re-seed mọi trạm trong `found` chưa nằm trong đĩa phủ |
| Enrich lỗi → `seen` vĩnh viễn | `evcs_enumerate.py:225-226` | `if data is None: seen.add(code)` | High (còn) | `evse_powers` trống giả → mất input cho P7 | Danh sách failed + pass 2 như discovery |
| Overpass trả 200 + kết quả cụt không kiểm | `overpass_poi.py:71-72` | `if r.status_code == 200: return r.json()` — không đọc trường `remark` ("Query timed out") mà Overpass gắn khi cắt cụt giữa chừng | **High** (mới) | POI thiếu hệ thống đúng ở ô dày (HN/HCM) → demand_h3 và anchor T1/T2 thiên lệch | Nếu `remark` chứa timeout → ép tách bbox như nhánh ≥40k |
| Pipeline không fail-fast + ckpt không atomic | `run_pipeline.sh:13`; `evcs_enumerate.py:311-313` | Chỉ `set -u`, các bước echo exit code rồi chạy tiếp; ckpt `json.dump` ghi thẳng; CSV append có thể rách dòng → mã ma | Medium | Enumerate chết giữa chừng → catalog thiếu nhưng QA vẫn PASS (QA chỉ kiểm khoá, không kiểm độ đầy) | `set -e` cho bước 1–3; ckpt ghi `.tmp` + `os.replace`; validate regex mã khi resume |
| `fetch_locators` không đối chiếu `meta.count`; parse không gate `.done` đủ | `fetch_locators.py:93-99,200` | Doc `vinfast-official.md:22-23` tự thú từng parse lúc mới có 202/23.240 file — code vẫn không chặn | Medium | Registry official khuyết im lặng → giảm verified/connector-standard oan | Assert `len(items) ≈ meta.count`; parse yêu cầu done đủ |
| `R_cov = 1.05·R` nới sai bất biến phủ; không có phép đo độ phủ độc lập | `evcs_enumerate.py:360` | Bất biến chỉ đúng cho bán kính R (trạm thứ 50); không có cross-check với registry 23.247 trạm | Medium | Trạm lọt lưới không chứng minh được là không tồn tại | Đo coverage vs official registry (match_official đã gián tiếp: 19.427 exact) |
| PBF/TIF không kiểm `got < total` + skip-if-nonempty | `roads_pbf.py:99,105-119`; `worldpop_pop.py:30,34-47` | Stream đóng sớm "sạch" → file cụt được replace và skip vĩnh viễn (worldcover.py **có** kiểm — dùng làm mẫu) | Low | Rasterio/osmium sẽ crash to (lỗi hiện hình) — rủi ro thấp | Thêm check `got<total` + đối chiếu md5 Geofabrik |

### 2b. Xây dựng dataset — `aGiang-evcs`

| Vấn đề | Vị trí | Bằng chứng | Mức | Ảnh hưởng nếu bỏ qua | Hướng xử lý |
|---|---|---|---|---|---|
| Bộ lọc toạ độ bẩn **vẫn chết** (từ 24/07); cờ thật `DUP_COORD_SUSPECT` không ai tiêu thụ | `build_candidates.py:53`, `build_covered0.py:47` | Lọc `{DUP_COORD, COORD_ADDR_MISMATCH}` — grep toàn `src/`: không producer nào sinh 2 cờ này. E-DQ2 đã tạo cờ thật `DUP_COORD_SUSPECT` (214 trạm) nhưng không module nào đọc. T0 còn **bypass cả bộ lọc buildable** (`build_candidates.py:225`) | **Critical** | 214 trạm toạ độ placeholder thành incumbent "bắt buộc mở" + coverage ảo trong baseline; phòng thủ P8/§7 tồn tại trên giấy 2 tuần nay | Fix 1 dòng × 2 file: thêm `DUP_COORD_SUSPECT` (cân nhắc thêm `COORD_INVALID`) vào `_DIRTY_COORD_FLAGS` |
| `build_covered0` bỏ qua toàn bộ P8/E-DQ2 | `build_covered0.py:44-52,73-76` | Lọc theo `status ∈ {Available, AllBusy}` + `is_public==True` **thô** (đúng loại tín hiệu telemetry mà P8 cấm dùng làm quyết định); không đọc `op_status`/`access`/`is_operational`/`is_primary` | **High** | 329 dup chéo nguồn đếm 2 lần trong baseline; trạm official-ACTIVE bị loại oan; **T0 và covered0 là hai tập trạm khác nhau** → MCLP đo coverage-tăng-thêm trên hệ quy chiếu lệch | Viết lại filter = `is_operational & access=='PUBLIC' & is_primary` (công thức 19.053 của chính known-issues); lý tưởng dùng chung `_load_stations` với candidates |
| NaN distance → `verified=True` | `match_official.py:249-250` | `v = (pd.isna(dist) or dist <= VERIFY_DIST_M)` — comment còn hợp thức hoá "(hoac thieu 1 phia)". Verified chảy vào confidence → survivor E-DQ2 | **High** (còn từ 24/07) | Trạm toạ độ hỏng vừa "verified" vừa dễ thắng survivor dedup | `pd.notna(dist) and ...`; thiếu toạ độ → mức riêng "code-only" |
| `match_official` không được wire vào pipeline | `Makefile`; `transform_canonical.py:246-249` | Không target `make match`; transform chạy được không cần xref (fallback im lặng) | Medium | Quên chạy matcher → mất `official_store_id` → **E-DQ2 T1 biến mất im lặng**, dedup chỉ còn coord_name, pipeline vẫn PASS | Thêm target + transform FAIL/WARN khi xref thiếu hoặc stale hơn master |
| Ngưỡng 25kW còn sống 4 chỗ | `build_master_evcs.py:26,57`; `transform_canonical.py:56,199,346` | Master CSV vẫn 100% tier-derived; canonical fallback tier cho connector evcs-only; trạm không có connector giữ nguyên current_type tier không cờ riêng | Medium | Tuyên bố P7 "không từ ngưỡng 25kW nữa" là overclaim một phần; ai đọc master CSV trực tiếp ăn nhãn AC/DC sai dải 20–22kW | Flag `CURRENT_TYPE_TIER_DERIVED` cho nhánh fallback; ghi rõ trong docs |
| `transform_canonical` rmtree không atomic | `transform_canonical.py:369-377` | `rmtree` → `mkdir` → `to_parquet`; crash giữa chừng = canonical rỗng, consumer đọc không cảnh báo | Medium | Dataset "biến mất" khó chẩn đoán | Ghi `.tmp-<ts>` rồi `os.replace` |
| Schema contract trôi so với code | `schema-contract.md §2,§6` vs `transform_canonical.py:317,381` | Contract thiếu cả 6 cột E-DQ2 (`physical_id`, `is_primary`…); QA "0 orphan FK, num_connectors==Σcount" trong contract **không tồn tại trong code** (orphan chỉ được print) | Medium | Kỳ đọc contract sẽ không biết phải lọc `is_primary` — chính lỗi tầng model dễ dính nhất | Sync contract + thêm 2 assert vào transform |
| `tot`/`num_ports` chắc chắn không phải số cổng sạc | `evcs_enumerate.py:64` → `build_master_evcs.py:224`; **đo trên dữ liệu thật** | 14.537/19.219 trạm cs có `tot=0`; **74% trạm có max xe sạc đồng thời > tot** (C.HNO0461: 109 vs 45) | Medium | Bất kỳ ai dùng làm capacity đều sai; may là canonical không xuất cột này | Rename `n_charging_snapshot` hoặc drop khỏi master |
| Manifest hỏng → cổng tự mở thành WARN | `validate.py:122-124` | `except Exception` bọc cả verify → MANIFEST corrupt = WARN không CRITICAL | Med-Low | Cổng drift vô hiệu đúng lúc đáng ngờ nhất | Tách "module thiếu" (WARN) khỏi "manifest không parse được" (CRITICAL) |
| `merge_catalog` ghi output dẫn xuất vào `data/raw/` đã freeze | `merge_catalog.py:11-12` | `evcs_catalog.csv` nằm trong vùng E-DQ10 read-only + manifest | Med-Low | Re-run merge sau freeze → Permission denied hoặc drift CRITICAL giả | Chuyển sang `data/interim/` |

### 2c. Bàn giao & phía tiêu thụ — `evcs-dataset`

| Vấn đề | Vị trí | Bằng chứng | Mức | Ảnh hưởng nếu bỏ qua | Hướng xử lý |
|---|---|---|---|---|---|
| **HF vẫn public và vừa push bản mới 28/07** | `huggingface.co/datasets/Wanderer210w/vgreen-charging-siting-data` | Fetch trực tiếp 28/07: public, license "Unknown", **last modified 2026-07-28**, chứa `raw/` + 19.218 series occupancy + 23.240 JSON VinFast, 47 download/tháng | **Critical (pháp lý, chặn)** | Public đúng thứ `_tos_firewall` của dự án chính cố tình chặn (ToS evcs.vn + vault); mỗi ngày public thêm là thêm bản sao ngoài tầm kiểm soát | Private/gỡ raw+occupancy+JSON **ngay**; license + SOURCES_AND_LICENSES rõ ràng trước khi cân nhắc public lại |
| Bàn giao 21/07 = snapshot mồ côi, cùng nhãn khác ruột | `evcs-dataset/data/00_raw/source=evcs_vn/...=2026-07-20/` vs `aGiang-evcs/data/raw/MANIFEST.json` | **Đo trực tiếp**: catalog bàn giao 28.417 trạm ≠ frozen 28.625; sha256 cả 2 file đều lệch manifest (load_ts lệch 4 bytes); cùng nhãn `snapshot_date=2026-07-20` | **High** | E-DQ10 "tái lập được" không phủ đúng consumer quan trọng nhất; mọi fix P6–P8/E-DQ2 **không có** trong dữ liệu Kỳ dùng; đối soát số chéo repo vô nghĩa | Re-handoff một snapshot chuẩn duy nhất: frozen catalog + canonical (có `op_status`/`is_primary`/`physical_id`/`connector_standard`) + hash khớp manifest |
| `evcs_new_supply` không dedup nội tập → nhiễm ground truth T1 | `evcs-dataset/src/evcs/transform/evcs_vn_new_supply.py:40-68` | **Đo trực tiếp**: 121/3.797 row NEW là cặp <50m (12 cụm exact-coord); riêng tier HIGH dùng làm ground truth B4: 40/1.544 row nghi trùng | **Critical cho sprint 2** (B4 deadline 30–31/07) | Hit-rate/AUC retrodiction tính trên nhãn đếm đôi | Dedup nội tập NEW (coord<50m + name-sim + blob guard, mượn logic `dedup_crosssource` của Giang) trước B4 |
| Toạ độ placeholder (E-DQ1) cắn cả hai phía | E-DQ1 ☐ Open; `enrich_map.parquet` | **Đo trực tiếp**: cụm 35 trạm cùng 1 điểm HCM tên "…Hà Nội"; **21 gold station bị enrich liveness/status từ đúng 1 mã `C.HNO7257` @0.0m**; 126 mã evcs bị ≥2 gold trỏ vào | **Critical** | 21+ gold mang danh tính sai trong `evcs_enrich`; placeholder chảy vào T0/covered0 phía Giang | Đóng E-DQ1: blob-guard trong enrich_map + loại cặp nghi khỏi liveness enrich; phía Giang wire cờ (2b dòng 1) |
| NEW chứa trạm chết được tính là cung sống | `evcs_vn_new_supply.py:40` | **Đo trực tiếp**: 46 OutOfService + 659 Maintaining (17,4%) pass filter `ever_active==1` (đo cả cửa sổ — trạm chết cuối kỳ vẫn qua) | **High** | Cung mới ảo trong ablation + retrodiction | Thêm cờ trạng thái resolve (nhận `op_status` từ master mới của Giang qua `station_code`) |
| `_tos_firewall` chỉ bọc bảng `stations` | `evcs-dataset/src/evcs/publish/export.py:102-155` | `connectors`/`agg_*`/`demand_*`/`nn_*` ghi vào dist không qua firewall (hiện chưa rò vì chưa có cột evcs) | Medium | Khi A2 calibration thêm cột occupancy vào demand → rò lặng qua dist | Wrap mọi `write_*` qua firewall |
| Cột bẫy trong bàn giao: `gold_station_id` NN không ngưỡng | `catalog.csv` bàn giao | **Đo trực tiếp**: phủ 100% kể cả 9.118 BSS; chỉ 51% @0m, p99 = 6,6 km | Medium | Ai join theo cột này gán trạm đổi pin vào gold cách 6km (phía Kỳ đã né đúng — recompute độc lập) | Drop cột này ở bản re-handoff, hoặc kèm `match_method`/ngưỡng |
| k=1 hub undercount (đã biết, đã log) | `evcs_vn_agreement.py:142-160`; `pha2-evcs-merge-audit.md` | 9,8% gold có ≥2 evcs trong 50m (max 36) | Medium | `max_concurrent` per-site bị thiếu ở hub | Aggregate theo bán kính site như backlog A2 đã ghi |

### 2d. Feature engineering — `aGiang-evcs`

| Vấn đề | Vị trí | Bằng chứng | Mức | Ảnh hưởng nếu bỏ qua | Hướng xử lý |
|---|---|---|---|---|---|
| `demand_proxy`, `mclp`, `export_geojson` đều là **stub** | `features/build_demand_proxy.py`, `models/mclp.py`, `viz/export_geojson.py` | Cả 3 file = `def ...: pass`; `demand_weight.parquet` chưa từng tồn tại; SCHEMA_CONTRACT mô tả demand A/B như đã có | **High** | Deliverable D1 chưa tồn tại trong khi lịch (Giang chốt `demand_weight` 01/08) đang đếm ngược | Ưu tiên build sau khi chốt data-requirements B5 |
| `built_up_frac<0.05` hard-exclude trên ước lượng nhiễu, gate chỉ WARN | `landuse/paths.py:55`; `build_buildable_h3.py:110,118`; `landuse/validate.py:61-63` | National: loại 47% ô `pop>0`; stride 8 → ~130 mẫu/ô, σ≈0.02 quanh ngưỡng 0.05 | **High** (national) | ~9% dân số không bao giờ được phủ, MCLP không thể chọn — mâu thuẫn mục tiêu phủ công bằng | Chuyển soft-penalty hoặc hạ ngưỡng + đổi WARN→FAIL có ngưỡng |
| `road_len_m=0` fill → hard-exclude gắn với độ phủ OSM; mọi class đường đều tính | `build_buildable_h3.py:87-90,111`; `roads_pbf.py:32-41` | Ô vắng khỏi demand_h3 = "không đường"; ngược lại ô chỉ có `track` đất = "có tiếp cận" | Med-High | Loại oan vùng OSM chưa vẽ (E-DQ8), giữ nhầm vùng chỉ có đường đất | Soft-penalty + phân biệt class như `road_len_mt_m` đã làm |
| `penalty` chuẩn hoá per-AOI trên file lookup dùng chung | `build_buildable_h3.py:125-126` | `dmax = dist[finite].max()` trong AOI lần chạy; `BUILDABLE_H3` là 1 file ghi đè | Medium | `capex_class` đổi nhãn theo scope chạy gần nhất — không tái lập | Cố định mẫu số vật lý (vd 10km) hoặc ghi `dmax` vào sidecar |
| `config/params.yaml` mồ côi, mâu thuẫn tham số chốt | `params.yaml:3` vs `features/paths.py:25` | `radius_m: 500` vs `R_BASELINE_KM=3.0`; grep: không ai import params.yaml | Medium | Ai đọc config sẽ chạy đúng cấu hình suy biến P4 đã fix | Xoá hoặc đồng bộ |
| Cột chết trong bàn giao candidate | `build_candidates.py:244,249` | `province_code=None` 100%, `exclusion_flags=[]` 100% | Med-Low | Kỳ nhận 2 cột vô nghĩa không cảnh báo | Drop hoặc ghi chú trong sidecar |
| Test né đúng chỗ có bug | `tests/` (3 file) | Không test `_load_stations` (nơi bộ lọc chết nằm từ 24/07), `_gapfill` (nơi vừa fix 495b0c3), `_qa_gate`, covered0 | Medium | Bug tái phát không ai biết; một test "cờ X phải bị loại" với X lấy từ producer thật đã bắt được A1 từ 2 tuần trước | Bổ sung 4 test đúng các điểm này |

### 2e. Chất lượng telemetry (đo trực tiếp trên 18,63M điểm — ảnh hưởng cách dùng, không phải bug code)

| Phát hiện | Bằng chứng | Mức | Hệ quả cho P1/A2 |
|---|---|---|---|
| Sampling theo sự kiện, không đều | Median gap 0,9 phút nhưng p99 41 phút, max 71 giờ; 513 trạm <50 obs; 129 trạm span <3 ngày | **High (phương pháp)** | Mean-of-samples thiên về giai đoạn hoạt động cao → **phải duration-weight/resample lưới đều** trước khi hồi quy demand |
| 3.417/19.218 trạm (17,8%) zero tuyệt đối suốt 7 ngày | Đo trực tiếp; xấp xỉ 3.447 trạm OutOfService/Maintaining | Medium | "Cung" không phục vụ; liên đới quyết định giữ MAINTENANCE làm brownfield (P8) |
| `n_cars_charging` max 109 > mọi capacity hợp lý | C.HNO0461: 109 xe vs tot=45 | Medium | Ngữ nghĩa counter chưa kiểm chứng (có gồm xe chờ? gộp nhiều bãi?) — cần Giang xác nhận trước khi calibrate |
| Đối soát trạm khớp gần hoàn hảo | 19.218 ts vs 19.219 cs: chỉ 2 cs thiếu ts (`C.TNG11495`, `C.DNA10968`), 1 mã lạ `AGI67-04`; 0 dup (station,ts); 0 giá trị âm; 1 dòng malformed | Checked-OK | — |

## 3. Đã kiểm tra, không phát hiện vấn đề

- **Crawl**: dedup 3 tab first-wins + đếm tách; timezone epoch-ms nhất quán; Cloudflare retry/bootstrap hợp lý; bbox VN phủ đủ điểm cực; WorldCover downloader chuẩn nhất (dùng làm mẫu cho 2 downloader kia); `run_detail` official chỉ ghi done khi thành công.
- **Xây dựng**: P6 cổng CRITICAL PK là thật (validate exit 1); P7 join official theo `(code, kW)` + roll-up đúng; P8 mapping status đúng chiều trong `transform_canonical`; E-DQ2 đủ T1/T2/blob-guard/survivor/5-gate-raise-thật; E-DQ10 manifest + read-only lock + drift gate hoạt động; đơn vị W→kW nhất quán phía evcs; các join official không fan-out.
- **Feature**: **không có data leakage** — demand_h3 (pop/road/POI) không dẫn xuất từ vị trí trạm sạc hiện có; H3 res 8 + haversine nhất quán; gate `R>d` (P4) có mặt; fix T4 AOI-clip (495b0c3) đúng và đủ trong phạm vi của nó.
- **Phía Kỳ**: bản bàn giao 07-20 không có dup PK (0/28.417 — đo trực tiếp); BSS/xe máy được loại cấu trúc (`tab=='cs'`); recompute NN độc lập, không tin cột match của Giang; cách ly lineage + 2 lớp containment gate cho `stations` còn hoạt động; telemetry malformed xử lý đúng.

## 4. Điểm mù

- ~~Dữ liệu processed của aGiang không có trên máy này~~ → **đã giải quyết 28/07**: tải trọn snapshot HF (2,19GB, 212 file) về `data/`, `make verify-snapshot` PASS. Còn lại: **log run crawl trên máy Giang** (đo thiệt hại thực của race listener / split-overwrite) vẫn không có.
- **Không diff được nội dung snapshot cũ (28.417) vs frozen (28.625)** — bản cũ chỉ còn ở `evcs-dataset/00_raw`, đã có thể diff sau khi tải HF (việc cho vòng fix).
- **Hành vi server evcs.vn** (trần kết quả POST /search, ngữ nghĩa `n_cars_charging`/`tot`, độ sâu thật của history 168h) — không kiểm chứng được từ code.
- **Không chạy được test suite tại thời điểm review** — đã giải quyết 28/07 (sửa `pyproject.toml` hỏng + `uv sync`).

## 5. Câu hỏi cần Giang xác nhận

1. **HF**: vì sao push bản mới 28/07 khi review 24/07 đã yêu cầu private/gỡ? Ai là người quyết và deadline gỡ là khi nào?
2. **`n_cars_charging`**: có bao gồm xe đang chờ không? Vì sao có trạm 109 xe đồng thời khi `tot=45`? Và `tot` (totalCharging) chính xác hiển thị gì trên evcs.vn?
3. **Run crawl thực tế có crash-resume lần nào không** (log enumerate/scrape)? — quyết định mức thiệt hại thật của split-overwrite và race listener, và có cần re-crawl telemetry không.
4. **Re-handoff**: có thể xuất cho Kỳ bản canonical mới (28.625, có `op_status`/`is_primary`/`physical_id`/`connector_standard`) kèm hash khớp MANIFEST trước B4 (30/07) không? *(Cập nhật 28/07: snapshot HF đã tải về `data/` — có thể tự re-handoff từ đây, vẫn cần Giang xác nhận đây là bản chốt.)*
5. 3.417 trạm zero-suốt-7-ngày trùng bao nhiêu % với 3.392 trạm MAINTENANCE? — quyết định giữ hay loại MAINTENANCE khỏi cung baseline.
6. Mã trạm evcs có tồn tại prefix `C.NA…` (Nghệ An?) không? — sentinel partition `province_code="NA"` sẽ đụng độ.
7. POST /search có trần bán kính/kết quả server-side nào ngoài cap 50 không? — hoàn thiện chứng minh độ phủ enumerate.

## 6. Thứ tự ưu tiên xử lý (theo tác động)

1. **HF private/gỡ ngay** — pháp lý, độc lập mọi thứ khác, và vừa nặng thêm 28/07.
2. **3 fix crawl bảo toàn telemetry** trước bất kỳ lần crawl nào tiếp theo: race listener (`socket.off` + validate stationId), `.done`-khi-null, split-overwrite — vì dữ liệu mất/nhiễm ở đây là **không khôi phục được** (server chỉ giữ 168h).
3. **2 fix 1-ngày mở khoá tính đúng đắn feature**: wire `DUP_COORD_SUSPECT` vào `_DIRTY_COORD_FLAGS` (2 file) + viết lại filter covered0 theo `is_operational & PUBLIC & is_primary`.
4. **Re-handoff snapshot chuẩn + Kỳ vá 2 lỗi gold trước B4 (30–31/07)**: dedup nội tập NEW + cờ trạng thái cho new_supply — nếu không, hit-rate T1 tính trên nhãn nhiễm.
5. **`match_official`**: sửa NaN→verified + wire vào Makefile/pipeline (bảo vệ E-DQ2 T1 khỏi suy giảm im lặng).
6. **Trước lần build national tiếp theo**: Overpass remark-check, force-seed khi resume, fail-fast pipeline, soft-penalty cho `built_up`/`no_road`.
7. **Nền tảng cho A2/P1**: chốt phương pháp duration-weighting occupancy, rồi mới build `demand_proxy` thật; đồng bộ schema-contract + bổ sung 4 test đúng chỗ có bug.
