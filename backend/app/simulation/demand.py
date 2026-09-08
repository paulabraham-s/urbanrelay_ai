"""Synthetic demand generator.

Deterministic given a seed. Demand per zone follows a realistic time-of-day
curve, scaled by the active scenario. All generated orders are explicitly
labeled SIMULATED — the platform never implies real operator integrations.
"""

import random
import uuid

from app.algorithms.geo import random_point_in_zone

PLATFORMS = ["Amazon", "Flipkart", "Blinkit", "Zepto", "Swiggy", "Local Store"]

FIRST_NAMES = [
    "Rahul", "Priya", "Amit", "Sneha", "Vikram", "Anjali", "Ravi", "Divya", "Kiran", "Pooja",
    "Suresh", "Neha", "Arjun", "Meena", "Sanjay", "Kavita", "Ramesh", "Lakshmi", "Mohan", "Deepa",
    "Naveen", "Shalini", "Prakash", "Sunita", "Anil", "Geeta", "Mahesh", "Ritu", "Srinivas", "Padma",
]
LAST_NAMES = [
    "Reddy", "Sharma", "Rao", "Iyer", "Khan", "Patel", "Gupta", "Naidu", "Verma", "Singh",
    "Kumar", "Das", "Nair", "Menon", "Joshi", "Bose", "Chowdary", "Agarwal", "Mehta", "Pillai",
]
STREET_SUFFIX = ["Main Road", "Nagar", "Colony", "Bazar", "Cross Road", "Layout", "Street", "Circle"]

VOLUME_UNITS = {"small": 1, "medium": 2, "large": 4}


def _poisson(rng: random.Random, lam: float) -> int:
    """Knuth's algorithm for a Poisson-distributed count."""
    import math

    if lam <= 0:
        return 0
    limit = math.exp(-lam)
    k, p = 0, 1.0
    while p > limit:
        k += 1
        p *= rng.random()
    return k - 1


def time_curve(hour: float) -> float:
    """Orders/hour multiplier by time of day (0.1x at night, 1.6x at 7pm)."""
    points = [(0, 0.15), (4, 0.10), (7, 0.45), (10, 1.0), (13, 1.15), (17, 1.35), (19, 1.6), (21, 1.0), (23, 0.4)]
    if hour < points[0][0] or hour >= points[-1][0]:
        hour = hour % 24
    for i in range(len(points) - 1):
        (h0, v0), (h1, v1) = points[i], points[i + 1]
        if h0 <= hour < h1:
            f = (hour - h0) / (h1 - h0)
            return v0 + (v1 - v0) * f
    return 1.0


class DemandGenerator:
    def __init__(self, rng: random.Random, zones: list[dict], scenario: dict):
        self.rng = rng
        self.zones = zones
        self.scenario = scenario
        self.counter = 0

    def orders_for(self, dt_hours: float, hour: float) -> list[dict]:
        orders: list[dict] = []
        mult = self.scenario["demand_multiplier"]
        for zone in self.zones:
            rate = zone["base_demand_rate"] * time_curve(hour) * mult
            count = _poisson(self.rng, rate * dt_hours)
            for _ in range(count):
                orders.append(self._order(zone))
        return orders

    def burst(self, total: int) -> list[dict]:
        """Warm-start burst: instantly generate `total` orders weighted by zone
        demand so the demo opens with the fleet already saturated."""
        weights = [max(z["base_demand_rate"], 1.0) for z in self.zones]
        orders: list[dict] = []
        remaining = total
        for i, zone in enumerate(self.zones):
            share = int(total * weights[i] / sum(weights))
            for _ in range(share):
                orders.append(self._order(zone))
            remaining -= share
        for _ in range(remaining):  # leftover lands on a random zone
            zone = self.rng.choices(self.zones, weights=weights, k=1)[0]
            orders.append(self._order(zone))
        return orders

    def _order(self, zone: dict) -> dict:
        lat, lng = random_point_in_zone(self.rng, zone)
        self.counter += 1
        vol_key = self._pick_volume()
        base_priority = 1 if self.rng.random() > 0.08 else 2
        priority_shift = self.scenario.get("priority_shift", 0)
        return {
            "id": str(uuid.uuid4()),
            "platform": self.rng.choice(PLATFORMS),
            "zone_id": zone["id"],
            "zone_name": zone["name"],
            "customer_lat": lat,
            "customer_lng": lng,
            "customer_name": f"{self.rng.choice(FIRST_NAMES)} {self.rng.choice(LAST_NAMES)}",
            "address": f"{self.rng.randint(1, 999)} {self.rng.choice(STREET_SUFFIX)}, {zone['name']}",
            "weight_kg": round(self.rng.uniform(0.2, 8.0), 2),
            "volume_units": VOLUME_UNITS[vol_key],
            "priority": min(5, base_priority + int(priority_shift)),
        }

    def _pick_volume(self) -> str:
        r = self.rng.random()
        if r < 0.6:
            return "small"
        if r < 0.9:
            return "medium"
        return "large"