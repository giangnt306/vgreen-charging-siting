#!/usr/bin/env python3
"""
evcs_scrape.py — Lấy time-series "số ô tô sạc" từ evcs.vn (mặc định 30 ngày).

CƠ CHẾ THẬT (đo lại trực tiếp 2026-07-29 — site đã đổi so với bản crawl 07-21/22):
  - /update (POST) chỉ là ping analytics -> luôn 204, BỎ QUA.
  - Dữ liệu chart đi qua Socket.IO, nhưng KHÔNG còn same-origin:
        socket = io('https://www2.evcs.vn/', {path:'/socket.io', auth:<fn>, ...})
        socket.emit('history', { stationId, hours, token:'', detail:false })
        socket.on('history_data', data)   # data = [[timestamp, value], ...]
  - `hours` là ENUM {24, 168, 720} khớp 3 nút UI "24 giờ / 7 ngày / 30 ngày".
    Giá trị ngoài enum (72/336/576/1440…) server im lặng bỏ qua -> timeout.
  - `subscribe` KHÔNG cần cho history (đo: 20/20 trạm OK khi bỏ) — bỏ đi để socket
    dùng chung không phải nuốt luồng `new_data` realtime của mọi trạm đã hỏi.
  - Handshake có `auth` callback sinh token ký; không tái tạo được từ Python nên
    ta mượn lại đối tượng opts của chính trang (xem `session.py`).

BA THAY ĐỔI PHÁ VỠ so với code cũ (nếu thấy 0 dòng/`AttributeError` thì là đây):
  host `io('/')` -> `www2.evcs.vn` · thiếu `auth` -> handshake bị từ chối ·
  payload `[{timestamp,value}]` -> `[[ts,value]]`.

CÔ LẬP DANH TÍNH (F3): payload history_data KHÔNG mang stationId, nên không thể
hậu kiểm bằng nội dung. Thay vì 1 socket/trạm (đo: 1,24 s/trạm ≈ 6,6 h) ta dùng
socket dùng chung + **một request in-flight tại một thời điểm** + **vứt và dựng
lại socket ngay khi timeout** (đo: 0,37 s/trạm ≈ 2,0 h). Reply muộn của trạm A vì
thế rơi vào socket đã đóng, không thể resolve request của trạm B.

Chạy:
    python -m ev_siting.data.evcs.evcs_scrape --codes C.HNO16154 --hours 720
    python -m ev_siting.data.evcs.evcs_scrape --codes-file data/interim/evcs_all_codes.txt

Output (F2): mặc định ghi RAW RUN BẤT BIẾN `data/raw/evcs/timeseries_runs/load_ts_<run-id>.csv`
(kèm `<run>.done` để resume và `<run>.failed` để audit/retry). Không bao giờ ghi đè run cũ;
gộp về canonical là việc của `split_timeseries --input <run>`. Đưa `--out <run cũ>` để resume.
"""

import argparse
import csv
import os
import re
import sys
import time
from datetime import datetime

from playwright.sync_api import sync_playwright

from .paths import TIMESERIES_RUNS_DIR
from .session import BOOTSTRAP_PAGES, open_session, renew_session, reset_socket

BASE = "https://evcs.vn"
BOOTSTRAP_PAGE = BOOTSTRAP_PAGES[0]  # tương thích ngược
HOURS_ALLOWED = (24, 168, 720)  # enum server chấp nhận; ngoài enum -> im lặng timeout

# JS chạy TRONG trang: hỏi history cho MỘT trạm trên socket dùng chung của trang.
# Một request in-flight tại một thời điểm; timeout được báo về Python để nơi đó
# vứt socket (xem `session.reset_socket`) trước khi hỏi trạm kế -> cô lập danh tính.
ASK_JS = """
async ([sid, hours, timeoutMs]) => {
  const s = window.__page_socket;
  if (!s || !s.connected) return { status: 'socket_down' };
  const t0 = performance.now();
  const r = await new Promise((resolve) => {
    const h = (d) => { clearTimeout(timer); resolve({ status: 'ok', data: d }); };
    const timer = setTimeout(() => { s.off('history_data', h); resolve({ status: 'timeout' }); }, timeoutMs);
    s.once('history_data', h);
    s.emit('history', { stationId: sid, hours, token: '', detail: false });
  });
  r.ms = performance.now() - t0;
  return r;
}
"""

# Metadata nhúng trong HTML trang trạm (object trong hàm favorite()).
META_RE = re.compile(r"favorite\(\)\s*\{\s*const station = (\{.*?\});", re.S)


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
    """Tập mã trạm nhận response hợp lệ (rỗng hợp lệ, timeout không được tính)."""
    if not os.path.exists(done_path):
        return set()
    with open(done_path, encoding="utf-8") as f:
        return {ln.strip() for ln in f if ln.strip()}


def reconcile_failed(failed_path, done):
    """Giữ `.failed` là tập mã chưa thành công, không tích luỹ lỗi đã retry xong."""
    failed = set()
    if os.path.exists(failed_path):
        with open(failed_path, encoding="utf-8") as f:
            failed = {ln.strip() for ln in f if ln.strip()}
    remaining = sorted(failed - done)
    tmp = failed_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("\n".join(remaining) + ("\n" if remaining else ""))
    os.replace(tmp, failed_path)
    return remaining


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


def normalize_series(data):
    """`history_data` -> [(timestamp, value)]. Trả (rows, n_bỏ_qua).

    Chấp nhận CẢ HAI định dạng: `[[ts, value], …]` (từ 2026-07-29) và
    `[{timestamp, value}, …]` (bản cũ, để đọc lại được run 07-21/22). Điểm không
    parse được KHÔNG bị nuốt im lặng mà được đếm — nếu server đổi schema lần nữa,
    `run()` sẽ dừng thay vì ghi hàng triệu dòng null.
    """
    if not isinstance(data, list):
        return None, 0
    rows, n_bad = [], 0
    for pt in data:
        if isinstance(pt, (list, tuple)) and len(pt) >= 2:
            rows.append((pt[0], pt[1]))
        elif isinstance(pt, dict) and "timestamp" in pt:
            rows.append((pt.get("timestamp"), pt.get("value")))
        else:
            n_bad += 1
    return rows, n_bad


def ask_station(page, ctx, sid, hours, timeout_ms=20000):
    """Hỏi history 1 trạm. Trả (rows|None, ghi_chú).

    Mọi nhánh hỏng (timeout / socket chết / evaluate lỗi) đều **dựng lại socket**
    trước khi trả về, nên request kế tiếp không bao giờ nhận reply muộn của trạm này.
    """
    try:
        r = page.evaluate(ASK_JS, [sid, hours, timeout_ms])
    except Exception as e:
        reset_socket(page, verbose=False) or renew_session(ctx, page, verbose=False)
        return None, f"evaluate: {str(e)[:60]}"
    if r.get("status") != "ok":
        note = r.get("status")
        if not reset_socket(page, verbose=False):
            renew_session(ctx, page, verbose=False)
        return None, note
    rows, n_bad = normalize_series(r.get("data"))
    if rows is None:
        return None, f"payload lạ: {type(r.get('data')).__name__}"
    return rows, ("ok" if not n_bad else f"ok ({n_bad} điểm không parse được)")


def run(codes, hours, out_path, from_sitemap, resume=True, overwrite=False, sleep=0.05, headless=False):
    if hours not in HOURS_ALLOWED:
        raise SystemExit(f"--hours={hours} không nằm trong enum server chấp nhận {HOURS_ALLOWED} -> sẽ timeout 100%.")
    done_path = out_path + ".done"  # 1 mã/dòng: các trạm đã crawl xong
    failed_path = out_path + ".failed"  # timeout/socket error: giữ lại để retry/audit
    codes_path = out_path + ".codes"  # cache danh sách mã từ sitemap
    done = load_done(done_path) if resume and not overwrite else set()

    # Mở output ở chế độ APPEND -> ghi tăng dần, không mất khi gián đoạn.
    new_file = overwrite or (not os.path.exists(out_path)) or os.path.getsize(out_path) == 0
    out_f = open(out_path, "w" if overwrite else "a", newline="", encoding="utf-8")
    writer = csv.DictWriter(out_f, fieldnames=["station_code", "timestamp", "n_cars_charging"])
    if new_file:
        writer.writeheader()
        out_f.flush()
    done_f = open(done_path, "w" if overwrite else "a", encoding="utf-8")
    failed_f = open(failed_path, "w" if overwrite else "a", encoding="utf-8")

    total_written = n_ok = n_fail = n_empty = 0
    t_start = time.time()
    try:
        with sync_playwright() as p:
            print(f"[1] Mở phiên evcs.vn (Cloudflare + socket {BOOTSTRAP_PAGE.split('/')[2]})", flush=True)
            ctx, page = open_session(p, headless=headless)

            if from_sitemap:
                codes = get_or_cache_sitemap_codes(ctx, codes_path)

            pending = [c for c in codes if c not in done]
            print(
                f"[2] Lấy history (hours={hours}): {len(done)} đã xong, {len(pending)}/{len(codes)} còn lại.",
                flush=True,
            )

            for i, sid in enumerate(pending, 1):
                rows, note = ask_station(page, ctx, sid, hours)
                if rows is None:  # F6: hỏng KHÔNG được tính là `.done`
                    rows, note2 = ask_station(page, ctx, sid, hours)  # một pass retry ngay
                    if rows is None:
                        failed_f.write(sid + "\n")
                        n_fail += 1
                        if n_fail <= 20 or n_fail % 100 == 0:
                            print(f"    ! {sid} thất bại ({note} / {note2})", file=sys.stderr, flush=True)
                        continue
                for ts, val in rows:
                    writer.writerow({"station_code": sid, "timestamp": ts, "n_cars_charging": val})
                total_written += len(rows)
                n_ok += 1
                n_empty += 1 if not rows else 0
                done_f.write(sid + "\n")  # chỉ response hợp lệ mới được resume bỏ qua

                if i % 200 == 0 or i == len(pending):
                    out_f.flush()
                    done_f.flush()
                    failed_f.flush()
                    el = time.time() - t_start
                    eta = el / i * (len(pending) - i)
                    print(
                        f"    ...{i}/{len(pending)}  ok={n_ok} fail={n_fail} rỗng={n_empty}  "
                        f"{total_written:,} điểm  |  {el / 60:.1f}' trôi, ETA {eta / 60:.0f}'",
                        flush=True,
                    )
                if sleep:
                    time.sleep(sleep)

            ctx.close()
    finally:
        out_f.close()
        done_f.close()
        failed_f.close()
    remaining_failed = reconcile_failed(failed_path, load_done(done_path))
    if remaining_failed:
        print(f"[3] Còn {len(remaining_failed)} trạm failed -> {failed_path} (sẽ retry khi resume)")
    print(
        f"[3] Xong sau {(time.time() - t_start) / 60:.1f}'. ok={n_ok} fail={n_fail} rỗng={n_empty}; "
        f"ghi thêm {total_written:,} điểm -> {out_path}"
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--codes", nargs="*", default=[], help="Danh sách mã trạm, vd C.HNO16154")
    ap.add_argument("--codes-file", help="File 1 mã/dòng (vd evcs_stations_codes.txt từ evcs_enumerate.py)")
    ap.add_argument(
        "--from-sitemap",
        action="store_true",
        help="[HỎNG] sitemap không chứa mã trạm — dùng evcs_enumerate.py + --codes-file",
    )
    ap.add_argument("--hours", type=int, default=720, help="ENUM server: 24 (1 ngày) | 168 (7 ngày) | 720 (30 ngày)")
    ap.add_argument("--out", help="raw run CSV; mặc định tạo run mới trong data/raw/evcs/timeseries_runs/")
    ap.add_argument("--no-resume", action="store_true", help="Bỏ qua file .done, crawl lại từ đầu")
    ap.add_argument("--overwrite", action="store_true", help="Crawl mới: ghi đè CSV và file .done của --out")
    ap.add_argument("--limit", type=int, help="Chỉ crawl N mã đầu (pilot/kiểm thử)")
    ap.add_argument("--sleep", type=float, default=0.05, help="Nghỉ giữa 2 trạm (giây) — lịch sự với nguồn")
    ap.add_argument("--headless", action="store_true", help="Chạy ẩn (profile đã có cf_clearance thì được)")
    args = ap.parse_args()
    if args.out is None:
        TIMESERIES_RUNS_DIR.mkdir(parents=True, exist_ok=True)
        run_id = datetime.now().strftime("%Y-%m-%dT%H-%M-%S-%f")
        args.out = str(TIMESERIES_RUNS_DIR / f"load_ts_{run_id}.csv")
    codes = list(args.codes)
    if args.codes_file:
        with open(args.codes_file, encoding="utf-8") as f:
            codes += [ln.strip() for ln in f if ln.strip()]
    if not codes and not args.from_sitemap:
        codes = ["C.HNO16154"]
    if args.limit:
        codes = codes[: args.limit]
    run(
        codes,
        args.hours,
        args.out,
        args.from_sitemap,
        resume=not args.no_resume,
        overwrite=args.overwrite,
        sleep=args.sleep,
        headless=args.headless,
    )
