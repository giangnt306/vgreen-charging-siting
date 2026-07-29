# notebooks/ — thăm dò, không phải pipeline

Chỗ cho phân tích khám phá và kiểm chứng nhanh. **Không** phải nơi chạy pipeline:
mọi thứ tái lập được phải sống trong `src/ev_siting/` và gọi qua `make`.

## Quy tắc

- **Đặt tên:** `NN-<chữ-cái-đầu>-<chủ-đề>.ipynb` — vd `01-ky-mclp-lambda-sweep.ipynb`.
  Số thứ tự cho biết thứ tự đọc, không phải thứ tự chạy.
- **Không khai lại đường dẫn.** Import từ package: `from ev_siting.models import paths`.
  Notebook hard-code `../data/...` là cách nhanh nhất để lệch khỏi hợp đồng schema.
- **Không commit dữ liệu.** Xoá output nặng trước khi commit (`jupyter nbconvert
  --clear-output --inplace <file>`); `data/` và `outputs/` đều gitignored.
- **Phát hiện nào cần giữ thì chuyển đi:** số + lập luận vào `docs/` hoặc `reports/`,
  code vào `src/`. Notebook là bản nháp — người sau không nên phải chạy lại nó để biết
  kết luận.

Môi trường: `uv run jupyter lab` (thêm `jupyter` vào dependency-group `dev` khi cần).
