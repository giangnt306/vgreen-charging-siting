#!/usr/bin/env python3
"""compare_osm.py — Đối chiếu tầng POI: OpenStreetMap ⟷ Overture Places.

**Câu hỏi phải trả lời, theo đúng thứ tự quan trọng:**

  A. *Ảnh chụp nào?* — không so được hai con số nếu không biết chúng chụp lúc nào.
  B. *Số lượng* theo lớp, trong lãnh thổ VN, sau khử trùng.
  C. *Chồng lấn không gian* — chênh lệch tổng KHÔNG chứng minh nguồn nào phủ hơn: hai
     nguồn có thể cùng 5.000 điểm mà không trùng nhau chỗ nào. Ghép cặp theo bán kính
     và tách matched / osm_only / overture_only.
  D. *Độ tươi* ở mức ĐỐI TƯỢNG (không phải mức release).
  E. *Có độc lập không?* — Overture nuốt cả OSM. Nếu 90% điểm Overture ở VN mang
     `dataset='OpenStreetMap'` thì "Overture nhiều hơn" chỉ là OSM được đóng gói lại,
     và mọi kết luận ở C sụp. Đây là kiểm tra **chặn**, phải đọc trước khi tin B.
  F. *Recall trên nền độc lập* — dùng lại bằng chứng thực địa của `osm/poi_recall.py`
     (trạm sạc mà `name`/`address` nêu đích danh một cây xăng ⇒ ở đó CÓ cây xăng) và
     hỏi cùng câu hỏi cho cả hai nguồn. Đây là phép đo duy nhất ở đây có **ground truth**
     ngoài cả hai nguồn; B/C chỉ mô tả chênh lệch, F mới nói ai đúng.

**Ghép cặp không gian — vì sao không dùng `poi_semantics.neighbour_pairs`.** Hàm đó
bucket theo `_bucket_res` = res 9 cho mọi bán kính > 60 m, mà res 9 có khoảng cách
tâm-tâm 0,37 km ⇒ vòng `k=1` chỉ **bảo đảm** phủ tới ~185 m. Ở 200/300 m nó bỏ sót cặp
thật (số ghép được **thấp hơn** brute-force). Ở đây dùng res 8 (tâm-tâm 0,98 km ⇒ bảo
đảm ~490 m) cho mọi bán kính ≤ 450 m, nên kết quả **bằng đúng** brute-force.

Chạy:
    PYTHONPATH=src python -m ev_siting.data.overture.compare_osm
    PYTHONPATH=src python -m ev_siting.data.overture.compare_osm --no-pairs
"""
import argparse
import json
import sys
from datetime import datetime, timezone

import h3
import pandas as pd

from ..osm import poi_recall as pr
from ..osm import poi_semantics as ps
from ..osm import poi_timestamps as pts
from ..osm.paths import POI_POINTS as OSM_POI_POINTS
from ..osm.paths import POI_RAW_DIR
from . import poi_taxonomy as tax
from .paths import (
    COMPARE_MD,
    COMPARE_PAIRS,
    COMPARE_REPORT,
    MATCH_RADII_M,
    MATCH_RADIUS_M,
    POI_POINTS,
    RELEASE,
    ensure_dirs,
    fetch_meta,
)

#: Ngưỡng "cũ" khi mô tả độ tươi (năm).
STALE_YEARS = (3, 5)


# --- ghép cặp không gian (xem docstring) ---------------------------------------
def _bucket_res(radius_m):
    if radius_m > 450:
        raise ValueError(f"bán kính {radius_m} m vượt bảo đảm của res 8 (~490 m)")
    return 10 if radius_m <= 60 else 8


def _cross_pairs(lat_a, lng_a, lat_b, lng_b, radius_m):
    """Sinh cặp (i thuộc A, j thuộc B) cách nhau ≤ `radius_m`. Kết quả = brute-force."""
    res = _bucket_res(radius_m)
    idx = {}
    for j, (la, lo) in enumerate(zip(lat_b, lng_b)):
        idx.setdefault(h3.latlng_to_cell(la, lo, res), []).append(j)
    for i, (la, lo) in enumerate(zip(lat_a, lng_a)):
        for nb in h3.grid_disk(h3.latlng_to_cell(la, lo, res), 1):
            for j in idx.get(nb, ()):
                if ps.haversine_m(la, lo, lat_b[j], lng_b[j]) <= radius_m:
                    yield i, j


def _match_flags(a, b, radius_m):
    """Hai mảng bool: điểm nào của A có đối ứng ở B, và ngược lại."""
    ha = [False] * len(a)
    hb = [False] * len(b)
    la, ga = a["lat"].tolist(), a["lng"].tolist()
    lb, gb = b["lat"].tolist(), b["lng"].tolist()
    for i, j in _cross_pairs(la, ga, lb, gb, radius_m):
        ha[i] = True
        hb[j] = True
    return ha, hb


# --- nạp 2 nguồn ----------------------------------------------------------------
def _load_osm():
    if not OSM_POI_POINTS.exists():
        raise SystemExit(f"thiếu {OSM_POI_POINTS} — chạy `make osm` trước")
    df = pd.read_parquet(OSM_POI_POINTS)
    df = df[df["in_vn"] & df["is_poi_primary"]].copy()
    ts = pts.load()
    if ts is not None:
        df = df.merge(ts, on=["osm_type", "osm_id"], how="left")
    else:
        df["updated_at"] = pd.NaT
    return df


def _load_overture():
    if not POI_POINTS.exists():
        raise SystemExit(f"thiếu {POI_POINTS} — chạy `make overture` trước")
    df = pd.read_parquet(POI_POINTS)
    return df[df["in_vn"] & df["is_poi_primary"]].copy()


# --- A. ảnh chụp ----------------------------------------------------------------
def _snapshots(release):
    ovt = {}
    if fetch_meta(release).exists():
        m = json.loads(fetch_meta(release).read_text())
        ovt = {"release": m["release"], "fetched_at_utc": m["fetched_at_utc"],
               "n_rows_bbox": m["n_rows"]}
    raws = {p.stem: datetime.fromtimestamp(p.stat().st_mtime, timezone.utc)
                                          .isoformat(timespec="seconds")
            for p in sorted(POI_RAW_DIR.glob("*.json"))}
    return {
        "overture": ovt,
        "osm": {"overpass_crawled_at_utc": raws,
                "pbf_snapshot": pts.pbf_snapshot_date(),
                "note": "raw Overpass KHÔNG có timestamp mức đối tượng — độ tươi ở §D "
                        "lấy từ .pbf đã freeze (xem osm/poi_timestamps.py)"},
    }


# --- B/C. số lượng + chồng lấn --------------------------------------------------
def _counts_and_overlap(osm, ovt, radii, want_pairs):
    rows, pair_rows = {}, []
    for cls in tax.SHARED_CLASSES:
        a = osm[osm["poi_class"] == cls].reset_index(drop=True)
        b = ovt[ovt["poi_class"] == cls].reset_index(drop=True)
        rec = {"n_osm": int(len(a)), "n_overture": int(len(b)),
               "ratio_overture_over_osm": (round(len(b) / len(a), 2) if len(a) else None),
               "overlap_by_radius": {}}
        for r in radii:
            if a.empty or b.empty:
                continue
            ha, hb = _match_flags(a, b, r)
            n_m = sum(ha)
            rec["overlap_by_radius"][str(int(r))] = {
                "osm_matched": int(n_m),
                "osm_only": int(len(a) - n_m),
                "overture_matched": int(sum(hb)),
                "overture_only": int(len(b) - sum(hb)),
                # union = ghép cặp rồi mới cộng: dùng phía OSM làm mốc cụm để không
                # đếm 1 địa điểm 2 lần khi 1 điểm OSM trùng nhiều điểm Overture.
                "union_est": int(len(a) + (len(b) - sum(hb))),
                "pct_osm_covered_by_overture": round(100 * n_m / len(a), 1),
                "pct_overture_covered_by_osm": round(100 * sum(hb) / len(b), 1),
            }
            if r == MATCH_RADIUS_M and want_pairs:
                pair_rows.append(pd.DataFrame({
                    "poi_class": cls, "source": "osm", "id": a["poi_physical_id"],
                    "name": a["name"], "lat": a["lat"], "lng": a["lng"],
                    "matched": ha}))
                pair_rows.append(pd.DataFrame({
                    "poi_class": cls, "source": "overture", "id": b["id"],
                    "name": b["name"], "lat": b["lat"], "lng": b["lng"],
                    "matched": hb}))
        rows[cls] = rec
    pairs = pd.concat(pair_rows, ignore_index=True) if pair_rows else None
    return rows, pairs


# --- D. độ tươi mức đối tượng ---------------------------------------------------
def _freshness(df, label):
    ts = pd.to_datetime(df["updated_at"], utc=True, errors="coerce")
    now = pd.Timestamp.now(tz="UTC")
    out = {"source": label, "n": int(len(df)),
           "n_with_timestamp": int(ts.notna().sum()),
           "pct_with_timestamp": round(100 * ts.notna().mean(), 1) if len(df) else 0.0}
    t = ts.dropna()
    if t.empty:
        return out
    out["median"] = t.median().date().isoformat()
    out["p10"] = t.quantile(0.10).date().isoformat()
    out["p90"] = t.quantile(0.90).date().isoformat()
    out["newest"] = t.max().date().isoformat()
    out["oldest"] = t.min().date().isoformat()
    for y in STALE_YEARS:
        out[f"pct_older_than_{y}y"] = round(
            100 * (t < now - pd.DateOffset(years=y)).mean(), 1)
    return out


def _freshness_by_class(osm, ovt):
    """Độ tươi theo lớp + **cổng chống độ-tươi-giả** cho phía Overture.

    Nếu `updated_at` của Overture chỉ có 1–2 giá trị phân biệt thì nó là *ngày giao lô*
    chứ không phải ngày sửa từng địa điểm, và mọi thống kê p50/p90 trên nó là vô nghĩa
    (chúng sẽ bằng nhau và trông rất "mới"). Ghi cờ vào báo cáo để người đọc không lỡ
    kết luận "Overture tươi hơn OSM 5 năm".
    """
    res = {}
    for cls in tax.SHARED_CLASSES:
        a, b = osm[osm["poi_class"] == cls], ovt[ovt["poi_class"] == cls]
        fo = _freshness(b, "overture")
        n_uniq = int(pd.to_datetime(b["updated_at"], utc=True, errors="coerce").nunique())
        fo["n_distinct_values"] = n_uniq
        # Cổng theo TỈ LỆ, không theo số tuyệt đối: lớp MALL có 20 giá trị phân biệt
        # trên 5.758 dòng (0,3%) — vẫn là ngày giao lô, chỉ lẫn vài trăm bản ghi
        # Foursquare/Microsoft có ngày thật. Ngưỡng tuyệt đối (">2") sẽ nói nhầm là
        # "có độ tươi mức đối tượng" và làm tắt cảnh báo ở bản Markdown.
        fo["object_level"] = len(b) > 0 and n_uniq / len(b) > 0.10
        if not fo["object_level"]:
            fo["warning"] = ("update_time là NGÀY GIAO LÔ của nhà cung cấp, không phải "
                             "ngày sửa từng địa điểm — không so được ở mức đối tượng")
        res[cls] = {"osm": _freshness(a, "osm"), "overture": fo}
    return res


# --- E. Overture có độc lập với OSM không --------------------------------------
def _provenance(ovt):
    out = {"overall": {str(k): int(v) for k, v in
                       ovt["src_dataset"].fillna("NULL").value_counts().items()},
           "by_class": {}}
    for cls in tax.SHARED_CLASSES:
        sub = ovt[ovt["poi_class"] == cls]
        if sub.empty:
            continue
        vc = sub["src_dataset"].fillna("NULL").value_counts()
        osm_like = int(sum(v for k, v in vc.items()
                           if "openstreetmap" in str(k).lower() or str(k).lower() == "osm"))
        out["by_class"][cls] = {"n": int(len(sub)),
                                "datasets": {str(k): int(v) for k, v in vc.items()},
                                "pct_from_osm": round(100 * osm_like / len(sub), 1)}
    return out


# --- F. recall trên nền độc lập (trạm sạc nêu đích danh) ------------------------
def _recall_vs_benchmark(osm, ovt, radii=(100.0, 200.0, 300.0)):
    """Dùng lại bằng chứng thực địa của `poi_recall.py` cho CẢ HAI nguồn.

    ⚠️ Chỉ dùng để **mô tả thiên lệch**, tuyệt đối không nhân/chia vào feature — lý do
    "rò rỉ mục tiêu" ghi trong docstring của `osm/poi_recall.py` vẫn nguyên giá trị.
    """
    st = pr._supply()
    if st is None:
        return {"skipped": "thiếu canonical stations"}
    txt = (st["name"].fillna("") + " " + st["address"].fillna("")).str.lower()
    out = {}
    for cls, keys in pr._KEYWORDS.items():
        bench = st[txt.str.contains("|".join(keys), regex=True, na=False)].reset_index(drop=True)
        if bench.empty:
            continue
        rec = {"n_benchmark": int(len(bench)), "recall_by_radius": {}}
        for r in radii:
            entry = {}
            for label, src in (("osm", osm), ("overture", ovt)):
                sub = src[src["poi_class"] == cls].reset_index(drop=True)
                if sub.empty:
                    entry[label] = None
                    continue
                hb, _ = _match_flags(bench, sub, r)
                entry[label] = round(sum(hb) / len(hb), 4)
            # hợp nhất 2 nguồn: điểm đối chiếu được phủ bởi ÍT NHẤT một nguồn
            a = osm[osm["poi_class"] == cls].reset_index(drop=True)
            b = ovt[ovt["poi_class"] == cls].reset_index(drop=True)
            if not a.empty and not b.empty:
                ha, _ = _match_flags(bench, a, r)
                hb2, _ = _match_flags(bench, b, r)
                entry["union"] = round(sum(x or y for x, y in zip(ha, hb2)) / len(ha), 4)
            rec["recall_by_radius"][str(int(r))] = entry
        out[cls] = rec
    return out


# --- H. nhiễu nhãn --------------------------------------------------------------
#: Danh từ riêng của từng lớp trong tên địa điểm (tiếng Việt + tên chuỗi phổ biến).
#: Tỉ lệ tên MANG danh từ của chính lớp mình là **chỉ báo** độ sạch nhãn, không phải
#: precision: một công viên tên "Bờ Hồ Sapa" là thật nhưng không khớp từ khoá nào.
#: Vì vậy con số này chỉ dùng để **so hai nguồn với nhau** trên cùng một thước đo.
_CLASS_NOUNS = {
    "FUEL": ["xăng", "xang", "dầu", "dau", "petrol", "pvoil", "pv oil", "comeco", "chxd", "gas"],
    "PARKING_OFF": ["bãi đỗ", "bai do", "bãi xe", "bai xe", "đậu xe", "dau xe", "gửi xe",
                    "giữ xe", "nhà xe", "nha xe", "parking", "hầm xe", "ham xe"],
    "MALL": ["trung tâm thương mại", "ttmt", "trung tâm mua sắm", "plaza", "mall",
             "vincom", "aeon", "lotte", "big c", "gigamall", "crescent"],
    "DEPT_STORE": ["bách hoá", "bách hóa", "bach hoa", "department", "thương xá"],
    "SUPERMARKET": ["siêu thị", "sieu thi", "mart", "supermarket", "co.op", "coop",
                    "winmart", "vinmart", "emart", "mega market"],
    "MARKET": ["chợ", "cho ", "market"],
    "APARTMENT": ["chung cư", "chung cu", "căn hộ", "can ho", "apartment", "toà nhà",
                  "tòa nhà", "toa nha", "block", "lô ", "ct1", "ct2", "hh1", "hh2"],
    "PARK": ["công viên", "cong vien", "vườn hoa", "vuon hoa", "park", "vườn quốc gia",
             "thảo cầm viên", "công viên nước"],
}

#: Nhãn **chắc chắn sai** — tên chứa mấy cụm này thì đối tượng không thể thuộc lớp đó.
#: Khác `_CLASS_NOUNS` ở chỗ đây là bằng chứng dương tính về nhiễu, không phải thiếu.
_CLASS_CONTRA = {
    "PARK": ["khu công nghiệp", "kcn", "nghĩa trang", "hoa viên nghĩa", "công ty",
             "cty", "tnhh", "nhà máy"],
    "PARKING_OFF": ["gara", "garage", "sửa chữa", "sua chua", "rửa xe", "chăm sóc ô",
                    "chăm sóc xe", "đồng sơn"],
    "MALL": ["cà phê", "ca phe", "coffee", "quán", "shop ", "nệm", "cửa hàng"],
    "SUPERMARKET": ["nội thất", "noi that", "ghế massage", "shop ", "quán"],
}


def _label_noise(osm, ovt):
    """% tên mang danh từ của chính lớp, và % tên mang dấu hiệu SAI lớp — cả 2 nguồn.

    Vì sao cần: chênh lệch số lượng ở §B **không** phân biệt được "phủ tốt hơn" với
    "gán nhãn rộng hơn". Lớp MALL của Overture đông gấp 22 lần OSM, nhưng nếu phần lớn
    tên là "Nệm Anh Thư"/"Coffee FIN" thì 22× là *nhiễu taxonomy*, không phải độ phủ —
    và đưa nó vào covariate cầu sẽ đưa vào toàn tiệm tạp hoá.
    """
    out = {}
    for cls in tax.SHARED_CLASSES:
        nouns = _CLASS_NOUNS.get(cls)
        if not nouns:
            continue
        rec = {}
        for label, src in (("osm", osm), ("overture", ovt)):
            s = src.loc[src["poi_class"] == cls, "name"].fillna("").str.lower()
            if s.empty:
                continue
            named = s.str.strip().ne("")
            hit = s.str.contains("|".join(nouns), regex=True, na=False)
            e = {"n": int(len(s)), "pct_named": round(100 * named.mean(), 1),
                 "pct_name_has_class_noun": round(100 * hit.mean(), 1),
                 "pct_of_named_with_class_noun": (round(100 * hit[named].mean(), 1)
                                                  if named.any() else None)}
            contra = _CLASS_CONTRA.get(cls)
            if contra:
                e["pct_name_contradicts_class"] = round(
                    100 * s.str.contains("|".join(contra), regex=True, na=False).mean(), 1)
            rec[label] = e
        out[cls] = rec
    return out


# --- G. phân bố không gian ------------------------------------------------------
def _spatial(osm, ovt):
    out = {}
    for cls in tax.SHARED_CLASSES:
        a = set(osm.loc[osm["poi_class"] == cls, "h3_r8"])
        b = set(ovt.loc[ovt["poi_class"] == cls, "h3_r8"])
        if not a and not b:
            continue
        out[cls] = {"cells_osm": len(a), "cells_overture": len(b),
                    "cells_both": len(a & b), "cells_osm_only": len(a - b),
                    "cells_overture_only": len(b - a),
                    "jaccard": round(len(a & b) / max(len(a | b), 1), 3)}
    return out


# --- báo cáo --------------------------------------------------------------------
def _markdown(rep):
    L = []
    A = L.append
    A("# OSM ⟷ Overture Places — đối chiếu tầng POI\n")
    A(f"_Sinh lúc {rep['generated_at_utc']} · Overture `{rep['release']}`_\n")

    A("## A. Ảnh chụp\n")
    o = rep["snapshots"]["overture"]
    s = rep["snapshots"]["osm"]
    A(f"- **Overture** release `{o.get('release')}` · quét lúc {o.get('fetched_at_utc')} "
      f"· {o.get('n_rows_bbox', 0):,} dòng trong cửa sổ bbox")
    A(f"- **OSM** `.pbf` chụp {s.get('pbf_snapshot')} · Overpass crawl: "
      + ", ".join(f"`{k}` {v[:10]}" for k, v in s["overpass_crawled_at_utc"].items()))
    A("")

    A("## B/C. Số lượng và chồng lấn (trong VN, sau khử trùng)\n")
    A(f"Ghép cặp ở bán kính **{int(MATCH_RADIUS_M)} m**.\n")
    A("| Lớp | OSM | Overture | Ovt/OSM | chỉ OSM | chỉ Ovt | trùng | % OSM được Ovt phủ | hợp nhất |")
    A("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for cls, r in rep["counts_overlap"].items():
        ov = r["overlap_by_radius"].get(str(int(MATCH_RADIUS_M)))
        if not ov:
            A(f"| {cls} | {r['n_osm']:,} | {r['n_overture']:,} | {r['ratio_overture_over_osm']} | — | — | — | — | — |")
            continue
        A(f"| {cls} | {r['n_osm']:,} | {r['n_overture']:,} | {r['ratio_overture_over_osm']} "
          f"| {ov['osm_only']:,} | {ov['overture_only']:,} | {ov['osm_matched']:,} "
          f"| {ov['pct_osm_covered_by_overture']}% | {ov['union_est']:,} |")
    A("")

    A("## D. Độ tươi (ngày sửa cuối, mức đối tượng)\n")
    if not any(r["overture"].get("object_level") for r in rep["freshness"].values()):
        A("> ⚠️ **Chỉ so được một chiều.** `update_time` của Overture ở VN là **ngày giao "
          "lô** của nhà cung cấp (`meta`, 99% số điểm) — mọi place mang cùng một ngày, "
          "xem `n_distinct_values`. OSM có ngày sửa THẬT cho từng đối tượng. Cột Ovt "
          "dưới đây là ngày lô, **không** so trực tiếp với p50 của OSM.\n")
    A("| Lớp | OSM p50 | OSM p10 | OSM %>5y | OSM % có ts | Ovt (ngày lô) | Ovt n giá trị |")
    A("|---|---|---|---:|---:|---|---:|")
    for cls, r in rep["freshness"].items():
        a, b = r["osm"], r["overture"]
        A(f"| {cls} | {a.get('median', '—')} | {a.get('p10', '—')} "
          f"| {a.get('pct_older_than_5y', '—')} | {a.get('pct_with_timestamp')}% "
          f"| {b.get('median', '—')} | {b.get('n_distinct_values', '—')} |")
    A("")

    A("## E. Overture có độc lập với OSM không?\n")
    A("| Lớp | n | % đến từ OpenStreetMap |")
    A("|---|---:|---:|")
    for cls, r in rep["provenance"]["by_class"].items():
        A(f"| {cls} | {r['n']:,} | {r['pct_from_osm']}% |")
    A("")

    A("## F. Recall trên nền độc lập (trạm sạc nêu đích danh)\n")
    A("| Lớp | n mốc | OSM @100m | Overture @100m | hợp nhất @100m |")
    A("|---|---:|---:|---:|---:|")
    for cls, r in rep.get("recall_vs_benchmark", {}).items():
        if not isinstance(r, dict) or "recall_by_radius" not in r:
            continue
        e = r["recall_by_radius"].get("100", {})
        f = lambda v: "—" if v is None else f"{100 * v:.1f}%"  # noqa: E731
        A(f"| {cls} | {r['n_benchmark']:,} | {f(e.get('osm'))} | {f(e.get('overture'))} "
          f"| {f(e.get('union'))} |")
    A("")

    A("## H. Nhiễu nhãn — chênh lệch số lượng có phải là độ phủ không?\n")
    A("`% tên có danh từ của lớp` là **chỉ báo so sánh** (tên không mang danh từ vẫn có "
      "thể đúng); `% tên mâu thuẫn` là bằng chứng dương tính về gán nhãn sai.\n")
    A("| Lớp | OSM % có tên | OSM % có danh từ lớp | Ovt % có tên | Ovt % có danh từ lớp | Ovt % tên mâu thuẫn |")
    A("|---|---:|---:|---:|---:|---:|")
    for cls, r in rep["label_noise"].items():
        a, b = r.get("osm", {}), r.get("overture", {})
        A(f"| {cls} | {a.get('pct_named', '—')}% | {a.get('pct_name_has_class_noun', '—')}% "
          f"| {b.get('pct_named', '—')}% | {b.get('pct_name_has_class_noun', '—')}% "
          f"| {b.get('pct_name_contradicts_class', '—')}{'%' if 'pct_name_contradicts_class' in b else ''} |")
    A("")

    A("## G. Phân bố không gian (ô H3 res 8)\n")
    A("| Lớp | ô OSM | ô Ovt | cả hai | Jaccard |")
    A("|---|---:|---:|---:|---:|")
    for cls, r in rep["spatial"].items():
        A(f"| {cls} | {r['cells_osm']:,} | {r['cells_overture']:,} "
          f"| {r['cells_both']:,} | {r['jaccard']} |")
    A("")
    if rep.get("unmapped_related_categories"):
        A("## Phụ lục — category Overture liên quan CHƯA ánh xạ\n")
        for row in rep["unmapped_related_categories"][:20]:
            A(f"- `{row['category']}` — {row['n']:,}")
    return "\n".join(L)


def compare(release=RELEASE, radii=MATCH_RADII_M, want_pairs=True):
    osm, ovt = _load_osm(), _load_overture()
    rep = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "release": release,
        "snapshots": _snapshots(release),
        "n_osm_points_vn": int(len(osm)),
        "n_overture_points_vn": int(len(ovt)),
        "match_radius_m": MATCH_RADIUS_M,
        "classes_without_overture_equivalent": tax.NO_OVERTURE_EQUIVALENT,
    }
    rep["counts_overlap"], pairs = _counts_and_overlap(osm, ovt, radii, want_pairs)
    rep["freshness"] = _freshness_by_class(osm, ovt)
    rep["provenance"] = _provenance(ovt)
    rep["recall_vs_benchmark"] = _recall_vs_benchmark(osm, ovt)
    rep["label_noise"] = _label_noise(osm, ovt)
    rep["spatial"] = _spatial(osm, ovt)
    return rep, pairs


def run(release=RELEASE, want_pairs=True):
    ensure_dirs()
    rep, pairs = compare(release, want_pairs=want_pairs)
    COMPARE_REPORT.write_text(json.dumps(rep, ensure_ascii=False, indent=2))
    COMPARE_MD.write_text(_markdown(rep))
    if pairs is not None:
        pairs.to_parquet(COMPARE_PAIRS, index=False)
    print(_markdown(rep))
    print(f"\n[compare] -> {COMPARE_REPORT}\n[compare] -> {COMPARE_MD}")
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--release", default=RELEASE)
    ap.add_argument("--no-pairs", action="store_true", help="bỏ qua parquet cặp ghép")
    a = ap.parse_args(argv)
    run(a.release, want_pairs=not a.no_pairs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
