#!/usr/bin/env python3
"""enrich_stations.py — E-DQ3 (phía TRẠM): điền nhãn hành chính + TRỌNG TÀI toạ độ.

Bốn cột `admin_l1_code`/`province_name`/`commune_name`/`commune_kind` được KHAI BÁO ở
`schema-contract` §3 nhưng **null 100%** trên cả 19.507 trạm — đây không phải "một cột
nullable đang null" mà là **vi phạm hợp đồng**: mọi consumer được hứa là lọc/nối được
theo tỉnh thì không làm được (AOI của E-DQ9 phải dùng hình TRÒN thay địa giới thật;
`demand_commune` chưa dựng được; `coverage_pop` cấp tỉnh của P10 không có khoá).

Nhưng phần đắt của E-DQ3 KHÔNG phải phép join. Nó là ba thứ dưới đây.

┌─ 1. NHÃN (E-DQ3a) — một phép join tất định, xong ngay ────────────────────────────┐
Point-in-polygon trên VNSDI cấp xã: **19.480/19.507 (99,86%)** khớp, **0 trạm** rơi vào
>1 xã. Trạm chưa resolve toạ độ (E-DQ1) thì **KHÔNG gán nhãn** — 38 trạm placeholder rơi
đúng vào một phường ở TP.HCM, gán nhãn cho chúng là biến một lỗi đã-biết thành một sự
thật hành chính trông rất thuyết phục. Bất biến: `có nhãn ⟺ coord_resolved`.

┌─ 2. TRỌNG TÀI TOẠ ĐỘ (E-DQ3b) — thứ E-DQ1 cố ý hoãn lại ──────────────────────────┐
27 trạm không rơi vào xã nào. Đo khoảng cách tới xã gần nhất cho ra **hai cụm tách bạch**
(dải rỗng 0,374 → 2,100 km): 11 trạm là **tổng quát hoá 1:1M** (xã gần nhất KHỚP địa chỉ)
-> snap; **16 trạm là lỗi toạ độ thật** -> `COORD_OUTSIDE_ADMIN`, `coord_resolved=False`,
`h3_r8=NULL`, loại khỏi cung (19.015 -> 18.999).

Vì sao lớp xã bắt được nhiều hơn `in_vn` của E-DQ7a (16 vs 4): polygon `admin_level=2`
**bao gồm lãnh hải** (506.834 km² so với 331.212 km² đất liền — Limitation của chính
E-DQ7a) nên chuỗi ramp giả `(9.0000xx, 107.0000xx)` nằm giữa Biển Đông vẫn "trong VN".
Ranh giới xã chỉ có đất ⇒ **nhạy hơn 4 lần** trên cùng một tập điểm.

┌─ 3. PHÂN XỬ 758 `COORD_ADDR_MISMATCH` (E-DQ3c) ───────────────────────────────────┐
E-DQ1 đo bằng Voronoi centroid-tỉnh và kết luận **~50/50, không tự quyết được** trường
nào sai, nên gắn cờ advisory và hoãn sang đây. Point-in-polygon + văn bản địa chỉ là hai
tín hiệu ĐỘC LẬP với nhau và với `province_code`:

    COORD_BAD        12  — ngoài mọi xã (>500 m)              => toạ độ sai, chắc chắn
    COORD_CONFIRMED 551  — tên XÃ **hoặc** tên TỈNH của polygon xuất hiện trong
                           `name`/`address` => toạ độ ĐÚNG, `province_code` mới là lỗi
    UNRESOLVED      195  — trong VN nhưng văn bản không xác nhận => GIỮ advisory

⇒ đóng được **74%** tồn đọng, không phải 50%. Ba lưu ý về mặt suy luận, ghi rõ để không
ai đọc quá lời:

  a. Tín hiệu **một chiều**. Khớp tên = bằng chứng toạ độ đúng; KHÔNG khớp **không** là
     bằng chứng toạ độ sai — địa chỉ evcs còn bẩn (E-DQ6 chưa chạy) và tỉ lệ khớp nền
     trên TOÀN tập cũng chỉ **79,8%**. Vì vậy 195 ca kia GIỮ NGUYÊN cờ, không bị loại.
  b. Dùng tên **xã** làm tín hiệu chính (không chỉ tên tỉnh) vì nó miễn nhiễm với chuyện
     sáp nhập tỉnh: **13,0%** địa chỉ vẫn ghi tên một tỉnh **đã giải thể** (`Kiên Giang`,
     `Bình Dương`…), nên so tên tỉnh một mình sẽ báo "không khớp" cho toạ độ hoàn toàn
     đúng. Đo được: xã 462 · tỉnh 501 · **hợp 551**.
  c. KHÔNG hardcode bảng sáp nhập 63->34 để "dịch" tên cũ. Bảng chép tay không kiểm
     chứng được, sai một dòng thì im lặng. Crosswalk ở đây **suy từ dữ liệu** kèm cổng
     cỡ mẫu + độ thuần (xem `build_crosswalk`).

┌─ NIÊN ĐẠI ────────────────────────────────────────────────────────────────────────┐
`province_code` của evcs là hệ **63 tỉnh CŨ** (65 giá trị: 63 tỉnh + `NA` rỗng + `AC` là
họ mã, không phải tỉnh). Nó **không phải** `admin_l1_code` và không được đổi tên thành —
mọi nhãn ở đây neo vào `ADMIN_VINTAGE = 2025-06-16` (34 tỉnh). Giữ cả hai cột cạnh nhau
là cố ý: `province_code` là provenance thô, `admin_l1_code` là sự thật hình học.

Cột thêm vào `stations`: 4 cột khai báo + `commune_code` (khoá join thật) + `admin_src`
/`admin_dist_m`/`admin_verdict` (provenance & trọng tài).

Chạy độc lập (đọc canonical, KHÔNG ghi đè — việc đó ở `transform_canonical`):
    PYTHONPATH=src python -m ev_siting.data.admin.enrich_stations --dump
"""
import argparse
import json
import re
import unicodedata

import numpy as np
import pandas as pd

from ..evcs.paths import STATIONS_DIR
from .boundaries import LABEL_COLS, assign_points, load_communes
from .paths import (ADMIN_SNAP_TOL_M, ADMIN_SOURCE, ADMIN_VINTAGE,
                    CROSSWALK_MIN_N, CROSSWALK_MIN_PURITY, EXPECTED_PROVINCES,
                    PROJECT_ROOT, PROVINCE_CROSSWALK, STATION_ADMIN_FLAGGED,
                    STATION_ADMIN_REPORT, ensure_dirs)

H3_RES = 8

MISMATCH_FLAG = "COORD_ADDR_MISMATCH"      # E-DQ1 detector B (advisory) — phân xử ở đây
OUTSIDE_FLAG = "COORD_OUTSIDE_ADMIN"       # E-DQ3b: ngoài mọi xã, quá dung sai snap
SNAPPED_FLAG = "ADMIN_COORD_SNAPPED"       # trong dung sai (tổng quát hoá 1:1M)
CONFLICT_FLAG = "ADMIN_PROVINCE_CONFLICT"  # tỉnh hình học != crosswalk(province_code)

#: Cột E-DQ3 thêm vào `stations` (4 cột khai báo nằm trong LABEL_COLS).
ADMIN_COLS = list(LABEL_COLS) + ["admin_src", "admin_dist_m", "admin_verdict"]

#: Tiền tố đơn vị hành chính cần bỏ trước khi so tên với văn bản địa chỉ.
_PREFIX = ("phuong", "xa", "dac khu", "thi tran", "quan", "huyen", "thanh pho",
           "tinh", "tp")
#: Tên ngắn dễ khớp bừa (vd "Xã An" khớp mọi chữ chứa "an") -> yêu cầu tối thiểu 4 ký tự.
_MIN_NAME_LEN = 4


def _norm(s) -> str:
    """Bỏ dấu + hạ chữ thường + chỉ giữ [a-z0-9 ] — so tên trên văn bản BẨN."""
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.replace("đ", "d").replace("Đ", "D")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]", " ", s.lower())).strip()


def _bare(name) -> str:
    """`Phường Ba Đình` -> `ba dinh` (bỏ tiền tố loại đơn vị)."""
    t = _norm(name)
    for p in _PREFIX:
        if t.startswith(p + " "):
            return t[len(p) + 1:]
    return t


def build_crosswalk(df: pd.DataFrame) -> pd.DataFrame:
    """`province_code` (hệ 63 cũ) -> `admin_l1_code` (34) SUY TỪ DỮ LIỆU, có cổng.

    Chỉ đếm trên các dòng toạ độ ĐÁNG TIN (`admin_src == 'inside'`, không cờ toạ độ) —
    nếu để toạ độ hỏng bỏ phiếu thì crosswalk chính là thứ nó phải giúp phát hiện.

    Mã nào không đủ `CROSSWALK_MIN_N` dòng **hoặc** độ thuần < `CROSSWALK_MIN_PURITY`
    -> `admin_l1_code = None` (AMBIGUOUS), KHÔNG đoán. Đo 2026-07-30: 63/65 mã có độ
    thuần >= 0,9379; hai mã trượt đúng là hai mã không phải tỉnh (`NA`, `AC`).

    Suy được từ cột CÔNG KHAI của bảng đã enrich (không cần trạng thái trung gian) nên
    gọi lại lúc nào cũng cho cùng kết quả — cả `enrich_admin` lẫn `admin_report` đều gọi."""
    flagged = df["quality_flags"].apply(
        lambda l: MISMATCH_FLAG in l if isinstance(l, (list, np.ndarray)) else False)
    trust = df[(df["admin_src"] == "inside")
               & df["coord_resolved"].fillna(False).astype(bool) & ~flagged]
    rows = []
    for code, g in trust.groupby("province_code", observed=True):
        vc = g["admin_l1_code"].value_counts()
        n, purity = len(g), float(vc.iloc[0] / len(g))
        ok = n >= CROSSWALK_MIN_N and purity >= CROSSWALK_MIN_PURITY
        rows.append({"province_code": code, "n": n, "purity": round(purity, 4),
                     "admin_l1_code": vc.index[0] if ok else None,
                     "status": "OK" if ok else "AMBIGUOUS"})
    cw = pd.DataFrame(rows, columns=["province_code", "n", "purity",
                                     "admin_l1_code", "status"])
    prov = load_communes().drop_duplicates("admin_l1_code").set_index("admin_l1_code")
    cw["province_name"] = cw["admin_l1_code"].map(prov["province_name"])
    return cw.sort_values(["status", "purity"]).reset_index(drop=True)


def enrich_admin(stations: pd.DataFrame) -> pd.DataFrame:
    """Điền nhãn hành chính + phân xử toạ độ. KHÔNG xoá dòng (nhất quán P6/P8/E-DQ1/2).

    Yêu cầu cột: station_id, lat, lng, h3_r8, province_code, name, address,
    coord_resolved, coord_src, quality_flags."""
    df = stations.copy().reset_index(drop=True)
    lab = assign_points(df["lat"].to_numpy(), df["lng"].to_numpy())
    df = pd.concat([df.drop(columns=[c for c in lab.columns if c in df.columns]),
                    lab], axis=1)

    # --- E-DQ3b: ngoài mọi xã & quá dung sai => toạ độ SAI (không phải join hụt) ---
    outside = df["admin_src"].eq("none") & df["lat"].notna()
    snapped = df["admin_src"].eq("nearest")

    # --- E-DQ3c: văn bản địa chỉ/tên trạm có xác nhận polygon không? (tín hiệu 1 chiều) ---
    txt = (df["address"].fillna("") + " " + df.get("name", pd.Series("", index=df.index))
           .fillna("")).map(_norm)
    xa = df["commune_name"].map(lambda v: _bare(v) if v else "")
    tinh = df["province_name"].map(lambda v: _bare(v) if v else "")
    hit_xa = [bool(x) and len(x) >= _MIN_NAME_LEN and x in t for x, t in zip(xa, txt)]
    hit_tinh = [bool(p) and len(p) >= _MIN_NAME_LEN and p in t for p, t in zip(tinh, txt)]
    corroborated = pd.Series(hit_xa, index=df.index) | pd.Series(hit_tinh, index=df.index)

    flagged = df["quality_flags"].apply(
        lambda l: MISMATCH_FLAG in l if isinstance(l, (list, np.ndarray)) else False)
    resolved_in = df["coord_resolved"].fillna(False).astype(bool)

    verdict = np.select(
        [~resolved_in, outside, flagged & corroborated, flagged],
        ["NO_COORD", "COORD_BAD", "COORD_CONFIRMED", "UNRESOLVED"],
        default="NOT_FLAGGED")
    df["admin_verdict"] = verdict

    # --- áp phán quyết: chỉ COORD_BAD mới đổi tập cung (giống cây của E-DQ1) ---
    bad = df["admin_verdict"].eq("COORD_BAD")
    df.loc[bad, "coord_resolved"] = False
    df.loc[bad, "coord_src"] = "outside_admin"
    df.loc[bad, "h3_r8"] = None

    # --- BẤT BIẾN: có nhãn <=> coord_resolved. Trạm chưa biết đứng ở đâu thì KHÔNG có
    #     nhãn hành chính (38 placeholder rơi vào một phường TP.HCM — gán nhãn cho chúng
    #     là mặc một sự thật hành chính lên một lỗi đã biết). ---
    unknown = ~df["coord_resolved"].fillna(False).astype(bool)
    df.loc[unknown, LABEL_COLS] = None
    df.loc[unknown, "admin_src"] = "unresolved"
    df.loc[unknown, "admin_dist_m"] = np.nan

    # --- crosswalk + cờ xung đột tỉnh (advisory, KHÔNG loại khỏi cung) ---
    cw = build_crosswalk(df)
    cw_map = cw.set_index("province_code")["admin_l1_code"].to_dict()
    expected = df["province_code"].map(cw_map)
    conflict = (expected.notna() & df["admin_l1_code"].notna()
                & (expected != df["admin_l1_code"]))

    add = {OUTSIDE_FLAG: bad, SNAPPED_FLAG: snapped & ~bad, CONFLICT_FLAG: conflict}
    new_flags = []
    for i, fl in enumerate(df["quality_flags"]):
        cur = list(fl) if isinstance(fl, (list, np.ndarray)) else []
        cur += [f for f, m in add.items() if bool(m.iat[i]) and f not in cur]
        new_flags.append(cur)
    df["quality_flags"] = new_flags
    return df


def admin_report(df: pd.DataFrame) -> dict:
    """Thống kê + 7 cổng QA (đóng E-DQ3 phía trạm THẬT, không chỉ 'có cột không null')."""
    cw = build_crosswalk(df)
    resolved = df["coord_resolved"].fillna(False).astype(bool)
    labelled = df["commune_code"].notna()
    supply = (resolved & df["is_operational"] & df["access"].eq("PUBLIC")
              & df["is_primary"]) if "is_operational" in df.columns else resolved
    com = load_communes()
    gates = {}

    # ① tỉ lệ join trên tập ĐÁNG GÁN (toạ độ đã resolve). Cổng FAIL được: polygon sai
    #    niên đại / sai hệ toạ độ sẽ kéo tỉ lệ này sập chứ không im lặng.
    rate = float(labelled[resolved].mean()) if resolved.any() else 0.0
    gates["admin_join_rate"] = bool(rate >= 0.995)

    # ② BẤT BIẾN nhãn <=> coord_resolved (không nhãn cho vị trí chưa biết, và ngược lại
    #    không có trạm resolved nào bị bỏ trắng nhãn).
    gates["admin_iff_coord_resolved"] = bool((labelled == resolved).all())

    # ③ mọi nhãn nằm trong ĐÚNG MỘT niên đại: 34 tỉnh của lớp VNSDI. Đây là cổng lẽ ra
    #    phải bắt được chuyện dùng nhầm 40 polygon adm4 của OSM (có cả bản "cũ").
    known = set(com["admin_l1_code"])
    seen = set(df.loc[labelled, "admin_l1_code"])
    gates["admin_vintage_single"] = bool(seen <= known and len(known) == EXPECTED_PROVINCES)

    # ④ toạ độ ngoài mọi xã PHẢI bị loại khỏi cung (không được vừa "không thuộc xã nào"
    #    vừa được tính là cung ở một ô H3 nào đó).
    bad = df["admin_verdict"].eq("COORD_BAD")
    gates["outside_admin_excluded"] = bool(
        (~df.loc[bad, "coord_resolved"].fillna(False)).all()
        and df.loc[bad, "h3_r8"].isna().all())

    # ⑤ crosswalk phủ hết mã tỉnh THẬT và đổ về đúng 34 tỉnh (mã AMBIGUOUS được phép
    #    tồn tại — nhưng phải là mã không-phải-tỉnh, kiểm bằng cổng ⑥).
    ok_cw = cw[cw["status"] == "OK"] if len(cw) else cw
    gates["crosswalk_total"] = bool(
        len(ok_cw) and ok_cw["admin_l1_code"].nunique() <= EXPECTED_PROVINCES
        and ok_cw["purity"].min() >= CROSSWALK_MIN_PURITY)

    # ⑥ mọi mã AMBIGUOUS phải là mã KHÔNG phải tỉnh. `NA` = province_code rỗng; `AC` =
    #    họ mã `C.AC…`. Nếu một mã tỉnh thật rơi vào đây => sáp nhập đã chia nhỏ một
    #    tỉnh cũ ra nhiều tỉnh mới và crosswalk 1-1 hết đúng => phải xem lại, không im.
    gates["ambiguous_codes_are_nonprovince"] = bool(
        set(cw.loc[cw["status"] != "OK", "province_code"]) <= {"NA", "AC"}
        if len(cw) else True)

    # ⑦ mọi trạm CUNG phải có nhãn (đây là điều kiện để `coverage_pop` cấp tỉnh/xã của
    #    P10 tính được — không có nhãn thì trạm biến mất khỏi mẫu số).
    gates["supply_fully_labelled"] = bool(labelled[supply].all() if supply.any() else True)

    verdicts = df["admin_verdict"].value_counts().to_dict()
    return {
        "admin_vintage": ADMIN_VINTAGE, "admin_source": ADMIN_SOURCE,
        "snap_tol_m": ADMIN_SNAP_TOL_M,
        "n_input": int(len(df)),
        "n_labelled": int(labelled.sum()),
        "join_rate_on_resolved": round(rate, 5),
        "admin_src": df["admin_src"].value_counts().to_dict(),
        "verdicts": verdicts,
        "n_outside_admin": int(bad.sum()),
        "n_snapped": int(df["admin_src"].eq("nearest").sum()),
        "n_province_conflict": int(df["quality_flags"].apply(
            lambda l: CONFLICT_FLAG in l).sum()),
        "n_supply": int(supply.sum()),
        "n_provinces": int(df.loc[labelled, "admin_l1_code"].nunique()),
        "n_communes": int(df.loc[labelled, "commune_code"].nunique()),
        "n_crosswalk_ok": int((cw["status"] == "OK").sum()) if len(cw) else 0,
        "crosswalk_ambiguous": cw.loc[cw["status"] != "OK", "province_code"].tolist()
        if len(cw) else [],
        "gates": gates,
        "all_gates_pass": bool(all(gates.values())),
    }


def _load_canonical() -> pd.DataFrame:
    cols = ["station_id", "station_code", "lat", "lng", "h3_r8", "province_code",
            "name", "address", "quality_flags", "coord_resolved", "coord_src",
            "is_operational", "access", "is_primary"]
    return pd.read_parquet(STATIONS_DIR, columns=cols)


def main():
    ap = argparse.ArgumentParser(
        description="E-DQ3 (trạm): nhãn hành chính + trọng tài toạ độ (inspect, không ghi đè)")
    ap.add_argument("--dump", action="store_true", help="dump trạm bị cờ ra CSV để eyeball")
    args = ap.parse_args()
    ensure_dirs()

    out = enrich_admin(_load_canonical())
    rep = admin_report(out)
    cw = build_crosswalk(out)
    cw.to_csv(PROVINCE_CROSSWALK, index=False)
    STATION_ADMIN_REPORT.write_text(json.dumps(rep, ensure_ascii=False, indent=2),
                                    encoding="utf-8")

    rel = lambda p: p.relative_to(PROJECT_ROOT)
    print("================ E-DQ3 NHÃN HÀNH CHÍNH (TRẠM) ================")
    print(f"  nguồn / niên đại        : {rep['admin_source']} / {rep['admin_vintage']}")
    print(f"  input                   : {rep['n_input']:,}")
    print(f"  gán nhãn được           : {rep['n_labelled']:,} "
          f"({rep['join_rate_on_resolved']:.4%} trên tập coord_resolved)")
    print(f"  admin_src               : {rep['admin_src']}")
    print(f"  phủ                     : {rep['n_provinces']} tỉnh · {rep['n_communes']:,} xã")
    print("--- E-DQ3b (trọng tài toạ độ bằng ranh giới xã) -----------")
    print(f"  snap <= {ADMIN_SNAP_TOL_M:.0f} m (1:1M)   : {rep['n_snapped']:,}")
    print(f"  COORD_OUTSIDE_ADMIN     : {rep['n_outside_admin']:,} (loại khỏi cung, h3_r8=NULL)")
    print("--- E-DQ3c (phân xử COORD_ADDR_MISMATCH) ------------------")
    for k in ("COORD_CONFIRMED", "COORD_BAD", "UNRESOLVED"):
        print(f"  {k:<22}: {rep['verdicts'].get(k, 0):,}")
    print(f"  ADMIN_PROVINCE_CONFLICT : {rep['n_province_conflict']:,} (advisory)")
    print("--- crosswalk 63 -> 34 ------------------------------------")
    print(f"  mã OK / AMBIGUOUS       : {int((cw['status'] == 'OK').sum())} / "
          f"{int((cw['status'] != 'OK').sum())} {rep['crosswalk_ambiguous']}")
    print(f"  -> {rel(PROVINCE_CROSSWALK)}")
    print(f"  QA gates (7 cổng)       : {rep['gates']}")
    print(f"  ALL GATES PASS          : {rep['all_gates_pass']}")
    if args.dump:
        m = out["admin_verdict"].ne("NOT_FLAGGED") | out["quality_flags"].apply(
            lambda l: CONFLICT_FLAG in l or SNAPPED_FLAG in l)
        out.loc[m, ["station_id", "province_code", "admin_l1_code", "province_name",
                    "commune_name", "admin_src", "admin_dist_m", "admin_verdict",
                    "lat", "lng", "address"]].to_csv(STATION_ADMIN_FLAGGED, index=False)
        print(f"  trạm bị cờ -> {rel(STATION_ADMIN_FLAGGED)}")
    print(f"-> {rel(STATION_ADMIN_REPORT)}")
    print("==============================================================")
    return out, rep


if __name__ == "__main__":
    main()
