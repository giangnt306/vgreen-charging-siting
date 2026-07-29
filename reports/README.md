# reports/ — bài viết bàn giao (được commit)

Kết quả trình bày cho người đọc: báo cáo sprint, phân tích nghiệm MCLP, tài liệu
khuyến nghị vị trí. Khác với `docs/` — `docs/` là **tài liệu sống** của hệ thống
(schema, register vấn đề, cách chạy), còn `reports/` là **bản chốt tại một thời điểm**
gắn với một bundle dữ liệu cụ thể.

## Ba nơi, ba vai trò — đừng trộn

| Nơi                  | Nội dung                                              | Git            |
| -------------------- | ----------------------------------------------------- | -------------- |
| `outputs/`           | Mọi artefact script sinh ra (nghiệm MCLP, hình, map)  | **gitignored** |
| `reports/`           | Bài viết + `figures/` được chọn để kèm bài            | commit         |
| `docs/`              | Tài liệu sống: schema, known-issues, cách chạy        | commit         |

Hình đi từ `outputs/figures/` sang `reports/figures/` bằng **thao tác có chủ đích**,
không tự động: đã commit thì nó là bằng chứng, phải biết nó thuộc bundle nào.

## Bắt buộc ghi trong mỗi report

1. **Nhãn bundle dữ liệu** đã dùng (`data/processed/<label>/FREEZE.json` — `snapshot_id`
   + `git_head`). Không có nhãn thì con số không đối soát lại được.
2. **Tham số model** (λ, p, ngân sách, R) — hợp đồng ở `src/ev_siting/models/paths.py`.
3. **Hai nghĩa vụ của [candidate-sites.md §10](../docs/data-layer/candidate-sites.md)**:
   cảnh báo khảo sát thực địa cho điểm `T4` hoặc `NO_ROAD_ACCESS ∧ NOT_BUILT_UP`, và
   bảng phân rã theo `penalty_flags` × `capex_class`.
4. **Sensitivity λ ∈ {0, 1, 3}** — lệch > 20% giữa λ=0 và λ=1 thì chưa được công bố số.

> Dữ liệu evcs.vn bị giới hạn ToS (known-issues **F1**): report rời khỏi repo phải qua
> sign-off, và không kèm dữ liệu thô.
