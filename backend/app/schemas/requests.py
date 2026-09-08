"""Request schemas (Pydantic v2)."""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str | None = None
    password: str | None = None
    demo: bool = False


class StartRequest(BaseModel):
    scenario_id: str = "FESTIVAL_SALE"
    seed: int = 42
    speed: float = 1.0
    burst: int = 0  # warm-start: instant orders so short demos open mid-rush


class ScenarioRequest(BaseModel):
    scenario_id: str = "NORMAL_DAY"
    mode: str | None = None


class SpeedRequest(BaseModel):
    speed: float = Field(1.0, ge=0.1, le=20.0)


class ModeRequest(BaseModel):
    mode: str = "urbanrelay"


class OptimizeRequest(BaseModel):
    order_ids: list[str] | None = None


class OrderCreateRequest(BaseModel):
    platform: str = "Local Store"
    customer_lat: float
    customer_lng: float
    zone_id: str | None = None
    weight_kg: float = 1.0
    volume_units: int = 1
    priority: int = 1


class HubUpdateRequest(BaseModel):
    capacity: int | None = None
    active: bool | None = None
    operating_start: int | None = Field(None, ge=0, le=23)
    operating_end: int | None = Field(None, ge=0, le=23)


class HubReserveRequest(BaseModel):
    slots: int = Field(1, ge=1)


class ReserveCurbRequest(BaseModel):
    lat: float
    lng: float
    eta_min: float
    unload_min: float = 8.0
    vehicle_label: str = "Manual booking"


class RouteOptimizeRequest(BaseModel):
    from_lat: float
    from_lng: float
    to_lat: float
    to_lng: float
    vehicle_type: str = "van"
    speed_kph: float | None = None
    algorithm: str = "dijkstra"


class ResolveAlertRequest(BaseModel):
    resolved: bool = True