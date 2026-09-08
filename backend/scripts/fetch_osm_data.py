"""Fetch real OpenStreetMap road data for the UrbanRelay demo zones and export a clean GeoJSON road graph.

Zones: Secunderabad, Kukatpally, Miyapur (Hyderabad metro).
Outputs:
  data/raw/hyderabad_overpass.json   raw Overpass response
  data/geojson/hyderabad_roads.geojson  cleaned graph (LineString edges + Point nodes)

Run from repo root:  python backend/scripts/fetch_osm_data.py
Requires network access to the Overpass API. Results are committed to the repo so the
demo itself runs fully offline.
"""

import json
import math
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
GEOJSON = ROOT / "data" / "geojson"
RAW.mkdir(parents=True, exist_ok=True)
GEOJSON.mkdir(parents=True, exist_ok=True)

# Per-city bounding boxes covering the demo zones plus corridors so each road
# graph is connected end-to-end (minlat, minlon, maxlat, maxlon)
CITIES = {
    "hyderabad": {
        "raw": "hyderabad_overpass.json",
        "out": "hyderabad_roads.geojson",
        "boxes": {
            "Secunderabad": (17.4200, 78.4700, 17.4700, 78.5300),
            "Kukatpally": (17.4700, 78.3800, 17.5200, 78.4400),
            "Miyapur": (17.4900, 78.3200, 17.5500, 78.3800),
            "Corridor": (17.4300, 78.4200, 17.5300, 78.4700),
        },
    },
    "vizag": {
        "raw": "vizag_overpass.json",
        "out": "vizag_roads.geojson",
        "boxes": {
            # Dwaraka Nagar CBD, Kancharapalem, MVP Colony
            "City Core": (17.6950, 83.2650, 17.7600, 83.3600),
            # Gajuwaka industrial belt
            "Gajuwaka": (17.6000, 83.1700, 17.6600, 83.2400),
            # corridor connecting Gajuwaka to the core
            "Corridor": (17.6500, 83.1900, 17.7100, 83.3100),
        },
    },
}

# backwards-compatible alias
ZONES = CITIES["hyderabad"]["boxes"]

HIGHWAY_RE = re.compile(
    r"^(motorway|motorway_link|trunk|trunk_link|primary|primary_link|secondary|"
    r"secondary_link|tertiary|tertiary_link|unclassified|residential|living_street)$"
)

SPEED_DEFAULT = {
    "motorway": 70, "motorway_link": 40, "trunk": 60, "trunk_link": 40,
    "primary": 50, "primary_link": 30, "secondary": 40, "secondary_link": 30,
    "tertiary": 30, "tertiary_link": 20, "unclassified": 20,
    "residential": 20, "living_street": 10,
}


def build_query(boxes: dict) -> str:
    bbox_clauses = "\n".join(
        f'  way["highway"]({a},{b},{c},{d});' for a, b, c, d in boxes.values()
    )
    return f"""
[out:json][timeout:180];
(
{bbox_clauses}
);
out body;
>;
out skel qt;
"""


def fetch(query: str, retries: int = 3) -> dict:
    url = "https://overpass-api.de/api/interpreter"
    data = urllib.parse.urlencode({"data": query}).encode()
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers={"User-Agent": "UrbanRelay-AI-dev/1.0"})
            with urllib.request.urlopen(req, timeout=180) as resp:
                return json.loads(resp.read().decode())
        except Exception as exc:  # noqa: BLE001
            print(f"  attempt {attempt + 1} failed: {exc}", file=sys.stderr)
            if attempt < retries - 1:
                time.sleep(5)
    raise SystemExit("Overpass fetch failed after retries")


def haversine_m(a_lat: float, a_lon: float, b_lat: float, b_lon: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dp, dl = math.radians(b_lat - a_lat), math.radians(b_lon - a_lon)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def speed_for(tags: dict) -> int:
    raw = (tags.get("maxspeed") or "").strip().lower()
    m = re.match(r"^(\d+(?:\.\d+)?)", raw)
    if m and "mph" not in raw:
        return int(round(float(m.group(1))))
    if "mph" in raw:
        return int(round(float(m.group(1)) * 1.609))
    return SPEED_DEFAULT.get(tags.get("highway", ""), 20)


def parse(raw: dict) -> dict:
    nodes: dict[str, tuple[float, float]] = {}
    for el in raw.get("elements", []):
        if el.get("type") == "node" and el.get("lat") is not None:
            nodes[str(el["id"])] = (el["lat"], el["lon"])

    edges: dict[tuple[str, str], dict] = {}  # (u, v) -> attrs (undirected key)
    stats = {"ways": 0, "edges": 0, "skipped_ways": 0}
    for el in raw.get("elements", []):
        if el.get("type") != "way":
            continue
        tags = el.get("tags", {})
        highway = tags.get("highway", "")
        if not HIGHWAY_RE.match(highway):
            stats["skipped_ways"] += 1
            continue
        refs = [str(n) for n in el.get("nodes", [])]
        if len(refs) < 2:
            stats["skipped_ways"] += 1
            continue
        stats["ways"] += 1
        speed = speed_for(tags)
        oneway = False
        ow = tags.get("oneway", "").strip().lower()
        # Only motorways are one-way by default in OSM. Trunk/primary roads in
        # India are frequently single-carriageway two-way, so they must rely on
        # an explicit oneway tag — otherwise one-way gates appear in the graph.
        if ow in ("yes", "true", "1") or tags.get("junction") == "roundabout" or highway == "motorway":
            oneway = True
        reverse = ow == "-1"
        name = tags.get("name", "")

        for i in range(len(refs) - 1):
            u, v = refs[i], refs[i + 1]
            if u == v:
                continue
            if u not in nodes or v not in nodes:
                continue
            la1, lo1 = nodes[u]
            la2, lo2 = nodes[v]
            length = haversine_m(la1, lo1, la2, lo2)
            if length < 5:
                continue
            key = (u, v)
            cur = edges.get(key)
            better = cur is None or (speed, -length) > (cur["speed"], -cur["length"])
            if better:
                edges[key] = {
                    "u": u, "v": v,
                    "class": highway,
                    "length": round(length),
                    "speed": speed,
                    "oneway": oneway,
                    "reverse": reverse,
                    "name": name,
                }
    stats["edges"] = len(edges)
    print(f"  parsed: {stats}", file=sys.stderr)
    return {"nodes": nodes, "edges": edges}


def export(data: dict) -> dict:
    """Slim export: LineString edges only; nodes are reconstructed from edge endpoints."""
    nodes, edges = data["nodes"], data["edges"]
    features = []
    for (u, v), attrs in sorted(edges.items()):
        la1, lo1 = nodes[u]
        la2, lo2 = nodes[v]
        coords = [[round(lo1, 6), round(la1, 6)], [round(lo2, 6), round(la2, 6)]]
        if attrs["oneway"] and attrs["reverse"]:
            # oneway=-1: traffic flows v->u; flip geometry so the LineString
            # direction always matches the permitted flow.
            coords = [coords[1], coords[0]]
        features.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": coords},
            "properties": {
                "kind": "edge",
                "class": attrs["class"],
                "length_m": attrs["length"],
                "speed_kph": attrs["speed"],
                "oneway": attrs["oneway"],
            },
        })
    return {"type": "FeatureCollection", "features": features}


def fetch_city(code: str) -> None:
    cfg = CITIES[code]
    RAW_FILE = RAW / cfg["raw"]
    if RAW_FILE.exists():
        print(f"[{code}] Reusing cached raw dump: {RAW_FILE}", file=sys.stderr)
        raw = json.loads(RAW_FILE.read_text(encoding="utf-8"))
    else:
        print(f"[{code}] Building Overpass query...", file=sys.stderr)
        query = build_query(cfg["boxes"])
        print(f"[{code}] Fetching OSM data...", file=sys.stderr)
        raw = fetch(query)
        RAW_FILE.write_text(json.dumps(raw), encoding="utf-8")
        print(f"  raw saved: {RAW_FILE} ({RAW_FILE.stat().st_size / 1e6:.1f} MB)", file=sys.stderr)

    print(f"[{code}] Parsing graph...", file=sys.stderr)
    data = parse(raw)
    fc = export(data)

    OUT = GEOJSON / cfg["out"]
    OUT.write_text(json.dumps(fc), encoding="utf-8")
    n_edges = sum(1 for f in fc["features"] if f["properties"]["kind"] == "edge")
    n_nodes = sum(1 for f in fc["features"] if f["properties"]["kind"] == "node")
    print(f"[{code}] Exported {n_edges} edges, {n_nodes} nodes -> {OUT} ({OUT.stat().st_size / 1e6:.1f} MB)")


def main() -> None:
    targets = sys.argv[1:] or list(CITIES)
    for code in targets:
        if code not in CITIES:
            raise SystemExit(f"unknown city '{code}'. Available: {', '.join(CITIES)}")
        fetch_city(code)


if __name__ == "__main__":
    main()