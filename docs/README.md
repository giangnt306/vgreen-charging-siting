# Tài liệu dự án — VGreen Charging Siting

Mục lục điều hướng. Tổ chức theo **vai trò**: cấp dự án ở gốc `docs/`, còn lại gom theo nhóm.
Cập nhật cấu trúc: **2026-07-30**.

```
docs/
├── de-bai-v2.md            # ĐỀ BÀI HIỆN HÀNH (29/07) — đọc TRƯỚC
├── problem-analysis.md     # define bài toán + roadmap 3 sprint (định nghĩa bài toán đã bị de-bai-v2 thay)
├── known-issues.md         # REGISTER vấn đề (chú giải · bảng trạng thái · thứ tự xử lý · ghi chú hợp nhất)
├── issues/                 # 1 file / 1 vấn đề, chia 5 thư mục theo nhóm A–E của register
│   ├── a-demand-target/        # A · Demand Target & Data Science
│   ├── b-spatial-geometry/     # B · Spatial Geometry & Siting Mechanics
│   ├── c-master-data/          # C · Master Data & Entity Resolution
│   ├── d-covariates/           # D · Covariates & Feature Engineering
│   └── e-data-quality/         # E · Data Quality & Cleaning (17 issue)
├── data-layer/             # kiến trúc tầng dữ liệu · kiểm kê · candidate sites
├── sources/                # tài liệu từng nguồn crawl
├── schema/                 # hợp đồng dữ liệu · data dictionary · ERD · review
├── reports/                # báo cáo bàn giao (đọc được cho người ngoài team)
├── review/                 # biên bản review trưởng nhóm dữ liệu (nhóm G của register)
├── lineage/                # bản đồ lineage đo trực tiếp (audit có niên đại)
└── sprint-reviews/         # slide/ghi chú mỗi buổi review (nhóm F của register)
```

## Cấp dự án (gốc `docs/`)

| File                                       | Nội dung                                                                              |
| ------------------------------------------ | ------------------------------------------------------------------------------------- |
| [de-bai-v2.md](de-bai-v2.md)               | **ĐỀ BÀI HIỆN HÀNH (29/07)** — phát biểu lại sau yêu cầu BO + 3 kết quả âm; hệ nhãn thẩm quyền A1–A4. Thay phần *định nghĩa bài toán* của `problem-analysis.md`. **Đọc file này TRƯỚC.** |
| [problem-analysis.md](problem-analysis.md) | Report define bài toán (20/07): mục tiêu 3 bên, phân tích dữ liệu, roadmap 3 sprint, output. ⚠️ Phần *định nghĩa bài toán* + DoD coverage **đã bị thay** bởi `de-bai-v2.md`; phần *phân tích nguồn dữ liệu* và *roadmap sprint* còn hiệu lực. |
| [known-issues.md](known-issues.md)         | **Register vấn đề** (P1–P11 + `E-DQ*` + nhóm `F`/`G` port 30/07) — trạng thái & thứ tự xử lý. **Nguồn chân lý.** |

## `issues/` — bộ giải pháp, một file mỗi vấn đề

Xem [issues/README.md](issues/README.md) để có bảng đầy đủ theo nhóm A–E.
Tách khỏi `known-issues.md §3` ngày 30/07 (§3 khi đó đã 1.660 dòng), rồi chia **5 thư mục theo nhóm**.
**Register giữ trạng thái + thứ tự xử lý; `issues/` giữ chi tiết.** Nhóm (thư mục) là thuộc tính **bền** của
issue nên đặt được vào đường dẫn; trạng thái và thứ tự thì **không** — chúng chỉ sống ở register.

## `data-layer/` — tầng dữ liệu

| File                                                       | Nội dung                                                                               |
| ---------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| [data-layer/overview.md](data-layer/overview.md)           | Kiến trúc pipeline, cấu trúc code, các bước `make`, trạng thái schema, build task còn thiếu. |
| [data-layer/dataset-inventory.md](data-layer/dataset-inventory.md) | **Kiểm kê dữ liệu** — số nguồn / bảng / dòng / cột / dung lượng (đo trực tiếp từ file). |
| [data-layer/candidate-sites.md](data-layer/candidate-sites.md) | Định nghĩa & sinh candidate sites (P5) cho MCLP.                                   |

## `sources/` — tài liệu từng nguồn crawl

| File                                                     | Nguồn                                      |
| -------------------------------------------------------- | ------------------------------------------ |
| [sources/evcs.md](sources/evcs.md)                       | evcs.vn (cung — trạm sạc + time-series).   |
| [sources/vinfast-official.md](sources/vinfast-official.md) | VinFast official (xác minh first-party).  |
| [sources/osm.md](sources/osm.md)                         | OpenStreetMap (POI + đường).               |
| [sources/worldpop.md](sources/worldpop.md)               | WorldPop (dân số → demand).                |

> Chưa có file riêng cho **VNSDI** (ranh giới + dân số cấp xã) và **ESA WorldCover** — nguồn được mô tả trong
> [issues/e-dq3-admin-enrichment.md](issues/e-data-quality/e-dq3-admin-enrichment.md) và
> [data-layer/candidate-sites.md](data-layer/candidate-sites.md).

## `schema/` — schema & hợp đồng dữ liệu

Xem [schema/README.md](schema/README.md) — `schema-contract.md`, `data-dictionary.md`, `schema-review.md`, `erd/`.

## `reports/` — báo cáo bàn giao

| File                                                       | Nội dung                                                        |
| ---------------------------------------------------------- | --------------------------------------------------------------- |
| [reports/evcs-data-quality.md](reports/evcs-data-quality.md) | Báo cáo chất lượng & xử lý dữ liệu evcs.vn (dạng đọc cho người ngoài team). |

## `review/` — biên bản review dữ liệu

| File                                                       | Nội dung                                                        |
| ---------------------------------------------------------- | --------------------------------------------------------------- |
| [review/2026-07-29-data-lead-review.md](review/2026-07-29-data-lead-review.md) | Review trưởng nhóm dữ liệu 29/07: phán quyết + 16 mục `L` (4 CHẶN đã đóng — nhóm `G` register; 12 còn mở theo dõi tại đây). |
| [review/2026-07-30-review-plan.md](review/2026-07-30-review-plan.md) | Kế hoạch review 5 phase + đề xuất `HANDOFF.json` một-nguồn-số (chặn họ lỗi doc-drift). |

## `lineage/` — bản đồ lineage

| File                                                       | Nội dung                                                        |
| ---------------------------------------------------------- | --------------------------------------------------------------- |
| [lineage/2026-07-30-full-lineage.md](lineage/2026-07-30-full-lineage.md) | Lineage đầy đủ đo trực tiếp (30/07, **trên nhánh Kỳ trước hợp nhất** — audit có niên đại, không sửa số bên trong). |

## `sprint-reviews/`

Slide / ghi chú mỗi buổi review (thứ 7 cuối sprint). Hai biên bản
[data-pipeline-review-2026-07-24.md](sprint-reviews/data-pipeline-review-2026-07-24.md) và
[data-pipeline-review-2026-07-28.md](sprint-reviews/data-pipeline-review-2026-07-28.md) là **nguồn bằng chứng**
của nhóm `F` trong register.
