# Review pipeline dữ liệu: aGiang ↔ evcs-dataset → dataset hoàn thiện

> Đánh giá 2026-07-24 (Opus). Đọc code thực tế cả 2 repo, không chỉ doc. Mục tiêu:
> (1) soi luồng crawl → final dataset trên HuggingFace, (2) so cách lấy/làm sạch của
> aGiang vs dự án chính, (3) đánh giá trung thực, (4) kế hoạch tạo bộ dataset hoàn thiện
> theo `evcs-dataset/docs/data-schema-by-phase.md`.

---

## 0. TL;DR — 5 kết luận thẳng

1. **Dataset trên HF (`Wanderer210w/vgreen-charging-siting-data`) chính là output của aGiang, và đây là rủi ro #1 — nhưng KHÔNG phải rủi ro "sạch dữ liệu" mà là PHÁT HÀNH.** Nó public cả `raw/` (crawl thô tramev/evcs.vn), 19.218 file occupancy time-series, 23.240 JSON VinFast, **license "Unknown"**. Dự án chính (`evcs-dataset/src/evcs/publish/export.py`) làm ngược lại: có `_tos_firewall()` loại **mọi cột `evcs_*`** + `assert` không cho lineage `evcs_vn` rò ra `dist/`, và README tuyên bố toàn bộ giữ **nội bộ (vault)** vì ODbL §4.6 + ToS độc quyền tramev/evcs.vn. → **aGiang đang public đúng thứ dự án gốc cố tình chặn.** Phải xử lý trước mọi thứ khác.

2. **"Merge 2 nguồn theo lat/long vì khác ID" thực chất là HAI merge khác nhau, và cả hai đều bị hiểu sai một phần:**
   - **(A) `conflate.py` (dự án chính)** — merge đa nguồn theo **hình học** (H3 block ~350m + blend fuzzy distance/name/operator/connector), **bỏ qua `master_id` của tramev vốn là khóa dedup thật**. Precision công bố **0.974 nhưng bị bơm phồng bởi cấu trúc**; đo trên slice cross-source thật chỉ **P≈0.84 → ~16% merge cross-source sai**.
   - **(B) `evcs_vn ↔ gold` NN k=1 ≤50m** — **KHÔNG phải trộn 2 khảo sát độc lập**: 97.9% cặp trùng **đúng 0m** vì cùng registry VinFast (SAME-LINEAGE). Vấn đề thật ở đây là **monoculture 95% VinFast**, không phải nhầm danh tính.

3. **aGiang SẠCH HƠN dự án chính ở đúng điểm bạn lo** — master khóa theo `station_code` gốc (ID ổn định của evcs.vn), ghép 1-1 timeseries, **0 orphan, không merge hình học**. Đây là thiết kế tránh được bẫy merge-lat/long. **Nhưng** nó chỉ phủ **1 nguồn** (evcs.vn ≈ VinFast), và **tầng dưới có nhiều bug cleaning nghiêm trọng, gồm 2 bug CHẶN** (mất dữ liệu + bộ lọc chết).

4. **Không repo nào hiện có bộ dataset "hoàn thiện"** theo `data-schema-by-phase.md`: dự án chính thiếu occupancy/candidate/land-use trong gold; aGiang thiếu conflate đa nguồn, `demand_proxy` là stub, admin null 100%, schema drift 7/11 cột.

5. **Đường đi đúng = hợp nhất có chủ đích, không phải chọn 1 bỏ 1:** lấy **backbone medallion + conflate + firewall** của dự án chính cho `gold/stations` + `demand_proxy`; lấy **occupancy (A2), candidate_sites/buildable_h3 (A4/P5), vinfast_official xref** của aGiang; và **thay merge-hình-học bằng merge-theo-khóa-cứng** (tramev `master_id` + evcs `station_code` + vinfast `store_id`) — chỉ dùng hình học cho phần không có ID chung.

---

## 1. Hai vũ trụ dữ liệu — không so ngang được

| Chiều | **evcs-dataset (Kỳ) — "clean" backbone** | **aGiang (Giang) — "new data"** |
|---|---|---|
| Nguồn | Đa nguồn: tramev (~22k id), OSM (~422), rabbitevc (82), evpower (17), selex (swap), + NL/FR (Pha 2) | **1 nguồn**: evcs.vn (28.417 catalog: VinFast 19.219 / BSS 9.118 / other 80) + occupancy 18.6M điểm; phụ trợ: vinfastauto.com official, OSM POI/roads, WorldPop, WorldCover |
| Khóa PK | `station_id = "vn-"+sha256(round(lat,5),round(lng,5),fold(name))[:12]` → **phụ thuộc toạ độ+tên** | `station_id = "vn-"+slug(station_code)` → **phụ thuộc ID gốc evcs.vn (ổn định)** |
| Cách gộp trùng | **conflate hình học** (H3 r9 block + blend fuzzy, gated) — bỏ qua `master_id` | **không gộp hình học**: 1 code = 1 trạm, `merge_catalog` chỉ ưu tiên cs>other>bss theo code |
| Kiến trúc | Medallion `00_raw→10_bronze→20_silver→30_gold→dist/` | `raw/ → interim/ → processed/` |
| Chuẩn hoá trường | Có: `normalize/{power,operator,connector}` + admin PIP + H3 | Ít: `derive_power` ngưỡng 25kW; admin **NA 100%**; không PIP |
| Occupancy | **Firewall khỏi gold/dist** (ToS) | **Là trung tâm dataset, publish công khai** |
| QA gate | Nhiều cổng (`run_qa.py`): coord, power band, PK unique, containment, golden precision ≥0.97 | `validate.py`: toàn vẹn khóa + 1-1 timeseries (CRITICAL); giá trị chỉ WARN |
| Phát hành | `dist/` local, **vault/nội bộ**, không có push HF | **Đã push HF công khai, license Unknown** |
| Đơn vị bài toán | gold_core 4 TP + demand_proxy | candidate_sites + covered0 + buildable_h3 (đã chạy national) |

**Điểm mấu chốt:** hai bên dùng **hệ ID khác nhau hoàn toàn**. Khi ghép, bạn lại đối mặt merge-lat/long **lần thứ 3** (gold Kỳ ↔ master aGiang). Vì cả hai ~95% là VinFast same-lineage, phần lớn sẽ trùng 0m (như audit `pha2-evcs-merge-audit.md` đã đo) — **nhưng đừng lặp lại lỗi cũ: hãy ghép bằng `evcs.station_code == tramev provider-id/master_id == vinfast store_id` trước, hình học chỉ cho phần dư.**

---

## 2. Mổ xẻ vấn đề merge (điều bạn lo nhất)

### 2A. `conflate.py` của dự án chính — merge hình học, bỏ khóa cứng
- **Blocking:** mỗi site → H3 r9 + `grid_disk(1)` (~350m). Cặp xa hơn **không bao giờ được xét** → trần recall cứng; trạm trùng có toạ độ hỏng nặng (>350m) tàng hình cả với matcher lẫn với thước đo recall.
- **Quyết định merge** (`accept`): có nhánh **auto-merge thuần khoảng cách `dm≤25m`** cho cặp không-franchise → đây là cơ chế "2 trụ thật trong 1 bãi bị dán làm 1 site". Sau merge, `gold._survivor` lấy **max** công suất & **max** số connector across nguồn → **false-merge thổi phồng cấu hình trạm và mất số đếm per-site thật**.
- **`master_id` của tramev có sẵn nhưng bị vứt vào `attrs`, không dùng để merge** (`tramev.py:57`, `bronze.py:180`). Đây là **cơ hội bị bỏ lỡ lớn nhất** — có khóa dedup thật mà lại đi merge theo proximity.
- **Đánh giá số công bố:** golden set 726–800 cặp, **546/726 nhãn do rule tự sinh** (mirror chính các gate) → **precision 0.974 là vòng tròn (circular)**. Precision người-thẩm-định thật chỉ **~0.73–0.94** (Wilson, trên 23 merge), tune+đo trên **cùng** golden set (không held-out) → lạc quan. Slice **cross_source P=0.84**. Dedup rate 12.8%→9.0% sau khi gỡ franchise merge láo (v0.3).
- **Hệ quả nhận thức:** `n_sources_independent` ~98% = 1 (OSM-với-operator-VinFast bị ép cùng lineage; CASH→None) → `confidence` median 0.47 gần như hằng số, `is_low_confidence` phủ ~98% ô. Đây là **finding thật (coverage VN gần đơn-lineage VinFast), không phải bug** — nhưng mọi metric "đa nguồn/đối chứng" của gold gần như vô nghĩa.

### 2B. `evcs_vn ↔ gold` — cái bạn mô tả "khác id nên join theo lat/long"
- **Cơ chế** (`evcs_vn_agreement.py:142-160`): `cs_tree.query(gold_xy, k=1)` — mỗi gold → **1 evcs gần nhất, đơn hướng, ngưỡng ≤50m**. Liveness/occupancy ghép vào gold theo cặp NN này. Không có ID chung, chỉ khoảng cách.
- **Đo được** (`pha2-evcs-merge-audit.md`): **97.9% cặp ở đúng 0m** (12.218/12.485); chỉ 267 cặp ∈(0,50]; p99=22.7m → ngưỡng 50m gần như vô tác dụng.
- **Kết luận ngược nỗi lo mặc định:** đây **không** phải "trộn 2 khảo sát độc lập → nhầm danh tính hàng loạt". Vì cùng registry VinFast (SAME-LINEAGE) nên toạ độ trùng khít — nó là **VinFast-rejoin-VinFast**. 3 hệ quả thật: (i) enrichment **không độc lập** (đã bị Gate-2 cấm cộng confidence — xử đúng); (ii) **monoculture**: liveness chỉ phủ 99% V-GREEN, 773 trạm ngoài-VinFast (73% non-VinFast) không có liveness → "dead filter" chỉ loại trạm VinFast; (iii) **k=1 undercount magnitude ở hub**: 9.8% gold có ≥2 evcs trong 50m.
- **Rủi ro tương lai:** join k=1/50m/đơn-hướng chỉ "chạy được" vì 2 tập là cùng registry. Nếu sau này đưa **một nguồn thật sự độc lập** qua đúng path này, nó sẽ **gán nhầm danh tính trong im lặng**.

**Tóm lại điều bạn lo:** phần ghép **không sai cơ học như hình dung** (98% trùng 0m same-lineage), nhưng dataset gốc **hẹp về nhận thức** (đơn-lineage VinFast) và **conflate đa nguồn thì bơm phồng precision + bỏ khóa cứng**. Đây là 2 thứ phải sửa khi làm bộ hoàn thiện.

---

## 3. Độ sạch aGiang — các bug THẬT (xếp theo mức chặn)

**🔴 CHẶN (phải fix trước khi dùng làm input model):**
1. **Bộ lọc dirty-coord CHẾT → phủ ảo.** `build_candidates.py:53` và `build_covered0.py:47` lọc theo `quality_flags ∈ {DUP_COORD, COORD_ADDR_MISMATCH}` — nhưng `build_master_evcs` **không bao giờ sinh 2 cờ này** (chỉ có COORD_INVALID/NO_TS/DUP_TS/…). → mọi toạ độ trùng/placeholder (vấn đề "274 trùng toạ độ" mà doc tuyên bố đã chặn) **chảy thẳng vào candidate + covered0**. Phòng thủ P8/§7 chỉ tồn tại trên giấy.
2. **`split_timeseries.py` ghi đè khi resume → mất dữ liệu.** `flush()` mở file mode `"w"` và giả định mỗi station là một khối liền mạch (`:26,48-50`); khi crash-rồi-resume, station bị phát lại ở khối sau **ghi đè** file trước → dedup chỉ đúng trong 1 khối. Đúng kịch bản docstring tuyên bố miễn nhiễm.

**🟠 CAO:**
3. **Telemetry mất im lặng.** Socket timeout → `null` → ghi `.done` không retry (`evcs_scrape.py:190,197`); enrich-mode query lỗi → đánh `seen` vĩnh viễn (`evcs_enumerate.py:226`). "Thiếu telemetry vì lỗi" không phân biệt được với "không có telemetry".
4. **AC/DC = 1 ngưỡng 25kW, không có chuẩn cắm (P7).** `AC_MAX_W=25000` gán nhãn power-tier thành `connector_type`; evcs.vn không lộ CCS2/Type2 → xe máy vs ô tô lẫn lộn.
5. **`built_up_frac<0.05` hard-exclude** loại ~9% dân số / 47% ô `pop>0` nông thôn; ngưỡng hardcoded trên fraction WorldCover nhiễu (national stride=8), chỉ WARN ở 70%.
6. **`verified=True` khi thiếu khoảng cách.** `match_official.py:250`: NaN distance coi như đồng thuận → trạm toạ độ hỏng vẫn "verified" first-party; confidence bị thổi.
7. **NO_ROAD_ACCESS over-exclude gắn với độ phủ OSM.** Ô vắng khỏi `demand_h3` bị fill `road_len_m=0` → hard-exclude (`build_buildable_h3.py:89`); ngược lại `unclassified/service/track` đều tính là đường → thổi `road_len_m`.

**🟡 TRUNG BÌNH / drift:**
8. **`build_demand_proxy.py` là STUB** (`def ...: pass`) — `demand_weight`/`demand_a`/`demand_b` chưa tồn tại dù SCHEMA_CONTRACT mô tả A/B r=0.91 như đã có.
9. **`demand_h3` 7 cột** (thực) vs **11 cột** (contract); `admin_*` NA 100%; `num_ports`=`totalCharging` (xe đang sạc, động) dễ bị dùng nhầm làm số cổng.
10. **Không idempotent:** TIF/PBF skip nếu file non-empty tồn tại (truncated không bao giờ tự lành); `transform_canonical` rmtree+ghi lại (crash → dataset rỗng); `freshness` tính theo max-batch chứ không wall-clock; `VN_BBOX`/`SPLIT_CAP` khác nhau giữa module; số trạm không khớp (28.417/28.625/19.507/13.258 — không reproduce được từ code, thiếu reconciliation).

**Điểm SÁNG của aGiang (giữ lại):** master khóa ID gốc + 1-1 timeseries + 0 orphan; QA time-series per-trạm (dup/monotonic/neg/sparse) tính trong 1 lượt; matcher official 2 tầng (exact_code trước, spatial sau) hợp lý; candidate T0–T4 + 5 QA gate + buildable_h3 là **đúng thứ dự án chính đang thiếu** cho D2/A4/P5.

---

## 4. Độ sạch evcs-dataset (backbone) — mạnh & yếu thật

**Mạnh (giữ làm xương sống):** medallion rõ ràng; **firewall ToS 3 lớp** (bronze isolation → gold containment QA → export firewall, đã test); `normalize/{power,operator,connector}` có guard (power band 0.5–600kW, POWER_SUSPECT DC<20kW, GB/T→AC nếu ≤22kW); admin PIP + COORD_ADMIN_MISMATCH; `gold_core` cắt 4 TP + loại cụm đảo; codebase **tự-document giới hạn rất trung thực** (`docs/pha2-*`).

**Yếu (phải xử khi làm hoàn thiện):**
- conflate bỏ `master_id`, auto-merge `dm≤25m`, survivorship max-across → false-merge thổi cấu hình (§2A).
- golden precision gate **circular** và **không wire `holdout.py`** (bản đánh giá trung thực) vào cổng QA → số lạc quan ship, số tỉnh táo không.
- `vehicle_class="CAR"` **hardcode** cho mọi nguồn non-tramev (`bronze.py:96`) → xe máy có thể lọt bảng ô tô, QA chỉ báo không chặn.
- toàn bộ cột power VN dựa trên **giả thuyết "powerInWh = watts" chưa kiểm chứng** + nhánh im lặng `POWER_ASSUMED_ALREADY_KW`.
- **ghost coord vẫn ship** trong `stations` (COORD_ADMIN_MISMATCH chỉ bị loại khỏi nn/coverage); export không lọc theo confidence.

---

## 5. Kế hoạch tạo bộ dataset HOÀN THIỆN (theo D0→D2)

Nguyên tắc: **1 xương sống + 2 track tách bạch + merge theo khóa cứng + đo lại trung thực.**

### Bước 0 — Xử lý phát hành HF (làm NGAY, chặn mọi thứ)
- Chuyển repo HF `Wanderer210w/...` sang **private**, hoặc gỡ `raw/` + occupancy time-series + VinFast JSON khỏi bản public.
- Gắn **license rõ ràng** + `SOURCES_AND_LICENSES.md` (mượn từ dự án chính). Occupancy evcs.vn + mọi bảng trộn OSM = **vault/ODbL-derived** → không public khi chưa có legal sign-off. Đây là bất biến của dự án chính, aGiang phải kế thừa.

### Bước 1 — Chốt 1 xương sống schema (D0)
- Lấy **gold medallion của dự án chính** làm chuẩn `gold/stations` (34 cột) + `gold/demand_proxy`. Map thư mục aGiang `interim/canonical/*` ↔ `gold/*` (xem `schema_review.md §2.1`). Đồng bộ **số trạm** (reconcile 13.258 vs 19.507 vs 28.417: khai báo rõ "sau lọc BSS + xe máy + non-car" ở từng mốc).
- Sửa `data-schema-by-phase.md`: đánh dấu `agg_h3`/`gold/core` là **"cần build"** (không phải "đã có"); thêm `candidate_sites` là **điểm bàn giao thứ 3**; ghi `demand_a/b` là TODO.

### Bước 2 — Sửa merge (gốc của nỗi lo) — dùng khóa cứng
- **Thêm tầng match-by-ID trước conflate hình học:** `tramev.provider/master_id` ↔ `evcs.station_code` ↔ `vinfast.store_id`. Chỉ những cặp **không** có ID chung mới rơi xuống matcher hình học.
- **Bật `master_id`** trong `conflate.py` như cannot-split / must-link tùy trường hợp; giữ gate operator/person/address.
- **Bỏ/siết auto-merge `dm≤25m`** khi thiếu bằng chứng tên/operator; survivorship: dùng **median hoặc primary-source** cho `num_connectors`/power thay vì blind max (giữ max như cột riêng `*_max`).

### Bước 3 — Đo lại dedup TRUNG THỰC
- Tách **held-out** thật (không tune trên tập đo); thêm **annotator #2 + κ** cho ≥100 cặp; wire `holdout.py` vào QA gate; báo cáo **P/R theo slice cross-source** (số quan trọng nhất). Mục tiêu: thay "0.974 circular" bằng khoảng tin cậy thật.

### Bước 4 — Nạp các bảng aGiang bổ sung (sau khi fix bug §3)
- **A2 occupancy (vault):** master evcs.vn (station_code) là **input calibrate cầu** — nhưng chỉ sau khi fix **split_timeseries overwrite** (concern #2) và **telemetry silent drop** (#3). Ghép vào gold **bằng station_code**, không phải NN 50m; và **chỉ claim occupancy trong tập VinFast** (dán nhãn monoculture).
- **A4/P5 candidate + buildable_h3:** giữ pipeline aGiang nhưng **fix bộ lọc dirty-coord chết** (#1) — sinh thật DUP_COORD/COORD_ADDR_MISMATCH ở producer trước; nới `built_up_frac` gate (#5) hoặc chuyển sang soft-penalty để không mất 9% dân số; xử NO_ROAD over-exclude (#7).
- **vinfast_official xref:** giữ, nhưng **sửa `verified` khi NaN distance** (#6) → NaN ≠ đồng thuận.

### Bước 5 — Xây `demand_proxy` thật (D1)
- Hiện thực `build_demand_proxy` (đang stub): `demand_a = 0.75·pop_n + 0.25·poi_n`, `demand_b = 0.55·poi_n + 0.25·road_n + 0.20·pop_n` (log1p→min-max per-country). Trọng số khai báo, **không fit từ outcome** (tránh circular với A1). Dùng làm 2 biến thể robustness.

### Bước 6 — Cổng QA hợp nhất + versioning
- Gộp QA: toàn vẹn khóa (aGiang) + power band/coord/containment/golden (dự án chính) + **land-use 70% pop-exclude chuyển từ WARN→FAIL-nếu-vượt-ngưỡng**.
- `snapshot_date` + `run_id`, không ghi đè; khóa mốc: cung 2026-07-20, occupancy 07/2026 (P9).

### Thứ tự ưu tiên đề xuất
1. **Bước 0** (pháp lý HF) — ngay, độc lập.
2. **Bước 3 fix #1 + #2 của aGiang** (dead filter + data-loss) — vì candidate/covered0/occupancy hiện đang sai âm thầm.
3. **Bước 2** (merge khóa cứng) — sửa đúng nỗi lo gốc + mở đường ghép 2 repo.
4. **Bước 4–5** (nạp bảng bổ sung + demand_proxy).
5. **Bước 1 + 6** (đồng bộ schema/contract + QA) — chạy xuyên suốt.

---

## Phụ lục — con số neo
- HF hiện tại: 2.2GB, raw/interim/processed/external, 19.218 timeseries, 23.240 VinFast JSON, license Unknown.
- Dự án chính: gold ~13.258 site (sau conflate + lọc), demand_proxy 316.526 ô; conflate P=0.974 (circular) / cross-source 0.84; evcs_vn↔gold 97.9% @0m.
- aGiang: catalog 28.417 (VinFast 19.219 / BSS 9.118 / other 80); occupancy 18.6M điểm; candidate national 16.793 (5/5 QA PASS, upper-bound coverage 0.913); buildable national 60.354 ô (22%).
