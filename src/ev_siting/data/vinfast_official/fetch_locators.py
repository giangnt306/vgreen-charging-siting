#!/usr/bin/env python3
"""fetch_locators.py — crawl + chuan hoa nguon CHINH THUC vinfastauto.com.

Nguon first-party (nha san xuat), dung lam nguon XAC MINH doi chieu evcs.vn.
Ba buoc (subcommand):

  bulk    Tai 1 file tinh tren CDN (meta -> full) -> loc tram sac O TO (type 2444)
          -> chuan hoa registry `official_stations.parquet`. 1 request, nhanh.
            CDN: https://static-cms-prod.vinfastauto.com/locators/locators-meta.json
                 -> meta["full"] (vd locators-15.json.gz) — CDN tra JSON da giai nen.

  detail  Crawl endpoint per-station /vn_vi/get-locator/<entity_id> (resume qua .done)
          -> luu raw data/raw/vinfast_official/details/<store_id>.json. Endpoint tra
          cau truc kieu OCPI: evses[].connectors[] (chuan cam CCS2/Type2 — thu evcs.vn
          KHONG lo), va admin (province/district/commune) per tram.

  parse   Doc raw details -> `official_connectors.parquet` (1 dong/connector) +
          `official_admin.parquet` (1 dong/tram: province/district/commune).

Chay:
    PYTHONPATH=src python -m ev_siting.data.vinfast_official.fetch_locators bulk
    PYTHONPATH=src python -m ev_siting.data.vinfast_official.fetch_locators detail --codes-file <f> --sleep 0.3
    PYTHONPATH=src python -m ev_siting.data.vinfast_official.fetch_locators parse
"""
import argparse
import gzip
import json
import sys
import time
from datetime import datetime, timezone

import pandas as pd
import requests

from .paths import (
    ADMIN_PARQUET,
    BULK_JSON,
    CONNECTORS_PARQUET,
    DETAIL_DIR,
    META_JSON,
    RAW_DIR,
    STATIONS_PARQUET,
    ensure_dirs,
)

CDN_BASE = "https://static-cms-prod.vinfastauto.com/locators"
SITE_BASE = "https://vinfastauto.com/vn_vi"
CAR_TYPE = "2444"                       # category_slug = car_charging_station
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept": "application/json"}


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _get_json(url, session, timeout=60, tries=3):
    """GET -> JSON. CDN co the tra gzip theo Content-Encoding (requests tu giai)
    hoac body gzip tho -> thu ca hai. Retry co backoff."""
    last = None
    for i in range(tries):
        try:
            r = session.get(url, headers=HEADERS, timeout=timeout)
            r.raise_for_status()
            try:
                return r.json()
            except ValueError:
                return json.loads(gzip.decompress(r.content).decode("utf-8"))
        except Exception as e:                      # noqa: BLE001 — crawl tolerant
            last = e
            time.sleep(1.5 * (i + 1))
    raise last


# ---------------------------------------------------------------------------
# bulk
# ---------------------------------------------------------------------------
def _norm_bool(v):
    """status tho co the la "1"/True/"0"/False -> bool."""
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("1", "true", "yes")


def _to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def run_bulk():
    ensure_dirs()
    s = requests.Session()
    meta = _get_json(f"{CDN_BASE}/locators-meta.json", s, timeout=30)
    META_JSON.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    fname = meta.get("full")
    if not fname:
        raise SystemExit(f"meta thieu key 'full': {meta}")
    print(f"[bulk] meta generation={meta.get('generation')} count={meta.get('count')} full={fname}")

    payload = _get_json(f"{CDN_BASE}/{fname}", s, timeout=120)
    items = payload["data"] if isinstance(payload, dict) and "data" in payload else payload
    items = [x for x in items if isinstance(x, dict)]
    BULK_JSON.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    print(f"[bulk] tai {len(items):,} locators (moi category) -> {BULK_JSON.name}")

    car = [x for x in items if str(x.get("type")) == CAR_TYPE]
    fetched = _now_iso()
    rows = [{
        "store_id": x.get("store_id"),          # == station_code evcs (khoa join)
        "entity_id": x.get("entity_id"),         # dung cho endpoint detail
        "code": x.get("code"),                   # vfc_<store_id>
        "name": x.get("name"),
        "address": x.get("address"),
        "lat": _to_float(x.get("lat")),
        "lng": _to_float(x.get("lng")),
        "charging_status": x.get("charging_status"),   # ACTIVE/INACTIVE/BUSY/UNAVAILABLE/OUTOFSERVICE
        "charging_publish": bool(x.get("charging_publish")),
        "access_type": x.get("access_type"),           # Public/Restricted
        "status": _norm_bool(x.get("status")),
        "party_id": x.get("party_id"),
        "parking_fee": bool(x.get("parking_fee")),
        "hotline": x.get("hotline"),
        "province_id": x.get("province_id"),
        "charging_avaiable_date": x.get("charging_avaiable_date"),
        "source_generation": meta.get("generation"),
        "fetched_at": fetched,
    } for x in car]
    df = pd.DataFrame(rows)
    n_dup = int(df["store_id"].duplicated().sum())
    if n_dup:
        df = df.drop_duplicates("store_id", keep="first")
    df.to_parquet(STATIONS_PARQUET, index=False)

    print(f"[bulk] tram sac oto (type {CAR_TYPE}): {len(df):,}  (dup store_id da bo: {n_dup})")
    print(f"       charging_status: {df.charging_status.value_counts(dropna=False).to_dict()}")
    print(f"       access_type    : {df.access_type.value_counts(dropna=False).to_dict()}")
    print(f"-> {STATIONS_PARQUET.relative_to(RAW_DIR.parents[2])}")
    return df


# ---------------------------------------------------------------------------
# detail
# ---------------------------------------------------------------------------
def _load_done(done_path):
    if done_path.exists():
        return set(done_path.read_text(encoding="utf-8").split())
    return set()


def run_detail(codes_file=None, only=None, sleep=0.3, overwrite=False):
    ensure_dirs()
    if not STATIONS_PARQUET.exists():
        raise SystemExit("thieu official_stations.parquet — chay `bulk` truoc")
    reg = pd.read_parquet(STATIONS_PARQUET)
    eid = dict(zip(reg.store_id, reg.entity_id))          # store_id -> entity_id

    if codes_file:
        want = [c.strip() for c in open(codes_file, encoding="utf-8") if c.strip()]
    elif only:
        want = list(only)
    else:
        want = list(reg.store_id)                          # mac dinh: toan bo registry
    # chi giu store_id co trong registry (co entity_id de goi endpoint)
    codes = [c for c in want if c in eid]
    skipped = len(want) - len(codes)

    done_path = DETAIL_DIR.parent / "details.done"
    done = set() if overwrite else _load_done(done_path)
    todo = [c for c in codes if c not in done]
    print(f"[detail] yeu cau={len(want)} | co trong registry={len(codes)} "
          f"(bo {skipped} khong khop) | da xong={len(codes)-len(todo)} | can crawl={len(todo)}")

    s = requests.Session()
    n_ok = n_err = 0
    with open(done_path, "a", encoding="utf-8") as df_done:
        for i, code in enumerate(todo, 1):
            url = f"{SITE_BASE}/get-locator/{eid[code]}"
            try:
                resp = _get_json(url, s, timeout=30)
                data = resp.get("data", resp) if isinstance(resp, dict) else resp
                (DETAIL_DIR / f"{code}.json").write_text(
                    json.dumps(data, ensure_ascii=False), encoding="utf-8")
                df_done.write(code + "\n"); df_done.flush()
                n_ok += 1
            except Exception as e:                          # noqa: BLE001
                n_err += 1
                print(f"    !! {code} loi: {e}", file=sys.stderr)
            if i % 200 == 0:
                print(f"    ...{i}/{len(todo)}  ok={n_ok} err={n_err}", flush=True)
            time.sleep(sleep)
    print(f"[detail] xong: ok={n_ok} err={n_err} -> {DETAIL_DIR}")


# ---------------------------------------------------------------------------
# parse
# ---------------------------------------------------------------------------
def _iter_details():
    for p in sorted(DETAIL_DIR.glob("*.json")):
        try:
            yield p.stem, json.loads(p.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue


def run_parse():
    ensure_dirs()
    conn_rows, admin_rows = [], []
    n = 0
    for store_id, det in _iter_details():
        n += 1
        d = det.get("data", det) if isinstance(det, dict) else {}
        if not isinstance(d, dict):
            continue
        admin_rows.append({
            "store_id": store_id,
            "province": d.get("province"),
            "district": d.get("district"),
            "commune": d.get("commune"),
            "city": d.get("city"),
            "state": d.get("state"),
            "country": d.get("country"),
        })
        for ei, evse in enumerate(d.get("evses") or []):
            if not isinstance(evse, dict):
                continue
            for c in evse.get("connectors") or []:
                if not isinstance(c, dict):
                    continue
                w = c.get("max_electric_power")
                conn_rows.append({
                    "store_id": store_id,
                    "evse_idx": ei,
                    "connector_id": c.get("id"),
                    "standard": c.get("standard"),        # vd IEC_62196_T2_COMBO (CCS2)
                    "format": c.get("format"),
                    "power_type": c.get("power_type"),     # AC/DC
                    "max_electric_power_kw": round(w / 1000, 1) if isinstance(w, (int, float)) else None,
                    "max_voltage": c.get("max_voltage"),
                    "max_amperage": c.get("max_amperage"),
                    "physical_reference": evse.get("physical_reference"),
                    "last_updated": c.get("last_updated"),
                })
    admin = pd.DataFrame(admin_rows)
    conn = pd.DataFrame(conn_rows)
    admin.to_parquet(ADMIN_PARQUET, index=False)
    conn.to_parquet(CONNECTORS_PARQUET, index=False)
    print(f"[parse] doc {n:,} file detail")
    print(f"        admin      -> {ADMIN_PARQUET.name}  ({len(admin):,} tram)")
    print(f"        connectors -> {CONNECTORS_PARQUET.name}  ({len(conn):,} connector, "
          f"{conn.store_id.nunique() if len(conn) else 0} tram co connector)")
    if len(conn):
        print(f"        standard   : {conn.standard.value_counts(dropna=False).to_dict()}")
        print(f"        power_type : {conn.power_type.value_counts(dropna=False).to_dict()}")
    return admin, conn


def main():
    ap = argparse.ArgumentParser(description="crawl + chuan hoa nguon chinh thuc vinfastauto.com")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("bulk", help="tai + chuan hoa registry tram sac oto")
    dp = sub.add_parser("detail", help="crawl endpoint per-station (resume)")
    dp.add_argument("--codes-file", help="file store_id (1/dong) can crawl; mac dinh: toan bo registry")
    dp.add_argument("--sleep", type=float, default=0.3, help="giay nghi giua request")
    dp.add_argument("--overwrite", action="store_true", help="bo qua .done, crawl lai")
    sub.add_parser("parse", help="raw details -> official_connectors + official_admin parquet")
    args = ap.parse_args()

    if args.cmd == "bulk":
        run_bulk()
    elif args.cmd == "detail":
        run_detail(codes_file=args.codes_file, sleep=args.sleep, overwrite=args.overwrite)
    elif args.cmd == "parse":
        run_parse()


if __name__ == "__main__":
    main()
