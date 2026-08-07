#!/usr/bin/env python3
"""fetch_places.py — Quét Overture Maps Places trong `VN_BBOX` về parquet thô.

**Vì sao DuckDB chứ không phải một API.** Overture không có API truy vấn; nó phát hành
GeoParquet trên S3 public (`s3://overturemaps-us-west-2`, không cần credentials, không
requester-pays). Toàn bộ theme `places` ~60M dòng / ~30 GB. DuckDB + `httpfs` đọc được
trực tiếp qua HTTP range request và **đẩy predicate xuống row-group**: cột `bbox` là
struct `{xmin,xmax,ymin,ymax}` nằm trong thống kê parquet, nên lọc theo `bbox.xmin/ymin`
chỉ tải về những row-group giao với Việt Nam. Lọc bằng `ST_Intersects` thay vì `bbox`
KHÔNG đẩy xuống được → tải hết 30 GB. Đây là điểm phải giữ nếu sửa câu SQL.

**Vì sao quét MỌI category chứ không chỉ 6 nhóm đang dùng.** Nguyên tắc C1 của E-DQ7c
(tách TRÍCH XUẤT khỏi CHÍNH SÁCH) đã trả giá một lần ở `overpass_poi.py`: nhóm crawl bị
đóng cứng vào lời gọi API nên đổi định nghĩa lớp = crawl lại cả nước. Ở đây một lần quét
là ~2–4 phút và ~vài trăm MB, nên raw giữ **nguyên `category` gốc** của Overture; việc
ánh xạ sang `poi_class` làm ở `poi_taxonomy.py` và chạy lại chỉ tốn vài giây.

**Raw là bất biến.** File ra mang tên release (`places_vn_bbox_<release>.parquet`) + một
sidecar `.meta.json` ghi bbox/SQL/số dòng/thời điểm quét, để `make freeze` (E-DQ10) băm
được và để biết số liệu đối chiếu sinh ra từ ảnh chụp nào.

⚠️ `VN_BBOX` là **cửa sổ quét**, KHÔNG phải bộ lọc lãnh thổ — nó chứa trọn Phnom Penh /
Viêng Chăn / Nam Ninh / Hải Nam (E-DQ7a). Clip lãnh thổ làm ở `build_poi.py` bằng polygon
`vn_boundary`, đúng chỗ OSM đang làm.

Chạy:
    PYTHONPATH=src python -m ev_siting.data.overture.fetch_places
    PYTHONPATH=src python -m ev_siting.data.overture.fetch_places --release 2026-06-17.0
    PYTHONPATH=src python -m ev_siting.data.overture.fetch_places --list-releases
"""
import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone

from ..osm.paths import VN_BBOX
from .paths import RELEASE, S3_REGION, ensure_dirs, fetch_meta, places_raw, places_url, releases_listing_url

#: Cột lấy về. Cố ý KHÔNG lấy `geometry` (WKB): place là điểm, `ST_X/ST_Y` đủ và giữ
#: parquet đọc được bằng pandas thuần, không cần geopandas (không có trong deps).
#: `sources` là list struct — trải phẳng thành 3 list song song để lưu được ở parquet
#: phẳng mà không mất thông tin ai cấp dòng này và cấp lúc nào.
SELECT_SQL = """
    id,
    ST_X(geometry)                                  AS lng,
    ST_Y(geometry)                                  AS lat,
    categories.primary                              AS category,
    categories.alternate                            AS category_alt,
    names.primary                                   AS name,
    confidence,
    operating_status,
    basic_category,
    addresses[1].freeform                           AS address,
    addresses[1].region                             AS region,
    list_transform(sources, s -> s.dataset)         AS src_datasets,
    list_transform(sources, s -> s.record_id)       AS src_record_ids,
    list_transform(sources, s -> s.update_time)     AS src_update_times
"""


def _connect(threads=4):
    """DuckDB + httpfs/spatial, trỏ vào region của bucket Overture."""
    import duckdb
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs; INSTALL spatial; LOAD spatial;")
    con.execute(f"SET s3_region='{S3_REGION}';")
    # bucket public: tắt mọi credential chain để không bị chặn bởi ~/.aws hỏng
    con.execute("SET s3_access_key_id=''; SET s3_secret_access_key='';")
    con.execute(f"SET threads={threads}; SET enable_progress_bar=false;")
    return con


def list_releases():
    """Danh sách release có trên bucket (mới nhất ở cuối)."""
    import requests
    r = requests.get(releases_listing_url(), timeout=60)
    r.raise_for_status()
    return sorted(set(re.findall(r"<Prefix>release/([^/<]+)/</Prefix>", r.text)))


def build_query(release, bbox, select_sql=SELECT_SQL):
    """Câu SELECT quét một release. `bbox` = (min_lat, min_lon, max_lat, max_lon)."""
    south, west, north, east = bbox
    # Lọc theo bbox.xmin/ymin (góc dưới-trái) chứ không phải giao hình học: place là
    # ĐIỂM nên xmin==xmax, ymin==ymax — hai cách tương đương, nhưng chỉ cách này nằm
    # trong thống kê parquet và được đẩy xuống row-group.
    return f"""
SELECT {select_sql.strip()}
FROM read_parquet('{places_url(release)}')
WHERE bbox.xmin BETWEEN {west} AND {east}
  AND bbox.ymin BETWEEN {south} AND {north}
"""


def fetch(release=RELEASE, bbox=VN_BBOX, threads=4, overwrite=False):
    """Quét → `data/raw/overture/places_vn_bbox_<release>.parquet`. Trả về dict meta."""
    ensure_dirs()
    out = places_raw(release)
    if out.exists() and not overwrite:
        print(f"[fetch] đã có {out.name} — bỏ qua (dùng --overwrite để quét lại)")
        return json.loads(fetch_meta(release).read_text()) if fetch_meta(release).exists() else None

    q = build_query(release, bbox)
    con = _connect(threads)
    t0 = time.time()
    print(f"[fetch] release={release} bbox={bbox} → {out}")
    print("[fetch] quét S3 (predicate pushdown theo bbox; ~2–5 phút)...", flush=True)
    # COPY ... TO: DuckDB stream thẳng ra đĩa, không materialise trong RAM Python.
    con.execute(f"COPY ({q}) TO '{out}' (FORMAT PARQUET, COMPRESSION ZSTD);")
    elapsed = round(time.time() - t0, 1)

    n = con.execute(f"SELECT count(*) FROM read_parquet('{out}')").fetchone()[0]
    meta = {
        "release": release,
        "source": places_url(release),
        "bbox_min_lat_min_lon_max_lat_max_lon": list(bbox),
        "n_rows": int(n),
        "bytes": out.stat().st_size,
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "elapsed_s": elapsed,
        "query": q.strip(),
        "note": "bbox là cửa sổ quét, KHÔNG phải bộ lọc lãnh thổ (E-DQ7a) — clip ở build_poi.py",
    }
    fetch_meta(release).write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    print(f"[fetch] {n:,} dòng · {meta['bytes'] / 1e6:.1f} MB · {elapsed}s")
    return meta


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--release", default=RELEASE, help=f"release Overture (mặc định {RELEASE})")
    ap.add_argument("--latest", action="store_true", help="dùng release mới nhất trên bucket")
    ap.add_argument("--list-releases", action="store_true", help="chỉ liệt kê release rồi thoát")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--overwrite", action="store_true", help="quét lại kể cả khi raw đã có")
    args = ap.parse_args(argv)

    if args.list_releases:
        for r in list_releases():
            print(r)
        return 0

    release = args.release
    if args.latest:
        release = list_releases()[-1]
        print(f"[fetch] --latest → {release}")
    fetch(release=release, threads=args.threads, overwrite=args.overwrite)
    return 0


if __name__ == "__main__":
    sys.exit(main())
