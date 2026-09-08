from app.core.constants import EMISSION_FACTORS_G_PER_KM
from app.services.persistence import PersistenceService


def test_default_factors_present():
    for mode in ("truck", "van", "motorcycle", "e-scooter", "bicycle", "walking"):
        assert mode in EMISSION_FACTORS_G_PER_KM
    assert EMISSION_FACTORS_G_PER_KM["bicycle"] == 0.0
    assert EMISSION_FACTORS_G_PER_KM["truck"] > EMISSION_FACTORS_G_PER_KM["e-scooter"]


def test_persistence_factors_from_db():
    ps = PersistenceService()
    ps.load_factors()
    truck = ps.emission_factor("truck")
    assert truck > 0
    assert ps.emission_factor("unknown-mode") == 0.0


def test_emission_calculation_shape():
    ps = PersistenceService()
    ps.load_factors()
    # 10 km by truck
    kg = ps.emission_factor("truck") * 10.0 / 1000.0
    assert kg == 6.2