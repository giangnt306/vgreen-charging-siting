"""Loader CÓ KIỂM CHỨNG cho bundle model-ready đã đóng băng (đối tác đọc của ``freeze_processed``).

Vì sao tồn tại: ``data/processed/`` root là MUTABLE và có thể LẪN SCOPE (build ``--national``
rồi ``--city hanoi`` ghi đè cùng đường dẫn). Mọi consumer (assess, MCLP) vì thế chỉ được đọc
``data/processed/<label>/<scope>/`` — và chỉ SAU KHI verify sha256 + bytes từng file so với
``FREEZE.json`` do ``freeze_processed`` ghi. Một byte lệch = bundle đã bị sửa tay sau freeze,
mọi con số downstream mất provenance ⇒ chặn cứng bằng ``SystemExit`` thay vì đọc tiếp.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .paths import PROCESSED_DIR

#: Label bundle sprint hiện hành — trùng default của freeze_processed và assess/params.FREEZE_LABEL.
DEFAULT_LABEL = "sprint2-2026-07-28"

#: 3 parquet mà consumer thực sự đọc — tên file khớp writer (freeze_processed copy giữ nguyên tên).
_CANDIDATES = "candidate_sites.parquet"
_COVERED0 = "covered0.parquet"
_COVERED0_OPERATIONAL = "covered0_operational.parquet"


@dataclass
class FrozenBundle:
    """Bundle đã qua verify — consumer cầm object này thay vì tự mở đường dẫn (khỏi quên verify)."""

    label: str
    scope: str
    dir: Path
    aoi: dict
    freeze: dict  # entry ``scopes.<scope>`` trong FREEZE.json (files, n_candidates, qa_gates, ...)
    candidates: pd.DataFrame
    covered0: pd.DataFrame
    covered0_operational: pd.DataFrame


def _fail(msg: str):
    # SystemExit (không phải ValueError) để CLI chết ngay với message rõ; prefix cố định
    # "FROZEN FAIL:" cho grep log + test match, cùng convention "FREEZE FAIL:" của writer.
    raise SystemExit(f"FROZEN FAIL: {msg}")


def _sha256(path: Path) -> str:
    # Đọc theo khối 1 MiB: parquet scope quốc gia nặng hàng trăm MB, không kéo cả file vào RAM.
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def verify_frozen(scope: str, label: str = DEFAULT_LABEL, processed_dir: Path | None = None) -> dict:
    """Verify sha256 + bytes TỪNG file của ``scope`` so với FREEZE.json; trả entry scope.

    ``processed_dir`` tham số hoá (default ``features.paths.PROCESSED_DIR``) để test dựng
    bundle giả trong tmp_path — logic verify thật được test không cần data thật.
    Mọi nhánh lỗi đều ``SystemExit`` prefix "FROZEN FAIL:" — không có chế độ "đọc tạm".
    """
    root = (Path(processed_dir) if processed_dir is not None else PROCESSED_DIR) / label
    fpath = root / "FREEZE.json"
    if not fpath.exists():
        _fail(f"không thấy {fpath} — bundle '{label}' chưa được đóng băng (chạy freeze_processed trước)")
    doc = json.loads(fpath.read_text(encoding="utf-8"))
    entry = (doc.get("scopes") or {}).get(scope)
    if entry is None:
        _fail(f"scope '{scope}' không có trong FREEZE.json (đã đóng băng: {sorted(doc.get('scopes') or {})})")

    scope_dir = root / scope
    for name, meta in (entry.get("files") or {}).items():
        p = scope_dir / name
        if not p.exists():
            _fail(f"thiếu file {name} trong {scope_dir} — bundle bị xoá/sửa sau khi freeze")
        # So bytes trước (rẻ, bắt được truncate/ghi đè khác cỡ) rồi mới băm nội dung.
        size = p.stat().st_size
        if size != meta.get("bytes"):
            _fail(f"{name}: bytes trên đĩa {size} != {meta.get('bytes')} khai trong FREEZE.json")
        digest = _sha256(p)
        if digest != meta.get("sha256"):
            _fail(f"{name}: sha256 {digest[:16]}… != {str(meta.get('sha256'))[:16]}… khai trong FREEZE.json")
    return entry


def load_frozen(scope: str, label: str = DEFAULT_LABEL, processed_dir: Path | None = None) -> FrozenBundle:
    """Verify rồi mới đọc 3 parquet model-ready từ thư mục bundle — đường vào DUY NHẤT cho consumer."""
    root = Path(processed_dir) if processed_dir is not None else PROCESSED_DIR
    entry = verify_frozen(scope, label=label, processed_dir=root)
    scope_dir = root / label / scope
    listed = entry.get("files") or {}
    for name in (_CANDIDATES, _COVERED0, _COVERED0_OPERATIONAL):
        # File có mặt trên đĩa nhưng KHÔNG được FREEZE.json liệt kê = chưa từng qua hash ⇒ cấm đọc.
        if name not in listed:
            _fail(f"{name} không được liệt kê trong FREEZE.json của scope '{scope}' — không đọc file chưa verify")
    return FrozenBundle(
        label=label,
        scope=scope,
        dir=scope_dir,
        aoi=entry.get("aoi") or {},
        freeze=entry,
        candidates=pd.read_parquet(scope_dir / _CANDIDATES),
        covered0=pd.read_parquet(scope_dir / _COVERED0),
        covered0_operational=pd.read_parquet(scope_dir / _COVERED0_OPERATIONAL),
    )
