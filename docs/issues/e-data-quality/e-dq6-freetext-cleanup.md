# E-DQ6 — Text tự do bẩn (`name`, `address`) (bước 13)

`⚪ SIMPLIFY · ☐ Open · Owner: Giang`

> ℹ️ **Chưa có chẩn đoán.** Issue này đến giờ chỉ tồn tại ở dòng register — chưa audit, chưa đo. File này là **chỗ
> để viết**, không phải bản tóm tắt của việc đã làm.

**Vì sao vẫn mở:** `name`/`address` là text marketing tự do (viết hoa lẫn lộn, dấu/không dấu, viết tắt đơn vị hành
chính, tên tỉnh theo hệ **63 tỉnh CŨ**). Hai consumer đang **chờ** nó:

- [E-DQ5](e-dq5-operator-ownership.md) — token chủ sở hữu/loại mặt bằng nằm trong `name`; parse trên text chưa
  chuẩn hoá sẽ đếm sai biến thể ⇒ **E-DQ6 phải chạy trước**.
- [E-DQ3](e-dq3-admin-enrichment.md) — **197** ca `COORD_ADDR_MISMATCH` còn advisory vì tín hiệu địa chỉ chưa parse
  được. ⚠️ Tín hiệu văn bản ở đây **một chiều** (khớp = bằng chứng, không khớp ≠ bằng chứng ngược) nên nó chỉ có
  thể làm con số phân xử **tốt lên**; vì vậy E-DQ3 **không bị chặn** bởi E-DQ6 — chạy lại phần trọng tài sau E-DQ6
  chỉ là một lệnh.

**Việc phải làm:** chuẩn hoá casing/dấu, tách token đơn vị hành chính khỏi tên riêng, và **giữ cột thô** cạnh cột
chuẩn hoá (nguyên tắc chung của nhóm E: *flag/thêm cột, không ghi đè*).

---

← [Register vấn đề](../../known-issues.md) · [Mục lục issue](../README.md)
