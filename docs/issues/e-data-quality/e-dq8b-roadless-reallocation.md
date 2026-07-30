# E-DQ8b — Dời dân ở ô không có lối vào (bước 10b)

`🟠 FIX · ☑ Xử lý 2026-07-30 · Owner: Giang`

**Tiền đề.** Sau 8a, `ADJACENT`/`NEAR`/`ISOLATED` là ô mà **xe không vào được tận nơi** nhưng vẫn mang
`pop_adj > 0`. Để MCLP nhìn thấy đúng cầu, khối lượng đó phải **dời sang ô đặt trụ được**, không phải bị xoá và
cũng không được để đọng. Dùng lại **đúng bộ máy E-DQ7f** (trọng tài bằng tổng độc lập cấp xã → rải theo built-up →
kế toán khối lượng theo TỔNG), khác 7f ở ba chỗ và **cả ba đều do đo được**:

**① Phạm vi khác.** Detector 7f là detector **dồn cục** (`max_px > 1.000` ∨ `pop>2.000 & top3>0,8`) → 139 ô. Tập
E-DQ8 là 6.350 ô và **giao chỉ 109 ô**. Hai lỗi khác nhau: 7f = "cả xã nhồi vào 1 pixel", 8b = "người ở ô mà xe
không vào được".

**② Khối lượng phần lớn là THẬT — ngược hẳn 7f.** Chạy **cùng phép trọng tài DANSO** trên tập E-DQ8 (join ô→xã
96,7%):

| Phân lớp xã                                         |    Ô | Người | % khối lượng |    7f để so |
| ------------------------------------------------------ | ----: | ------: | --------------: | ------------: |
| `RETOTAL` (WorldPop\_xã > 1,5×DANSO ⇒ người ma) |   765 | 229.224 | **18,5%** | **63%** |
| `REPLACE` (DANSO xác nhận tổng ⇒ chỉ sai chỗ)  | 5.373 | 944.229 | **81,5%** |           37% |

⇒ Với 8b, mặc định là **REPLACE (bảo toàn khối lượng, chỉ đổi chỗ)**. Nếu bê nguyên chính sách của 7f sang đây
thì sẽ **gỡ mất ~800k người thật**.

> **Một tiền đề suýt dẫn tới phép sửa sai — ghi lại để không ai đề xuất lại.** Giả thuyết ban đầu: "dân ở ô
> roadless mà WorldCover không thấy built-up là dasymetric smear" (đo thô ủng hộ: khối lượng ở ô `built_up_frac=0`
> chiếm **47,6%** trong nhóm roadless so với **2,0%** trong nhóm có đường — chênh 24×). **Đo phân bố thì tiền đề
> sụp:** ô `built_up_frac = 0` mà **có** đường có p50 = 97 · p90 = 558 · p99 = **1.779** người; ô `built_up_frac = 0`
> mà **không** đường có p50 = 70 · p90 = 391 · p99 = **1.183** — **đuôi NHẸ HƠN**. Tức "dân trên đất không có
> built-up" là **thuộc tính toàn quốc của cặp WorldPop×WorldCover** (12.182 ô · 2,50 M người); nhóm roadless chỉ
> chiếm 24% của nó, và chênh 24× kia là chênh **tỉ trọng trong tầng**, không phải bất thường **theo ô**. Kết luận
> vận hành: **built-up là TRỌNG SỐ ô nhận, không bao giờ là detector.** Cùng bài học "đại lượng phải chứa thông
> tin về lỗi" của 7a/7f — lần này bắt được *trước* khi cài đặt.
>
> Cùng lúc phát hiện `POP_BUILTUP_DENSITY_CEIL = 750` trong `worldpop/paths.py` là **hằng số CHẾT có docstring
> sai**: 737 vốn là `pop_per_eff_px` (người/pixel hiệu dụng), **không** phải người/ha built-up. Đo đúng đại lượng:
> p99 mật độ built-up lõi TP.HCM r=12 km là **904** (max 1.491). Dùng 750 làm detector gắn cờ **15.056 ô / 8,97 M
> người (9,2% toàn quốc)**, gồm **26 ô lõi TP.HCM/Hà Nội THẬT** ⇒ vô dụng. Đã ghi cảnh báo tại chỗ, **không** đấu
> dây vào cổng nào.

**③ Ô nhận phải ĐẶT TRỤ ĐƯỢC — và điều này sửa một hồi quy của 7f.** D4 của 7f rải theo built-up **không xét lối
vào**, nên nó **đổ người vào ô roadless**: số ô `pop>0 & road_access=0` đi từ **6.350** (`pop`) lên **6.467**
(`pop_adj`).
Ở 8b trọng số ô nhận là `built_ha × 1{access_tier == DIRECT}`.

**Cách xử lý (ĐÃ CÀI ĐẶT) — [`reallocate_roadless.py`](../../../src/ev_siting/data/worldpop/reallocate_roadless.py).**

1. **R1 — lưới hợp nhất + bậc.** `pop ∪ đường ∪ built-up`, tính `access_tier` trên lưới hợp nhất (tổng vành phụ
   thuộc láng giềng nên **không** tính được trên tập con). Loại 191.506 ô đệm ngoài VN do tile WorldCover kéo vào.
2. **R2 — phạm vi:** `pop_adj > 0` & `access_tier ≠ DIRECT` → **6.469 ô / 1.183.197 người**.
3. **R3 — trọng tài cấp xã** (dùng lại `POP_RETOTAL_RATIO=1,5` + `POP_WORLDPOP_OVER_DANSO=0,859`): **92 xã**
   `RETOTAL` · **855 xã** `REPLACE`.
4. **R4 — ô nhận = built-up ∧ `DIRECT`, cùng xã**, trọng số theo `built_ha`. **KHÔNG có nhánh dự phòng** "rải vào
   built-up bất kỳ": bản đầu có nhánh đó và **cổng ② bắt ngay** — nó đổ dân sang một ô roadless KHÁC, tức tự sinh
   lại đúng lỗi đang sửa. Xã không có ô nào vừa built-up vừa `DIRECT` ⇒ **giữ tại chỗ có nhãn**, đầu vào 8c.
5. **R5 — chính sách khối lượng** (kế toán theo TỔNG, bài học cổng ⑤ của 7f):
   `REPLACE`: `target = removed` (bảo toàn tuyệt đối) · `RETOTAL`: `target = removed × (0,859·DANSO / wp_xã) < removed`.
   RETOTAL ở đây **chỉ hạ phần khối lượng đang dời**, KHÔNG viết lại cả xã như 7f — 8b sửa *vị trí của khối lượng
   roadless*, không sửa *tổng của xã*, để hai phép sửa không tranh nhau cùng khối lượng.
6. **R6 — `pop` bất biến từng bit**; mọi thay đổi vào `pop_adj` (hợp đồng D5 của 7f). Artefact mới
   `worldpop_pop_acc_h3.parquet`; `build_demand_h3` nạp theo thang **8b → 7f → 7e**, mỗi bậc in cảnh báo.

**Sổ cái `pop_src`** (kiểm được, không phải tự khai):

| `pop_src`                             |              Ô | Ý nghĩa                                               |
| --------------------------------------- | --------------: | ------------------------------------------------------- |
| `WORLDPOP`                            |         252.529 | không đụng                                           |
| `MOVED_TO_ACCESSIBLE`                 | **6.244** | dời sang ô`DIRECT` cùng xã (8b)                   |
| `REDISTRIBUTED` / `RETOTALED_DANSO` |     2.915 / 936 | ô do 7f xử lý                                        |
| `UNREPAIRED_NO_COMMUNE`               |             222 | ngoài mọi polygon xã → 8c                           |
| `UNREPAIRED_NO_ACCESSIBLE_BUILTUP`    |               3 | xã không có đất vừa built-up vừa`DIRECT` → 8c |

**Cổng QA — 8 cổng, giá trị đo khi chạy 30/07 (mỗi cổng FAIL được):**

| Cổng                                | Đo được 30/07                                                  |
| ------------------------------------ | ------------------------------------------------------------------ |
| `pop_bit_invariant`                | max\|Δpop\| = **0,0**                                       |
| `no_unlabelled_roadless_pop`       | 225 ô còn dân,**0 ô KHÔNG nhãn**                       |
| `retotal_only_reduces`             | gỡ**110.855** người ma (removed 196.865 − target 86.009) |
| `global_mass_accounted`            | \|Σpop_adj − kỳ vọng\| = **0,000 người**               |
| `national_drift_lt_1pct`           | **0,114%** so `pop_adj` sau 7f                             |
| `roadless_mass_strictly_decreases` | 1.183.197 →**42.576** (**−96,4%**)                   |
| `all_received_mass_landed_direct`  | **0** ô không-`DIRECT` nhận thêm dân                  |
| `supply_ranking_shift` (advisory)  | **2.541/12.811** ô cung đổi `pop_adj` (19,83%)          |

> **Hai cổng đã bắt lỗi thật trong lúc dựng** — và đó là lý do chúng được viết để FAIL được. Lần chạy 1: cổng ②
> đỏ với **224 ô** bị bỏ qua im lặng (không gán được xã ⇒ không vào vòng lặp). Lần chạy 2: vẫn đỏ với **2 ô** —
> chính là ô nhận của nhánh dự phòng "built-up bất kỳ", tức phép sửa đang **tái tạo** lỗi. Gỡ nhánh đó xong mới
> xanh. Cổng ⑦ ban đầu đo bằng **nhãn `pop_src`** — nhưng nhãn là thứ code **tự ghi**, kiểm bằng nó thì cổng chỉ
> xác nhận code đồng ý với chính nó (đúng lỗi `poi_coords_in_vn` của 7a); đã đổi sang so `pop_adj` trước/sau trên
> chính các ô không-`DIRECT`.

**Kết quả:**

| Đại lượng                                      |             `pop` (UN-anchored) |              `pop_adj` (sau 7f+8b) |
| -------------------------------------------------- | --------------------------------: | -----------------------------------: |
| khối lượng ở ô roadless                       |                         1.241.833 | **42.249** (**−96,6%**) |
| Σ toàn quốc                                     | **97.563.106** (bất biến) |     96.965.852 (−0,612% cộng dồn) |
| ô`pop>0 & road_access=0` do phép sửa TỰ SINH |                 7f:**+117** |            8b:**0** (cổng ⑦) |

`make demand` PASS · `osm/validate` PASS · `landuse/validate` PASS · `candidates` Hà Nội **1.707** (không đổi) ·
40 test PASS.

**Limitation (`DOC`):**

- **Không sửa được nguyên nhân gốc** — vẫn là mặt nạ built-settlement của BSGM (7f) cộng với OSM thiếu đường. 8b
  chỉ **đặt lại chỗ** theo WorldCover; muốn phân bổ tử tế cần lớp built-up độc lập tốt hơn (Microsoft/Google
  footprints) — roadmap, cùng dòng với limitation của 7f.
- **Ranh giới xã là ranh giới dời dân, không phải nhãn hành chính.** Gán ô→xã ở 8b theo **tâm ô** còn 7f theo
  **pixel**, nên hai bảng có thể lệch ở ô vắt biên. Chấp nhận được vì kế toán theo TỔNG không lệ thuộc nhãn — và
  nhãn admin thật vẫn là việc của **E-DQ3**.
- **Dời trong xã có thể dời khá xa.** Không có ràng buộc khoảng cách: một xã dài thì người có thể nhảy vài km sang
  ô built-up khác. Đúng về mặt "ai phục vụ được họ", nhưng nếu Sprint 3 cần khoảng cách đi lại thật thì phải thêm
  trần khoảng cách vào R4.
- **`ADJACENT` bị dời khối lượng dù chỉ cách 1 vành.** Có thể tranh luận nên **chia tỉ lệ** thay vì dời hết. Chưa
  làm vì chưa có nguồn nào đo được tỉ lệ đó — giữ dứt khoát để cổng kế toán còn kiểm được.

---

← [Register vấn đề](../../known-issues.md) · [Mục lục issue](../README.md)
