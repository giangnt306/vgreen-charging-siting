# P8 — Lọc trạng thái vận hành & access (private vs public)

`🟡 FIX · ☑ chốt 2026-07-27 · Owner: Giang`

**Chẩn đoán:** pipeline **chưa bao giờ lọc** trạm theo trạng thái vận hành hay quyền truy cập
→ trạm **đã ngừng** (OutOfService) vẫn tính là cung, trạm **tư nhân** (Restricted) vẫn tính là cung
công khai, và null (`status` 72 · `is_public` 80) bị **giữ ngầm** không tường minh. Hai trục **độc lập**:
(1) trạng thái vận hành, (2) access public/private.

**Cách xử lý — resolve official-first, tường minh, không xoá dòng.** Registry VinFast là
ground-truth ([[vinfast-official-join-key]]); `status` của evcs chỉ là **snapshot telemetry**
(trạng thái tức thời lúc polling occupancy) nên **không** lật ngược registry (vd evcs `Available`
một khoảnh khắc vs official `INACTIVE` → theo official). Thêm 3 cột canonical vào `stations`:

- **`op_status`** ∈ {`OPERATIONAL`, `MAINTENANCE`, `OUT_OF_SERVICE`, `UNKNOWN`} — official-first,
  fallback evcs khi trạm evcs-only. Gom telemetry occupancy (ACTIVE/BUSY ← Available/AllBusy) về
  `OPERATIONAL`; INACTIVE ← Maintaining → `MAINTENANCE`; OUTOFSERVICE/UNAVAILABLE → `OUT_OF_SERVICE`.
- **`access`** ∈ {`PUBLIC`, `RESTRICTED`, `UNKNOWN`} — official-first (Public/Restricted), fallback `is_public`.
- **`is_operational`** (bool) — **lọc cứng DUY NHẤT:** loại `OUT_OF_SERVICE` (trạm đã ngừng, không
  còn là cung thực). **MAINTENANCE + UNKNOWN GIỮ** (có hạ tầng vật lý / không có ground-truth) — chỉ
  flag để model quyết loc thêm (**chạy 2 chiều** ở bước xử lý khuyết, `E-DQ4`).

Cờ tường minh gắn vào `quality_flags`: `NOT_OPERATIONAL` · `UNDER_MAINTENANCE` · `STATUS_UNKNOWN` ·
`NON_PUBLIC` · `ACCESS_UNKNOWN`. `build_candidates._load_stations` loại **OUT_OF_SERVICE ∪ RESTRICTED**
khỏi anchor **T0** (T0 = incumbent *bắt buộc mở*, CapEx=0 → không được ép mở trạm đã ngừng/tư nhân).

**Kết quả** (19.507 trạm car-only). `op_status`: OPERATIONAL **16.014** · MAINTENANCE **3.392** ·
UNKNOWN **59** · OUT_OF_SERVICE **42**. `access`: PUBLIC **19.418** · UNKNOWN **67** · RESTRICTED **22**.
Cung công khai khả dụng (`is_operational & access=PUBLIC`) = **19.377**. T0 national loại **63 trạm**
(OUT_OF_SERVICE ∪ RESTRICTED) → **19.444**; candidate national **mọi gate PASS**.

**Limitation (`DOC`):** `MAINTENANCE` (3.392, ~17%) là quyết định giữ-làm-cung (siting chiến lược đa
năm coi hạ tầng bảo trì là brownfield hiện hữu); model có thể loại qua cờ `UNDER_MAINTENANCE`. UNKNOWN
(evcs-only, không khớp registry) không có ground-truth → giữ + flag, không suy đoán.

---

← [Register vấn đề](../../known-issues.md) · [Mục lục issue](../README.md)
