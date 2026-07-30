#!/usr/bin/env python3
"""
evcs_probe.py — Dò endpoint POST /update của evcs.vn qua Cloudflare.

Mục tiêu: in ra CẤU TRÚC JSON thật của dữ liệu "số ô tô sạc" để viết parser/loader.

Cài đặt (một lần):
    pip install playwright
    playwright install chromium

Chạy:
    python evcs_probe.py                     # dùng mã trạm mẫu C.HCM1339
    python evcs_probe.py C.HCM0160 C.HCM1339 # nhiều mã

Ghi chú:
- Chạy headful (headless=False) dễ qua Cloudflare managed challenge hơn.
  Nếu server không có màn hình, dùng xvfb-run hoặc thử headless=True.
- Script thử cả b=0 và b=1 để xem 'b' chọn dữ liệu gì (live vs lịch sử 7 ngày).
"""
import json
import sys

from playwright.sync_api import sync_playwright

# Mã trạm mẫu -> URL trang tương ứng (để nạp trang, lấy cf_clearance).
SAMPLE_PAGE = "https://evcs.vn/tram-sac-vinfast-vincom-center-dong-khoi-ham-b6-c.hcm0160.html"
UPDATE_URL = "https://evcs.vn/update"


def probe(station_codes):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)   # đổi True nếu chạy nền + xvfb
        ctx = browser.new_context(
            locale="en-US",
            user_agent=("Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:152.0) "
                        "Gecko/20100101 Firefox/152.0"),
        )
        page = ctx.new_page()

        print(f"[1] Mở trang trạm để qua Cloudflare: {SAMPLE_PAGE}")
        page.goto(SAMPLE_PAGE, wait_until="domcontentloaded", timeout=60000)

        # Chờ Cloudflare cấp cf_clearance (tối đa ~30s)
        for _ in range(30):
            cookies = {c["name"]: c["value"] for c in ctx.cookies()}
            if "cf_clearance" in cookies:
                break
            page.wait_for_timeout(1000)
        cookies = {c["name"]: c["value"] for c in ctx.cookies()}
        print(f"    cf_clearance: {'OK' if 'cf_clearance' in cookies else 'CHƯA CÓ'} | "
              f"PHPSESSID: {'OK' if 'PHPSESSID' in cookies else 'CHƯA CÓ'}")

        # Dùng request context ĐÃ xác thực của trình duyệt -> tự mang cookie + CF.
        # Thử nhiều giá trị 'b' để tìm chế độ trả về time-series (thay vì danh sách trạm).
        for code in station_codes:
            for b in range(0, 4):
                body = {"a": code, "b": b}
                resp = ctx.request.post(
                    UPDATE_URL,
                    data=json.dumps(body),
                    headers={
                        "Content-Type": "application/json",
                        "Origin": "https://evcs.vn",
                        "Referer": SAMPLE_PAGE,
                    },
                )
                raw = resp.text()
                print("\n" + "=" * 70)
                print(f"POST /update  body={body}  -> HTTP {resp.status}")
                if not raw.strip():
                    print("  (body rỗng — 204/không có thay đổi)")
                    continue
                try:
                    parsed = resp.json()
                except Exception:
                    print(raw[:2000])
                    continue
                # In các khóa cấp cao + nguyên vẹn PHẦN TỬ ĐẦU TIÊN của 'data'
                if isinstance(parsed, dict):
                    print("  keys:", list(parsed.keys()))
                    data = parsed.get("data")
                    if isinstance(data, list) and data:
                        print(f"  data: list[{len(data)}] — phần tử đầu (đầy đủ field):")
                        print(json.dumps(data[0], ensure_ascii=False, indent=2))
                    else:
                        print(json.dumps(parsed, ensure_ascii=False, indent=2)[:2000])
                else:
                    print(json.dumps(parsed, ensure_ascii=False, indent=2)[:2000])

        browser.close()


if __name__ == "__main__":
    codes = sys.argv[1:] or ["C.HCM1339"]
    probe(codes)
