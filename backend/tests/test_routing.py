import json
import math
import tempfile
from pathlib import Path

from app.algorithms.graph import RoadGraph

# small synthetic grid: 3x3 nodes, each edge ~100m in lat/lng terms
NODES = {
    "a": (17.4800, 78.4000), "b": (17.4810, 78.4000), "c": (17.4820, 78.4000),
    "d": (17.4800, 78.4010), "e": (17.4810, 78.4010), "f": (17.4820, 78.4010),
    "g": (17.4800, 78.4020), "h": (17.4810, 78.4020), "i": (17.4820, 78.4020),
}
EDGES = [
    ("a", "b"), ("b", "c"), ("d", "e"), ("e", "f"), ("g", "h"), ("h", "i"),  # rows
    ("a", "d"), ("d", "g"), ("b", "e"), ("e", "h"), ("c", "f"), ("f", "i"),  # cols
]


def _edge_len(u, v):
    (la1, lo1), (la2, lo2) = NODES[u], NODES[v]
    return round(math.hypot((la2 - la1) * 111000, (lo2 - lo1) * 111000), 1)


def _make_geojson(path: Path, oneway_edges: set[tuple[str, str]] | None = None) -> None:
    oneway_edges = oneway_edges or set()
    features = []
    for u, v in EDGES:
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": [[NODES[u][1], NODES[u][0]], [NODES[v][1], NODES[v][0]]]},
                "properties": {
                    "kind": "edge", "class": "residential", "length_m": _edge_len(u, v),
                    "speed_kph": 20, "oneway": (u, v) in oneway_edges,
                },
            }
        )
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features}), encoding="utf-8")


def test_shortest_path():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "grid.geojson"
        _make_geojson(path)
        g = RoadGraph(str(path), zones=[])
        a, c = NODES["a"], NODES["c"]
        r = g.route(a[0], a[1], c[0], c[1], vehicle_speed_kph=20)
        assert r.polyline
        assert r.distance_m > 0
        assert r.duration_min > 0
        # direct row path a->b->c is shortest
        assert len(r.polyline) == 3
        assert abs(r.distance_m - _edge_len("a", "b") * 2) < 10


def test_oneway_forces_detour():
    # A one-way ring: traffic must loop the full cycle c->f->i->h->g->d->a
    ring = [("a", "b"), ("b", "c"), ("c", "f"), ("f", "i"), ("i", "h"), ("h", "g"), ("g", "d"), ("d", "a")]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "ring.geojson"
        fc = {"type": "FeatureCollection", "features": []}
        for u, v in ring:
            fc["features"].append(
                {
                    "type": "Feature",
                    "geometry": {"type": "LineString", "coordinates": [[NODES[u][1], NODES[u][0]], [NODES[v][1], NODES[v][0]]]},
                    "properties": {"kind": "edge", "class": "residential", "length_m": _edge_len(u, v), "speed_kph": 20, "oneway": True},
                }
            )
        path.write_text(json.dumps(fc))
        g = RoadGraph(str(path), zones=[])
        c, a = NODES["c"], NODES["a"]
        r = g.route(c[0], c[1], a[0], a[1], vehicle_speed_kph=20)
        assert r.polyline
        assert r.used_undirected is False  # directed path exists via the ring
        assert len(r.polyline) == 7  # c->f->i->h->g->d->a


def test_undirected_fallback_when_oneway_blocks():
    # One-way chain a->b->c: from c back to a there is no directed path,
    # so the engine must fall back to the undirected network.
    chain = [("a", "b"), ("b", "c")]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "chain.geojson"
        fc = {"type": "FeatureCollection", "features": []}
        for u, v in chain:
            fc["features"].append(
                {
                    "type": "Feature",
                    "geometry": {"type": "LineString", "coordinates": [[NODES[u][1], NODES[u][0]], [NODES[v][1], NODES[v][0]]]},
                    "properties": {"kind": "edge", "class": "residential", "length_m": _edge_len(u, v), "speed_kph": 20, "oneway": True},
                }
            )
        path.write_text(json.dumps(fc))
        g = RoadGraph(str(path), zones=[])
        c, a = NODES["c"], NODES["a"]
        r = g.route(c[0], c[1], a[0], a[1], vehicle_speed_kph=20)
        assert r.polyline
        assert r.used_undirected is True


def test_congestion_increases_duration():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "grid.geojson"
        _make_geojson(path)
        g = RoadGraph(str(path), zones=[])
        a, c = NODES["a"], NODES["c"]
        r1 = g.route(a[0], a[1], c[0], c[1], vehicle_speed_kph=20, congestion=lambda z: 0.0)
        r2 = g.route(a[0], a[1], c[0], c[1], vehicle_speed_kph=20, congestion=lambda z: 0.9)
        assert r2.duration_min > r1.duration_min
        assert r2.cost > r1.cost


def test_snapping_to_nearest_node():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "grid.geojson"
        _make_geojson(path)
        g = RoadGraph(str(path), zones=[])
        # a point slightly off-grid snaps to a real node
        node = g.nearest_node(17.48005, 78.40005)
        assert node is not None
        assert abs(node[0] - 17.48) < 0.0002