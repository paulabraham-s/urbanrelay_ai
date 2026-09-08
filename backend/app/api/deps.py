"""Shared FastAPI dependencies."""

from app.services.sim_service import SimulationService

sim_service = SimulationService()


def get_sim_service() -> SimulationService:
    return sim_service