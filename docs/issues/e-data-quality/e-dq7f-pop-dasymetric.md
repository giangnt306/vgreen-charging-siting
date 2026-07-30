# E-DQ7f — `pop` phân bổ sai chỗ trong ô (dasymetric spike) (bước 9)

`🟠 FIX · ☑ Xử lý 2026-07-29 · Owner: Giang · Chẩn đoán → cài đặt: 29/07`

> ⚠️ **Sửa con số của register cũ (đo lại trên artefact UNadj sau E-DQ7e).** Mọi số "146 ô / 792.118 dân /
> đỉnh 29.337 / 67 ô mật độ / 82.426 km²" ở bản trước **tính trên raster UN-UNADJUSTED** (trước khi 7e đổi
> nguồn cùng ngày). Trên artefact `worldpop_pop_h3` **thực đang dùng** (UNadj), tỉ số 0,979344 kéo mọi ngưỡng
> tuyệt đối xuống: **139 ô / 745.283 dân (0,764%)**, đỉnh pixel **28.731**, **61 ô** mật độ >48.000/km²
> (đỉnh **80.724/km²**), **giao vẫn = 0**. Bài học phụ: **detector KHÔNG bất biến theo scale** — một phép
> rescale đơn điệu (7e) dịch 7 ô ra/vào tập cờ vì ngưỡng đặt tuyệt đối. Vì vậy detector nay **buộc chạy lại**
> mỗi khi đổi nguồn (`make demand` gọi `reconcile_dasymetric` trước `build_demand_h3`).

**Chẩn đoán.** WorldPop *constrained* (BSGM) rải tổng dân cấp xã xuống **chỉ pixel mặt nạ built-settlement cho là
có người**. Nơi mặt nạ **bỏ sót** (núi đá vôi Đông Bắc/Tây Bắc, đảo), cả xã dồn vào 1–5 pixel — đỉnh **28.731
người trên MỘT pixel 100 m** = 2,9 triệu người/km². Đó không phải mật độ, đó là artefact.

**Detector mật độ cũ (`POP_DENSITY_OUTLIER` >48.000/km²) bắt nhầm tập hoàn toàn — giao = 0:**

| Bộ phát hiện                            |        Số ô | `pop` | trung vị max/pixel | trung vị top-3 |
| ------------------------------------------ | ------------: | ------: | ------------------: | --------------: |
| **pixel bất khả thi** (lỗi thật) | **139** | 745.283 |     **1.252** |  **1,00** |
| mật độ > 48.000/km² (đặc tả cũ)    |  **61** |  2,96 M |                 585 |           0,035 |
| **giao hai tập**                    |   **0** |      — |                  — |              — |

61 ô "mật độ cao" nằm **liền khối** trong lõi TP.HCM (~100 pixel/ô, 500–800 người/pixel — quận nội thành thật);
139 ô hỏng có mật độ **cấp ô** trung vị chỉ **~3.100/km²**, **không ô nào chạm 48.000**. Lỗi **không quan sát
được** ở thang mật-độ-ô mà đặc tả cũ chọn — chỉ lộ ở **cấp pixel**. Cùng họ lỗi `poi_coords_in_vn` của E-DQ7a:
**một cổng đo bằng đại lượng không chứa thông tin về lỗi**.

**BƯỚC NGOẶT — đối chiếu VNSDI DANSO lật đổ tiền đề "chỉ sai chỗ".** Trước 29/07, register giả định *tổng cấp
xã đúng, chỉ vị trí sai* — và tự ghi nhận không nguồn nào trong dự án kiểm được. Nay đã **crawl nguồn dân số cấp
xã ĐỘC LẬP** ([`data/vnsdi/`](../../../src/ev_siting/data/vnsdi/), ArcGIS VNSDI 34DVHC layer 2, **3.321 xã**, DANSO
2025). Spatial-join 2,64M pixel WorldPop → xã (**99,88% gán được**, 0,16% khối lượng ngoài polygon) rồi so tổng
mỗi xã:

| Kiểm chứng                                                                       | Đo được                                                                            |
| ---------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| 1 ô nhiều dân hơn**CẢ XÃ** (bất khả thi — chống lệch niên đại) | **16/139 ô · 321.684 dân (43%)**                                              |
| xã có WorldPop >**1,5× DANSO** (dồn thừa)                               | **50 ô · 468.593 dân (63%)**                                                  |
| cụm đảo Hòn Nghệ + Sơn Hải (An Giang)                                       | WorldPop**117.126** vs DANSO **5.335** (~**22×**)                   |
| tổng WorldPop vs Σ DANSO / Spearman xã                                          | 97,57 M vs 113,63 M · ρ=**0,827**; tỉ số/xã p10–p90 = **0,28–1,36** |

⇒ Với **63% khối lượng bị cờ, `pop` cấp xã CHÍNH NÓ sai** (dồn thừa), không chỉ sai vị trí. **Rải lại giữ nguyên
khối lượng ở đó = rải NGƯỜI MA.** Đây là lý do đặc tả D1–D6 cũ (rải trong ô, bảo toàn khối lượng WorldPop) bị
thay: sửa phải **TÁCH theo tổng độc lập**.

**Hậu quả (đo trên artefact UNadj) — bơm rác vào đúng đỉnh hàm mục tiêu:** **16/139** ô trong top-500 `pop` toàn
quốc · **42/139** ô `buildable=True` (ứng viên T4 khi chạy national) · **5** ô `POP_NO_ROAD` giả (E-DQ8, nay là 5/6.350 và đã dời ở [E-DQ8b](e-dq8b-roadless-reallocation.md)) · chỉ
**14/12.811** ô cung ⇒ **không** chặn E-DQ7d.

---

**Cách xử lý (ĐÃ CÀI ĐẶT) — [`reconcile_dasymetric.py`](../../../src/ev_siting/data/worldpop/reconcile_dasymetric.py).**
Giữ `pop` bất biến từng bit (UN-anchored, cổng 7e còn xanh); thêm cột song song `pop_adj` (đã đặt lại chỗ) +
cờ `pop_pixel_implausible`.

1. **D1 — thống kê pixel + gán xã.** Đọc raster (nơi duy nhất còn pixel), xuất `n_px`, `max_px`, `top3_px_share`,
   `n_eff = (Σp)²/Σp²`, `pop_per_eff_px = Σp²/Σp`, trọng tâm `pop_lat`/`pop_lon`; gán pixel → xã bằng `STRtree`.
2. **D2 — detector cứng** (khuôn hai-detector E-DQ1): `max_px > 1.000` **hoặc** (`pop > 2.000` & `top3 > 0,8`)
   → **139 ô**. Ngưỡng 1.000 nay **neo ngoại vi**: `pop_per_eff_px` của ô lõi TP.HCM đã kiểm chứng dày thật có
   p99 = **737**; ô bị cờ trung vị **1.201** — 1.000 nằm đúng khe đo được, không còn là số đặt tay thuần.
3. **D3 — phân lớp theo tổng độc lập** (trung hoà niên đại bằng tỉ số quốc gia 0,859 = 97,569/113,626):
   **RETOTAL** (WorldPop > 1,5×DANSO → **17 xã**) vs **REPLACE** (còn lại → **53 xã**); **70 xã** ảnh hưởng.
4. **D4 — rải lại theo built-up WorldCover 10 m** trong ranh giới xã (KHÔNG winsorize: cắt ngọn san phẳng lõi
   TP.HCM mà không chạm ô hỏng). RETOTAL: hạ tổng về **0,859·DANSO** rồi rải (gỡ người ma); REPLACE: **giữ tổng
   cấp xã**, chỉ đổi chỗ. 3.771 ô built-up trước đó `pop=0` nhận khối lượng dịch sang.
5. **D5 — neo khối lượng + consumer.** `pop` cho phát biểu **tuyệt đối** (`coverage_pop`, GSO); `pop_adj` cho
   consumer **XẾP HẠNG** (MCLP `demand_weight`, T4). Σ`pop_adj` quốc gia **97,083 M** (−0,499% = 486.399 người
   ma gỡ khỏi đảo/núi) — hệ quả CÓ CHỦ Ý, có cổng canh. **KHÔNG** cân bằng người ma sang xã thiếu toàn quốc
   (việc đó kéo thứ hạng cả lưới theo số 2025, trộn hiệu chỉnh niên đại P10 vào lỗi phân bổ — ngoài scope 7f).
6. **D6 — chặn downstream.** [`build_demand_h3`](../../../src/ev_siting/data/worldpop/build_demand_h3.py) mang `pop_adj`
   + cờ vào `demand_h3`; [`_gapfill`](../../../src/ev_siting/features/build_candidates.py) chấm điểm bằng `pop_adj` **và**
     loại ô `pop_pixel_implausible` không có đường trục/POI xác nhận.

**Cổng QA — 7 cổng, giá trị đo khi chạy 29/07 (mỗi cổng FAIL được):**

| Cổng                                | Đo được 29/07                                                                    |
| ------------------------------------ | ------------------------------------------------------------------------------------ |
| `pop_bit_invariant`                | max\|Δ\| = **0,0** (không đụng cột UN-anchored)                           |
| `no_unflagged_implausible_pixel`   | **0** ô `max_px>1.000` không cờ                                           |
| `flagged_mass_share_lt_1pct`       | **0,764%**                                                                     |
| `retotal_reduces_mass`             | gỡ**486.399** (removed 651.049 − target 164.651) — chỉ HẠ                 |
| `global_mass_accounted`            | \|Σpop_adj − kỳ vọng\| = **0,000 người** (kế toán độc lập nhãn ô) |
| `pop_adj_national_drift_lt_1pct`   | **0,499%**                                                                     |
| `commune_join_coverage` (advisory) | pixel không gán =**0,16%**                                                   |

> Cổng `global_mass_accounted` là chỗ tinh tế: ô nhận vắt biên thuộc **hai** xã nên bảo toàn theo NHÃN ô không
> giữ (lệch 5,2e-3); kế toán theo **TỔNG** trong lượt rải (REPLACE net 0, RETOTAL hạ đúng phần người ma) cho
> residual **0,000 người**. Cùng bài học "đo ở thang mà đại lượng thực sự bảo toàn" của các cổng E-DQ trước.

**Kết quả** (`make demand` → `build_candidates`):

| Đại lượng                        | Trước (`pop`) | Sau (`pop_adj`)                                                      |
| ------------------------------------ | ----------------- | ---------------------------------------------------------------------- |
| ô đảo Hòn Nghệ`8865a30cd5f…` | **28.731**  | **493** (xã 2.546 dân)                                         |
| ô bị cờ trong top-500 quốc gia   | **16**      | **0**                                                            |
| ô built-up bị cờ → ứng viên T4 | 42                | **21 loại · 21 chấm lại** (trung bình 8.727 → 1.834)       |
| `candidate_sites` (Hà Nội MVP)   | 1.707             | **1.707** (không đổi — 7f chạm núi/đảo, không chạm HN) |
| Σ`pop` (UN-anchored)              | 97.563.106        | **97.563.106** (bất biến, cổng 7e xanh)                       |

`make verify-snapshot` **PASS**; mọi validator `osm/validate`, `demand_h3`, `build_candidates` **PASS**.

**Limitation (`DOC`):**

- **DANSO là dân số ĐĂNG KÝ 2025** (+16,5% vs WorldPop 2020; Σ 113,63 M vs GSO 2024 ~101 M). Trung hoà lệch mức
  quốc gia bằng ×0,859 nhưng **lệch niên đại/đô-thị-hoá theo từng xã còn lại** — chính vì thế RETOTAL chỉ kích
  hoạt ở `r > 1,75` (vượt xa mức niên đại giải thích được), và 16 ô "1 ô > cả xã" là lõi **chống lệch niên đại**.
- **Không sửa được nguyên nhân gốc.** Lỗi ở mặt nạ built-settlement của BSGM; ta chỉ **phát hiện + rải lại** theo
  WorldCover. Dựng lại phân bổ tử tế cần lớp built-up độc lập tốt hơn (Microsoft/Google footprints) — roadmap.
- **6/139 ô không có built-up để rải** → giữ tại chỗ, `pop_src = UNREPAIRED_NO_BUILTUP` (đo 29/07: 0 ô — mọi ô
  bị cờ đều có built-up trong xã; nhánh vẫn còn để phòng snapshot sau).
- **Thứ hạng bị xê dịch ⇒ khác E-DQ7e về bản chất** — lý do phải tách hai dòng: 7e an toàn với mọi downstream,
  7f thì không (nên có cột `pop_adj` riêng, không đè `pop`).

---

← [Register vấn đề](../../known-issues.md) · [Mục lục issue](../README.md)
