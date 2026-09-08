from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_sim_service
from app.core.security import require_auth
from app.schemas.requests import ModeRequest, ScenarioRequest, SpeedRequest, StartRequest
from app.simulation.scenarios import SCENARIOS

router = APIRouter(prefix="/api/simulation", tags=["simulation"])


@router.get("/scenarios")
def scenarios() -> dict:
    return {"scenarios": list(SCENARIOS.values())}


@router.get("/status")
def status(sim=Depends(get_sim_service)) -> dict:
    return sim.status()


@router.post("/start")
async def start(req: StartRequest, claims=Depends(require_auth), sim=Depends(get_sim_service)):
    try:
        return await sim.start(req.scenario_id, req.seed, req.speed, req.burst)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/stop")
async def stop(claims=Depends(require_auth), sim=Depends(get_sim_service)):
    return await sim.stop()


@router.post("/reset")
def reset(claims=Depends(require_auth), sim=Depends(get_sim_service)):
    return sim.reset()


@router.post("/scenario")
def scenario(req: ScenarioRequest, claims=Depends(require_auth), sim=Depends(get_sim_service)):
    if req.scenario_id not in SCENARIOS:
        raise HTTPException(status_code=422, detail=f"Unknown scenario {req.scenario_id}")
    return sim.set_scenario_and_mode(req.scenario_id, req.mode)


@router.post("/speed")
def speed(req: SpeedRequest, claims=Depends(require_auth), sim=Depends(get_sim_service)):
    return sim.set_speed(req.speed)


@router.post("/activate")
def activate(req: ModeRequest, claims=Depends(require_auth), sim=Depends(get_sim_service)):
    if not sim.state.running:
        raise HTTPException(status_code=409, detail="Start the simulation first")
    return sim.set_mode(req.mode)


@router.get("/state")
def state(sim=Depends(get_sim_service)) -> dict:
    return sim.snapshot()


@router.get("/kpis")
def kpis(sim=Depends(get_sim_service)) -> dict:
    return sim.kpis()


@router.get("/before-after")
def before_after(sim=Depends(get_sim_service)) -> dict:
    return sim.before_after()


@router.get("/history")
def history(limit: int = Query(600, ge=10, le=4000), sim=Depends(get_sim_service)) -> dict:
    return {"history": sim.history(limit)}


@router.get("/recommendations")
def recommendations(sim=Depends(get_sim_service)) -> dict:
    return {"recommendations": sim.recommendations()}


@router.get("/optimizations")
def optimizations(sim=Depends(get_sim_service)) -> dict:
    return {"last_optimization": sim.last_optimization()}