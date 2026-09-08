"""Agent 1 — Hub Selection.

Scores candidate micro-hubs for a delivery wave with an interpretable weighted
model:

    HubScore = w1*distance + w2*capacity + w3*congestion
             + w4*accessibility + w5*utilization + w6*operating

All components normalized to [0,1] (higher = better). Weights configurable.
"""

from app.agents import AIDecisionRecord
from app.algorithms.geo import haversine_km
from app.algorithms.scoring import clamp01, normalize, weighted_score

DEFAULT_WEIGHTS = {
    "distance": 0.30,
    "capacity": 0.25,
    "congestion": 0.15,
    "accessibility": 0.10,
    "utilization": 0.10,
    "operating": 0.10,
}

LABELS = {
    "distance": "Distance from wave centroid",
    "capacity": "Free capacity",
    "congestion": "Low zone congestion",
    "accessibility": "Road accessibility",
    "utilization": "Balanced utilization",
    "operating": "Open now",
}

MAX_REASONABLE_DISTANCE_KM = 6.0


class HubSelectionAgent:
    def __init__(self, weights: dict[str, float] | None = None):
        self.weights = dict(DEFAULT_WEIGHTS if weights is None else weights)

    def select_hub(
        self,
        *,
        centroid_lat: float,
        centroid_lng: float,
        required_slots: int,
        hubs: list[dict],
        zone_load_fn,
        now_hour: int,
    ) -> tuple[dict, AIDecisionRecord]:
        """Pick the best hub for a wave. Returns (hub, decision_record)."""
        best_hub: dict | None = None
        best_score = -1.0
        best_components: dict[str, float] = {}
        considered: list[dict] = []

        for hub in hubs:
            if not hub.get("active", True):
                continue
            remaining = hub["capacity"] - hub["occupied"]
            d_km = haversine_km(centroid_lat, centroid_lng, hub["lat"], hub["lng"])
            if d_km > MAX_REASONABLE_DISTANCE_KM:
                continue
            hour_open = hub["operating_start"] <= now_hour < hub["operating_end"]
            zone_load = zone_load_fn(hub.get("zone_id"))
            components = {
                "distance": normalize(d_km, 0, MAX_REASONABLE_DISTANCE_KM, higher_better=False),
                "capacity": clamp01(remaining / max(hub["capacity"], 1)),
                "congestion": 1.0 - clamp01(zone_load),
                "accessibility": clamp01(hub.get("accessibility", 0.8)),
                "utilization": 1.0 - clamp01(hub["occupied"] / max(hub["capacity"], 1)),
                "operating": 1.0 if hour_open else 0.0,
            }
            if remaining < required_slots:
                components["capacity"] = 0.0
            score, reasons = weighted_score(components, self.weights, LABELS.get)
            considered.append(
                {"hub": hub, "score": score, "components": components, "reasons": reasons, "remaining": remaining, "d_km": d_km}
            )
            if score > best_score:
                best_score, best_hub, best_components = score, hub, components

        if best_hub is None:
            record = AIDecisionRecord(
                agent="HUB_SELECTION",
                decision="No feasible hub found for this wave — keeping orders pending.",
                reasons=[{"label": "All hubs full, closed, or beyond reach", "value": 0.0}],
                inputs={"centroid_lat": centroid_lat, "centroid_lng": centroid_lng, "required_slots": required_slots},
                score=0.0,
                impact={"orders_affected": 0},
            )
            return {}, record

        _, reasons = weighted_score(best_components, self.weights, LABELS.get)
        remaining = best_hub["capacity"] - best_hub["occupied"]
        reason_text = (
            f"Hub {best_hub['name']} selected with score {best_score:.2f}: "
            f"{remaining} free slots, {haversine_km(centroid_lat, centroid_lng, best_hub['lat'], best_hub['lng']):.1f} km "
            f"from wave centroid, zone congestion {1.0 - best_components['congestion']:.0%}."
        )
        record = AIDecisionRecord(
            agent="HUB_SELECTION",
            decision=reason_text,
            reasons=reasons,
            inputs={
                "centroid_lat": centroid_lat,
                "centroid_lng": centroid_lng,
                "required_slots": required_slots,
                "candidates": len(considered),
            },
            score=best_score,
            impact={
                "hub_id": best_hub["id"],
                "hub_name": best_hub["name"],
                "free_slots_after": remaining - required_slots,
                "expected_orders": required_slots,
            },
        )
        return best_hub, record