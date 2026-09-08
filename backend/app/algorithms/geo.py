"""Geospatial helpers used across routing, agents, and simulation."""

import math
import random
from typing import Sequence

EARTH_RADIUS_M = 6_371_000.0


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    return haversine_m(lat1, lng1, lat2, lng2) / 1000.0


def point_in_zone(zone: dict, lat: float, lng: float) -> bool:
    return haversine_km(zone["center_lat"], zone["center_lng"], lat, lng) <= zone["radius_km"]


def random_point_in_zone(rng: random.Random, zone: dict) -> tuple[float, float]:
    """Gaussian scatter around the zone center, clipped to the radius."""
    for _ in range(50):
        dlat = rng.gauss(0, zone["radius_km"] * 0.35 / 111.0)
        dlng = rng.gauss(0, zone["radius_km"] * 0.35 / (111.0 * math.cos(math.radians(zone["center_lat"]))))
        lat, lng = zone["center_lat"] + dlat, zone["center_lng"] + dlng
        if point_in_zone(zone, lat, lng):
            return lat, lng
    return zone["center_lat"], zone["center_lng"]


def nearest_zone(zone_list: Sequence[dict], lat: float, lng: float) -> dict | None:
    best, best_d = None, float("inf")
    for zone in zone_list:
        d = haversine_km(zone["center_lat"], zone["center_lng"], lat, lng)
        if d <= zone["radius_km"] and d < best_d:
            best, best_d = zone, d
    return best


def polyline_point(polyline: list[list[float]], cumdist: list[float], dist_m: float) -> list[float]:
    """Return the interpolated [lat, lng] at `dist_m` along a polyline.

    `cumdist` is the precomputed cumulative distance (m) at each vertex.
    """
    if dist_m <= 0:
        return polyline[0]
    if dist_m >= cumdist[-1]:
        return polyline[-1]
    # binary search for the segment
    lo, hi = 0, len(cumdist) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if cumdist[mid] < dist_m:
            lo = mid + 1
        else:
            hi = mid
    i = max(lo - 1, 0)
    seg_len = cumdist[i + 1] - cumdist[i]
    if seg_len <= 0:
        return polyline[i + 1]
    f = (dist_m - cumdist[i]) / seg_len
    return [
        polyline[i][0] + (polyline[i + 1][0] - polyline[i][0]) * f,
        polyline[i][1] + (polyline[i + 1][1] - polyline[i][1]) * f,
    ]


def polyline_cumdist(polyline: list[list[float]]) -> list[float]:
    cum = [0.0]
    for i in range(1, len(polyline)):
        cum.append(cum[-1] + haversine_m(*polyline[i - 1], *polyline[i]))
    return cum


def polyline_length_m(polyline: list[list[float]]) -> float:
    if not polyline:
        return 0.0
    return polyline_cumdist(polyline)[-1]