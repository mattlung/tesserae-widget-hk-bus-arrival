"""Live KMB ETA fetcher for the Hong Kong Bus Arrival widget."""

from __future__ import annotations

import contextlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from flask import current_app

BASE_URL = "https://data.etabus.gov.hk/v1/transport/kmb"
USER_AGENT = "tesserae/0.1 (+hk_bus_arrival)"
HTTP_TIMEOUT_S = 12
ETA_CACHE_TTL_S = 25
MAX_ROUTES = 8
ROUTE_RE = re.compile(r"^[A-Z0-9]{1,8}$")
STOP_RE = re.compile(r"^[A-F0-9]{16}$")


def _core_module() -> Any:
    registry = current_app.config.get("PLUGIN_REGISTRY")
    if registry is None:
        return None
    core = registry.get("hk_bus_core")
    if core is None:
        return None
    return core.server_module


def choices(name: str) -> list[dict[str, str]]:
    core = _core_module()
    core_choices = getattr(core, "choices", None) if core is not None else None
    if not callable(core_choices):
        return []
    try:
        return list(core_choices(name) or [])
    except Exception:
        return []


def _list_journeys() -> list[dict[str, Any]]:
    core = _core_module()
    list_journeys = getattr(core, "list_journeys", None) if core is not None else None
    if not callable(list_journeys):
        return []
    try:
        return [row for row in list_journeys() if isinstance(row, dict)]
    except Exception:
        return []


def _journey_ids(raw: Any) -> list[str]:
    if isinstance(raw, list):
        values = [str(value).strip() for value in raw]
    else:
        values = re.split(r"[\s,]+", str(raw or "").strip())

    result = []
    seen = set()
    for value in values:
        if value and value not in seen:
            result.append(value)
            seen.add(value)
    return result


def _get_json(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Unexpected response from KMB")
    return payload


def _read_cache(path: Path, fresh_only: bool) -> dict[str, Any] | None:
    if not path.exists():
        return None
    if fresh_only and time.time() - path.stat().st_mtime >= ETA_CACHE_TTL_S:
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _write_cache(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    temp_path.replace(path)


def _cache_path(data_dir: Path, journey_id: str, max_etas: int) -> Path:
    safe_id = re.sub(r"[^a-zA-Z0-9_-]+", "_", journey_id)
    return data_dir / f"eta_{safe_id}_{max_etas}.json"


def _filter_arrivals(
    payload: dict[str, Any], journey: dict[str, Any], max_etas: int
) -> list[dict[str, Any]]:
    rows = payload.get("data")
    if not isinstance(rows, list):
        return []

    route = str(journey.get("route") or "").upper()
    bound = str(journey.get("bound") or "")
    service_type = int(journey.get("service_type") or 0)
    seq = int(journey.get("seq") or 0)
    filtered = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            matches = (
                str(row.get("route") or "").upper() == route
                and str(row.get("dir") or "") == bound
                and int(row.get("service_type") or 0) == service_type
                and int(row.get("seq") or 0) == seq
            )
        except (TypeError, ValueError):
            matches = False
        if not matches:
            continue
        filtered.append(
            {
                "eta_seq": row.get("eta_seq"),
                "eta": row.get("eta"),
                "dest_en": row.get("dest_en") or journey.get("dest_en") or "",
                "dest_tc": row.get("dest_tc") or journey.get("dest_tc") or "",
                "dest_sc": row.get("dest_sc") or journey.get("dest_sc") or "",
                "remark_en": row.get("rmk_en") or "",
                "remark_tc": row.get("rmk_tc") or "",
                "remark_sc": row.get("rmk_sc") or "",
                "data_timestamp": row.get("data_timestamp") or "",
            }
        )

    filtered.sort(
        key=lambda row: (
            row.get("eta") is None,
            int(row.get("eta_seq") or 999),
        )
    )
    return filtered[:max_etas]


def _friendly_error(error: Exception) -> str:
    if isinstance(error, urllib.error.HTTPError) and error.code == 429:
        return "KMB is receiving too many requests. Try again shortly."
    if isinstance(error, urllib.error.HTTPError):
        return "KMB arrival times are temporarily unavailable."
    if isinstance(error, (urllib.error.URLError, TimeoutError)):
        return "KMB could not be reached from the Tesserae host."
    return "Arrival times could not be loaded right now."


def _valid_journey(journey: dict[str, Any]) -> bool:
    route = str(journey.get("route") or "").upper()
    stop_id = str(journey.get("stop_id") or "").upper()
    service_type = str(journey.get("service_type") or "")
    return bool(
        ROUTE_RE.fullmatch(route)
        and STOP_RE.fullmatch(stop_id)
        and service_type.isdigit()
    )


def _fetch_journey(
    journey: dict[str, Any], max_etas: int, data_dir: Path
) -> dict[str, Any]:
    journey_id = str(journey.get("id") or "")
    route = str(journey.get("route") or "").upper()
    stop_id = str(journey.get("stop_id") or "").upper()
    service_type = str(journey.get("service_type") or "")
    cache_path = _cache_path(data_dir, journey_id, max_etas)
    cached = _read_cache(cache_path, fresh_only=True)
    if cached is not None:
        return cached

    url = (
        f"{BASE_URL}/eta/{urllib.parse.quote(stop_id, safe='')}/"
        f"{urllib.parse.quote(route, safe='')}/{urllib.parse.quote(service_type, safe='')}"
    )
    try:
        payload = _get_json(url)
        arrivals = _filter_arrivals(payload, journey, max_etas)
    except Exception as error:
        stale = _read_cache(cache_path, fresh_only=False)
        if stale is not None:
            stale["stale"] = True
            return stale
        return {"error": _friendly_error(error), "journey": journey, "arrivals": []}

    data_timestamps = [
        row.get("data_timestamp") for row in arrivals if row.get("data_timestamp")
    ]
    result = {
        "journey": journey,
        "arrivals": arrivals,
        "generated_timestamp": payload.get("generated_timestamp") or "",
        "data_timestamp": max(data_timestamps) if data_timestamps else "",
        "stale": False,
    }
    with contextlib.suppress(OSError):
        _write_cache(cache_path, result)
    return result


def fetch(
    options: dict[str, Any], settings: dict[str, Any], *, ctx: dict[str, Any]
) -> dict[str, Any]:
    del settings
    journey_ids = _journey_ids(options.get("journey_id"))
    if not journey_ids:
        return {"error": "Choose at least one saved journey for this cell."}
    if len(journey_ids) > MAX_ROUTES:
        return {"error": f"Choose no more than {MAX_ROUTES} saved journeys."}

    journeys_by_id = {
        str(row.get("id") or ""): row for row in _list_journeys() if row.get("id")
    }
    if any(journey_id not in journeys_by_id for journey_id in journey_ids):
        return {
            "error": "One or more saved journeys are no longer available. Update this cell."
        }
    journeys = [journeys_by_id[journey_id] for journey_id in journey_ids]
    if not all(_valid_journey(journey) for journey in journeys):
        return {"error": "A saved journey is invalid. Create it again in Bus Setup."}

    try:
        max_etas = max(1, min(3, int(options.get("max_etas") or 3)))
    except (TypeError, ValueError):
        max_etas = 3

    data_dir = Path(ctx["data_dir"])
    if len(journeys) == 1:
        routes = [_fetch_journey(journeys[0], max_etas, data_dir)]
    else:
        with ThreadPoolExecutor(max_workers=min(4, len(journeys))) as executor:
            routes = list(
                executor.map(
                    lambda journey: _fetch_journey(journey, max_etas, data_dir),
                    journeys,
                )
            )

    data_timestamps = [row.get("data_timestamp") for row in routes if row.get("data_timestamp")]
    generated_timestamps = [
        row.get("generated_timestamp") for row in routes if row.get("generated_timestamp")
    ]
    first_journey = journeys[0]
    return {
        "stop": {
            "stop_id": first_journey.get("stop_id") or "",
            "stop_name_en": first_journey.get("stop_name_en") or "",
            "stop_name_tc": first_journey.get("stop_name_tc") or "",
            "stop_name_sc": first_journey.get("stop_name_sc") or "",
        },
        "routes": routes,
        "generated_timestamp": max(generated_timestamps) if generated_timestamps else "",
        "data_timestamp": max(data_timestamps) if data_timestamps else "",
        "stale": any(bool(row.get("stale")) for row in routes),
    }
