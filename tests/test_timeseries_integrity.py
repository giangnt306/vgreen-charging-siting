"""Regression tests for F2/F3 telemetry preservation."""

import csv

import pytest

from ev_siting.data.evcs.evcs_scrape import ASK_JS, HOURS_ALLOWED, normalize_series, reconcile_failed
from ev_siting.data.evcs.split_timeseries import flush


def test_split_merges_discontiguous_blocks_and_new_run_wins(tmp_path):
    # Station A can reappear after B when scrape crashes/resumes. Its first block
    # must survive, and a newer observation of the same timestamp wins deterministically.
    flush("C.A", {100: "1", 200: "2"}, ts_dir=tmp_path)
    stats = flush("C.A", {200: "9", 300: "3"}, ts_dir=tmp_path)

    with (tmp_path / "C.A.csv").open(newline="", encoding="utf-8") as fh:
        assert list(csv.DictReader(fh)) == [
            {"timestamp": "100", "n_cars_charging": "1"},
            {"timestamp": "200", "n_cars_charging": "9"},
            {"timestamp": "300", "n_cars_charging": "3"},
        ]
    assert stats["overlap"] == 1


def test_history_asks_one_station_at_a_time_and_reports_timeout():
    # history_data carries no station id, so identity safety rests on: exactly one
    # in-flight request, the listener detached on timeout, and the timeout surfaced
    # to Python so `ask_station` can tear the shared socket down before the next sid.
    assert "async ([sid, hours, timeoutMs])" in ASK_JS  # mot tram moi lan goi
    assert "s.off('history_data', h)" in ASK_JS  # go listener khi timeout
    assert "status: 'timeout'" in ASK_JS  # bao ve Python de reset socket
    assert "subscribe" not in ASK_JS  # khong dang ky stream new_data


def test_ask_station_resets_socket_on_every_failure(monkeypatch):
    # Reply muon cua tram A chi co the resolve request cua tram B neu socket dung
    # chung song sot qua mot timeout -> moi nhanh hong PHAI dung socket lai.
    from ev_siting.data.evcs import evcs_scrape as m

    calls = []
    monkeypatch.setattr(m, "reset_socket", lambda page, verbose=True: calls.append("reset") or True)
    monkeypatch.setattr(m, "renew_session", lambda ctx, page, verbose=True: calls.append("renew") or True)

    class P:
        def __init__(self, r):
            self.r = r

        def evaluate(self, *a):
            if isinstance(self.r, Exception):
                raise self.r
            return self.r

    assert m.ask_station(P({"status": "timeout"}), None, "C.A", 720)[0] is None
    assert m.ask_station(P({"status": "socket_down"}), None, "C.A", 720)[0] is None
    assert m.ask_station(P(RuntimeError("boom")), None, "C.A", 720)[0] is None
    assert calls == ["reset", "reset", "reset"]

    # Duong thanh cong KHONG duoc dung socket (lang phi ~1s handshake moi tram).
    calls.clear()
    rows, _ = m.ask_station(P({"status": "ok", "data": [[1, 0], [2, 3]]}), None, "C.A", 720)
    assert rows == [(1, 0), (2, 3)] and calls == []


def test_normalize_series_accepts_both_payload_shapes():
    # 2026-07-29 server doi [{timestamp,value}] -> [[ts,value]]. Doc duoc CA HAI thi
    # run cu (07-21/22) van parse lai duoc; diem la khong duoc nuot im lang.
    assert normalize_series([[1, 0], [2, 5]]) == ([(1, 0), (2, 5)], 0)
    assert normalize_series([{"timestamp": 1, "value": 0}]) == ([(1, 0)], 0)
    assert normalize_series([]) == ([], 0)
    assert normalize_series([[1, 0], "rac", {"khong_co_timestamp": 1}]) == ([(1, 0)], 2)
    assert normalize_series("khong phai list") == (None, 0)  # -> ask_station bao 'payload la'


def test_hours_outside_server_enum_fails_fast():
    # Server chi ton trong {24,168,720}; gia tri khac bi bo qua im lang -> timeout 100%.
    # Fail ngay con hon chay 6 tieng roi thu duoc 0 diem.
    assert HOURS_ALLOWED == (24, 168, 720)
    from ev_siting.data.evcs import evcs_scrape as m

    with pytest.raises(SystemExit):
        m.run(["C.A"], 336, "/tmp/khong-duoc-tao.csv", False)


def test_failed_file_drops_codes_that_later_succeed(tmp_path):
    failed = tmp_path / "run.failed"
    failed.write_text("C.A\nC.B\n", encoding="utf-8")
    assert reconcile_failed(str(failed), {"C.A"}) == ["C.B"]
    assert failed.read_text(encoding="utf-8") == "C.B\n"
