from fastapi import APIRouter
from services.ml.baseline_model import baseline_model
from services.ml.watch_analysis import watch_analyzer
from services.ml.fusion_engine  import fusion_engine, SignalInput
import datetime

router = APIRouter(prefix="/api/session")

@router.post("/start")
async def start_session(body: dict):
    user_id  = body.get("user_id", "demo_user")
    watch    = watch_analyzer.to_dict()

    # Get personalised opening context from Dev 1's baseline model
    context = baseline_model.get_session_opening_context(
        user_id     = user_id,
        current_eli = body.get("current_eli", 50),
        current_hrv = watch.get("hrv"),
        sleep_hours = watch.get("sleep_hours"),
        day_of_week = datetime.datetime.now().strftime("%A"),
    )

    return {
        "session_id":  f"session_{int(__import__('time').time())}",
        "user_id":     user_id,
        "context":     context,
        "started_at":  __import__("time").time(),
    }

@router.post("/end")
async def end_session(body: dict):
    start_eli = body.get("start_eli", 50)
    end_eli   = body.get("end_eli",   50)
    duration  = body.get("duration_minutes", 0)

    improvement = start_eli - end_eli

    return {
        "start_eli":   start_eli,
        "end_eli":     end_eli,
        "improvement": round(improvement, 1),
        "message":     _session_summary(start_eli, end_eli, improvement),
        "duration":    duration,
    }

def _session_summary(start, end, improvement):
    if improvement > 15:
        return f"Great session — your stress reduced from {start:.0f} to {end:.0f}. Keep it up."
    elif improvement > 5:
        return f"Good progress — slight improvement from {start:.0f} to {end:.0f}."
    elif improvement < -10:
        return f"Tough session — ELI rose from {start:.0f} to {end:.0f}. That's okay, tomorrow is a new day."
    else:
        return f"Session complete. ELI: {start:.0f} → {end:.0f}."