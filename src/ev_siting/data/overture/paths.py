"""Canonical filesystem paths cho tầng Overture Places.

Cùng quy ước với `ev_siting.data.osm.paths`: mọi thứ neo vào `PROJECT_ROOT` suy từ vị
trí file này, nên pipeline chạy giống nhau bất kể working directory. Tải/phản hồi bất
biến nằm dưới `data/raw/overture/`; artefact dẫn xuất nằm dưới `data/interim/overture/`.

    PYTHONPATH=src python -m ev_siting.data.overture.fetch_places
    PYTHONPATH=src python -m ev_siting.data.overture.build_poi
    PYTHONPATH=src python -m ev_siting.data.overture.compare_osm
"""
from pathlib import Path

# overture -> data -> ev_siting -> src -> <project root>
PROJECT_ROOT = Path(__file__).resolve().parents[4]

DATA = PROJECT_ROOT / "data"

# --- nguồn ---
#: Bucket public của Overture (requester KHÔNG trả phí, không cần credentials).
S3_BUCKET = "overturemaps-us-west-2"
S3_REGION = "us-west-2"
#: Release đang pin. Overture phát hành hàng tháng và **xoá release cũ sau ~1 năm**;
#: pin để số liệu đối chiếu tái lập được, nâng có chủ đích bằng `--release`.
RELEASE = "2026-07-22.0"


def places_url(release: str = RELEASE) -> str:
    """URL S3 của theme `places/place` cho một release."""
    return f"s3://{S3_BUCKET}/release/{release}/theme=places/type=place/*"


def releases_listing_url() -> str:
    """Endpoint liệt kê công khai của bucket — dùng để hỏi release mới nhất."""
    return f"https://{S3_BUCKET}.s3.amazonaws.com/?list-type=2&delimiter=/&prefix=release/"


# --- raw, bất biến (data/raw/overture) ---
RAW_DIR = DATA / "raw" / "overture"


def places_raw(release: str = RELEASE) -> Path:
    """Parquet thô: MỌI place trong `VN_BBOX`, giữ nguyên `category` gốc của Overture."""
    return RAW_DIR / f"places_vn_bbox_{release}.parquet"


def fetch_meta(release: str = RELEASE) -> Path:
    """Sidecar mô tả lần quét (release, bbox, câu SQL, số dòng, thời điểm)."""
    return RAW_DIR / f"places_vn_bbox_{release}.meta.json"


# --- dẫn xuất (data/interim/overture) ---
INTERIM_DIR = DATA / "interim" / "overture"
POI_POINTS = INTERIM_DIR / "overture_poi_points.parquet"   # 1 dòng/POI trong VN, đã phân lớp
POI_OUTSIDE_VN = INTERIM_DIR / "overture_poi_outside_vn.parquet"  # bbox-spill bị cắt (audit)
POI_H3 = INTERIM_DIR / "overture_poi_h3.parquet"           # bảng LỚP POI theo ô H3
BUILD_REPORT = INTERIM_DIR / "overture_build_report.json"

# --- đối chiếu 2 nguồn ---
COMPARE_REPORT = INTERIM_DIR / "osm_vs_overture.json"
COMPARE_MD = INTERIM_DIR / "osm_vs_overture.md"
COMPARE_PAIRS = INTERIM_DIR / "osm_vs_overture_pairs.parquet"  # cặp ghép + phía lẻ

#: Bán kính coi 2 điểm ở 2 nguồn là CÙNG một địa điểm vật lý. 50 m (không phải 30 m như
#: `poi_semantics.DUP_RADIUS_M`): ghép **liên nguồn** phải chịu thêm sai số vị trí của
#: Overture (điểm Meta/Microsoft lấy từ POS/địa chỉ, không phải khảo sát thực địa).
MATCH_RADIUS_M = 50.0
#: Bán kính phụ để chứng minh phần "chỉ có ở 1 nguồn" không phải hiệu ứng dung sai.
MATCH_RADII_M = (50.0, 100.0, 200.0)


def ensure_dirs():
    """Tạo mọi thư mục output (idempotent)."""
    for d in (RAW_DIR, INTERIM_DIR):
        d.mkdir(parents=True, exist_ok=True)
