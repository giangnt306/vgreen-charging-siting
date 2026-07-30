# E-DQ5 — `operator` bẩn → thực chất là tín hiệu CHỦ SỞ HỮU chưa parse (bước 12)

`⚪ DOC → FUTURE · ⊘ Won't-fix (chốt 2026-07-30) · Owner: Giang`

> **Quyết định 30/07 (Giang): KHÔNG sửa trong scope.** Lý do là chính kết quả đo bên dưới — tiêu đề gốc
> ("`operator` bẩn") **sai tiền đề**: cột đó là hằng số, không có gì để làm sạch. Phần còn lại (parse chủ sở
> hữu/loại mặt bằng từ `name`) là **thêm feature**, không phải sửa lỗi chất lượng, nên nó thuộc `FUTURE` —
> và nếu mở lại thì phải chạy **sau** [E-DQ6](e-dq6-freetext-cleanup.md). Mục này giữ lại để lần sau không ai
> audit lại từ đầu.

> 🔴 **CẢNH BÁO — phần chẩn đoán chi tiết của issue này đã MẤT.** Bản viết đầy đủ (~130 dòng, gồm bảng đo và bộ
> cổng đề xuất) từng có trong working tree nhưng **chưa bao giờ được commit**: commit `afe27a3` dán một transcript
> vào giữa `known-issues.md` và ghi đè lên nó. Không phục hồi được từ git (`git log -S` chỉ tìm thấy chính đoạn
> transcript). Dưới đây là **toàn bộ những gì còn sót lại**, trích nguyên văn từ các mảnh grep nằm trong transcript
> đó (đã lưu ở scratchpad phiên 30/07). **Phải đo lại trước khi dùng bất kỳ số nào.**

**Chẩn đoán (đảo tiền đề của bản register cũ).** Tiêu đề gốc "trường `operator` bẩn" là **sai**:

- `operator` là **HẰNG SỐ trên tập cung** — 0 null, 0 biến thể hoa/thường, **1** giá trị phân biệt trên 19.015 trạm
  cung (số cung của ngày đo; nay là **18.999**, xem [E-DQ3](e-dq3-admin-enrichment.md)). Không có gì để "làm sạch".
- Tín hiệu thật — **chủ sở hữu / loại mặt bằng** — nằm trong `name`, **chưa parse**: **76,8%** trạm cung mang token
  `Tư nhân`/`NQ`. ⚠️ Đây là **quyền sở hữu/nhượng quyền, KHÔNG phải access**: đừng loại chúng như trạm tư nhân —
  xem memory [[private-owner-not-access]] và [P8](../c-master-data/p8-status-access.md).
- **33** dòng lỗi phạm trù: phương thức thanh toán bị ghi vào cột network.

**Các mảnh đo còn sót lại** (nguyên văn, không suy diễn thêm):

- *"Trên tập cung canonical (`is_operational & PUBLIC & is_primary & coord_resolved`, **19.015** trạm), …"*
- *"…loại mặt bằng nằm trong `name`, chưa parse. Trên **19.015** trạm cung: …"*
- *"**Hai chiều TÁCH RỜI, không phải một cột** (join 18,6M poll occupancy → `occ_mean`/trạm; **18.809/19.015** trạm
  cung …)"* — tức chủ-sở-hữu và loại-mặt-bằng là **hai** trục, không được gộp thành một cột.
- *"**17.588/19.015 = 92,5%**; dư **1.427 (7,5%)** không nhãn ở cả hai."*
- Cổng đề xuất ②: *"`ownership_covers_supply ≥ 0,76` | hiện **0,768** (14.608/19.015)"*

**Việc phải làm (khi mở lại):**

1. Đo lại toàn bộ trên artefact hiện hành (mẫu số **18.999** trạm cung / **12.801** ô), **không** tái sử dụng số 19.015.
2. Parse `name` thành **hai cột tách rời** (chủ sở hữu · loại mặt bằng) sau khi [E-DQ6](e-dq6-freetext-cleanup.md)
   chuẩn hoá text — thứ tự này là ràng buộc, không phải sở thích: parse token trên text chưa chuẩn hoá sẽ đếm sai
   biến thể.
3. Sửa **33** dòng lỗi phạm trù (payment → network) và thêm cổng chặn tái xuất.
4. Dựng lại bộ cổng, mỗi cổng **phải chứng minh FAIL được** trên một input cố ý làm hỏng (doctrine của
   [E-DQ7d](e-dq7d-demand-proxy-validation.md): dự án đã ship 3 cổng không bao giờ FAIL).

**Limitation (`DOC`):** chủ sở hữu/nhượng quyền chỉ suy được từ text marketing trong `name` — không có registry
quyền sở hữu công khai để kiểm chứng ngoại vi, nên đây là nhãn **suy luận**, không phải quan sát.

---

← [Register vấn đề](../../known-issues.md) · [Mục lục issue](../README.md)
