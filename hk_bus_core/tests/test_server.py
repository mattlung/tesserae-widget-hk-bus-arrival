from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any


MODULE_PATH = Path(__file__).parents[1] / "server.py"
SPEC = importlib.util.spec_from_file_location("hk_bus_core_server", MODULE_PATH)
assert SPEC and SPEC.loader
server = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(server)


def route(
    number: str,
    bound: str,
    service_type: str = "1",
    destination: str = "DESTINATION",
) -> dict[str, Any]:
    return {
        "route": number,
        "bound": bound,
        "service_type": service_type,
        "orig_en": "ORIGIN",
        "orig_tc": "起點",
        "orig_sc": "起点",
        "dest_en": destination,
        "dest_tc": "終點",
        "dest_sc": "终点",
    }


def test_search_routes_prioritises_exact_matches_and_deduplicates() -> None:
    routes = [
        route("11", "O"),
        route("1A", "I"),
        route("1", "I"),
        route("1", "O"),
        route("1", "O"),
    ]

    matches = server._search_routes(routes, " 1 ")

    assert [(row["route"], row["bound"]) for row in matches[:2]] == [
        ("1", "O"),
        ("1", "I"),
    ]
    assert len(matches) == 4


def test_join_stops_sorts_sequence_and_keeps_a_fallback_name() -> None:
    route_stops = [
        {"seq": "2", "stop": "BBBBBBBBBBBBBBBB"},
        {"seq": "1", "stop": "AAAAAAAAAAAAAAAA"},
    ]
    stops = [
        {
            "stop": "AAAAAAAAAAAAAAAA",
            "name_en": "FIRST STOP",
            "name_tc": "第一站",
            "name_sc": "第一站",
        }
    ]

    result = server._join_stops(route_stops, stops)

    assert [row["seq"] for row in result] == [1, 2]
    assert result[0]["name_tc"] == "第一站"
    assert result[1]["name_en"] == "BBBBBBBBBBBBBBBB"


def test_build_journey_preserves_direction_and_localised_names() -> None:
    stop = {
        "stop_id": "A3ADFCDF8487ADB9",
        "seq": 1,
        "name_en": "SAU MAU PING (CENTRAL)",
        "name_tc": "中秀茂坪",
        "name_sc": "中秀茂坪",
    }

    journey = server._build_journey(route("1A", "O", destination="STAR FERRY"), stop)

    assert journey["id"] == "1a-o-1-a3adfcdf8487adb9"
    assert journey["bound"] == "O"
    assert journey["stop_name_tc"] == "中秀茂坪"
    assert journey["dest_en"] == "STAR FERRY"


def test_store_round_trip_and_corrupt_file_fallback(tmp_path: Path) -> None:
    data = {"journeys": [{"id": "one"}]}
    server._save(data, tmp_path)
    assert server._load(tmp_path) == data

    server._store_path(tmp_path).write_text("not json", encoding="utf-8")
    assert server._load(tmp_path) == {"journeys": []}
