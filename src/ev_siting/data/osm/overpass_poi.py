#!/usr/bin/env python3
"""overpass_poi.py — Trích POI Việt Nam từ Overpass API (OpenStreetMap).

Các nhóm POI (theo [problem-analysis.md] mục 2 #5 — sinh cầu sạc):
  - fuel       : amenity=fuel                         -> demand_h3.n_fuel
  - parking    : amenity=parking                      -> demand_h3.n_parking
  - mall       : shop=mall / shop=department_store    -> demand_h3.n_poi (TTTM)
  - apartments : building=apartments                  -> demand_h3.n_poi (chung cư)
  - retail     : shop=supermarket / amenity=marketplace -> demand_h3.n_poi

CƠ CHẾ:
  - Query `nwr[<tag>](bbox); out center tags;` -> node lấy lat/lon trực tiếp,
    way/relation lấy tâm (`center`).
  - Cả nước là vùng lớn -> chia đệ quy (quadtree): nếu 1 bbox trả về quá nhiều
    phần tử hoặc Overpass lỗi/timeout -> tách 4 góc, thu nhỏ dần tới khi vừa.
  - Lịch sự với server: 1 endpoint, backoff khi 429/504, nghỉ giữa các call.

Raw (bất biến): data/raw/osm/poi/<category>.json  (list phần tử OSM đã khử trùng).
Chạy:
    PYTHONPATH=src python -m ev_siting.data.osm.overpass_poi              # tất cả nhóm
    PYTHONPATH=src python -m ev_siting.data.osm.overpass_poi --only fuel parking
"""
import argparse
import json
import sys
import time

import requests

from .paths import POI_RAW_DIR, VN_BBOX, ensure_dirs

ENDPOINT = "https://overpass-api.de/api/interpreter"
# Overpass chặn UA mặc định của requests (trả 406) -> khai báo UA rõ ràng.
HEADERS = {"User-Agent": "vgreen-charging-siting/0.1 (OSM POI extract; contact: giangnt306w@gmail.com)"}

# category -> danh sách bộ lọc tag Overpass (OR trong cùng nhóm)
CATEGORIES = {
    "fuel": ['["amenity"="fuel"]'],
    "parking": ['["amenity"="parking"]'],
    "mall": ['["shop"="mall"]', '["shop"="department_store"]'],
    "apartments": ['["building"="apartments"]'],
    "retail": ['["shop"="supermarket"]', '["amenity"="marketplace"]'],
}

# Ngưỡng tách bbox: >= CAP phần tử -> nghi ngờ bị cắt/quá tải -> chia 4.
SPLIT_CAP = 40000
# Không tách nhỏ hơn cạnh này (độ) để tránh đệ quy vô hạn ở ổ dày đặc.
MIN_TILE_DEG = 0.05
OVERPASS_TIMEOUT = 180          # timeout khai báo TRONG query (giây)
HTTP_TIMEOUT = 300              # timeout HTTP phía client
PAUSE_S = 1.0                   # nghỉ giữa 2 request thành công


def build_query(filters, bbox):
    south, west, north, east = bbox
    body = "".join(f"  nwr{f}({south},{west},{north},{east});\n" for f in filters)
    return f"[out:json][timeout:{OVERPASS_TIMEOUT}];\n(\n{body});\nout center tags;"


def _post(query, tries=4):
    """POST tới Overpass với backoff. Trả về JSON hoặc raise sau khi hết lượt."""
    for attempt in range(tries):
        try:
            r = requests.post(ENDPOINT, data={"data": query},
                              headers=HEADERS, timeout=HTTP_TIMEOUT)
        except requests.RequestException as e:
            wait = 5 * (attempt + 1)
            print(f"      ! network {type(e).__name__}; chờ {wait}s...", file=sys.stderr)
            time.sleep(wait)
            continue
        if r.status_code == 200:
            try:
                data = r.json()
            except ValueError as e:
                raise RuntimeError(f"Overpass HTTP 200 nhưng JSON hỏng: {e}") from e
            # Overpass hay báo timeout/runtime qua HTTP 200 + `remark`; payload
            # đó không complete nên phải vào nhánh quadtree, không được accept.
            if not isinstance(data, dict) or data.get("remark"):
                raise RuntimeError(f"Overpass HTTP 200 nhưng incomplete: {data.get('remark') if isinstance(data, dict) else 'payload lạ'}")
            return data
        if r.status_code in (429, 504, 502, 503):  # rate-limit / quá tải -> lùi
            wait = 10 * (attempt + 1)
            print(f"      ! HTTP {r.status_code}; chờ {wait}s...", file=sys.stderr)
            time.sleep(wait)
            continue
        raise RuntimeError(f"Overpass HTTP {r.status_code}: {r.text[:200]}")
    raise RuntimeError("Overpass thất bại sau nhiều lần thử")


def _quadrants(bbox):
    s, w, n, e = bbox
    mlat, mlon = (s + n) / 2, (w + e) / 2
    return [(s, w, mlat, mlon), (s, mlon, mlat, e),
            (mlat, w, n, mlon), (mlat, mlon, n, e)]


def fetch_category(filters, bbox, depth=0):
    """Đệ quy quadtree: trả về dict {(*type*, id): element} đã khử trùng."""
    indent = "  " * (depth + 1)
    height = bbox[2] - bbox[0]
    try:
        data = _post(build_query(filters, bbox))
        els = data.get("elements", [])
    except RuntimeError as e:
        els = None  # coi như quá tải -> ép tách nếu còn tách được
        print(f"{indent}! {e} -> thử tách", file=sys.stderr)

    too_big = els is None or len(els) >= SPLIT_CAP
    can_split = height / 2 >= MIN_TILE_DEG
    if too_big and can_split:
        acc = {}
        for q in _quadrants(bbox):
            acc.update(fetch_category(filters, q, depth + 1))
        return acc

    if els is None:  # không tách được nữa mà vẫn lỗi -> bỏ ô, ghi cảnh báo
        print(f"{indent}!! bỏ ô {bbox} (lỗi & đã tối thiểu)", file=sys.stderr)
        return {}

    print(f"{indent}bbox {tuple(round(x, 2) for x in bbox)} -> {len(els)} phần tử")
    time.sleep(PAUSE_S)
    return {(el["type"], el["id"]): el for el in els}


def _coord(el):
    """Lat/lon của phần tử: node có lat/lon; way/relation có center."""
    if el["type"] == "node":
        return el.get("lat"), el.get("lon")
    c = el.get("center") or {}
    return c.get("lat"), c.get("lon")


def run(only=None):
    ensure_dirs()
    cats = only or list(CATEGORIES)
    summary = {}
    for cat in cats:
        filters = CATEGORIES[cat]
        print(f"[{cat}] Overpass nwr {filters} trên toàn VN...")
        elements = fetch_category(filters, VN_BBOX)
        # chỉ giữ phần tử có toạ độ hợp lệ
        rows = []
        for el in elements.values():
            lat, lon = _coord(el)
            if lat is None or lon is None:
                continue
            tags = el.get("tags", {})
            rows.append({
                "osm_type": el["type"], "osm_id": el["id"],
                "category": cat, "lat": lat, "lng": lon,
                "name": tags.get("name", ""),
                "tags": tags,
            })
        out = POI_RAW_DIR / f"{cat}.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False)
        summary[cat] = len(rows)
        print(f"[{cat}] -> {len(rows)} POI có toạ độ  ->  {out}")
    print("\nTổng kết:", json.dumps(summary, ensure_ascii=False))
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", choices=list(CATEGORIES),
                    help="Chỉ crawl các nhóm này (mặc định: tất cả)")
    args = ap.parse_args()
    run(only=args.only)
