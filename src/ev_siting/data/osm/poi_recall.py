#!/usr/bin/env python3
"""poi_recall.py — Đo ĐỘ PHỦ của tầng POI bằng nguồn độc lập (E-DQ7c, C4/C7).

**Vì sao phải đo, và vì sao không đo bằng số liệu chính thức.** Register ghi "OSM chỉ
phủ ~30% cây xăng" — con số ngoại lai (~17.000 cửa hàng bán lẻ toàn quốc). E-DQ7b đã
chốt nguyên tắc: **không đặt cổng theo số liệu chính thức chưa freeze vào
`data/external/`** (xem limitation `motorway` của E-DQ7b). Vả lại MOIT công bố thương
nhân đầu mối/phân phối chứ **không** công bố danh sách cửa hàng bán lẻ có toạ độ; danh
sách của Sở Công Thương là PDF/xlsx địa chỉ chữ, mà E-DQ6 đã cho thấy địa chỉ ở VN
không geocode được đáng tin.

**Nguồn đối chiếu dùng ở đây là dữ liệu bạn đã có, và nó độc lập với OSM:** trong tập
cung 19.015 trạm sạc công khai, có những trạm mà `name`/`address` **nêu đích danh một
cây xăng** ("Cửa hàng xăng dầu…", "Petrolimex…", "CHXD…") hoặc một bãi đỗ. Mỗi trạm như
vậy là **bằng chứng thực địa** rằng ở đó có một cây xăng/bãi đỗ. Hỏi ngược: OSM có POI
tương ứng trong bán kính không? ⇒ **recall đo được, tái lập được, không cần nguồn mới.**

Đo 28/07 (bán kính 100 m): **fuel 35,9%** (505/1.408) · **parking 9,6%** (81/844). Recall
gần như không đổi khi nới 100→300 m (35,9→37,6%) ⇒ đây là **thiếu POI thật**, không
phải hiệu ứng dung sai khoảng cách. Con số fuel xác nhận "~30%" bằng đường độc lập; con
số parking là **phát hiện mới** — `n_parking` tệ hơn `n_fuel` khoảng **4 lần**, điều mà
register không hề nói.

**Vì sao KHÔNG đo recall theo từng ô H3.** Ba lý do, lý do thứ ba là chặn:

  1. *Không xác định được:* 1.408 điểm đối chiếu nằm trên ~1.200 ô trong tổng **254.035**
     ô ⇒ >99% ô có mẫu **rỗng**, recall theo ô không tồn tại.
  2. *Vô nghĩa ở nơi có mẫu:* ô có 1–2 điểm đối chiếu chỉ cho ra 0% hoặc 100% — nhiễu
     thuần, không phải ước lượng.
  3. *Rò rỉ mục tiêu:* dùng **vị trí trạm sạc** để hiệu chỉnh **covariate dự đoán cầu
     sạc** là vòng luẩn quẩn — nó bơm thông tin cung hiện hữu vào biến cầu, và E-DQ7d
     khi hiệu chuẩn với occupancy sẽ đo lại chính cái rò rỉ đó. Recall ở đây chỉ được
     dùng để **mô tả thiên lệch**, tuyệt đối không để nhân/chia vào feature.

**Cái cần đo là THIÊN LỆCH, không phải độ phủ tuyệt đối.** Với một covariate *tương
đối*, thiếu đều 64% chỉ là hằng số tỉ lệ — vô hại. Thiếu **không đều theo mật độ dân**
mới là chất độc. Vì vậy recall được phân **tầng theo tam phân vị `pop`** của ô chứa
điểm đối chiếu, và cổng QA canh **tỉ số tầng cao/tầng thấp**, không canh mức tuyệt đối.

Chạy:
    PYTHONPATH=src python -m ev_siting.data.osm.poi_recall
"""
import json

import pandas as pd

from . import poi_semantics as ps
from .paths import POI_POINTS, POI_RECALL_REPORT, ensure_dirs

#: Từ khoá nhận diện trạm sạc ĐẶT TẠI một cây xăng / bãi đỗ (trên `name`+`address`).
_KEYWORDS = {
    "FUEL": ["xăng", "xang dau", "petrolimex", "pvoil", "pv oil", "chxd",
             "petrol", "comeco", "saigon petro", "mipec"],
    "PARKING_OFF": ["bãi đỗ", "bai do xe", "bãi xe", "parking", "hầm xe",
                    "nhà xe", "bãi giữ xe"],
}

#: Bán kính báo cáo. 100 m là số dùng cho cổng; 200/300 m để chứng minh recall thấp
#: KHÔNG phải do dung sai (nếu nới bán kính mà recall vọt lên thì lỗi là toạ độ, không
#: phải thiếu POI).
RADII_M = (100, 200, 300)
GATE_RADIUS_M = 100

#: Ngưỡng cổng — xem docstring: canh THIÊN LỆCH, không canh mức tuyệt đối.
RECALL_FUEL_MIN = 0.30          # dưới mức này thì `n_fuel` không còn là "số cây xăng"
BIAS_RATIO_WARN = 2.0           # recall(tầng pop cao) / recall(tầng pop thấp)


def _supply():
    from ev_siting.data.evcs.paths import STATIONS_DIR
    if not STATIONS_DIR.exists():
        return None
    st = pd.read_parquet(STATIONS_DIR)
    for col, val in (("is_operational", True), ("access", "PUBLIC"),
                     ("is_primary", True), ("coord_resolved", True)):
        if col in st.columns:
            st = st[st[col] == val]
    return st[st["lat"].notna() & st["lng"].notna()].copy()


def _hits(bench, poi, radius_m):
    """Với mỗi điểm đối chiếu: có POI cùng lớp trong bán kính không? -> mảng bool."""
    lat = bench["lat"].tolist() + poi["lat"].tolist()
    lng = bench["lng"].tolist() + poi["lng"].tolist()
    nb = len(bench)
    # nhãn nhóm: mọi điểm cùng một lớp -> ghép cặp tự do; chỉ giữ cặp bench↔poi
    hit = [False] * nb
    for i, j in ps.neighbour_pairs(lat, lng, radius_m):
        a, b = (i, j) if i < j else (j, i)
        if a < nb <= b:                 # đúng một đầu là điểm đối chiếu
            hit[a] = True
    return hit


def _strata(bench):
    """Tam phân vị `pop` của ô chứa điểm đối chiếu -> nhãn tầng."""
    from ev_siting.data.worldpop.paths import DEMAND_H3
    if not DEMAND_H3.exists():
        return pd.Series(["ALL"] * len(bench), index=bench.index)
    dem = pd.read_parquet(DEMAND_H3, columns=["h3_r8", "pop"]).set_index("h3_r8")
    pop = bench["h3_r8"].map(dem["pop"]).fillna(0.0)
    try:
        return pd.qcut(pop.rank(method="first"), 3,
                       labels=["pop_thap", "pop_trung", "pop_cao"])
    except ValueError:
        return pd.Series(["ALL"] * len(bench), index=bench.index)


def measure():
    """Trả về dict recall theo lớp × bán kính × tầng (None nếu thiếu artefact)."""
    st = _supply()
    if st is None or not POI_POINTS.exists():
        return None
    poi = pd.read_parquet(POI_POINTS)
    poi = poi[poi["in_vn"] & poi["is_poi_primary"]]
    txt = (st["name"].fillna("") + " " + st["address"].fillna("")).str.lower()

    out = {"n_supply": int(len(st)), "gate_radius_m": GATE_RADIUS_M, "by_class": {}}
    for cls, keys in _KEYWORDS.items():
        bench = st[txt.str.contains("|".join(keys), regex=True, na=False)].copy()
        sub = poi[poi["poi_class"] == cls]
        if bench.empty or sub.empty:
            continue
        rec = {"n_benchmark": int(len(bench)), "n_osm_poi": int(len(sub)),
               "recall_by_radius": {}, "recall_by_stratum": {}}
        for r in RADII_M:
            h = _hits(bench, sub, r)
            rec["recall_by_radius"][str(r)] = round(sum(h) / len(h), 4)
            if r == GATE_RADIUS_M:
                bench["_hit"] = h
        g = bench.groupby(_strata(bench), observed=True)["_hit"]
        rec["recall_by_stratum"] = {str(k): {"n": int(v), "recall": round(m, 4)}
                                    for k, v, m in zip(g.size().index, g.size(),
                                                       g.mean())}
        strat = rec["recall_by_stratum"]
        if "pop_cao" in strat and "pop_thap" in strat and strat["pop_thap"]["recall"] > 0:
            rec["bias_ratio_high_over_low"] = round(
                strat["pop_cao"]["recall"] / strat["pop_thap"]["recall"], 3)
        out["by_class"][cls] = rec
    return out


def run():
    ensure_dirs()
    rep = measure()
    if rep is None:
        print("[recall] bỏ qua — thiếu canonical stations hoặc osm_poi_points")
        return None
    for cls, rec in rep["by_class"].items():
        print(f"[{cls}] {rec['n_benchmark']} điểm đối chiếu vs {rec['n_osm_poi']} POI OSM")
        for r, v in rec["recall_by_radius"].items():
            print(f"    recall @{r:>3}m = {v:.1%}")
        for k, v in rec["recall_by_stratum"].items():
            print(f"    {k:10s} n={v['n']:5d}  recall={v['recall']:.1%}")
        if "bias_ratio_high_over_low" in rec:
            print(f"    thiên lệch pop_cao/pop_thap = {rec['bias_ratio_high_over_low']}")
    POI_RECALL_REPORT.write_text(json.dumps(rep, ensure_ascii=False, indent=2),
                                 encoding="utf-8")
    print(f"\n-> {POI_RECALL_REPORT}")
    return rep


if __name__ == "__main__":
    run()
