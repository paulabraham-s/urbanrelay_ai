"""In-memory simulation state.

The simulation is authoritative in memory; the database keeps durable records
(orders, waves, decisions, alerts, run summaries) for history and analytics.
"""

import random
from dataclasses import dataclass, field

from app.algorithms.geo import polyline_cumdist, polyline_point, polyline_length_m
from app.core.constants import SIMULATION_MODE_BASELINE

ACTIVE_ORDER_STATUSES = ("PENDING", "WAVE_ASSIGNED", "PICKED_UP", "AT_HUB", "OUT_FOR_DELIVERY")


@dataclass
class VehicleState:
    id: str
    name: str
    type: str
    capacity: int
    speed_kph: float
    lat: float
    lng: float
    status: str = "IDLE"
    zone_id: str | None = None
    cargo: list[str] = field(default_factory=list)
    route: list[list[float]] = field(default_factory=list)
    cumdist: list[float] = field(default_factory=list)
    travelled_m: float = 0.0
    mode: str = SIMULATION_MODE_BASELINE
    hub_id: str | None = None

    @property
    def total_m(self) -> float:
        return self.cumdist[-1] if self.cumdist else 0.0

    @property
    def progress(self) -> float:
        return min(1.0, self.travelled_m / self.total_m) if self.total_m > 0 else 0.0

    def assign_route(self, polyline: list[list[float]]) -> None:
        self.route = polyline
        self.cumdist = polyline_cumdist(polyline)
        self.travelled_m = 0.0

    def position(self) -> list[float]:
        if not self.route:
            return [self.lat, self.lng]
        return polyline_point(self.route, self.cumdist, self.travelled_m)

    def advance(self, dist_m: float) -> bool:
        """Advance and return True when the route is complete."""
        self.travelled_m += dist_m
        return self.travelled_m >= self.total_m


@dataclass
class CourierState:
    id: str
    name: str
    mode: str
    capacity: int
    lat: float
    lng: float
    status: str = "AVAILABLE"
    zone_id: str | None = None
    cargo: list[str] = field(default_factory=list)
    route: list[list[float]] = field(default_factory=list)
    cumdist: list[float] = field(default_factory=list)
    travelled_m: float = 0.0
    hub_id: str | None = None
    earnings: float = 0.0
    target_order_id: str | None = None

    @property
    def total_m(self) -> float:
        return self.cumdist[-1] if self.cumdist else 0.0

    @property
    def progress(self) -> float:
        return min(1.0, self.travelled_m / self.total_m) if self.total_m > 0 else 0.0

    def assign_route(self, polyline: list[list[float]]) -> None:
        self.route = polyline
        self.cumdist = polyline_cumdist(polyline)
        self.travelled_m = 0.0

    def position(self) -> list[float]:
        if not self.route:
            return [self.lat, self.lng]
        return polyline_point(self.route, self.cumdist, self.travelled_m)

    def advance(self, dist_m: float) -> bool:
        self.travelled_m += dist_m
        return self.travelled_m >= self.total_m


@dataclass
class OrderState:
    id: str
    platform: str
    zone_id: str
    zone_name: str
    customer_lat: float
    customer_lng: float
    customer_name: str
    address: str
    weight_kg: float
    volume_units: int
    priority: int
    created_t: float
    status: str = "PENDING"
    mode: str = SIMULATION_MODE_BASELINE
    warehouse: dict = field(default_factory=dict)
    hub_id: str | None = None
    vehicle_id: str | None = None
    courier_id: str | None = None
    delivered_t: float | None = None
    distance_km: float | None = None
    duration_min: float | None = None
    emissions_kg: float | None = None


@dataclass
class Metrics:
    deliveries: dict[str, int] = field(default_factory=lambda: {"baseline": 0, "urbanrelay": 0})
    distance_km: dict[str, float] = field(default_factory=lambda: {"baseline": 0.0, "urbanrelay": 0.0})
    duration_min: dict[str, float] = field(default_factory=lambda: {"baseline": 0.0, "urbanrelay": 0.0})
    emissions_kg: dict[str, float] = field(default_factory=lambda: {"baseline": 0.0, "urbanrelay": 0.0})
    dispatches: dict[str, int] = field(default_factory=lambda: {"baseline": 0, "urbanrelay": 0})
    history: list[dict] = field(default_factory=list)


class SimulationState:
    def __init__(self) -> None:
        self.run_id: str | None = None
        self.city_id: str | None = None
        self.running: bool = False
        self.t: float = 0.0
        self.speed: float = 1.0
        self.seed: int = 42
        self.scenario: dict = {}
        self.mode: str = SIMULATION_MODE_BASELINE
        self.next_reopt_t: float = 0.0
        self.last_optimization: dict | None = None

        self.rng = random.Random(self.seed)
        self.zones: list[dict] = []
        self.warehouses: list[dict] = []
        self.hubs: dict[str, dict] = {}
        self.curb_zones: list[dict] = []
        self.vehicles: dict[str, VehicleState] = {}
        self.couriers: dict[str, CourierState] = {}
        self.orders: dict[str, OrderState] = {}
        self.waves: list[dict] = []
        self.curb_reservations: list[dict] = []
        self.metrics = Metrics()
        self.pending_ids: list[str] = []
        self.alerts_this_tick: list[dict] = []
        self._alert_last: dict[tuple[str, str | None], float] = {}
        self.orders_generated: int = 0

    # ------------------------------------------------------------- helpers
    def zone_load(self, zone_id: str | None) -> float:
        """Congestion load 0..1 for a zone based on current road occupancy."""
        if not zone_id:
            return 0.0
        zone = next((z for z in self.zones if z["id"] == zone_id), None)
        if not zone:
            return 0.0
        moving = self.vehicles_in_zone(zone_id)
        capacity = zone["road_capacity"]
        raw = moving / max(capacity, 1)
        return min(1.0, raw * self.scenario.get("congestion_multiplier", 1.0))

    # Road footprint of each unit type (a truck occupies ~3x the road of a scooter)
    ROAD_WEIGHT = {
        "truck": 3.0, "van": 2.0, "motorcycle": 1.2, "e-scooter": 0.8,
        "bicycle": 0.6, "walking": 0.4,
    }

    def vehicles_in_zone(self, zone_id: str) -> float:
        """Weighted road occupancy in a zone — heavy vehicles count more."""
        count = 0.0
        for v in self.vehicles.values():
            if v.status in ("TO_HUB", "TO_CUSTOMER") and self._zone_of_point(v.position()) == zone_id:
                count += self.ROAD_WEIGHT.get(v.type, 1.0)
        for c in self.couriers.values():
            if c.status == "DELIVERING" and self._zone_of_point(c.position()) == zone_id:
                count += self.ROAD_WEIGHT.get(c.mode, 1.0)
        return count

    def _zone_of_point(self, point: list[float]) -> str | None:
        from app.algorithms.geo import nearest_zone

        zone = nearest_zone(self.zones, point[0], point[1])
        return zone["id"] if zone else None

    def active_order_count(self) -> int:
        return sum(1 for o in self.orders.values() if o.status in ACTIVE_ORDER_STATUSES)

    def hub_utilization(self) -> float:
        hubs = [h for h in self.hubs.values() if h.get("active", True)]
        if not hubs:
            return 0.0
        return sum(h["occupied"] / max(h["capacity"], 1) for h in hubs) / len(hubs)

    def congestion_index(self) -> float:
        if not self.zones:
            return 0.0
        return sum(self.zone_load(z["id"]) for z in self.zones) / len(self.zones)

    def vehicles_on_road(self) -> int:
        return sum(1 for v in self.vehicles.values() if v.status in ("TO_HUB", "TO_CUSTOMER")) + sum(
            1 for c in self.couriers.values() if c.status == "DELIVERING"
        )

    def zone_loads(self) -> list[dict]:
        return [
            {"zone_id": z["id"], "zone_name": z["name"], "index": round(self.zone_load(z["id"]), 3)}
            for z in self.zones
        ]