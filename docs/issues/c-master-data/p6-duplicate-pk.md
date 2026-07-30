# P6 — Trùng PK & số trạm lệch giữa các báo cáo

`🟡 FIX · ☑ chốt 2026-07-24 · Owner: Giang`

**Chẩn đoán:**

1. **Trùng PK (236 dòng).** Catalog evcs gộp từ 3 tab (`cs`/`other`/`bss`); enumerate quét lưới
   chồng lấn → cùng `station_code` xuất hiện nhiều lần.
2. **Số trạm lệch (28.417 vs 28.625).** Không phải lỗi dữ liệu mà là **doc-drift**: tài liệu ghi
   snapshot cũ **28.417**, còn file thực tế là snapshot chốt **28.625** (crawl lại 2026-07-21/22).

**Cách xử lý:**

- **Dedup có kiểm soát.** `merge_catalog.py` giữ **first-wins** (ưu tiên `cs > other > bss`),
  **đếm rõ** số dòng trùng bị bỏ (tách trong-tab vs chéo-tab) và in ra — **không bao giờ gộp/cộng
  công suất** giữa các bản trùng (nguyên tắc E-DQ2). `validate.py` có **cổng CRITICAL** bắt buộc
  `station_code` unique → pipeline **fail** nếu trùng PK tái xuất. Master hiện: **0 trùng**.
- **Đối soát số trạm về một snapshot chốt.** Neo **28.625** (snapshot 2026-07-21/22) là con số chính
  thức; chênh **+208** so với 28.417 = crawl lại tab `cs` (19.219 → 19.427). Đồng bộ mọi tài liệu
  ([evcs.md](../../sources/evcs.md), [schema-contract.md](../../schema/schema-contract.md)) + neo **chuỗi đối soát tầng**
  để dứt điểm câu hỏi "số nào đúng":

  $$
  \underbrace{28.625}_{\text{raw catalog}} \;-\; \underbrace{9.118}_{\text{BSS (lọc, --keep-bss để giữ)}}
  \;=\; \underbrace{19.507}_{\text{canonical car-only}} \;=\; \underbrace{19.427}_{cs} + \underbrace{80}_{other}
  $$

**Kết quả.** Master 28.625 trạm, PK `station_code` **unique** (0 CRITICAL), lineage ghi ở
`quality_report.json`. `by_station_type`: VINFAST_CS 19.427 · BATTERY_SWAP 9.118 · OTHER 80.

**Limitation (`DOC`):** đây chỉ giải **trùng PK nội bộ evcs** + đối soát số. Trùng **chéo nguồn**
(cùng 1 trạm vật lý lệch toạ độ giữa evcs và registry official) là **[E-DQ2](../e-data-quality/e-dq2-crosssource-dedup.md)** —
đã đóng 27/07 (identity resolution `physical_id`, **không** dedup H3 thô).

---

← [Register vấn đề](../../known-issues.md) · [Mục lục issue](../README.md)
