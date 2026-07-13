from __future__ import annotations

import importlib.util
import os
import time
import urllib.error
from pathlib import Path
from types import SimpleNamespace
from typing import Any


MODULE_PATH = Path(__file__).parents[1] / "server.py"
SPEC = importlib.util.spec_from_file_location("hk_bus_arrival_server", MODULE_PATH)
assert SPEC and SPEC.loader
server = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(server)


JOURNEY = {
    "id": "1a-o-1-a3adfcdf8487adb9",
    "route": "1A",
    "bound": "O",
    "service_type": "1",
    "seq": 1,
    "stop_id": "A3ADFCDF8487ADB9",
    "stop_name_en": "SAU MAU PING (CENTRAL)",
    "stop_name_tc": "中秀茂坪",
    "stop_name_sc": "中秀茂坪",
    "dest_en": "STAR FERRY",
    "dest_tc": "尖沙咀碼頭",
    "dest_sc": "尖沙咀码头",
}


def eta_row(
    *,
    direction: str = "O",
    service_type: int = 1,
    seq: int = 1,
    eta_seq: int = 1,
) -> dict[str, Any]:
    return {
        "route": "1A",
        "dir": direction,
        "service_type": service_type,
        "seq": seq,
        "eta_seq": eta_seq,
        "eta": f"2026-07-13T17:{27 + eta_seq:02d}:00+08:00",
        "dest_en": "STAR FERRY",
        "dest_tc": "尖沙咀碼頭",
        "dest_sc": "尖沙咀码头",
        "rmk_en": "Scheduled Bus",
        "rmk_tc": "原定班次",
        "rmk_sc": "原定班次",
        "data_timestamp": "2026-07-13T17:26:15+08:00",
    }


def fake_core() -> SimpleNamespace:
    return SimpleNamespace(
        list_journeys=lambda: [JOURNEY],
        choices=lambda name: (
            [{"value": JOURNEY["id"], "label": "1A to Star Ferry"}]
            if name == "journeys"
            else []
        ),
    )


def test_filter_arrivals_rejects_opposite_terminal_direction() -> None:
    payload = {
        "data": [
            eta_row(direction="I", seq=34, eta_seq=1),
            eta_row(service_type=2, eta_seq=1),
            eta_row(eta_seq=3),
            eta_row(eta_seq=1),
            eta_row(eta_seq=2),
        ]
    }

    result = server._filter_arrivals(payload, JOURNEY, 3)

    assert [row["eta_seq"] for row in result] == [1, 2, 3]
    assert all(row["dest_tc"] == "尖沙咀碼頭" for row in result)


def test_choices_delegates_to_setup_plugin(monkeypatch: Any) -> None:
    monkeypatch.setattr(server, "_core_module", fake_core)
    assert server.choices("journeys") == [
        {"value": JOURNEY["id"], "label": "1A to Star Ferry"}
    ]


def test_fetch_filters_and_caches_live_payload(tmp_path: Path, monkeypatch: Any) -> None:
    payload = {
        "generated_timestamp": "2026-07-13T17:26:17+08:00",
        "data": [eta_row(eta_seq=2), eta_row(direction="I", seq=34), eta_row(eta_seq=1)],
    }
    requested_urls: list[str] = []
    monkeypatch.setattr(server, "_core_module", fake_core)

    def get_json(url: str) -> dict[str, Any]:
        requested_urls.append(url)
        return payload

    monkeypatch.setattr(server, "_get_json", get_json)
    options = {"journey_id": JOURNEY["id"], "max_etas": "2"}

    result = server.fetch(options, {}, ctx={"data_dir": str(tmp_path)})

    assert [row["eta_seq"] for row in result["arrivals"]] == [1, 2]
    assert requested_urls == [
        "https://data.etabus.gov.hk/v1/transport/kmb/eta/A3ADFCDF8487ADB9/1A/1"
    ]
    assert list(tmp_path.glob("eta_*.json"))

    monkeypatch.setattr(server, "_get_json", lambda _url: (_ for _ in ()).throw(AssertionError()))
    assert server.fetch(options, {}, ctx={"data_dir": str(tmp_path)}) == result


def test_fetch_returns_stale_cache_when_kmb_is_unavailable(
    tmp_path: Path, monkeypatch: Any
) -> None:
    monkeypatch.setattr(server, "_core_module", fake_core)
    payload = {
        "generated_timestamp": "2026-07-13T17:26:17+08:00",
        "data": [eta_row(eta_seq=1)],
    }
    monkeypatch.setattr(server, "_get_json", lambda _url: payload)
    options = {"journey_id": JOURNEY["id"], "max_etas": "1"}
    server.fetch(options, {}, ctx={"data_dir": str(tmp_path)})

    cache_path = next(tmp_path.glob("eta_*.json"))
    old_time = time.time() - server.ETA_CACHE_TTL_S - 1
    os.utime(cache_path, (old_time, old_time))
    monkeypatch.setattr(
        server,
        "_get_json",
        lambda _url: (_ for _ in ()).throw(urllib.error.URLError("offline")),
    )

    stale = server.fetch(options, {}, ctx={"data_dir": str(tmp_path)})

    assert stale["stale"] is True
    assert stale["arrivals"][0]["eta_seq"] == 1


def test_fetch_requires_a_saved_journey(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.setattr(server, "_core_module", fake_core)
    result = server.fetch({}, {}, ctx={"data_dir": str(tmp_path)})
    assert result == {"error": "Choose a saved journey for this cell."}
