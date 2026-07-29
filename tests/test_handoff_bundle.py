"""Bundle bàn giao F10 — neo toàn vẹn cho catalog interim (F18).

F18 chuyển output của `merge_catalog` từ `data/raw/` sang `data/interim/`, nên catalog
rời khỏi vùng phủ của MANIFEST frozen. Từ đó `HANDOFF.json` là chỗ DUY NHẤT còn ghi
lại nguồn gốc + hash của nó.
"""

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from ev_siting.data.evcs import export_handoff


def _stub_sources(tmp_path, monkeypatch):
    """Bộ input tối thiểu cho `export()`: catalog interim + telemetry + canonical."""
    catalog = tmp_path / "data" / "interim" / "evcs_catalog.csv"
    catalog.parent.mkdir(parents=True)
    catalog.write_text("code,name\nC.HNO0001,A\nC.HNO0002,B\n", encoding="utf-8")

    load_ts = tmp_path / "data" / "raw" / "evcs" / "load_ts.csv"
    load_ts.parent.mkdir(parents=True)
    load_ts.write_text("code,ts,n\nC.HNO0001,2026-07-20T00:00:00,1\n", encoding="utf-8")

    manifest_path = tmp_path / "data" / "raw" / "MANIFEST.json"
    manifest_path.write_text(json.dumps({"snapshot_id": "test-snapshot"}), encoding="utf-8")

    stations_dir = tmp_path / "data" / "interim" / "canonical" / "stations"
    connectors_dir = tmp_path / "data" / "interim" / "canonical" / "connectors"
    stations_dir.mkdir(parents=True)
    connectors_dir.mkdir(parents=True)
    stations = pd.DataFrame([{c: "x" for c in export_handoff.REQUIRED_STATION_COLS}])
    stations["station_code"] = "C.HNO0001"
    pd.DataFrame([{c: "x" for c in export_handoff.REQUIRED_CONNECTOR_COLS}]).to_parquet(
        connectors_dir / "part-0.parquet"
    )
    stations.to_parquet(stations_dir / "part-0.parquet")

    monkeypatch.setattr(export_handoff, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(export_handoff, "CATALOG_CSV", catalog)
    monkeypatch.setattr(export_handoff, "LOAD_TS", load_ts)
    monkeypatch.setattr(export_handoff, "STATIONS_DIR", stations_dir)
    monkeypatch.setattr(export_handoff, "CONNECTORS_DIR", connectors_dir)
    monkeypatch.setattr(export_handoff.snapshot_manifest, "MANIFEST_PATH", manifest_path)
    monkeypatch.setattr(export_handoff.snapshot_manifest, "load_manifest", lambda: {"snapshot_id": "test-snapshot"})
    monkeypatch.setattr(export_handoff.snapshot_manifest, "verify_manifest", lambda m, full=False: [])
    return catalog


def test_f18_handoff_records_interim_catalog_source(tmp_path, monkeypatch):
    catalog = _stub_sources(tmp_path, monkeypatch)
    out = export_handoff.export(tmp_path / "bundle")

    doc = json.loads((out / "HANDOFF.json").read_text(encoding="utf-8"))
    source = doc["catalog"]["source"]
    assert source["path"] == "data/interim/evcs_catalog.csv"
    assert source["derived_from_manifest_role"] == "evcs/catalog"
    assert source["bytes"] == catalog.stat().st_size
    # Bản copy trong bundle và file interim phía producer phải là cùng một nội dung.
    assert source["sha256"] == doc["catalog"]["sha256"] == hashlib.sha256(catalog.read_bytes()).hexdigest()
    assert doc["catalog"]["rows"] == 2


def test_f10_catalog_rewritten_mid_export_fails_instead_of_shipping_torn_copy(tmp_path, monkeypatch):
    """`merge_catalog` ghi không atomic — chạy song song lúc export = bundle rách."""
    catalog = _stub_sources(tmp_path, monkeypatch)
    real_copy2 = export_handoff.shutil.copy2

    def racing_copy2(src, dst, *args, **kwargs):
        result = real_copy2(src, dst, *args, **kwargs)
        if Path(src) == catalog:
            catalog.write_text("code,name\nC.HNO0001,A\n", encoding="utf-8")
        return result

    monkeypatch.setattr(export_handoff.shutil, "copy2", racing_copy2)
    with pytest.raises(SystemExit, match="F10 FAIL"):
        export_handoff.export(tmp_path / "bundle")

    assert not (tmp_path / "bundle").exists()
    assert not list(tmp_path.glob(".bundle.tmp-*")), "bỏ lại thư mục tạm nửa vời"
