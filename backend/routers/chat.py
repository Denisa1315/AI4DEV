from fastapi import APIRouter
from services.agents.therapy_router import route
import time

router = APIRouter(prefix="/api")

@router.post("/chat")
async def chat(body: dict):
    eli_payload = body.get("eli_payload", {})

    # If the caller provided a top-level message, inject it as the transcript
    # so the therapy router can use it even without a running WebSocket session.
    message = body.get("message", "").strip()
    if message and not eli_payload.get("transcript"):
        eli_payload["transcript"] = message

    result = route(eli_payload)

    # `result` is a dict with keys: response, agent, emotion, eli, transcript_heard
    # The frontend reads: data.response, data.therapy_mode, data.contradiction_detected
    return {
        "response":               result.get("response", ""),
        "therapy_mode":           result.get("agent", "supportive"),   # frontend key
        "agent":                  result.get("agent", "supportive"),   # backend key (keep both)
        "emotion":                result.get("emotion", "neutral"),
        "eli":                    result.get("eli", 50),
        "contradiction_detected": eli_payload.get("contradiction_detected", False),
        "show_resources":         result.get("show_resources", False),
        "resources":              result.get("resources", {}),
        "timestamp":              time.time(),
    }