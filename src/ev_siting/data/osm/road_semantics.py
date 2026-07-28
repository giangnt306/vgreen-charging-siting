#!/usr/bin/env python3
"""road_semantics.py — Ngữ nghĩa `road_len` (E-DQ7b): phân lớp + suy dẫn cột.

**R1 — tách TRÍCH XUẤT khỏi CHÍNH SÁCH.** Trước đây `_EXCLUDE`/`_MAJOR` nằm ngay
trong vòng lặp stream `.pbf` ở `roads_pbf.py`: mỗi lần đổi định nghĩa "đường" là một
lần stream lại 325 MB (~7 phút) và **không thể hoàn tác** vì bảng ra chỉ còn 2 số.
Nay `roads_pbf.py` chỉ ghi **km + lane-mét theo TỪNG LỚP** cho mỗi ô; mọi cột vô
hướng downstream do `derive()` ở đây suy ra — đổi chính sách = tính lại vài giây.

Ngoại lệ duy nhất còn nằm ở khâu trích xuất là `NON_DRIVABLE`: `footway`/`cycleway`/
`steps`/… không phải đường lái xe được theo **bất kỳ** định nghĩa downstream nào, nên
loại ngay để bảng lớp không phình vô ích.

**R2 — hai cột, hai nhiệm vụ.** `road_len_m` cũ phải phục vụ hai định nghĩa mâu thuẫn:

  - `buildable_h3` dùng `road_len_m <= 0` làm bộ lọc cứng `NO_ROAD_ACCESS` → cần định
    nghĩa **rộng** (đường đất vẫn là lối vào).
  - Proxy cầu cần định nghĩa **hẹp** (đường mòn không sinh nhu cầu sạc).

Đo trên lưới hiện tại: bỏ `service`+`track` khỏi một cột duy nhất đẩy số ô `road=0`
từ **6.350 → 34.178**; trong 27.828 ô lật có **2.474 ô chứa 850.207 dân** và **36 ô
chứa 145 trạm sạc đang vận hành** — tức bộ lọc khả thi sẽ loại chính những nơi đã có
trạm thật. Vì vậy tách:

  - `road_access_m` = mọi đường lái xe được (**gồm** `service`+`track`) → lối vào.
    Bằng đúng `road_len_m` cũ ⇒ `buildable_h3`/E-DQ8 giữ nguyên hành vi.
  - `road_len_m`    = mạng lái xe **trừ** `service`+`track` → cầu.

**R3 — sửa double-count bằng lane-mét, không nhân 0,5.** Đường đôi có dải phân cách
được vẽ thành 2 way một chiều ⇒ 1 hành lang tính 2 lần, trong khi đường 4 làn không
phân cách chỉ tính 1 lần: `road_len` **không** tỉ lệ với năng lực thông hành. Nhân 0,5
cho mọi way `oneway` là sai — 3.028 km `oneway` thuộc lớp LOCAL là cặp phố một chiều
thật, không phải đường đôi (và cách này cắt `_MAJOR` tới 20,5%). Lane-mét xử lý tận
gốc: 2 chiều của đường đôi đóng góp số làn của chúng, đường không phân cách cũng vậy.
Quan trọng: `lanes` được gắn tag ở **97,4% motorway · 50,4% trunk · 40,6% primary**
nhưng chỉ **0,6% residential** ⇒ lane-mét là số **đo được** đúng ở các lớp trục lớn,
là số **suy đoán** ở lớp địa phương → chỉ dùng lane-mét cho trục lớn.

**R4 — tách `_MAJOR`.** Trên các ô có `_MAJOR>0`: ρ_Spearman(`road_len_mt_m`, motorway)
= **0,31** còn với trunk+primary = **0,70** — cột cũ thực chất là "trục đô thị", tín
hiệu cao tốc bị chìm (motorway chỉ chiếm 14,8% km `_MAJOR`). Hai lớp có ngữ nghĩa chọn
điểm ngược nhau: ô motorway có `pop` trung vị **73** (liên tỉnh, dừng lâu, DC công suất
cao), ô trunk/primary **312–374** (trục đô thị). Chúng gần như không chồng lấn: 3.311 ô
chỉ-motorway vs 37.574 ô chỉ-trunk/primary. Vì vậy `road_len_mt_m` **bị khai tử** (đổi
tên thay vì đổi nghĩa ngầm — consumer cũ phải gãy to, cùng nguyên tắc với cổng
`poi_has_in_vn_flag` của E-DQ7a), thay bằng `road_lane_mw_m` + `road_lane_ar_m`.
"""

#: Loại `highway` KHÔNG lái xe được — loại ngay ở khâu trích xuất (xem docstring).
NON_DRIVABLE = {
    "footway", "path", "pedestrian", "steps", "cycleway", "bridleway",
    "corridor", "construction", "proposed", "raceway", "elevator", "platform",
}

#: Thứ tự lớp — cố định vì nó quyết định tên cột của `osm_roads_h3.parquet`.
TIERS = ["MOTORWAY", "TRUNK", "PRIMARY", "SECONDARY", "TERTIARY",
         "LOCAL", "SERVICE", "TRACK", "OTHER"]

#: `highway=*` -> lớp. Giá trị không có trong bảng rơi vào `OTHER`
#: (`services`, `rest_area`, `busway`, … — vẫn là đường lái xe được).
TIER_OF = {
    "motorway": "MOTORWAY", "motorway_link": "MOTORWAY",
    "trunk": "TRUNK", "trunk_link": "TRUNK",
    "primary": "PRIMARY", "primary_link": "PRIMARY",
    "secondary": "SECONDARY", "secondary_link": "SECONDARY",
    "tertiary": "TERTIARY", "tertiary_link": "TERTIARY",
    "residential": "LOCAL", "unclassified": "LOCAL",
    "living_street": "LOCAL", "road": "LOCAL",
    "service": "SERVICE",
    "track": "TRACK",
}

#: Lớp bị loại khỏi `road_len_m` (mạng sinh cầu) nhưng GIỮ trong `road_access_m`.
NON_DEMAND_TIERS = ("SERVICE", "TRACK")
#: Lớp trục lớn — tách đôi theo R4.
MOTORWAY_TIERS = ("MOTORWAY",)
ARTERIAL_TIERS = ("TRUNK", "PRIMARY")

#: Giá trị `oneway=*` coi là một chiều.
_ONEWAY_TRUE = {"yes", "-1", "true", "1"}
#: Dải `lanes` hợp lệ — ngoài dải coi như không có tag (VN có way gắn lanes=50).
_LANES_MIN, _LANES_MAX = 1.0, 12.0
#: Số làn mặc định khi thiếu tag `lanes`, theo lớp và chiều.
_DEFAULT_LANES_SINGLE_TRACK = 1.0   # SERVICE/TRACK: gần như luôn 1 làn


def is_oneway(oneway_raw) -> bool:
    return (oneway_raw or "").strip().lower() in _ONEWAY_TRUE


def parse_lanes(lanes_raw):
    """`lanes=*` -> float trong dải hợp lệ, hoặc None. Chịu được `2;3`, `2.5`, rác."""
    if not lanes_raw:
        return None
    txt = str(lanes_raw).split(";")[0].strip()
    try:
        v = float(txt)
    except ValueError:
        return None
    return v if _LANES_MIN <= v <= _LANES_MAX else None


def lanes_for(tier, lanes_raw, oneway):
    """(số làn, có_tag) cho một way.

    Thiếu tag thì mặc định theo lớp: SERVICE/TRACK = 1 làn; còn lại 1 nếu một chiều,
    2 nếu hai chiều. Cờ `có_tag` để cổng QA đo tỉ lệ lane-mét **quan sát được** — nếu
    tỉ lệ suy đoán lấn át thì feature trục lớn không còn là số đo.
    """
    v = parse_lanes(lanes_raw)
    if v is not None:
        return v, True
    if tier in NON_DEMAND_TIERS:
        return _DEFAULT_LANES_SINGLE_TRACK, False
    return (1.0 if oneway else 2.0), False


# --- tên cột của bảng lớp (osm_roads_h3.parquet) ---
def m_col(tier):
    return f"m_{tier}"


def lane_col(tier):
    return f"lane_m_{tier}"


def lane_obs_col(tier):
    return f"lane_obs_m_{tier}"


BRIDGE_COL = "bridge_m"

#: Toàn bộ cột số của bảng lớp, **đúng thứ tự ô nhớ** của accumulator trong
#: `roads_pbf.RoadHandler` (3 ô/lớp, xen kẽ, rồi cầu/hầm). `roads_pbf` lấy chỉ số
#: slot bằng `TIER_COLUMNS.index(...)` chứ không tự giả định — hai bên không thể lệch.
TIER_COLUMNS = ([c for t in TIERS
                 for c in (m_col(t), lane_col(t), lane_obs_col(t))]
                + [BRIDGE_COL])

#: Cột vô hướng suy ra, dùng ở `osm_demand_components_h3` và `demand_h3`.
DERIVED_COLUMNS = ["road_access_m", "road_len_m",
                   "road_lane_mw_m", "road_lane_ar_m", "road_bridge_m"]


def derive(df):
    """Thêm `DERIVED_COLUMNS` vào bảng lớp theo ô (không sửa `df` gốc).

    - `road_access_m`  = Σ km mọi lớp lái xe được  → lối vào (buildable, E-DQ8)
    - `road_len_m`     = Σ km trừ SERVICE/TRACK    → mạng sinh cầu
    - `road_lane_mw_m` = lane-mét cao tốc          → hành lang liên tỉnh (R4)
    - `road_lane_ar_m` = lane-mét trunk+primary    → trục đô thị (R4)
    - `road_bridge_m`  = km cầu/hầm (TẬP CON của `road_access_m`, không cộng dồn):
      ô mà đường duy nhất là mặt cầu vẫn đang lọt bộ lọc lối vào — 4.178 km cầu +
      203 km hầm toàn quốc.
    """
    out = df.copy()
    for c in TIER_COLUMNS:
        if c not in out.columns:
            out[c] = 0.0
        out[c] = out[c].fillna(0.0)

    out["road_access_m"] = sum(out[m_col(t)] for t in TIERS)
    out["road_len_m"] = sum(out[m_col(t)] for t in TIERS if t not in NON_DEMAND_TIERS)
    out["road_lane_mw_m"] = sum(out[lane_col(t)] for t in MOTORWAY_TIERS)
    out["road_lane_ar_m"] = sum(out[lane_col(t)] for t in ARTERIAL_TIERS)
    out["road_bridge_m"] = out[BRIDGE_COL]
    return out


def major_lane_observed_share(df):
    """Tỉ lệ lane-mét **quan sát được** (có tag `lanes`) trên các lớp trục lớn."""
    tiers = MOTORWAY_TIERS + ARTERIAL_TIERS
    tot = float(sum(df[lane_col(t)].sum() for t in tiers))
    obs = float(sum(df[lane_obs_col(t)].sum() for t in tiers))
    return (obs / tot) if tot > 0 else 0.0
