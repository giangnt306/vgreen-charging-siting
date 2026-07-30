# ev-charging-siting

Tối ưu vị trí đặt trạm sạc EV (MCLP) — crawl evcs.vn + occupancy telemetry, land-use/demand features, candidate sites, map demo.

> **Dữ liệu nội bộ (vault):** nguồn evcs.vn/tramev bị giới hạn ToS, bảng trộn OSM là ODbL-derived.
> **Không public dữ liệu** khi chưa có license + sign-off — xem `docs/known-issues.md` mục **F1**.

## Quickstart

```bash
make setup              # uv sync + playwright chromium (cho tầng crawl)
make verify-snapshot    # đối chiếu data/raw với MANIFEST.json (E-DQ10); HASHES=1 để check nội dung
make test               # unit tests
make help               # toàn bộ lệnh pipeline (crawl / canonical / demand / landuse / candidates / covered0)
```

Dữ liệu không nằm trong git (trừ `data/raw/MANIFEST.json`). Snapshot chốt `2026-07-20`
(2,19GB) khôi phục được từ bản sao HF nội bộ — sau khi tải về `data/`, giải nén
`data/interim/evcs_timeseries.tar.zst` và `data/raw/vinfast_official/details.tar.zst`
tại chỗ, rồi chạy `make verify-snapshot HASHES=1` (phải PASS).

## Trạng thái & register vấn đề

- **Nguồn chân lý vấn đề:** [`docs/known-issues.md`](docs/known-issues.md) — P1–P11, E-DQ1–10, và **F1–F19** (review 28/07).
- **Review pipeline gần nhất:** [`docs/sprint-reviews/data-pipeline-review-2026-07-28.md`](docs/sprint-reviews/data-pipeline-review-2026-07-28.md) (bảng phát hiện + bằng chứng + thứ tự ưu tiên fix).
- `build_demand_proxy` / `mclp` / `export_geojson` hiện là **stub** (chưa hiện thực).

## Project structure

```
ev-charging-siting/
├── README.md                  # mô tả, cách chạy, phân công (link tới docs/)
├── .gitignore                 # Python + loại data/ + .env (giữ lại data/raw/MANIFEST*.json)
├── .env.example               # mẫu biến môi trường (KHÔNG commit .env thật)
├── pyproject.toml             # deps thật của src/ (uv sync; editable install)
├── Makefile                   # mọi lệnh tái lập: setup/test/crawl/canonical/demand/landuse/candidates/...
│
├── docs/                      # tài liệu (xem docs/README.md để điều hướng)
│   ├── README.md              # mục lục tài liệu
│   ├── problem-analysis.md    # report define bài toán + roadmap
│   ├── known-issues.md        # register vấn đề P1–P11 + E-DQ + F (nguồn chân lý)
│   ├── issues/                # 1 file / 1 vấn đề — chẩn đoán, cách xử lý, QA gate
│   ├── sources/               # tài liệu từng nguồn crawl (evcs/osm/vinfast/worldpop)
│   ├── data-layer/            # overview tầng dữ liệu + kiểm kê + candidate sites
│   ├── schema/                # SCHEMA_CONTRACT + data-dictionary + ERD + schema-review
│   ├── reports/               # báo cáo bàn giao (evcs data quality)
│   └── sprint-reviews/        # slide/ghi chú mỗi buổi review
│
├── data/                      # (gitignored — trừ .gitkeep và raw/MANIFEST*.json, E-DQ10)
│   ├── raw/                   # dữ liệu crawl thô, BẤT BIẾN (freeze read-only, checksum trong MANIFEST)
│   ├── external/              # WorldPop, OSM, biểu giá điện
│   ├── interim/               # master/canonical/landuse/demand + evcs_timeseries/ (19.218 csv)
│   └── processed/             # model-ready: candidate_sites, covered0
│
├── config/                    # cấu hình
│   └── db/                    # tầng cơ sở dữ liệu (Giang)
│       ├── migrations/        # SQL tạo bảng station→port→connector + GIST index
│       └── seeds/             # script load data vào PostGIS
│
├── src/ev_siting/             # code chính (package import được)
│   ├── aoi.py                 # AOI city/national duck-typed (E-DQ9)
│   ├── data/
│   │   ├── evcs/              # enumerate → scrape → split → master → canonical → dedup → validate
│   │   ├── vinfast_official/  # registry chính thức + matcher (xref verified, F7)
│   │   ├── osm/               # vn_boundary + roads (pbf) + POI → h3  [E-DQ7a/c]
│   │   ├── worldpop/          # pop → reconcile/reallocate → demand_h3  [E-DQ7f, E-DQ8]
│   │   ├── admin/             # nhãn commune/province (VNSDI) cho stations + grid  [E-DQ3]
│   │   ├── vnsdi/             # crawl polygon xã/phường + dân số VNSDI  [E-DQ7f]
│   │   ├── landuse/           # worldcover + osm_exclusion → buildable_h3  [P5]
│   │   └── provenance/        # freeze/verify snapshot (E-DQ10)
│   ├── features/              # build_candidates, build_covered0, build_demand_proxy (stub)
│   ├── models/                # mclp.py — optimization (stub)
│   └── viz/                   # export_geojson.py, map helpers (stub)
│
├── app/                       # map demo frontend (Giang) — React/Leaflet
│
├── outputs/                   # kết quả sinh ra
│   ├── geojson/               # ← handoff Kỳ→Giang (vị trí đề xuất + coverage)
│   └── figures/               # hình cho report
│
└── tests/                     # unit test cho src/
```
