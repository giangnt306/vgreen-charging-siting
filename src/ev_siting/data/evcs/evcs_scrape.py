#!/usr/bin/env python3
"""
evcs_scrape.py — Lấy time-series "số ô tô sạc" (24h/7 ngày) từ evcs.vn.

CƠ CHẾ THẬT (giải mã từ scripts.js của trang trạm):
  - /update (POST) chỉ là ping analytics -> luôn 204, BỎ QUA.
  - Dữ liệu chart đi qua Socket.IO:
        socket = io('/')
        socket.emit('subscribe', stationId)
        socket.emit('history', { stationId, hours })   # hours = 24 | 168
        socket.on('history_data', data)  # data = [{timestamp, value}]  value = số xe
  - Trang bị Cloudflare -> phải mở bằng trình duyệt thật (Playwright) để có cf_clearance,
    rồi tái dùng chính socket same-origin của trang => tự qua Cloudflare.

Cài đặt:
    pip install playwright
    playwright install chromium

Chạy:
    # 1) Lấy history cho vài mã trạm cụ thể:
    python evcs_scrape.py --codes C.HNO16154 C.HCM1339 --hours 168

    # 2) Enumerate toàn bộ mã trạm từ sitemap rồi lấy history:
    python evcs_scrape.py --from-sitemap --hours 168 --out load_ts.csv
"""
import argparse
import csv
import os
import re
import sys

from playwright.sync_api import sync_playwright

from .paths import LOAD_TS

BASE = "https://evcs.vn"
# Trang trạm để nạp socket.io + qua Cloudflare. Nhiều URL dự phòng: URL này chết thì thử URL kế.
BOOTSTRAP_PAGES = [
    f"{BASE}/tram-sac-vinfast-nguyen-van-chenh-thon-dao-xuyen-xa-bat-trang-c.hno16154.html",
    f"{BASE}/tram-sac-vinfast-c.hcm0014.html",
]
BOOTSTRAP_PAGE = BOOTSTRAP_PAGES[0]  # tương thích ngược

# JS chạy TRONG trang: dùng `io` (socket.io đã load) để lấy history cho nhiều trạm.
FETCH_JS = """
async ([stationIds, hours]) => {
  const socket = io('/', { transports:['websocket','polling'], reconnection:false, timeout:10000 });
  await new Promise((res, rej) => {
    socket.on('connect', res);
    socket.on('connect_error', rej);
    setTimeout(() => rej(new Error('socket timeout')), 10000);
  });
  const out = {};
  for (const sid of stationIds) {
    socket.emit('subscribe', sid);
    out[sid] = await new Promise((res) => {
      const done = (d) => res(d);
      socket.once('history_data', done);
      socket.emit('history', { stationId: sid, hours });
      setTimeout(() => res(null), 8000);   // timeout 1 trạm
    });
  }
  socket.disconnect();
  return out;
}
"""

# Metadata nhúng trong HTML trang trạm (object trong hàm favorite()).
META_RE = re.compile(r'favorite\(\)\s*\{\s*const station = (\{.*?\});', re.S)


def get_station_codes_from_sitemap(ctx):
    """Đọc sitemap qua browser context (đã qua Cloudflare) -> list mã C.XXXXnnnn."""
    codes = set()
    to_visit = [f"{BASE}/sitemap.xml"]
    seen = set()
    while to_visit:
        url = to_visit.pop()
        if url in seen:
            continue
        seen.add(url)
        resp = ctx.request.get(url)
        if resp.status != 200:
            print(f"  ! sitemap {url} -> HTTP {resp.status}", file=sys.stderr)
            continue
        xml = resp.text()
        # sitemap index -> thêm sitemap con
        to_visit += re.findall(r"<sitemap>.*?<loc>(.*?)</loc>", xml, re.S)
        # url trạm dạng ...-c.<code>.html
        for m in re.findall(r"-c\.([a-z]+\d+)\.html", xml):
            codes.add("C." + m.upper())
    return sorted(codes)


def load_done(done_path):
    """Tập mã trạm ĐÃ crawl (để resume, kể cả trạm trả về rỗng)."""
    if not os.path.exists(done_path):
        return set()
    with open(done_path, encoding="utf-8") as f:
        return {ln.strip() for ln in f if ln.strip()}


def get_or_cache_sitemap_codes(ctx, codes_path):
    """Enumerate mã từ sitemap, cache ra file để lần chạy sau khỏi quét lại."""
    if os.path.exists(codes_path) and os.path.getsize(codes_path) > 0:
        with open(codes_path, encoding="utf-8") as f:
            codes = [ln.strip() for ln in f if ln.strip()]
        print(f"    Dùng lại {len(codes)} mã từ cache {codes_path}")
        return codes
    print("[2] Enumerate mã trạm từ sitemap...")
    codes = get_station_codes_from_sitemap(ctx)
    with open(codes_path, "w", encoding="utf-8") as f:
        f.write("\n".join(codes) + "\n")
    print(f"    Tìm thấy {len(codes)} mã -> đã cache {codes_path}")
    return codes


def bootstrap(page, ctx, tries=4):
    """Nạp trang qua Cloudflare + đảm bảo io() sẵn sàng (retry nếu socket.io chưa nạp)."""
    # domcontentloaded (KHÔNG networkidle): trang giữ 1 kết nối Socket.IO thường trực
    # nên mạng không bao giờ "idle" -> networkidle sẽ treo tới hết timeout.
    for attempt in range(tries):
        url = BOOTSTRAP_PAGES[attempt % len(BOOTSTRAP_PAGES)]  # xoay vòng URL dự phòng
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            for _ in range(45):
                if any(c["name"] == "cf_clearance" for c in ctx.cookies()):
                    break
                page.wait_for_timeout(1000)
            ok = any(c["name"] == "cf_clearance" for c in ctx.cookies())
            print("    cf_clearance:", "OK" if ok else "CHƯA CÓ")
            page.wait_for_function("typeof io !== 'undefined'", timeout=20000)
            return
        except Exception as e:
            print(f"    ! bootstrap thử {attempt+1}/{tries} ({url}) lỗi ({str(e)[:60]}); nạp lại...")
            page.wait_for_timeout(3000)
    raise RuntimeError("bootstrap thất bại: io() không sẵn sàng sau nhiều lần thử")


def run(codes, hours, out_path, from_sitemap, resume=True, overwrite=False):
    done_path = out_path + ".done"        # 1 mã/dòng: các trạm đã crawl xong
    codes_path = out_path + ".codes"      # cache danh sách mã từ sitemap
    done = load_done(done_path) if resume and not overwrite else set()

    # Mở output ở chế độ APPEND -> ghi tăng dần, không mất khi gián đoạn.
    new_file = overwrite or (not os.path.exists(out_path)) or os.path.getsize(out_path) == 0
    out_f = open(out_path, "w" if overwrite else "a", newline="", encoding="utf-8")
    writer = csv.DictWriter(out_f, fieldnames=["station_code", "timestamp", "n_cars_charging"])
    if new_file:
        writer.writeheader()
        out_f.flush()
    done_f = open(done_path, "w" if overwrite else "a", encoding="utf-8")

    total_written = 0
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)  # True + xvfb nếu chạy server
            ctx = browser.new_context(
                locale="vi-VN",
                user_agent=("Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:152.0) "
                            "Gecko/20100101 Firefox/152.0"),
            )
            # Ẩn navigator.webdriver (bẫy bot trong isHeadlessBrowser)
            ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>false})")
            page = ctx.new_page()

            print(f"[1] Nạp trang bootstrap (qua Cloudflare): {BOOTSTRAP_PAGE}")
            bootstrap(page, ctx)

            if from_sitemap:
                codes = get_or_cache_sitemap_codes(ctx, codes_path)

            pending = [c for c in codes if c not in done]
            print(f"[3] Lấy history (hours={hours}): {len(done)} đã xong, "
                  f"{len(pending)}/{len(codes)} còn lại.")

            BATCH = 50  # emit theo lô để tránh giữ 1 promise quá lâu
            for i in range(0, len(pending), BATCH):
                batch = pending[i:i + BATCH]
                try:
                    result = page.evaluate(FETCH_JS, [batch, hours])
                except Exception as e:                       # socket/nav hỏng -> nạp lại 1 lần
                    print(f"    ! batch lỗi ({e}); nạp lại trang & thử lại...", file=sys.stderr)
                    try:
                        bootstrap(page, ctx)
                        result = page.evaluate(FETCH_JS, [batch, hours])
                    except Exception as e2:
                        print(f"    !! bỏ qua batch (retry lỗi: {e2})", file=sys.stderr)
                        continue
                for sid, series in result.items():
                    for pt in (series or []):
                        writer.writerow({
                            "station_code": sid,
                            "timestamp": pt.get("timestamp"),
                            "n_cars_charging": pt.get("value"),
                        })
                        total_written += 1
                    done_f.write(sid + "\n")   # đánh dấu xong (kể cả rỗng) để resume bỏ qua
                out_f.flush()
                done_f.flush()
                print(f"    ...{min(i + BATCH, len(pending))}/{len(pending)}  "
                      f"(+{total_written} điểm tích luỹ)")

            browser.close()
    finally:
        out_f.close()
        done_f.close()
    print(f"[4] Xong. Đã ghi thêm {total_written} điểm -> {out_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--codes", nargs="*", default=[], help="Danh sách mã trạm, vd C.HNO16154")
    ap.add_argument("--codes-file", help="File 1 mã/dòng (vd evcs_stations_codes.txt từ evcs_enumerate.py)")
    ap.add_argument("--from-sitemap", action="store_true",
                    help="[HỎNG] sitemap không chứa mã trạm — dùng evcs_enumerate.py + --codes-file")
    ap.add_argument("--hours", type=int, default=168, help="24 (1 ngày) hoặc 168 (7 ngày)")
    ap.add_argument("--out", default=str(LOAD_TS))
    ap.add_argument("--no-resume", action="store_true",
                    help="Bỏ qua file .done, crawl lại từ đầu")
    ap.add_argument("--overwrite", action="store_true",
                    help="Crawl mới: ghi đè CSV và file .done của --out")
    args = ap.parse_args()
    codes = list(args.codes)
    if args.codes_file:
        with open(args.codes_file, encoding="utf-8") as f:
            codes += [ln.strip() for ln in f if ln.strip()]
    if not codes and not args.from_sitemap:
        codes = ["C.HNO16154"]
    run(codes, args.hours, args.out, args.from_sitemap,
        resume=not args.no_resume, overwrite=args.overwrite)
