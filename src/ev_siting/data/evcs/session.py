#!/usr/bin/env python3
"""session.py — phiên trình duyệt evcs.vn dùng chung cho enumerate + scrape.

Vì sao tách ra: từ 2026-07-29 site đổi kiến trúc realtime, và cả hai crawler đều
cần đúng một thứ — một trang đã qua Cloudflare, đã nạp socket.io, và **đã tự mở
socket** để ta mượn lại tham số kết nối của nó.

Ba thay đổi phía server (đo trực tiếp 2026-07-29, xem `docs/sources/evcs.md`):

1. **Socket không còn same-origin.** Trang gọi
   ``io("https://www2.evcs.vn/", {path:"/socket.io", auth:<fn>, ...})``.
   Code cũ gọi ``io("/")`` → nối vào evcs.vn → `websocket error`.
2. **Handshake có `auth` callback** sinh token ``{t:"<epoch>.<chữ ký>"}``. Không
   tái tạo được từ Python, nên ta **giữ nguyên đối tượng opts của trang** (kèm
   chính hàm auth đó) trong ``window.__io_args`` rồi truyền lại cho ``io()``.
3. **`history_data` đổi định dạng** ``[{timestamp,value}]`` → ``[[ts,value]]``.
   (Phần parse nằm ở `evcs_scrape.py`; ghi ở đây để một chỗ kể đủ câu chuyện.)

Profile Chromium được giữ lại giữa các lần chạy (`data/.cache/cf_profile`) nên
`cf_clearance` được tái dùng: bootstrap lần đầu ~15 s, các lần sau ~1 s. Đây cũng
là cách giảm số lần chạm Cloudflare — lịch sự với nguồn và ít bị challenge nặng.
"""

import time

from .paths import DATA

# Profile bền vững -> cache cf_clearance. Nằm trong data/ nên đã gitignore.
PROFILE_DIR = DATA / ".cache" / "cf_profile"
UA = "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:152.0) Gecko/20100101 Firefox/152.0"

# Nhiều trang trạm dự phòng: URL này chết thì thử URL kế.
BOOTSTRAP_PAGES = [
    "https://evcs.vn/tram-sac-vinfast-nguyen-van-chenh-thon-dao-xuyen-xa-bat-trang-c.hno16154.html",
    "https://evcs.vn/tram-sac-vinfast-c.hcm0014.html",
]

# Chèn TRƯỚC mọi script của trang: bọc `window.io` để giữ lại (a) tham số kết nối
# thật — kể cả hàm `auth` — và (b) socket đầu tiên trang tự mở.
_SPY_JS = """
(() => {
  if (window.__spy_installed) return;
  window.__spy_installed = true;
  let real;
  Object.defineProperty(window, 'io', {
    configurable: true,
    get() { return real ? window.__wio : undefined; },
    set(v) {
      real = v;
      window.__raw_io = real;
      window.__wio = function (...args) {
        if (!window.__io_args) window.__io_args = args;   // giữ nguyên hàm auth
        const s = real.apply(this, args);
        if (!window.__page_socket) window.__page_socket = s;
        return s;
      };
      Object.assign(window.__wio, real);
    },
  });
})();
"""

# Dựng lại socket dùng chung sau timeout (cô lập danh tính — xem evcs_scrape.py).
RESET_SOCKET_JS = """
() => {
  try { window.__page_socket && window.__page_socket.disconnect(); } catch (_) {}
  const [url, opts] = window.__io_args;
  window.__page_socket = window.__raw_io(url, opts);
  return new Promise((resolve) => {
    const t = setTimeout(() => resolve(false), 20000);
    window.__page_socket.once('connect', () => { clearTimeout(t); resolve(true); });
    window.__page_socket.once('connect_error', () => { clearTimeout(t); resolve(false); });
  });
}
"""


def open_session(p, headless=False, tries=4, verbose=True):
    """Mở phiên đã sẵn sàng gọi API. Trả `(ctx, page)`; ném RuntimeError kèm giai đoạn hỏng.

    Chờ theo BA giai đoạn tách bạch để lỗi chỉ đúng chỗ thay vì "timeout" chung chung:
    `cf_clearance` → `typeof io` → trang đã mở socket (`__page_socket.connected`).
    """
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    ctx = p.chromium.launch_persistent_context(
        str(PROFILE_DIR),
        headless=headless,
        locale="vi-VN",
        user_agent=UA,
        viewport={"width": 1280, "height": 900},
        args=["--disable-blink-features=AutomationControlled"],
    )
    ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>false})")
    ctx.add_init_script(_SPY_JS)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    ok, last = _bring_up(ctx, page, tries, verbose)
    if ok:
        return ctx, page
    ctx.close()
    raise RuntimeError(f"bootstrap thất bại sau {tries} lần — {last}")


def renew_session(ctx, page, tries=4, verbose=True):
    """Dựng lại phiên tại chỗ khi socket chết giữa run dài (cf_clearance hết hạn…).

    Giữ nguyên context/profile nên không mất cookie đã có; chỉ nạp lại trang để
    `__io_args`/`__page_socket` được tạo mới. Trả True nếu phiên dùng được lại.
    """
    ok, last = _bring_up(ctx, page, tries, verbose)
    if not ok and verbose:
        print(f"    ! renew session thất bại — {last}", flush=True)
    return ok


def _bring_up(ctx, page, tries, verbose):
    """Nạp trang rồi chờ BA giai đoạn. Trả (ok, mô_tả_lỗi_cuối)."""
    last = "chưa thử lần nào"
    for attempt in range(tries):
        url = BOOTSTRAP_PAGES[attempt % len(BOOTSTRAP_PAGES)]
        t0 = time.time()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=90000)
        except Exception as e:
            last = f"goto: {str(e)[:90]}"
            if verbose:
                print(f"    ! bootstrap {attempt + 1}/{tries} — {last}", flush=True)
            continue

        # (1) Cloudflare — trang challenge trả HTTP 403 rồi mới set cookie.
        if not _wait_cookie(ctx, page, "cf_clearance", 90):
            last = f"không có cf_clearance sau 90s (title={page.title()[:40]!r})"
            if verbose:
                print(f"    ! bootstrap {attempt + 1}/{tries} — {last}", flush=True)
            page.wait_for_timeout(5000)
            continue

        # (2) bundle socket.io đã nạp
        try:
            page.wait_for_function("typeof io !== 'undefined'", timeout=45000)
        except Exception:
            last = f"io() không nạp sau cf_clearance (title={page.title()[:40]!r})"
            if verbose:
                print(f"    ! bootstrap {attempt + 1}/{tries} — {last}", flush=True)
            continue

        # (3) trang đã tự mở socket -> __io_args có hàm auth thật để ta tái dùng
        try:
            page.wait_for_function(
                "!!(window.__page_socket && window.__page_socket.connected && window.__io_args)",
                timeout=45000,
            )
        except Exception:
            last = "trang không mở được socket (auth hoặc websocket bị chặn?)"
            if verbose:
                print(f"    ! bootstrap {attempt + 1}/{tries} — {last}", flush=True)
            continue

        if verbose:
            print(f"    session sẵn sàng sau {time.time() - t0:.1f}s", flush=True)
        return True, None
    return False, last


def _wait_cookie(ctx, page, name, seconds):
    for _ in range(seconds):
        if any(c["name"] == name for c in ctx.cookies()):
            return True
        page.wait_for_timeout(1000)
    return any(c["name"] == name for c in ctx.cookies())


def reset_socket(page, verbose=True):
    """Vứt socket dùng chung và dựng cái mới. Trả True nếu nối lại được."""
    try:
        ok = page.evaluate(RESET_SOCKET_JS)
    except Exception as e:
        if verbose:
            print(f"    ! reset socket lỗi: {str(e)[:80]}", flush=True)
        return False
    if verbose and not ok:
        print("    ! reset socket: không connect lại được", flush=True)
    return bool(ok)
