# Bản đồ khác biệt nhánh — 2026-07-30

> ⛔ **HỒ SƠ LỊCH SỬ — số liệu trong file này ĐÃ BỊ THAY THẾ.** Đây là biên bản chốt tại thời điểm
> ghi trên tiêu đề; **cố ý không cập nhật** để giữ đúng dấu vết quyết định. Số hiện hành (rebuild
> toàn chuỗi **2026-07-31**, snapshot `2026-07-20`): `stations` **19.507 × 56** · `connectors`
> **24.415 × 11** · master **28.625** · cung **19.181 / 12.801 ô** · `candidate_sites` **16.686 × 16** ·
> `covered0` **19.012**. Nguồn chân lý: [dataset-inventory.md](../data-layer/dataset-inventory.md) ·
> [overview.md](../data-layer/overview.md) · [processed-data-checklist.md](../data-layer/processed-data-checklist.md).

Chuẩn bị cho hợp nhất `integrate/final`. Giai đoạn này **chỉ đọc**, chưa sửa gì.

## Tham chiếu

| | |
|---|---|
| merge-base | `495b0c3` |
| `data/giang` (Giang) | `3a836cc` — 14 commit, **+10 023 / −845** trên 87 file |
| `devky/review-dataset` (Kỳ) | `67f3f14` — 6 commit, **+4 676 / −901** trên 69 file |
| Working tree (chưa commit, trên devky) | **+45 769 / −20** trên 32 file — xem Phụ lục E |

## Commit từng bên (từ merge-base)

### data/giang
```
3a836cc docs: restructure issue docs and refresh data quality documentation
afe27a3 fix(data): address E-DQ3 by populating administrative columns for stations and demand grid
cdf0f1c fix(data): address E-DQ4 by implementing asset/live configuration resolver and validation gates
30c58dc fix(data): address E-DQ8 by classifying missing demand cells from road lookup and persisting access_tier
1dd25a7 feat(data): implement E-DQ7f population reconciliation with VNSDI
08e7620 feat(vnsdi): complete pixel-commune join and generate E-DQ7f analysis artefacts
afac5ff fix(data-worldpop): switch to UN-adjusted raster and validate E-DQ7e gates
537c4bb docs(data-quality): split E-DQ7e into calibration and dasymetric issues
7a537b0 feat(docs): hand off E-DQ7d to Ky
a96c5b4 refactor(poi): separate POI semantics and improve data quality validation
1bf8b07 feat(data): resolve E-DQ7b by separating road access and demand semantics
79d2214 feat(data): resolve E-DQ7a with Vietnam boundary clipping, in_vn validation, and demand QA gates
8a260cb fix(docs): split E-DQ7 into five sub-problems in the register table
346d770 feat(data): implement E-DQ1 coordinate quality pipeline
```

### devky/review-dataset
```
67f3f14 idk
8f44dd1 fix(pipeline): close F8/F9/F13-F16/F18 + move E-DQ1 coord policy in-repo
9f80409 fix(pipeline): close F7/F10/F12 + wire matcher into canonical
a96766a fix(pipeline): close F2–F6 + F10 export from 2026-07-28 review
c115c37 rm ci
17558f8 start review
```

## Nhóm A — chỉ Giang đổi (file có sẵn ở merge-base)

| File | Trạng thái |
|---|---|
| docs/README.md | M (⚠ working tree Kỳ cũng sửa — xem E) |
| docs/problem-analysis.md | M |
| docs/schema/schema-review.md | M |
| docs/sources/osm.md | M |
| docs/sources/worldpop.md | M |
| src/ev_siting/data/landuse/__init__.py | M |
| src/ev_siting/data/osm/__init__.py | M |

## Nhóm B — chỉ Kỳ đổi (file có sẵn ở merge-base)

| File | Trạng thái |
|---|---|
| .github/workflows/ci.yml | **D** (xóa CI) |
| .gitignore | M (⚠ working tree sửa thêm) |
| LICENSE | **D** |
| app/.gitkeep | **D** |
| config/params.yaml | **D** (Giang chỉ còn tham chiếu trong README + 1 issue doc, không có code dùng) |
| notebooks/01-giang-eda-stations.ipynb | **D** |
| notebooks/02-ky-mclp-toy-example.ipynb | **D** |
| pyproject.toml | M |
| src/ev_siting/aoi.py | M |
| src/ev_siting/data/evcs/build_master_evcs.py | M |
| src/ev_siting/data/evcs/dedup_crosssource.py | M |
| src/ev_siting/data/evcs/evcs_enumerate.py | M (+430 dòng — seed discovery, tầng lấy mẫu) |
| src/ev_siting/data/evcs/evcs_probe.py | M |
| src/ev_siting/data/evcs/evcs_scrape.py | M (+317) |
| src/ev_siting/data/evcs/merge_catalog.py | M |
| src/ev_siting/data/evcs/paths.py | M |
| src/ev_siting/data/evcs/run_pipeline.sh | M |
| src/ev_siting/data/evcs/split_timeseries.py | M |
| src/ev_siting/data/landuse/paths.py | M |
| src/ev_siting/data/landuse/worldcover.py | M |
| src/ev_siting/data/opex_electricity.py | M |
| src/ev_siting/data/provenance/freeze_snapshot.py | M |
| src/ev_siting/data/vinfast_official/fetch_locators.py | M |
| src/ev_siting/data/vinfast_official/match_official.py | M |
| src/ev_siting/data/vinfast_official/paths.py | M |
| src/ev_siting/features/paths.py | M |
| tests/test_candidates.py | M |
| tests/test_landuse.py | M |

## Nhóm C — cả hai đổi (vùng xung đột thực sự)

Con số là mức thay đổi mỗi bên (dòng +/− so với merge-base).

| File | Giang | Kỳ | Ghi chú |
|---|---|---|---|
| .claude/settings.json | M +153 | **D** | Giang sửa, Kỳ xóa — allowlist quyền cá nhân của Giang (`/home/wanderer210/…`) → hỏi B3 |
| Makefile | ±43 | ±64 | working tree Kỳ sửa thêm ±28 |
| README.md | ±12 | ±91 | |
| data/raw/MANIFEST.json | ±218 | ±145 | hai bên ghi manifest khác nhau |
| db/{migrations,seeds}/.gitkeep | R → config/db/ | **D** | tầm thường |
| docs/data-layer/candidate-sites.md | ±55 | ±53 | |
| docs/data-layer/overview.md | ±361 (viết lại) | ±6 | |
| docs/known-issues.md | ±459 (tái cấu trúc → docs/issues/) | +70 | working tree +234 |
| docs/schema/data-dictionary.md | ±2 | +11 | |
| docs/schema/schema-contract.md | ±93 | ±11 | working tree ±9 |
| docs/sources/evcs.md | ±2 | ±21 | |
| src/ev_siting/data/evcs/transform_canonical.py | +113 | +338 | **nặng cả hai bên** |
| src/ev_siting/data/evcs/validate.py | +42 | ±14 | |
| src/ev_siting/data/landuse/build_buildable_h3.py | +120 | ±47 | |
| src/ev_siting/data/landuse/osm_exclusion.py | ±41 | ±7 | |
| src/ev_siting/data/osm/build_osm_h3.py | +268 | ±42 | |
| src/ev_siting/data/osm/overpass_poi.py | ±18 | ±10 | |
| src/ev_siting/data/osm/paths.py | ±18 | ±6 | |
| src/ev_siting/data/osm/roads_pbf.py | +107 | ±7 | |
| src/ev_siting/data/osm/validate.py | +341 | ±22 | |
| src/ev_siting/data/provenance/manifest.py | ±33 | ±45 | |
| src/ev_siting/data/worldpop/build_demand_h3.py | +273 | +107 | **nặng cả hai bên** |
| src/ev_siting/data/worldpop/paths.py | ±72 | ±33 | |
| src/ev_siting/data/worldpop/worldpop_pop.py | +130 | ±60 | UN-adjusted (Giang) vs settlement mask (Kỳ) |
| src/ev_siting/features/build_candidates.py | +104 | +263 | **nặng cả hai bên** |
| src/ev_siting/features/build_covered0.py | +65 | +184 | **nặng cả hai bên** |

## Nhóm D — file mới chỉ tồn tại ở một bên

### D-Giang

| File | Vai trò |
|---|---|
| docs/data-layer/dataset-inventory.md | docs |
| docs/issues/README.md + 26 file docs/issues/** | sổ đăng ký vấn đề P1–P11, E-DQ1–E-DQ10 (tách từ known-issues.md) |
| docs/reports/evcs-data-quality.md | báo cáo |
| src/ev_siting/data/admin/{__init__,boundaries,enrich_grid,enrich_stations,paths}.py | enrich hành chính (E-DQ3) |
| src/ev_siting/data/evcs/export_supply.py | export cung (⚠ so với export_handoff.py của Kỳ) |
| src/ev_siting/data/evcs/fix_coords.py | pipeline tọa độ E-DQ1 (⚠ trùng vai trò coord_quality.py của Kỳ) |
| src/ev_siting/data/evcs/resolve_config.py | resolver asset/live config (E-DQ4) |
| src/ev_siting/data/osm/access_tiers.py | phân tầng tiếp cận (E-DQ8a) |
| src/ev_siting/data/osm/poi_recall.py | recall POI |
| src/ev_siting/data/osm/poi_semantics.py | tách ngữ nghĩa POI (E-DQ7c) |
| src/ev_siting/data/osm/road_semantics.py | tách ngữ nghĩa đường (E-DQ7b) |
| src/ev_siting/data/osm/vn_boundary.py | cắt biên VN 402 dòng (⚠ trùng vai trò src/ev_siting/vn_boundary.py của Kỳ) |
| src/ev_siting/data/vnsdi/{__init__,fetch_communes,paths}.py | xã/phường VNSDI (E-DQ7f) |
| src/ev_siting/data/worldpop/reallocate_roadless.py | tái phân bổ ô không đường (E-DQ8b) |
| src/ev_siting/data/worldpop/reconcile_dasymetric.py | đối soát dân số dasymetric (E-DQ7f) |
| tests/test_access_tiers.py, test_admin.py, test_config_semantics.py, test_export_supply.py, test_poi_semantics.py, test_road_semantics.py | test của Giang |

### D-Kỳ

| File | Vai trò |
|---|---|
| data/raw/MANIFEST-2026-07-20.json | snapshot manifest cũ |
| docs/sprint-reviews/data-pipeline-review-2026-07-{24,28}.md | biên bản review nguồn gốc chuỗi F1–F18 |
| src/ev_siting/data/evcs/admin_join.py | join hành chính (⚠ trùng vai trò data/admin/* của Giang) |
| src/ev_siting/data/evcs/compare_runs.py | so sánh hai lần crawl |
| src/ev_siting/data/evcs/coord_quality.py | chất lượng tọa độ E-DQ1 (⚠ trùng vai trò fix_coords.py của Giang) |
| src/ev_siting/data/evcs/export_handoff.py | export bàn giao (⚠ so với export_supply.py của Giang) |
| src/ev_siting/data/evcs/session.py | 1-phiên-Cloudflare (giao thức evcs.vn 29/07) |
| src/ev_siting/data/worldpop/settlement.py | mặt nạ settlement (⚠ giao vai trò reallocate_roadless/reconcile_dasymetric của Giang) |
| src/ev_siting/vn_boundary.py | cắt biên VN 138 dòng (⚠ trùng vai trò osm/vn_boundary.py của Giang) |
| tests/test_covered0.py, test_f7_f12_integrity.py, test_f8_f9_f13_f14_f16.py, test_timeseries_integrity.py | test của Kỳ (working tree sửa thêm) |

## Va chạm ngữ nghĩa (khác file, cùng bài toán) — trọng tâm Bước 2/3

Đây là xung đột thật dù không đụng nhau ở mức file:

1. **Biên giới VN**: `osm/vn_boundary.py` (Giang, 402 dòng, gắn vào pipeline OSM E-DQ7a) vs `src/ev_siting/vn_boundary.py` (Kỳ, 138 dòng, dùng chung + test_vn_boundary.py ở working tree).
2. **Chất lượng tọa độ (E-DQ1)**: `evcs/fix_coords.py` (Giang) vs `evcs/coord_quality.py` (Kỳ, kèm chính sách E-DQ1 in-repo + test_coord_quality.py).
3. **Enrich hành chính (E-DQ3)**: gói `data/admin/*` (Giang) vs `evcs/admin_join.py` (Kỳ, kèm test_admin_join.py). Hai bên có thể dùng nguồn biên khác nhau.
4. **Dân số/ô không đường (E-DQ7e/f, E-DQ8b)**: Giang = UN-adjusted raster + `reallocate_roadless.py` + `reconcile_dasymetric.py` (VNSDI); Kỳ = `settlement.py` mặt nạ định cư (kèm test_settlement.py). Đụng trực tiếp cách tính lớp cầu.
5. **Export**: `export_supply.py` (Giang, kèm test_export_supply.py) vs `export_handoff.py` (Kỳ).

## Phụ lục E — thay đổi CHƯA COMMIT trên working tree (devky)

+45 769 dòng, chưa thuộc nhánh nào. Về bản chất là phần việc mới nhất của Kỳ:

| Cụm | File |
|---|---|
| Notebook pipeline 00–09 | notebooks/00_tong_quan → 09_provenance_opex.ipynb (10 file), explore_data.ipynb, nbtools.py, run_notebooks.py, notebooks/README.md |
| Docs | docs/de-bai-v2.md (đề bài v2, 796 dòng), docs/lineage/2026-07-30-full-lineage.md (1 218 dòng), docs/review/2026-07-29-data-lead-review.md (787 dòng), checklist.txt |
| Test mới | tests/test_admin_join.py, test_coord_quality.py, test_seed_discovery.py, test_settlement.py, test_vn_boundary.py |
| Sửa tiếp file đã commit | .gitignore, Makefile, docs/README.md, docs/known-issues.md, docs/schema/schema-contract.md, tests/test_covered0.py, test_f7_f12_integrity.py, test_f8_f9_f13_f14_f16.py, test_timeseries_integrity.py |

⚠ Ràng buộc "không đụng devky/review-dataset" nghĩa là không thể commit phần này vào devky. Cách xử lý (đưa vào integrate/final hay bỏ ngoài) là câu hỏi Bước 3.

---

*Bước 2 (đánh giá + quyết định từng mục) sẽ được ghi tiếp vào file này.*

---

## Bước 2 — Quyết định từng mục (2026-07-30)

Phương pháp: 12 agent đánh giá song song theo cụm (mỗi agent đọc diff thật hai bên, trả lời: giải quyết gì / ai phụ thuộc / bỏ thì mất gì) + 1 agent phản biện độ phủ và mâu thuẫn chéo. Các hiệu chỉnh của phản biện đã áp vào bảng (đánh dấu `*` = quyết định có điều kiện theo đáp án Bước 3).

Quy ước cột "lấy từ": `giang` / `ky` = lấy nguyên bản một bên; `port-ky` = lấy nội dung Kỳ nhưng viết theo cấu trúc/quy ước Giang; `union` = gộp cả hai; `drop` = không đưa vào; `chờ B3 (Qn)` = dừng hỏi, không tự đoán.

### EVCS canonical (transform + validate + schema contract)

| File | Lấy từ | Lý do |
|---|---|---|
| src/ev_siting/data/evcs/transform_canonical.py | chờ B3 (Q3+Q5) | Nền Giang + port F7/F12 (kèm phía ghi sha256 ở match_official) là phần không tranh cãi, nhưng hai bên xuất CÙNG TÊN cột coord_src/coord_resolved/coord_fix_dist_m và cờ COORD_PLACEHOLDER với nghĩa + value domain KHÁC nhau, và cùng cột current_type với chính sách điền khác nhau (tier-fallback 25 kW vs UNKNOWN) → tiêu chí 5 bắt buộc hỏi, không tự đoán. |
| src/ev_siting/data/evcs/validate.py | union | Hai bên sửa các vùng dòng không giao nhau, đều đúng về dữ liệu → gộp: nền Giang (khối E-DQ4) + WARN→CRIT và xoá biến chết của Kỳ; phần reflow import port out-of-band để diff phẫu thuật. |

### Features (candidates, covered0)

| File | Lấy từ | Lý do |
|---|---|---|
| src/ev_siting/features/build_candidates.py | chờ B3 (Q2+Q3+Q8) | Hướng đúng là nền Giang + port 4 mảnh Kỳ (in_vn fail-closed, VN-mask tâm T4, guard pop_unsupported có điều kiện cột, penalty_flags), nhưng hai bên đặt GIÁ TRỊ KHÁC NHAU cho cùng chính sách lọc toạ độ bẩn T0 và định nghĩa cột output khác nhau — theo tiêu chí 5 phải hỏi trước, không tự đoán. |
| src/ev_siting/features/build_covered0.py | union | Hai fix bổ khuyết cho nhau và Giang tự tuyên bố hướng của Kỳ là điều phải sửa — port _baseline_mask/_operational_only_mask + covered0_operational của Kỳ vào cấu trúc file Giang, giữ _capacity_accounting và cột tài sản của Giang trong _OUT_COLS/geojson; tập cờ toạ độ bẩn theo đáp án Q1. |
| src/ev_siting/features/paths.py | ky* | Lấy Kỳ CÓ ĐIỀU KIỆN: nội dung DIRTY_COORD_FLAGS/COORD_LOW_TRUST chốt theo đáp án Q3 — nếu Q3=chỉ-Giang thì gỡ COORD_LOW_TRUST khỏi paths + PRODUCER_FLAGS test_covered0 để tránh test đỏ giả. |
| tests/test_candidates.py | ky | Diff thuần cosmetic, lấy bản Kỳ để khỏi tạo conflict vô nghĩa khi port các test khác của Kỳ (tiêu chí 4: không bỏ test bên nào). |
| tests/test_covered0.py | ky* | Giữ test Kỳ (ghost-flag check có giá trị); danh sách PRODUCER_FLAGS chỉnh theo đáp án Q3. |

### WorldPop / lớp cầu

| File | Lấy từ | Lý do |
|---|---|---|
| src/ev_siting/data/worldpop/build_demand_h3.py | chờ B3 (Q6) | Hai bên định nghĩa schema demand_h3 khác nhau ở 3 điểm không tự quyết được: bộ cột (Giang xóa n_poi/n_parking/road_len_mt_m mà tests+notebooks WT của Kỳ còn đọc), ngữ nghĩa ô thiếu (NaN+cờ vs fillna(0)), và cột neo xếp hạng — đúng cả 3 điều kiện bắt buộc ask-user. |
| src/ev_siting/data/worldpop/worldpop_pop.py | union | Hai tính năng trực giao và cùng đúng: cấu trúc Giang (UNadj + cổng QA) làm nền, port cơ chế vintage + guard tải của Kỳ vào theo quy ước Giang; riêng nguồn 2020 lấy UNadj vì Giang đã chứng minh thứ hạng bất biến từng bit nên không phá gì của Kỳ. |
| src/ev_siting/data/worldpop/paths.py | union | Không đụng độ giá trị cùng tên nào (POP_TIF 2020 nghiêng về UNadj theo bằng chứng E-DQ7e, phần 2025 của Kỳ là khóa mới), thuần cộng gộp — lấy file Giang làm nền rồi thêm khối POP_SOURCES/resolve_tif của Kỳ. |
| src/ev_siting/data/worldpop/settlement.py | port-ky | Thuần cộng thêm (không sửa pop) nên tương thích với pop_adj của Giang; port nguyên module vào cấu trúc Giang, đổi import vn_boundary sang osm/vn_boundary, gỡ vòng settlement.main() tự gọi build_demand_h3.run() bằng thứ tự Makefile demand → settlement. |
| tests/test_settlement.py | union | Tiêu chí 4: test gộp cả hai bên, không bỏ; chỉ cần sửa test_gapfill nếu user chốt schema demand_h3 không mang pop_unsupported trực tiếp (đổi sang đọc SETTLEMENT_H3). |
| src/ev_siting/data/worldpop/reconcile_dasymetric.py | giang | Kỳ không có bản đối trọng — settlement chỉ gắn cờ và lý do 'không có nguồn thẩm quyền để sửa' của Kỳ bị vô hiệu chính bởi VNSDI DANSO mà module này mang vào; hai lớp bổ trợ nhau (cờ để chẩn đoán, 7f để sửa). |
| src/ev_siting/data/worldpop/reallocate_roadless.py | giang | Không có đối trọng phía Kỳ (pop_2025/cờ phủ xử lý chiều ngược lại — có đường không dân), phương pháp có trọng tài độc lập và cổng FAIL được; giữ nguyên của Giang. |
| src/ev_siting/data/vnsdi/fetch_communes.py | giang | Kỳ không có gì tương đương (vinfast_official không phải nguồn độc lập, và không liên quan dân số); module tự trọn gói, không va chạm tên với phía Kỳ. |

### OSM (H3, POI/road semantics)

| File | Lấy từ | Lý do |
|---|---|---|
| src/ev_siting/data/osm/build_osm_h3.py | chờ B3 (Q2) | Hai bên định nghĩa NỘI DUNG artifact POI_POINTS khác nhau (chỉ-VN vs toàn-bộ+cờ) và một bên xóa dòng bên kia dựa vào — đúng tiêu chí 5, không tự quyết. |
| src/ev_siting/data/osm/overpass_poi.py | port-ky | Lấy file Giang làm nền (docstring E-DQ7c) và ghép nguyên văn hunk _post của Kỳ — hai hunk không giao nhau, port sạch. |
| src/ev_siting/data/osm/paths.py | giang | Giang là siêu tập; hằng POI_OUTSIDE_VN thêm sau tuỳ câu trả lời B3 của build_osm_h3, không cần hỏi riêng. |
| src/ev_siting/data/osm/roads_pbf.py | port-ky | Thân file lấy Giang (đúng hơn về phương pháp, sửa double-count), chỉ port guard tải-thiếu của Kỳ vào download_pbf; import reorder của Kỳ bỏ. |
| src/ev_siting/data/osm/validate.py | giang | Cùng đúng về ý (kiểm đa giác) nhưng Giang là siêu tập nghiêm ngặt hơn với các ngưỡng khai báo rõ (MAJOR_LANE_OBS_MIN=0.40, SUPPLY_NO_ACCESS 1%/2%, APT_LEVELS_OBS_MIN=0.25) mà Kỳ không có bản đối chọi. |
| src/ev_siting/data/osm/poi_semantics.py | chờ B3 (Q6) | File chắc chắn vào từ Giang (đúng hơn về phương pháp, có số đo chứng minh), nhưng nó xóa cột (n_poi/n_parking, kéo theo road_len_mt_m bên road_semantics) mà Kỳ còn dùng ở contract/test/notebook — tiêu chí 5 bắt hỏi. |
| src/ev_siting/data/osm/road_semantics.py | giang | Kỳ không có bản đối chọi; đúng hơn về phương pháp và là nền của chuỗi hạ nguồn — số phận cột cũ đã nằm trong câu hỏi B3 chung. |
| src/ev_siting/data/osm/access_tiers.py | giang | Không trùng vai trò với gì bên Kỳ trong cụm này; lưu ý tích hợp chéo với fix settlement-mask của Kỳ (tests/test_settlement.py, cụm WorldPop) vì cả hai cùng trả lời 'dân ở ô không đường thì tính thế nào' — xem notes. |
| src/ev_siting/data/osm/poi_recall.py | giang | Bổ sung thuần Giang, không xung đột; rủi ro duy nhất là hợp đồng cột với canonical stations sau khi merge cụm EVCS — ghi ở notes. |
| tests/test_poi_semantics.py + tests/test_road_semantics.py + tests/test_access_tiers.py | union | Tiêu chí 4: gộp test cả hai bên, không có va chạm tên file. |
| tests/test_vn_boundary.py (Kỳ, chưa commit) | union | Tiêu chí 4 giữ test Kỳ, nhưng port phải viết lại 2 test theo kết quả B3: test_aggregate_counts_only_rows_it_is_given viết lại theo hợp đồng poi_layers/aggregate của Giang (nơi lọc chuyển từ run() sang poi_layers), và test_poi_points_artifact_has_no_foreign_rows đổi assert theo chính sách POI_POINTS được chọn; import boundary đổi theo câu trả lời về module ranh giới. |
| src/ev_siting/vn_boundary.py (Kỳ) vs src/ev_siting/data/osm/vn_boundary.py (Giang) | chờ B3 (Q1) | Hai bên đặt cùng một 'tham số' (nguồn sự thật ranh giới lãnh thổ) với giá trị khác nhau, và mỗi bên có consumer riêng đang sống — tiêu chí 5. |

### Landuse / buildable

| File | Lấy từ | Lý do |
|---|---|---|
| src/ev_siting/data/landuse/build_buildable_h3.py | chờ B3 (Q7) | Hai bên định nghĩa cột buildable + schema output + tham số phạt khác nhau về bản chất (tiêu chí 5) — không được tự đoán; nhưng hai cải tiến của Kỳ (scale 50km, gate F14) trực giao và port được lên nền Giang bất kể câu trả lời. |
| src/ev_siting/data/landuse/osm_exclusion.py | giang | Giang sửa bug tái lập thực; delta của Kỳ thuần phong cách nên theo tiêu chí 1 lấy Giang nguyên vẹn. |
| src/ev_siting/data/landuse/paths.py | port-ky | Port SUBSTATION_PENALTY_SCALE_M + MAX_POP_NO_ROAD_FRAC lên paths.py bản Giang (đúng quy ước hằng-ở-paths của Giang); NOT_BUILT_PENALTY/NO_ROAD_PENALTY chỉ port nếu câu (a) của B3 chọn phương án Kỳ. |
| src/ev_siting/data/landuse/worldcover.py | drop | Diff thuần định dạng, giữ bản nền để diff hợp nhất sạch. |
| tests/test_landuse.py | drop | Không có nội dung test mới để union — chỉ style, giữ bản nền. |
| src/ev_siting/data/landuse/__init__.py | giang | Kỳ không đụng file này và delta khớp với nền Giang; nếu B3 chọn ngữ nghĩa Kỳ cho buildable thì sửa lại docstring tương ứng khi port. |

### Va chạm: biên giới VN

| File | Lấy từ | Lý do |
|---|---|---|
| src/ev_siting/data/osm/vn_boundary.py | chờ B3 (Q1) | Hai bên dùng NGUỒN ranh giới khác nhau (OSM adm2 từ PBF freeze, có lãnh hải vs union 34 tỉnh vn_admin adm6, chỉ đất) và định nghĩa SCHEMA khác nhau (cell_state/frac_in_vn vs lọc nhị phân) — đúng hai điều kiện bắt buộc ask-user, kết quả clip khác nhau về phương pháp lẫn nguồn. |
| src/ev_siting/vn_boundary.py | chờ B3 (Q1) | Nửa còn lại của cùng xung đột nguồn/schema ở trên — nhưng dù B3 chọn nguồn nào, PHẢI port sang bản hợp nhất: (1) clip điểm trong build_candidates, (2) tách/đánh dấu POI ngoài VN sao cho khớp test fail-closed, (3) cảnh báo fallback ngoài repo. |
| src/ev_siting/aoi.py | drop | Khác biệt whitespace thuần tuý, lấy nguyên trạng file trên nền Giang là xong. |
| tests/test_vn_boundary.py | union | Tiêu chí 4: gộp test cả hai bên; các case điểm + chiều vị từ port được sang BẤT KỲ bản boundary nào, riêng 2 test (admin_dir chung, POI-file-sạch) phụ thuộc kết quả B3 ở trên nên phải sửa theo lựa chọn thay vì xoá. |

### Va chạm: chất lượng tọa độ E-DQ1

| File | Lấy từ | Lý do |
|---|---|---|
| src/ev_siting/data/evcs/fix_coords.py | chờ B3 (Q3) | Hai bên đặt ngưỡng khác giá trị (stack>=5 + 100km vs >=2/5 tín hiệu) và cùng tên cột coord_src nhưng enum khác nhau, cho tập loại trừ khác nhau trên cùng dữ liệu (54 vs ~171 trạm; supply 18.999 vs 18.889) — tiêu chí 5 cấm tự đoán. |
| src/ev_siting/data/evcs/coord_quality.py | chờ B3 (Q3) | Cùng va chạm ngưỡng/enum/tập-loại-trừ như fix_coords (một câu hỏi B3 quyết cả hai file); nếu user chọn hybrid thì port theo cấu trúc Giang: đọc output enrich_stations (admin_verdict) thay cho STATION_ADMIN của admin_join vì 2/5 tín hiệu (outside_all_provinces/communes) trùng vai E-DQ3 của Giang. |
| tests/test_coord_quality.py | union | Tiêu chí 4: gộp test cả hai bên — nhưng file này chỉ chạy được nếu B3 chọn (2) hoặc (3) vì nó import coord_quality; nếu user chọn (1) chỉ-Giang thì test chết theo module và cần ghi nhận mất mát này trong biên bản. |

### Va chạm: enrich hành chính E-DQ3

| File | Lấy từ | Lý do |
|---|---|---|
| src/ev_siting/data/admin/boundaries.py | giang | Kỳ không có counterpart cho phía lưới và phép gán điểm của Giang đúng hơn về phương pháp (khoá MAXA, dung sai đo được, không đoán) — tiêu chí 1. |
| src/ev_siting/data/admin/paths.py | giang | Là hạ tầng của package nền; không va chạm trực tiếp file nào của Kỳ (Kỳ khai hằng số ngay trong admin_join.py). |
| src/ev_siting/data/admin/enrich_stations.py | chờ B3 (Q4) | Cùng vai trò với admin_join.py của Kỳ nhưng HAI BÊN ĐỊNH NGHĨA CÙNG CỘT KHÁC GIÁ TRỊ — tiêu chí 5 bắt buộc hỏi; khuyến nghị nghiêng Giang (nguồn có mã, 1 niên đại, in-repo, không dính ODbL). |
| src/ev_siting/data/admin/enrich_grid.py | giang | Không có đối thủ phía Kỳ và giải đúng bài toán kế toán khối lượng — tiêu chí 1. |
| src/ev_siting/data/admin/__init__.py | giang | Đi kèm package nền, không va chạm gì. |
| src/ev_siting/data/evcs/admin_join.py | chờ B3 (Q4) | Bị enrich_stations của Giang thay thế về chức năng nhưng downstream Kỳ còn bám vào output của nó — phải hỏi trước khi drop. |
| tests/test_admin.py | union | Tiêu chí 4: test gộp cả hai bên; test này theo package được chọn làm nền. |
| tests/test_admin_join.py | port-ky | Tiêu chí 4 không bỏ test bên nào, nhưng test này bám API của admin_join — port các ý (chiều vị từ, trục toạ độ, fail-loud thiếu lớp, không fan-out) sang assign_points/load_communes theo cấu trúc + tên của Giang; bỏ phần đặc thù lớp OSM (lọc LINESTRING, SIDE_COLS license-scope) nếu admin_join bị drop. |

### Crawler EVCS (gần như chỉ Kỳ)

| File | Lấy từ | Lý do |
|---|---|---|
| src/ev_siting/data/evcs/evcs_enumerate.py | ky | Giang không đụng file này; bản Kỳ sửa 3 bug dữ liệu có bằng chứng đo đạc, chỉ cần port kèm vinfast_official/paths.py. |
| src/ev_siting/data/evcs/evcs_scrape.py | ky | Bản merge-base/Giang không còn chạy được với giao thức evcs.vn hiện hành; bản Kỳ là bản duy nhất hoạt động. |
| src/ev_siting/data/evcs/session.py | ky | Thành phần bắt buộc của crawler mới, Giang không có gì trùng vai trò. |
| src/ev_siting/data/evcs/evcs_probe.py | ky | Vô hại, lấy bản Kỳ để file khớp nguyên trạng nhánh Kỳ, đỡ một hunk diff thủ công. |
| src/ev_siting/data/evcs/build_master_evcs.py | chờ B3 (Q5) | Đúng tiêu chí 5: hai bên định nghĩa ngữ nghĩa cột current_type/connector_types khác nhau và Kỳ xóa cơ chế Giang còn dùng — không được tự đoán. |
| src/ev_siting/data/evcs/merge_catalog.py | ky | Giang không đụng; fix đóng đúng lỗ hổng đã làm mồ côi 298 trạm, phải port nguyên khối cùng paths.py. |
| src/ev_siting/data/evcs/dedup_crosssource.py | ky | Kỳ đúng hơn về phương pháp với bằng chứng định lượng; Giang giữ nguyên bản merge-base lỗi nên không có tham số cạnh tranh. |
| src/ev_siting/data/evcs/split_timeseries.py | ky | Giang không đụng; fix mất-dữ-liệu có thật, tương thích ngược qua default args. |
| src/ev_siting/data/evcs/paths.py | ky | Không phá symbol nào của nền Giang, là mắt xích bắt buộc của cả cụm crawler Kỳ; chỉ cần ghi rõ default TS_DIR mới vào docs/Makefile khi tích hợp. |
| src/ev_siting/data/evcs/run_pipeline.sh | ky | Nhất quán nguyên khối với evcs_scrape/split_timeseries/paths mới; không đụng wiring riêng của Giang trong Makefile. |
| src/ev_siting/data/evcs/compare_runs.py | ky | Công cụ thuần bổ sung, zero rủi ro với nền Giang. |
| tests/test_seed_discovery.py | union | Tiêu chí 4: gộp test cả hai bên; Giang không có test trùng vai trò. |
| tests/test_timeseries_integrity.py | union | Tiêu chí 4: union; nội dung chỉ test module Kỳ nên không va chạm test Giang. |
| tests/test_f7_f12_integrity.py | union | Tiêu chí 4: union; phụ thuộc xuyên cụm (matcher + transform) cần port đồng bộ. |
| tests/test_f8_f9_f13_f14_f16.py | union | Tiêu chí 4: union, nhưng số phận của test_f13 buộc phải theo kết quả câu hỏi ask-user về current_type — hai thứ này phải quyết cùng nhau. |

### Export + VinFast official + provenance

| File | Lấy từ | Lý do |
|---|---|---|
| src/ev_siting/data/evcs/export_supply.py | giang | File chỉ có bên Giang, vai trò KHÁC export_handoff (CSV cung sạch cho MCLP/QGIS vs bundle bàn giao liên-repo) — không va chạm, giữ nguyên trên nền Giang. |
| tests/test_export_supply.py | giang | Tiêu chí 4: union test — chỉ Giang có, giữ nguyên. |
| src/ev_siting/data/evcs/export_handoff.py | port-ky | Giữ nhưng port lên nền Giang KÈM sửa FX-05 mà chính lineage của Kỳ đã chỉ ra (bundle đóng gói LOAD_TS = tầng 168h trong khi canonical dựng từ 720h — cần tham số hoá tier + cổng assert khớp TS_DIR) và trỏ lại CATALOG_CSV theo paths hợp nhất; chưa có test riêng, nên viết khi port. |
| src/ev_siting/data/vinfast_official/fetch_locators.py | ky | Giang không đụng file này; toàn bộ thay đổi của Kỳ là sửa đúng đắn cho nguồn sống, khớp giao thức evcs.vn/registry 29/07 đã ghi nhận. |
| src/ev_siting/data/vinfast_official/paths.py | ky | Thuần cộng thêm, Giang không có bản đối ứng; khi port lưu ý R-8 trong lineage (latest_registry chọn generation cao nhất trên đĩa — nên thêm tham số ghim generation để seed tất định). |
| src/ev_siting/data/vinfast_official/match_official.py | ky | Ngữ nghĩa verify chặt chẽ hơn hẳn và Giang không sửa matcher; port cùng một bước với transform_canonical của Kỳ vì hai bên khớp cột/hash với nhau. |
| src/ev_siting/data/provenance/freeze_snapshot.py | ky | Cộng thêm an toàn mà Giang không có, không va chạm (Giang không sửa file này); chưa có test riêng — nên thêm test archive-trước-khi-đè khi port. |
| src/ev_siting/data/provenance/manifest.py | union* | Thu hẹp sau phản biện: 2020=UN-adjusted chốt theo bằng chứng E-DQ7e (Spearman=1, tỉ số hằng 0,979344 — không phá số Kỳ ngoài scale); pop_2025 giữ raster unadjusted R2024B Kỳ đã tải cho sensitivity (không có xung đột thật — Giang không có raster 2025); manifest khai đủ 3 raster làm member. |
| data/raw/MANIFEST.json | union | Cùng tồn tại được nhờ quy ước archive MANIFEST-<id>.json: giữ bản Kỳ 2026-07-29 làm hiện hành, lưu bản Giang thành file archive (vd MANIFEST-2026-07-20-revised.json — KHÔNG đè bản gốc vì hai nội dung khác nhau cùng claim id 2026-07-20), rồi sau khi hợp nhất manifest.py + trả lời B3 worldpop thì chạy lại `make freeze` snapshot 2026-07-30 làm bản chân lý duy nhất. |
| data/raw/MANIFEST-2026-07-20.json | ky | File chỉ Kỳ có, chi phí bằng 0, là điều kiện để quy ước snapshot-versioning có nghĩa — giữ nguyên. |

### Root / meta

| File | Lấy từ | Lý do |
|---|---|---|
| Makefile | union* | Union target-by-target; riêng recipe `canonical` (prereq match-official giữ; hậu bước admin-join/coord-quality) CHỜ đáp án Q3/Q4 — không chốt trước. |
| README.md | union | Hai bản không mâu thuẫn nội dung mà bổ sung nhau: lấy thân bài Kỳ (vault + quickstart + trạng thái) rồi vá cây thư mục theo Giang (config/db/, app/, docs/issues/, docs/reports/) + cập nhật mục notebooks/ theo suite 00-09 mới; dòng 66 `.github/workflows/ci.yml` đang nói dối (Kỳ đã xóa CI) — sửa theo kết quả câu hỏi B3 về CI. |
| .claude/settings.json | ky (xóa) | QUYẾT sau phản biện: file committed auto-allow git push/commit/pkill VÀ chứa token VNSDI còn sống trong 4 URL curl → xóa khỏi repo, gitignore .claude/; PHẢI báo Giang rotate token + chuyển allowlist sang settings.local.json. Giữ file có token sống không phải phương án hợp lệ. |
| db/{migrations,seeds}/.gitkeep (Giang: config/db/) | giang | Docs nền (Giang) vẫn tham chiếu như hạng mục roadmap mở, giữ .gitkeep rỗng không tốn gì — lấy bản Giang (config/db/); chỉ xóa khi tầng PostGIS được descope chính thức có Giang xác nhận. |
| pyproject.toml | ky | Chỉ Kỳ sửa, không xung đột; bản Kỳ đúng chuẩn và phủ đủ import của toàn bộ cây src Giang (đã kiểm bằng grep, không đoán). |
| .gitignore | ky | Chỉ Kỳ + WT sửa, Giang không đụng; lấy bản WT (mới nhất, chứa fix F10) — lưu ý dòng `.claude` phụ thuộc câu trả lời B3 về settings.json, và khuyến nghị BỎ dòng `uv.lock` (commit lock để uv sync tái lập đúng phiên bản — cùng tinh thần E-DQ10), không chặn merge. |
| src/ev_siting/data/opex_electricity.py | ky | Chỉ Kỳ sửa, 1 dòng, Giang không đụng file — lấy thẳng. |
| LICENSE (Kỳ xóa) | ky | Không đáng ask-user: nội dung chỉ là placeholder không grant gì, repo là vault nội bộ nên không-license = all-rights-reserved đúng hiện trạng; ghi chú follow-up: khi nào định public code thì mới cần quyết license thật (việc mới, không phải khôi phục file cũ). |
| .github/workflows/ci.yml (Kỳ xóa) | chờ B3 (Q9) | Ý định tự mâu thuẫn (viết CI thật → xóa ngay, nhưng README + notebooks-check vẫn giả định có CI) — không tự đoán được đây là quyết định hay tình thế. |
| config/params.yaml (Kỳ xóa) | ky | Không code nào đọc, hai nhánh cùng chốt R=3.0 trong code — xóa là đúng; kèm việc bắt buộc cho cụm docs: sửa README.md:33 + viết lại lập luận e-dq8c §2 theo R=3.0km (với R=3km, ô roadless VẪN có thể được trạm lân cận phủ — kết luận 'không phủ được theo cấu tạo' hiện dựa trên 500m không còn đứng vững). |
| app/.gitkeep (Kỳ xóa) | giang | Cùng logic config/db/: placeholder rỗng của hạng mục roadmap còn mở do Giang phụ trách, giữ không tốn gì — không để một bên lặng lẽ xóa scope của bên kia; không cần ask-user vì giữ là zero-cost và đảo được. |
| notebooks/01-giang-eda-stations.ipynb + 02-ky-mclp-toy-example.ipynb (Kỳ xóa) | ky | Stub rỗng bị thay bằng suite notebook chạy được có hạ tầng riêng — hiển nhiên an toàn; README hợp nhất cập nhật mục notebooks/ theo suite mới (đã gộp vào quyết định README). |

### Docs

| File | Lấy từ | Lý do |
|---|---|---|
| docs/known-issues.md | union* | Cấu trúc Giang (register trỏ docs/issues/**) thắng; port mục F/G + phần working tree của Kỳ vào cấu trúc đó. QUYẾT sau phản biện (Q12): cặp trùng lớp (E-DQ11↔E-DQ7a, P10/E-DQ12↔E-DQ7e/f, L4↔Q1) gộp vào file e-dq* hiện có, ghi rõ "hai lần fix độc lập, phương án nào thắng, vì sao" — một sự thật mỗi lớp, cross-link ID F/L để 6 file test đặt tên theo F/L vẫn truy vết được. |
| docs/schema/schema-contract.md | union-sau-B3 | Một quyết định duy nhất (gộp 2 cụm): cấu trúc union cả hai; 3 bảng stations/demand_h3/candidate_sites chỉ viết MỘT enum/tập cột theo đáp án Q3/Q5/Q6/Q8 — không giữ song song hai enum trùng tên khác nghĩa. |
| docs/data-layer/candidate-sites.md | chờ B3 (Q7+Q8) | Hai bên đặt CÙNG các ngưỡng lọc buildable với giá trị/chính sách khác nhau (loại cứng vs phạt +0,35/+0,25 vs ISOLATED-only) → cấm tự đoán theo tiêu chí 5; riêng dòng cờ toạ độ bẩn thì Kỳ đúng hơn bất kể kết quả (F4 đã chứng minh cờ Giang ghi là cờ chết). |
| docs/data-layer/overview.md | union | Nền Giang (viết lại là bản đúng cấu trúc), port 3 dòng sửa của Kỳ vào đúng ô bảng — không xung đột vì chúng mô tả các phần pipeline khác nhau; riêng con số lưới/tập cung phải chờ kết quả 2 câu ask-user ở schema-contract rồi đo lại. |
| docs/schema/data-dictionary.md | union | Hai thay đổi trực giao, gộp thẳng; câu chữ 'hard exclusions are absent' trong bảng Kỳ phải sửa lại theo kết quả câu hỏi buildable ở candidate-sites.md. |
| docs/sources/evcs.md | union | Nội dung Kỳ là bản đúng của pipeline sau fix, cộng path-fix của Giang — union một chiều gần như lấy Kỳ; enum current_type UNKNOWN phải khớp câu trả lời schema-contract. |
| docs/README.md | union | Nền Giang, chèn dòng de-bai-v2 + chú thích của Kỳ, và thêm mục cho docs/review/, docs/lineage/, notebooks/README.md khi port các file đó. |
| docs/issues/** (27 file + issues/README.md) | giang | Chỉ Giang có, là nền cấu trúc; khi port nhóm F/G của Kỳ thì tạo THÊM thư mục f-pipeline-integrity/ + g-data-lead-review/ theo đúng quy ước file này (union bổ sung, không sửa 27 file hiện có). |
| docs/sources/osm.md | giang | Chỉ Giang sửa, nội dung đúng hơn về phương pháp; câu 'n_poi khai tử' phụ thuộc câu trả lời demand_h3 ở schema-contract (nếu user giữ schema Kỳ thì phải nới lại). |
| docs/sources/worldpop.md | giang | Chỉ Giang sửa; NHƯNG nội dung mâu thuẫn chính sách pop với P10 của Kỳ (UNadj-mặc-định vs 2020+pop_2025) — file này phải viết lại theo câu trả lời ask-user ở known-issues/schema-contract, nếu chọn hợp cả ba cột thì bổ sung mục pop_2025 từ bản Kỳ. |
| docs/data-layer/dataset-inventory.md | giang | Chỉ Giang có; giữ nguyên cấu trúc nhưng TOÀN BỘ con số phải đo lại sau khi hợp code (đo trên artefact nhánh Giang, sẽ lệch với pipeline hợp nhất — chính file tuyên bố nguyên tắc 'đo trực tiếp từ file'). |
| docs/problem-analysis.md | giang | Lấy bản Giang, thêm banner 'định nghĩa bài toán + DoD coverage đã bị thay bởi de-bai-v2.md (29/07)' đúng như chú thích Kỳ viết trong README. |
| docs/schema/schema-review.md | giang | Chỉ Giang sửa, không xung đột. |
| docs/reports/evcs-data-quality.md | giang | Chỉ Giang có; con số trong báo cáo cần đối chiếu lại sau merge (cùng lý do dataset-inventory). |
| docs/sprint-reviews/data-pipeline-review-2026-07-24.md + -28.md | ky | Chỉ Kỳ có, thuần bổ sung, đúng vị trí thư mục theo cả hai cấu trúc — giữ nguyên. |
| docs/de-bai-v2.md | ky | Chỉ Kỳ có (working tree), là văn bản thẩm quyền cấp dự án — giữ nguyên đường dẫn docs/ gốc, thêm vào mục lục README. |
| docs/review/2026-07-29-data-lead-review.md | ky | Chỉ Kỳ có; giữ nguyên (thư mục docs/review/ mới — thêm vào mục lục README khi hợp nhất). |
| docs/lineage/2026-07-30-full-lineage.md | ky | Chỉ Kỳ có; giữ như tài liệu audit CÓ NIÊN ĐẠI (đo trên nhánh Kỳ trước merge) — sau hợp nhất không sửa số bên trong, chỉ ghi chú đầu file rằng lineage phản ánh trạng thái 30/07 nhánh Kỳ. |
| checklist.txt | port-ky | Nội dung giữ nhưng theo quy ước cấu trúc Giang thì file nháp không nằm ở gốc repo — port vào docs/review/ (vd docs/review/2026-07-30-review-plan.md), gốc repo sạch. |
| notebooks/README.md | ky | Thuộc cụm notebooks (Kỳ-only); giữ nguyên, thêm dòng vào docs/README.md; nội dung bảng nhắc tới module coord_quality/admin_join phía Kỳ nên phải cập nhật tên module nếu cụm code chọn bản Giang. |

### Bổ sung sau phản biện (file bị sót)

| File | Lấy từ | Lý do |
|---|---|---|
| src/ev_siting/data/evcs/resolve_config.py | giang | Resolver ASSET/LIVE E-DQ4, 452 dòng, không có đối trọng phía Kỳ; bước C so live-vs-asset sẽ chỉnh theo đáp án Q5. |
| tests/test_config_semantics.py | union | Test của resolve_config — giữ theo tiêu chí union test. |
| src/ev_siting/data/osm/__init__.py | giang | Docstring 10 cột POI/road E-DQ7b/c; sửa lại nếu đáp án Q6 giữ cột cũ. |
| src/ev_siting/data/vnsdi/{__init__,paths}.py | giang | Đi nguyên gói vnsdi cùng fetch_communes.py. |
| notebooks/00–09, explore_data.ipynb, nbtools.py, run_notebooks.py | chờ B3 (Q13) | Suite chưa commit, phụ thuộc dày module/cột phía Kỳ — số phận quyết ở Q13, không tự đoán. |
| docs/review/2026-07-30-branch-diff-map.md | giữ (file này) | Meta của quá trình hợp nhất, commit vào integrate/final. |

### Quyết định đã tự chốt ở mức B2 (không thuộc 3 nhóm bắt buộc hỏi)

- **Raster 2025**: giữ bản unadjusted R2024B Kỳ đã tải làm sensitivity (Giang không có raster 2025 → không có xung đột hai-bên); 2020 = UN-adjusted theo bằng chứng E-DQ7e.
- **`.claude/settings.json`**: xóa khỏi repo (chứa token VNSDI sống + auto-allow git push/pkill). Rủi ro bảo mật, không phải lựa chọn phong cách. Cần báo Giang rotate token.
- **Register known-issues**: cấu trúc docs/issues/** của Giang thắng; mục F/G của Kỳ port vào, cặp trùng lớp gộp một-sự-thật-mỗi-lớp với cross-link ID F/L.

### Mâu thuẫn chéo phản biện đã phát hiện (đã xử lý trong bảng)

- Makefile canonical chain: root-meta chốt 'bản WT Kỳ' (canonical → admin-join → coord-quality) trong khi cụm canonical + admin + coord-quality đều khuyến nghị nền Giang enrich inline và thay thế hai hậu bước đó — quyết ngược nhau về cùng một recipe; phải để recipe này chờ đáp án Q-coord/Q-admin.
- schema-contract.md có HAI quyết định từ hai cụm (union vs ask-user) — cần gộp về một dòng sở hữu duy nhất.
- manifest.py POP_TIF: cụm worldpop đã tự quyết 2020=UNadj (union, có bằng chứng thứ hạng bất biến) trong khi cụm export-vinfast đưa đúng điểm đó vào ask-user — một bên tự quyết cái bên kia coi là phải hỏi; đề xuất thu hẹp câu hỏi còn phần vintage 2025.
- COORD_LOW_TRUST xuyên cụm: features (paths.py 'ky', test_covered0 'ky') và worldpop/canonical đều tiêu thụ cờ này, nhưng producer duy nhất (coord_quality.py) đang là ask-user ở cụm coord — nếu đáp án là chỉ-Giang thì 3 quyết định 'ky' kia phải sửa theo, hiện chưa cụm nào ghi điều kiện đó vào decision chính (chỉ nằm trong notes).
- Chính sách POI_POINTS: cụm OSM khuyến nghị flag-and-keep (Giang), cụm vn-boundary khuyến nghị port fail-closed tách file (Kỳ) — hai khuyến nghị mặc định ngược nhau cho cùng câu hỏi.
- Câu hỏi ranh giới VN bị hỏi 4 lần với 4 bộ phương án hơi khác nhau (osm, vn-boundary, admin câu (b), docs câu (1)) — nếu trả lời rời rạc có thể tự mâu thuẫn (vd chọn PBF adm2 cho lưới nhưng giữ test admin_dir-shared); phải gộp thành một câu duy nhất kèm hệ quả cho test_admin_dir_shared_with_admin_join.
- Câu hỏi current_type bị hỏi 3 lần (canonical Q2, crawler build_master_evcs, crawler test_f8_f9) — cùng một quyết định, đã xác nhận bằng code là xung đột thật (Giang transform_canonical.py:206 fallback AC/DC 25kW vs test WT assert UNKNOWN); phải trả lời một lần và cascade sang resolve_config bước C + test_f13 + build_master label.
- Câu hỏi demand_h3 schema bị hỏi 3 lần (worldpop build_demand_h3, osm poi_semantics khai tử n_poi/road_len_mt_m, docs schema-contract) — một đáp án, lan sang tests test_f8_f9/test_vn_boundary + notebooks 01/02/08 + build_candidates WT.
- Câu hỏi buildable hard-vs-soft bị hỏi 2 lần (landuse build_buildable_h3 câu (a), docs candidate-sites) — một đáp án; hai phần trực giao của Kỳ (scale 50km, gate F14) cả hai cụm đều đồng ý port nên rút khỏi câu hỏi.
- candidate_sites province_code/exclusion_flags bị hỏi 2 lần (features Q2, docs câu (2)) — một đáp án, cần xác minh consumer MCLP bên repo evcs-dataset trước khi trả lời.

*Các câu hỏi Bước 3 đã gộp trùng (11 câu) được đặt trực tiếp cho data lead — đáp án ghi bên dưới.*

---

## Bước 3 — Đáp án của data lead (2026-07-30)

| # | Chủ đề | Đáp án | Hệ quả thực thi |
|---|---|---|---|
| Q1 | Nguồn ranh giới VN | **Giang** — OSM adm2 rel 49915 từ PBF freeze | Giữ `osm/vn_boundary.py`; KHÔNG port `src/ev_siting/vn_boundary.py` + thay đổi `aoi.py` của Kỳ; test một-bản-đồ của Kỳ đổi nghĩa/gỡ; giữ cell_state/frac_in_vn |
| Q2 | POI ngoài VN | **Kỳ** — fail-closed | Port chính sách tách file lên nền semantics Giang: POI_POINTS chỉ chứa in_vn + `osm_poi_outside_vn.parquet` riêng + hằng POI_OUTSIDE_VN vào osm/paths; giữ test fail-closed. Bắt buộc thêm lọc in_vn trong `build_candidates._load_poi` |
| Q3 | Tọa độ E-DQ1 | **Chỉ Giang** | Giữ `fix_coords.py` + gate cứng coord_resolved; KHÔNG port `coord_quality.py`; gỡ COORD_LOW_TRUST khỏi `features/paths.py` + PRODUCER_FLAGS test_covered0; test_coord_quality.py không đưa vào; giữ số supply 18.999 |
| Q4 | Admin E-DQ3 | **Giang** — VNSDI, ghi thẳng canonical | Giữ gói `data/admin/*`; KHÔNG port `admin_join.py`; port Ý ĐỊNH test_admin_join sang API Giang; cell QA notebook "admin null là đúng" hết hiệu lực (notebook không vào — Q13) |
| Q5 | current_type evcs-only | **Giang** — fallback tier 25 kW | Giữ transform_canonical:206; test F13 của Kỳ đổi expectation theo; vẫn lấy rename num_ports→n_charging_snapshot (không consumer nào dùng num_ports) |
| Q6i | Cột demand cũ | **Khai tử + migrate** | Bỏ n_poi/n_parking/road_len_mt_m; migrate test_f8_f9 + test_vn_boundary sang cột semantics mới |
| Q6ii | NaN vs 0 | **Giang** — fillna(0) | Hợp đồng demand_h3 giữ fillna(0); cờ phủ pop_covered/osm_covered của Kỳ không đưa vào |
| Q6iii | Neo dân số | **pop_adj chính; settlement cả hai** | pop_adj neo xếp hạng, pop_2025 sensitivity; settlement/pop_k1 giữ như Kỳ chạy trên pop thô + pop_2025 (không đo lại) |
| Q7 | Buildable | **Giang** — loại cứng NOT_BUILT_UP | buildable ~23%; vẫn port 2 phần trực giao của Kỳ: SUBSTATION_PENALTY_SCALE_M=50km + gate F14 MAX_POP_NO_ROAD_FRAC=0.20 |
| Q8 | Schema candidate_sites | **Giang** (user tự ghi "chọn của Giang") | Giữ province_code + exclusion_flags theo Giang (E-DQ3 nay đổ dữ liệu thật vào province_code; Q7 loại cứng nên exclusion_flags có nội dung); penalty_flags của Kỳ không đưa vào (mất producer sau Q7) |
| Q11 | CI | **Giữ không-CI** | ci.yml không khôi phục; sửa README:66 + chú thích notebooks-check cho docs hết nói dối |
| Q13 | Notebooks WT | **Không đưa vào** | Suite 00–09 + nbtools + run_notebooks + explore_data + notebooks/README.md ở lại working tree Kỳ (bảo toàn qua stash/backup, không commit vào integrate/final); gỡ Makefile targets notebooks/notebooks-check |

Hai quyết định B2 tự chốt (đã ghi ở trên): raster 2025 = unadjusted R2024B của Kỳ; `.claude/settings.json` xóa (token VNSDI sống — cần rotate).

---

## Bước 4 — Thực thi (2026-07-30, nhánh integrate/final)

14 commit từ nền `data/giang` (3a836cc), tổng +7 840/−829 trên 67 file. Xem `git log 3a836cc..integrate/final` — mỗi commit một nhóm logic, message ghi nguồn gốc và mã quyết định B3 tương ứng. Working tree chưa commit của Kỳ bảo toàn tại `stash@{0}` (khôi phục: `git checkout devky/review-dataset && git stash pop`) + patch dự phòng trong scratchpad phiên làm việc.

## Bước 5 — Kiểm chứng

- `uv run pytest`: **158 passed, 3 skipped, 0 failed** (24,7s). Trước khi dựng `make boundary` là 145 passed/16 skipped; sau khi dựng `vn_boundary.parquet` từ PBF freeze, 13 test biên giới chạy thật và pass (kể cả 2 case đảo + trần T0≤4). 3 skip còn lại đều cần `make vnsdi` (crawl + token, không chạy cục bộ được).
- Notebook: không áp dụng — suite notebooks không vào integrate/final (B3-Q13).

### Đã bỏ đi và vì sao

| Bỏ | Vì |
|---|---|
| coord_quality.py + test_coord_quality.py + cờ COORD_LOW_TRUST | B3-Q3 chỉ-Giang; nhánh sửa-theo-official là nhánh chết (0/19.427) |
| admin_join.py + test_admin_join.py nguyên bản | B3-Q4 VNSDI; ý định test port sang tests/test_admin_enrich.py (API Giang) |
| src/ev_siting/vn_boundary.py + sửa aoi.py + test một-bản-đồ | B3-Q1; thiết kế hai-bản-đồ (lãnh thổ adm2 ≠ nhãn admin VNSDI) có chủ đích |
| Cờ pop_covered/osm_covered (hợp đồng NaN) | B3-Q6ii chọn fillna(0) |
| penalty_flags + phạt mềm buildable | B3-Q7/Q8 theo Giang (loại cứng; schema province_code + exclusion_flags) |
| Suite notebooks 00–09 + nbtools + run_notebooks + notebooks/README | B3-Q13 — ở lại stash trên devky |
| .github/workflows/ci.yml | B3-Q11 giữ không-CI; README đã hết tham chiếu |
| .claude/settings.json, LICENSE, config/params.yaml | Xóa theo Kỳ; settings.json chứa TOKEN VNSDI SỐNG |
| Entry vn_admin trong manifest.py (MANIFEST.json vẫn giữ bản ghi) | Module sinh nó bị khai tử theo Q1/Q4; bản ghi giữ làm bằng chứng |
| Hậu bước Makefile admin-join/coord-quality | Enrich chạy inline trong transform_canonical (Giang) |

### Nợ lại

1. **Token VNSDI phải rotate** — đã xóa file trên integrate/final nhưng còn nguyên trong lịch sử `data/giang`; báo Giang chuyển allowlist sang `.claude/settings.local.json`.
2. `make verify-snapshot` FAIL cục bộ: thiếu `data/raw/worldpop/vnm_ppp_2020_UNadj_constrained.tif` + `data/raw/vnsdi/` trên máy này — cần copy raw từ máy Giang, verify rồi re-freeze (`merge_note` trong MANIFEST đã ghi).
3. export_handoff.py chưa có test riêng.
4. 3 test VNSDI đang skip (`make vnsdi`).
5. Pipeline rebuild đầy đủ (osm → demand → settlement → landuse → candidates → covered0) chưa chạy trên nhánh hợp nhất; các con số docs đánh dấu "(cần đo lại sau rebuild)" (buildable 28.075/59.927, penalty substation, Σ pop_2025, gate F14); số cụm settlement sẽ xê dịch nhẹ do lưới nền là clip Giang.
6. Dấu ☑ nhóm F trong register đo trên nhánh Kỳ — tái kiểm khi rebuild.
7. `crawl-validate` giờ FAIL (không chỉ WARN) khi manifest không đối chiếu được — hành vi cố ý (F-fix của Kỳ), lưu ý môi trường chưa freeze.
8. `make export-handoff` fail-fast nếu TS_DIR ≠ tầng 168h và không truyền `TELEMETRY=` — cố ý (FX-05).

---

## Rebuild dữ liệu đầy đủ — 2026-07-30 → 31

Toàn chuỗi dẫn xuất rebuild từ raw trên `integrate/final` (log gate trong `data/interim/**/*_report.json`):

- Raw bổ sung: raster 2020 UNadj (sha256 khớp manifest từng byte), VNSDI crawl tươi (3.321 xã — `commune_pages` trùng hash bản 29/07, số E-DQ7f tái lập chính xác). Registry official fetch mới gen 210.
- Chuỗi: boundary → roads_pbf → osm → worldpop(2 vintage) → reconcile-pop → demand → settlement → landuse-national → **official → match-official → canonical → resolve-config → export-supply** → candidates-national → covered0-national → export-handoff(720h). Hai lệch so thứ tự đề ra, đều do phụ thuộc thật: (1) covered0 fail-fast trên canonical stale (thiếu cột E-DQ4) → canonical dựng trước, candidates/covered0 chạy lại sau; (2) `make official` bị khóa read-only của freeze chặn → mở khóa đúng phạm vi, re-freeze khóa lại.
- Kết quả: mọi QA gate PASS (1 WARN không chặn: `poi_recall_bias_parking_off` 2,44); **pytest 161/161, 0 skip**; `verify-snapshot HASHES=1` PASS trên snapshot mới `2026-07-30` (entry vn_admin tự rớt đúng thiết kế); bundle handoff `evcs_vn_2026-07-30` (19.805 trạm/24.787 connector, telemetry 720h, 1,06 GB).
- Con số chốt (đo từ artefact): master 28.923 · canonical 19.805/24.787 · cung 19.086 + 719 loại = 19.805 · lưới demand 314.934 (INSIDE 311.447/BORDER 3.487) · Σpop_adj 97.083.046 (−0,499%) · Σpop_2025 101,30M · buildable 59.926/314.934 (19,0%) · candidates 16.659 · covered0 18.928/15.552.
- Nợ đã đóng so danh sách B5: raw thiếu ✓ · verify-snapshot ✓ · 3 test VNSDI hết skip ✓ · số docs "(cần đo lại)" ✓ · dấu ☑ nhóm F tái kiểm ✓. Còn lại: test riêng cho export_handoff.py; token VNSDI trong lịch sử data/giang vẫn phải rotate (không phụ thuộc repo này); mirror HF chưa đồng bộ thế hệ mới.

---

## Hoàn thiện dữ liệu — 2026-07-31 (phiên grill với data lead)

Sáu nợ/blocker còn lại được đưa qua grill từng-câu-một; quyết định cuối (mọi mục đều do data lead chốt):

1. **Mirror HF — GIỮ PUBLIC nguyên raw** (bác khuyến nghị private; hỏi lại lần hai vẫn giữ). Register F1 → RISK-ACCEPTED, owner Kỳ, 31/07. Mirror chưa đồng bộ thế hệ 2026-07-30.
2. **Token VNSDI — HẠ MỨC, ĐÓNG.** Cải chính đánh giá B2/B3: xác minh `_fetch_token` cho thấy `tokenChinh` là token public tự xoay phát cho mọi khách vãng lai (referer-bound, không bền) — không phải secret, không cần rotate/rewrite lịch sử. Vệ sinh còn lại: Giang chuyển allowlist sang `settings.local.json`.
3. **Bản tách TS 720h — đo 31/07:** 19.426 file, 38.255.343 dòng, **khớp nguồn từng dòng**; giữ nguyên, không crawl lại.
4. **pop_2025 lệch footprint thế hệ** (đo 31/07: 188.094 ô/11,33M người chỉ có ở R2024B; chiều ngược 417 ô/28,2K = 0,029%): người dùng mở lại Q9 → chốt tải **R2024B-2020** (fact: bản "2025 UN-adjusted" không tồn tại và cũng không sửa được footprint). Kết quả: `worldpop_pop_2020_r24_h3` 303.192 ô, Σ 97.620.404, **giao footprint 100% với lớp 2025** — cặp per-cell hợp lệ; `demand_h3` không đổi schema; vintage `2020_r24` thêm vào POP_SOURCES (+12 dòng code, có producer tái lập).
5. **export_handoff.py — KHÔNG viết test** (quyết định có chủ đích, ghi register; bằng chứng vận hành: bundle 30/07 qua F10/FX-05 thật kể cả nhánh FAIL).
6. **WARN parking bias 2,44 — chấp nhận** (fact: PARKING_OFF là anchor T1, T4 gap-fill đang bù 920 ô, upper-bound 91,05% PASS); docs ghi hệ quả + cấm đọc `n_parking_off` tuyệt đối.

Re-freeze giữ `snapshot_id=2026-07-30` (chỉ thêm member `population_raster_2020_r24`, nguồn cũ không đổi — tránh cascade sang bundle handoff đã đóng).

---

## Bổ sung 2026-08-01 — 2 commit Giang sau phiên chốt 31/07

`data/giang` nhận thêm 2 commit của Giang sau khi `integrate/final` đã "chốt" (10:01 31/07):
`fe3fefc` (14:26, gate `covered0`/admin mapping) và `f19777e` (16:19, gỡ 5 cột LIVE trùng lặp
khỏi `stations` → nguồn chân lý duy nhất là `connectors`, xem `connector_rollup.py`).

Kiểm tra ancestry: `origin/data/giang` = `integrate/final` (87d15b5) + đúng 2 commit này theo
đường thẳng (không rẽ nhánh) — cả hai chỉ sửa tiếp các file đã thuộc về Giang theo quyết định
B3 (Q3/Q5/Q7/Q8), không đụng vùng nào của Kỳ. Vì vậy port bằng `git merge --ff-only
origin/data/giang`, không cherry-pick/port thủ công, zero conflict.

Sau merge: `make canonical` phải chạy lại (schema `stations` đổi, artefact cũ trên đĩa còn cột
LIVE cũ → `test_stations_artifact_has_no_live_copy` đỏ). Rebuild xong: gates PASS, **pytest
170/170, 0 skip**. Chưa rebuild tiếp `admin-grid`/`demand`/`candidates`/`covered0`-national —
để trong phạm vi kickoff thuật toán, không phải phần đóng nhánh này.
