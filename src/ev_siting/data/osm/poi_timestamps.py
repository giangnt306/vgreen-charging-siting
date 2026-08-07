#!/usr/bin/env python3
"""poi_timestamps.py — Gắn **ngày sửa cuối** (OSM `timestamp`) cho từng POI.

**Vì sao phải có module riêng.** `overpass_poi.py` gọi `out center tags;` — không có
`meta`, nên raw JSON **không mang timestamp**. Muốn có độ tươi ở mức đối tượng thì hoặc
crawl lại cả nước bằng `out meta` (≈30 phút, và **ghi đè raw đã freeze** — vi phạm
E-DQ10), hoặc đọc từ chính `vietnam-latest.osm.pbf` đã freeze. Chọn cách hai: dump PBF
của Geofabrik mang đầy đủ metadata (`version`/`timestamp`/`uid`), và nó đã nằm trong
`MANIFEST.json`.

**Giới hạn phải nêu khi báo cáo:** ảnh `.pbf` chụp *trước* lần crawl Overpass, nên POI
được tạo sau ngày chụp sẽ **không có** timestamp (cột `updated_at` = NaT). Tỉ lệ khuyết
được ghi vào báo cáo chứ không lấp bằng ngày crawl — lấp là bịa độ tươi.

Chạy:
    PYTHONPATH=src python -m ev_siting.data.osm.poi_timestamps
"""
import argparse
import json
import sys

import osmium
import pandas as pd

from .paths import INTERIM_DIR, PBF_PATH, POI_POINTS, ensure_dirs

POI_TIMESTAMPS = INTERIM_DIR / "osm_poi_timestamps.parquet"


class _TsHandler(osmium.SimpleHandler):
    """Thu `timestamp` cho đúng những (type, id) được hỏi — không giữ gì thừa."""

    def __init__(self, want):
        super().__init__()
        self.want = want                 # {"node": {...ids}, "way": {...}, "relation": {...}}
        self.out = {}                    # (type, id) -> iso timestamp

    def _take(self, kind, o):
        if o.id in self.want[kind]:
            ts = o.timestamp
            if ts is not None:
                self.out[(kind, o.id)] = ts.isoformat()

    def node(self, n): self._take("node", n)
    def way(self, w): self._take("way", w)
    def relation(self, r): self._take("relation", r)


def pbf_snapshot_date(pbf=PBF_PATH):
    """Ngày ảnh chụp của dump (`osmosis_replication_timestamp` trong header)."""
    try:
        hdr = osmium.io.Reader(str(pbf)).header()
        return hdr.get("osmosis_replication_timestamp") or None
    except Exception:
        return None


def build(pbf=PBF_PATH, poi_points=POI_POINTS):
    if not pbf.exists():
        raise SystemExit(f"thiếu {pbf} — chạy `make roads`/tải Geofabrik trước")
    poi = pd.read_parquet(poi_points, columns=["osm_type", "osm_id"])
    want = {k: set(poi.loc[poi["osm_type"] == k, "osm_id"].tolist())
            for k in ("node", "way", "relation")}
    print(f"[ts] hỏi {sum(len(v) for v in want.values()):,} đối tượng; stream {pbf.name}...")
    h = _TsHandler(want)
    h.apply_file(str(pbf))
    rows = [{"osm_type": t, "osm_id": i, "updated_at": ts} for (t, i), ts in h.out.items()]
    df = pd.DataFrame(rows, columns=["osm_type", "osm_id", "updated_at"])
    df["updated_at"] = pd.to_datetime(df["updated_at"], format="ISO8601", utc=True,
                                      errors="coerce")
    n_want = sum(len(v) for v in want.values())
    rep = {"pbf": pbf.name, "pbf_snapshot": pbf_snapshot_date(pbf),
           "n_requested": n_want, "n_resolved": int(len(df)),
           "pct_resolved": round(100 * len(df) / max(n_want, 1), 1)}
    return df, rep


def load():
    """Bảng timestamp đã build, hoặc None."""
    return pd.read_parquet(POI_TIMESTAMPS) if POI_TIMESTAMPS.exists() else None


def run():
    ensure_dirs()
    df, rep = build()
    df.to_parquet(POI_TIMESTAMPS, index=False)
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    print(f"[ts] -> {POI_TIMESTAMPS}")
    return rep


def main(argv=None):
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args(argv)
    run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
