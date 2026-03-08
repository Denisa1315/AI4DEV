from fastapi import FastAPI, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from pymongo.errors import ConnectionFailure
from database.connection import get_db

# Routers
from routers import chat, session, watch, voice
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
    try:
        # Verify the database connection
        db = get_db()
        # The ismaster command is cheap and does not require auth.
        db.command("ismaster")
        print("Connected to the MongoDB database!")
    except ConnectionFailure:
        print("Server not available. Could not connect to the MongoDB database.")

# Register API Routers
app.include_router(chat.router)
app.include_router(session.router)
app.include_router(watch.router)
app.include_router(voice.router)

# Register WebSocket Endpoint
@app.websocket("/ws/eli")
async def websocket_eli_stream(websocket: WebSocket):
    await eli_stream_endpoint(websocket)

@app.get("/")
async def root():
    return {"message": "Welcome to the AI Voice Emergency Monitoring API", "status": "running"}