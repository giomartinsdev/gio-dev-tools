from __future__ import annotations

import csv
import io
import math
import time
import zipfile
from collections import Counter
from pathlib import Path

import httpx

from shared.logger import get_logger

logger = get_logger(__name__)

# SMTR's official monthly GTFS export for Rio (SPPO + BRT), published on data.rio.
_GTFS_URL = "https://www.arcgis.com/sharing/rest/content/items/8ffe62ad3b2f42e49814bf941654ea6c/data"
_CACHE_PATH = Path("/tmp/gtfs_rio_cache.zip")
_CACHE_TTL_SECONDS = 24 * 3600

# GTFS gives each direction/platform its own stop_id, so the same physical
# stop (e.g. both sides of the road) shows up twice with the same name a few
# meters apart — merge those instead of drawing two overlapping map dots.
_DEDUP_NAME_RADIUS_M = 100


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return r * 2 * math.asin(math.sqrt(a))


def _dedup_stops(stops: list[dict]) -> list[dict]:
    kept: list[dict] = []
    for stop in stops:
        duplicate = any(
            stop["name"] and stop["name"] == other["name"]
            and _haversine_m(stop["lat"], stop["lon"], other["lat"], other["lon"]) < _DEDUP_NAME_RADIUS_M
            for other in kept
        )
        if not duplicate:
            kept.append(stop)
    return kept


def _download_gtfs() -> bytes:
    if _CACHE_PATH.exists() and (time.time() - _CACHE_PATH.stat().st_mtime) < _CACHE_TTL_SECONDS:
        return _CACHE_PATH.read_bytes()
    with httpx.Client(timeout=60.0) as client:
        resp = client.get(_GTFS_URL, follow_redirects=True)
        resp.raise_for_status()
        data = resp.content
    _CACHE_PATH.write_bytes(data)
    return data


def fetch_directions_for_line(line_code: str) -> list[dict]:
    """Returns each GTFS travel direction for a line — headsign, deduped
    stops, and the route's shape polyline — so a rider can pick "toward X" vs
    "toward Y" instead of getting both directions' buses/stops merged
    together."""
    zip_bytes = _download_gtfs()
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        target = line_code.strip().lower()

        route_ids: set[str] = set()
        with zf.open("routes.txt") as f:
            for row in csv.DictReader(io.TextIOWrapper(f, encoding="utf-8")):
                if row["route_short_name"].strip().lower() == target:
                    route_ids.add(row["route_id"])
        if not route_ids:
            return []

        # direction_id -> headsign/shape candidates + the trip_ids that make up that direction
        directions: dict[int, dict] = {}
        trip_to_direction: dict[str, int] = {}
        with zf.open("trips.txt") as f:
            for row in csv.DictReader(io.TextIOWrapper(f, encoding="utf-8")):
                if row["route_id"] not in route_ids:
                    continue
                direction_id = int(row["direction_id"] or 0)
                d = directions.setdefault(direction_id, {"headsign": Counter(), "shape": Counter()})
                d["headsign"][row["trip_headsign"]] += 1
                d["shape"][row["shape_id"]] += 1
                trip_to_direction[row["trip_id"]] = direction_id
        if not directions:
            return []

        stop_ids_by_direction: dict[int, set[str]] = {d: set() for d in directions}
        with zf.open("stop_times.txt") as f:
            for row in csv.DictReader(io.TextIOWrapper(f, encoding="utf-8")):
                direction_id = trip_to_direction.get(row["trip_id"])
                if direction_id is not None:
                    stop_ids_by_direction[direction_id].add(row["stop_id"])

        all_stop_ids = {sid for ids in stop_ids_by_direction.values() for sid in ids}
        stop_by_id: dict[str, dict] = {}
        with zf.open("stops.txt") as f:
            for row in csv.DictReader(io.TextIOWrapper(f, encoding="utf-8")):
                if row["stop_id"] in all_stop_ids:
                    stop_by_id[row["stop_id"]] = {
                        "stop_id": row["stop_id"],
                        "name": row["stop_name"] or None,
                        "lat": float(row["stop_lat"]),
                        "lon": float(row["stop_lon"]),
                    }

        target_shape_ids = {d["shape"].most_common(1)[0][0] for d in directions.values() if d["shape"]}
        shape_points: dict[str, list[tuple[int, float, float]]] = {sid: [] for sid in target_shape_ids}
        with zf.open("shapes.txt") as f:
            for row in csv.DictReader(io.TextIOWrapper(f, encoding="utf-8")):
                if row["shape_id"] in shape_points:
                    shape_points[row["shape_id"]].append((
                        int(row["shape_pt_sequence"]), float(row["shape_pt_lat"]), float(row["shape_pt_lon"]),
                    ))
        for points in shape_points.values():
            points.sort(key=lambda p: p[0])

        result = []
        for direction_id, d in directions.items():
            headsign = d["headsign"].most_common(1)[0][0] if d["headsign"] else None
            shape_id = d["shape"].most_common(1)[0][0] if d["shape"] else None
            stops = _dedup_stops([stop_by_id[sid] for sid in stop_ids_by_direction[direction_id] if sid in stop_by_id])
            shape = [{"lat": lat, "lon": lon} for _, lat, lon in shape_points.get(shape_id, [])]
            result.append({
                "direction_id": direction_id,
                "headsign": headsign,
                "stops": stops,
                "shape": shape,
            })
        return result
