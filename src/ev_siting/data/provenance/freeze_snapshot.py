#!/usr/bin/env python3
"""freeze_snapshot.py — đóng băng tập input thô về snapshot bất biến (E-DQ10).

Băm mọi nguồn thô (đặc tả ở ``manifest.py``), ghi ``data/raw/MANIFEST.json`` và
(mặc định) khoá thư mục raw về read-only để chống sửa vô tình. Manifest được
**commit vào git** dù blob bị .gitignore → lineage/provenance version-hoá.

Vận hành hoá **P9**: snapshot_id mặc định = 2026-07-20 (khớp mốc replication .pbf).

Dùng:
    # đóng băng (băm nội dung + ghi manifest + khoá read-only)
    PYTHONPATH=src python -m ev_siting.data.provenance.freeze_snapshot
    # đóng băng nhanh (bỏ băm nội dung; chỉ bytes/mtime) — dùng thử
    PYTHONPATH=src python -m ev_siting.data.provenance.freeze_snapshot --quick
    # KHÔNG khoá read-only (còn crawl tiếp)
    PYTHONPATH=src python -m ev_siting.data.provenance.freeze_snapshot --no-lock
    # đối chiếu snapshot đang có (nhanh); thêm --hashes để băm lại nội dung
    PYTHONPATH=src python -m ev_siting.data.provenance.freeze_snapshot --verify [--hashes]

Thoát mã: 0 = OK; 1 = drift/thiếu khi --verify; 2 = lỗi cấu hình.
"""
import argparse
import json
import os
import stat
import sys

from . import manifest as M


def _lock_readonly(paths) -> int:
    """Bỏ cờ ghi (a-w) trên mọi file thô đã đóng băng. Trả số file đã khoá."""
    n = 0
    for base in paths:
        if not base.exists():
            continue
        targets = [base] if base.is_file() else base.rglob("*")
        for p in targets:
            if p.is_file():
                mode = p.stat().st_mode
                p.chmod(mode & ~0o222)  # bỏ w của user/group/other
                n += 1
    return n


def _member_paths():
    for spec in M.source_specs():
        for m in spec["members"]:
            yield m["path"]


def do_freeze(snapshot_id: str, content: bool, lock: bool) -> int:
    print(f"[freeze] snapshot_id={snapshot_id}  content_hash={content}")
    print("[freeze] băm nguồn thô (có thể mất vài chục giây với file GB)…")
    man = M.build_manifest(snapshot_id, content=content)

    M.MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    M.MANIFEST_PATH.write_text(
        json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")

    _summary(man)
    print(f"[freeze] manifest -> {M.MANIFEST_PATH.relative_to(M.PROJECT_ROOT)}")

    if lock:
        n = _lock_readonly(list(_member_paths()))
        print(f"[freeze] đã khoá read-only {n:,} file (chống sửa vô tình)")
    else:
        print("[freeze] --no-lock: bỏ qua khoá read-only")
    print("[freeze] LƯU Ý: commit data/raw/MANIFEST.json vào git (blob bị .gitignore).")
    return 0


def do_verify(full: bool) -> int:
    man = M.load_manifest()
    if man is None:
        print(f"CRITICAL: chưa có {M.MANIFEST_PATH.relative_to(M.PROJECT_ROOT)} "
              f"— chạy freeze trước.", file=sys.stderr)
        return 2
    mode = "ĐẦY ĐỦ (băm nội dung)" if full else "NHANH (bytes/số file)"
    print(f"[verify] snapshot_id={man.get('snapshot_id')}  chế độ={mode}")
    issues = M.verify_manifest(man, full=full)
    _summary(man)
    if issues:
        print(f"[verify] DRIFT ({len(issues)}):")
        for i in issues:
            print(f"  ✗ {i}")
        print("[verify] KẾT QUẢ: FAIL — input đã lệch khỏi snapshot đóng băng.")
        return 1
    print("[verify] KẾT QUẢ: PASS — input khớp snapshot đóng băng.")
    return 0


def _summary(man: dict):
    print("------------------ SNAPSHOT ------------------")
    print(f"snapshot_id : {man.get('snapshot_id')}")
    print(f"frozen_at   : {man.get('frozen_at')}")
    for src in man.get("sources", []):
        present = [m for m in src["members"] if m.get("present", True)]
        missing = [m for m in src["members"] if not m.get("present", True)]
        tb = 0
        for m in present:
            tb += m.get("bytes", 0) + m.get("total_bytes", 0)
        ver = src.get("vintage")
        vtxt = ""
        if isinstance(ver, dict):
            vtxt = " · " + ", ".join(f"{k}={v}" for k, v in ver.items() if v)
        elif ver:
            vtxt = f" · {ver}"
        miss = f"  (thiếu {len(missing)})" if missing else ""
        print(f"  {src['id']:<16} {tb/1e6:8.1f} MB  "
              f"{len(present)} member{miss}{vtxt}")
    print("----------------------------------------------")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Freeze/verify snapshot input thô (E-DQ10)")
    ap.add_argument("--snapshot-id", default=M.SNAPSHOT_ID,
                    help=f"định danh snapshot (mặc định {M.SNAPSHOT_ID}, neo P9)")
    ap.add_argument("--quick", action="store_true",
                    help="bỏ băm nội dung (chỉ bytes/mtime) — nhanh, kém bất biến")
    ap.add_argument("--no-lock", action="store_true",
                    help="không khoá raw read-only (còn crawl tiếp)")
    ap.add_argument("--verify", action="store_true",
                    help="đối chiếu snapshot đang có thay vì tạo mới")
    ap.add_argument("--hashes", action="store_true",
                    help="với --verify: băm lại nội dung (đối chiếu đầy đủ)")
    args = ap.parse_args(argv)

    if args.verify:
        sys.exit(do_verify(full=args.hashes))
    sys.exit(do_freeze(args.snapshot_id, content=not args.quick, lock=not args.no_lock))


if __name__ == "__main__":
    main()
