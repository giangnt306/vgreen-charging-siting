# ev-charging-siting

Tối ưu vị trí đặt trạm sạc EV (MCLP) — crawl evcs.vn + occupancy telemetry, land-use/demand features, candidate sites.

> **Dữ liệu nội bộ (vault):** nguồn evcs.vn/tramev bị giới hạn ToS, bảng trộn OSM là ODbL-derived.
> **Không public dữ liệu** khi chưa có license + sign-off — xem `docs/known-issues.md` mục **F1**.

## Quickstart

```bash
make setup              # uv sync + playwright chromium (cho tầng crawl)
make verify-snapshot    # đối chiếu data/raw với MANIFEST.json (E-DQ10); HASHES=1 để check nội dung
make test               # unit tests
make help               # toàn bộ lệnh pipeline (crawl / canonical / landuse / candidates / covered0)
```

Dữ liệu không nằm trong git (trừ `data/raw/MANIFEST.json`). Snapshot chốt `2026-07-20`
(2,19GB) khôi phục được từ bản sao HF nội bộ — sau khi tải về `data/`, giải nén
`data/interim/evcs_timeseries.tar.zst` và `data/raw/vinfast_official/details.tar.zst`
tại chỗ, rồi chạy `make verify-snapshot HASHES=1` (phải PASS).

## Sản phẩm: hồ sơ thẩm định vị trí

Deliverable hiện tại **không phải điểm số** — là **hồ sơ facts** cho người duyệt (2 kết luận:
`Đủ điều kiện xem xét` / `Cần khảo sát`, không bao giờ tự "Từ chối"). Lý do đổi:
`docs/…/postmortem-assess-v0.md` phía repo kế hoạch.

```bash
make assess-occupancy            # cache occupancy duration-weighted (F19) — chạy một lần
make sizing                      # benchmark định cỡ: utilization theo (loại trụ × mật độ × cổng)
make dossier IN=points.csv       # CSV (lat,lng[,point_id]) -> hồ sơ .md + bảng phẳng .csv
make spotcheck                   # 20 điểm bẫy + oracle độc lập; exit != 0 nếu có lỗi fact
make pilot                       # API: POST /dossier · /dossier/markdown · /dossier/batch (CSV->CSV)
make mclp-bench                  # bấm giờ solver MCLP quốc gia (HiGHS + greedy)
```

Chấm một điểm ~0,3 s (ngữ cảnh dựng 2 s một lần). Mọi output mang `data_version`,
`model_version` và nhãn hiệu chỉnh; không output nào chứa toạ độ/mã trạm vault.

## Trạng thái & register vấn đề

- **Nguồn chân lý vấn đề:** [`docs/known-issues.md`](docs/known-issues.md) — P1–P11, E-DQ1–10, và **F1–F19** (review 28/07).
- **Review pipeline gần nhất:** [`docs/sprint-reviews/data-pipeline-review-2026-07-28.md`](docs/sprint-reviews/data-pipeline-review-2026-07-28.md) (bảng phát hiện + bằng chứng + thứ tự ưu tiên fix).
- `build_demand_proxy` / `export_geojson` hiện là **stub** (chưa hiện thực) —
  vị trí + hợp đồng đã chốt ở [`docs/data-layer/overview.md` §2](docs/data-layer/overview.md).
- `models/mclp.py` **đã hiện thực** (29/07): solver HiGHS + greedy + bench bấm giờ — bài quốc gia
  giải tối ưu chứng minh được trong ~4 s (`make mclp-bench`). Mục tiêu hiện là `cov@pop`, **chưa**
  phải `cov@demand_weight` (còn chờ `build_demand_proxy`).

## Project structure

```
ev-charging-siting/
├── README.md
├── pyproject.toml             # deps thật của src/ (uv sync; editable install)
├── Makefile                   # mọi lệnh tái lập: setup/test/crawl/canonical/landuse/candidates/...
├── .env.example               # mẫu biến môi trường (KHÔNG commit .env thật)
│
├── docs/
│   ├── README.md              # mục lục tài liệu
│   ├── problem-analysis.md    # define bài toán + roadmap
│   ├── known-issues.md        # register P/E-DQ/F — NGUỒN CHÂN LÝ để monitor & xử lý
│   ├── sources/               # tài liệu từng nguồn crawl (evcs/osm/vinfast/worldpop)
│   ├── data-layer/            # overview tầng dữ liệu + candidate-sites
│   ├── schema/                # SCHEMA_CONTRACT + data-dictionary + schema-review
│   └── sprint-reviews/        # review 24/07, 28/07
│
├── data/                      # gitignored, trừ raw/MANIFEST.json (E-DQ10)
│   ├── raw/                   # crawl thô BẤT BIẾN (freeze read-only, checksum trong MANIFEST)
│   ├── interim/               # master/canonical/landuse/demand + evcs_timeseries/ (19.218 csv)
│   ├── processed/             # model-ready: candidate_sites, covered0 + bundle <label>/<scope>/
│   └── external/              # biểu giá điện EVN
│
├── src/ev_siting/             # MỖI package có paths.py neo PROJECT_ROOT + hằng số của tầng
│   ├── aoi.py                 # AOI city/national duck-typed (E-DQ9)
│   ├── data/
│   │   ├── evcs/              # enumerate → scrape → split → master → canonical → dedup → validate
│   │   ├── vinfast_official/  # registry chính thức + matcher (xref verified)
│   │   ├── osm/               # roads (pbf) + POI (overpass) → h3
│   │   ├── worldpop/          # pop → demand_h3
│   │   ├── landuse/           # worldcover + osm_exclusion → buildable_h3
│   │   └── provenance/        # freeze/verify snapshot (E-DQ10)
│   ├── features/              # build_candidates, build_covered0, freeze_processed, demand_proxy (stub)
│   ├── models/                # paths.py (hợp đồng λ/R) + mclp.py (solver+bench), assess.py
│   └── viz/                   # paths.py + export_geojson.py (stub)
│
├── notebooks/                 # thăm dò (không phải pipeline) — xem notebooks/README.md
├── reports/                   # bài viết bàn giao + figures/ được chọn kèm bài
├── outputs/                   # gitignored: nghiệm MCLP, hình, map — tái lập được
│
└── tests/                     # pytest (44 test) — `make test`
```

> CI chưa được nối lại sau khi gỡ workflow (commit `rm ci`); cổng chất lượng hiện chạy tay:
> `make test` + `uv run ruff check src tests`.
