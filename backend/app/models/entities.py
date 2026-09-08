"""SQLAlchemy models for UrbanRelay AI.

Portable schema: runs on SQLite (default, zero-setup) and PostgreSQL/PostGIS
(production mode). UUID primary keys as strings for cross-DB portability.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(32), index=True)
    full_name: Mapped[str] = mapped_column(String(128), default="")


class City(Base, TimestampMixin):
    __tablename__ = "cities"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    center_lat: Mapped[float] = mapped_column(Float, default=17.45)
    center_lng: Mapped[float] = mapped_column(Float, default=78.40)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    start_hour: Mapped[int] = mapped_column(Integer, default=7)
    zones: Mapped[list["Zone"]] = relationship(back_populates="city")


class Zone(Base, TimestampMixin):
    __tablename__ = "zones"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    city_id: Mapped[str] = mapped_column(ForeignKey("cities.id"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    code: Mapped[str] = mapped_column(String(32))
    center_lat: Mapped[float] = mapped_column(Float)
    center_lng: Mapped[float] = mapped_column(Float)
    radius_km: Mapped[float] = mapped_column(Float, default=4.0)
    base_demand_rate: Mapped[float] = mapped_column(Float, default=40.0)  # orders/hour
    road_capacity: Mapped[int] = mapped_column(Integer, default=60)  # concurrent vehicles before congestion
    color: Mapped[str] = mapped_column(String(16), default="#38bdf8")
    city: Mapped["City"] = relationship(back_populates="zones")


class MicroHub(Base, TimestampMixin):
    __tablename__ = "micro_hubs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    city_id: Mapped[str] = mapped_column(ForeignKey("cities.id"), index=True)
    zone_id: Mapped[str] = mapped_column(ForeignKey("zones.id"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    type: Mapped[str] = mapped_column(String(32), index=True)
    lat: Mapped[float] = mapped_column(Float, index=True)
    lng: Mapped[float] = mapped_column(Float, index=True)
    capacity: Mapped[int] = mapped_column(Integer, default=100)
    occupied: Mapped[int] = mapped_column(Integer, default=0)
    operating_start: Mapped[int] = mapped_column(Integer, default=8)   # hour (0-23)
    operating_end: Mapped[int] = mapped_column(Integer, default=22)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    accessibility: Mapped[float] = mapped_column(Float, default=0.8)  # 0..1 road accessibility
    address: Mapped[str] = mapped_column(String(256), default="")
    owner_name: Mapped[str] = mapped_column(String(128), default="")
    earnings: Mapped[float] = mapped_column(Float, default=0.0)


class Order(Base, TimestampMixin):
    __tablename__ = "orders"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    city_id: Mapped[str] = mapped_column(ForeignKey("cities.id"), index=True)
    zone_id: Mapped[str] = mapped_column(ForeignKey("zones.id"), index=True)
    platform: Mapped[str] = mapped_column(String(64), default="SIMULATED")
    customer_name: Mapped[str] = mapped_column(String(128), default="")
    address: Mapped[str] = mapped_column(String(256), default="")
    customer_lat: Mapped[float] = mapped_column(Float, index=True)
    customer_lng: Mapped[float] = mapped_column(Float, index=True)
    weight_kg: Mapped[float] = mapped_column(Float, default=1.0)
    volume_units: Mapped[int] = mapped_column(Integer, default=1)
    priority: Mapped[int] = mapped_column(Integer, default=1)  # 1 normal .. 5 emergency
    delivery_window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True)
    mode: Mapped[str] = mapped_column(String(32), default="baseline", index=True)
    wave_id: Mapped[str | None] = mapped_column(ForeignKey("delivery_waves.id"), nullable=True, index=True)
    hub_id: Mapped[str | None] = mapped_column(ForeignKey("micro_hubs.id"), nullable=True, index=True)
    vehicle_id: Mapped[str | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    courier_id: Mapped[str | None] = mapped_column(ForeignKey("couriers.id"), nullable=True)
    distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    emissions_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DeliveryWave(Base, TimestampMixin):
    __tablename__ = "delivery_waves"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(64))
    zone_id: Mapped[str] = mapped_column(ForeignKey("zones.id"), index=True)
    hub_id: Mapped[str | None] = mapped_column(ForeignKey("micro_hubs.id"), nullable=True, index=True)
    window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    order_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="ASSIGNED")
    strategy: Mapped[str] = mapped_column(String(64), default="dbscan+scoring")


class Vehicle(Base, TimestampMixin):
    __tablename__ = "vehicles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    city_id: Mapped[str] = mapped_column(ForeignKey("cities.id"), index=True)
    zone_id: Mapped[str | None] = mapped_column(ForeignKey("zones.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(64))
    type: Mapped[str] = mapped_column(String(32), index=True)
    capacity: Mapped[int] = mapped_column(Integer)
    speed_kph: Mapped[float] = mapped_column(Float)
    lat: Mapped[float] = mapped_column(Float, index=True)
    lng: Mapped[float] = mapped_column(Float, index=True)
    status: Mapped[str] = mapped_column(String(32), default="IDLE", index=True)
    battery: Mapped[float] = mapped_column(Float, default=100.0)
    cargo_count: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Courier(Base, TimestampMixin):
    __tablename__ = "couriers"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    city_id: Mapped[str] = mapped_column(ForeignKey("cities.id"), index=True)
    zone_id: Mapped[str | None] = mapped_column(ForeignKey("zones.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    mode: Mapped[str] = mapped_column(String(32), index=True)
    capacity: Mapped[int] = mapped_column(Integer, default=6)
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(32), default="AVAILABLE")
    earnings: Mapped[float] = mapped_column(Float, default=0.0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class CurbZone(Base, TimestampMixin):
    __tablename__ = "curb_zones"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    city_id: Mapped[str] = mapped_column(ForeignKey("cities.id"), index=True)
    zone_id: Mapped[str] = mapped_column(ForeignKey("zones.id"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    capacity: Mapped[int] = mapped_column(Integer, default=2)
    operating_start: Mapped[int] = mapped_column(Integer, default=8)
    operating_end: Mapped[int] = mapped_column(Integer, default=22)


class CurbReservation(Base, TimestampMixin):
    __tablename__ = "curb_reservations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    curb_id: Mapped[str] = mapped_column(ForeignKey("curb_zones.id"), index=True)
    vehicle_id: Mapped[str | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), default="BOOKED")


class Route(Base, TimestampMixin):
    __tablename__ = "routes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    kind: Mapped[str] = mapped_column(String(32), index=True)  # bulk | lastmile | baseline
    mode: Mapped[str] = mapped_column(String(32), index=True)
    order_id: Mapped[str | None] = mapped_column(ForeignKey("orders.id"), nullable=True, index=True)
    wave_id: Mapped[str | None] = mapped_column(ForeignKey("delivery_waves.id"), nullable=True, index=True)
    vehicle_id: Mapped[str | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    courier_id: Mapped[str | None] = mapped_column(ForeignKey("couriers.id"), nullable=True)
    from_lat: Mapped[float] = mapped_column(Float)
    from_lng: Mapped[float] = mapped_column(Float)
    to_lat: Mapped[float] = mapped_column(Float)
    to_lng: Mapped[float] = mapped_column(Float)
    distance_m: Mapped[float] = mapped_column(Float)
    duration_min: Mapped[float] = mapped_column(Float)
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    polyline_json: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(32), default="PLANNED")


class AIDecision(Base, TimestampMixin):
    __tablename__ = "ai_decisions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    agent: Mapped[str] = mapped_column(String(64), index=True)
    run_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    decision: Mapped[str] = mapped_column(Text)
    reasons: Mapped[list] = mapped_column(JSON, default=list)
    inputs: Mapped[dict] = mapped_column(JSON, default=dict)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    impact: Mapped[dict] = mapped_column(JSON, default=dict)


class Alert(Base, TimestampMixin):
    __tablename__ = "alerts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String(64), index=True)
    severity: Mapped[str] = mapped_column(String(16), index=True)  # INFO | WARNING | CRITICAL
    zone_id: Mapped[str | None] = mapped_column(ForeignKey("zones.id"), nullable=True, index=True)
    message: Mapped[str] = mapped_column(Text)
    recommendation: Mapped[str] = mapped_column(Text, default="")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SimulationRun(Base, TimestampMixin):
    __tablename__ = "simulation_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    city_id: Mapped[str | None] = mapped_column(ForeignKey("cities.id"), nullable=True)
    scenario: Mapped[str] = mapped_column(String(64), default="NORMAL_DAY")
    seed: Mapped[int] = mapped_column(Integer, default=42)
    speed: Mapped[float] = mapped_column(Float, default=1.0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="RUNNING")
    orders_generated: Mapped[int] = mapped_column(Integer, default=0)
    metrics_json: Mapped[dict] = mapped_column(JSON, default=dict)


class EmissionFactor(Base, TimestampMixin):
    __tablename__ = "emission_factors"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    mode: Mapped[str] = mapped_column(String(32), unique=True)
    gco2_per_km: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(256), default="Configured estimate")


class Setting(Base, TimestampMixin):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")