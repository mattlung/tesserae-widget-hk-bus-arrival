"""Saved-journey setup for the Hong Kong Bus Arrival Tesserae bundle."""

from __future__ import annotations

import contextlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from werkzeug.wrappers import Response

BASE_URL = "https://data.etabus.gov.hk/v1/transport/kmb"
USER_AGENT = "tesserae/0.1 (+hk_bus_core)"
HTTP_TIMEOUT_S = 15
REFERENCE_CACHE_TTL_S = 20 * 60 * 60
ROUTE_RE = re.compile(r"^[A-Z0-9]{1,8}$")
STOP_RE = re.compile(r"^[A-F0-9]{16}$")


def _data_dir() -> Path:
    registry = current_app.config["PLUGIN_REGISTRY"]
    plugin = registry.get("hk_bus_core")
    if plugin is None:
        raise RuntimeError("hk_bus_core plugin not registered")
    return plugin.data_dir  # type: ignore[no-any-return]


def _store_path(data_dir: Path | None = None) -> Path:
    return (data_dir or _data_dir()) / "journeys.json"


def _load(data_dir: Path | None = None) -> dict[str, Any]:
    path = _store_path(data_dir)
    if not path.exists():
        return {"journeys": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"journeys": []}
    if not isinstance(data, dict) or not isinstance(data.get("journeys"), list):
        return {"journeys": []}
    return data


def _save(data: dict[str, Any], data_dir: Path | None = None) -> None:
    path = _store_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".json.tmp")
    temp_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temp_path.replace(path)


def _read_json(path: Path, max_age_s: int | None = None) -> Any | None:
    if not path.exists():
        return None
    if max_age_s is not None and time.time() - path.stat().st_mtime >= max_age_s:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    temp_path.replace(path)


def _get_json(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Unexpected response from KMB")
    return payload


def _api_data(endpoint: str, cache_name: str) -> list[dict[str, Any]]:
    cache_path = _data_dir() / f"api_{cache_name}.json"
    cached = _read_json(cache_path, REFERENCE_CACHE_TTL_S)
    if isinstance(cached, list):
        return cached

    payload = _get_json(f"{BASE_URL}/{endpoint.lstrip('/')}")
    data = payload.get("data")
    if not isinstance(data, list):
        raise ValueError("KMB returned an unexpected data format")
    rows = [row for row in data if isinstance(row, dict)]
    with contextlib.suppress(OSError):
        _write_json(cache_path, rows)
    return rows


def _load_routes() -> list[dict[str, Any]]:
    return _api_data("route/", "routes")


def _load_stops() -> list[dict[str, Any]]:
    return _api_data("stop", "stops")


def _load_route_stops(
    route: str, bound: str, service_type: str
) -> list[dict[str, Any]]:
    direction = "outbound" if bound == "O" else "inbound"
    endpoint = "/".join(
        [
            "route-stop",
            urllib.parse.quote(route, safe=""),
            direction,
            urllib.parse.quote(service_type, safe=""),
        ]
    )
    cache_name = f"route_stops_{route}_{bound}_{service_type}"
    return _api_data(endpoint, cache_name)


def _route_sort_key(row: dict[str, Any]) -> tuple[int, str, int, str]:
    route = str(row.get("route") or "")
    match = re.match(r"^(\d+)(.*)$", route)
    number = int(match.group(1)) if match else 99999
    suffix = match.group(2) if match else route
    bound_rank = 0 if row.get("bound") == "O" else 1
    return (number, suffix, bound_rank, str(row.get("service_type") or ""))


def _search_routes(
    routes: list[dict[str, Any]], query: str, limit: int = 40
) -> list[dict[str, Any]]:
    needle = re.sub(r"\s+", "", query).upper()
    if not needle:
        return []

    matches = []
    seen: set[tuple[str, str, str]] = set()
    for row in routes:
        route = str(row.get("route") or "").upper()
        if needle not in route:
            continue
        key = (route, str(row.get("bound") or ""), str(row.get("service_type") or ""))
        if key in seen:
            continue
        seen.add(key)
        matches.append(row)

    matches.sort(
        key=lambda row: (
            0 if str(row.get("route") or "").upper() == needle else 1,
            0 if str(row.get("route") or "").upper().startswith(needle) else 1,
            _route_sort_key(row),
        )
    )
    return matches[:limit]


def _find_route(
    routes: list[dict[str, Any]], route: str, bound: str, service_type: str
) -> dict[str, Any] | None:
    for row in routes:
        if (
            str(row.get("route") or "").upper() == route
            and str(row.get("bound") or "") == bound
            and str(row.get("service_type") or "") == service_type
        ):
            return row
    return None


def _route_variants(
    routes: list[dict[str, Any]], route: str
) -> list[dict[str, Any]]:
    rows = [
        row
        for row in routes
        if str(row.get("route") or "").upper() == route.upper()
    ]
    rows.sort(key=_route_sort_key)
    return rows


def _join_stops(
    route_stop_rows: list[dict[str, Any]], stop_rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    stops_by_id = {
        str(row.get("stop") or ""): row
        for row in stop_rows
        if row.get("stop")
    }
    joined = []
    for route_stop in route_stop_rows:
        stop_id = str(route_stop.get("stop") or "")
        if not stop_id:
            continue
        stop = stops_by_id.get(stop_id, {})
        with contextlib.suppress(TypeError, ValueError):
            seq = int(route_stop.get("seq") or 0)
            joined.append(
                {
                    "stop_id": stop_id,
                    "seq": seq,
                    "name_en": stop.get("name_en") or stop_id,
                    "name_tc": stop.get("name_tc") or stop.get("name_en") or stop_id,
                    "name_sc": stop.get("name_sc") or stop.get("name_tc") or stop_id,
                }
            )
    joined.sort(key=lambda row: row["seq"])
    return joined


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _journey_id(route: str, bound: str, service_type: str, stop_id: str) -> str:
    route_slug = re.sub(r"[^a-z0-9]+", "-", route.lower()).strip("-")
    return f"{route_slug}-{bound.lower()}-{service_type}-{stop_id.lower()}"


def _build_journey(
    route_info: dict[str, Any], stop: dict[str, Any], custom_name: str = ""
) -> dict[str, Any]:
    route = str(route_info["route"]).upper()
    bound = str(route_info["bound"])
    service_type = str(route_info["service_type"])
    stop_id = str(stop["stop_id"])
    return {
        "id": _journey_id(route, bound, service_type, stop_id),
        "name": custom_name.strip(),
        "route": route,
        "bound": bound,
        "service_type": service_type,
        "seq": int(stop["seq"]),
        "stop_id": stop_id,
        "orig_en": route_info.get("orig_en") or "",
        "orig_tc": route_info.get("orig_tc") or route_info.get("orig_en") or "",
        "orig_sc": route_info.get("orig_sc") or route_info.get("orig_tc") or "",
        "dest_en": route_info.get("dest_en") or "",
        "dest_tc": route_info.get("dest_tc") or route_info.get("dest_en") or "",
        "dest_sc": route_info.get("dest_sc") or route_info.get("dest_tc") or "",
        "stop_name_en": stop.get("name_en") or stop_id,
        "stop_name_tc": stop.get("name_tc") or stop.get("name_en") or stop_id,
        "stop_name_sc": stop.get("name_sc") or stop.get("name_tc") or stop_id,
        "created_at": _now_iso(),
    }


def list_journeys() -> list[dict[str, Any]]:
    return list(_load().get("journeys", []))


def choices(name: str) -> list[dict[str, str]]:
    if name != "journeys":
        return []
    result = []
    for journey in list_journeys():
        label = journey.get("name") or (
            f"{journey.get('route', '-')} to {journey.get('dest_tc') or journey.get('dest_en', '-')}"
            f" - {journey.get('seq', '-')} {journey.get('stop_name_tc') or journey.get('stop_name_en', '-')}"
        )
        result.append({"value": str(journey.get("id") or ""), "label": str(label)})
    return result


def _friendly_api_error(error: Exception) -> str:
    if isinstance(error, urllib.error.HTTPError) and error.code == 429:
        return "KMB is receiving too many requests. Try again shortly."
    if isinstance(error, urllib.error.HTTPError):
        return "KMB could not load that route right now."
    if isinstance(error, (urllib.error.URLError, TimeoutError)):
        return "The KMB service could not be reached. Check the Tesserae host connection."
    return "Route information could not be loaded right now."


def blueprint() -> Blueprint:
    bp = Blueprint("hk_bus_core_admin", __name__, template_folder="templates")

    @bp.get("/")
    def index() -> str:
        query = (request.args.get("q") or "").strip()
        route = (request.args.get("route") or "").strip().upper()
        bound = (request.args.get("bound") or "O").strip().upper()
        service_type = (request.args.get("service_type") or "1").strip()

        search_results: list[dict[str, Any]] = []
        variants: list[dict[str, Any]] = []
        selected_route: dict[str, Any] | None = None
        stops: list[dict[str, Any]] = []

        if query or route:
            try:
                routes = _load_routes()
                if query:
                    search_results = _search_routes(routes, query)
                if route and ROUTE_RE.fullmatch(route):
                    variants = _route_variants(routes, route)
                    selected_route = _find_route(routes, route, bound, service_type)
                    if selected_route is None and variants:
                        selected_route = variants[0]
                        bound = str(selected_route.get("bound") or "O")
                        service_type = str(selected_route.get("service_type") or "1")
                    if selected_route is not None:
                        route_stops = _load_route_stops(route, bound, service_type)
                        stops = _join_stops(route_stops, _load_stops())
            except Exception as error:
                flash(_friendly_api_error(error), "error")

        return render_template(
            "hk_bus_core/index.html",
            journeys=list_journeys(),
            query=query,
            search_results=search_results,
            variants=variants,
            selected_route=selected_route,
            stops=stops,
            selected_bound=bound,
            selected_service_type=service_type,
        )

    @bp.post("/journeys")
    def create_journey() -> Response:
        route = (request.form.get("route") or "").strip().upper()
        bound = (request.form.get("bound") or "").strip().upper()
        service_type = (request.form.get("service_type") or "").strip()
        stop_id = (request.form.get("stop_id") or "").strip().upper()
        custom_name = (request.form.get("name") or "").strip()

        redirect_args = {
            "route": route,
            "bound": bound,
            "service_type": service_type,
        }
        if (
            not ROUTE_RE.fullmatch(route)
            or bound not in {"I", "O"}
            or not service_type.isdigit()
            or not STOP_RE.fullmatch(stop_id)
        ):
            flash("Choose a valid route, direction, and stop.", "error")
            return redirect(url_for("hk_bus_core_admin.index", **redirect_args))

        try:
            routes = _load_routes()
            route_info = _find_route(routes, route, bound, service_type)
            if route_info is None:
                raise ValueError("route not found")
            stops = _join_stops(
                _load_route_stops(route, bound, service_type), _load_stops()
            )
            stop = next((row for row in stops if row["stop_id"] == stop_id), None)
            if stop is None:
                raise ValueError("stop not found")
        except ValueError:
            flash("That stop is not part of the selected route direction.", "error")
            return redirect(url_for("hk_bus_core_admin.index", **redirect_args))
        except Exception as error:
            flash(_friendly_api_error(error), "error")
            return redirect(url_for("hk_bus_core_admin.index", **redirect_args))

        journey = _build_journey(route_info, stop, custom_name)
        data = _load()
        journeys = data.setdefault("journeys", [])
        if any(item.get("id") == journey["id"] for item in journeys):
            flash("That route and stop is already saved.", "error")
        else:
            journeys.append(journey)
            _save(data)
            flash(f"Saved route {route} at stop {stop['seq']}.", "ok")
        return redirect(url_for("hk_bus_core_admin.index", **redirect_args))

    @bp.post("/journeys/<journey_id>/delete")
    def delete_journey(journey_id: str) -> Response:
        data = _load()
        journeys = data.get("journeys", [])
        data["journeys"] = [row for row in journeys if row.get("id") != journey_id]
        if len(data["journeys"]) == len(journeys):
            abort(404)
        _save(data)
        flash("Saved journey removed.", "ok")
        return redirect(url_for("hk_bus_core_admin.index"))

    @bp.post("/refresh")
    def refresh_reference_data() -> Response:
        removed = 0
        for cache_path in _data_dir().glob("api_*.json"):
            with contextlib.suppress(OSError):
                cache_path.unlink()
                removed += 1
        flash("KMB route and stop data will refresh on the next search.", "ok")
        return redirect(url_for("hk_bus_core_admin.index"))

    return bp
