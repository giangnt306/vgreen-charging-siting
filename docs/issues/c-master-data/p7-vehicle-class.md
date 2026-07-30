# P7 — Nhiễm xe máy điện (dùng chung power tier)

`🟠 FIX · ☑ chốt 2026-07-24 · Owner: Giang`

**Chẩn đoán:** Gốc vấn đề là **nguồn tín hiệu**: `evse_powers` của evcs.vn
chỉ lộ **công suất (W)**, *không* lộ chuẩn cắm. Code cũ suy `AC/DC` từ một ngưỡng power tier
(`AC_MAX_W = 25 kW`) → hai hệ quả:

1. **Sai AC/DC ở dải 20-22 kW.** Đối chiếu registry chính thức VinFast cho thấy **20/22 kW
   là DC CCS2**, không phải AC. Ngưỡng 25 kW gán nhầm **1.588 connector (1.079 trạm)** thành AC.
2. **Không tách được xe máy/ô tô bằng công suất**

**Cách xử lý - chuẩn cắm là sự thật, không phải power tier.** `official_connectors.standard`
lộ chuẩn cắm IEC: `IEC_62196_T2_COMBO` = **CCS2**, `IEC_62196_T2` = **Type2**. Join theo
`(station_code, power_kw)` khớp **100%** (24.406/24.415 connector). Thêm 2 cột:

- `connectors.connector_standard` ∈ {`CCS2`, `TYPE2`, `UNKNOWN`}
- `connectors.vehicle_class` + roll-up `stations.vehicle_class` ∈ {`CAR`, `UNVERIFIED`, `UNKNOWN`}

`current_type` giờ **suy từ `power_type` chính thức** (AC/DC/MIXED), không từ ngưỡng kW nữa.

**Kết quả.** Sau khi lọc BSS (9.118 trạm đổi pin — hạ tầng 2 bánh thật), **100% connector khớp official đều là chuẩn ô tô** (CCS2 8.641 · Type2 15.765)

**Limitation (`DOC`):** chuẩn cắm chỉ xác minh được cho trạm khớp registry VinFast

---

← [Register vấn đề](../../known-issues.md) · [Mục lục issue](../README.md)
