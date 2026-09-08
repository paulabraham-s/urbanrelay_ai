"""Agent 2 — Delivery Wave.

Groups pending orders into geographic waves with DBSCAN (haversine distance).
Each wave shares one bulk leg (warehouse -> hub) and then fans out to nearby
customers, so one vehicle replaces many duplicated trips.
"""

from app.agents import AIDecisionRecord
from app.algorithms.clustering import cluster_centroid, dbscan
from app.algorithms.geo import nearest_zone

DEFAULT_EPS_M = 1200.0
DEFAULT_MIN_PTS = 3


class DeliveryWaveAgent:
    def __init__(self, eps_m: float = DEFAULT_EPS_M, min_pts: int = DEFAULT_MIN_PTS):
        self.eps_m = eps_m
        self.min_pts = min_pts

    def build_waves(self, orders: list[dict], zones: list[dict], alphabet: list[str] | None = None) -> tuple[list[dict], AIDecisionRecord]:
        """Cluster orders -> (waves, decision_record).

        Each wave: {id, name, zone_id, orders: [order dicts], centroid, total_slots,
        priority_max, created_min, created_max, noise}
        """
        alphabet = alphabet or list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        if not orders:
            record = AIDecisionRecord(
                agent="DELIVERY_WAVE",
                decision="No pending orders to cluster.",
                inputs={"orders": 0},
                score=1.0,
                impact={"waves": 0},
            )
            return [], record

        points = [(o["customer_lat"], o["customer_lng"]) for o in orders]
        labels = dbscan(points, self.eps_m, self.min_pts)

        by_cluster: dict[int, list[int]] = {}
        for idx, lab in enumerate(labels):
            by_cluster.setdefault(lab, []).append(idx)

        waves: list[dict] = []
        wave_idx = 0
        for cluster_id in sorted(by_cluster, key=lambda c: len(by_cluster[c]), reverse=True):
            members = [orders[i] for i in by_cluster[cluster_id]]
            centroid = cluster_centroid(points, labels, cluster_id)
            zone = nearest_zone(zones, centroid[0], centroid[1]) if centroid else None
            waves.append(
                {
                    "id": f"W{wave_idx + 1}",
                    "name": f"Wave {alphabet[wave_idx % len(alphabet)]}",
                    "zone_id": zone["id"] if zone else None,
                    "zone_name": zone["name"] if zone else "Unknown",
                    "orders": members,
                    "order_ids": [o["id"] for o in members],
                    "centroid": [centroid[0], centroid[1]] if centroid else None,
                    "total_slots": sum(o["volume_units"] for o in members),
                    "priority_max": max(o.get("priority", 1) for o in members),
                    "noise": cluster_id == -1,
                }
            )
            wave_idx += 1

        clustered = sum(1 for w in waves if not w["noise"])
        record = AIDecisionRecord(
            agent="DELIVERY_WAVE",
            decision=(
                f"Clustered {len(orders)} pending orders into {len(waves)} delivery waves "
                f"({clustered} consolidated, {len(waves) - clustered} singles) using DBSCAN "
                f"with {self.eps_m:.0f} m radius."
            ),
            reasons=[
                {"label": f"Wave {w['name']} — {w['zone_name']}", "value": w["total_slots"], "weight": 0.0}
                for w in waves[:8]
            ],
            inputs={"orders": len(orders), "eps_m": self.eps_m, "min_pts": self.min_pts},
            score=round(clustered / max(len(waves), 1), 3),
            impact={
                "waves": len(waves),
                "consolidated": clustered,
                "single_orders": len(waves) - clustered,
                "orders": len(orders),
            },
        )
        return waves, record