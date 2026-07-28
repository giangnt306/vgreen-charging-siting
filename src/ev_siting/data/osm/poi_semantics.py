#!/usr/bin/env python3
"""poi_semantics.py — Ngữ nghĩa POI (E-DQ7c): phân lớp + khử trùng + suy dẫn cột.

**C1 — tách TRÍCH XUẤT khỏi CHÍNH SÁCH** (nguyên tắc R1 của E-DQ7b, áp cho POI).
Trước đây `build_osm_h3._COUNT_COL` gộp 5 nhóm crawl thành 3 vô hướng **ngay trong
khâu gộp**: `mall`+`apartments`+`retail` → `n_poi`. Đổi định nghĩa = sửa code gộp,
và không hoàn tác được vì bảng ra chỉ còn 3 số. Nay `build_osm_h3.py` ghi **bảng LỚP**
`osm_poi_h3.parquet` (một cột/lớp tag) và mọi cột vô hướng do `derive()` ở đây suy ra.

**C2 — `n_poi` lẫn đơn vị, đo được.** `n_poi` cộng `apartments` (một TOÀ NHÀ) với
`mall` (một TRUNG TÂM) tỉ lệ 1:1. Đo trên lưới 254.035 ô: apartments **53,5%** ·
retail **32,1%** · mall **14,5%** tổng `n_poi`; ở **top-100 ô theo `n_poi` thì 84,8%
số đếm là apartments**. Tức `n_poi` thực chất là "mật độ toà chung cư ở HN/HCM",
không phải "điểm sinh cầu". Vì vậy `n_poi` **bị khai tử** (đổi tên thay vì đổi nghĩa
ngầm — consumer cũ phải gãy to, cùng nguyên tắc `road_len_mt_m` của E-DQ7b).

**Lẫn đơn vị còn nằm BÊN TRONG từng nhóm** (không có trong register, đo 28/07):

  - `retail` = 1.698 `amenity=marketplace` (chợ truyền thống, xe máy, không bãi đỗ)
    + 1.409 `shop=supermarket` (siêu thị, có bãi đỗ ô tô) — hai loại cầu khác hẳn nhau.
  - `mall`   = 1.137 `shop=department_store` + 262 `shop=mall`.
  - `parking` = 376 surface / 146 **street_side** / 93 underground / 42 multi-storey
    / 20 lane / 32 carports — đỗ ven đường không phải bãi đỗ đặt được trụ sạc.

⇒ lớp phân theo **tag**, không theo nhóm crawl.

**C3 — không chọn trọng số ở đây.** Cám dỗ là gán `mall=5, retail=2, apartments=1`.
Đo thử: đổi bộ trọng số **hoán đổi 147–254 trong top-500 ô**, tức đây là quyết định
mô hình có hậu quả thật. `E-DQ7d`/`P1` có **18,6M bản ghi occupancy** để *fit* nó.
Việc của E-DQ7c là **giao ra các cột tách rời fit được**; việc của E-DQ7d là gán trọng
số. (Lưu ý đo đạc: ρ_Spearman **vô dụng** để so các bộ trọng số ở đây — 98,8% ô bằng 0
nên ρ = 1,000 cho cả những bộ đảo lộn 1/3 top-500. Dùng **top-K overlap**.)

**C5 — kích thước ở đâu ĐO được thì ghi, ở đâu không thì gắn cờ.** `building:levels`
có ở **36%** toà chung cư (trung vị 18 tầng); `building:flats` chỉ 6%; `capacity` của
bãi đỗ chỉ **1,3%** (55/2.463) ⇒ **`capacity` không dùng được cho parking**, ghi lại
để không ai đề xuất lại (cùng kiểu ghi chú với `service` subtype 86% khuyết ở E-DQ7b).

**C6 — cụm chung cư phải gộp TRƯỚC khi cân theo kích thước.** 60,8% polygon chung cư
nằm trong cụm ≥5 thành viên trong bán kính 200 m, và tên lặp nhiều nhất đúng là
`block b` / `lô a` / `ct1` / `a2` — tức **các toà trong CÙNG một khu**. Đếm theo toà
thì một khu tính 5–10 lần trong khi một mall tính 1 lần. Vì vậy bảng lớp ghi **cả hai**:
`n_apartment` (toà) và `n_apartment_complex` (khu, gộp đơn liên kết 150 m).
"""
import math

#: Thứ tự lớp — cố định vì nó quyết định tên cột của `osm_poi_h3.parquet`.
CLASSES = ["FUEL", "PARKING_OFF", "PARKING_STREET", "MALL", "DEPT_STORE",
           "SUPERMARKET", "MARKET", "APARTMENT"]

#: Độ ưu tiên khi MỘT đối tượng OSM rơi vào nhiều lớp (số nhỏ = thắng).
#:
#: ⚠️ Khoá khử trùng cũ `(osm_type, osm_id, category)` **cố ý cho phép** một đối tượng
#: được đếm hai lần nếu nó lọt vào hai file nhóm. Đo thực tế: **13 đối tượng** ở 2 nhóm
#: (8 `in_vn`) — `mall+retail` ×5, `apartments+retail` ×5, `apartments+mall`,
#: `mall+parking`, `fuel+retail`; **4/5 tổ hợp cùng dồn vào `n_poi`** ⇒ đếm đôi trong
#: chính feature. Một đối tượng vật lý = **một** lớp: venue thắng vỏ nhà.
CLASS_PRIORITY = {c: i for i, c in enumerate(CLASSES)}

#: `parking=*` được coi là đỗ VEN ĐƯỜNG (không đặt được trụ sạc → tách khỏi bãi đỗ).
_STREET_PARKING = {"street_side", "lane", "on_kerb", "half_on_kerb", "shoulder"}

#: `access=*` chặn công chúng. `customers` KHÔNG nằm đây: bãi đỗ khách của TTTM là
#: đúng chỗ đặt trụ sạc công cộng.
_ACCESS_RESTRICTED = {"private", "no", "employees", "permit", "agricultural",
                      "forestry", "delivery", "military"}
_ACCESS_PUBLIC = {"yes", "public", "permissive", "customers", "destination"}

#: Ngưỡng ghép node↔way/relation cùng một địa điểm vật lý (mét).
#: Chọn 30 m thay vì 50/100 m: từ 30→100 m số cặp `parking` nhảy 36→84, phần tăng chủ
#: yếu là **bãi đỗ liền kề có thật**, không phải bản trùng. Đổi recall lấy an toàn —
#: cùng đánh đổi với `STACK_MIN=5` của E-DQ1.
DUP_RADIUS_M = 30.0

#: Ngưỡng gộp toà chung cư về một KHU (đơn liên kết). 150 m ≈ đường kính một khu đô
#: thị nhỏ ở VN; đo ở 200 m thì 60,8% toà đã nằm trong cụm ≥5.
COMPLEX_RADIUS_M = 150.0

#: Dải `building:levels` hợp lệ (VN có toà gắn levels=0 và levels rác).
_LEVELS_MIN, _LEVELS_MAX = 1.0, 100.0


def classify(category, tags):
    """(nhóm crawl, tags) -> lớp tag. `None` nếu không nhận dạng được."""
    tags = tags or {}
    if category == "fuel":
        return "FUEL"
    if category == "parking":
        return ("PARKING_STREET" if (tags.get("parking") or "").strip().lower()
                in _STREET_PARKING else "PARKING_OFF")
    if category == "mall":
        return "MALL" if (tags.get("shop") or "").strip().lower() == "mall" else "DEPT_STORE"
    if category == "retail":
        shop = (tags.get("shop") or "").strip().lower()
        if shop == "supermarket":
            return "SUPERMARKET"
        if (tags.get("amenity") or "").strip().lower() == "marketplace":
            return "MARKET"
        return "SUPERMARKET" if shop else "MARKET"
    if category == "apartments":
        return "APARTMENT"
    return None


def access_of(tags):
    """`access=*` -> PUBLIC / RESTRICTED / UNKNOWN (giữ 3 trạng thái như P8).

    80% bãi đỗ **không có** tag `access` ⇒ UNKNOWN là đa số và **không** bị loại
    (loại ngầm cái không biết là đúng lỗi mà P8 đã sửa cho `evcs`).
    """
    v = (tags or {}).get("access")
    v = (v or "").strip().lower()
    if v in _ACCESS_RESTRICTED:
        return "RESTRICTED"
    if v in _ACCESS_PUBLIC:
        return "PUBLIC"
    return "UNKNOWN"


def parse_levels(raw):
    """`building:levels=*` -> float trong dải hợp lệ, hoặc None. Chịu được `5;6`, rác."""
    if raw is None:
        return None
    txt = str(raw).split(";")[0].strip()
    try:
        v = float(txt)
    except ValueError:
        return None
    return v if _LEVELS_MIN <= v <= _LEVELS_MAX else None


def haversine_m(lat1, lon1, lat2, lon2):
    """Khoảng cách mét giữa hai điểm (scalar; dùng trong vòng lặp ghép cặp)."""
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


# --- tên cột của bảng lớp (osm_poi_h3.parquet) ---
# Tiền tố `poi_` để bảng LỚP không bao giờ trùng tên với cột SUY RA (`n_*`) — nếu trùng,
# `derive()` sẽ ghi đè chính đầu vào của mình và cổng đối soát Σ lớp mất ý nghĩa.
# Cùng quy ước với `m_MOTORWAY` (lớp) vs `road_lane_mw_m` (suy ra) của E-DQ7b.
def n_col(cls):
    return f"poi_{cls.lower()}"


def restricted_col(cls):
    return f"poi_{cls.lower()}_restricted"


#: Cột kích thước chung cư — cặp (tổng, số quan sát được) để cổng QA đo tỉ lệ ĐO/SUY,
#: y hệt `lane_obs_m_*` của E-DQ7b.
APARTMENT_COMPLEX_COL = "poi_apartment_complex"
APARTMENT_LEVELS_COL = "poi_apartment_levels"
APARTMENT_LEVELS_OBS_COL = "poi_apartment_levels_obs"

#: Toàn bộ cột số của bảng lớp.
CLASS_COLUMNS = ([n_col(c) for c in CLASSES] + [restricted_col(c) for c in CLASSES]
                 + [APARTMENT_COMPLEX_COL, APARTMENT_LEVELS_COL,
                    APARTMENT_LEVELS_OBS_COL])

#: Cột vô hướng suy ra, dùng ở `osm_demand_components_h3` và `demand_h3`.
#: `n_poi` và `n_parking` **đã khai tử** — không có trong danh sách này.
DERIVED_COLUMNS = ["n_fuel", "n_parking_off", "n_parking_street", "n_mall",
                   "n_dept_store", "n_supermarket", "n_market", "n_apartment",
                   "n_apartment_complex", "apartment_levels_sum"]

#: Lớp mà `access=RESTRICTED` bị trừ khỏi cột suy ra. Chỉ parking có tag `access`
#: đáng kể (20%); trạm xăng/siêu thị/chợ về bản chất là công cộng.
_SUBTRACT_RESTRICTED = ("PARKING_OFF", "PARKING_STREET")


def derive(df):
    """Thêm `DERIVED_COLUMNS` vào bảng lớp theo ô (không sửa `df` gốc).

    Chính sách nằm **trọn** trong hàm này — đổi định nghĩa cột vô hướng = chạy lại vài
    giây, không phải crawl lại Overpass.

      - `n_fuel`            : trạm xăng (ngữ nghĩa **không đổi**, chỉ thêm khử trùng)
      - `n_parking_off`     : bãi đỗ ngoài lòng đường, **trừ** `access=RESTRICTED`
      - `n_parking_street`  : đỗ ven đường/lòng đường (tách ra, không đặt được trụ)
      - `n_mall`/`n_dept_store`/`n_supermarket`/`n_market`/`n_apartment` : theo lớp tag
      - `n_apartment_complex` : số KHU chung cư (gộp 150 m), gán theo **trọng tâm khu**
      - `apartment_levels_sum`: Σ `building:levels` **quan sát được** (36% toà có tag)
        — số ĐO, dùng làm proxy quy mô; ô không có tag thì bằng 0, **không nội suy**.
    """
    out = df.copy()
    for c in CLASS_COLUMNS:
        if c not in out.columns:
            out[c] = 0
        out[c] = out[c].fillna(0).astype(int)

    #: lớp tag -> cột vô hướng (chính sách 1-1, chỉ khác ở việc trừ RESTRICTED)
    for cls, scalar in (("FUEL", "n_fuel"),
                        ("PARKING_OFF", "n_parking_off"),
                        ("PARKING_STREET", "n_parking_street"),
                        ("MALL", "n_mall"),
                        ("DEPT_STORE", "n_dept_store"),
                        ("SUPERMARKET", "n_supermarket"),
                        ("MARKET", "n_market"),
                        ("APARTMENT", "n_apartment")):
        out[scalar] = out[n_col(cls)]
        if cls in _SUBTRACT_RESTRICTED:
            out[scalar] = out[scalar] - out[restricted_col(cls)]
    out["n_apartment_complex"] = out[APARTMENT_COMPLEX_COL]
    out["apartment_levels_sum"] = out[APARTMENT_LEVELS_COL]
    return out


def trip_gen_interim(df):
    """Điểm sinh cầu **tạm thời** thay cho `n_poi` đã khai tử (T4 gap-fill, P5).

    ⚠️ Trọng số **đặt tay**, y như `0,025·road_lane_ar_m + 0,05·road_lane_mw_m` của
    E-DQ7b — **E-DQ7d/P1 sẽ hiệu chuẩn** bằng 18,6M bản ghi occupancy. Ở đây chỉ giữ
    hai cải thiện *không cần fit* mà E-DQ7c đã chứng minh:

      1. chung cư đếm theo **KHU** (`n_apartment_complex`), không theo toà — 60,8% toà
         nằm trong cụm ≥5 nên đếm theo toà là nhân 5–10 lần cùng một khu;
      2. **đỗ ven đường không tính** (`n_parking_street` vắng mặt) và chợ tách khỏi
         siêu thị, vì hai loại này không sinh cầu sạc **ô tô** như nhau.

    Giữ đúng độ lớn cũ (`n_poi` nhân 50 ở `build_candidates`) để T4 không đổi thang.
    """
    return (df.get("n_mall", 0) + df.get("n_dept_store", 0)
            + df.get("n_supermarket", 0) + 0.5 * df.get("n_market", 0)
            + df.get("n_apartment_complex", 0))


# --- ghép cặp không gian (C3/C6) -----------------------------------------------
# Dùng lưới H3 làm chỉ mục lân cận thay vì cây KD của scikit-learn: `h3` đã là phụ
# thuộc sẵn có của pipeline, còn `sklearn` thì không — không thêm phụ thuộc cứng chỉ
# để ghép vài nghìn điểm. Bucket theo ô res R rồi lọc chính xác bằng haversine, với R
# chọn sao cho vòng k=1 phủ chắc ngưỡng ⇒ kết quả **giống hệt** brute-force.

#: res H3 dùng làm bucket theo ngưỡng (cạnh ô res 10 ≈ 65 m, res 9 ≈ 174 m).
def _bucket_res(radius_m):
    return 10 if radius_m <= 60 else 9


def neighbour_pairs(lat, lng, radius_m, same_group=None):
    """Sinh mọi cặp (i, j), i<j, cách nhau ≤ `radius_m`.

    `same_group`: dãy nhãn — chỉ ghép cặp trong cùng nhãn (dùng để không ghép nhầm
    trạm xăng với bãi đỗ ở cùng một góc phố).
    """
    import h3
    res = _bucket_res(radius_m)
    cells = [h3.latlng_to_cell(a, b, res) for a, b in zip(lat, lng)]
    index = {}
    for i, c in enumerate(cells):
        index.setdefault(c, []).append(i)
    seen = set()
    for i, c in enumerate(cells):
        for nb in h3.grid_disk(c, 1):
            for j in index.get(nb, ()):
                if j <= i:
                    continue
                if same_group is not None and same_group[i] != same_group[j]:
                    continue
                if (i, j) in seen:
                    continue
                seen.add((i, j))
                if haversine_m(lat[i], lng[i], lat[j], lng[j]) <= radius_m:
                    yield i, j


class _Union:
    """Union-find tối giản (gộp đơn liên kết)."""

    def __init__(self, n):
        self.p = list(range(n))

    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[max(ra, rb)] = min(ra, rb)


def single_link_groups(lat, lng, radius_m, same_group=None):
    """Gộp đơn liên kết trong bán kính -> dãy chỉ số nhóm (0..k-1).

    Tương đương `DBSCAN(eps=radius, min_samples=1)` nhưng không cần scikit-learn.
    """
    n = len(lat)
    uf = _Union(n)
    for i, j in neighbour_pairs(lat, lng, radius_m, same_group):
        uf.union(i, j)
    roots, out = {}, []
    for i in range(n):
        r = uf.find(i)
        out.append(roots.setdefault(r, len(roots)))
    return out
