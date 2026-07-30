# P5 — Candidate set chưa định nghĩa & thiếu lọc land-use (hồ/núi/đất cấm)

`🟡 SIMPLIFY · ☑ chốt 2026-07-24 · Owner: Giang`

**Chẩn đoán:** P5 thực chất là **3 câu hỏi độc lập**: (a) candidate sinh từ đâu, (b) điểm nào phải loại, (c) candidate là điểm hay ô H3. Giải chi tiết ở **[candidate-sites.md](../../data-layer/candidate-sites.md)**; tóm tắt bên dưới.

**Cách xử lý:**

- **(c) Granularity — mô hình lai.** Với `R = 3 km`, `d = 0,98 km` → `R/d = 3,07`, hai điểm bất kỳ trong cùng ô H3 phủ gần như y hệt tập ô demand → giữ nhiều điểm/ô gây MCLP **tie-degenerate** (biến thể ẩn của **P4**). Chốt: candidate = **một điểm thực** (giữ toạ độ để explainability), nhưng **tối đa 1 candidate/ô H3 res 8**; coverage tính theo `h3_r8`.
- **(a) Sinh candidate — phân tầng anchor.** T0 trạm hiện có (brownfield, `is_existing=True` — ràng buộc thiết kế: incumbent bắt buộc mở) · T1 `parking`/`fuel` · T2 `mall`/`retail`/`apartments` · **T4 gap-fill tổng hợp** (ô demand cao, buildable, chưa có anchor → centroid `SYNTHETIC`). T4 **bắt buộc** để chống thiên vị đô thị của OSM (POI thưa ở vùng ven → nếu không có T4 thì MCLP không thể chọn ở đó → mâu thuẫn mục tiêu "phủ công bằng" của Nhà nước). T3 rest_area/nút giao QL cần road-class từ `.pbf` → để roadmap.
- **(b) Bộ lọc land-use — 2 mức, `buildable_h3`.** Nền chính **ESA WorldCover 10m v200 (CC-BY)** vì OSM land-use ở VN quá thưa ("không có polygon nước" ≠ đất khô). *Loại cứng:* `frac_water≥0,5` · `water+wetland≥0,7` · `built_up_frac<0,05` (núi/rừng/chưa đô thị hoá) · cờ OSM MILITARY/PROTECTED/AIRPORT/WATER_OSM · `access_tier == ISOLATED` (không có đường trong ô **lẫn** vành 1/2 — **E-DQ8a** 30/07, thay `road_access_m≤0` vốn loại oan 4.862 ô có đường ở ô kề; nguồn vẫn là cột lối vào của **E-DQ7b**, GỒM `service`/`track`). *Phạt mềm:* đất nông nghiệp (`frac_crop≥0,6`) · hạ tầng mỏng · `NEEDS_ACCESS_ROAD` (đường chỉ ở vành — **E-DQ8a**) · `ROAD_ACCESS_INFORMAL` · `ROAD_BRIDGE_ONLY` · `pop>0 & road=0` (cờ chẩn đoán) · khoảng cách tới `power=substation` (proxy đấu nối lưới — Nhóm 2 #3).

**QA gate 5 cổng** (đóng P5 thật, không chỉ "có file candidate"): ① upper-bound coverage của toàn bộ candidate ≥ 90% demand lõi AOI (fail = candidate set chặn model) · ② `|candidates| ≥ 5×p` (tỷ lệ tự do) · ③ `|candidates| ≤ 3.000` (trần giải MCLP) · ④ **anti-degenerate** `unique(coverage_set)/|candidates| ≥ 0,9` (biến thể ẩn P4) · ⑤ gate lưới↔bán kính `R > d` (P4).

**Bàn giao Kỳ:** `data/processed/candidate_sites.{parquet,geojson}` — điểm chạm interop thứ 3. Cột `is_existing` + `capex_class` phục vụ ràng buộc ngân sách Sprint 3.

**Kết quả:**

- **MVP Hà Nội (24/07):** 1.672 candidate (T0 1.411 · T1 96 · T2 54 · T4 111); 79% ô AOI buildable, chỉ 17% ô `pop>0` bị loại (ngưỡng `BUILT_UP_MIN` hợp lý); **mọi gate PASS**.
- **Toàn quốc (national) — đã chạy 24/07:** trên **lưới `demand_h3` quốc gia (268.404 ô)** qua `--national` (`make landuse-national && make candidates-national`). Đã vector hoá/scale: WorldCover 16 tile đất + stride 8, OSM exclusion quadtree + STRtree, substation-dist BallTree, buildable numpy.

**Limitation (`DOC`):** quy hoạch sử dụng đất chính thức VN không public → WorldCover/OSM chỉ là **proxy** (điểm "buildable" vẫn có thể bị cấm theo quy hoạch địa phương); WorldCover 2021 vs 2026 (lệch vintage như **P10**); bias đô thị OSM giảm nhẹ bằng T4 nhưng không khử; candidate `SYNTHETIC` (T4) **không** trình bày như khuyến nghị chốt — phải kèm cảnh báo khảo sát thực địa.

---

← [Register vấn đề](../../known-issues.md) · [Mục lục issue](../README.md)
