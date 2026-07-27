"""manifest.py — đặc tả nguồn thô + hàm băm/đối chiếu cho snapshot freeze (E-DQ10).

Một chỗ khai báo **mọi nguồn thô** mà pipeline tiêu thụ, cùng provenance (URL, giấy
phép, phiên bản/vintage, phạm vi không/thời gian). ``freeze_snapshot`` dùng module
này để sinh ``data/raw/MANIFEST.json``; ``validate`` (cổng QA evcs) dùng
``verify_manifest`` để **chặn drift** trên input đã đóng băng.

Nguyên tắc:
  - Blob thô bị .gitignore (``/data/``) → **manifest được commit** = lineage version-hoá.
  - File đơn: băm nội dung ``sha256`` (content-addressed, bất biến).
  - Thư mục nhiều file: cuộn thành **1 bản ghi** ``tree_sha256`` (băm danh sách đã sort
    ``relpath\tbytes\tsha256``) — manifest gọn mà vẫn content-addressed.
  - Đối chiếu **2 tầng**: *nhanh* (tồn tại + bytes + số file, không đọc nội dung — dùng
    ở cổng mỗi lần chạy) và *đầy đủ* (băm lại nội dung — chạy theo yêu cầu/CI).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

# provenance -> data -> ev_siting -> src -> <project root>
PROJECT_ROOT = Path(__file__).resolve().parents[4]
DATA = PROJECT_ROOT / "data"
RAW_DIR = DATA / "raw"
MANIFEST_PATH = RAW_DIR / "MANIFEST.json"

#: Neo P9. Cung chính thức khoá 2026-07-20 (khớp osmosis_replication_timestamp của
#: bản .pbf) → dùng làm định danh snapshot mặc định.
SNAPSHOT_ID = "2026-07-20"

#: Thư mục có <= ngưỡng này thì liệt kê từng file trong manifest; nhiều hơn thì chỉ
#: cuộn tổng hợp (n_files/total_bytes/tree_sha256) để manifest không phình.
LIST_MAX = 64

_CHUNK = 1 << 20  # 1 MiB


# --------------------------------------------------------------------------- #
# Băm                                                                          #
# --------------------------------------------------------------------------- #
def sha256_file(path: Path) -> str:
    """sha256 nội dung file (stream theo khối, an toàn với file GB)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(_CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).astimezone().isoformat()


def _dir_files(path: Path) -> list[Path]:
    return sorted(p for p in path.rglob("*") if p.is_file())


def _tree(path: Path, files: list[Path], content: bool):
    """Cuộn 1 thư mục -> (tree_sha256, per_file_records).

    ``content=True`` băm nội dung từng file (bất biến thật); ``False`` (chế độ
    --quick) chỉ dùng (relpath, bytes, mtime_ns) để soát nhanh cấu trúc.
    """
    h = hashlib.sha256()
    recs = []
    total = 0
    for p in files:
        st = p.stat()
        rel = p.relative_to(path).as_posix()
        total += st.st_size
        if content:
            fh = sha256_file(p)
            h.update(f"{rel}\t{st.st_size}\t{fh}\n".encode())
        else:
            fh = None
            h.update(f"{rel}\t{st.st_size}\t{st.st_mtime_ns}\n".encode())
        recs.append({"path": rel, "bytes": st.st_size,
                     **({"sha256": fh} if fh else {})})
    return h.hexdigest(), total, recs


# --------------------------------------------------------------------------- #
# Đặc tả nguồn                                                                 #
# --------------------------------------------------------------------------- #
def _osm_version(pbf: Path) -> dict:
    """Rút mốc replication từ header .pbf -> pin bản 'latest' về ngày/seq cụ thể."""
    try:
        import osmium
        r = osmium.io.Reader(str(pbf))
        hdr = r.header()
        ver = {
            "replication_timestamp": hdr.get("osmosis_replication_timestamp") or None,
            "replication_sequence": hdr.get("osmosis_replication_sequence_number") or None,
            "replication_base_url": hdr.get("osmosis_replication_base_url") or None,
        }
        r.close()
        return {k: v for k, v in ver.items() if v}
    except Exception as e:  # pyosmium thiếu / header trống -> fallback mtime
        return {"replication_timestamp": None, "note": f"pbf header unread: {e}"}


def source_specs() -> list[dict]:
    """Khai báo toàn bộ nguồn thô + provenance. Path có thể chưa tồn tại (freeze sẽ
    ghi ``present=false`` và bỏ qua) — cho phép freeze từng phần khi crawl dở."""
    from ..evcs import paths as evcs
    from ..vinfast_official import paths as vo
    from ..osm import paths as osm
    from ..worldpop import paths as wp
    from ..landuse import paths as lu

    # Provenance thời gian của evcs lấy từ quality_report (cửa sổ telemetry occupancy).
    evcs_window = {}
    if evcs.QUALITY_REPORT.exists():
        try:
            qr = json.loads(evcs.QUALITY_REPORT.read_text(encoding="utf-8"))
            evcs_window = {
                "time_window_start": qr.get("time_window_start"),
                "time_window_end": qr.get("time_window_end"),
            }
        except Exception:
            pass

    # Version chính thức lấy từ locators_meta.json (generation/count).
    vo_version = {}
    if vo.META_JSON.exists():
        try:
            m = json.loads(vo.META_JSON.read_text(encoding="utf-8"))
            vo_version = {"generation": m.get("generation"), "count": m.get("count")}
        except Exception:
            pass

    return [
        {
            "id": "evcs",
            "name": "evcs.vn — catalog trạm sạc công cộng + telemetry occupancy",
            "retrieval_url": "https://evcs.vn (API bản đồ nội bộ)",
            "license": "Proprietary (public map API, dùng cho nghiên cứu)",
            "vintage": "crawl 2026-07-21/22",
            "temporal_extent": evcs_window or None,
            "members": [
                {"role": "catalog", "path": evcs.CATALOG_DIR, "kind": "dir"},
                {"role": "occupancy_timeseries", "path": evcs.LOAD_TS, "kind": "file"},
            ],
        },
        {
            "id": "vinfast_official",
            "name": "vinfastauto.com — store locator (registry xác minh chéo)",
            "retrieval_url": "https://vinfastauto.com (store locator API)",
            "license": "Proprietary (public locator, ground-truth đối soát)",
            "vintage": vo_version or None,
            "members": [
                {"role": "locators_meta", "path": vo.META_JSON, "kind": "file"},
                {"role": "locators_full", "path": vo.BULK_JSON, "kind": "file"},
                {"role": "station_details", "path": vo.DETAIL_DIR, "kind": "dir"},
            ],
        },
        {
            "id": "osm",
            "name": "OpenStreetMap — Geofabrik VN dump (roads) + Overpass POI",
            "retrieval_url": osm.GEOFABRIK_URL,
            "license": "ODbL 1.0 (OpenStreetMap contributors)",
            "spatial_extent": {"bbox_min_lat_min_lon_max_lat_max_lon": list(osm.VN_BBOX)},
            "vintage": _osm_version(osm.PBF_PATH) if osm.PBF_PATH.exists() else None,
            "members": [
                {"role": "roads_pbf", "path": osm.PBF_PATH, "kind": "file"},
                {"role": "poi_overpass", "path": osm.POI_RAW_DIR, "kind": "dir"},
            ],
        },
        {
            "id": "worldpop",
            "name": "WorldPop — VN mật độ dân số 2020 constrained (~100m)",
            "retrieval_url": wp.WORLDPOP_URL,
            "license": "CC-BY 4.0",
            "vintage": "2020 constrained (BSGM), UN-unadjusted",
            "members": [
                {"role": "population_raster", "path": wp.POP_TIF, "kind": "file"},
            ],
        },
        {
            "id": "landuse",
            "name": "ESA WorldCover 10m + Overpass exclusion (land-use, P5)",
            "retrieval_url": lu.WC_BASE_URL,
            "license": "CC-BY 4.0 (WorldCover) / ODbL 1.0 (OSM exclusion)",
            "vintage": {"worldcover_version": lu.WC_VERSION, "worldcover_year": lu.WC_YEAR},
            "members": [
                {"role": "worldcover_tiles", "path": lu.WC_TILE_DIR, "kind": "dir"},
                {"role": "osm_exclusion", "path": lu.OSM_EXCL_DIR, "kind": "dir"},
            ],
        },
    ]


# --------------------------------------------------------------------------- #
# Dựng bản ghi member                                                         #
# --------------------------------------------------------------------------- #
def build_member(member: dict, content: bool) -> dict:
    """Dựng bản ghi manifest cho 1 member (file hoặc dir). Trả present=false nếu thiếu."""
    path: Path = member["path"]
    rel = path.relative_to(PROJECT_ROOT).as_posix()
    out = {"role": member["role"], "path": rel, "kind": member["kind"]}
    if not path.exists():
        out["present"] = False
        return out
    out["present"] = True

    if member["kind"] == "file":
        st = path.stat()
        out["bytes"] = st.st_size
        out["modified"] = _iso(st.st_mtime)
        if content:
            out["sha256"] = sha256_file(path)
    else:  # dir
        files = _dir_files(path)
        tree, total, recs = _tree(path, files, content)
        out["n_files"] = len(files)
        out["total_bytes"] = total
        out["tree_sha256"] = tree
        if len(files) <= LIST_MAX:
            out["files"] = recs
    return out


def build_manifest(snapshot_id: str, content: bool = True) -> dict:
    sources = []
    for spec in source_specs():
        # build_member đã đổi Path -> rel str nên bản ghi member là JSON-safe.
        s = {k: v for k, v in spec.items() if k != "members"}
        s["members"] = [build_member(m, content) for m in spec["members"]]
        sources.append(s)
    return {
        "schema": "vgreen.snapshot-manifest/1",
        "snapshot_id": snapshot_id,
        "frozen_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "hash_algo": "sha256",
        "content_hashed": content,
        "project_root": str(PROJECT_ROOT),
        "sources": sources,
    }


# --------------------------------------------------------------------------- #
# Đối chiếu                                                                    #
# --------------------------------------------------------------------------- #
def load_manifest() -> dict | None:
    if not MANIFEST_PATH.exists():
        return None
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def verify_manifest(manifest: dict, full: bool = False) -> list[str]:
    """Đối chiếu snapshot trên đĩa với manifest. Trả danh sách issue (rỗng = OK).

    ``full=False`` (mặc định, dùng ở cổng QA): chỉ soát tồn tại + bytes + số file
    (rẻ, không đọc nội dung). ``full=True``: băm lại nội dung/tree và so sánh.
    """
    issues: list[str] = []
    manifest_has_content = manifest.get("content_hashed", True)
    for src in manifest.get("sources", []):
        sid = src.get("id")
        for m in src.get("members", []):
            role = m.get("role")
            tag = f"{sid}/{role}"
            path = PROJECT_ROOT / m["path"]
            if not m.get("present", True):
                continue  # member vốn không có khi freeze -> bỏ qua
            if not path.exists():
                issues.append(f"{tag}: MẤT trên đĩa ({m['path']})")
                continue

            if m["kind"] == "file":
                size = path.stat().st_size
                if size != m.get("bytes"):
                    issues.append(f"{tag}: bytes lệch ({size} != {m.get('bytes')})")
                    continue
                if full and "sha256" in m:
                    if sha256_file(path) != m["sha256"]:
                        issues.append(f"{tag}: sha256 KHÔNG khớp (nội dung đã đổi)")
            else:  # dir
                files = _dir_files(path)
                if len(files) != m.get("n_files"):
                    issues.append(f"{tag}: số file lệch ({len(files)} != {m.get('n_files')})")
                    continue
                total = sum(p.stat().st_size for p in files)
                if total != m.get("total_bytes"):
                    issues.append(f"{tag}: total_bytes lệch ({total} != {m.get('total_bytes')})")
                    continue
                if full and manifest_has_content and "tree_sha256" in m:
                    tree, _, _ = _tree(path, files, content=True)
                    if tree != m["tree_sha256"]:
                        issues.append(f"{tag}: tree_sha256 KHÔNG khớp (1+ file đã đổi)")
    return issues
