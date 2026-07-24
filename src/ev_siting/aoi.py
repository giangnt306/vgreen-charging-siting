"""aoi.py — Vùng nghiên cứu (Area of Interest) dùng chung cho tầng dữ liệu.

MVP chạy trên **1 thành phố + buffer 5 km** ([data-layer-overview.md] §8 bước 2)
để demand ở rìa không bị coi là "chưa phủ" oan. Lớp ranh giới hành chính chưa có
(cột admin còn null 100% — §7 #3, enrich ở §8 bước 8), nên AOI ở đây được định
nghĩa bằng **tâm + bán kính** thay vì polygon ranh giới:

    AOI = hình tròn(tâm thành phố, radius_km)  +  vành buffer buffer_km

- `radius_km`  : lõi thành phố — nơi đo coverage/DoD.
- `buffer_km`  : vành ngoài — candidate **được phép** đặt (trạm ngoài rìa vẫn
                 phủ được lõi), nhưng đánh dấu `in_core = False`.

Khi §8 bước 8 (enrich admin) xong, chỉ cần thay `AOI.cells()` bằng spatial-join
với ranh giới xã/tỉnh; mọi module tiêu thụ AOI không phải sửa.

Dùng:
    from ev_siting.aoi import add_aoi_args, aoi_from_args, resolve_aoi
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import h3
import numpy as np

EARTH_R_KM = 6371.0088
H3_RES_R8 = 8
#: khoảng cách tâm–tâm 2 ô H3 res 8 kề nhau ở VN (`d = a·√3`) — xem P4.
H3_CENTER_SPACING_KM = 0.98

DEFAULT_BUFFER_KM = 5.0

#: Bounding box Việt Nam (gồm quần đảo xa bờ): (min_lat, min_lon, max_lat, max_lon).
#: Đồng bộ với ``ev_siting.data.osm.paths.VN_BBOX``.
VN_BBOX = (8.0, 102.0, 23.7, 110.0)

#: preset thành phố: name -> (lat, lng, radius_km lõi).
#: Bán kính lõi chọn theo phạm vi đô thị hoá liên tục, không theo ranh giới hành chính.
CITY_PRESETS: dict[str, tuple[float, float, float]] = {
    "hanoi": (21.0278, 105.8342, 25.0),
    "hcm": (10.7769, 106.7009, 25.0),
    "danang": (16.0544, 108.2022, 20.0),
    "haiphong": (20.8449, 106.6881, 20.0),
    "cantho": (10.0452, 105.7469, 15.0),
}

DEFAULT_CITY = "hanoi"


def haversine_km(lat1, lng1, lat2, lng2):
    """Khoảng cách great-circle (km). Nhận scalar hoặc mảng numpy (broadcast)."""
    lat1, lng1, lat2, lng2 = map(np.radians, (lat1, lng1, lat2, lng2))
    dlat, dlng = lat2 - lat1, lng2 - lng1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlng / 2) ** 2
    return 2 * EARTH_R_KM * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


@dataclass(frozen=True)
class AOI:
    """Vùng nghiên cứu = tròn(tâm, radius_km) + vành buffer_km."""

    name: str
    lat: float
    lng: float
    radius_km: float
    buffer_km: float = DEFAULT_BUFFER_KM

    @property
    def outer_radius_km(self) -> float:
        """Bán kính ngoài cùng (lõi + buffer) — biên thật của AOI."""
        return self.radius_km + self.buffer_km

    def bbox(self) -> tuple[float, float, float, float]:
        """Bounding box bao AOI: (min_lat, min_lon, max_lat, max_lon).

        Dùng cho query Overpass / cắt cửa sổ raster (rộng hơn hình tròn một chút).
        """
        dlat = self.outer_radius_km / 111.32
        dlon = self.outer_radius_km / (111.32 * math.cos(math.radians(self.lat)))
        return (self.lat - dlat, self.lng - dlon, self.lat + dlat, self.lng + dlon)

    def dist_km(self, lat, lng):
        """Khoảng cách từ tâm AOI tới (lat, lng), km."""
        return haversine_km(self.lat, self.lng, lat, lng)

    def contains(self, lat, lng):
        """True nếu điểm nằm trong AOI (lõi **hoặc** buffer)."""
        return self.dist_km(lat, lng) <= self.outer_radius_km

    def in_core(self, lat, lng):
        """True nếu điểm nằm trong lõi thành phố (không tính buffer)."""
        return self.dist_km(lat, lng) <= self.radius_km

    def cells(self) -> list[str]:
        """Danh sách ô H3 res 8 có **tâm ô** nằm trong AOI (đã sắp xếp)."""
        center = h3.latlng_to_cell(self.lat, self.lng, H3_RES_R8)
        k = int(math.ceil(self.outer_radius_km / H3_CENTER_SPACING_KM)) + 1
        disk = list(h3.grid_disk(center, k))
        latlng = np.array([h3.cell_to_latlng(c) for c in disk])
        keep = self.dist_km(latlng[:, 0], latlng[:, 1]) <= self.outer_radius_km
        return sorted(c for c, ok in zip(disk, keep) if ok)

    def to_dict(self) -> dict:
        """Metadata AOI để ghi vào report/sidecar (truy vết cấu hình chạy)."""
        s, w, n, e = self.bbox()
        return {
            "name": self.name,
            "center": [round(self.lat, 6), round(self.lng, 6)],
            "radius_km": self.radius_km,
            "buffer_km": self.buffer_km,
            "outer_radius_km": self.outer_radius_km,
            "bbox": [round(x, 5) for x in (s, w, n, e)],
        }

    def __str__(self) -> str:
        return (f"AOI({self.name}: {self.lat:.4f},{self.lng:.4f} "
                f"r={self.radius_km}km +{self.buffer_km}km buffer)")


class NationalAOI:
    """AOI toàn quốc — không dùng hình tròn mà lấy **toàn bộ lưới `demand_h3`**.

    Cùng giao diện với ``AOI`` (duck-typing): mọi module tiêu thụ chỉ gọi
    ``bbox()``/``contains()``/``in_core()``/``cells()``/``to_dict()`` nên không cần
    biết đang chạy city hay national. `contains`/`in_core` = kiểm tra trong bbox VN
    (không có khái niệm buffer ở national). `cells()` đọc trực tiếp lưới quốc gia từ
    ``demand_h3`` (268k ô res 8) thay vì sinh disk từ tâm.
    """

    def __init__(self, name: str = "vietnam", bbox: tuple = VN_BBOX):
        self.name = name
        self._bbox = bbox
        s, w, n, e = bbox
        self.lat, self.lng = (s + n) / 2, (w + e) / 2
        self.buffer_km = 0.0

    @property
    def outer_radius_km(self) -> float:
        # nửa đường chéo bbox (km) — chỉ để tương thích, national không dùng disk.
        s, w, n, e = self._bbox
        return haversine_km(s, w, n, e) / 2

    def bbox(self):
        return self._bbox

    def contains(self, lat, lng):
        s, w, n, e = self._bbox
        return (np.asarray(lat) >= s) & (np.asarray(lat) <= n) & \
               (np.asarray(lng) >= w) & (np.asarray(lng) <= e)

    def in_core(self, lat, lng):
        return self.contains(lat, lng)

    def cells(self) -> list[str]:
        """Lưới quốc gia = mọi ô trong `demand_h3` (đã có sẵn, phủ toàn VN)."""
        import pandas as pd
        from ev_siting.data.worldpop.paths import DEMAND_H3
        if not DEMAND_H3.exists():
            raise SystemExit(f"national AOI cần {DEMAND_H3} — chạy build_demand_h3 trước")
        return sorted(pd.read_parquet(DEMAND_H3, columns=["h3_r8"])["h3_r8"].tolist())

    def to_dict(self) -> dict:
        s, w, n, e = self._bbox
        return {"name": self.name, "scope": "national",
                "bbox": [round(x, 5) for x in (s, w, n, e)]}

    def __str__(self) -> str:
        return f"NationalAOI({self.name}: bbox={self._bbox})"


def resolve_aoi(city: str | None = None, lat: float | None = None,
                lng: float | None = None, radius_km: float | None = None,
                buffer_km: float | None = None, national: bool = False):
    """Dựng AOI từ preset thành phố, cho phép override tâm/bán kính.

    `national=True` → trả về ``NationalAOI`` (toàn VN, bỏ qua city/tâm/bán kính).
    """
    if national:
        return NationalAOI()
    city = (city or DEFAULT_CITY).lower()
    if city not in CITY_PRESETS and (lat is None or lng is None):
        raise SystemExit(
            f"AOI '{city}' không có trong preset {sorted(CITY_PRESETS)} "
            f"— truyền --aoi-lat/--aoi-lng để tự định nghĩa")
    p_lat, p_lng, p_r = CITY_PRESETS.get(city, (lat, lng, 20.0))
    return AOI(
        name=city,
        lat=p_lat if lat is None else lat,
        lng=p_lng if lng is None else lng,
        radius_km=p_r if radius_km is None else radius_km,
        buffer_km=DEFAULT_BUFFER_KM if buffer_km is None else buffer_km,
    )


def add_aoi_args(parser):
    """Gắn nhóm tham số AOI chung cho mọi CLI của pipeline."""
    g = parser.add_argument_group("AOI (vùng nghiên cứu)")
    g.add_argument("--national", action="store_true",
                   help="chạy toàn quốc (dùng lưới demand_h3 quốc gia; bỏ qua --city/tâm/bán kính)")
    g.add_argument("--city", default=DEFAULT_CITY,
                   help=f"preset thành phố {sorted(CITY_PRESETS)} (mặc định: {DEFAULT_CITY})")
    g.add_argument("--aoi-lat", type=float, default=None, help="override vĩ độ tâm")
    g.add_argument("--aoi-lng", type=float, default=None, help="override kinh độ tâm")
    g.add_argument("--radius-km", type=float, default=None, help="override bán kính lõi (km)")
    g.add_argument("--buffer-km", type=float, default=None,
                   help=f"vành buffer quanh lõi (km, mặc định {DEFAULT_BUFFER_KM})")
    return parser


def aoi_from_args(args):
    """Dựng AOI từ namespace argparse đã gắn `add_aoi_args`."""
    return resolve_aoi(city=args.city, lat=args.aoi_lat, lng=args.aoi_lng,
                       radius_km=args.radius_km, buffer_km=args.buffer_km,
                       national=getattr(args, "national", False))
