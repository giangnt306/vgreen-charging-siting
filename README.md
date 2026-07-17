# ev-charging-siting

Tối ưu vị trí đặt trạm sạc EV (MCLP) - demand proxy + map demo.

## Project structure

```
ev-charging-siting/
├── README.md                  # mô tả, cách chạy, phân công (link tới docs/)
├── LICENSE
├── .gitignore                 # Python + loại data/ + .env
├── .env.example               # mẫu biến môi trường (KHÔNG commit .env thật)
├── pyproject.toml             # dự án Python
├── Makefile                   # lệnh tái lập: make data, make proxy, make model
│
├── docs/                      # tài liệu
│   ├── problem-analysis.md    # report này
│   ├── data-dictionary.md     # mô tả trường dữ liệu (schema bàn giao Kỳ↔Giang)
│   ├── schema/                # ERD + tài liệu schema PostGIS
│   └── sprint-reviews/        # slide/ghi chú mỗi buổi review
│
├── data/                      # (gitignored — trừ .gitkeep)
│   ├── raw/                   # dữ liệu crawl thô, BẤT BIẾN (Kỳ)
│   ├── external/              # WorldPop, OSM, biểu giá điện
│   ├── interim/               # data đã làm sạch (Giang)
│   └── processed/             # model-ready: demand proxy, candidate sites
│
├── db/                        # tầng cơ sở dữ liệu (Giang)
│   ├── migrations/            # SQL tạo bảng station→port→connector + GIST index
│   └── seeds/                 # script load data vào PostGIS
│
├── notebooks/                 # EDA/thử nghiệm — đánh số + tên người
│   ├── 01-giang-eda-stations.ipynb
│   └── 02-ky-mclp-toy-example.ipynb
│
├── src/ev_siting/             # code chính (package import được)
│   ├── data/                  # crawl, clean, load_to_postgis (Kỳ+Giang)
│   ├── features/              # build_demand_proxy.py (Giang)
│   ├── models/                # mclp.py — optimization (Kỳ)
│   └── viz/                   # export_geojson.py, map helpers
│
├── app/                       # map demo frontend (Giang) — React/Leaflet
│
├── outputs/                   # kết quả sinh ra
│   ├── geojson/               # ← handoff Kỳ→Giang (vị trí đề xuất + coverage)
│   └── figures/               # hình cho report
│
├── tests/                     # unit test cho src/
├── config/                    # params.yaml (bán kính, mức ngân sách, trọng số)
└── .github/workflows/         # CI (lint + test)
```
