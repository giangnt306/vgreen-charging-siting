# P1 — Heuristic weights vs fit model 18,6M occupancy

`🟠 SIMPLIFY · ☐ Open · Owner: Kỳ` — **gộp vào [E-DQ7d](../e-data-quality/e-dq7d-demand-proxy-validation.md)** (29/07)

> ⚠️ **Đính chính 29/07 — tiền đề của P1 đã bị bác bỏ bằng đo đạc.** P1 giả định vấn đề nằm ở
> **trọng số** ("heuristic thay vì fit"). Audit E-DQ7d fit đúng cái mà P1 đề xuất — NNLS không âm trên
> log1p, 20 cột (10 feature × k0/k-ring 1), spatial CV **leave-one-province-out** 64 tỉnh, 11.628 ô cung
> — và được **ρ = 0,329**. Cùng lúc: `pop` **đơn độc** cho **0,261**, và **đảo ngẫu nhiên chính bộ trọng
> số vừa fit** vẫn cho **0,266**. Tức là toàn bộ công sức "fit có giám sát" mua được **+0,07 so với không
> làm gì** và **+0,06 so với trọng số vô nghĩa**, trong khi trần đo được của target là **0,865**.
>
> ⇒ **Nút thắt không phải trọng số mà là TẬP FEATURE.** 10 cột hiện có mô tả *cư dân và cửa hàng*; còn
> occupancy do *xe đang di chuyển* và *thời gian đỗ* quyết định. Fit lại trọng số trên đúng tập cột này
> **không thể** đóng được khoảng cách 0,33 → 0,865, dù dùng model gì.

**P1 đổi mục tiêu** (không còn là "fit trọng số"): bổ sung **feature dòng chảy** dẫn từ `.pbf` **đã
freeze** (betweenness centrality mạng đường · khoảng cách tới nút giao cao tốc · 91 đối tượng
`highway=services|rest_area` mà E-DQ7b đã tìm ra) + **số hạng catchment k-ring** đồng bộ `R = 3 km`
(**P4**), rồi mới nói chuyện trọng số. Chi tiết chẩn đoán, seam bàn giao và bộ cổng:
[E-DQ7d](../e-data-quality/e-dq7d-demand-proxy-validation.md).

**Giữ lại từ bản cũ (chưa kiểm chứng lại sau E-DQ7a/7b/7c):** hai công thức Proxy A & B cho gợi ý vị
trí tương đồng **91%** ($r = 0,91$). ⚠️ Con số này **không** chứng minh "heuristic đã ổn định" — hai
công thức cùng sai theo một hướng thì vẫn tương đồng cao; nó chỉ đo **độ nhạy giữa hai bộ trọng số**,
đúng thứ mà C3 của E-DQ7c cảnh báo là phải đo bằng **top-K overlap**, và đúng thứ mà cổng
`proxy_beats_scramble` bây giờ đo được **ngoại vi** thay vì nội tại.

---

← [Register vấn đề](../../known-issues.md) · [Mục lục issue](../README.md)
