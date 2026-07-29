"""Paths cho tầng trình bày (bản đồ hiện trạng, heatmap, hình cho báo cáo).

Cùng quy ước với ``ev_siting.models.paths``: neo ``PROJECT_ROOT`` theo vị trí file,
ghi ra ``outputs/`` (gitignored, tái lập được).

**Ranh giới cần giữ.** GeoJSON *bàn giao dữ liệu* (``candidate_sites.geojson``,
``covered0.geojson``) do tầng feature sinh và sống ở ``data/processed/`` — chúng là
một phần hợp đồng schema, không phải hình vẽ. ``viz/`` chỉ sinh artefact *trình bày*
từ những file đó; nó không được là nơi thứ hai định nghĩa nội dung dữ liệu.

Hình nào thực sự đi vào báo cáo thì **copy có chủ đích** sang ``reports/figures/``
(được commit) — xem ``reports/README.md``.
"""

from pathlib import Path

# viz -> ev_siting -> src -> <project root>
PROJECT_ROOT = Path(__file__).resolve().parents[3]

OUTPUTS_DIR = PROJECT_ROOT / "outputs"
FIGURES_DIR = OUTPUTS_DIR / "figures"  # .png/.svg sinh ra từ script
MAPS_DIR = OUTPUTS_DIR / "maps"  # .geojson/.html phục vụ xem bản đồ

#: Nơi hình đã chọn được commit kèm bài viết.
REPORTS_FIGURES_DIR = PROJECT_ROOT / "reports" / "figures"


def ensure_dirs():
    for d in (FIGURES_DIR, MAPS_DIR):
        d.mkdir(parents=True, exist_ok=True)
