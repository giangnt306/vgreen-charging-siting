# `issues/` — một file cho mỗi vấn đề

Tách khỏi `known-issues.md §3` ngày **2026-07-30** (§3 khi đó đã 1.660 dòng). Phân công vai:

| File                                       | Giữ gì                                                                          |
| ------------------------------------------ | ------------------------------------------------------------------------------- |
| [`../known-issues.md`](../known-issues.md) | **Register**: chú giải · bảng trạng thái · thứ tự xử lý & ràng buộc phụ thuộc |
| `issues/<nhóm>/<id>-<slug>.md`             | **Giải pháp**: chẩn đoán · cách xử lý · kết quả đo · QA gate · limitation      |

Chia thư mục theo **5 nhóm vấn đề** của register (30/07) — nhóm là **thuộc tính bền** của issue (bản chất vấn đề),
khác với *trạng thái* và *thứ tự xử lý* vốn thay đổi liên tục nên chỉ sống ở register:

| Thư mục                                    | Nhóm                              | Số issue |
| ------------------------------------------ | --------------------------------- | -------- |
| [`a-demand-target/`](a-demand-target/)     | A · Demand Target & Data Science  | 1 (+2 won't-fix không có file) |
| [`b-spatial-geometry/`](b-spatial-geometry/) | B · Spatial Geometry & Siting Mechanics | 2  |
| [`c-master-data/`](c-master-data/)         | C · Master Data & Entity Resolution | 4      |
| [`d-covariates/`](d-covariates/)           | D · Covariates & Feature Engineering | 2     |
| [`e-data-quality/`](e-data-quality/)       | E · Data Quality & Cleaning       | 17       |

Quy ước mỗi file: `# <ID> — <tiêu đề>` → dòng trạng thái `` `mức · trạng thái · owner` `` → **Chẩn đoán** →
**Cách xử lý** → **Kết quả** → **QA gate** → **Limitation (`DOC`)**. Trạng thái là **của register** — sửa ở
[bảng §2](../known-issues.md#2-bảng-tổng-hợp-vấn-đề-đã-gộp) trước, rồi đồng bộ dòng trạng thái ở đây.

---

## A · Demand Target & Data Science

| ID                                     | Vấn đề                                             | Trạng thái                        |
| -------------------------------------- | ----------------------------------------------------- | ----------------------------------- |
| [P1](a-demand-target/p1-heuristic-weights.md)          | Heuristic weights vs fit model 18,6M occupancy         | ☐ Open — **gộp vào E-DQ7d** |
| P2                                     | Selection bias (chỉ quan sát nơi đã có trạm)   | ⊘ Won't-fix (không có file)     |
| P3                                     | Cửa sổ 7,15 ngày → không thấy mùa vụ          | ⊘ Won't-fix (không có file)     |

## B · Spatial Geometry & Siting Mechanics

| ID                             | Vấn đề                                      | Trạng thái       |
| ------------------------------ | ---------------------------------------------- | ------------------ |
| [P4](b-spatial-geometry/p4-service-radius.md)     | Bán kính suy biến (`R/d < 1` → sort top-p) | ☑ 2026-07-24 |
| [P5](b-spatial-geometry/p5-candidate-set.md)      | Candidate set & lọc land-use                 | ☑ 2026-07-24 |

## C · Master Data & Entity Resolution

| ID                             | Vấn đề                                        | Trạng thái       |
| ------------------------------ | ------------------------------------------------ | ------------------ |
| [P6](c-master-data/p6-duplicate-pk.md)       | Trùng PK & lệch số trạm giữa báo cáo    | ☑ 2026-07-24 |
| [P7](c-master-data/p7-vehicle-class.md)      | Nhiễm xe máy điện (power tier vs chuẩn cắm) | ☑ 2026-07-24 |
| [P8](c-master-data/p8-status-access.md)      | Trạng thái vận hành & access                 | ☑ 2026-07-27 |
| [P9](c-master-data/p9-snapshot-skew.md)      | Lệch thời điểm giữa các đợt crawl        | ☐ Open           |

## D · Covariates & Feature Engineering

| ID                                | Vấn đề                              | Trạng thái       |
| --------------------------------- | -------------------------------------- | ------------------ |
| [P10](d-covariates/p10-worldpop-vintage.md)    | WorldPop 2020 lỗi thời (6 năm)     | ⊘ Won't-fix      |
| [P11](d-covariates/p11-car-ownership.md)       | Dân số tổng vs mật độ sở hữu ô tô | ☐ Open           |

## E · Data Quality & Cleaning

Thứ tự dưới đây **là thứ tự xử lý** (xem [ràng buộc phụ thuộc](../known-issues.md#3-thứ-tự-xử-lý--ràng-buộc-phụ-thuộc)).

| Bước | ID                                                | Vấn đề                                                | Trạng thái                     |
| ------ | ------------------------------------------------- | -------------------------------------------------------- | -------------------------------- |
| 0      | [E-DQ10](e-data-quality/e-dq10-freeze-snapshot.md)               | Freeze snapshot & provenance                             | ☑ 2026-07-27               |
| 1      | [E-DQ9](e-data-quality/e-dq9-aoi-clip.md)                        | Grid toàn quốc vs MVP 1 thành phố                     | ☑ 2026-07-27               |
| 2      | [E-DQ2](e-data-quality/e-dq2-crosssource-dedup.md)               | Trùng chéo nguồn (evcs ↔ official)                   | ☑ 2026-07-27               |
| 3      | [E-DQ1](e-data-quality/e-dq1-coord-placeholder.md)               | Toạ độ placeholder / trùng khít                      | ☑ 2026-07-28               |
| 4      | [E-DQ7a](e-data-quality/e-dq7a-poi-outside-vn.md)                | POI + road ngoài lãnh thổ VN                          | ☑ 2026-07-28               |
| 5      | [E-DQ7b](e-data-quality/e-dq7b-road-semantics.md)                | `road_len` sai ngữ nghĩa                              | ☑ 2026-07-28               |
| 6      | [E-DQ7c](e-data-quality/e-dq7c-poi-taxonomy.md)                  | POI thiếu & lẫn đơn vị                             | ☑ 2026-07-28               |
| 8      | [E-DQ7e](e-data-quality/e-dq7e-pop-calibration.md)               | `pop` chưa hiệu chuẩn tuyệt đối                    | ☑ 2026-07-29               |
| 9      | [E-DQ7f](e-data-quality/e-dq7f-pop-dasymetric.md)                | `pop` dồn cục trong ô + dồn thừa cấp xã           | ☑ 2026-07-29               |
| 10     | [E-DQ8a](e-data-quality/e-dq8a-access-tier.md)                   | Lối vào đo ở thang SAI (`access_tier`)               | ☑ 2026-07-30               |
| 10b    | [E-DQ8b](e-data-quality/e-dq8b-roadless-reallocation.md)         | Dời dân ở ô không có lối vào                        | ☑ 2026-07-30               |
| 10c    | [E-DQ8c](e-data-quality/e-dq8c-servable-denominator.md)          | Dân KHÔNG phục vụ được (mẫu số) + tessellation    | ☐ Open — cần chốt policy |
| 11     | [E-DQ4](e-data-quality/e-dq4-asset-vs-live-config.md)            | Cấu hình đọc ở tầng SAI (LIVE vs ASSET)             | ☑ 2026-07-30               |
| 7      | [E-DQ7d](e-data-quality/e-dq7d-demand-proxy-validation.md)       | **Proxy cầu chưa kiểm chứng ngoại vi** (gate `demand_weight`) | 🔴 ☐ Open — **Kỳ**  |
| ~~12~~ | [E-DQ5](e-data-quality/e-dq5-operator-ownership.md)              | ~~`operator` bẩn~~ → hằng số, không có gì để sạch    | ⊘ Won't-fix 30/07 (tiền đề bị bác) |
| 13     | [E-DQ6](e-data-quality/e-dq6-freetext-cleanup.md)                | Text tự do bẩn (`name`, `address`)                    | ☐ Open — chưa audit        |
| 14     | [E-DQ3](e-data-quality/e-dq3-admin-enrichment.md)                | Cột admin trống + trọng tài toạ độ                | ☑ 2026-07-30               |

> ⚠️ **E-DQ7d nằm ở bước 7 trong tên nhưng chạy SAU E-DQ4** (đổi thứ tự 30/07) — số bước là **danh tính**
> lịch sử của issue, không phải vị trí trong hàng. Vị trí thật nằm ở
> [§3 của register](../known-issues.md#3-thứ-tự-xử-lý--ràng-buộc-phụ-thuộc).

---

## Nguyên tắc chung của nhóm E

- **Flag dòng, không xoá.** Mọi bước phải đối soát `input = output + quarantined + merged`.
- **Thêm cột, không ghi đè** (khuôn 2 cột của E-DQ7b R1): tách **TRÍCH XUẤT** khỏi **CHÍNH SÁCH**.
- **Mỗi cổng QA phải chứng minh FAIL được** trên một input cố ý làm hỏng. Dự án đã ship 3 cổng không bao giờ
  FAIL được (`poi_coords_in_vn` · `road_mt_le_total` · `poi_no_dup`) — đó là lý do có luật này.
- **Kiểm chứng NGOẠI VI** thay vì tự tuyên bố: cổng phải so với nguồn độc lập (registry official, VNSDI DANSO,
  18,6M bản ghi occupancy), không so với chính artefact vừa sinh ra.
