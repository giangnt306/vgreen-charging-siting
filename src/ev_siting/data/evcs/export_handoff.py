"""Export bundle re-handoff có kiểm chứng cho consumer (F10).

Bundle là thư mục mới, không ghi đè snapshot consumer cũ. Trước khi copy, script
verify full frozen manifest và schema canonical; sau đó ghi HANDOFF.json chứa hash
mọi artefact để consumer có thể gate trước khi dùng.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .paths import CATALOG_CSV, CONNECTORS_DIR, LOAD_TS, PROJECT_ROOT, STATIONS_DIR
from ..provenance import manifest as snapshot_manifest

REQUIRED_STATION_COLS = {
    "station_id", "station_code", "op_status", "access", "is_operational",
    "physical_id", "is_primary", "quality_flags", "lat_raw", "lng_raw",
    "coord_src", "coord_fix_dist_m", "coord_resolved",
}
REQUIRED_CONNECTOR_COLS = {"station_id", "station_code", "connector_standard", "vehicle_class"}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _tree_sha256(path: Path) -> tuple[str, int, int]:
    h = hashlib.sha256()
    files = sorted(p for p in path.rglob("*") if p.is_file())
    total = 0
    for p in files:
        size = p.stat().st_size
        total += size
        h.update(f"{p.relative_to(path).as_posix()}\t{size}\t{_sha256(p)}\n".encode())
    return h.hexdigest(), len(files), total


def _build_provenance() -> dict[str, object]:
    """Record the code generation that produced canonical data (F20)."""
    def run(*args: str) -> str | None:
        proc = subprocess.run(args, cwd=PROJECT_ROOT, text=True, capture_output=True)
        return proc.stdout.strip() if proc.returncode == 0 else None

    return {
        "git_head": run("git", "rev-parse", "HEAD"),
        "git_dirty": bool(run("git", "status", "--porcelain")),
        "coordinate_policy": "raw-valid; exact-code official replace if invalid or drift>=200m; fuzzy never moves",
    }


def _validate_sources() -> tuple[pd.DataFrame, pd.DataFrame, dict, int]:
    manifest = snapshot_manifest.load_manifest()
    if manifest is None:
        raise SystemExit("F10 FAIL: thiếu data/raw/MANIFEST.json")
    issues = snapshot_manifest.verify_manifest(manifest, full=True)
    if issues:
        raise SystemExit(f"F10 FAIL: frozen manifest lệch ({issues[0]})")
    if not CATALOG_CSV.exists():
        raise SystemExit(f"F10 FAIL: thiếu catalog {CATALOG_CSV}")
    if not LOAD_TS.exists():
        raise SystemExit(f"F10 FAIL: thiếu frozen telemetry {LOAD_TS}")
    with CATALOG_CSV.open(newline="", encoding="utf-8") as f:
        catalog = list(csv.DictReader(f))
    codes = [r.get("code") for r in catalog]
    if not catalog or any(not c for c in codes) or len(codes) != len(set(codes)):
        raise SystemExit("F10 FAIL: raw catalog rỗng, thiếu code, hoặc station_code trùng")

    stations = pd.read_parquet(STATIONS_DIR)
    connectors = pd.read_parquet(CONNECTORS_DIR)
    missing_station = REQUIRED_STATION_COLS - set(stations.columns)
    missing_connector = REQUIRED_CONNECTOR_COLS - set(connectors.columns)
    if missing_station or missing_connector:
        raise SystemExit(
            f"F10 FAIL: canonical thiếu cột station={sorted(missing_station)} "
            f"connector={sorted(missing_connector)}"
        )
    if not stations["station_code"].is_unique:
        raise SystemExit("F10 FAIL: canonical station_code không unique")
    if "gold_station_id" in stations.columns or "gold_station_id" in connectors.columns:
        raise SystemExit("F10 FAIL: cột bẫy gold_station_id không được phép bàn giao")
    return stations, connectors, manifest, len(catalog)


def export(out_dir: Path) -> Path:
    stations, connectors, manifest, catalog_rows = _validate_sources()
    out_dir = out_dir.resolve()
    if out_dir.exists():
        raise SystemExit(f"F10 FAIL: output đã tồn tại, không ghi đè bundle: {out_dir}")
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_dir.parent / f".{out_dir.name}.tmp-{uuid.uuid4().hex}"
    try:
        (tmp / "canonical").mkdir(parents=True)
        shutil.copy2(CATALOG_CSV, tmp / "catalog.csv")
        # Consumer bronze/liveness can only be rebuilt from the same verified
        # telemetry. Omitting this file leaves F10 half-migrated.
        shutil.copy2(LOAD_TS, tmp / "load_ts.csv")
        shutil.copy2(snapshot_manifest.MANIFEST_PATH, tmp / "SOURCE_MANIFEST.json")
        shutil.copytree(STATIONS_DIR, tmp / "canonical" / "stations")
        shutil.copytree(CONNECTORS_DIR, tmp / "canonical" / "connectors")

        station_hash, station_files, station_bytes = _tree_sha256(tmp / "canonical" / "stations")
        connector_hash, connector_files, connector_bytes = _tree_sha256(tmp / "canonical" / "connectors")
        # F18 chuyển output của `merge_catalog` từ `data/raw/` sang `data/interim/`, nên
        # catalog KHÔNG còn nằm trong MANIFEST frozen (manifest chỉ phủ `data/raw/`).
        # HANDOFF.json vì thế là neo toàn vẹn DUY NHẤT còn lại cho artefact dẫn xuất
        # này: ghi hash + đường dẫn nguồn interim + role thô đã freeze mà nó dẫn ra.
        # Đối chiếu nguồn SAU khi copy: `merge_catalog` ghi không atomic (open("w")),
        # nên một lần merge chạy song song sẽ cho bản copy rách mà không gì báo.
        catalog_sha = _sha256(tmp / "catalog.csv")
        catalog_source_sha = _sha256(CATALOG_CSV)
        if catalog_sha != catalog_source_sha:
            raise SystemExit(
                f"F10 FAIL: {CATALOG_CSV} đổi trong lúc export (nguồn {catalog_source_sha[:12]} "
                f"≠ bản copy {catalog_sha[:12]}); dừng merge_catalog rồi chạy lại"
            )
        handoff = {
            "schema": "vgreen.evcs-handoff/1",
            "created_at": datetime.now(timezone.utc).astimezone().isoformat(),
            "snapshot_id": manifest["snapshot_id"],
            "source_manifest_sha256": _sha256(snapshot_manifest.MANIFEST_PATH),
            "catalog": {"rows": catalog_rows,
                        "sha256": catalog_sha,
                        "source": {"path": CATALOG_CSV.relative_to(PROJECT_ROOT).as_posix(),
                                   "sha256": catalog_source_sha,
                                   "bytes": CATALOG_CSV.stat().st_size,
                                   "derived_from_manifest_role": "evcs/catalog"}},
            "telemetry": {"sha256": _sha256(tmp / "load_ts.csv"),
                          "bytes": (tmp / "load_ts.csv").stat().st_size},
            "stations": {"rows": len(stations), "tree_sha256": station_hash,
                         "n_files": station_files, "bytes": station_bytes,
                         "required_columns": sorted(REQUIRED_STATION_COLS)},
            "connectors": {"rows": len(connectors), "tree_sha256": connector_hash,
                           "n_files": connector_files, "bytes": connector_bytes,
                           "required_columns": sorted(REQUIRED_CONNECTOR_COLS)},
            "forbidden_columns": ["gold_station_id"],
            "build_provenance": _build_provenance(),
        }
        (tmp / "HANDOFF.json").write_text(json.dumps(handoff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, out_dir)
    except BaseException:
        # BaseException, không phải Exception: cổng `SystemExit` ở trên nằm TRONG khối
        # này, và một lần Ctrl-C giữa copytree canonical cũng phải dọn, không để lại
        # `.<name>.tmp-*` nửa vời cạnh bundle thật.
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    print(f"[F10] bundle -> {out_dir}")
    print(f"[F10] stations={len(stations):,}; connectors={len(connectors):,}; snapshot={manifest['snapshot_id']}")
    return out_dir


def main():
    ap = argparse.ArgumentParser(description="F10: export verified EVCS canonical handoff bundle")
    ap.add_argument("--out", type=Path,
                    default=PROJECT_ROOT / "data" / "interim" / "handoff" / "evcs_vn_2026-07-20")
    args = ap.parse_args()
    export(args.out)


if __name__ == "__main__":
    main()
