"""Agent 3 — Fleet Balancer.

Assigns bulk vehicles (truck/van) to delivery waves and last-mile couriers to
individual orders, then rebalances idle vehicles between zones to avoid
vehicle duplication and protect roads from over-concentration.
"""

from app.agents import AIDecisionRecord
from app.algorithms.geo import haversine_km

BULK_TYPES = ("truck", "van")
LAST_MILE_TYPES = ("motorcycle", "e-scooter", "bicycle", "walking")


class FleetBalancerAgent:
    def allocate(
        self,
        *,
        waves: list[dict],
        vehicles: list[dict],
        couriers: list[dict],
        zone_load_fn=None,
    ) -> tuple[dict, AIDecisionRecord]:
        """Returns (plan, record).

        plan = {
          "bulk_assignments": [{wave_id, vehicle_id, order_ids, vehicle_type}],
          "courier_assignments": [{order_id, courier_id, courier_mode, wave_id}],
          "rebalance_actions": [str],
          "unassigned_order_ids": [str],
        }
        """
        available_vehicles = [
            v for v in vehicles if v.get("status") == "IDLE" and v.get("active", True)
        ]
        available_couriers = [
            c for c in couriers if c.get("status") == "AVAILABLE" and c.get("active", True)
        ]

        bulk_assignments: list[dict] = []
        courier_assignments: list[dict] = []
        unassigned: list[str] = []

        for wave in sorted(waves, key=lambda w: w["priority_max"], reverse=True):
            centroid = wave["centroid"]
            remaining = wave["total_slots"]
            wave_orders = list(wave["orders"])

            # 1) bulk leg: assign bulk vehicle(s) until the wave's volume fits;
            #    orders are partitioned across vehicles so nothing is duplicated
            used_vehicle_ids: set[str] = set()
            while remaining > 0 and wave_orders:
                candidate = None
                for v in sorted(available_vehicles, key=lambda v: haversine_km(centroid[0], centroid[1], v["lat"], v["lng"])):
                    if v["id"] in used_vehicle_ids:
                        continue
                    if v["type"] in BULK_TYPES and v["capacity"] > 0:
                        candidate = v
                        break
                if candidate is None:
                    break
                used_vehicle_ids.add(candidate["id"])
                load = min(candidate["capacity"], remaining)
                taken = [o["id"] for o in wave_orders[:load]]
                wave_orders = wave_orders[load:]
                bulk_assignments.append(
                    {
                        "wave_id": wave["id"],
                        "vehicle_id": candidate["id"],
                        "vehicle_type": candidate["type"],
                        "load": load,
                        "order_ids": taken,
                    }
                )
                remaining -= load

            # 2) last mile: PACK nearby orders onto shared couriers (multi-drop).
            #    Each courier carries several orders from the same wave to nearby
            #    customers — this is where per-delivery vehicle count collapses.
            remaining_capacity = {c["id"]: c["capacity"] for c in available_couriers}
            for order in sorted(wave["orders"], key=lambda o: -o.get("priority", 1)):
                slot_needed = order["volume_units"]
                courier = None
                # prefer a courier already loaded with orders from this wave (same hub),
                # then the nearest free courier
                candidates = sorted(
                    available_couriers,
                    key=lambda c: (
                        0 if c["id"] in {a["courier_id"] for a in courier_assignments if a["wave_id"] == wave["id"]} else 1,
                        haversine_km(centroid[0], centroid[1], c["lat"], c["lng"]),
                    ),
                )
                for c in candidates:
                    if remaining_capacity.get(c["id"], 0) >= slot_needed:
                        courier = c
                        break
                if courier is None:
                    unassigned.append(order["id"])
                    continue
                remaining_capacity[courier["id"]] -= slot_needed
                courier_assignments.append(
                    {
                        "order_id": order["id"],
                        "courier_id": courier["id"],
                        "courier_mode": courier["mode"],
                        "wave_id": wave["id"],
                    }
                )

        # 3) zone rebalancing of idle vehicles (keeps road concentration balanced)
        rebalance_actions: list[str] = []
        if zone_load_fn is not None:
            rebalance_actions = self._rebalance(available_vehicles, zone_load_fn)

        record = AIDecisionRecord(
            agent="FLEET_BALANCER",
            decision=(
                f"Allocated {len(bulk_assignments)} bulk vehicle(s) for {len(waves)} waves "
                f"and {len(courier_assignments)} last-mile couriers; "
                f"{len(unassigned)} orders wait for capacity."
            ),
            reasons=[
                {"label": f"Bulk {a['vehicle_type']} → wave {a['wave_id']} ({a['load']} parcels)", "value": 0.0, "weight": 0.0}
                for a in bulk_assignments[:6]
            ]
            + [
                {"label": f"{a['courier_mode']} courier → order {a['order_id'][:8]}", "value": 0.0, "weight": 0.0}
                for a in courier_assignments[:6]
            ],
            inputs={"waves": len(waves), "vehicles_available": len(available_vehicles), "couriers_available": len(available_couriers)},
            score=round(len(courier_assignments) / max(len([o for w in waves for o in w["orders"]]), 1), 3),
            impact={
                "bulk_vehicles": len(bulk_assignments),
                "couriers": len(courier_assignments),
                "unassigned": len(unassigned),
                "rebalance_actions": rebalance_actions,
            },
        )
        return (
            {
                "bulk_assignments": bulk_assignments,
                "courier_assignments": courier_assignments,
                "rebalance_actions": rebalance_actions,
                "unassigned_order_ids": unassigned,
            },
            record,
        )

    @staticmethod
    def _rebalance(vehicles: list[dict], zone_load_fn) -> list[str]:
        from collections import defaultdict

        counts: dict[str, int] = defaultdict(int)
        for v in vehicles:
            if v.get("zone_id"):
                counts[v["zone_id"]] += 1
        zones = list({v.get("zone_id") for v in vehicles if v.get("zone_id")})
        loads = {z: zone_load_fn(z) for z in zones}
        overloaded = [z for z in zones if loads.get(z, 0) > 0.8 and counts.get(z, 0) > 1]
        underloaded = [z for z in zones if loads.get(z, 0) < 0.5]
        actions: list[str] = []
        for z_high in overloaded:
            for z_low in underloaded:
                if z_high == z_low:
                    continue
                move = min(counts[z_high] - 1, max(0, int((0.5 - loads[z_low]) * 10)), 3)
                if move > 0:
                    actions.append(f"Move {move} idle vehicle(s) from zone {z_high} to {z_low}")
                    counts[z_high] -= move
                    counts[z_low] += move
        return actions