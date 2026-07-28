#!/usr/bin/env python3
"""
evcs_enumerate.py — Liệt kê TOÀN BỘ mã trạm evcs.vn qua endpoint /search.

Vì sao cần: sitemap chỉ có 702 trang khu vực (không có mã trạm); mỗi truy vấn
/search chỉ trả 50 trạm GẦN NHẤT quanh 1 toạ độ (cap cứng = 50). Crawler tạo lưới
địa lý phủ Việt Nam làm tâm truy vấn, rồi "phủ đĩa" tham lam:

  POST https://evcs.vn/search?t=<nonce16>   body {latitude, longitude, search:true}
    -> {code:200000, data:[ {locationId:'C.HNO0317', latitude, longitude,
                             distance(km), stationName, evse, totalCharging, ...}, ... ]}

  Bất biến phủ: 1 truy vấn tại q trả 50 trạm gần nhất, trạm thứ 50 cách q = R_q.
  => MỌI trạm trong bán kính R_q quanh q đều đã được trả về. Nên bỏ qua seed nào
  nằm trong đĩa (q, R_q) đã truy vấn -> vùng thưa R_q lớn nên rất ít lệnh.

Kết quả:
  - evcs_stations.csv : 1 dòng / trạm (mã + toạ độ + tên + totalCharging...)
  - evcs_codes.txt    : danh sách mã (nạp cho evcs_scrape.py lấy time-series)
  - evcs_enum_ckpt.json: checkpoint (đĩa đã truy vấn) để resume.

Chạy:  ./.venv/bin/python evcs_enumerate.py            # quét toàn Việt Nam
       ./.venv/bin/python evcs_enumerate.py --bbox 20.9 21.1 105.7 105.9 --max-queries 30  # test
"""

import argparse
import csv
import json
import math
import os
import time

import numpy as np
from playwright.sync_api import sync_playwright

from .paths import CATALOG_DIR

BASE = "https://evcs.vn"
# Nhiều trang trạm để bootstrap qua Cloudflare — nếu 1 URL chết thì thử URL kế.
BOOT_URLS = [
    f"{BASE}/tram-sac-vinfast-nguyen-van-chenh-thon-dao-xuyen-xa-bat-trang-c.hno16154.html",
    f"{BASE}/",
]
BOOT = BOOT_URLS[0]  # tương thích ngược
# Geographic bounds of Vietnam.  Discovery deliberately has no dependency on
# the project's gold dataset or any other station catalogue.
VN_BBOX = (8.0, 23.6, 102.0, 110.0)  # lat_min, lat_max, lng_min, lng_max

# fetch /search TRONG trang (same-origin, tự qua Cloudflare). Trả 'data' thô.
# type: 'cs'=VinFast (mặc định), 'other'=hãng khác, 'bss'=đổi pin (thêm &type=...).
SEARCH_JS = r"""
async ([lat,lng,type]) => {
  const nonce=(n)=>{let c="";const a="abcdefghijklmnopqrstuvwxyz0123456789";
    for(let i=0;i<n;i++)c+=a.charAt(Math.floor(36*Math.random()));return c;};
  let url = "/search?t="+nonce(16);
  const body = {latitude:lat, longitude:lng};
  if (type && type !== 'cs') url += "&type="+type; else body.search = true;
  const r = await fetch(url, {
    method:"POST", headers:{"Content-Type":"application/json"},
    body: JSON.stringify(body)
  });
  const j = await r.json();
  if (!j || j.code !== 200000 || !Array.isArray(j.data)) return {err: (j&&j.code)||r.status};
  return {data: j.data.map(s => ({
    code:s.locationId, name:s.stationName, addr:s.stationAddress, lat:s.latitude,
    lng:s.longitude, dist:s.distance, evse:s.evse, tot:s.totalCharging,
    verified:s.verified, depot:s.depotStatus,
    // evsePowers = cấu hình súng sạc: [{type:<W>, totalEvse:<số súng>, numberOfAvailableEvse:<đang trống>}]
    // -> nguồn DUY NHẤT của num_connectors / power / current_type / connector_types (mục SCHEMA_CONTRACT).
    evsePowers:s.evsePowers,
    workingTime:s.workingTimeDescription, isPublic:s.isPublic, isFreeParking:s.isFreeParking,
    nBattery:s.numberBattery, nBatteryAvail:s.numberBatteryAvailable   // chỉ BSS (đổi pin)
  }))};
}
"""

# evse_powers = JSON thô của evsePowers (giữ nguyên vẹn để build_master dẫn xuất cột schema).
FIELDS = [
    "code",
    "name",
    "addr",
    "lat",
    "lng",
    "evse",
    "tot",
    "verified",
    "depot",
    "evse_powers",
    "working_time",
    "is_public",
    "is_free_parking",
    "n_battery",
    "n_battery_avail",
]


def rec_from_search(s):
    """1 bản ghi /search (đã map trong SEARCH_JS) -> dict theo FIELDS của catalog."""
    return {
        "code": s.get("code"),
        "name": s.get("name"),
        "addr": s.get("addr"),
        "lat": s.get("lat"),
        "lng": s.get("lng"),
        "evse": s.get("evse"),
        "tot": s.get("tot"),
        "verified": s.get("verified"),
        "depot": s.get("depot"),
        "evse_powers": json.dumps(s.get("evsePowers") or [], ensure_ascii=False),
        "working_time": s.get("workingTime"),
        "is_public": s.get("isPublic"),
        "is_free_parking": s.get("isFreeParking"),
        "n_battery": s.get("nBattery"),
        "n_battery_avail": s.get("nBatteryAvail"),
    }


def haversine_km(lat1, lng1, lat2, lng2):
    """Vectorised (lat1,lng1 scalar; lat2,lng2 arrays) -> km."""
    R = 6371.0088
    p1 = math.radians(lat1)
    p2 = np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlmb = np.radians(lng2 - lng1)
    a = np.sin(dphi / 2) ** 2 + math.cos(p1) * np.cos(p2) * np.sin(dlmb / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


def make_seed_grid(bbox, step):
    """Make a staggered geographic scan grid without external seed data."""
    lat0, lat1, lng0, lng1 = bbox
    if step <= 0:
        raise ValueError("grid step must be greater than zero")
    latitudes = np.arange(lat0, lat1 + step * 0.01, step)
    longitudes = np.arange(lng0, lng1 + step * 0.01, step)
    return [
        (float(lat), float(lng + (step / 2 if row % 2 else 0)))
        for row, lat in enumerate(latitudes)
        for lng in longitudes
        if lng0 <= lng + (step / 2 if row % 2 else 0) <= lng1
    ]


def bootstrap(page, ctx, nav_gate):
    nav_gate["on"] = True  # cho phép điều hướng khi bootstrap
    ok = False
    for url in BOOT_URLS:  # thử lần lượt các URL bootstrap
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            print(f"    ! bootstrap {url} lỗi ({str(e)[:50]}); thử URL khác...")
            continue
        for _ in range(45):
            if any(c["name"] == "cf_clearance" for c in ctx.cookies()):
                break
            page.wait_for_timeout(1000)
        ok = any(c["name"] == "cf_clearance" for c in ctx.cookies())
        if ok:
            break
    print("    cf_clearance:", "OK" if ok else "CHƯA CÓ")
    nav_gate["on"] = False  # sau đó KHÓA: chặn interstitial/redirect phá context


def run_enrich(args):
    """Bổ sung cột mới cho các trạm ĐÃ BIẾT (KHÔNG discovery).

    Truy vấn /search tại toạ độ từng trạm mục tiêu; mỗi lần trả tối đa 50 trạm lân cận
    -> lấp dữ liệu cho mọi trạm trong tập mục tiêu rồi BỎ QUA trạm đã lấy. Nhờ vậy số
    truy vấn ~ (số trạm / mật độ), KHÔNG bùng nổ 1-truy-vấn-mỗi-trạm như discovery.
    Ghi tăng dần (atomic temp+replace) nên resume được nếu gián đoạn.
    """
    codes_path = os.path.splitext(args.out)[0] + "_codes.txt"
    failed_path = os.path.splitext(args.out)[0] + "_failed.txt"

    # 1) toạ độ mục tiêu (lọc theo --type qua cột 'tab' nếu catalog có)
    targets, order = {}, []
    with open(args.enrich_from, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            code = row.get("code")
            if not code:
                continue
            tab = row.get("tab")
            if tab not in (None, "", args.type):
                continue
            try:
                lat, lng = float(row["lat"]), float(row["lng"])
            except (TypeError, ValueError, KeyError):
                continue
            if code not in targets:
                targets[code] = (lat, lng)
                order.append(code)
    print(f"[0] {len(targets)} trạm mục tiêu (type={args.type}) từ {args.enrich_from}")

    # 2) resume: giữ nguyên hàng đã có trong --out; trạm CÓ evse_powers coi như đã lấy
    enriched, seen = {}, set()
    if not args.overwrite and os.path.exists(args.out):
        for row in csv.DictReader(open(args.out, encoding="utf-8")):
            c = row.get("code")
            if not c:
                continue
            enriched[c] = {k: row.get(k, "") for k in FIELDS}
            if (row.get("evse_powers") or "").strip() not in ("", "[]"):
                seen.add(c)
        print(f"    resume: {len(enriched)} hàng trong {args.out}, {len(seen)} đã có evse_powers")

    def flush_out():
        tmp = args.out + ".tmp"
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
            w.writeheader()
            for rrow in enriched.values():
                w.writerow(rrow)
        os.replace(tmp, args.out)

    n_queries, t0 = 0, time.time()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context(
            locale="vi-VN", user_agent="Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:152.0) Gecko/20100101 Firefox/152.0"
        )
        ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>false})")
        page = ctx.new_page()
        nav_gate = {"on": True}

        def _guard(route):
            req = route.request
            if not nav_gate["on"] and req.is_navigation_request() and req.frame == page.main_frame:
                return route.abort()
            return route.continue_()

        ctx.route("**/*", _guard)
        print("[1] Bootstrap qua Cloudflare...")
        bootstrap(page, ctx, nav_gate)

        def query_point(lat, lng, max_attempts=6):
            for attempt in range(max_attempts):
                try:
                    res = page.evaluate(SEARCH_JS, [lat, lng, args.type])
                    if isinstance(res, dict) and "data" in res:
                        return res["data"]
                except Exception:
                    pass
                try:
                    bootstrap(page, ctx, nav_gate)
                except Exception:
                    pass
                time.sleep(min(3 + attempt * 3, 15))
            return None

        print(f"[2] Bổ sung (sleep={args.sleep}s)...")
        failed = []
        for i, code in enumerate(order):
            if code in seen:
                continue
            lat, lng = targets[code]
            data = query_point(lat, lng)
            n_queries += 1
            if data is None:
                failed.append(code)  # F6: lỗi không được coi là đã enrich
                continue
            for s in data:
                c = s.get("code")
                if c:
                    enriched[c] = rec_from_search(s)
                    seen.add(c)  # đánh dấu đã lấy (kể cả evsePowers rỗng)
            if n_queries % 25 == 0:
                flush_out()
                rate = n_queries / max(time.time() - t0, 1e-9)
                remaining = sum(1 for c in order if c not in seen)
                print(
                    f"    q={n_queries}  mục {i + 1}/{len(order)}  "
                    f"đã lấp={len(targets) - remaining}/{len(targets)}  còn≈{remaining}  ({rate:.2f} q/s)"
                )
            time.sleep(args.sleep + np.random.uniform(0, args.sleep))
            if args.max_queries and n_queries >= args.max_queries:
                print("    [dừng: đạt --max-queries]")
                break

        # Pass 2 cho lỗi transient (Cloudflare/socket). Còn lỗi được ghi riêng để
        # resume lần sau; tuyệt đối không `seen.add(code)` khi chưa có response.
        # Một truy vấn /search trả về MỌI trạm quanh điểm, nên trạm từng lỗi có thể
        # đã được điểm lân cận lấp -> lọc lại theo `seen` để không retry/báo lỗi oan.
        failed = [c for c in failed if c not in seen]
        if failed and not (args.max_queries and n_queries >= args.max_queries):
            print(f"[2b] Retry enrich cho {len(failed)} trạm từng lỗi...")
            still_failed = []
            for code in failed:
                if code in seen:  # điểm retry trước đó đã lấp trạm này
                    continue
                lat, lng = targets[code]
                data = query_point(lat, lng, max_attempts=8)
                n_queries += 1
                if data is None:
                    still_failed.append(code)
                    continue
                for s in data:
                    c = s.get("code")
                    if c:
                        enriched[c] = rec_from_search(s)
                        seen.add(c)
                time.sleep(args.sleep + np.random.uniform(0, args.sleep))
            failed = still_failed

        browser.close()

    flush_out()
    with open(codes_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(enriched)) + "\n")
    with open(failed_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(set(failed))) + ("\n" if failed else ""))
    got = sum(1 for c in targets if c in enriched and (enriched[c].get("evse_powers") or "") not in ("", "[]"))
    print(f"[3] Xong: {n_queries} truy vấn; {len(enriched)} hàng -> {args.out}")
    print(f"    {got}/{len(targets)} trạm mục tiêu có evse_powers")
    if failed:
        print(f"    ! {len(failed)} trạm lỗi -> {failed_path} (chưa được đánh dấu seen)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(CATALOG_DIR, "evcs_stations.csv"))
    ap.add_argument(
        "--type",
        choices=["cs", "other", "bss"],
        default="cs",
        help="cs=VinFast (mặc định), other=hãng khác, bss=đổi pin",
    )
    ap.add_argument(
        "--bbox",
        nargs=4,
        type=float,
        metavar=("LATMIN", "LATMAX", "LNGMIN", "LNGMAX"),
        help="Vùng quét: lat_min lat_max lng_min lng_max (mặc định: toàn Việt Nam)",
    )
    ap.add_argument(
        "--grid-step", type=float, default=0.20, help="Khoảng cách lưới seed theo độ (mặc định 0.20, ~22 km)"
    )
    ap.add_argument("--max-queries", type=int, default=0, help="Dừng sau N truy vấn (0=không giới hạn)")
    ap.add_argument("--sleep", type=float, default=0.35, help="Nghỉ giữa 2 truy vấn (giây)")
    ap.add_argument("--no-resume", action="store_true")
    ap.add_argument("--overwrite", action="store_true", help="Bắt đầu catalog mới: ghi đè CSV và checkpoint của --out")
    ap.add_argument(
        "--enrich-from",
        metavar="CATALOG_CSV",
        help="CHẾ ĐỘ BỔ SUNG (không discovery): nạp toạ độ các trạm ĐÃ BIẾT từ "
        "CATALOG_CSV (cột code/lat/lng[/tab]) rồi truy vấn /search tại từng toạ độ "
        "để lấp cột mới (evse_powers…) cho ĐÚNG các station_code đó — bounded, "
        "bỏ qua trạm đã lấy nên rẻ hơn discovery nhiều. Resume theo --out.",
    )
    args = ap.parse_args()

    if args.enrich_from:
        run_enrich(args)
        return

    ckpt_path = args.out + ".ckpt.json"
    codes_path = os.path.splitext(args.out)[0] + "_codes.txt"

    bbox = tuple(args.bbox) if args.bbox else VN_BBOX
    # Tuple third element means "query even if it falls in an existing coverage
    # disk".  Newly found stations use this mode to expand past the 50-result
    # boundary of the query that found them.
    seeds = [(lat, lng, False) for lat, lng in make_seed_grid(bbox, args.grid_step)]
    print(f"[0] {len(seeds)} điểm seed độc lập, bbox={bbox}, step={args.grid_step}°")

    # resume state
    q_lat, q_lng, q_r = [], [], []  # đĩa đã truy vấn (tâm + bán kính km)
    found = {}  # code -> record
    if not args.overwrite and not args.no_resume and os.path.exists(ckpt_path):
        ck = json.load(open(ckpt_path, encoding="utf-8"))
        q_lat, q_lng, q_r = ck["q_lat"], ck["q_lng"], ck["q_r"]
        print(f"    resume: {len(q_lat)} đĩa đã truy vấn từ {ckpt_path}")
    if not args.overwrite and not args.no_resume and os.path.exists(args.out):
        for row in csv.DictReader(open(args.out, encoding="utf-8")):
            found[row["code"]] = row
        print(f"    resume: {len(found)} trạm đã có trong {args.out}")

    new_file = args.overwrite or (not os.path.exists(args.out)) or os.path.getsize(args.out) == 0
    out_f = open(args.out, "w" if args.overwrite else "a", newline="", encoding="utf-8")
    writer = csv.DictWriter(out_f, fieldnames=FIELDS, extrasaction="ignore")
    if new_file:
        writer.writeheader()
        out_f.flush()

    qa_lat = np.array(q_lat)
    qa_lng = np.array(q_lng)
    qa_r = np.array(q_r)
    n_queries = 0
    t0 = time.time()

    def save_ckpt():
        json.dump({"q_lat": q_lat, "q_lng": q_lng, "q_r": q_r}, open(ckpt_path, "w", encoding="utf-8"))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context(
            locale="vi-VN", user_agent="Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:152.0) Gecko/20100101 Firefox/152.0"
        )
        ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>false})")
        page = ctx.new_page()
        # Khi nav_gate khoá: chặn mọi điều hướng top-level (interstitial/redirect quảng cáo
        # hay phá huỷ execution context giữa các lần fetch /search). Fetch không phải nav -> vẫn chạy.
        nav_gate = {"on": True}

        def _guard(route):
            req = route.request
            if not nav_gate["on"] and req.is_navigation_request() and req.frame == page.main_frame:
                return route.abort()
            return route.continue_()

        ctx.route("**/*", _guard)

        print(f"[1] Bootstrap qua Cloudflare: {BOOT}")
        bootstrap(page, ctx, nav_gate)

        def covered(lat, lng):
            return len(qa_r) and bool(np.any(haversine_km(lat, lng, qa_lat, qa_lng) <= qa_r))

        def query_point(lat, lng, max_attempts=6):
            """POST /search với retry bền: gặp Cloudflare-challenge -> re-bootstrap + backoff."""
            for attempt in range(max_attempts):
                try:
                    res = page.evaluate(SEARCH_JS, [lat, lng, args.type])
                    if isinstance(res, dict) and "data" in res:
                        return res["data"]
                    # {err:...} = non-JSON/challenge -> làm mới cf_clearance
                except Exception:
                    pass
                wait = min(3 + attempt * 3, 15)  # backoff: 3,6,9,12,15,15s
                try:
                    bootstrap(page, ctx, nav_gate)
                except Exception:
                    pass
                time.sleep(wait)
            return None

        def record(data, lat, lng):
            nonlocal qa_lat, qa_lng, qa_r
            dists = [s["dist"] for s in data if s.get("dist") is not None]
            R = max(dists) if dists else 0.0
            R_cov = R * 1.05 if len(data) >= 50 else max(R * 1.05, 0.05)  # +5% biên sai số toạ độ
            q_lat.append(lat)
            q_lng.append(lng)
            q_r.append(R_cov)
            qa_lat = np.append(qa_lat, lat)
            qa_lng = np.append(qa_lng, lng)
            qa_r = np.append(qa_r, R_cov)
            new = 0
            for s in data:
                code = s.get("code")
                if not code or code in found:
                    continue
                found[code] = rec_from_search(s)
                writer.writerow(found[code])
                new += 1
                # A nationwide grid can discover a dense cluster, but one /search
                # response is capped at 50 results.  Expand from every discovered
                # station as well; already-covered centres are skipped by the loop.
                try:
                    s_lat, s_lng = float(s["lat"]), float(s["lng"])
                    if bbox[0] <= s_lat <= bbox[1] and bbox[2] <= s_lng <= bbox[3]:
                        seeds.append((s_lat, s_lng, True))
                except (TypeError, ValueError):
                    pass
            out_f.flush()
            return R, new

        print(f"[2] Quét /search (cap=50, sleep={args.sleep}s)...")
        failed = []
        for k, (lat, lng, force_query) in enumerate(seeds):
            if not force_query and covered(lat, lng):
                continue
            data = query_point(lat, lng)
            if data is None:
                failed.append((lat, lng))
                continue
            R, new = record(data, lat, lng)
            n_queries += 1
            if n_queries % 10 == 0:
                save_ckpt()
                rate = n_queries / max(time.time() - t0, 1e-9)
                print(
                    f"    q={n_queries}  điểm {k + 1}/{len(seeds)}  trạm={len(found)}  "
                    f"R={R:.1f}km +{new}  ({rate:.2f} q/s)  fail={len(failed)}"
                )
            if args.max_queries and n_queries >= args.max_queries:
                print("    [dừng: đạt --max-queries]")
                break
            time.sleep(args.sleep + np.random.uniform(0, args.sleep))  # jitter

        # PASS 2: gỡ các điểm từng lỗi (nhiều điểm giờ đã được đĩa khác phủ)
        if failed and not (args.max_queries and n_queries >= args.max_queries):
            print(f"[2b] Pass 2 cho {len(failed)} điểm từng lỗi...")
            still = []
            for lat, lng in failed:
                if covered(lat, lng):
                    continue
                data = query_point(lat, lng, max_attempts=8)
                if data is None:
                    still.append((lat, lng))
                    continue
                record(data, lat, lng)
                n_queries += 1
                time.sleep(args.sleep + np.random.uniform(0, args.sleep))
            if still:
                print(f"    ! {len(still)} điểm vẫn lỗi sau pass 2 (bỏ qua): {still[:10]}")

        save_ckpt()
        browser.close()

    out_f.close()
    with open(codes_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(found)) + "\n")
    print(f"[3] Xong: {len(found)} trạm, {n_queries} truy vấn -> {args.out}")
    print(f"    {len(found)} mã -> {codes_path}")


if __name__ == "__main__":
    main()
