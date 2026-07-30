#!/usr/bin/env python3
"""export_handoff.py — bundle ban giao lien-repo CO KIEM CHUNG (F10).

VI SAO CAN FILE NAY. Ban giao 21/07 sang repo evcs-dataset co hash khong khop
MANIFEST — khong truy duoc bundle dung tu snapshot nao (F10). Module nay la duong
ban giao DUY NHAT co kiem chung: verify FULL frozen manifest (E-DQ10) + schema
canonical + cam cot bay `gold_station_id` TRUOC khi copy, roi ghi `HANDOFF.json`
(tree-sha256 tung dataset, git_head/git_dirty, chinh sach toa do) de consumer
gate truoc khi dung. Bundle la thu muc MOI, ghi nguyen tu, KHONG ghi de bundle cu.

KHAC export_supply.py (khong va cham): export_supply xuat CSV cung sach cho
MCLP/QGIS tu canonical; export_handoff dong goi NGUYEN canonical + catalog +
telemetry + manifest thanh bundle lien-repo. Hai module khong chung output/consumer.

FX-05 (tang telemetry): canonical co the dung tang 720h (`EVCS_TS_DIR`) trong khi
`load_ts.csv` la tang 168h cua dot crawl 21-22/07 — dong goi nham tang la consumer
rebuild bronze ra tap tram khac + mat do mau khac. Tier suy tu TS_DIR; tang khac
168h BAT BUOC chi dinh run qua `--telemetry` hoac env `EVCS_TS_RUN` (fail-fast,
khong ghim sai tang roi phat hanh).

Chay:
    PYTHONPATH=src python -m ev_siting.data.evcs.export_handoff
    PYTHONPATH=src python -m ev_siting.data.evcs.export_handoff \
        --telemetry data/raw/evcs/timeseries_runs/load_ts_2026-07-29-full.csv
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

from ..provenance import manifest as snapshot_manifest
from .paths import CATALOG_CSV, CONNECTORS_DIR, LOAD_TS, PROJECT_ROOT, STATIONS_DIR, TS_DIR

# Hop dong toi thieu voi consumer — canonical PHAI mang du cac tang chat luong:
# P8 (op_status/access), E-DQ2 (physical_id/is_primary), E-DQ1 (coord_*),
# E-DQ3 (commune_code/admin_*), E-DQ4 (n_guns_installed/config_*).
REQUIRED_STATION_COLS = {
    "station_id", "station_code", "op_status", "access", "is_operational",
    "physical_id", "is_primary", "quality_flags", "lat_raw", "lng_raw",
    "coord_src", "coord_fix_dist_m", "coord_resolved",
    "commune_code", "admin_src", "admin_verdict",
    "n_guns_installed", "config_src", "config_resolved",
}
REQUIRED_CONNECTOR_COLS = {"station_id", "station_code", "connector_standard", "vehicle_class"}

# Chinh sach toa do cua canonical (E-DQ1 + E-DQ3, xem fix_coords.py +
# admin/enrich_stations.py) — ghi vao HANDOFF.json de consumer khong phai doan.
COORDINATE_POLICY = (
    "E-DQ1 placeholder-stack: coord_src in {evcs, official, placeholder}; "
    "placeholder -> coord_resolved=False, h3_r8=NULL, loai khoi cung; "
    "E-DQ3 trong tai bang ranh gioi xa VNSDI (COORD_OUTSIDE_ADMIN loai them)"
)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _tree_sha256(path: Path) -> tuple[str, int, int]:
    """Hash on dinh cho ca cay thu muc (ten tuong doi + size + sha256 tung file)."""
    h = hashlib.sha256()
    files = sorted(p for p in path.rglob("*") if p.is_file())
    total = 0
    for p in files:
        size = p.stat().st_size
        total += size
        h.update(f"{p.relative_to(path).as_posix()}\t{size}\t{_sha256(p)}\n".encode())
    return h.hexdigest(), len(files), total


def _build_provenance() -> dict[str, object]:
    """Ghi lai the he code da sinh canonical (F10 — bundle phai truy nguoc duoc)."""
    def run(*args: str) -> str | None:
        proc = subprocess.run(args, cwd=PROJECT_ROOT, text=True, capture_output=True)
        return proc.stdout.strip() if proc.returncode == 0 else None

    return {
        "git_head": run("git", "rev-parse", "HEAD"),
        "git_dirty": bool(run("git", "status", "--porcelain")),
        "coordinate_policy": COORDINATE_POLICY,
    }


def _resolve_telemetry(telemetry: Path | None) -> tuple[Path, str]:
    """FX-05: chon DUNG run telemetry cho tang canonical dang dung.

    Tier suy tu TS_DIR: `evcs_timeseries` = 168h (event, crawl 21-22/07, nguon
    `load_ts.csv`); tang 720h (luoi 5'/30 ngay) den tu run trong
    `data/raw/evcs/timeseries_runs/`. Chi tang 168h moi tu suy duoc nguon; tang
    khac phai chi dinh tuong minh — consumer rebuild bronze tu file nay, ghim
    sai tang la lech ca tap tram lan mat do mau."""
    tier = "720h" if TS_DIR.name.endswith("720h") else "168h"
    if telemetry is None:
        env = os.environ.get("EVCS_TS_RUN")
        if env:
            telemetry = Path(env)
        elif tier == "168h":
            telemetry = LOAD_TS
        else:
            raise SystemExit(
                f"F10/FX-05 FAIL: canonical dung tang telemetry {tier} ({TS_DIR.name}) "
                f"— truyen --telemetry <run.csv> (data/raw/evcs/timeseries_runs/) "
                f"hoac dat env EVCS_TS_RUN de bundle dong goi DUNG tang")
    if not telemetry.exists():
        raise SystemExit(f"F10 FAIL: thieu frozen telemetry {telemetry}")
    return telemetry.resolve(), tier


def _validate_sources() -> tuple[pd.DataFrame, pd.DataFrame, dict, int]:
    """Verify manifest FULL + catalog + schema canonical TRUOC khi copy bat cu gi."""
    manifest = snapshot_manifest.load_manifest()
    if manifest is None:
        raise SystemExit("F10 FAIL: thieu data/raw/MANIFEST.json — chay `make freeze` truoc")
    issues = snapshot_manifest.verify_manifest(manifest, full=True)
    if issues:
        raise SystemExit(f"F10 FAIL: frozen manifest lech ({issues[0]})")
    if not CATALOG_CSV.exists():
        raise SystemExit(f"F10 FAIL: thieu catalog {CATALOG_CSV}")
    with CATALOG_CSV.open(newline="", encoding="utf-8") as f:
        catalog = list(csv.DictReader(f))
    codes = [r.get("code") for r in catalog]
    if not catalog or any(not c for c in codes) or len(codes) != len(set(codes)):
        raise SystemExit("F10 FAIL: catalog rong, thieu code, hoac station_code trung")

    stations = pd.read_parquet(STATIONS_DIR)
    connectors = pd.read_parquet(CONNECTORS_DIR)
    missing_station = REQUIRED_STATION_COLS - set(stations.columns)
    missing_connector = REQUIRED_CONNECTOR_COLS - set(connectors.columns)
    if missing_station or missing_connector:
        raise SystemExit(
            f"F10 FAIL: canonical thieu cot station={sorted(missing_station)} "
            f"connector={sorted(missing_connector)}")
    if not stations["station_code"].is_unique:
        raise SystemExit("F10 FAIL: canonical station_code khong unique")
    if "gold_station_id" in stations.columns or "gold_station_id" in connectors.columns:
        raise SystemExit("F10 FAIL: cot bay gold_station_id khong duoc phep ban giao")
    return stations, connectors, manifest, len(catalog)


def export(out_dir: Path | None, telemetry: Path | None = None) -> Path:
    telemetry, tier = _resolve_telemetry(telemetry)
    stations, connectors, manifest, catalog_rows = _validate_sources()
    if out_dir is None:
        out_dir = (PROJECT_ROOT / "data" / "interim" / "handoff"
                   / f"evcs_vn_{manifest['snapshot_id']}")
    out_dir = out_dir.resolve()
    if out_dir.exists():
        raise SystemExit(f"F10 FAIL: output da ton tai, khong ghi de bundle: {out_dir}")
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_dir.parent / f".{out_dir.name}.tmp-{uuid.uuid4().hex}"
    try:
        (tmp / "canonical").mkdir(parents=True)
        shutil.copy2(CATALOG_CSV, tmp / "catalog.csv")
        # Consumer chi rebuild duoc bronze/liveness tu DUNG telemetry da kiem chung;
        # bo file nay la F10 moi di duoc nua duong (ten trong bundle co dinh la
        # load_ts.csv, nguon that + tier ghi trong HANDOFF.json).
        shutil.copy2(telemetry, tmp / "load_ts.csv")
        shutil.copy2(snapshot_manifest.MANIFEST_PATH, tmp / "SOURCE_MANIFEST.json")
        shutil.copytree(STATIONS_DIR, tmp / "canonical" / "stations")
        shutil.copytree(CONNECTORS_DIR, tmp / "canonical" / "connectors")

        station_hash, station_files, station_bytes = _tree_sha256(tmp / "canonical" / "stations")
        connector_hash, connector_files, connector_bytes = _tree_sha256(tmp / "canonical" / "connectors")
        try:
            telemetry_src = str(telemetry.relative_to(PROJECT_ROOT))
        except ValueError:
            telemetry_src = str(telemetry)
        handoff = {
            "schema": "vgreen.evcs-handoff/1",
            "created_at": datetime.now(timezone.utc).astimezone().isoformat(),
            "snapshot_id": manifest["snapshot_id"],
            "source_manifest_sha256": _sha256(snapshot_manifest.MANIFEST_PATH),
            "catalog": {"rows": catalog_rows,
                        "sha256": _sha256(tmp / "catalog.csv")},
            "telemetry": {"tier": tier, "source": telemetry_src,
                          "sha256": _sha256(tmp / "load_ts.csv"),
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
        (tmp / "HANDOFF.json").write_text(
            json.dumps(handoff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, out_dir)
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    print(f"[F10] bundle -> {out_dir}")
    print(f"[F10] stations={len(stations):,}; connectors={len(connectors):,}; "
          f"snapshot={manifest['snapshot_id']}; telemetry={tier}")
    return out_dir


def main():
    ap = argparse.ArgumentParser(
        description="F10: export bundle ban giao canonical co kiem chung")
    ap.add_argument("--out", type=Path, default=None,
                    help="thu muc bundle (mac dinh data/interim/handoff/evcs_vn_<snapshot_id>)")
    ap.add_argument("--telemetry", type=Path, default=None,
                    help="run telemetry dong goi vao bundle (FX-05 — bat buoc khi TS_DIR "
                         "la tang khac 168h; hoac dat env EVCS_TS_RUN)")
    args = ap.parse_args()
    export(args.out, args.telemetry)


if __name__ == "__main__":
    main()
