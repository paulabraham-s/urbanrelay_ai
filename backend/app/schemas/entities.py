"""Response schemas for database-backed entities."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CityOut(ORMModel):
    id: str
    name: str
    code: str
    center_lat: float
    center_lng: float
    active: bool


class ZoneOut(ORMModel):
    id: str
    city_id: str
    name: str
    code: str
    center_lat: float
    center_lng: float
    radius_km: float
    base_demand_rate: float
    road_capacity: int
    color: str


class HubOut(ORMModel):
    id: str
    city_id: str
    zone_id: str | None
    name: str
    type: str
    lat: float
    lng: float
    capacity: int
    occupied: int
    operating_start: int
    operating_end: int
    active: bool
    accessibility: float
    address: str
    owner_name: str


class OrderOut(ORMModel):
    id: str
    city_id: str | None
    zone_id: str | None
    platform: str
    customer_name: str
    address: str
    customer_lat: float
    customer_lng: float
    weight_kg: float
    volume_units: int
    priority: int
    status: str
    mode: str
    hub_id: str | None
    vehicle_id: str | None
    courier_id: str | None
    distance_km: float | None
    duration_min: float | None
    emissions_kg: float | None
    created_at: datetime


class VehicleOut(ORMModel):
    id: str
    name: str
    type: str
    capacity: int
    speed_kph: float
    status: str
    battery: float
    active: bool


class CourierOut(ORMModel):
    id: str
    name: str
    mode: str
    capacity: int
    status: str
    earnings: float
    active: bool


class CurbZoneOut(ORMModel):
    id: str
    city_id: str
    zone_id: str | None
    name: str
    lat: float
    lng: float
    capacity: int


class AlertOut(ORMModel):
    id: str
    code: str
    severity: str
    zone_id: str | None
    message: str
    recommendation: str
    resolved_at: datetime | None
    created_at: datetime


class AIDecisionOut(ORMModel):
    id: str
    agent: str
    run_id: str | None
    decision: str
    reasons: list
    inputs: dict
    score: float
    impact: dict
    created_at: datetime


class WaveOut(ORMModel):
    id: str
    zone_id: str | None
    hub_id: str | None
    name: str
    order_count: int
    status: str
    strategy: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str
    full_name: str