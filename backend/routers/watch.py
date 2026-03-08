from fastapi import APIRouter
from services.ml.watch_analysis import watch_analyzer

router = APIRouter(prefix="/api/watch")

@router.post("/apple")
async def receive_apple_watch(payload: dict):
    reading = watch_analyzer.parse_apple_watch(payload)
    result  = watch_analyzer.process(reading)
    return watch_analyzer.to_dict()

@router.post("/samsung")
async def receive_samsung(payload: dict):
    reading = watch_analyzer.parse_samsung(payload)
    result  = watch_analyzer.process(reading)
    return watch_analyzer.to_dict()

@router.post("/generic")
async def receive_generic(payload: dict):
    reading = watch_analyzer.parse_generic(payload)
    result  = watch_analyzer.process(reading)
    return watch_analyzer.to_dict()

@router.post("/simulate/{scenario}")
async def simulate_watch(scenario: str):
    result = watch_analyzer.simulate_and_process(scenario)
    return watch_analyzer.to_dict()