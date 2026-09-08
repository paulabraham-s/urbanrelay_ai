"""Road graph + routing engine.

Loads the bundled OSM-derived GeoJSON road network into a directed graph and
routes with congestion-aware edge costs:

    cost = alpha * distance_km + beta * time_s
    time_s = length / effective_speed * (1 + CONGESTION_PENALTY * congestion(zone))

One-way tags are respected, but if OSM's one-way interchange modeling leaves no
directed path (a known artifact of partial/dual-carriageway data), routing
falls back to the undirected network so the demo graph is always navigable.
Snapping prefers the giant connected component so isolated stub nodes are
avoided. See ALGORITHMS.md.
"""

import heapq
import json
import math
from collections import OrderedDict
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Callable

import networkx as nx

from app.algorithms.geo import haversine_km, haversine_m
from app.core.constants import CONGESTION_PENALTY, ROUTING_ALPHA, ROUTING_BETA

CongestionFn = Callable[[str | None], float]

# Heavy vehicles move slower on narrow roads (speed multiplier per road class)
VEHICLE_ROAD_FACTOR: dict[str, dict[str, float]] = {
    "truck": {"residential": 0.55, "living_street": 0.3, "unclassified": 0.8},
    "van": {"residential": 0.75, "living_street": 0.5},
}

_SNAP_GRID_DEG = 0.002


@dataclass
class RouteResult:
    from_lat: float
    from_lng: float
    to_lat: float
    to_lng: float
    distance_m: float = 0.0
    duration_min: float = 0.0
    cost: float = 0.0
    polyline: list[list[float]] = field(default_factory=list)
    node_count: int = 0
    algorithm: str = "dijkstra"
    used_undirected: bool = False


class RoadGraph:
    def __init__(self, geojson_path: str, zones: list[dict] | None = None):
        self.path = geojson_path
        self.zones = zones or []
        self.graph: nx.DiGraph = nx.DiGraph()
        self._snap_grid: dict[tuple[int, int], list[tuple[float, float]]] = {}
        self.giant: set[tuple[float, float]] = set()
        # LRU over solved paths (node lists). Distances/durations are recomputed
        # from the path on every call so congestion stays live; only the search
        # is skipped. Repeated legs (warehouse->hub, hub->customer) dominate
        # simulation routing load.
        self._path_cache: OrderedDict[tuple, list] = OrderedDict()
        self._load()

    # ------------------------------------------------------------- loading
    def _load(self) -> None:
        with open(self.path, encoding="utf-8") as fh:
            fc = json.load(fh)
        g = self.graph
        for feature in fc["features"]:
            props = feature.get("properties", {})
            if props.get("kind") != "edge":
                continue
            coords = feature["geometry"]["coordinates"]
            if len(coords) < 2:
                continue
            u = (round(coords[0][1], 6), round(coords[0][0], 6))
            v = (round(coords[1][1], 6), round(coords[1][0], 6))
            if u == v:
                continue
            zone_id = self._zone_of(u, v)
            attrs = {
                "length_m": float(props.get("length_m", 0)),
                "speed_kph": float(props.get("speed_kph", 20)),
                "class": props.get("class", "residential"),
                "zone": zone_id,
            }
            if attrs["length_m"] <= 0:
                continue
            g.add_edge(u, v, **attrs)
            if not props.get("oneway"):
                g.add_edge(v, u, **attrs)
        # snapping index + giant component
        for node in g.nodes:
            bx, by = int(node[0] / _SNAP_GRID_DEG), int(node[1] / _SNAP_GRID_DEG)
            self._snap_grid.setdefault((bx, by), []).append(node)
        if g.number_of_nodes() > 0:
            comps = nx.weakly_connected_components(g)
            self.giant = max(comps, key=len)

    def _zone_of(self, u: tuple[float, float], v: tuple[float, float]) -> str | None:
        lat, lng = (u[0] + v[0]) / 2, (u[1] + v[1]) / 2
        best, best_d = None, float("inf")
        for z in self.zones:
            d = haversine_km(z["center_lat"], z["center_lng"], lat, lng)
            if d <= z["radius_km"] and d < best_d:
                best, best_d = z["id"], d
        return best

    # ------------------------------------------------------------- snapping
    def nearest_node(self, lat: float, lng: float) -> tuple[float, float] | None:
        bx, by = int(lat / _SNAP_GRID_DEG), int(lng / _SNAP_GRID_DEG)
        best, best_d = None, float("inf")
        best_giant, best_giant_d = None, float("inf")
        for ring in range(0, 10):
            found_any = False
            for dx in range(-ring, ring + 1):
                for dy in range(-ring, ring + 1):
                    if max(abs(dx), abs(dy)) != ring:
                        continue
                    for node in self._snap_grid.get((bx + dx, by + dy), ()):
                        found_any = True
                        d = haversine_m(lat, lng, *node)
                        if d < best_d:
                            best, best_d = node, d
                        if node in self.giant and d < best_giant_d:
                            best_giant, best_giant_d = node, d
            if found_any and best is not None:
                return best_giant if best_giant is not None else best
        return best

    # ------------------------------------------------------------- routing
    def _cost(self, attrs: dict, vehicle_speed_kph: float, road_factor: dict[str, float], cong: float) -> float:
        speed = min(float(attrs["speed_kph"]), vehicle_speed_kph)
        speed = max(speed * road_factor.get(attrs["class"], 1.0), 2.0)
        time_s = attrs["length_m"] / (speed / 3.6)
        time_s *= 1.0 + CONGESTION_PENALTY * max(0.0, min(1.0, cong))
        return ROUTING_ALPHA * attrs["length_m"] / 1000.0 + ROUTING_BETA * time_s

    def _edge_cost(self, graph, u, v, vehicle_speed_kph: float, road_factor: dict[str, float], congestion: CongestionFn) -> float:
        attrs = graph[u][v]
        return self._cost(attrs, vehicle_speed_kph, road_factor, congestion(attrs.get("zone")))

    def route(
        self,
        from_lat: float,
        from_lng: float,
        to_lat: float,
        to_lng: float,
        *,
        vehicle_speed_kph: float = 30.0,
        vehicle_type: str | None = None,
        congestion: CongestionFn | None = None,
        algorithm: str = "dijkstra",
    ) -> RouteResult:
        src = self.nearest_node(from_lat, from_lng)
        dst = self.nearest_node(to_lat, to_lng)
        result = RouteResult(from_lat, from_lng, to_lat, to_lng)
        if src is None or dst is None or src not in self.graph or dst not in self.graph:
            return result
        if src == dst:
            result.polyline = [list(src)]
            result.node_count = 1
            return result

        congestion = congestion or (lambda _z: 0.0)
        road_factor = VEHICLE_ROAD_FACTOR.get(vehicle_type or "", {})

        cache_key = (src, dst, algorithm, vehicle_type or "")
        cached = self._path_cache.get(cache_key)
        used_undirected = False
        if cached is not None:
            self._path_cache.move_to_end(cache_key)
            path = cached
        else:
            path, _ = self._solve(self.graph, src, dst, vehicle_speed_kph, road_factor, congestion, algorithm)
            if not path:
                # one-way interchange artifacts can leave no directed path; fall back
                # to the undirected network so the city remains fully navigable
                undirected = self.graph.to_undirected()
                path, _ = self._solve(undirected, src, dst, vehicle_speed_kph, road_factor, congestion, algorithm)
                used_undirected = bool(path)
            if path:
                self._path_cache[cache_key] = path
                while len(self._path_cache) > 4096:
                    self._path_cache.popitem(last=False)
        if not path:
            return result

        distance = 0.0
        time_s = 0.0
        polyline: list[list[float]] = []
        undirected = None  # built lazily: only paths from the one-way fallback need it
        for i in range(len(path) - 1):
            if self.graph.has_edge(path[i], path[i + 1]):
                attrs = self.graph[path[i]][path[i + 1]]
            else:
                if undirected is None:
                    undirected = self.graph.to_undirected()
                attrs = undirected[path[i]][path[i + 1]]
            distance += attrs["length_m"]
            speed = max(min(attrs["speed_kph"], vehicle_speed_kph) * road_factor.get(attrs["class"], 1.0), 2.0)
            t = attrs["length_m"] / (speed / 3.6)
            t *= 1.0 + CONGESTION_PENALTY * max(0.0, min(1.0, congestion(attrs.get("zone"))))
            time_s += t
            if i == 0:
                polyline.append([path[i][0], path[i][1]])
            polyline.append([path[i + 1][0], path[i + 1][1]])
        result.distance_m = distance
        result.duration_min = time_s / 60.0
        result.cost = ROUTING_ALPHA * distance / 1000.0 + ROUTING_BETA * time_s
        result.polyline = polyline
        result.node_count = len(path)
        result.algorithm = algorithm
        result.used_undirected = used_undirected
        return result

    def _solve(self, graph, src, dst, v_speed, road_factor, congestion, algorithm):
        if algorithm == "astar":
            return self._astar(graph, src, dst, v_speed, road_factor, congestion)
        return self._dijkstra(graph, src, dst, v_speed, road_factor, congestion)

    def _dijkstra(self, graph, src, dst, v_speed, road_factor, congestion):
        dist = {src: 0.0}
        prev: dict = {}
        pq: list[tuple[float, tuple[float, float]]] = [(0.0, src)]
        visited: set = set()
        while pq:
            d, node = heapq.heappop(pq)
            if node in visited:
                continue
            visited.add(node)
            if node == dst:
                break
            for nb in graph[node]:
                cost = self._edge_cost(graph, node, nb, v_speed, road_factor, congestion)
                nd = d + cost
                if nd < dist.get(nb, float("inf")):
                    dist[nb] = nd
                    prev[nb] = node
                    heapq.heappush(pq, (nd, nb))
        if dst not in dist:
            return [], 0.0
        path = [dst]
        node = dst
        while node != src:
            node = prev.get(node)
            if node is None:
                return [], 0.0
            path.append(node)
        return path[::-1], dist[dst]

    def _astar(self, graph, src, dst, v_speed, road_factor, congestion):
        def h(node) -> float:
            return haversine_m(*node, *dst) / 1000.0 * ROUTING_ALPHA + (
                haversine_m(*node, *dst) / max(v_speed, 5) * 3.6
            ) * ROUTING_BETA * 60

        open_heap: list[tuple[float, float, tuple[float, float]]] = [(h(src), 0.0, src)]
        g_score = {src: 0.0}
        prev: dict = {}
        visited: set = set()
        while open_heap:
            _, g, node = heapq.heappop(open_heap)
            if node in visited:
                continue
            visited.add(node)
            if node == dst:
                break
            for nb in graph[node]:
                cost = self._edge_cost(graph, node, nb, v_speed, road_factor, congestion)
                tentative = g + cost
                if tentative < g_score.get(nb, float("inf")):
                    g_score[nb] = tentative
                    prev[nb] = node
                    heapq.heappush(open_heap, (tentative + h(nb), tentative, nb))
        if dst not in g_score:
            return [], 0.0
        path = [dst]
        node = dst
        while node != src:
            node = prev.get(node)
            if node is None:
                return [], 0.0
            path.append(node)
        return path[::-1], g_score[dst]


@lru_cache(maxsize=2)
def _graph_cache(geojson_path: str, zones_key: str) -> RoadGraph:
    zones = json.loads(zones_key) if zones_key else []
    return RoadGraph(geojson_path, zones)


def get_road_graph(geojson_path: str, zones: list[dict] | None = None) -> RoadGraph:
    zones_key = _json_key(zones)
    return _graph_cache(geojson_path, zones_key)


def _json_key(zones: list[dict] | None) -> str:
    if not zones:
        return "[]"
    slim = [
        {
            "id": z["id"],
            "center_lat": z["center_lat"],
            "center_lng": z["center_lng"],
            "radius_km": z["radius_km"],
        }
        for z in zones
    ]
    return json.dumps(slim, sort_keys=True)