#!/usr/bin/env python3
"""fetch_communes.py — crawl + chuẩn hoá ranh giới/dân số cấp xã VNSDI.

Hai bước (subcommand):

  crawl   Lấy token tươi từ ``config.aspx`` -> query ArcGIS layer 2 theo TỪNG tỉnh
          (34 trang, resume qua file đã có), ``f=geojson``, ``outSR=4326``. Lưu thô
          -> ``data/raw/vnsdi/pages/<MATINH>.geojson`` + ``endpoint.json``. Token
          referer-bound + xoay vòng nên KHÔNG lưu; cái checksum được (E-DQ10) là các
          trang geojson — dữ liệu thật, không phải request.

  parse   Đọc các trang thô -> ``communes.parquet`` (geom WKB + thuộc tính) + geojson
          tâm xã (QA) + ``communes_report.json`` với cổng QA (đều FAIL được).

Chạy:
    PYTHONPATH=src python -m ev_siting.data.vnsdi.fetch_communes crawl
    PYTHONPATH=src python -m ev_siting.data.vnsdi.fetch_communes crawl --force
    PYTHONPATH=src python -m ev_siting.data.vnsdi.fetch_communes parse
"""
import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone

import pandas as pd
import requests
from shapely.geometry import shape
from shapely import wkb as shapely_wkb

from .paths import (CONFIG_URL, REFERER, SERVICE_PATH, OUT_SR, FIELDS,
                    EXPECTED_COMMUNES, EXPECTED_PROVINCES, RAW_DIR, PAGES_DIR,
                    ENDPOINT_JSON, INTERIM_DIR, COMMUNES_PARQUET,
                    COMMUNES_GEOJSON, COMMUNES_REPORT, ensure_dirs)

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept": "application/json", "Referer": REFERER}
PAGE_SIZE = 1000          # < maxRecordCount (3500); phân trang phòng tỉnh > PAGE_SIZE xã

# VN_BBOX (lat_min, lat_max, lng_min, lng_max) — đồng bộ match_official.VN_BBOX
VN_BBOX = (8.0, 23.6, 102.0, 110.0)
#: Hai ĐẶC KHU đảo xa nằm NGOÀI VN_BBOX một cách chính đáng (Hoàng Sa 111,7°E,
#: Trường Sa 117,2°E) — cùng khuôn allowlist "điểm neo ngoài" của vn_boundary.py.
#: Hoàng Sa danso=0 (không có hộ khẩu dân sự thường trú) là ĐÚNG, không phải lỗi.
OFFSHORE_ZONES = {"20333", "22736"}  # MAXA: Hoàng Sa (Đà Nẵng), Trường Sa (Khánh Hoà)


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _get(url, session, timeout=90, tries=4, **params):
    last = None
    for i in range(tries):
        try:
            r = session.get(url, headers=HEADERS, params=params, timeout=timeout)
            r.raise_for_status()
            return r
        except Exception as e:                       # noqa: BLE001 — crawl tolerant
            last = e
            time.sleep(2.0 * (i + 1))
    raise last


# ---------------------------------------------------------------------------
# crawl
# ---------------------------------------------------------------------------
def _fetch_token(session):
    """config.aspx trả JS thô: BASE_URL_CHINH="..."; tokenChinh="...". Lấy tươi mỗi lần
    (token referer-bound + xoay vòng nên KHÔNG bền để hardcode)."""
    r = _get(CONFIG_URL, session, timeout=30)
    txt = r.text
    def grab(name):
        m = re.search(rf'{name}\s*=\s*"([^"]+)"', txt)
        if not m:
            raise SystemExit(f"[vnsdi] config.aspx thiếu {name}: {txt[:200]!r}")
        return m.group(1)
    base = grab("BASE_URL_CHINH").rstrip("/")        # .../basemap/rest/services
    token = grab("tokenChinh")
    return base, token


def _query(session, base, token, where, offset=0):
    url = f"{base}/{SERVICE_PATH}/query"
    r = _get(url, session, where=where, outFields=",".join(FIELDS),
             returnGeometry="true", outSR=OUT_SR, f="geojson",
             resultOffset=offset, resultRecordCount=PAGE_SIZE, token=token)
    try:
        return r.json()
    except ValueError:
        raise SystemExit(f"[vnsdi] phản hồi không phải JSON (token hết hạn?): {r.text[:200]!r}")


def _count(session, base, token, where="1=1"):
    url = f"{base}/{SERVICE_PATH}/query"
    r = _get(url, session, where=where, returnCountOnly="true", f="json", token=token)
    return int(r.json().get("count", -1))


def run_crawl(force=False):
    ensure_dirs()
    s = requests.Session()
    base, token = _fetch_token(s)
    print(f"[vnsdi] base={base} service={SERVICE_PATH}")
    total = _count(s, base, token)
    print(f"[vnsdi] returnCountOnly (toàn quốc) = {total} (kỳ vọng {EXPECTED_COMMUNES})")

    # danh sách MATINH (không lấy geometry)
    r = _get(f"{base}/{SERVICE_PATH}/query", s, where="1=1", outFields="MATINH",
             returnGeometry="false", returnDistinctValues="true",
             orderByFields="MATINH", f="json", token=token)
    provinces = sorted({f["attributes"]["MATINH"] for f in r.json().get("features", [])})
    print(f"[vnsdi] {len(provinces)} tỉnh (kỳ vọng {EXPECTED_PROVINCES})")

    per_prov = {}
    for i, mt in enumerate(provinces, 1):
        dst = PAGES_DIR / f"{mt}.geojson"
        if dst.exists() and dst.stat().st_size > 0 and not force:
            n = len(json.loads(dst.read_text())["features"])
            per_prov[mt] = n
            print(f"  [{i:2d}/{len(provinces)}] {mt}: đã có ({n} xã) — bỏ qua")
            continue
        feats, offset = [], 0
        while True:
            gj = _query(s, base, token, where=f"MATINH='{mt}'", offset=offset)
            batch = gj.get("features", [])
            feats.extend(batch)
            if len(batch) < PAGE_SIZE:
                break
            offset += PAGE_SIZE
        fc = {"type": "FeatureCollection", "features": feats}
        dst.write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")
        per_prov[mt] = len(feats)
        print(f"  [{i:2d}/{len(provinces)}] {mt}: {len(feats)} xã -> {dst.name}")
        time.sleep(0.3)

    crawled = sum(per_prov.values())
    ENDPOINT_JSON.write_text(json.dumps({
        "retrieved_at": _now_iso(), "base_url": base, "service": SERVICE_PATH,
        "out_sr": OUT_SR, "fields": FIELDS, "server_count": total,
        "provinces": per_prov, "crawled_total": crawled,
        "note": "token referer-bound, không lưu; checksum là các trang geojson",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[vnsdi] crawl xong: {crawled} xã / {len(per_prov)} tỉnh -> {PAGES_DIR}")
    if crawled != total:
        print(f"[vnsdi] ⚠️ crawl {crawled} != server_count {total} — kiểm tra phân trang",
              file=sys.stderr)


# ---------------------------------------------------------------------------
# parse -> parquet + QA
# ---------------------------------------------------------------------------
def _check(report, name, ok, detail="", fatal=True):
    status = "PASS" if ok else ("FAIL" if fatal else "WARN")
    report["checks"].append({"name": name, "status": status, "detail": detail})
    print(f"  [{status}] {name} {('- ' + detail) if detail else ''}")
    return ok or not fatal


def _load_pages():
    rows = []
    for p in sorted(PAGES_DIR.glob("*.geojson")):
        fc = json.loads(p.read_text())
        for f in fc.get("features", []):
            a = f.get("properties", {})
            geom = f.get("geometry")
            g = shape(geom) if geom else None
            rows.append({
                "maxa": a.get("MAXA"), "tenxa": a.get("TENXA"),
                "matinh": a.get("MATINH"), "tentinh": a.get("TENTINH"),
                "dientich_km2": a.get("DIENTICH"), "danso": a.get("DANSO"),
                "ngayhieuluc": a.get("NGAYHIEULUC"), "ngayxuatban": a.get("NGAYXUATBAN"),
                "geom_wkb": g.wkb if g is not None else None,
                "geom_valid": bool(g is not None and g.is_valid and not g.is_empty),
            })
    return pd.DataFrame(rows)


def qa_gates(report, df):
    """Cổng QA cấp xã VNSDI — mỗi cổng canh một giả định, và FAIL được."""
    all_ok = True
    n = len(df)
    all_ok &= _check(report, "commune_count", n == EXPECTED_COMMUNES,
                     f"{n} xã (kỳ vọng {EXPECTED_COMMUNES})")

    dup = int(df["maxa"].duplicated().sum())
    all_ok &= _check(report, "maxa_unique", dup == 0 and df["maxa"].notna().all(),
                     f"{dup} MAXA trùng, {int(df['maxa'].isna().sum())} null")

    bad_geom = int((~df["geom_valid"]).sum())
    all_ok &= _check(report, "geometry_valid", bad_geom == 0,
                     f"{bad_geom} geometry rỗng/không hợp lệ")

    nprov = df["matinh"].nunique()
    all_ok &= _check(report, "province_count", nprov == EXPECTED_PROVINCES,
                     f"{nprov} tỉnh (kỳ vọng {EXPECTED_PROVINCES})")

    # dân số toàn quốc — chỉ kiểm HỢP LÝ (bắt lỗi đơn vị/nhân bản), KHÔNG neo chính xác.
    # ⚠️ Σdanso VNSDI = 113,6 M là số "quy mô dân số" ĐĂNG KÝ 2025 (nghị quyết sáp
    # nhập) — cao hơn WorldPop 2020 (97,57 M) ~16,5% và GSO 2024 (~101 M). Đây là lệch
    # NIÊN ĐẠI + ĐỊNH NGHĨA (đăng ký vs de-facto), tức lý do VNSDI dùng để KIỂM CHỨNG
    # HÌNH DẠNG phân bổ (tỉ lệ trong tỉnh), KHÔNG bao giờ làm control-total tái phân bổ
    # (giữ neo tổng WorldPop của E-DQ7e). Dải rộng chỉ để bắt lỗi ×1000.
    tot = float(df["danso"].fillna(0).sum())
    all_ok &= _check(report, "danso_total_plausible", 95e6 <= tot <= 120e6,
                     f"Σdanso = {tot:,.0f} (đăng ký 2025; +16,5% vs WorldPop 97,57 M)")

    # diện tích toàn quốc — gồm cả đặc khu đảo (Hoàng Sa/Trường Sa) nên > 331.000 km² đất
    area = float(df["dientich_km2"].fillna(0).sum())
    all_ok &= _check(report, "area_total_plausible", 320e3 <= area <= 360e3,
                     f"Σdiện tích = {area:,.0f} km² (VN đất ~331k + đặc khu đảo)")

    # reproject sanity: mọi tâm xã ĐẤT LIỀN nằm trong VN_BBOX; 2 đặc khu đảo xa được
    # allowlist (Hoàng Sa/Trường Sa) — chúng ngoài bbox một cách chính đáng.
    main = df[df["geom_valid"] & ~df["maxa"].isin(OFFSHORE_ZONES)]
    cen = main["geom_wkb"].map(lambda b: shapely_wkb.loads(b).representative_point())
    lat = cen.map(lambda p: p.y); lon = cen.map(lambda p: p.x)
    outb = int(((lat < VN_BBOX[0]) | (lat > VN_BBOX[1]) |
                (lon < VN_BBOX[2]) | (lon > VN_BBOX[3])).sum())
    all_ok &= _check(report, "centroids_in_vn_bbox", outb == 0,
                     f"{outb} tâm xã đất liền ngoài VN_BBOX "
                     f"(2 đặc khu đảo allowlist: reproject 3857->4326 OK)")

    # cờ dòng, không xoá: xã ĐẤT LIỀN danso<=0 (advisory). Hoàng Sa danso=0 là ĐÚNG
    # (không hộ khẩu dân sự) nên loại khỏi advisory qua allowlist đặc khu.
    zero = int(((df["danso"].fillna(0) <= 0) & ~df["maxa"].isin(OFFSHORE_ZONES)).sum())
    _check(report, "danso_positive", zero == 0,
           f"{zero} xã đất liền danso<=0 (đánh cờ, không xoá; Hoàng Sa=0 đã allowlist)",
           fatal=False)
    return all_ok


def run_parse():
    ensure_dirs()
    if not any(PAGES_DIR.glob("*.geojson")):
        raise SystemExit(f"thiếu trang thô ở {PAGES_DIR} — chạy `crawl` trước")
    df = _load_pages()
    print(f"[vnsdi] đọc {len(df)} xã từ {PAGES_DIR}")

    report = {"source": "VNSDI 34DVHC layer 2 (Địa phận cấp xã)",
              "retrieved": json.loads(ENDPOINT_JSON.read_text())["retrieved_at"]
              if ENDPOINT_JSON.exists() else None,
              "rows": len(df), "checks": []}
    print("\n[vnsdi] cổng QA:")
    ok = qa_gates(report, df)
    report["overall"] = "PASS" if ok else "FAIL"

    report["danso_total"] = float(df["danso"].fillna(0).sum())
    report["area_km2_total"] = float(df["dientich_km2"].fillna(0).sum())
    # tỉ số dùng cho E-DQ7f: VNSDI (đăng ký 2025) / WorldPop (UNadj 2020) = lệch mức.
    report["danso_vs_worldpop_unadj"] = round(report["danso_total"] / 97_569_444.24, 4)
    COMMUNES_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                               encoding="utf-8")
    if not ok:
        print(f"\n[FAIL] -> {COMMUNES_REPORT} (KHÔNG ghi {COMMUNES_PARQUET.name})",
              file=sys.stderr)
        sys.exit(1)

    df.to_parquet(COMMUNES_PARQUET, index=False)
    _write_centroids(df)
    print(f"\n[PASS] -> {COMMUNES_REPORT}")
    print(f"[vnsdi] -> {COMMUNES_PARQUET} ({len(df)} xã, "
          f"Σdanso {report['danso_total']/1e6:.2f}M, Σdiện tích {report['area_km2_total']:,.0f} km²)")
    return df


def _write_centroids(df):
    feats = []
    for r in df[df["geom_valid"]].itertuples():
        p = shapely_wkb.loads(r.geom_wkb).representative_point()
        feats.append({"type": "Feature",
                      "geometry": {"type": "Point", "coordinates": [p.x, p.y]},
                      "properties": {"maxa": r.maxa, "tenxa": r.tenxa,
                                     "tentinh": r.tentinh, "danso": r.danso,
                                     "dientich_km2": r.dientich_km2}})
    COMMUNES_GEOJSON.write_text(
        json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False),
        encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("crawl", help="crawl 34 tỉnh -> data/raw/vnsdi/pages")
    c.add_argument("--force", action="store_true", help="crawl lại kể cả trang đã có")
    sub.add_parser("parse", help="chuẩn hoá -> communes.parquet + QA")
    args = ap.parse_args()
    if args.cmd == "crawl":
        run_crawl(force=args.force)
    else:
        run_parse()


if __name__ == "__main__":
    main()
