# Tài liệu dự án — VGreen Charging Siting

Mục lục điều hướng tài liệu. Tổ chức theo **vai trò**: cấp dự án ở gốc, còn lại gom theo nhóm.

## Cấp dự án (gốc `docs/`)

| File | Nội dung |
| --- | --- |
| [problem-analysis.md](problem-analysis.md) | Report define bài toán: mục tiêu 3 bên, phân tích dữ liệu, roadmap 3 sprint, output. |
| [known-issues.md](known-issues.md) | **Register vấn đề** (P1–P11 + nhóm chất lượng dữ liệu `E-DQ`) — nguồn chân lý để monitor & xử lý. |

## `sources/` — tài liệu từng nguồn crawl

| File | Nguồn |
| --- | --- |
| [sources/evcs.md](sources/evcs.md) | evcs.vn (cung — trạm sạc + time-series). |
| [sources/vinfast-official.md](sources/vinfast-official.md) | VinFast official (xác minh first-party). |
| [sources/osm.md](sources/osm.md) | OpenStreetMap (POI + đường). |
| [sources/worldpop.md](sources/worldpop.md) | WorldPop (dân số → demand). |

## `data-layer/` — tầng dữ liệu

| File | Nội dung |
| --- | --- |
| [data-layer/overview.md](data-layer/overview.md) | Tổng quan pipeline dữ liệu (kiến trúc, code, schema thực tế, build tasks còn thiếu). |
| [data-layer/candidate-sites.md](data-layer/candidate-sites.md) | Định nghĩa & sinh candidate sites (P5) cho MCLP. |

## `schema/` — schema & hợp đồng dữ liệu

Xem [schema/README.md](schema/README.md) — `schema-contract.md`, `data-dictionary.md`, `schema-review.md`, `erd/`.

## `sprint-reviews/`

Slide / ghi chú mỗi buổi review (thứ 7 cuối sprint).
