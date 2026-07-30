# Kế hoạch review dataset — 2026-07-30 (Kỳ)

> **Nguồn gốc & trạng thái:** port từ `checklist.txt` (nháp ở gốc repo, nhánh `devky/review-dataset`,
> working tree 30/07) vào `docs/review/` theo quy ước cấu trúc khi hợp nhất (B3). Con số trong file đo trên
> **nhánh Kỳ trước hợp nhất** (primary 19.644 · covered0 19.081 · candidate 22.217…) — sau rebuild trên
> `integrate/final` phải đo lại. Mục nhắc tới `coord_quality`/`COORD_LOW_TRUST` đã **chú thích** theo B3
> (pipeline hợp nhất dùng `fix_coords`/`coord_resolved` — xem [known-issues.md §2.1](../known-issues.md)).

Bạn sẽ luôn phát hành một dataset có lỗi. Không có phiên bản nào của dự án này mà `demand_h3` "đúng" —
WorldPop là mô hình, WorldCover là proxy cho quy hoạch, OSM thiên lệch đô thị, telemetry chỉ là cầu K1.
Nếu tiêu chí chốt là "sạch" thì bạn không bao giờ chốt được.

Nhưng có một phân biệt quyết định, và nó không phải phân biệt về mức độ nặng nhẹ:

| | Bản chất | Chấp nhận được? |
| --- | --- | --- |
| **Lỗi dữ liệu** | WorldCover 2021 vs 2026 · pop 2020 vs 2025 lệch 46% lớp URBAN_CENTRE · MAINTENANCE giữ làm cung · T4 synthetic là mặt bằng chưa xác định | Được — nếu đo được, khai ra, và có sensitivity |
| **Lỗi nhận thức** | Không tái lập được · cổng không thể đỏ · lỗi bị nuốt im lặng · số trong doc không khớp số trong file | Không bao giờ — vì bạn không thể bound thứ bạn không thấy |

Ba lỗi CHẶN vừa sửa (L1/L4/L6) đều thuộc nhóm dưới. Không lỗi nào trong đó là "data bẩn" — dữ liệu vẫn thế.
Cái hỏng là bạn không biết mình đang giữ cái gì: `_distinct_store` làm cung sai 131 trạm nhưng gate vẫn PASS;
lớp ranh giới đổi thì mọi số cắt biên đổi mà `verify-snapshot` vẫn PASS.

⇒ Tiêu chí chốt không phải "data sạch" mà là: mỗi lỗi còn lại đều **(a) có tên, (b) có số đo, (c) không đỡ
kết luận nào bạn phát ra**. Đây đúng là học thuyết dự án đã có — flag không xoá, thang phát biểu loại 1/2/3
của `de-bai-v2` §9.1, và §8.1 ("tham số đồng nhất triệt tiêu khỏi xếp hạng"). Không cần phát minh tiêu chí
mới, chỉ cần áp nó cho tầng dữ liệu thay vì chỉ cho tầng mô hình.

---

## Kế hoạch review

### Phase 0 — Chốt "đúng" nghĩa là gì, TRƯỚC khi review (nửa ngày)

Việc này phải làm đầu tiên vì nó chính là cỗ máy sinh doc-drift. `known-issues.md` từng neo các số đã hết
hiệu lực (primary 19.178, covered0 18.839, candidate 28.075 — trong khi file thật trên nhánh Kỳ là
19.644 / 19.081 / 22.217). `de-bai-v2` §7.1 tự nhận điều đó ("nền covered0 = 18.839 đã cũ; mọi số neo phải
tính lại").

**Viết một file duy nhất — kiểu `HANDOFF.json` — chứa mọi con số bàn giao, sinh bằng code, không gõ tay.**
Doc chỉ được trích từ nó. Số nào không sinh được từ code thì không được xuất hiện trong doc.

Đây là bước rẻ nhất và chặn được cả một họ lỗi (P6 doc-drift, F15, L16). *(Sau hợp nhất 30/07 nó còn cấp
thiết hơn: mỗi nhánh in số đo trên artefact của chính nó — rebuild trên `integrate/final` rồi sinh
HANDOFF.json là cách duy nhất có một bộ số chân lý.)*

### Phase 1 — Cổng tái lập (gần xong, cần khoá lại)

Bất biến: chạy pipeline hai lần từ bản sạch → giống bit. Đã kiểm cho `make canonical`. Còn thiếu:

- Áp cho `covered0`-national và `candidates`-national (chưa kiểm hai lần).
- **[L14]:** `make freeze` mặc định đặt `snapshot_id = 2026-07-20` — lùi nhãn snapshot về mốc cũ trong khi
  nội dung là 07-29. Bẫy còn nguyên; ai chạy `make freeze` không nhớ truyền `--snapshot-id` là dán nhãn sai.
  *(Manifest hợp nhất 30/07 ghi rõ: sau tích hợp chạy lại `make freeze` snapshot 2026-07-30 làm bản chân lý.)*
- Mọi artefact trong `data/interim`/`data/processed` phải mang `snapshot_id` + revision. `holdout_split.json`
  chưa có ⇒ **[L13]** pre-registration mất hiệu lực im lặng.

### Phase 2 — Pass phủ định trên từng dấu ☑ (2 ngày, giá trị cao nhất)

Với mỗi mục ☑ trong register, viết một truy vấn trả lời:

> "Nếu lỗi này CHƯA đóng thì tôi sẽ thấy con số nào?"

Rồi chạy nó. Không hỏi "đã đóng chưa".

Cách này bắt được E-DQ2 (đóng sai — nhóm rơi 289→27 sau L1) và xác nhận E-DQ11/E-DQ7a (đóng thật — 0/17.106).
Cùng một phương pháp, hai kết quả trái ngược, và bạn chỉ biết bằng cách chạy.

Quan trọng: đặt các truy vấn đó vào repo như một tầng gate riêng (`tests/data_gates/`), chạy trên **artefact
thật**, không phải unit test trên dữ liệu tổng hợp. Các test hiện tại chạy trên `pd.DataFrame` dựng tay —
chúng không thể bắt L1/L4/L6, và thực tế đã không bắt.

Kèm câu hỏi cho từng gate đã có: "nếu lỗi này xảy ra, gate có đỏ không?" Ba gate đã hỏng đúng kiểu này —
chúng lấy chuẩn từ chính thứ chúng phải kiểm:

| Gate | Lấy chuẩn từ | Hệ quả |
| --- | --- | --- |
| `poi_coords_in_vn` | chính cái bbox đã sinh ra lỗi | luôn PASS |
| `_distinct_store` | PK unique | luôn True |
| `upper_bound_cov` | pop 2020 đã bị tuyên hỏng | không thể FAIL |

### Phase 3 — Sampling có mắt người (1 ngày, không thay thế được)

Rút 20–30 dòng mỗi quyết định rủi ro và tự đọc: nhóm dedup, điểm T4, ô `pop_unsupported`, trạm toạ độ bẩn
*(bản gốc ghi "trạm `COORD_LOW_TRUST`" — lớp đó thuộc `coord_quality` phía Kỳ, không tồn tại sau hợp nhất;
lớp tương đương trên `integrate/final`: `coord_resolved=False` / cụm `COORD_PLACEHOLDER` của `fix_coords`)*,
cụm toạ độ trùng khít.

Không metric nào nói được `C.HCM17177` (TP.HCM) và `C.HYE10751` (Côn Đảo) cùng toạ độ là placeholder, hay
`Vincom Plaza Trà Vinh` ×2 là trùng thật còn `Văn Hiền 1`/`Văn Hiền 2` là hai trạm. Đây là chỗ duy nhất
trong toàn bộ quy trình mà người bắt buộc phải có mặt.

### Phase 4 — Oracle độc lập cho từng lớp (tuỳ lớp)

Việc nên giao cho AI, và là mẫu đã chứng minh hiệu quả: E-DQ12 dùng WorldCover kiểm WorldPop; P10 dùng
nhà/đường OSM làm trọng tài mặt nạ BSGM. Nguyên tắc: **một nguồn không liên quan trả lời cùng câu hỏi**.

Lớp còn thiếu oracle: cột road (chưa có gì kiểm), POI (chỉ có chính OSM — recall fuel 35,9% / parking 8,6%
là đo ngoại vi duy nhất), và toàn bộ tầng cung (official **không phải** oracle — xem dưới).

⚠️ Cạm bẫy phải nhớ: **official không độc lập với evcs** — 99,85% `store_id == station_code`. Mỗi lần thấy
chữ "đối chiếu / xác minh / cross-check" trong repo, hỏi ngay hai nguồn này có thật độc lập không.
`verified=True` cho 99,1% và `confidence` TB 0,995 là cột hằng số: trông như tín hiệu chất lượng, không mang
thông tin, mà vẫn đang được `_pick_survivor` dùng để xếp hạng (**[L2]**).

### Phase 5 — Sensitivity ở tầng QUYẾT ĐỊNH, không phải tầng dữ liệu

Tiêu chí nghiệm thu cho một lớp có lỗi:

> Lỗi đó có làm đảo top-N không?

Không phải "sai bao nhiêu phần trăm". Áp vào các lỗi còn lại (trạng thái đo trên nhánh Kỳ 30/07):

| Lỗi | Đảo quyết định? | Phán quyết |
| --- | --- | --- |
| **[L3]** `.fillna(0.0)` ở `_gapfill` | 17,5% tập T4 đổi, 13,12M người bị chấm 0 | ⛔ phải sửa — sai khuyến nghị xây trạm |
| **[L9]** cap 30′ cho tầng 720h | lệch cohort ~19% ⇒ 19% doanh thu | ⛔ phải sửa nếu phát biểu kinh tế |
| **[L16]** `settlement_class` chỉ có bản 2020 | 46% ô URBAN_CENTRE đổi lớp theo niên đại | 🟠 xuất cả hai cột, để consumer đo |
| WorldCover 2021 vs 2026 | chưa đo, nhưng đồng nhất theo vùng | 🟡 khai limitation là đủ |
| MAINTENANCE giữ làm cung | đã có `covered0_operational` để đo | ✅ chấp nhận được — đã làm đúng cách |
| Toạ độ bẩn (flag, không xoá, đảo ngược được) | không | ✅ chấp nhận được |

Bảng này chính là "cách chấp nhận dataset lỗi": dòng ✅ được phát hành kèm khai báo; dòng ⛔ thì giữ dataset,
rút kết luận — không phải ngược lại.

---

## Việc còn hở lớn nhất, và nó không phải lỗi kỹ thuật

Trước khi bỏ công polish thêm: `de-bai-v2` (chốt 29/07, README bảo đọc trước) tuyên bố hàm mục tiêu phủ
FAIL gate G3 (ρ = −0,114) và G2 AUC 0,452 với trần thật 0,698. Nhưng `demand_h3` + `candidate_sites` +
`covered0` là dataset cho MCLP phủ, và `schema-contract.md` vẫn khai như vậy.

Nghĩa là bạn có thể review rất kỹ một artefact mà **consumer của nó đã bị rút**. Quyết định phạm vi trước
khi review sâu:

- **Tầng cung + cầu thô** (`canonical/stations`, `connectors`, `demand_h3` thành phần): đúng, sạch, dùng
  được cho cả hai bài toán ⇒ chốt được.
- **`candidate_sites.parquet`**: artefact của hàm mục tiêu đã rút. `de-bai-v2` §2.2 nói tập ứng viên tốt
  nhất là các trạm AC-only đã có sẵn trong canonical; §6.4 nói T4 synthetic nên bị thay bằng mặt bằng thật
  ⇒ đừng chốt cái này làm bàn giao cuối.

---

## Nếu chỉ làm được vài việc

1. **Phase 0** — sinh `HANDOFF.json` bằng code, doc chỉ trích từ nó. Chặn cả họ doc-drift, rẻ nhất.
2. **Phase 2** trên 6 mục ☑ nặng nhất (E-DQ1, E-DQ2, E-DQ7a, E-DQ12, P8, P10) — viết truy vấn phủ định,
   đặt vào `tests/data_gates/`.
3. **Sửa [L3]** — lỗi duy nhất còn lại làm sai khuyến nghị, không chỉ sai báo cáo.
4. **Phase 3** sampling trên nhóm dedup mới + điểm T4 — 1 ngày, và nó là thứ AI không làm thay được.

Còn "bài tổng hợp theo từng bước": register + issues/ đã là bài đó, và bản cũ 569 dòng chính là nơi ba lỗi
CHẶN trú ẩn suốt mấy đợt review. Thêm một bài nữa không mua thêm gì; thêm một truy vấn chạy được thì có.
