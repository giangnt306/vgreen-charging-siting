#!/usr/bin/env python3
"""poi_taxonomy.py — Ánh xạ `categories.primary` của Overture → `poi_class` của dự án.

**Điều kiện để so sánh có nghĩa: hai bên phải nói cùng một bảng chữ.** OSM phân lớp
theo *tag* (`osm/poi_semantics.CLASSES`); Overture phân lớp theo *taxonomy* riêng
(~2.000 leaf category, cây 3 tầng). Nếu đối chiếu `amenity=fuel` với `gas_station` bằng
mắt thì mọi chênh lệch đều có thể đổ cho "định nghĩa khác nhau" và phép đo mất giá trị.
Vì vậy ánh xạ được viết **tường minh, một chiều, có kiểm kê**: `unmapped_report()` liệt
kê mọi category chưa ánh xạ kèm số lượng, để không có lớp nào bị bỏ quên trong im lặng.

**Ba quyết định ánh xạ có hậu quả, ghi lại để không ai đảo ngược nhầm:**

1. **`grocery_store` KHÔNG phải `SUPERMARKET`.** Overture có `grocery_store` (24.518 ở
   cửa sổ quét) tách khỏi `supermarket`; ở VN `grocery_store` bắt phần lớn **tạp hoá
   mặt phố** — cùng loại cầu với `convenience_store`, không phải siêu thị có bãi đỗ ô
   tô. Gộp nó vào `SUPERMARKET` sẽ tự tạo ra "Overture hơn OSM 20×" một cách giả tạo.
   → `grocery_store`/`convenience_store` vào lớp phụ `CONVENIENCE`, **không** so với OSM.

2. **`PARK` là lớp MỚI, cả hai nguồn đều phải crawl lại.** Tầng POI của OSM trong repo
   này **chưa từng crawl `leisure=park`** — không phải nó thiếu, mà là **không có**
   (`overpass_poi.CATEGORIES` không có nhóm nào sinh ra lớp này). Đó là lý do "công viên
   thiếu nhiều" khi verify. `osm/poi_semantics` đã được bổ sung lớp `PARK`; ở đây gom
   các category công viên **đô thị đi bộ được** và loại `amusement_park`/`water_park`
   (khu vui chơi có vé — cầu sạc khác hẳn), `rv_park`/`mobile_home_park` (bãi đỗ xe nhà
   lưu động), `dog_park`/`skate_park` (tiện ích nhỏ trong công viên khác, đếm sẽ trùng).

3. **`ev_charging_station` bị loại khỏi mọi lớp.** Nó là **CUNG**, và tập cung đã có
   nguồn canon riêng (19.015 trạm). Để nó lọt vào covariate cầu là đúng kiểu rò rỉ mục
   tiêu mà `poi_recall.py` đã từ chối.
"""
from collections import Counter

#: Lớp dùng chung với OSM. Giữ nguyên chuỗi của `osm.poi_semantics.CLASSES` + `PARK`.
#: Lớp `CONVENIENCE` là **phụ**, chỉ Overture có nghĩa (OSM không crawl) — nó tồn tại để
#: `grocery_store` có chỗ đi mà không làm bẩn `SUPERMARKET`; `compare_osm` bỏ qua lớp này.
SHARED_CLASSES = ["FUEL", "PARKING_OFF", "MALL", "DEPT_STORE", "SUPERMARKET",
                  "MARKET", "APARTMENT", "PARK"]
AUX_CLASSES = ["CONVENIENCE"]
CLASSES = SHARED_CLASSES + AUX_CLASSES

#: `PARKING_STREET` **không** có bên Overture: taxonomy places không phân biệt đỗ ven
#: đường với bãi đỗ. Ghi lại để không ai đi tìm — so sánh `PARKING_STREET` là vô nghĩa.
NO_OVERTURE_EQUIVALENT = ["PARKING_STREET"]

#: Overture category (leaf, `categories.primary`) → poi_class.
#: Danh sách đóng, không dùng regex: leaf name của Overture đổi giữa các release, và một
#: pattern `%park%` sẽ nuốt cả `car_park`, `parking`, `theme_park`, `park_and_ride`.
CATEGORY_MAP = {
    # --- FUEL ---------------------------------------------------------------
    "gas_station": "FUEL",
    "truck_gas_station": "FUEL",
    "automotive_fuel_station": "FUEL",

    # --- PARKING (bãi đỗ đặt được trụ, không phải đỗ ven đường) --------------
    "parking": "PARKING_OFF",
    "parking_lot": "PARKING_OFF",
    "public_parking": "PARKING_OFF",
    "parking_garage": "PARKING_OFF",
    "garage_parking": "PARKING_OFF",
    "valet_parking": "PARKING_OFF",
    "park_and_ride": "PARKING_OFF",

    # --- MALL / DEPT_STORE --------------------------------------------------
    "shopping_center": "MALL",
    "shopping_mall": "MALL",
    "mall": "MALL",
    "outlet_mall": "MALL",
    "department_store": "DEPT_STORE",

    # --- SUPERMARKET (siêu thị có bãi đỗ ô tô) -------------------------------
    "supermarket": "SUPERMARKET",
    "superstore": "SUPERMARKET",
    "hypermarket": "SUPERMARKET",
    "warehouse_store": "SUPERMARKET",

    # --- MARKET (chợ truyền thống) ------------------------------------------
    "market": "MARKET",
    "public_market": "MARKET",
    "farmers_market": "MARKET",
    "night_market": "MARKET",
    "flea_market": "MARKET",
    "wholesale_market": "MARKET",

    # --- APARTMENT ----------------------------------------------------------
    "apartments": "APARTMENT",
    "apartment_building": "APARTMENT",
    "service_apartments": "APARTMENT",
    "condominium": "APARTMENT",
    "residential_building": "APARTMENT",

    # --- PARK (công viên đô thị, đi bộ được) --------------------------------
    "park": "PARK",
    "public_park": "PARK",
    "city_park": "PARK",
    "state_park": "PARK",
    "national_park": "PARK",
    "botanical_garden": "PARK",
    "garden": "PARK",

    # --- CONVENIENCE (phụ — xem docstring §1) -------------------------------
    "grocery_store": "CONVENIENCE",
    "convenience_store": "CONVENIENCE",
    "organic_grocery_store": "CONVENIENCE",
    "specialty_grocery_store": "CONVENIENCE",
}

#: Loại tường minh (KHÔNG phải "quên ánh xạ") — `unmapped_report` sẽ không kêu về chúng.
EXCLUDED = {
    "ev_charging_station",          # CUNG, không phải cầu — xem docstring §3
    "amusement_park", "water_park", "theme_park", "atv_recreation_park",
    "rv_park", "mobile_home_park", "trailer_park",
    # tiện ích NẰM TRONG một công viên khác — đếm sẽ trùng với `park` (539 `playground`
    # ở cửa sổ quét, phần lớn là sân chơi trong công viên đã có bản ghi riêng)
    "dog_park", "skate_park", "playground", "beer_garden", "community_gardens",
    "nursery_and_gardening", "home_and_garden", "gardener",
    "seafood_market", "health_market", "stock_market",  # cửa hàng/dịch vụ, không phải chợ
}


def classify(category):
    """`categories.primary` → poi_class, hoặc None nếu không thuộc lớp nào ta quan tâm."""
    if not category:
        return None
    return CATEGORY_MAP.get(str(category).strip().lower())


def unmapped_report(categories, top=40, keywords=None):
    """Kiểm kê category CHƯA ánh xạ, lọc theo từ khoá liên quan → list (category, n).

    Không có nó thì một release đổi `supermarket` thành `supermarket_store` sẽ làm lớp
    đó về 0 mà không ai biết — đúng kiểu hỏng im lặng mà F7/E-DQ10 tồn tại để chặn.
    """
    keywords = keywords or ("gas", "fuel", "petrol", "park", "garden", "market",
                            "mall", "shopping", "supermarket", "grocer", "store",
                            "apartment", "condo", "residential")
    # `categories.primary` khuyết ở ~6% place (Overture cho phép NULL) -> lọt NaN float
    c = Counter(x for x in categories if isinstance(x, str) and x)
    rows = [(cat, n) for cat, n in c.items()
            if cat not in CATEGORY_MAP and cat not in EXCLUDED
            and any(k in cat for k in keywords)]
    return sorted(rows, key=lambda r: -r[1])[:top]
