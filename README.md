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

## Trạng thái & register vấn đề

- **Nguồn chân lý vấn đề:** [`docs/known-issues.md`](docs/known-issues.md) — P1–P11, E-DQ1–10, và **F1–F19** (review 28/07).
- **Review pipeline gần nhất:** [`docs/sprint-reviews/data-pipeline-review-2026-07-28.md`](docs/sprint-reviews/data-pipeline-review-2026-07-28.md) (bảng phát hiện + bằng chứng + thứ tự ưu tiên fix).
- `build_demand_proxy` / `mclp` / `export_geojson` hiện là **stub** (chưa hiện thực).

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
│   ├── processed/             # model-ready: candidate_sites, covered0
│   └── external/              # biểu giá điện EVN
│
├── src/ev_siting/
│   ├── aoi.py                 # AOI city/national duck-typed (E-DQ9)
│   ├── data/
│   │   ├── evcs/              # enumerate → scrape → split → master → canonical → dedup → validate
│   │   ├── vinfast_official/  # registry chính thức + matcher (xref verified)
│   │   ├── osm/               # roads (pbf) + POI (overpass) → h3
│   │   ├── worldpop/          # pop → demand_h3
│   │   ├── landuse/           # worldcover + osm_exclusion → buildable_h3
│   │   └── provenance/        # freeze/verify snapshot (E-DQ10)
│   ├── features/              # build_candidates, build_covered0, build_demand_proxy (stub)
│   ├── models/                # mclp.py (stub)
│   └── viz/                   # export_geojson.py (stub)
│
├── tests/                     # pytest (15 test; cần bổ sung theo F16)
└── .github/workflows/ci.yml   # uv sync + ruff + pytest
```
