"""Durability layer.

The simulation is authoritative in memory; this service mirrors events into
the database (orders, waves, routes, AI decisions, alerts, run summaries) so
history and analytics survive the run. Emission factors come from the DB
(seeded) with code-level defaults as fallback.

Events are buffered and flushed ONCE per tick in a single transaction —
per-event commits blocked the event loop under burst load.
"""

import logging
from datetime import datetime, timezone
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import EMISSION_FACTORS_G_PER_KM
from app.database.session import SessionLocal
from app.models.entities import (
    AIDecision,
    Alert,
    DeliveryWave,
    EmissionFactor,
    Order,
    Route,
    SimulationRun,
    MicroHub,
)

logger = logging.getLogger(__name__)

BufferedOp = Callable[[Session], None]


class PersistenceService:
    def __init__(self) -> None:
        self._factors = dict(EMISSION_FACTORS_G_PER_KM)
        self._buffer: list[BufferedOp] = []
        self._buffer_cap = 400

    # ------------------------------------------------------------- buffering
    def _queue(self, op: BufferedOp) -> None:
        self._buffer.append(op)
        if len(self._buffer) >= self._buffer_cap:
            self.flush()

    def flush(self) -> None:
        """Commit all buffered events in a single transaction."""
        if not self._buffer:
            return
        ops, self._buffer = self._buffer, []
        try:
            db = SessionLocal()
            try:
                for op in ops:
                    op(db)
                db.commit()
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()
        except Exception:  # noqa: BLE001
            logger.exception("persist flush failed (%d ops dropped)", len(ops))

    def pending(self) -> int:
        return len(self._buffer)

    # ------------------------------------------------------------- factors
    def load_factors(self) -> None:
        try:
            db = SessionLocal()
            try:
                for row in db.execute(select(EmissionFactor)).scalars():
                    self._factors[row.mode] = row.gco2_per_km
            finally:
                db.close()
        except Exception:  # noqa: BLE001
            logger.warning("could not load emission factors from DB, using defaults")

    def emission_factor(self, mode: str) -> float:
        return self._factors.get(mode, 0.0)

    # ------------------------------------------------------------- run
    def run_start(self, state) -> None:
        try:
            db = SessionLocal()
            try:
                db.add(
                    SimulationRun(
                        id=state.run_id,
                        city_id=state.city_id,
                        scenario=state.scenario["id"],
                        seed=state.seed,
                        speed=state.speed,
                        status="RUNNING",
                        started_at=datetime.now(timezone.utc),
                    )
                )
                db.commit()
            finally:
                db.close()
        except Exception:  # noqa: BLE001
            logger.exception("persist run_start failed")

    def run_end(self, state) -> None:
        self.flush()
        try:
            db = SessionLocal()
            try:
                run = db.get(SimulationRun, state.run_id)
                if run:
                    run.status = "FINISHED"
                    run.finished_at = datetime.now(timezone.utc)
                    run.orders_generated = state.orders_generated
                    run.metrics_json = {
                        "deliveries": state.metrics.deliveries,
                        "distance_km": state.metrics.distance_km,
                        "emissions_kg": state.metrics.emissions_kg,
                        "dispatches": state.metrics.dispatches,
                    }
                    db.commit()
            finally:
                db.close()
        except Exception:  # noqa: BLE001
            logger.exception("persist run_end failed")

    # ------------------------------------------------------------- orders
    def order_created(self, state, order) -> None:
        def op(db: Session) -> None:
            db.add(
                Order(
                    id=order.id,
                    city_id=state.city_id,
                    zone_id=order.zone_id,
                    platform=order.platform,
                    customer_name=order.customer_name,
                    address=order.address,
                    customer_lat=order.customer_lat,
                    customer_lng=order.customer_lng,
                    weight_kg=order.weight_kg,
                    volume_units=order.volume_units,
                    priority=order.priority,
                    status="PENDING",
                    mode=order.mode,
                )
            )

        self._queue(op)

    def _order_update(self, order_id: str, **fields) -> None:
        def op(db: Session) -> None:
            row = db.get(Order, order_id)
            if row:
                for key, value in fields.items():
                    setattr(row, key, value)

        self._queue(op)

    def order_assigned(self, state, order) -> None:
        self._order_update(
            order.id,
            status=order.status,
            mode=order.mode,
            vehicle_id=order.vehicle_id,
            courier_id=order.courier_id,
            hub_id=order.hub_id,
        )

    def order_at_hub(self, state, order) -> None:
        self._order_update(order.id, status=order.status)

    def order_delivered(self, state, order) -> None:
        self._order_update(
            order.id,
            status="DELIVERED",
            distance_km=order.distance_km,
            duration_min=order.duration_min,
            emissions_kg=order.emissions_kg,
            delivered_at=datetime.now(timezone.utc),
        )

    # ------------------------------------------------------------- waves / routes / decisions / alerts
    def wave_created(self, state, wave) -> None:
        def op(db: Session) -> None:
            db.add(
                DeliveryWave(
                    id=wave["id"],
                    zone_id=wave.get("zone_id"),
                    hub_id=wave.get("hub_id"),
                    name=wave["name"],
                    order_count=len(wave["orders"]),
                    status="ASSIGNED" if wave.get("hub_id") else "PENDING_HUB",
                    strategy="dbscan+scoring",
                )
            )

        self._queue(op)

    def route_created(self, state, veh, wave, hub, warehouse, payload_kg: float) -> None:
        def op(db: Session) -> None:
            db.add(
                Route(
                    kind="bulk",
                    mode="urbanrelay",
                    wave_id=wave["id"],
                    vehicle_id=veh.id,
                    from_lat=warehouse["lat"],
                    from_lng=warehouse["lng"],
                    to_lat=hub["lat"],
                    to_lng=hub["lng"],
                    distance_m=veh.total_m,
                    duration_min=round(veh.total_m / 1000.0 / max(veh.speed_kph, 5) * 60.0, 1),
                    cost=0.0,
                    polyline_json=veh.route,
                    status="PLANNED",
                )
            )

        self._queue(op)

    def decision(self, state, record) -> None:
        def op(db: Session) -> None:
            db.add(AIDecision(**record.to_db_dict(state.run_id)))

        self._queue(op)

    def alert(self, state, alert) -> None:
        def op(db: Session) -> None:
            db.add(
                Alert(
                    code=alert["code"],
                    severity=alert["severity"],
                    zone_id=alert["zone_id"],
                    message=f"[t+{alert['created_t']:.0f}s] {alert['message']}",
                    recommendation=alert["recommendation"],
                )
            )

        self._queue(op)

    def hub_updated(self, state, hub) -> None:
        def op(db: Session) -> None:
            row = db.get(MicroHub, hub["id"])
            if row:
                row.occupied = hub["occupied"]

        self._queue(op)
