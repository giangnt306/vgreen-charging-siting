"""CLI của assess() — ``python -m ev_siting.assess.cli <sub>`` (Done B3: CSV→CSV + cache F19 + T1).

Ba subcommand tách bạch ba hành động CHỦ Ý:
- ``score``: chấm một file CSV điểm; mode retrodiction BẮT BUỘC ``--exclude-new-from``
  (parquet new_supply) — không cho chạy "retro" trên nền còn nguyên wave NEW (leakage §2);
- ``build-occupancy``: cày 18,6M dòng telemetry là hành động đắt, không được xảy ra ngầm
  trong lúc chấm điểm (occupancy.load_occupancy đã chặn tự-build);
- ``t1``: chạy retrodiction đóng băng §5, chạy MỘT lần as-is;
- ``sizing``: build bảng benchmark utilization theo (loại trụ × mật độ × số cổng);
- ``dossier``: **deliverable v1** — lập hồ sơ thẩm định dạng facts, không xuất điểm số
  (lý do đổi: xem `dossier.py` và docs/sprint2/postmortem-assess-v0.md).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from ev_siting.assess import dossier, engine, occupancy, params, paths, retrodiction, sizing, spotcheck

#: Cột list trong output engine — CSV không có kiểu list nên join " | " (đọc lại tách được).
_LIST_COLS = ("gates_fired", "reasons")


def _cmd_score(args) -> None:
    pts = pd.read_csv(args.inp)
    exclude: tuple[str, ...] = ()
    if args.mode == "retrodiction":
        # Danh sách purge lấy từ CHÍNH gold new_supply — cùng đường đọc với T1, không cho
        # người dùng tự gõ tay danh sách mã (dễ lệch map, lệch wave).
        _, codes, _ = retrodiction.load_ground_truth(Path(args.exclude_new_from))
        exclude = tuple(params.station_id_from_code(c) for c in codes)
    actx = engine.make_context(
        mode=args.mode,
        exclude_station_ids=exclude,
        credit_rule=args.credit,
        scope=args.scope,
        label=args.label,
    )
    out = engine.assess(pts, actx, plan=args.plan)

    flat = out.copy()
    for col in _LIST_COLS:
        flat[col] = [" | ".join(v) for v in flat[col]]
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    flat.to_csv(out_path, index=False)

    print(f"Đã chấm {len(out)} điểm (mode={args.mode}, plan={args.plan}) -> {out_path}")
    for tier, cnt in out["tier"].value_counts().items():
        print(f"  {tier}: {int(cnt)}")


def _cmd_build_occupancy(args) -> None:
    if paths.OCC_CACHE.exists() and paths.OCC_META.exists() and not args.force:
        # Cache là dẫn xuất tái lập được — nhưng build lại 460MB phải là lựa chọn tường minh.
        print(f"Cache F19 đã có: {paths.OCC_CACHE} — dùng --force nếu muốn build lại")
        return
    stats = occupancy.build_occupancy_cache()
    print(f"Đã build cache F19: {len(stats)} trạm -> {paths.OCC_CACHE}")


def _cmd_t1(args) -> None:
    results = retrodiction.run_t1(ground_truth_path=args.ground_truth)
    # run_t1 đã in summary một dòng; ở đây in metrics JSON đầy đủ cho người gọi pipe tiếp.
    print(json.dumps(results["metrics"], ensure_ascii=False, indent=2))


def _cmd_sizing(args) -> None:
    table = sizing.build_benchmark(scope=args.scope, label=args.label)
    ok = table[table["reportable"]]
    print(f"Benchmark định cỡ: {len(ok)}/{len(table)} nhóm đủ mẫu (≥{sizing.MIN_GROUP_N}) -> {sizing.BENCH_PATH}")
    print(ok.to_string(index=False))


def _cmd_dossier(args) -> None:
    """Deliverable v1: hồ sơ facts thay cho điểm số — xem dossier.py phần 'vì sao đổi'."""
    pts = pd.read_csv(args.inp)
    dctx = dossier.build_context(scope=args.scope, label=args.label)
    out_dir = Path(args.out_dir)
    (out_dir / "md").mkdir(parents=True, exist_ok=True)

    for i, r in pts.reset_index(drop=True).iterrows():
        pid = str(r["point_id"]) if "point_id" in pts.columns else f"HS-{i:04d}"
        d = dossier.make_dossier(float(r["lat"]), float(r["lng"]), dctx, point_id=pid)
        (out_dir / "md" / f"{pid}.md").write_text(dossier.render_markdown(d) + "\n", encoding="utf-8")

    tab = dossier.batch(pts, dctx)
    tab.to_csv(out_dir / "dossier_batch.csv", index=False)
    print(f"Đã lập {len(tab)} hồ sơ -> {out_dir}/md/*.md  +  {out_dir}/dossier_batch.csv")
    print(tab["verdict"].value_counts().to_string())


def _cmd_spotcheck(args) -> None:
    """B8 — 20 hồ sơ bẫy + oracle độc lập. Mục tiêu công bố: 0 lỗi fact."""
    tab = spotcheck.run(scope=args.scope, label=args.label)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    tab.to_csv(out_dir / "spotcheck.csv", index=False)
    (out_dir / "spotcheck.md").write_text(spotcheck.render_markdown(tab), encoding="utf-8")
    n_bad = int((tab["lỗi_fact"] != "").sum())
    print(f"{len(tab)} điểm bẫy · **{n_bad} lỗi fact** -> {out_dir}/spotcheck.{{csv,md}}")
    for _, r in tab[tab["lỗi_fact"] != ""].iterrows():
        print(f"  [LỆCH] {r['point_id']} {r['địa_điểm']}: {r['lỗi_fact']}")
    raise SystemExit(1 if n_bad else 0)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="python -m ev_siting.assess.cli",
        description="Máy thẩm định vị trí trạm sạc assess() v0 — tham số đóng băng theo pre-reg B2",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sc = sub.add_parser("score", help="chấm CSV điểm (lat,lng[,point_id]) -> CSV kết quả")
    sc.add_argument("--in", dest="inp", required=True, help="CSV vào: cột lat,lng[,point_id]")
    sc.add_argument("--out", required=True, help="CSV ra (cột list join ' | ')")
    sc.add_argument("--mode", choices=("live", "retrodiction"), default="live")
    sc.add_argument("--plan", action="store_true", help="coi cả file là MỘT kế hoạch (chia công + G3)")
    sc.add_argument("--credit", choices=params.CREDIT_RULES, default=params.DEFAULT_CREDIT_RULE)
    sc.add_argument("--scope", default=params.SCOPE)
    sc.add_argument("--label", default=params.FREEZE_LABEL)
    sc.add_argument(
        "--exclude-new-from",
        dest="exclude_new_from",
        default=None,
        metavar="PATH",
        help="parquet gold new_supply để purge wave NEW — BẮT BUỘC khi --mode retrodiction",
    )

    bo = sub.add_parser("build-occupancy", help="build cache occupancy F19 từ telemetry frozen")
    bo.add_argument("--force", action="store_true", help="build lại kể cả khi cache đã có")

    t1 = sub.add_parser("t1", help="chạy T1 retrodiction đóng băng (pre-reg §5)")
    t1.add_argument("--ground-truth", dest="ground_truth", default=None, metavar="PATH")

    sz = sub.add_parser("sizing", help="build bảng benchmark định cỡ (utilization theo loại trụ × mật độ)")
    sz.add_argument("--scope", default=params.SCOPE)
    sz.add_argument("--label", default=params.FREEZE_LABEL)

    spc = sub.add_parser("spotcheck", help="B8 — chấm 20 điểm bẫy + kiểm lại mọi fact bằng oracle độc lập")
    spc.add_argument("--out-dir", dest="out_dir", default=str(paths.OUT_DIR / "spotcheck"))
    spc.add_argument("--scope", default=params.SCOPE)
    spc.add_argument("--label", default=params.FREEZE_LABEL)

    ds = sub.add_parser("dossier", help="lập HỒ SƠ THẨM ĐỊNH (deliverable v1 — facts, không điểm số)")
    ds.add_argument("--in", dest="inp", required=True, help="CSV vào: cột lat,lng[,point_id]")
    ds.add_argument("--out-dir", dest="out_dir", default=str(paths.OUT_DIR / "dossier"))
    ds.add_argument("--scope", default=params.SCOPE)
    ds.add_argument("--label", default=params.FREEZE_LABEL)

    args = p.parse_args(argv)
    if args.cmd == "score":
        if args.mode == "retrodiction" and not args.exclude_new_from:
            # parser.error thoát mã 2 — retro tay không là leakage, chặn từ tầng CLI (§2).
            p.error("--mode retrodiction bắt buộc --exclude-new-from PATH (parquet new_supply)")
        _cmd_score(args)
    elif args.cmd == "build-occupancy":
        _cmd_build_occupancy(args)
    elif args.cmd == "sizing":
        _cmd_sizing(args)
    elif args.cmd == "dossier":
        _cmd_dossier(args)
    elif args.cmd == "spotcheck":
        _cmd_spotcheck(args)
    else:
        _cmd_t1(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
