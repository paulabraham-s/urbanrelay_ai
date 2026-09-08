"""Agent 4 — Curb Reservation.

Digitally reserves loading/unloading curb space for bulk vehicle arrivals.
Uses greedy interval scheduling: arrivals sorted by ETA are slotted into the
nearest curb zone with a free window; conflicts are counted when a booking has
to shift later than requested.
"""

from app.agents import AIDecisionRecord
from app.algorithms.geo import haversine_km


class CurbReservationAgent:
    def plan(
        self,
        *,
        arrivals: list[dict],   # [{vehicle_id, lat, lng, eta_min, unload_min}]
        curb_zones: list[dict],
        now_min: float,
    ) -> tuple[list[dict], int, AIDecisionRecord]:
        """Returns (reservations, conflicts, record).

        Each reservation: {curb_id, curb_name, vehicle_id, starts_at_min, ends_at_min, requested_at_min}
        """
        reservations: list[dict] = []
        conflicts = 0
        # per-curb busy intervals
        busy: dict[str, list[tuple[float, float]]] = {c["id"]: [] for c in curb_zones}

        for arrival in sorted(arrivals, key=lambda a: a["eta_min"]):
            start = arrival["eta_min"]
            end = start + arrival["unload_min"]
            chosen: dict | None = None
            chosen_start: float = start

            for curb in sorted(curb_zones, key=lambda c: haversine_km(arrival["lat"], arrival["lng"], c["lat"], c["lng"])):
                slot = self._first_free(busy[curb["id"]], start, end, curb["capacity"])
                if slot is not None:
                    chosen, chosen_start = curb, slot
                    break

            if chosen is None:
                conflicts += 1
                continue

            busy[chosen["id"]].append((chosen_start, chosen_start + (end - start)))
            if chosen_start > start + 1.0:
                conflicts += 1
            reservations.append(
                {
                    "curb_id": chosen["id"],
                    "curb_name": chosen["name"],
                    "vehicle_id": arrival["vehicle_id"],
                    "starts_at_min": round(chosen_start, 1),
                    "ends_at_min": round(chosen_start + (end - start), 1),
                    "requested_at_min": round(start, 1),
                }
            )

        record = AIDecisionRecord(
            agent="CURB_RESERVATION",
            decision=(
                f"Reserved {len(reservations)} curb slot(s) for {len(arrivals)} bulk arrivals; "
                f"{conflicts} conflict(s) shifted or missed."
            ),
            reasons=[
                {"label": f"{r['curb_name']} @ {int(r['starts_at_min'])}–{int(r['ends_at_min'])} min (vehicle {r['vehicle_id'][:8]})", "value": 0.0, "weight": 0.0}
                for r in reservations[:8]
            ],
            inputs={"arrivals": len(arrivals), "curb_zones": len(curb_zones), "now_min": now_min},
            score=round((len(arrivals) - conflicts) / max(len(arrivals), 1), 3),
            impact={"reserved": len(reservations), "conflicts": conflicts},
        )
        return reservations, conflicts, record

    @staticmethod
    def _first_free(busy: list[tuple[float, float]], start: float, end: float, capacity: int) -> float | None:
        """Earliest start time >= `start` where [s, s+duration] fits with <= capacity overlaps."""
        duration = end - start
        candidates = [start]
        for (s, e) in busy:
            candidates.append(e)  # slot after an existing booking frees up
        candidates = sorted(c for c in candidates if c >= start)
        for cand in candidates:
            overlaps = sum(1 for (s, e) in busy if s < cand + duration and cand < e)
            if overlaps < capacity:
                return cand
        return None