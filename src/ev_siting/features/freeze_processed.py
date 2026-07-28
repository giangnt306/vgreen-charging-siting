#!/usr/bin/env python3
"""Đóng băng `data/processed/` thành một bundle sprint bất biến, có provenance.

Cùng tinh thần với `E-DQ10` (`data/raw/MANIFEST.json`) và `F10`
(`export_handoff.py`), nhưng cho tầng **model-ready**: thứ mà MCLP thực sự đọc.

Vì sao cần: `build_covered0` và `build_candidates` ghi vào **cùng một đường dẫn**
cho mọi AOI (`covered0.parquet`, `candidate_sites.parquet`). Chạy `--national`
rồi `--city hanoi` để lại `data/processed/` **lẫn scope** — baseline của cả nước
đứng cạnh candidate của một thành phố. Đó là input câm cho MCLP: mọi phép "phủ
thêm bao nhiêu" đều sai mà không có gì báo. Script này **chặn** đúng lỗi đó
trước khi đóng băng (`_assert_same_aoi`).

Chạy (mỗi scope một lần, sau khi đã build xong scope đó):
    make covered0-national && make candidates-national
    PYTHONPATH=src python -m ev_siting.features.freeze_processed --label sprint2-2026-07-28

    make landuse CITY=hanoi && make covered0 CITY=hanoi && make candidates CITY=hanoi
    PYTHONPATH=src python -m ev_siting.features.freeze_processed --label sprint2-2026-07-28
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from ev_siting.data.evcs.paths import STATIONS_DIR
from ev_siting.data.provenance import manifest as snapshot_manifest

from .paths import (
    CANDIDATE_GEOJSON,
    CANDIDATE_SITES,
    COVERED0_GEOJSON,
    COVERED0_OPERATIONAL_GEOJSON,
    COVERED0_OPERATIONAL_SITES,
    COVERED0_SITES,
    PROCESSED_DIR,
    R_BASELINE_KM,
)

#: Artefact bắt buộc có mặt — thiếu bất kỳ file nào = scope build chưa xong.
_REQUIRED = [
    CANDIDATE_SITES,
    CANDIDATE_GEOJSON,
    COVERED0_SITES,
    COVERED0_GEOJSON,
    COVERED0_OPERATIONAL_SITES,
    COVERED0_OPERATIONAL_GEOJSON,
]
_CAND_QA = Path(str(CANDIDATE_SITES).replace(".parquet", "_qa.json"))
_COV_REPORT = Path(str(COVERED0_SITES).replace(".parquet", "_report.json"))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _tree_sha256(path: Path) -> str:
    """Băm cây thư mục (đường dẫn + kích thước + nội dung) — dùng cho canonical."""
    h = hashlib.sha256()
    for p in sorted(q for q in path.rglob("*") if q.is_file()):
        h.update(f"{p.relative_to(path).as_posix()}\t{p.stat().st_size}\t{_sha256(p)}\n".encode())
    return h.hexdigest()


def _git(*args: str) -> str | None:
    proc = subprocess.run(("git", *args), cwd=PROCESSED_DIR.parents[1], text=True, capture_output=True)
    return proc.stdout.strip() if proc.returncode == 0 else None


def _assert_same_aoi(cand_qa: dict, cov_report: dict) -> dict:
    """Cổng chặn: candidate và covered0 phải cùng MỘT AOI.

    So cả `name` lẫn hình học (`bbox`/`radius_km`) — đổi bán kính mà giữ nguyên
    tên vẫn là hai vùng khác nhau, và MCLP không có cách nào tự phát hiện.
    """
    a, b = cand_qa.get("aoi") or {}, cov_report.get("aoi") or {}
    if not a or not b:
        raise SystemExit("FREEZE FAIL: report thiếu khối `aoi`; build lại candidate/covered0")
    keys = ("name", "scope", "radius_km", "buffer_km", "bbox")
    lech = [k for k in keys if a.get(k) != b.get(k)]
    if lech:
        raise SystemExit(
            f"FREEZE FAIL: candidate ({a.get('name')}) và covered0 ({b.get('name')}) khác AOI "
            f"ở {lech} — data/processed/ đang LẪN SCOPE. Build lại cả hai cho cùng một AOI."
        )
    return a


def _load_reports() -> tuple[dict, dict, dict]:
    missing = [p.name for p in (*_REQUIRED, _CAND_QA, _COV_REPORT) if not p.exists()]
    if missing:
        raise SystemExit(f"FREEZE FAIL: thiếu artefact {missing}; chạy covered0 + candidates trước")
    cand_qa = json.loads(_CAND_QA.read_text(encoding="utf-8"))
    cov_report = json.loads(_COV_REPORT.read_text(encoding="utf-8"))
    if cand_qa.get("overall") != "PASS":
        raise SystemExit(f"FREEZE FAIL: candidate QA = {cand_qa.get('overall')}; không đóng băng bản FAIL")
    return cand_qa, cov_report, _assert_same_aoi(cand_qa, cov_report)


def freeze(label: str, force: bool = False) -> Path:
    cand_qa, cov_report, aoi = _load_reports()
    scope = aoi.get("name") or "unknown"
    root = PROCESSED_DIR / label
    scope_dir = root / scope
    if scope_dir.exists() and not force:
        raise SystemExit(f"FREEZE FAIL: {scope_dir} đã tồn tại (dùng --force để ghi đè có chủ đích)")

    tmp = root / f".{scope}.tmp-{uuid.uuid4().hex}"
    tmp.mkdir(parents=True)
    try:
        files = {}
        for src in (*_REQUIRED, _CAND_QA, _COV_REPORT):
            shutil.copy2(src, tmp / src.name)
            files[src.name] = {"sha256": _sha256(tmp / src.name), "bytes": (tmp / src.name).stat().st_size}
        if scope_dir.exists():
            shutil.rmtree(scope_dir)
        tmp.replace(scope_dir)
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise

    manifest = snapshot_manifest.load_manifest()
    entry = {
        "aoi": aoi,
        "files": files,
        "n_candidates": cand_qa.get("n_candidates"),
        "R_km": cand_qa.get("R_km", R_BASELINE_KM),
        "qa_gates": {c["gate"]: c["status"] for c in cand_qa.get("checks", [])},
        "n_covered0": cov_report.get("n_covered0"),
        "n_covered0_operational": cov_report.get("n_covered0_operational_only"),
        "covered0_baseline_def": cov_report.get("baseline_def"),
    }

    fpath = root / "FREEZE.json"
    doc = json.loads(fpath.read_text(encoding="utf-8")) if fpath.exists() else {}
    doc.setdefault("schema", "vgreen.processed-freeze/1")
    doc["label"] = label
    doc["frozen_at"] = datetime.now(timezone.utc).astimezone().isoformat()
    doc["snapshot_id"] = (manifest or {}).get("snapshot_id")
    doc["canonical_tree_sha256"] = _tree_sha256(STATIONS_DIR)
    doc["build_provenance"] = {"git_head": _git("rev-parse", "HEAD"), "git_dirty": bool(_git("status", "--porcelain"))}
    doc.setdefault("scopes", {})[scope] = entry
    tmp_f = fpath.with_suffix(f".json.tmp-{uuid.uuid4().hex}")
    tmp_f.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp_f, fpath)

    print(f"[freeze] {scope} -> {scope_dir}  ({len(files)} file)")
    print(
        f"[freeze] candidate={entry['n_candidates']} · covered0={entry['n_covered0']} "
        f"(operational {entry['n_covered0_operational']}) · R={entry['R_km']}km"
    )
    print(f"[freeze] scopes đã đóng băng: {sorted(doc['scopes'])} -> {fpath}")
    return scope_dir


def main():
    ap = argparse.ArgumentParser(description="Đóng băng data/processed/ thành bundle sprint bất biến")
    ap.add_argument("--label", default="sprint2-2026-07-28", help="tên bundle (thư mục con của data/processed/)")
    ap.add_argument("--force", action="store_true", help="ghi đè scope đã đóng băng")
    args = ap.parse_args()
    freeze(args.label, force=args.force)


if __name__ == "__main__":
    main()
