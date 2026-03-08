from fastapi import FastAPI, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from pymongo.errors import ConnectionFailure
from database.connection import get_db

# Routers
from routers import chat, session, watch, voice, face, stream
from websocket.eli_stream import eli_stream_endpoint

app = FastAPI(
    title="AI Voice Emergency Monitoring API",
    description="Backend for the AI Voice Emergency Monitoring System",
    version="1.0.0",
)

# CORS middleware to allow requests from the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Update this to specific frontend origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_db_client():
    # ── Seed watch data with realistic demo values ───────────────────────────
    # Uses the same WatchReading path as a real Apple Watch push, so the
    # fusion engine and frontend dashboard see plausible data immediately.
    from services.ml.watch_analysis import watch_analyzer, WatchReading
    seed = WatchReading(
        hrv          = 75.0,   # ms  — normal-to-good HRV
        heart_rate   = 78.0,   # bpm — normal resting HR
        sleep_hours  = 7.0,    # hrs — decent sleep
        sleep_quality= 70.0,   # 0-100
        steps        = 3500,
        source       = "simulated",
    )
    watch_analyzer.process(seed)
    print("[Startup] Watch data seeded with demo values ✓")

    # ── MongoDB connection check ──────────────────────────────────────────────
    try:
        db = get_db()
        db.client.admin.command("ping")
        print("Connected to the MongoDB database!")
    except ConnectionFailure:
        print("Warning: Could not connect to MongoDB. Check your MONGO_URI and network access.")
    except Exception as e:
        print(f"Warning: MongoDB startup check failed: {e}")


# Register API Routers
app.include_router(chat.router)
app.include_router(session.router)
app.include_router(watch.router)
app.include_router(voice.router)
app.include_router(face.router)
app.include_router(stream.router)

# Register WebSocket Endpoint
@app.websocket("/ws/eli")
async def websocket_eli_stream(websocket: WebSocket):
    await eli_stream_endpoint(websocket)

@app.get("/")
async def root():
    return {"message": "Welcome to the AI Voice Emergency Monitoring API", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "ok"}