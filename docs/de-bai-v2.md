# ĐỀ BÀI v2 — Thẩm định & quy hoạch vị trí trạm sạc V-GREEN

> **Chốt 2026-07-29.** Thay thế phần *định nghĩa bài toán* của [`problem-analysis.md`](problem-analysis.md)
> (viết 20/07, trước khi có yêu cầu BO và trước khi đo được ba kết quả âm ở §1.2). Phần *phân tích
> nguồn dữ liệu* và *roadmap sprint* của file cũ vẫn còn hiệu lực.
>
> **Quy tắc phân xử:** code thắng doc · số đo thắng số chép lại · **văn bản BO thắng suy đoán của ta**.

---

## §0 · Nguồn thẩm quyền — đọc trước mọi thứ khác

Đây là mục quan trọng nhất của tài liệu. Mọi dòng trong đề bài phải truy được về **một trong bốn** mức
dưới đây, và mức được ghi ngay tại chỗ phát biểu.

| Mức | Nhãn | Nghĩa | Ai được đổi |
|---|---|---|---|
| **A1** | `YÊU-CẦU` | Nguyên văn từ BO/mentor — `requirements.txt`, `sample_hard_rule.txt` | Chỉ BO/mentor |
| **A2** | `ĐO-ĐƯỢC` | Số đo trực tiếp trên dữ liệu, có ngày + đường tái lập | Đo lại thì đổi |
| **A3** | `TA-QUYẾT` | Ta có toàn quyền (mentor xác nhận 29/07); phải nằm trong §8 Sổ giả định | Ta, kèm sensitivity |
| **A4** | `GIẢ-ĐỊNH-HỞ` | Chưa quyết, chưa đo — **cấm** xuất hiện trong bất kỳ khuyến nghị nào | — |

**Toàn bộ tài sản A1 của dự án là hai file văn bản.** Không có gì khác. Mọi thứ còn lại là A2 hoặc A3.
Điều này **không** làm dự án yếu đi — nó làm nghĩa vụ khai báo trở nên tuyệt đối rõ ràng.

### §0.1 · Nguyên văn A1 — trích để không phải mở lại file

**Từ `requirements.txt` (yêu cầu ban đầu + trong quá trình khảo sát):**

1. *"Quy hoạch vị trí trạm sạc tối ưu (**theo công suất, mật độ, lưu lượng xe**)"*
2. *"Phân tích hiệu quả vận hành trạm và đề xuất triển khai (**giữ nguyên, nâng cấp hoặc di dời**)"*
3. *"**Gợi ý phê duyệt vị trí đặt trạm sạc do nhà phân phối đề xuất** nhằm bảo đảm **quyền lợi và hiệu
   quả kinh doanh cho nhà phân phối**"*
4. Nỗi đau: *"người đánh giá cần **tự tổng hợp** nhiều tiêu chí: số trạm gần đó, hiệu suất trạm gần đó,
   loại trụ/cổng sạc, trạng thái triển khai và business sense"*; *"chưa có một **lớp tổng hợp chuẩn**"*
5. *"tránh tình trạng chỉ dựa vào cảm tính hoặc **một ngưỡng đơn lẻ như hiệu suất > 30**"*
6. Output: 3 tier — *Đồng ý phê duyệt* / *Cần review thêm* / *Từ chối phê duyệt* — **kèm lý do**, kèm
   `score`, kèm *"các chỉ số/thông tin chi tiết"*
7. *"Hệ thống **không tự động đưa ra quyết định** thay cho con người"*
8. Tích hợp qua **API hoặc bản đồ/dashboard**, *"tùy định hướng phát triển của product"*

**Từ `sample_hard_rule.txt` (7 điều):**

| # | Nguyên văn (rút gọn) | Vai trò trong mô hình |
|---|---|---|
| **L1** | Lọc trạm từ **depot** VF: *ngày hoạt động ≠ null* + *blockstatus đang mở* | định nghĩa `S₀` |
| **L2** | Trạm **chỉ có trụ AC** → không đưa vào đánh giá, không hiện trên bản đồ | lọc `S₀` + sinh ứng viên nâng cấp |
| **L3** | Hiệu suất tính **theo tháng**: từ **daily** VF → `sum(kWh)` + `avg(hiệu suất)` | định nghĩa đại lượng hiệu suất |
| **L4** | Quận/Phường/**Thị xã**: được mở gần — *miễn đảm bảo hiệu suất* | tắt L5/L6 ở đô thị |
| **L5** | **Xã**: bán kính **2 km** không được có trạm khác → **không phê duyệt** | ràng buộc cứng có điều kiện |
| **L6** | Xã + **trạm cao tải**: được mở nếu **> 500 m** và không vi phạm công suất | nới L5 |
| **L7** | Lân cận hiệu suất **>30%** → đồng ý · **<30%** → từ chối · **hỗn hợp** → sense người duyệt | gate 3 giá trị |

> ⚠ **Bất khớp phải đóng:** tài liệu nội bộ `results-rules-encoding.md` (repo `evcs-dataset`) encode
> thêm **R8** (2 km giữa các *đề xuất* với nhau) và **R9** (phân lớp công suất) và ghi nguồn *"BO, 9 điều"*.
> File A1 ta có chỉ có **7 điều**. ⇒ **R8/R9 tạm hạ xuống `A3 TA-QUYẾT`** cho tới khi mentor xác nhận.
> Điều này quan trọng vì R8 là thứ **phá bảo hành 1−1/e** và làm gap greedy xấu đi 3× (0,32% → 0,95%).

---

## §1 · Vì sao viết lại — ba kết quả âm đã đóng cửa hướng cũ

### §1.1 · Hướng cũ là gì

`problem-analysis.md` §3 (DoD cuối dự án) đặt: *"đặt trạm ở đâu, bao nhiêu trạm, **coverage bao nhiêu %
theo từng mức ngân sách**"*. Toàn bộ Sprint 1–2 xây quanh **MCLP tối đa phủ dân số**.

### §1.2 · Ba kết quả âm `ĐO-ĐƯỢC` đã đóng cửa nó

| # | Kết quả | Số | Nguồn |
|---|---|---|---|
| **N1** | Hàm mục tiêu MCLP **xếp ngược** kết quả vận hành trên chính mạng đang chạy | ρ(Δ phủ biên, util) = **−0,1144**; tỷ số ngũ phân vị **0,76×**; **47,1%** trạm DC có Δ = 0 | `results-objective-validity.md` (G3) |
| **N2** | Máy chấm v0 **không phân biệt được** nơi operator thật đã xây với ô ngẫu nhiên | AUC **0,452**; 81,1% ô cầu-thấp được Đồng ý | `results-t1-retrodiction.md` (T1) |
| **N3** | Ở thước đo phủ, mạng **đã bão hoà** — biên của tối ưu rất mỏng | HN nền **0,9909**, +20 trạm = **+0,68 pp**, bộ tối ưu **tự dừng ở 16 điểm** | `results-pilot-cities.md` |

**Cơ chế của N1 (phải hiểu, không chỉ ghi nhận):** max-coverage thưởng cho phần *chưa được phủ*. Trên một
mạng operator đã đặt ~19k trạm ở đúng trung tâm cầu, *"chưa ai xây ở đây"* là **chỉ báo của cầu thấp**,
không phải của cơ hội. Bằng chứng đối lập, cùng lớp dữ liệu cùng bán kính: **tổng** dân trong 3 km cho
ρ = **+0,3055**, **biên** cho **−0,1144**. ⇒ **Cái hỏng là phép lấy biên — tức là chính định nghĩa MCLP.**

**Và một quan sát ít ai để ý:** **82,71%** ứng viên có `marginal = 0`. Một hàm mục tiêu bằng hằng số trên
4/5 miền khả thi thì **không còn sức phân giải**, bất kể solver nào.

### §1.3 · Đồng thời: coverage **chưa bao giờ là yêu cầu**

`YÊU-CẦU` #1 nói *"theo **công suất, mật độ, lưu lượng xe**"*. Không có chữ "độ phủ dân số".
⇒ Tiêu chí *"coverage % theo mức ngân sách"* là **tự áp**. Bỏ nó **không cần xin phép ai** — chỉ là quay
về đúng chữ của BO.

### §1.4 · Cái KHÔNG hỏng — để không đi sửa nhầm chỗ

| Thành phần | Bằng chứng |
|---|---|
| **Thuật toán** | gap greedy↔exact **0,00–0,32%** (không luật) / **0,00–0,95%** (có R8); MILP brownfield quốc gia tối ưu chứng minh được trong **3,7–3,8 s**. **Đóng.** |
| **Kernel phủ & tầng fact** | B8: **0/20 lỗi fact**, oracle độc lập; 15 golden test + 9 test cho chính bộ kiểm |
| **Tầng occupancy** | bit-exact 19.218/19.218 với duckdb gốc |
| **Kỷ luật** | pre-reg · adversarial-verify · nhãn bằng chứng — giữ nguyên, **có sửa 3 lỗ hổng** ở §9.4 |

> **Fail không phải do code sai. Code làm đúng thứ được yêu cầu; thứ được yêu cầu là sai.**

---

## §2 · Hai chế độ sản phẩm — và vì sao là **một** mô hình

`YÊU-CẦU` #1 và #3 là hai chế độ khác nhau về chiều dòng chảy, giống nhau về hạt nhân toán:

```
Hướng A — SINH (công ty)
   Cho: ngân sách X trạm (hoặc B đồng) trên một địa bàn
   Ra:  tập S vị trí đề xuất + chứng chỉ tối ưu + đường cong X ↦ giá trị

Hướng B — CHẤM (nhà phân phối)
   Cho: một điểm q do NPP nộp (chỉ cần lat/lng)
   Ra:  tier + score + reasons[] + bảng chỉ số  ← YÊU-CẦU #6

               ↑ CÙNG một đại lượng: ΔΠ(q | S₀) — thay đổi giá trị của TOÀN MẠNG khi thêm q
```

**Bất biến nối hai hướng — viết được thành test hồi quy:**

```
∀ q ∈ solve_A(X):   verdict_B(q) ≠ "Từ chối phê duyệt"
```

Bộ sinh không bao giờ được đề xuất thứ bộ chấm sẽ từ chối. Chiều ngược lại **không** bắt buộc: một điểm
hợp lệ vẫn có thể có `ΔΠ` thấp. Đây là thứ biến "hai sản phẩm" thành "một mô hình".

**Chế độ thứ ba — `YÊU-CẦU` #2 (giữ nguyên / nâng cấp / di dời)** — dùng **cùng** `ΔΠ` với biến quyết định
là *cấu hình* thay vì *vị trí*. Không phải mô hình mới.

### §2.1 · Ba loại quyết định — một mô hình, **ba bậc bằng chứng khác nhau**

Lead chốt 29/07: *"thuật toán vẫn chạy trên tất cả mọi thứ … nhưng chọn cái ta mạnh nhất."*
Mô hình biểu diễn cả ba. **Hợp đồng output thì KHÁC nhau**, theo đúng bằng chứng đo được:

| Quyết định | Bằng chứng mạnh nhất | Bậc | Được phép phát biểu |
|---|---|---|---|
| **① Nâng cấp / định cỡ** (AC→DC, thêm trụ) | `util ↔ max_power_kw` ρ **+0,342** · `↔ num_connectors` **+0,235** — **mạnh nhất toàn dự án**. `util` DC / AC = **1,42–2,29×** ở **mọi** vùng đo. Nâng cấp mua **+25,3 pp** vs xây mới +16,4 pp ở vùng pilot | ✅ **MẠNH NHẤT** | Khuyến nghị **có xếp hạng** (loại 2) |
| **② Mở mới** | Còn nghĩa ở vùng chưa bão hoà (+16,4 pp). Nhưng objective phủ **FAIL G3**; trần dự đoán AUC **0,698**; T4 synthetic = mặt bằng **chưa xác định** | 🟡 TRUNG BÌNH | **Vành ~400 m + hồ sơ**, kèm caveat |
| **③ Đóng cửa / di dời** | Nhận diện được trạm util thấp. **Nhưng:** không có COD ⇒ **không phân biệt được ramp-up với thất bại**; cửa sổ 30 ngày ⇒ chưa loại được mùa vụ; không có hợp đồng/giá trị chiến lược. Và là khuyến nghị **không đảo ngược được** | 🔴 YẾU NHẤT | **CHỈ danh sách theo dõi (facts, loại 1)** — *"N trạm nằm ở thập phân vị thấp nhất trong lớp, đây là số liệu, người quyết định phải xác định vì sao"*. **KHÔNG BAO GIỜ là khuyến nghị.** |

### §2.2 · 🔑 Mạng AC-only là **tập ứng viên đã được xác thực trước**

Đây là hệ quả quan trọng nhất của §2.1 và nó gỡ đúng nút sâu nhất của cả dự án
(*"tập ứng viên thật không quan sát được"* — micro-siting không phải dữ liệu mở):

> **13.149 trạm chỉ-AC là 13.149 mặt bằng mà V-GREEN ĐÃ chọn, ĐÃ thuê được, ĐÃ đấu điện, ĐÃ có bãi đỗ.**
> Chúng là *mặt bằng khả thi đã được bộc lộ* — thông tin micro-siting duy nhất ta có được **miễn phí**.
> Luật L2 rút chúng khỏi phần-được-tính-cung, và **chính điều đó biến chúng thành tập ứng viên tốt nhất
> ta từng có** — không phải ô lưới tổng hợp, không phải centroid lệch 353 m.

⚠ **Hiệu chỉnh bắt buộc mang theo:** trạm chỉ-AC gần như **toàn bộ là 1 trụ**
(`ĐO-ĐƯỢC`: Nam Định–Thái Bình 228 trụ / 227 trạm · Hải Dương–Hưng Yên 281/281 · Hà Nội 1.459/1.225).
⇒ Lợi thế thật là **đất + quan hệ chủ mặt bằng + bãi đỗ**, **không** phải công suất đấu nối sẵn có
(đấu nối 1 trụ AC là rất nhỏ). Đừng bán "nâng cấp = rẻ vì đã có điện" — bán *"đã có mặt bằng khả thi
được xác thực bởi chính operator"*.

---

## §3 · Đại lượng quyết định

### §3.1 · Định nghĩa

Với điểm `q`, cấu hình `c` (số trụ × công suất), trên nền mạng `S₀`:

```
ΔΠ(q, c | S₀)  =  DT_bắt_được(q,c)  −  DT_bị_hút_khỏi_S₀  −  (CapEx/T + OpEx)
                        │                      │                     │
                        │                      │                     └─ §8 sổ giả định
                        │                      └─ "tính ảnh hưởng" — số hạng YÊU-CẦU #3 đòi
                        └─ mô hình phân bổ cầu có sức chứa
```

### §3.2 · Vì sao đại lượng này, không phải coverage

| Tiêu chí | max-coverage | `ΔΠ` |
|---|---|---|
| Qua gate G3 (§9.2)? | ❌ ρ = −0,114 | ✅ dựng từ **tổng cầu tiếp cận được** (ρ = +0,306) |
| Diễn đạt được **công suất** (`YÊU-CẦU` #1)? | ❌ `y_j` nhị phân: ô 12 trạm ≡ ô 1 trạm | ✅ `cap` là biến |
| Diễn đạt được **quyền lợi NPP** (`YÊU-CẦU` #3)? | ❌ | ✅ chính là số hạng giữa |
| Phân giải miền quyết định? | ❌ 82,71% ứng viên objective = 0 | ✅ mọi điểm nhận một phần cầu |
| Trả lời được *giữ/nâng/dời* (`YÊU-CẦU` #2)? | ❌ | ✅ đổi `c`, giữ nguyên máy |

### §3.3 · Cái mất khi đổi — khai trước

1. 🔴 **Mất bảo hành 1−1/e.** Chi phí cố định làm hàm mục tiêu **không đơn điệu**; ràng buộc ngân sách
   *tiền* (không phải *đếm*) hạ bảo hành greedy từ **0,632** xuống **0,405** (Tang et al. 2021 — và
   chứng minh gốc Khuller–Moss–Naor 1999 cho hằng 1−1/√e **là sai**, Zhang 2018 chỉ ra).
   → **Trả giá bằng scope:** ở địa bàn 1/3 tỉnh (vài trăm ứng viên) **MILP giải exact**, không cần bảo
   hành xấp xỉ. *Thu hẹp phạm vi mua đúng thứ nâng cấp mục tiêu tiêu tốn.*
2. 🔴 **Mô hình hiệu chuẩn từ throughput quan sát ⇒ vẫn bị điều kiện hoá bởi cung.** Nó tái lập logic
   mạng hiện tại tốt hơn MCLP, nhưng **không phát hiện được cầu tiềm ẩn** ở nơi chưa có trạm nào; độ lớn
   phần đó **không định danh được** với dữ liệu hiện có.
   → **Bảo hiểm bằng cấu trúc:** giữ **sàn phủ dạng ε-constraint** làm **RÀNG BUỘC**, không làm mục tiêu
   (§5). Số đã có: sàn ε = 0,50 kéo phân vị 25 của vùng từ **1,97% → 52,2%** (26×) với giá **1,82 pp**.
3. 🟠 **Nhiều tham số hơn ⇒ nhiều mặt tấn công hơn.** Bài học nhóm trước: *chi tiết ≠ chính xác*.
   → Giới hạn: mọi tham số kinh tế nằm trong §8, tối đa ~8 dòng, mỗi dòng có khoảng + sensitivity.

---

## §4 · Phát biểu toán học

### §4.1 · Thể hiện

```
⟨ I, J, d, T, S₀, cap(·), cost(·), xa(·), η(·) ⟩
```

| Ký hiệu | Nghĩa | Nguồn |
|---|---|---|
| `I` | tập ứng viên (Hướng A) hoặc `{q}` (Hướng B) | §6.2 |
| `J` | nút cầu trong địa bàn | lưới H3 r8 (`ĐO-ĐƯỢC` 268.404 ô toàn quốc) |
| `d_j` | cầu tại `j` (kWh/tháng) | hiệu chuẩn ngược từ throughput quan sát — §7.2 |
| `T[j,k]` | **thời gian lái** j → k | **OSRM** (`A3`, thay Euclid — §6.3) |
| `S₀` | mạng hiện hữu được tính cung | **L1 + L2** tái dựng — §7.1 |
| `cap_k` | sức chứa (kWh/tháng) | `n_ports × kW × 730 h × utilisation ceiling` |
| `cost_i` | CapEx + OpEx | §8 |
| `xa(i)` | i ở **Xã** hay không | quyết định L5/L6 áp hay không — ⚠ proxy 72,9% |
| `η(k)` | hiệu suất trạm đang vận hành k | L7 — **báo theo phân vị**, §7.3 |

### §4.2 · Mô hình (Hướng A)

```
biến:  x_i ∈ {0,1}     mở ứng viên i
       u_i ∈ ℤ₊        số trụ tại i          ← "công suất" của YÊU-CẦU #1
       z_jk ≥ 0        phần cầu j do trạm k phục vụ

max    Σ_jk d_j z_jk · m           −  γ · Σ_jk d_j z_jk · T[j,k]   −  Σ_i cost_i(u_i) x_i
       └ biên đóng góp mỗi kWh        └ phạt tiếp cận (γ = chọn giá trị, §5.3)

s.t.   Σ_k z_jk ≤ 1                            ∀j    cầu được phép KHÔNG phục vụ
       Σ_j d_j z_jk ≤ cap_k(u_k) · x_k         ∀k    SỨC CHỨA
       z_jk = 0  nếu  T[j,k] > T_max                 chỉ cầu ĐI ĐƯỢC tới
       Σ_i cost_i x_i ≤ B    hoặc   Σ_i x_i ≤ X      ngân sách (2 biến thể, báo cả hai)
       Σ_{j∈R} d_j (Σ_k z_jk) ≥ ε · D_R        ∀R    SÀN CÔNG BẰNG (§5.2)
       x_k = 1, u_k = u_k⁰                     ∀k∈S₀ trạm đã triển khai BẤT KHẢ XÂM PHẠM
       + tiền lọc L2 / L5 / L6                       (§5.1)
```

**Hướng B** = cùng mô hình với `I = {q}`, đọc ra `ΔΠ(q)` và bảng phân rã theo trạm bị ảnh hưởng.

### §4.3 · Bất biến bắt buộc (có test)

| # | Bất biến | Lý do |
|---|---|---|
| **B0′** | **Trạm đã triển khai không bị bộ tối ưu đóng/di dời.** Đóng cửa nằm trong phạm vi *sản phẩm* (§2.1 ③) nhưng **KHÔNG** là biến quyết định của solver — nó ra ở **danh sách theo dõi** riêng, dạng facts. Lý do: thiếu COD ⇒ không phân biệt ramp-up với thất bại | `assert_existing_untouched` |
| **B1** | Bộ sinh ⊆ bộ chấm cho phép (§2) | test hồi quy |
| **B2** | Nền `S₀` tính trên **toàn bộ** mạng, không chỉ trong địa bàn | trạm ngoài ranh vẫn phục vụ vào trong |
| **B3** | Cùng một **hệ quy chiếu phủ/khoảng cách** giữa mọi tầng | `_assert_same_frame` 25 mẫu mỗi lần dựng |
| **B4** | **Cấm claim loại 3** (dự đoán tuyệt đối: kWh/tháng của trạm chưa xây, doanh thu) | §9.1 |
| **B5** | Mọi output mang `data_version` · `model_version` · nhãn `v0 — chưa calibrate` | — |

---

## §5 · Ràng buộc — phân loại theo mức cưỡng chế

Dùng bộ nhãn của file `list_cau_hoi_rang_buoc.xlsx` (nguồn: intern toán, `A3`). Nguyên tắc bất di:

> **Luật quyết định TÍNH HỢP LỆ. Bộ tối ưu quyết định THỨ TỰ ƯU TIÊN. Không trộn hai thứ vào một điểm số.**

### §5.1 · Ràng buộc cứng — từ A1

| ID | Nội dung | Dạng toán | Hàng MILP | Trạng thái |
|---|---|---|---|---|
| **L2** | trạm chỉ-AC không tính cung | lọc `S₀`, đồng thời **thêm** ô AC-only vào `I` (nâng cấp) | 0 | ✅ encode được |
| **L5/L6** | xã: 2 km (500 m nếu cao tải) | **MỀM** (Q1): `D₀(i) = 2000·xa·(1−hl) + 500·xa·hl`; vi phạm ⇒ **cờ + hạ tier**, không tiền lọc | 0 | ⚠ đứng trên `xa(·)` chỉ đúng **72,9%** |
| **L4** | đô thị: tắt L5/L6 | không sinh ràng buộc. **"Thị trấn" + "Thị xã" xếp về ĐÔ THỊ** (Q5) | 0 | ✅ khoảng trống 12,6% đã đóng |
| **B0** | T0 bắt buộc mở | `x_k = 1` | 0 | ✅ |
| **cap** | sức chứa | `Σ_j d_j z_jk ≤ cap_k x_k` | \|K\| | ✅ **MỚI** — thứ mô hình cũ không có |

### §5.1a · 🔑 Luật MỀM + cơ chế vượt luật — cách giữ được cả Q1 lẫn Q3

Q1 nói luật khoảng cách *"chỉ là nên như vậy, linh hoạt khi vị trí thật sự đắt địa"*. Q3 nói **giữ tier
"Từ chối"**. Hai điều đó chỉ mâu thuẫn nếu luật là **tiền lọc**. Giải bằng cơ chế:

```
verdict(q) =
  "Từ chối phê duyệt"   ⟺  vi phạm luật cứng  ∧  KHÔNG có override_reason được ghi nhận
  "Cần review thêm"     ⟺  vi phạm luật mềm  ∨  có cờ §5.4  ∨  có override_reason
  "Đủ điều kiện xem xét" ⟺  không vi phạm gì, xếp hạng theo ΔΠ
```

- **`override_reason` là một trường ĐẦU VÀO**, do người duyệt điền (vd *"mặt bằng đắt địa, mặt tiền QL,
  không có phương án thay thế trong 5 km"*). Máy **không bao giờ tự vượt luật cho chính mình**.
- Mọi lần override được **log** ⇒ sau N hồ sơ ta có **phân bố lý do vượt luật thật** — đó chính là data
  để calibrate ngưỡng, và là thứ BO đang không có.
- Điều này đúng nguyên văn `YÊU-CẦU` #7 (*"hệ thống không tự động đưa ra quyết định thay cho con người"*)
  và đúng chữ **L7** (*"hỗn hợp thì dùng sense của người phê duyệt"*).

**Hệ quả kỹ thuật của việc bỏ tiền lọc:** luật không còn cắt tập khả thi ⇒ bài toán trở lại **ràng buộc
lực lượng thuần** ⇒ **lấy lại bảo hành greedy 1 − 1/e** và gap đo được về **0,00–0,32%** (thay vì
0,00–0,95% khi có R8 cứng). Đây là lợi ích trực tiếp, đo được, của Q1.

### §5.2 · Ràng buộc mềm — ta quyết (A3)

| ID | Nội dung | Vì sao là ràng buộc chứ không phải mục tiêu |
|---|---|---|
| **E1** | **Sàn công bằng ε-constraint** theo vùng (H3 r5 ≈ 252 km², hoặc ranh hành chính khi có) | Bảo hiểm đúng chỗ mô hình lợi nhuận mù (§3.3 mất #2). `2\|R\|` ràng buộc, không cần dữ liệu mới. **Đã chạy, đã có đường cong.** |
| **E2** | Trần số trạm mỗi vùng / mỗi kỳ | Nếu BO nói có; mặc định không áp |

⚠ **Cảnh báo Gazmeh 2024 đã kiểm:** p50 *tăng* (0,699 → 0,725), Gini *giảm* (0,384 → 0,286) — không có
hiệu ứng ngược ở thân phân bố. **Nhưng `p05` đứng yên ở 0,0000 với mọi ε** — 5% vùng tệ nhất không có
ứng viên nào với tới; sàn **không cứu được đuôi thật**. Phải khai khi báo.

### §5.3 · Ứng viên mục tiêu — cần một quyết định, đã có bảng để chọn

`YÊU-CẦU` không nói kiểm soát khoảng cách theo TB / phân vị / xấu nhất. Đây là **chọn giá trị**, và ta
**đã có bảng đánh đổi** — nên đây là *quyết định 30 phút*, không phải *workshop*:

| họ mục tiêu | coverage | mean_d | max_d |
|---|---:|---:|---:|
| MCLP (tối đa phủ) | **0,817** | 3.199 m | 16.631 m |
| p-median (tiện lợi TB) | 0,754 | **2.850 m** | 11.604 m |
| p-center (không bỏ ai) | 0,463 | 3.495 m | **6.709 m** |

*(toy · greenfield · r7 · R=3000 · top-120 localities · p=20 · HN — **exhibit**, không phải khuyến nghị siting)*

Trong mô hình §4.2, `γ` là núm xoay giữa hai cực này. **Đề xuất mặc định:** `γ` đặt sao cho phạt tiếp cận
bằng ~10% biên trung bình; sweep `γ ∈ {0, γ₀, 3γ₀}` và báo cả ba.

### §5.4 · Cờ rà soát — KHÔNG được tự động từ chối/duyệt

Đây là điều kiện tiên quyết của **chuyên gia đánh giá site**, và nó chống đúng kịch bản chết B:

| Cờ | Vì sao không quyết được bằng dữ liệu mở |
|---|---|
| Công suất lưới tại site | EVN không public; `d_substation_m` đo được **AUC 0,499** = vô dụng |
| Số chỗ đỗ dành được cho sạc | không có |
| Diện tích / khoảng trống an toàn / PCCC | không có |
| Xe con vào được qua cổng hợp pháp | cần khảo sát hiện trường |
| Pháp lý mặt bằng, chủ đất, hợp đồng | không có |

⇒ Mọi mục trên ra `Cần review thêm` **kèm câu hỏi cụ thể cho người khảo sát**. **Không bao giờ tự Từ chối
vì thiếu dữ liệu** — từ chối oan đắt hơn review thừa nhiều lần.

### §5.5 · Ràng buộc **tạm hạ cấp**, chờ xác nhận

| ID | Nội dung | Vì sao hạ |
|---|---|---|
| **R8** | 2 km giữa các đề xuất với nhau | **Không có trong A1** (§0.1). Và nó phá bảo hành 1−1/e. Nếu tự đặt: bỏ. |
| **R9** | phân lớp công suất | Không có trong A1; hiện chỉ dùng để phân lớp, chưa ràng buộc |
| **L7** | gate hiệu suất 30% | ⛔ **CHƯA CHẠY ĐƯỢC** — đại lượng chưa khớp (§7.3). Bật là nguy hiểm: sẽ chặn ~3/4 mạng. |

---

## §6 · Phạm vi — bốn scope, cấm trộn

### §6.1 · Bốn scope

| Scope | Là gì | Quyết bởi | Cỡ |
|---|---|---|---|
| **Tính toán** | **LUÔN toàn quốc.** B6 đo: brownfield quốc gia tối ưu chứng minh được trong **3,7–3,8 s** ⇒ thu hẹp để "giải nhanh hơn" là **vô nghĩa**, mà lại tự tạo hiệu ứng biên | kỹ thuật | 268.404 ô |
| **Quyết định** | 1 site (B) hoặc X site (A) | task | 1 → vài trăm |
| **Đánh giá** | **2R** quanh điểm (chặn chứng minh được — §6.2a) | **suy ra**, không chọn | 6 km · p50 **3 trạm** |
| **Nền `S₀`** | **3R**, và không bao giờ cắt theo ranh địa bàn | vật lý | 9 km · p50 7 trạm |
| **Báo cáo** | lát cắt theo địa bàn được giao + **giá của ràng buộc đó** | kế hoạch kinh doanh | tuỳ |
| **Thống kê / hiệu chuẩn** | **giữ ở quốc gia** | thống kê | 19k trạm |

> **Cỡ địa bàn không phải hằng số của dự án.** Nó là **hàm của task**: 2R cho một hồ sơ · tự-do-trải cho
> X nhỏ · phân bổ đa vùng cho X lớn. Xem §6.2.

🔴 **Vì sao scope 4 phải ở quốc gia:** GT quốc gia có **1.271** trạm NEW-HIGH. Ở 1/3 tỉnh còn ~20–50 ⇒ với
n ≈ 25/nhóm, khoảng tin cậy AUC là **±0,18** ⇒ **T1 thành không dùng được**. *Hiệu chuẩn ở quốc gia, quyết
định ở vùng.*

### §6.2 · Địa bàn — **KHÔNG phải tham số đầu vào của mô hình**

> **Đính chính 29/07.** Bản trước của mục này chốt cứng *"1/3 tỉnh = cụm Nam Định–Thái Bình"*. **Sai
> phương pháp:** "1/3 tỉnh" là một **ví dụ về quy mô** do lead nêu, không phải đặc tả; và cỡ địa bàn
> phải **suy ra từ task**, không được áp đặt trước. Đo lại xong thì kết luận còn mạnh hơn thế.

#### (a) Hướng B — cỡ địa bàn **suy ra được bằng lập luận**, không phải chọn

Thêm một trạm tại `q` chỉ đổi phân bổ của những ô cầu nằm trong `R` quanh `q`. Trạm bị mất cầu phải
đang phục vụ một trong các ô đó ⇒ nó nằm trong `R` của ô đó ⇒ **≤ 2R khỏi `q`**. Đây là **chặn chứng
minh được**, không phải quy ước.

| Bán kính | Vai trò | Số trạm DC trong bán kính (`ĐO-ĐƯỢC`, 28.514 ứng viên) |
|---|---|---|
| `R` = 3 km | catchment của chính q | p50 **1** · p90 13 · p99 29 |
| **`2R` = 6 km** | **vành ăn thịt bậc 1 — phạm vi quyết định** | p50 **3** · p90 35 · p99 90 |
| `3R` = 9 km | bậc 2 (cascade khi sức chứa cắn) — **phạm vi nền** | p50 7 · p90 63 · p99 184 |

⇒ **Hướng B: quyết định trên đĩa 2R, dựng nền tới 3R.** Hồ sơ điển hình 3 trạm, đuôi 35 — vừa đúng
cỡ một con người đọc được. Không có tham số nào phải chọn ở đây.

#### (b) Hướng A — **nghiệm không có địa bàn**; địa bàn là **ràng buộc kinh doanh có giá**

Chạy greedy trên **toàn quốc** (28.514 ứng viên = 15.241 xây-mới ∪ 13.273 nâng-cấp AC-only), nền
DC-only `cov@pop` = **0,7192**, rồi **đo độ phân tán của chính nghiệm**:

| X | Δ pp | **số cụm cách nhau ≥ 6 km** | bán kính bao | cụm lớn nhất | % nâng cấp |
|---:|---:|---:|---:|---:|---:|
| 5 | 0,32 | **5** | 672 km | 1 | 0% |
| 20 | 1,07 | **20** | 939 km | 1 | 5% |
| 100 | 3,70 | **97** | 924 km | 3 | 16% |
| 500 | 11,06 | **429** | 892 km | 6 | 29% |

> **Ở mọi X, nghiệm tối ưu là X điểm gần như CÔ LẬP, rải khắp cả nước.** X = 20 cho **20 cụm riêng
> biệt** trải bán kính 939 km; ở X = 500 cụm lớn nhất vẫn chỉ có 6 điểm.
> ⇒ **"Chọn địa bàn" không phải câu hỏi hợp lệ với Hướng A.** Không tồn tại vùng nào chứa nghiệm.

**Và đây là xác nhận độc lập thứ ba cho N1/G3** — lần này bằng hình học: mục tiêu phủ đẩy nghiệm về
những nơi **cô lập**, mà cô lập trên mạng bão hoà nghĩa là **cầu thấp**. `ρ = −0,114` nhìn từ trên bản đồ.

*(Cùng bảng còn cho thấy: dưới mục tiêu **phủ**, nâng cấp gần như không được chọn ở X nhỏ — 0% ở X≤10.
Nâng cấp một trạm AC ở vùng đã phủ cho phủ-biên bằng 0. Dưới mục tiêu **`ΔΠ`** thì ngược lại. ⇒ **Họ
mục tiêu quyết định loại quyết định nào thắng** — thêm một lý do M2/G3 phải đóng trước mọi thứ khác.)*

#### (c) ⇒ Địa bàn là **đầu vào của bài toán kinh doanh**, và ta **định giá** nó

`ĐO-ĐƯỢC` — giá của việc áp đặt địa bàn, X = 20:

| Ràng buộc địa bàn | Δ pp | giữ được | chọn nổi X? |
|---|---:|---:|---|
| **Không (toàn quốc)** | **1,07** | — | 20/20 |
| Bắc Bộ, r = 150 km | 0,92 | **86%** | 20/20 |
| Nam Bộ, r = 150 km | 0,70 | 66% | 20/20 |
| Nam Định–Thái Bình, r = 20 km | 0,40 | **37%** | 20/20 |
| Cần Thơ, r = 20 km | 0,40 | 37% | 20/20 |
| **Hà Nội, r = 20 km** | **0,06** | **5%** | ❌ **14/20** — hết chỗ có giá trị dương |

**Ép về một đĩa 20 km tốn ~63% giá trị đạt được; ép về Hà Nội tốn 95% và không tiêu hết ngân sách.**
Ở quy mô vùng (r ≈ 150 km) giữ được 66–86%.

> **Hệ quả cho deliverable — và nó tốt hơn hẳn bản cũ:** ta **không** đi hỏi *"cho tôi địa bàn nào"*.
> Ta nhận địa bàn từ **kế hoạch kinh doanh** (nó là ràng buộc thật: nhân sự, NPP, quan hệ địa phương),
> rồi **báo cái giá của nó**: *"trong Ω, X trạm mua được Δ_Ω; không ràng buộc thì Δ_free; ràng buộc địa
> bàn đang tốn (Δ_free − Δ_Ω)."* **Định giá cái mandate** — chưa ai làm, và BO đọc được ngay.

#### (d) Bảng tham chiếu quy mô vùng — dùng khi CẦN chọn một vùng để thí điểm

Quét **16 cực dân số** (đĩa 20 km, cách nhau ≥ 35 km), `cov@pop` R = 3 km, nền chỉ-DC, `ĐO-ĐƯỢC` 29/07.
Bảng này **không chốt địa bàn** — nó trả lời *"nếu kế hoạch chỉ định vùng này thì bài toán ở đó là loại gì"*:

| Vùng (đĩa 20 km) | dân | nền DC | **nâng cấp** | **xây mới** | tỷ lệ | DC | AC-only | ứng viên | util DC p50 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Long Xuyên–An Giang | 1.282k | 0,6262 | +14,2 pp | **+33,5 pp** | 0,42 | 45 | 58 | 142 | 0,516 |
| Cần Thơ | 1.383k | 0,6874 | +12,9 | **+27,7** | 0,46 | 53 | 124 | 133 | 1,219 |
| **Nam Định–Thái Bình** | **1.564k** | **0,7175** | **+25,3** | **+16,4** | **1,54** | **89** | **227** | **95** | 0,827 |
| Vinh–Nghệ An | 898k | 0,7998 | +18,5 | +9,8 | 1,89 | 63 | 179 | 43 | 0,821 |
| Hải Dương–Hưng Yên | 1.423k | 0,8034 | +18,7 | +11,9 | 1,57 | 84 | 281 | 83 | 1,241 |
| Thanh Hoá | 1.252k | 0,8578 | +12,5 | +11,4 | 1,09 | 100 | 241 | 88 | 1,189 |
| Đà Nẵng | 1.338k | 0,9514 | +4,2 | +2,1 | 2,05 | 87 | 214 | 72 | 2,046 |
| Hà Nội lõi | 5.357k | **0,9929** | +0,7 | +0,5 | 1,37 | 476 | 1.225 | 196 | 1,253 |
| TP.HCM lõi | 10.609k | **0,9955** | +0,4 | +0,3 | 1,65 | 485 | 793 | 250 | 1,361 |

*(bảng rút gọn 9/16 vùng · `nâng cấp` = phủ tăng nếu nâng **toàn bộ** trạm AC-only trong vùng ·
`xây mới` = phủ tăng nếu mở **toàn bộ** ứng viên · `util` = `occ_dw(720h, không cap)` — trụ bận đồng thời)*

**Cách đọc bảng — ba chế độ, xác định bởi `nền` và `tỷ lệ`:**

| Chế độ | Dấu hiệu | Vùng | Deliverable bắt buộc thu về |
|---|---|---|---|
| **Bão hoà** | nền > 0,95 | Hà Nội · TP.HCM · Biên Hoà · Đà Nẵng | ① **nâng cấp + định cỡ**. Bài toán phủ ở đó **đã chết** (biên +0,3→+2,1 pp) |
| **Nâng cấp thắng** | tỷ lệ > 1 | Nam Định–Thái Bình · Hải Dương–Hưng Yên · Vinh · Thanh Hoá | ① dẫn, ② phụ — nơi đòn bẩy mạnh nhất của ta khớp bài toán |
| **Chọn chỗ thắng** | tỷ lệ < 1, nền < 0,70 | Cần Thơ · Long Xuyên–An Giang | ② dẫn — bài toán siting thuần còn nguyên |

⚠ **Quy mô địa bàn phải khớp task, không khớp một con số cố định** (đính chính ở đầu §6.2):
- **Hướng B, 1 điểm** ⇒ 2R = 6 km. Suy ra được, không chọn.
- **Hướng A, X nhỏ (≤ 20)** ⇒ nghiệm tự do trải **939 km**; nếu kế hoạch buộc một vùng thì báo giá của
  ràng buộc đó (§6.2c).
- **Hướng A, X lớn (≥ 100)** ⇒ nghiệm chạm 97–429 cụm; đây là bài toán **phân bổ ngân sách qua nhiều
  vùng**, đúng dạng *"per-đơn-vị exact + DP trên các đường cong biên `f*(p)`"* — **exact-tương-đương**
  khi các đơn vị cách nhau > 2R, không mất chính xác.

**Không chốt địa bàn trong đề bài này.** Nó đến từ kế hoạch kinh doanh; nghĩa vụ của mô hình là chạy
đúng với địa bàn được giao **và định giá ràng buộc đó**.

⚠ **Chi phí luật KHÔNG chuyển từ quốc gia sang vùng.** Đo quốc gia: bật đủ luật tốn **0,000 pp** ở p ≤ 100.
Nhưng tỷ lệ ứng viên sống sót L5 là **HN 51,45%** · HCM 68,35% · ĐN 84,54% · QN 87,01%; và mật độ DC Hà Nội
(0,6525/km²) **vượt 2,3×** chặn đóng gói của luật 2 km (0,2887/km²). ⇒ **Phải đo lại tại đúng địa bàn.**

### §6.3 · Khoảng cách: Euclid → **OSRM travel-time** (`A3`)

Ở quốc gia đây là job 8 h nên bị hoãn, và `results-pilot-cities` gọi nó là *"giới hạn nghiêm trọng nhất"*.
Ở 1/3 tỉnh: vài trăm × vài nghìn OD = **một request bảng, tính bằng phút**. ⇒ **Gỡ được. Bắt buộc gỡ.**
Đĩa Euclid băng qua sông ở HN/HCM làm sai catchment một cách hệ thống.

### §6.4 · Đơn vị ứng viên — vành, không phải toạ độ

`ĐO-ĐƯỢC`: lệch điểm-thật ↔ tâm-ô p50 = **353 m** = 1,8× ngưỡng bảo hộ 200 m.
⇒ **Hướng A trả "vành tìm kiếm ~400 m + hồ sơ", không trả một toạ độ giả-chính-xác.**
Ở scale 1/3 tỉnh, ứng viên T4 tổng hợp (ô buildable không anchor, mặt bằng chưa xác định) **nên được thay
bằng mặt bằng thật liệt kê được** — đây là nâng cấp mà scope nhỏ mua cho ta.

---

## §7 · Ba thứ BO không cấp — và cách ta dựng lại từ nguồn công khai

Mentor xác nhận 29/07: **không có quyền truy cập dữ liệu công ty.** Ba mục dưới đây thay thế đúng ba
blocker, và cả ba **đã nằm trong tay**.

### §7.1 · L1 (depot) → tái dựng từ telemetry + registry

```
S₀ = có ≥1 mẫu telemetry trong cửa sổ 720h                    ≈ "ngày hoạt động ≠ null"
   ∧ charging_status ∉ {INACTIVE, OUTOFSERVICE, UNAVAILABLE}  ≈ blockstatus
   ∧ access = PUBLIC ∧ is_primary ∧ toạ độ sạch
   ∧ có ≥1 trụ DC                                             ← L2
```
Telemetry 30 ngày là **bằng chứng vận hành trực tiếp**, mạnh hơn mọi cột status.
`ĐO-ĐƯỢC` cửa sổ mới: **19.426 trạm**, 2026-06-29 → 07-29, span p50 **29,95 ngày** (cũ: 6,95).

⚠ **Phải rebuild trước:** fix dedup 29/07 trả **+314 trạm** về cung (primary 19.178 → **19.492**).
Nền `covered0 = 18.839` đã **cũ**; mọi số neo phải tính lại.

### §7.2 · Sổ pipeline (`ask #3`, đang chạy `[mô phỏng]`) → registry `UNAVAILABLE`

Registry `vinfastauto.com`: `charging_status = UNAVAILABLE` = **"đang chuẩn bị mở"**, vắng mặt hoàn toàn
khỏi bản đồ evcs.vn. `ĐO-ĐƯỢC`: **3.466 trạm ô tô** ở đúng trạng thái đó.

⇒ Đó là **sổ "đã duyệt / đang triển khai", công khai** ⇒ gate trùng-pipeline gỡ được nhãn `[mô phỏng]`.
Và nó cho **tập ground-truth thứ hai mang tính dự báo thật** (điểm operator đã quyết xây nhưng chưa xây) —
sạch hơn tập đã-xây vì không dính survivorship.
🔬 **Phải kiểm chứng trước khi dùng:** diff registry với `generation = 16` (frozen 20/07), đếm tỷ lệ
`UNAVAILABLE → ACTIVE`. Nếu tỷ lệ ≈ 0 thì cách đọc sai và mục này bị huỷ.
⏸ **HOÃN (Q9):** lead đang củng cố dataset ⇒ chưa pull registry mới. Cho tới khi kiểm chứng xong,
`§7.2` giữ nhãn **`GIẢ-ĐỊNH-HỞ`** và **không được** dùng trong bất kỳ khuyến nghị nào (§0 quy tắc A4).

### §7.3 · L3/L7 "hiệu suất" → **núm xoay phân vị**, không phải ngưỡng 30%

Ba đại lượng khác nhau đang cùng tên *"hiệu suất"*:

| | là gì | số |
|---|---|---|
| `occ_mean_dw` | **số trụ bận đồng thời** (duration-weighted) | trung vị 0,145; max 59,2 — **không phải tỷ lệ** |
| `occ_mean_dw / n_ports` | tỷ lệ **thời gian** chiếm dụng | DC trung vị **16,9%**; **25,2%** vượt 30% |
| kWh thực / kWh danh định | đại lượng **của BO** (L3) | **luôn ≤** cái trên (xe sạc taper) |

Áp 30% lên đại lượng của ta ⇒ **74,8% trạm DC nằm dưới** ⇒ L7 sẽ chặn quanh ba phần tư mạng.

> **`TA-QUYẾT`:** không ánh xạ sang 30%. Báo **phân vị trong cùng lớp** (DC/AC × đô thị/xã), ngưỡng là
> **một tham số phân vị cấu hình được**. Khi BO cho biết 30% ứng với phân vị nào, gate khớp ngay bằng
> một tham số — **không sửa mô hình.**

Và: giữ L7 là **cờ mềm có lý do**, không phải từ chối cứng — vì **nội sinh làm nó tự khoá**:
ρ(cầu, occupancy) = +0,28 → **+0,06–0,13** khi khống chế số trạm trong ô ⇒ nơi thiếu trạm thì hiệu suất
trạm cũ thấp *vì lý do khác*, và luật sẽ chặn **đúng chỗ cần thêm**.

### §7.4 · 🔴 Bằng chứng đi ngược giả định nền của L5/L6

L5/L6 đứng trên giả định *"trạm gần nhau ăn thịt nhau"*. `ĐO-ĐƯỢC` (n = 4.475 trạm DC):

| | ρ với `util` |
|---:|---:|
| số trạm DC khác trong 2 km | **+0,1861** |
| khoảng cách tới trạm DC gần nhất | **−0,1713** |

**Mật độ là dấu hiệu của cầu, không phải thứ rút cầu của nhau. Ở mật độ hiện tại, tụ hội thắng ăn thịt.**
⚠ Nội sinh nặng (đồng vị trí *vì* cầu cao) ⇒ phát biểu đúng là **kết quả âm**: *"không tìm thấy bằng chứng
ăn thịt ở mật độ hiện tại"*, **không** phải nhân quả. Đóng bằng COD (§7.2) ⇒ quasi-experiment trước/sau.

---

### §7.5 · 🔑 S8 đã có câu trả lời — và nó thành **trục kịch bản**, không còn là giả định hở

`YÊU-CẦU`/lead 29/07: **mạng V-GREEN hiện chỉ phục vụ VinFast; có kế hoạch mở cho các hãng khác theo
yêu cầu Chính phủ.**

Suốt hai sprint đây là *giả định hở lớn nhất dự án* (băng **0,776**: HN `cov_open` 0,925 ↔ `cov_neutral`
**0,149**). Giờ nó đảo vai — từ **caveat** thành **deliverable**:

| Kịch bản | Cầu tiếp cận được | Trạng thái |
|---|---|---|
| **K1 — độc quyền (HÔM NAY)** | chỉ chủ xe VinFast | ✅ đây là nền để hiệu chuẩn: **toàn bộ telemetry ta có là cầu K1** |
| **K2 — mở mạng (KẾ HOẠCH)** | mọi chủ xe điện | cầu mỗi trạm **tăng**; sức chứa **cắn sớm hơn** |

**Ba hệ quả bắt buộc:**

1. **Con số phủ báo ra ngoài phải nói rõ mẫu số.** *"Phủ 92,5% dân Hà Nội"* là đúng **cho chủ xe VinFast**.
   Với "mọi chủ xe điện" con số hôm nay gần **0,149**. Đây là bất biến báo cáo, không phải chi tiết.
2. **Mọi khuyến nghị phải bền qua CẢ HAI kịch bản** — dùng đúng máy robustness đã có (sweep kịch bản,
   báo tập bền vững). Khuyến nghị chỉ đúng ở một kịch bản thì **không được phát**.
3. **Đây là lập luận mạnh nhất cho ①.** Dưới K2 cầu tăng nhưng **vị trí không đổi** ⇒ ràng buộc chuyển
   từ *chỗ nào* sang *bao nhiêu trụ*. ⇒ **Nâng cấp/định cỡ là quyết định KHÔNG-HỐI-TIẾC dưới cả K1 lẫn
   K2**; mở mới thì không (dưới K2 thì cầu dồn về trạm sẵn có trước). Đây là bằng chứng độc lập, đến từ
   chính sách chứ không từ dữ liệu, và nó **trùng kết luận** với §2.1.

---

## §8 · Sổ giả định kinh tế — điều kiện để bất kỳ khuyến nghị nào được phát

### §8.1 · Lập luận làm cho toàn bộ tầng assumption đứng được

> **Tham số ĐỒNG NHẤT giữa các site triệt tiêu khỏi xếp hạng. Chỉ tham số BIẾN THIÊN THEO SITE mới đổi
> quyết định.**

⇒ Ta bán phát biểu **loại 2** (*"A đáng ưu tiên hơn B"* — kiểm được bằng lịch sử), **không** bán loại 3
(*"trạm này đạt X kWh/tháng"* — cấm, bất biến **B4**).

### §8.2 · Sổ (mỗi dòng: giá trị · căn cứ · khoảng · thứ hạng có đảo trong khoảng không)

| # | Tham số | Biến thiên theo site? | Ảnh hưởng **xếp hạng** | Nguồn dự kiến |
|---|---|---|---|---|
| A1 | giá bán điện/kWh cho user | ❌ đồng nhất | **0** — chỉ đổi payback tuyệt đối | công bố V-GREEN |
| A2 | giá **mua** điện | 🟡 theo cấp áp/khung giờ | nhỏ | QĐ 14/2025 + QĐ 1279 — **đã có `opex_electricity.py`** |
| A3 | hệ số taper τ | ❌ theo lớp trụ | **0** trong lớp | văn liệu sạc DC |
| A4 | thời gian khấu hao | ❌ | **0** | `TA-QUYẾT` |
| **A5** | **CapEx theo `capex_class`** | ✅ | **CÓ** | vcharge.vn — dùng **khoảng**, không dùng điểm |
| **A6** | **thuê mặt bằng** | ✅ mạnh | **CÓ** | tin BĐS theo khu (batdongsan/chotot) |
| A7 | O&M phi điện | 🟡 | nhỏ | định mức ngành |
| **A8** | **`utilisation ceiling`** cho `cap` | ❌ theo lớp | **0** trong lớp, nhưng đổi mức bão hoà | `TA-QUYẾT` + telemetry |

**Nghĩa vụ:** mọi khuyến nghị chạy sensitivity qua khoảng của **A5, A6** (và A2). **Nếu thứ hạng đảo trong
khoảng ⇒ khuyến nghị đó KHÔNG được phát.**

### §8.3 · 🔴 Nợ mới `ĐO-ĐƯỢC` 29/07 — chảy thẳng vào doanh thu

Chính sách F19 (*duration-weighted, cap 30′/khoảng*) chỉnh cho tầng **168h sự-kiện**. Tầng **720h là lưới
5′ phát-khi-đổi-giá-trị** (gap p90 45′, có gap tới 13 ngày). Đo trên 1.500 trạm/tầng:

| | 168h sự-kiện | 720h lưới-5′ |
|---|---:|---:|
| % thời lượng bị cap cắt | p50 **43,2%** · p90 77,7% | p50 **44,9%** · p90 78,4% |
| `occ` trung vị cohort — cap / không-cap | 0,1403 / **0,1725** | 0,1419 / **0,1694** |
| tỷ số cap/không-cap mỗi trạm | p50 0,999 · **p90 1,203** | p50 0,977 · **p90 1,158** |

Cap đang cắt **~45% tổng thời lượng**; mức cohort lệch **~19%**; thổi phồng **+16–20%** cho một phần mười
trạm. Với mô hình phủ: vô hại. **Với mô hình doanh thu: 19% throughput = 19% doanh thu = 19% payback.**
⇒ **Chính sách cap phải suy lại riêng cho tầng 720h và pre-register như tham số kinh tế.**
⇒ Hai tầng timestamp chồng khớp ~0 (2/483.808) ⇒ **cấm union mù**.

---

## §9 · "Đúng" nghĩa là gì — định nghĩa trước khi xây

Nhóm trước chết vì nhãn *"model không chính xác"* dán lên xác chết. Mục này tồn tại để nhãn đó không dán
được nữa.

### §9.1 · Thang phát biểu — dồn output vào loại 1–2, **TỪ CHỐI** loại 3

| Loại | Ví dụ | Kiểm được? |
|---|---|---|
| **1 · Facts** | "6 trạm trong 1 km", "48.210 dân trong 2 km", "3 trạm lân cận ở phân vị hiệu suất < 25" | ✅ ngay — sai là bug data, sửa được |
| **2 · Xếp hạng tương đối** | "A đáng ưu tiên hơn B", "thuộc top 12% cầu tiếp cận được" | ✅ bằng lịch sử |
| **3 · Dự đoán tuyệt đối** | "trạm này đạt 42 phiên/ngày", "doanh thu X đồng" | ❌ — **nhóm trước nhiều khả năng chết ở đây** |

### §9.2 · Gate — điều kiện để một hàm mục tiêu được phép xếp hạng

| Gate | Câu hỏi | Ngưỡng | Trạng thái |
|---|---|---|---|
| **G0** | Fact có sai không? | **0 lỗi** trên 20 hồ sơ spot-check, oracle độc lập | ✅ **PASS** (B8) |
| **G3** | **Hàm mục tiêu có xếp đúng thứ tự các vị trí ĐÃ xây không?** | ρ(mục tiêu, util) **> 0** ∧ tỷ số ngũ phân vị **> 1,0** | 🔴 MCLP **FAIL** (−0,114 / 0,76×) — `ΔΠ` **phải chạy lại gate này trước khi dùng** |
| **G2** | Proxy cầu có dự đoán được vị trí operator chọn không? | AUC ≥ 0,70 | 🔴 **FAIL** (0,452) — và **trần đo được chỉ 0,698 ± 0,039** |
| **G4** | Ràng buộc có còn phân biệt không? | không được 95% hồ sơ ra cùng một tier | ✅ đo 400 candidate: 72/28 |

> **G3 là gate quan trọng nhất và nó rẻ nhất.** *Không hàm mục tiêu nào được xếp hạng vị trí CHƯA xây
> trước khi chứng minh nó xếp đúng thứ tự các vị trí ĐÃ xây.*

### §9.3 · Thang kiểm chứng

| Tầng | Kiểm gì | Cần gì | Khi nào | Ngưỡng |
|---|---|---|---|---|
| **T0** | Facts không sai | có sẵn | ✅ xong | 0 lỗi / 20 hồ sơ |
| **T1** | Máy có nhận ra chỗ operator đã xây? | có sẵn (1.271 điểm) | ✅ chạy, FAIL, cơ chế đã hiểu | AUC ≥ 0,70 — **trần thật 0,698** ⇒ **không có biên an toàn** |
| **T1′** | Máy có nhận ra chỗ operator **SẮP** xây? | **§7.2** — 3.466 UNAVAILABLE | 🆕 **mở được ngay** | đề xuất AUC ≥ 0,65 |
| **T2** | Khớp quyết định người | hồ sơ lịch sử BO | ❌ **không có quyền** | — |
| **T3** | Điểm cao có chạy tốt thật? | COD + telemetry dài | 🟡 **§7.2 mở được tiến về phía trước** | ρ hạng > 0 |

⚠ **Hai caveat phải nói trước:** retrodiction đo *"máy giống hành vi operator"*, **không** đo *"operator
chọn đúng"*. Và bài toán là **Positive-Unlabeled** — ta thấy trạm đã xây, **không bao giờ thấy hồ sơ bị
từ chối** ⇒ mọi AUC trên control ngẫu nhiên **không nói gì** về hiệu năng trên hồ sơ thật.

### §9.4 · Ba lỗ hổng quy trình đã lộ — sửa trong đề bài này

1. **Sàng tín hiệu (EDA) đi TRƯỚC pre-reg.** v0 đóng băng trục điểm rồi mới đo → **cả hai trục ngược dấu**.
   Pre-reg chống p-hacking khi *kiểm định*, **không** được đóng băng giai đoạn *khám phá*.
2. **Pre-reg bắt buộc có mục "Tài sản tái dùng"** — liệt kê module/layer đã tồn tại + **lý do nếu không dùng**.
3. **Vòng adversarial bắt buộc có một refuter công kích SPEC**, không chỉ code. 21 finding CONFIRMED bắt
   sạch lỗi hiện thực; không ai được giao câu *"trục này đo sai thứ gì?"*.

---

## §10 · Hợp đồng output

### §10.1 · Hướng B — hồ sơ thẩm định một điểm

Đúng `YÊU-CẦU` #6. **Chỉ cần `lat/lng` là chấm được**; mọi trường khác là bonus, thiếu → `Cần review`,
**không bao giờ tự Từ chối vì thiếu data**.

```json
{
  "tier": "Đồng ý phê duyệt | Cần review thêm | Từ chối phê duyệt",
  "score": {"value": 0-100, "basis": "phân vị trong lớp tham chiếu", "label": "v0 — chưa calibrate"},
  "reasons": [{"code": "L5_XA_2KM", "severity": "hard|soft|info", "evidence": "trạm DC gần nhất 1.430 m"}],
  "indicators": {
    "facts":        {"n_within_1km": 3, "n_within_r": 11, "connectors_within_r": 44,
                     "d_nearest_m": 1430, "pop_catchment": 48210},
    "network":      {"delta_demand_captured_pct": 2.1,
                     "cannibalization": [{"station": "…", "delta_pct": -3.4}]},
    "neighbours":   {"util_percentile_in_class": [62, 18, 41], "n_below_p25": 1},
    "pipeline":     {"approved_within_2km": 1, "source": "registry UNAVAILABLE"},
    "feasibility":  {"REVIEW": ["công suất lưới", "số chỗ đỗ", "lối vào hợp pháp"]}
  },
  "data_version": "…", "model_version": "…"
}
```

Tích hợp: **API-first** (`YÊU-CẦU` #8) + **batch CSV** (workflow thật của BO là Excel-ish) + 1 trang map
tĩnh để demo. **Không xây UI trước khi BO chốt định hướng.**

### §10.2 · Hướng A — kế hoạch X trạm

- **Vành tìm kiếm ~400 m** (§6.4) + hồ sơ mỗi vành, **không** phải toạ độ đơn;
- đường cong `X ↦ ΔΠ` và `X ↦ cầu phục vụ thêm`, **hai biến thể ngân sách** (đếm / tiền);
- **chứng chỉ tối ưu** (`mip_gap`) + biến thể có/không sàn công bằng;
- GeoJSON để Giang tích hợp map.

### §10.3 · Ba tier — giữ hay bỏ?

`YÊU-CẦU` #6 nêu rõ **3 tier có "Từ chối phê duyệt"**. Quyết định 28/07 bỏ tier đó là đúng khi từ chối dựa
trên **điểm số mô hình** (không kiểm toán được). Nhưng **L5/L7 là luật do BO ban hành**: xác định, nêu
được lý do bằng số đo, đảo ngược ngay khi luật đổi.

> **`TA-QUYẾT`:** giữ *"Từ chối phê duyệt"* **CHỈ KHI** có một điều luật A1 cụ thể bị vi phạm, kèm số đo.
> **Không bao giờ** từ chối vì điểm số thấp hoặc vì thiếu dữ liệu. — *cần mentor xác nhận.*

---

## §11 · Ngoài phạm vi — khai rõ để không ai tưởng bị bỏ quên

| Hạng mục | Lý do |
|---|---|
| Dự báo kWh/doanh thu tuyệt đối của trạm chưa xây | Bất biến **B4**; trần R² của **toàn bộ** biến hiện có = **0,244** |
| Corridor liên tỉnh (FRLM) | Lớp bài toán riêng; chặn bởi dữ liệu OD (không public ở VN) |
| Xe 2 bánh / battery-swap | Ngoài phạm vi ô tô công cộng |
| Tối ưu lưới điện (power flow) | EVN không public feeder capacity; `d_substation_m` đo **AUC 0,499** = vô dụng |
| Metaheuristic (GA/PSO) | Gap greedy↔exact đã **0,00–0,95%**; và MILP **không bao giờ nộp nghiệm phạm ràng buộc cứng**, GA xử ràng buộc bằng điểm phạt ⇒ có thể trả nghiệm **vi phạm quy định** trước mặt người duyệt |
| RBAC / auth / deploy / CI-CD | M2 — hoãn tới khi BO trả lời volume |
| PostGIS | Nợ đã khai; Parquet/DuckDB là chuẩn bàn giao |

---

## §12 · Rủi ro & nợ đã khai

| # | Rủi ro | Mức | Giảm nhẹ |
|---|---|---|---|
| **1** | **Nhãn hành chính chỉ đúng 72,9%** (đoán bừa đã 58,4%) mà L5/L6 gate quyết định phê duyệt đứng trên nó | 🔴 | Ở 1/3 tỉnh: **tra tay** vài trăm điểm. Hoặc xin trường địa bàn đi kèm mỗi đề xuất. |
| **2** | **"Thị trấn"/"Thị xã" không nằm trong điều luật nào** — 12,6% trạm rơi vào khoảng trống | 🟠 | Mặc định xếp về **đô thị**; dán nhãn GIẢ ĐỊNH; hỏi mentor |
| **3** | **Nội sinh cầu** — ρ 0,28 → 0,06–0,13 | 🔴 | Cấm claim loại 3; L7 làm **cờ mềm**; đóng bằng COD (§7.2) |
| **4** | **Positive-Unlabeled** — không có hồ sơ bị từ chối | 🔴 | Khai trong mọi báo cáo AUC; T1′ (§7.2) là bù đắp tốt nhất có được |
| **5** | **`base(capex_class)` chưa có số** ⇒ không định giá được nâng cấp AC→DC (86% hiệu quả phủ của xây mới) lẫn việc nới tập ứng viên | 🟠 | §8 A5 dùng **khoảng** từ vcharge.vn + sensitivity |
| **6** | **Chính sách cap 720h** lệch 19% throughput | 🟠 | §8.3 — suy lại + pre-register |
| **7** | **`covered0 = 18.839` đã cũ** (+314 trạm sau fix dedup) | 🟠 | Rebuild trước mọi số mới |
| **8** | ~~S8 — mạng V-GREEN mở tới đâu~~ → **ĐÃ TRẢ LỜI (Q6)**: hôm nay **độc quyền VinFast**, kế hoạch mở | 🟢 **đóng** | §7.5 — thành trục kịch bản K1/K2; mọi số phủ **bắt buộc nói rõ mẫu số** |
| **11** | **Nhãn kịch bản dễ bị đọc nhầm**: `cov@pop` hiện tại là *phủ cho chủ xe VinFast*, không phải *phủ cho mọi chủ xe điện* | 🔴 **MỚI** | Bất biến báo cáo: cấm chữ "coverage" trần **và** cấm bỏ trống mẫu số nhóm-xe |
| **9** | Toạ độ 20 mốc spot-check là **xấp xỉ** (lấy từ tên địa danh) | 🟠 | Người thuộc địa bàn chốt lại **trước demo** — điều kiện, không phải nice-to-have |
| **10** | ToS nguồn `evcs.vn` | 🔴 | Mọi thứ khách/NPP nhìn = **gold-only**; assert firewall trước mỗi export |

---

## §13 · Tiêu chí nghiệm thu

| Mốc | Đạt khi |
|---|---|
| **M1 — nền** | `covered0` rebuild (+314) · chính sách cap 720h pre-register · §7.2 đã kiểm chứng bằng diff registry |
| **M2 — mục tiêu hợp lệ** | **`ΔΠ` qua gate G3**: ρ > 0 ∧ tỷ số ngũ phân vị > 1,0 trên trạm đã xây. **Không qua ⇒ không được dùng để xếp hạng bất cứ thứ gì.** |
| **M3 — Hướng B** | Chấm 1 điểm bất kỳ trong địa bàn < 1 s, có `reasons[]` đọc được · **0 lỗi fact** trên 20 hồ sơ · mọi mục §5.4 ra `Cần review` kèm câu hỏi khảo sát |
| **M4 — Hướng A** | Kế hoạch X trạm có **chứng chỉ tối ưu** · đường cong `X ↦ ΔΠ` · biến thể có/không sàn công bằng · **bất biến B1 có test** |
| **M5 — trung thực** | Sổ giả định §8 đầy đủ · sensitivity A5/A6 chạy · mọi khuyến nghị có thứ hạng **không đảo** trong khoảng · nợ §12 khai đủ |

> **DoD cũ *"coverage % theo từng mức ngân sách"* được thay bằng M2–M4.** Lý do: coverage không có trong
> `YÊU-CẦU`, và G3 chứng minh nó xếp ngược thứ tự thực tế. Đây là thay đổi **cần mentor xác nhận** — kèm
> ba con số N1/N2/N3 làm căn cứ.

---

## §14 · Quyết định đã chốt 2026-07-29 (lead)

| # | Câu hỏi | **Chốt** | Hệ quả trong đề bài |
|---|---|---|---|
| Q1 | R8/R9 có phải luật BO? | **Không cứng — chỉ "nên như vậy", linh hoạt khi vị trí thật sự đắt địa** | §5.1/§5.5 — luật khoảng cách thành **mềm + cơ chế vượt luật**; **lấy lại bảo hành 1−1/e** |
| Q2 | Bỏ DoD coverage? | **Mentor chưa đề cập rõ ⇒ chọn cách đọc có lợi cho bài toán** | §13 — thay bằng M2–M5. Guardrail ở §14.1 |
| Q3 | Giữ tier "Từ chối phê duyệt"? | **GIỮ** | §10.3 + §5.1a cơ chế vượt luật |
| Q4 | Địa bàn | **Giao cho phân tích quyết định** ⇒ §6.2: **cụm Nam Định–Thái Bình** (≈32% tỉnh Ninh Bình) | §6.2 |
| Q5 | "Thị trấn" thuộc bên nào | **Đô thị** — vào danh sách được mở gần | §5.1 — cùng nhóm Quận/Phường/Thị xã (L4) |
| Q6 | S8 — mạng V-GREEN mở tới đâu | **Hiện chỉ phục vụ VinFast; có kế hoạch mở cho hãng khác theo yêu cầu Chính phủ** | §7.5 — thành **trục kịch bản**, không còn là giả định hở |
| Q7 | Họ mục tiêu (TB / phân vị / xấu nhất) | **Không có yêu cầu ⇒ ta quyết** | §5.3 — lợi nhuận + phạt tiếp cận nhẹ `γ` + sàn ε; sweep `γ ∈ {0, γ₀, 3γ₀}` |
| Q8 | Phạm vi quyết định | **Cả ba: đóng cửa · mở mới · nâng cấp — nhưng chọn cái ta mạnh nhất** | §2.1 — ba bậc bằng chứng, ba hợp đồng output |
| Q9 | Crawl thêm dữ liệu? | **Chưa — dùng lại bundle hiện có**; lead đang củng cố dataset, review lại sau | §7.2 kiểm chứng pipeline **hoãn** tới sau khi dataset ổn định |

### §14.1 · 🔒 Guardrail cho nguyên tắc *"chưa rõ ⇒ chọn cách có lợi"*

Nguyên tắc này **được phép** áp cho **phạm vi và định nghĩa** (địa bàn, đơn vị, họ mục tiêu, cách đọc
điều luật mơ hồ). Nó **BỊ CẤM** áp cho **bằng chứng** — chọn trục/feature/ngưỡng vì "nghe hợp lý" chính
là cơ chế đã làm v0 fail (cả hai trục ra **ngược dấu**: 0,436 và 0,437). Ranh giới:

> Có lợi khi **chọn hỏi câu nào** — không có lợi khi **đọc câu trả lời**.

Mọi lựa chọn ảnh hưởng tới số phải qua §9.2 gate, không qua nguyên tắc này.

---

*Viết 2026-07-29. Mọi số `ĐO-ĐƯỢC` trong file này truy được về một doc kết quả đã qua adversarial-verify
hoặc một lần đo ghi ngày. Mọi dòng `TA-QUYẾT` nằm trong §8 hoặc §14. Không dòng nào là `GIẢ-ĐỊNH-HỞ`.*
