"""Loader kiểm chứng bundle frozen (read_frozen) — dựng bundle giả tí hon trong tmp_path.

Vì sao test kỹ nhánh fail: read_frozen là chốt chặn duy nhất giữa consumer (assess/MCLP)
và một bundle bị sửa tay sau freeze; đọc nhầm một byte là mọi con số downstream mất provenance.
"""

import hashlib
import json

import pandas as pd
import pytest

from ev_siting.features.read_frozen import load_frozen, verify_frozen

_LABEL = "sprint2-2026-07-28"
_SCOPE = "vietnam"
_AOI = {"name": _SCOPE, "scope": "national", "bbox": [8.0, 102.0, 23.7, 110.0]}


def _make_bundle(processed_dir, scope=_SCOPE, label=_LABEL):
    """Bundle giả: 3 parquet nhỏ + FREEZE.json với sha256/bytes THẬT (tính bằng hashlib)."""
    scope_dir = processed_dir / label / scope
    scope_dir.mkdir(parents=True)
    frames = {
        "candidate_sites.parquet": pd.DataFrame({"cell": ["c1", "c2"], "lat": [21.00, 21.05], "lng": [105.80, 105.85]}),
        "covered0.parquet": pd.DataFrame({"station_id": ["vn-c-a", "vn-c-b", "vn-c-c"], "num_connectors": [2, 4, 1]}),
        "covered0_operational.parquet": pd.DataFrame({"station_id": ["vn-c-a"], "num_connectors": [2]}),
    }
    files = {}
    for name, df in frames.items():
        path = scope_dir / name
        df.to_parquet(path)
        raw = path.read_bytes()
        files[name] = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    doc = {
        "schema": "vgreen.processed-freeze/1",
        "label": label,
        "snapshot_id": "2026-07-20",
        "scopes": {scope: {"aoi": _AOI, "files": files, "n_candidates": 2, "n_covered0": 3}},
    }
    freeze_path = processed_dir / label / "FREEZE.json"
    freeze_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return scope_dir, freeze_path


def _expect_frozen_fail(fn):
    with pytest.raises(SystemExit) as e:
        fn()
    # Hợp đồng message: mọi nhánh lỗi bắt đầu bằng prefix cố định (grep log + CLI chết rõ ràng).
    assert str(e.value).startswith("FROZEN FAIL:")
    return str(e.value)


def test_load_ok_tra_du_3_df_va_aoi(tmp_path):
    _make_bundle(tmp_path)
    bundle = load_frozen(_SCOPE, label=_LABEL, processed_dir=tmp_path)
    assert len(bundle.candidates) == 2
    assert len(bundle.covered0) == 3
    assert len(bundle.covered0_operational) == 1
    assert bundle.aoi["name"] == _SCOPE and bundle.aoi["bbox"] == _AOI["bbox"]
    assert bundle.label == _LABEL and bundle.scope == _SCOPE
    assert bundle.dir == tmp_path / _LABEL / _SCOPE
    assert set(bundle.freeze["files"]) == {
        "candidate_sites.parquet",
        "covered0.parquet",
        "covered0_operational.parquet",
    }


def test_sua_1_byte_parquet_bi_chan(tmp_path):
    scope_dir, _ = _make_bundle(tmp_path)
    target = scope_dir / "covered0.parquet"
    raw = bytearray(target.read_bytes())
    raw[len(raw) // 2] ^= 0xFF  # lật 1 bit giữa file: bytes giữ nguyên, sha256 phải lệch
    target.write_bytes(bytes(raw))
    msg = _expect_frozen_fail(lambda: load_frozen(_SCOPE, label=_LABEL, processed_dir=tmp_path))
    assert "sha256" in msg and "covered0.parquet" in msg


def test_scope_la_bi_chan(tmp_path):
    _make_bundle(tmp_path)
    msg = _expect_frozen_fail(lambda: verify_frozen("hanoi", label=_LABEL, processed_dir=tmp_path))
    assert "hanoi" in msg


def test_thieu_file_bi_chan(tmp_path):
    scope_dir, _ = _make_bundle(tmp_path)
    (scope_dir / "candidate_sites.parquet").unlink()
    msg = _expect_frozen_fail(lambda: load_frozen(_SCOPE, label=_LABEL, processed_dir=tmp_path))
    assert "thiếu file" in msg and "candidate_sites.parquet" in msg


def test_bytes_lech_trong_freeze_bi_chan(tmp_path):
    _, freeze_path = _make_bundle(tmp_path)
    doc = json.loads(freeze_path.read_text(encoding="utf-8"))
    doc["scopes"][_SCOPE]["files"]["covered0_operational.parquet"]["bytes"] += 1
    freeze_path.write_text(json.dumps(doc), encoding="utf-8")
    msg = _expect_frozen_fail(lambda: verify_frozen(_SCOPE, label=_LABEL, processed_dir=tmp_path))
    assert "bytes" in msg and "covered0_operational.parquet" in msg
