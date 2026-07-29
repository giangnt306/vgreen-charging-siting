# REPORT: PHÂN TÍCH BÀI TOÁN TỐI ƯU VỊ TRÍ TRẠM SẠC VGREEN

1. Mục tiêu

**Góc nhìn doanh nghiệp (VGreen):**

- Tối đa hóa doanh thu (kWh tiêu thụ)
- Tối đa hóa hiệu suất sử dụng súng sạc (utilization rate)
- Tối ưu chi phí hạ tầng (CapEx lắp đặt + OpEx vận hành)
- Tối đa hóa ROI và rút ngắn thời gian hoàn vốn (payback period)

**Góc nhìn người dùng (VinFast EV Users):**

- Giảm thiểu thời gian chờ đợi (queuing time)
- Giảm quãng đường di chuyển đến trạm sạc (detour distance)
- Tránh tình trạng trạm "quá tải"
- Đảm bảo độ phủ (coverage) — luôn có trạm khả dụng trong bán kính chấp nhận được

**Góc nhìn Nhà nước / Chính quyền địa phương:**

- **Giảm ùn tắc giao thông:** bố trí trạm tránh gây tụ tập/xếp hàng tràn ra lòng đường tại điểm sạc; ưu tiên vị trí có bãi đỗ đủ lớn; khuyến khích sạc lệch giờ cao điểm.
- **Giảm phát thải & ô nhiễm không khí:** thúc đẩy chuyển đổi sang xe điện, phù hợp cam kết Net Zero 2050 và Quyết định 876/QĐ-TTg (chuyển đổi năng lượng xanh ngành GTVT).
- **Phủ hạ tầng công bằng giữa các khu vực:** tránh chỉ tập trung đô thị lớn; đảm bảo vùng ven, nông thôn, tuyến quốc lộ cũng có độ phủ tối thiểu.
- **Ổn định lưới điện & an toàn:** không gây quá tải cục bộ lưới điện; tuân thủ quy hoạch đô thị và an toàn PCCC của trạm sạc.

> **Lưu ý bản chất bài toán:** Ba nhóm mục tiêu này **xung đột lẫn nhau (trade-off)**. Ví dụ: giảm thời gian chờ của user cần dư thừa công suất → giảm utilization rate của doanh nghiệp; hoặc mục tiêu "phủ công bằng" của nhà nước (đặt trạm ở vùng thưa dân) lại làm giảm ROI của doanh nghiệp. Đây là bài toán **multi-objective optimization** ba bên, cần định nghĩa hàm mục tiêu có trọng số hoặc ràng buộc (ví dụ: tối đa doanh thu với ràng buộc thời gian chờ TB < X phút **và** độ phủ tối thiểu ≥ Y% dân số mỗi khu vực). Lợi ích nhà nước một phần có thể chuyển thành **ràng buộc cứng** (quy hoạch, an toàn, phủ tối thiểu) thay vì chỉ là mục tiêu mềm.

---

## 2. Phân tích các bộ dữ liệu

Chia làm 2 nhóm chính. Nguyên tắc phân loại (đã cập nhật **sau khi công ty xác nhận không cung cấp dữ liệu** — chỉ còn nguồn công khai / crawl / khảo sát):

- **Nhóm 1 — Có sẵn:** **có nguồn công khai** chất lượng, đầy đủ, rõ ràng, phủ khu vực Việt Nam (không phụ thuộc công ty).
- **Nhóm 2 — Không có sẵn / phải tự thu thập:** không có nguồn công khai đủ tốt → phải crawl, khảo sát thị trường, ước lượng từ proxy, hoặc đặt giả định. Mỗi bộ được đánh giá **cách thu thập**, **tính khả thi** và **độ chính xác**.

### Nhóm 1: Dữ liệu có nguồn công khai

| # | Dữ liệu                                            | Nội dung / vai trò                                                                                                | Nguồn                                                                                                                                                              | Ghi chú                                                                            |
| - | ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| 1 | **Chi phí hạ tầng — CapEx**                | Chi phí thiết bị (trụ sạc AC/DC, bộ điều khiển, phần mềm), thi công, đấu nối lưới, trạm biến áp | **Đổi nguồn:**  vcharge.vn                                                                                                                                | Độ tin cậy hạ một bậc → dùng khoảng (min–max) thay vì con số cố định |
| 2 | **Chi phí vận hành — OpEx (tiền điện)** | Giá điện đầu vào theo khung giờ & cấp điện áp cho trạm sạc                                             | **Nguồn công khai VN:** biểu giá điện riêng cho trạm sạc theo QĐ 14/2025/QĐ-TTg + QĐ 1279/QĐ-BCT (~1.565–4.298 đ/kWh tùy khung giờ/cấp áp) | Cấu phần OpEx lớn nhất, nguồn pháp lý rõ ràng → tin cậy cao              |
| 3 | **Tọa độ trạms**                           | Xác định khoảng cách địa lý, độ phủ, tránh chồng lấn                                                  | **Đổi nguồn:** crawl evcs.vn                                                                                                                               | Lat/long crawl được cho phần lớn trạm công khai; có thể thiếu trạm mới  |
| 4 | **Cấu hình trạm**                           | Số lượng súng sạc, loại AC/DC, công suất (30/60/150/250 kW)                                                 | **Đổi nguồn:** crawl evcs.vn                                                                                                                               |                                                                                     |
| 5 | **POI & Trắc địa**                          | Trạm xăng, cao tốc/quốc lộ, khu đô thị, TTTM, chung cư, bãi đỗ                                          | **Nguồn công khai VN:** OpenStreetMap (Geofabrik `vietnam-latest`, cập nhật hàng ngày), HDX/HOT export theo tag                                       | Chất lượng đủ tốt cho MVP                                                     |
| 6 | **Mật độ dân cư**                         | Grid mật độ dân số ~100m–1km                                                                                  | **Nguồn công khai VN:** WorldPop (Vietnam, 2020, CC-BY), Tổng cục Thống kê                                                                              | Đầu vào lõi cho Demand Map                                                      |
| 7 | **Log vận hành VGreen**                      | Bottleneck / underutilized, giờ cao điểm thực                                                                  | **Đối nguồn:** crawl evcs.vn                                                                                                                              |                                                                                     |

### Nhóm 2: Dữ liệu không có sẵn — cách thu thập, khả thi & độ chính xác

Dùng để hoàn thiện **"Bản đồ nhu cầu" (Demand Map)** và các ràng buộc thực tế. Vì công ty không cung cấp gì, mọi bộ đều phải **tự thu thập**. Mỗi bộ được đánh giá: **cách thu thập đề xuất**, **tính khả thi** (Cao/TB/Thấp), **độ chính xác** (Cao/TB/Thấp), và **ưu tiên** — **(A)** bắt buộc cho MVP, **(B)** tăng độ chính xác, **(C)** nice-to-have.

| # | Dữ liệu                                    | Vai trò                                                        | Cách thu thập đề xuất (khi không có dữ liệu công ty)                                                                                                                                                                                 | Khả thi  | Độ chính xác                               | Ưu tiên |
| - | -------------------------------------------- | --------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- | ---------------------------------------------- | --------- |
| 1 | **Di chuyển (GPS/Traffic)**           | Lộ trình phổ biến, điểm dừng đỗ lâu                   | Traffic API công khai/thương mại:**Mapbox / HERE / TomTom** (trả phí, có free tier); **Google Roads/Distance Matrix**; định tuyến trên **OSM (OSRM/Overpass)**; xin hợp tác Grab/Be. Uber Movement đã ngừng  | TB        | TB                                             | A         |
| 3 | **Lưới điện (Grid constraints)**   | Khả năng cấp điện trạm biến áp cho DC nhanh             | EVN**không public**. Proxy: vị trí trạm biến áp/đường dây từ **OSM (`power=substation`, `power=line`)**; ước lượng công suất theo cấp điện áp; xác minh mẫu bằng khảo sát điện lực địa phương | Thấp–TB | Thấp                                          | A         |
| 4 | **OpEx phi-điện**                    | Nhân công, bảo trì, thuê mặt bằng                        | **Khảo sát thị trường:** đơn giá nhân công/bảo trì theo định mức; giá thuê từ trang BĐS (batdongsan.com.vn, chotot) theo khu vực; benchmark ngành                                                                   | TB        | TB                                             | B         |
| 5 | **Dữ liệu đối thủ**               | Vị trí & công suất trạm bên thứ ba → tránh chồng lấn | **Crawl:** evcs.vn, PlugShare, Google Maps Places, OSM `charging_station`. Chuẩn hóa & khử trùng lặp                                                                                                                              | Cao       | TB (thiếu công suất/tình trạng real-time) | B         |
| 6 | **Chi phí & tình trạng mặt bằng** | Giá thuê, diện tích khả dụng → ràng buộc chọn điểm  | Crawl trang BĐS + lọc theo diện tích/mặt tiền; đối chiếu ảnh vệ tinh/Street View; khảo sát thực địa điểm shortlist                                                                                                           | TB        | TB                                             | B         |
| 7 | **Biến động mùa vụ / thời gian** | Nhu cầu lễ tết, cuối tuần, du lịch (trạm cao tốc)       | **Nguồn công khai:** thống kê lượt khách du lịch (Cục Du lịch, Sở VHTT&DL tỉnh); lịch lễ tết; Google Popular Times làm proxy; giả định hệ số mùa vụ                                                               | Cao       | TB                                             | C         |

---

## 3. Roadmap

Phân vai tổng quát:

- **Kỳ — Model only:** research facility location (p-median, MCLP, set cover) → định nghĩa bài toán → implement MCLP trên demand proxy + candidate sites do Giang cấp → report cuối. *Không đụng tới tầng dữ liệu.*
- **Giang — Toàn bộ Data layer + Demo:** tự crawl `station/connector` → validate/chuẩn hóa → schema + DB PostGIS → tự xây demand proxy (WorldPop/OSM/POI theo H3) + tính coverage → map demo / visualization.

> **Điểm bàn giao (2 điểm chạm interop — xem [SCHEMA_CONTRACT.md](schema/schema-contract.md)):**
>
> 1. **Giang → Kỳ** *(giữa Sprint 2)*: **demand proxy (grid heatmap) + candidate sites** làm input trực tiếp cho MCLP — Giang tự xây `demand_h3` từ nguồn công khai rồi dẫn xuất **trọng số demand per ô H3**.
> 2. **Kỳ → Giang** *(cuối Sprint 2 → Sprint 3)*: **GeoJSON kết quả model** (vị trí đề xuất + coverage) để tích hợp lên map.

> | Sprint   | Khoảng thời gian  | **Buổi đánh giá (thứ 7)** |
> | -------- | ------------------- | ------------------------------------ |
> | Sprint 1 | 17/07 → 25/07/2026 | **25/07/2026**                 |
> | Sprint 2 | 26/07 → 08/08/2026 | **08/08/2026**                 |
> | Sprint 3 | 09/08 → 22/08/2026 | **22/08/2026**                 |

### Sprint 1 — Nền tảng: dữ liệu thô, schema DB & định nghĩa bài toán *(review 25/07)*

| ✔ | Deadline            | Người     | Công việc                                                                                     | Input → Output                                                                                                                                                                                                                                                                                                                  |
| -- | ------------------- | ----------- | ----------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ☐ | **21/07**     | Kỳ + Giang | **Chốt schema data + format bàn giao** *(việc chặn — làm trước tiên)*          | **In:** yêu cầu bài toán + 2 điểm chạm interop (demand proxy, GeoJSON), mô hình **2 tầng `station → connector`.** <br /><br />**Out:** tài liệu schema thống nhất, đơn vị lưới **H3 res 8** — "hợp đồng" giữa 2 người → **[SCHEMA_CONTRACT.md](schema/schema-contract.md)** |
| ☐ | **17→21/07** | Giang       | Khảo sát nguồn dân số / POI / OSM cho demand proxy                                         | **In:** khu vực mục tiêu (1 thành phố). <br /><br />**Out:** danh mục nguồn khả dụng (WorldPop, OSM Geofabrik, POI) + đánh giá độ phủ/chất lượng + phác thảo **công thức trọng số demand**                                                                                             |
| ☐ | **17→22/07** | Kỳ         | Research facility location: p-median, MCLP, set cover + case study EV                           | **In:** tài liệu học thuật + case study EV siting. <br /><br />**Out:** bảng so sánh mô hình + **lý do chọn MCLP làm baseline** (đưa vào report define)                                                                                                                                          |
| ☐ | **22/07**     | Giang       | **Tự crawl `station`/`connector`** từ đầu (thay dataset lỗi của Kỳ) + data doc | **In:** nguồn crawl (evcs.vn / PlugShare / OSM / Google Places) + schema đã chốt ([SCHEMA_CONTRACT.md](schema/schema-contract.md)). <br /><br />**Out:** dataset `station`/`connector` parquet (snapshot Giang tự tạo, đúng schema mục tiêu) + data doc mới do Giang viết                                    |
| ☐ | **23/07**     | Giang       | Validate + làm sạch dataset Giang tự crawl                                                   | **In:** dataset thô Giang tự crawl + schema. <br /><br />**Out:** dataset sạch (khử trùng lặp, chuẩn hóa tọa độ/loại trụ, xử lý thiếu) + log lỗi                                                                                                                                                    |
| ☐ | **24/07**     | Giang       | Thiết kế schema**PostGIS**, dựng DB, load data                                         | **In:** dataset sạch + schema chốt. <br /><br />**Out:** DB PostGIS (`station/connector` 2 tầng + bảng H3 demand/coverage + GIST index) đã load data, sẵn sàng query — chờ **mentor approve**                                                                                                      |
| ☐ | **24/07**     | Kỳ         | Report**define bài toán**                                                               | **In:** kết quả research + yêu cầu bài toán + ràng buộc dữ liệu (mục 2). <br /><br />**Out:** report define (input/output, hàm mục tiêu, trade-off, lý do chọn hướng) — chờ **mentor review & approve**                                                                                    |

**DoD Sprint 1 (chốt tại review 25/07):** dataset thô đủ trường + ghi chú *(Giang tự crawl)*; report define được **mentor approve** *(Kỳ)*; data chuẩn hóa đã load vào PostGIS, **schema được mentor approve** *(Giang)*.

> **Phụ thuộc:** việc **chốt schema (dòng 1)** phải xong sớm nhất vì nó chặn toàn bộ pipeline dữ liệu của Giang. Chuỗi Sprint 1 của Giang: **tự crawl (22/07) → validate (23/07) → load PostGIS (24/07)** đều do một mình Giang chủ động, không còn phụ thuộc bàn giao từ Kỳ. *(Kỳ xác nhận crawl vẫn kịp deadline.)*

### Sprint 2 — Demand proxy, baseline MCLP & map demo v1 *(review 08/08)*

| ✔ | Deadline                           | Người | Công việc                                                                                                     | Input → Output                                                                                                                                                                                                                                                                                                 |
| -- | ---------------------------------- | ------- | --------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ☐ | **29/07**                    | Kỳ     | **Toy example** MCLP trên data giả lập *(làm sớm, dựng khung model trong lúc chờ demand proxy)* | **In:** data giả lập nhỏ (grid demand + candidate sites tự tạo). <br /><br />**Out:** code MCLP chạy được + hình minh họa (chọn p điểm phủ tối đa) — khung model tái dùng                                                                                                       |
| ☐ | **29/07**                    | Giang   | EDA phân bố trạm hiện tại (mật độ, khoảng trống địa lý)                                            | **In:** DB PostGIS (Sprint 1) + nn_distance/coverage do Giang tự tính. <br /><br />**Out:** phân tích mật độ + bản đồ khoảng trống địa lý (vùng thiếu phủ) → định hướng vùng ưu tiên                                                                                      |
| ☐ | **01/08** *(giữa sprint)* | Giang   | Xây**demand proxy** (grid heatmap nhu cầu); **bàn giao Kỳ** — *mốc chặn của sprint*       | **In:** WorldPop + POI + OSM (khảo sát Sprint 1) + DB — Giang **tự tính `demand_h3`** theo ô H3 res 8. <br /><br />**Out:** **grid heatmap nhu cầu** (mỗi cell có trọng số demand `= f(pop, road, POI…)`) dạng file chuẩn (GeoJSON/CSV) — input trực tiếp cho MCLP |
| ☐ | **05/08**                    | Kỳ     | Implement**baseline MCLP** cho 1 thành phố trên demand proxy của Giang                                | **In:** demand proxy (01/08) + candidate sites (trạm hiện tại + điểm tiềm năng). <br /><br />**Out:** model chọn vị trí cho 1 thành phố + danh sách vị trí đề xuất theo tham số                                                                                                  |
| ☐ | **05/08**                    | Giang   | **Map demo v1**: hiển thị trạm + heatmap demand *(song song với MCLP của Kỳ)*                     | **In:** DB trạm + demand proxy. <br /><br />**Out:** map demo hiển thị trạm hiện có + layer heatmap demand (bật/tắt)                                                                                                                                                                        |
| ☐ | **06/08**                    | Kỳ     | Đo coverage: mạng trạm hiện tại**vs.** vị trí model đề xuất                                     | **In:** vị trí model đề xuất + demand proxy + mạng trạm hiện tại. <br /><br />**Out:** chỉ số coverage (% demand/dân số được phủ) so sánh 2 kịch bản                                                                                                                            |
| ☐ | **07/08**                    | Kỳ     | Xuất**GeoJSON** cho map demo; trình bày lấy feedback mentor                                           | **In:** kết quả model + coverage. <br /><br />**Out:** file **GeoJSON** (vị trí đề xuất + coverage) bàn giao Giang + slide trình bày tại review 08/08                                                                                                                              |

**DoD Sprint 2 (chốt tại review 08/08):** demand proxy dùng trực tiếp làm input model *(Giang → Kỳ)*; baseline MCLP chạy được trên 1 thành phố + có **GeoJSON output** *(Kỳ)*; map demo v1 hiển thị trạm + heatmap *(Giang)*.

> **Phụ thuộc:** **demand proxy (01/08)** là mốc chặn — Kỳ không chạy được MCLP "thật" nếu chưa có nó. Vì vậy Kỳ làm **toy example trước** để dựng khung model, còn Giang ưu tiên xong proxy giữa sprint. *Giang tự xây demand từ nguồn công khai (WorldPop/OSM/POI) → chủ động hoàn toàn tiến độ proxy.*

> **⚠️ Đổi phân vai trong mốc 01/08 (29/07) — `E-DQ7d` bàn giao Kỳ.** Việc hiệu chuẩn & kiểm chứng
> `demand_weight` chuyển sang **Kỳ** (gộp với **P1**), vì audit cho thấy đây là bài toán **mô hình** chứ
> không phải làm sạch dữ liệu. Seam chia **theo tầng**, không theo vấn đề, để không đảo ngược điểm chạm
> interop #1:
>
> - **Giang vẫn giao đúng hạn 01/08:** lưới `demand_h3` (254.035 ô, 10 cột POI + 5 cột road đã làm sạch
>   qua `E-DQ7a/7b/7c`) · target `occ_h3` dựng từ 18,6M bản ghi occupancy · harness
>   `demand_validation.py` + 12 cổng QA.
> - **Kỳ nhận:** dạng hàm và trọng số của `demand_weight`, bổ sung **feature dòng chảy**, và trách nhiệm
>   **vượt cổng**.
>
> Hệ quả tiến độ: mốc 01/08 vẫn là mốc chặn nhưng **đổi nội dung** — thứ bàn giao là *lưới + target +
> cổng*, còn `demand_weight` cuối cùng do Kỳ chốt. **Cần xác nhận hai chiều tại buổi bàn giao 01/08.**

> **Lưu ý coverage:** coverage/gap do **Giang tự tính** theo **bán kính R của MCLP** — chốt **R = 3 km (baseline)**, quét {1,5 · 2 · 3 · 5} km (không dùng ngưỡng cố định 5 km), đồng bộ giữa demand proxy của Giang và bước đo coverage của Kỳ. ⚠️ **R phải > 0,98 km** (khoảng cách tâm–tâm ô res 8), nếu không MCLP suy biến thành `sort top-p` (**P4**).

### Sprint 3 — Ràng buộc, tích hợp & report cuối *(review 22/08)*

| ✔ | Deadline        | Người | Công việc                                                                                     | Input → Output                                                                                                                                                                                                  |
| -- | --------------- | ------- | ----------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ☐ | **14/08** | Kỳ     | Thêm ràng buộc**ngân sách, AC/DC** *(nếu kịp)*                                   | **In:** model baseline (Sprint 2) + chi phí CapEx theo loại trụ (mục 2). <br /><br />**Out:** model đa mức ngân sách — mỗi mức budget → (số trạm, vị trí, coverage)                  |
| ☐ | **15/08** | Kỳ     | **Bàn giao GeoJSON đa mức ngân sách** cho Giang                                      | **In:** model có ràng buộc. <br /><br />**Out:** **GeoJSON theo từng mức ngân sách** (vị trí + số trạm + coverage)                                                                  |
| ☐ | **18/08** | Giang   | Tích hợp**output model (GeoJSON)** lên map: vị trí đề xuất + coverage             | **In:** GeoJSON đa ngân sách (15/08). <br /><br />**Out:** map hiển thị vị trí đề xuất + vùng coverage đọc từ GeoJSON                                                                  |
| ☐ | **20/08** | Giang   | **What-if slider ngân sách** → map cập nhật coverage theo mức chọn *(nếu kịp)* | **In:** GeoJSON đa ngân sách + map tích hợp. <br /><br />**Out:** slider ngân sách → map cập nhật số trạm & coverage theo mức chọn                                                     |
| ☐ | **21/08** | Giang   | Hoàn thiện demo + data documentation                                                          | **In:** toàn bộ map demo + pipeline data. <br /><br />**Out:** demo hoàn chỉnh + tài liệu data (nguồn, schema, cách chạy)                                                                   |
| ☐ | **21/08** | Kỳ     | **Report cuối**                                                                          | **In:** kết quả model + coverage theo ngân sách + demo. <br /><br />**Out:** report cuối (kết quả, khuyến nghị vị trí, hướng mở rộng: power sharing, xe hãng khác, thời gian chờ) |

> **Phụ thuộc:** Kỳ phải **thêm ràng buộc ngân sách + xuất GeoJSON đa ngân sách trước** (14–15/08) thì Giang mới tích hợp map + slider được (18–20/08). Report cuối & hoàn thiện demo chạy cuối cùng.

**Tiêu chí hoàn thành (DoD cuối project):**

- **Model chạy end-to-end** *(Kỳ)* — trả lời được: **đặt trạm ở đâu, bao nhiêu trạm, coverage bao nhiêu % theo từng mức ngân sách**.
- **Map demo** *(Giang)* — hiển thị coverage + vị trí đề xuất từ output model, đọc trực tiếp GeoJSON của Kỳ.

**Gợi ý stack:** Model Python (PuLP / OR-Tools / NetworkX cho MCLP) · DB PostgreSQL + PostGIS · Demand proxy & EDA bằng Python (GeoPandas, rasterio) · Map demo React + Mapbox GL / deck.gl, hoặc nhanh hơn cho demo: Leaflet / kepler.gl / QGIS export.

> **Ghi chú phạm vi:** Các hạng mục hạ tầng nặng (API CRUD đầy đủ, auth/phân quyền, caching, CI/CD, containerize, monitoring) **nằm ngoài phạm vi 3 sprint** — xem "hướng mở rộng" ở mục 4 & 5. Mục tiêu internship là **model end-to-end + demo minh họa**, không phải sản phẩm production.

---

## 4. Output

Output của cả 2 người ghép lại thành **2 tầng**:

**(a) Model output — do Kỳ tạo (bàn giao dạng GeoJSON):**

- Danh sách **vị trí đề xuất** (tọa độ) cho mỗi mức ngân sách.
- **Số trạm** đề xuất tương ứng từng mức ngân sách.
- **Coverage (%)** đạt được theo từng mức ngân sách (đường cong coverage vs. budget).
- Loại trụ AC/DC gợi ý cho từng vị trí *(nếu kịp ràng buộc Sprint 3)*.

**(b) Demo & Report — do Giang + Kỳ trình bày:**

- **Map demo** *(Giang)*: hiện trạng (trạm + heatmap demand) + lớp vị trí đề xuất & coverage đọc từ GeoJSON; what-if slider ngân sách *(nếu kịp)*.
- **Report cuối** *(Kỳ)*: tổng hợp kết quả, khuyến nghị vị trí, hướng mở rộng — cho stakeholder không dùng tool.

**Metrics output cốt lõi (khả thi trong phạm vi dữ liệu công khai):**

- **Coverage (%)** dân số / nhu cầu trong bán kính X km có trạm — **theo từng mức ngân sách** *(core, đúng tiêu chí hoàn thành)*.
- **Số trạm đề xuất** theo từng mức ngân sách.
- So sánh coverage: **mạng hiện tại vs. vị trí model đề xuất**.
- Vị trí đề xuất (tọa độ) + loại trụ AC/DC gợi ý.

> **Đơn vị output cho mỗi vị trí đề xuất** là một record gồm: tọa độ, cấu hình súng sạc khuyến nghị (nếu có), mức ngân sách áp dụng, và đóng góp coverage của điểm đó.

> **Hướng mở rộng (ngoài phạm vi internship — cần dữ liệu vận hành mà công ty chưa cung cấp):** utilization rate, kWh & doanh thu dự phóng, CapEx/OpEx, payback period, ROI, số trạm bottleneck/underutilized, thời gian chờ & queue probability, grid capacity utilization. Các metric này **phụ thuộc log vận hành thực** (mục 2 #1) hoặc mô phỏng nhu cầu chi tiết → chỉ khả thi ở giai đoạn sau.

---

## 5. Frontend / Map demo (mô tả sơ lược)

Trong phạm vi internship, frontend = **map demo** do **Giang** đảm nhiệm, lấy input là **GeoJSON kết quả model của Kỳ**. Đây là demo minh họa, không phải dashboard production.

**Phạm vi demo (3 sprint):**

- **Bản đồ hiện trạng** *(Giang, Sprint 2)*: trạm hiện có + **layer heatmap nhu cầu (Demand Map)** bật/tắt.
- **Layer vị trí đề xuất + coverage** *(Giang, Sprint 3)*: marker vị trí model đề xuất, vùng phủ theo bán kính, đọc trực tiếp từ GeoJSON của Kỳ.
- **What-if slider ngân sách** *(Giang, Sprint 3 — nếu kịp)*: kéo mức ngân sách → map cập nhật số trạm & coverage tương ứng.

**Ưu tiên UX cho demo:** hiển thị rõ **coverage theo mức ngân sách** và **explainability** — mỗi vị trí đề xuất trả lời được "tại sao đặt ở đây" (nằm ở vùng nhu cầu cao / lấp khoảng trống phủ).

> **Hướng mở rộng (ngoài phạm vi internship):** dashboard đầy đủ — filter theo khu vực/loại súng/thời gian, info panel chi tiết trạm, metrics summary bar (KPI), so sánh kịch bản cạnh nhau, tối ưu render nhiều điểm (clustering / WebGL). Các phần này chỉ cần khi chuyển từ demo sang sản phẩm decision-support thực thụ.

---

## Phụ lục — Assumptions & Limitations (đề xuất bổ sung)

> **⚠️ Rủi ro & vấn đề đã biết (11 mục P1–P11, kèm nhóm chất lượng dữ liệu E-DQ):** theo dõi & xử lý ở **[known-issues.md](known-issues.md)** — đã kiểm chứng thực nghiệm; **P4 là lỗi FATAL** (bán kính 500 m suy biến MCLP thành sort top-p) — **đã chốt cách xử lý 24/07: giữ lưới H3 res 8, chốt R = 3 km**; quyết định cốt lõi: có dùng 18,6M điểm occupancy để calibrate demand hay không.
>
> **Đã trả lời (29/07, `E-DQ7d`): dùng occupancy làm TRỌNG TÀI, chưa phải làm THẦY.** Đo đạc cho thấy fit
> trọng số trên tập feature hiện tại chỉ hơn `pop` đơn độc **+0,07** và hơn **chính bộ trọng số bị đảo**
> **+0,06**, trong khi trần đo được của target là **0,865** — nút thắt là **tập feature**, không phải trọng
> số. Vì vậy occupancy trước mắt dùng để **kiểm chứng** `demand_weight` (12 cổng QA), chưa dùng để huấn
> luyện nó. **E-DQ7d là mục 🔴 chặn duy nhất còn mở**, đã **bàn giao Kỳ (29/07)**; target `occ_h3` + harness
> vẫn thuộc tầng dữ liệu (Giang). Chi tiết: [known-issues.md — E-DQ7d](known-issues.md#e-dq7d--proxy-cầu-chưa-kiểm-chứng-ngoại-vi-bước-7).


- Phạm vi internship là **model MCLP end-to-end (Kỳ) + toàn bộ data layer & map demo (Giang)**; hạ tầng production (API đầy đủ, auth, CI/CD, monitoring) là hướng mở rộng sau. *(Cần chốt lại với mentor.)*
- **Đổi phân vai (21/07):** dataset gold của Kỳ bị lỗi → bỏ hẳn; **Giang tự xây toàn bộ tầng dữ liệu** (crawl station/connector + demand + coverage). Kỳ chỉ còn model. `DATASET_EXPLAINED.md` (của Kỳ) **deprecated**.
- POI (OSM) và mật độ dân cư (WorldPop) là dữ liệu mở, độ chính xác đủ cho MVP nhưng có thể lệch ở khu vực cập nhật thưa → giai đoạn sau nên đối chiếu dữ liệu nội bộ.
- **Đơn vị không gian là H3 res 8** — ô ở VN: cạnh 0,56 km, **tâm 2 ô kề nhau cách `d` = 0,98 km**, diện tích 0,83 km² — chuẩn hóa demand/coverage/candidate về cùng lưới (xem [SCHEMA_CONTRACT.md](schema/schema-contract.md)). Đi kèm: **bán kính phục vụ R = 3 km**, bắt buộc `R > d` nếu không MCLP suy biến (**P4**). Demand do **Giang tự xây** từ WorldPop/OSM/POI theo H3 (không dùng dataset của Kỳ). Mỗi lần rebuild tạo snapshot mới.
- **Coverage/gap được Giang tự tính theo bán kính R của MCLP** (**R = 3 km baseline**, gate `R > 0,98 km` — **P4**), không dùng ngưỡng `has_station_5km` cố định. Trọng số demand (`f(pop, road, POI…)`) do Giang định nghĩa.
- Biểu giá điện có thể thay đổi khi EVN điều chỉnh giá bình quân → pipeline cần cho phép cập nhật `pricing_tiers`.
- Dữ liệu GPS/traffic và grid constraints phụ thuộc thương lượng nội bộ / bên thứ ba → là rủi ro tiến độ chính của Demand Map.
- Không có log vận hành thực → các metric hiệu quả doanh nghiệp (utilization, ROI, bottleneck) chỉ ước lượng/mô phỏng, không phải số thật (xem mục 2 #1 & mục 4).
