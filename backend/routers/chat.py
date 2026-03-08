from fastapi import APIRouter
from services.agents.therapy_router import route_therapy
from services.ml.fusion_engine import fusion_engine
from services.ml.voice_analysis import voice_analyzer

router = APIRouter(prefix="/api")

@router.post("/chat")
async def chat(body: dict):
    message     = body.get("message", "")
    eli_payload = body.get("eli_payload", {})
    voice_data  = voice_analyzer.to_dict()

    response = route_therapy(eli_payload, voice_data)

    return {
        "response":  response,
        "timestamp": __import__("time").time()
    }