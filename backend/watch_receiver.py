# watch_receiver.py
# Run with: uvicorn watch_receiver:app --host 0.0.0.0 --port 5001
#
# This is the public-facing receiver for Apple Watch / smartwatch webhooks.
# It forwards all data to the main backend (port 8000) so the WebSocket ELI
# loop's watch_analyzer singleton gets updated and the data appears in the
# frontend dashboard.
#
# Why forward instead of direct import?
#   watch_receiver runs as a SEPARATE process (port 5001). Python module
#   singletons are per-process, so directly calling watch_analyzer.process()
#   here would update a different object from the one the ELI WebSocket reads.

import sys, os, socket
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

# Main backend URL — update if running on a different host
MAIN_BACKEND = os.environ.get("MAIN_BACKEND_URL", "http://127.0.0.1:8000")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _forward(path: str, payload: dict) -> dict:
    """Forward a watch payload to the main backend and return its response."""
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.post(f"{MAIN_BACKEND}{path}", json=payload)
        r.raise_for_status()
        return r.json()


@app.post("/api/watch/apple")
async def receive_apple_watch(payload: dict):
    print(f"\n[Watch] Received: {payload}")
    try:
        result = await _forward("/api/watch/apple", payload)
        print(f"[Watch] Forwarded → physio_score={result.get('physio_score', '?'):.1f} "
              f"hrv={result.get('hrv')} hr={result.get('heart_rate')}")
        return result
    except Exception as e:
        print(f"[Watch] Forward failed: {e}")
        return {"error": str(e)}


@app.post("/api/watch/samsung")
async def receive_samsung(payload: dict):
    return await _forward("/api/watch/samsung", payload)


@app.post("/api/watch/generic")
async def receive_generic(payload: dict):
    return await _forward("/api/watch/generic", payload)


@app.get("/api/watch/status")
async def watch_status():
    """Check what the main backend's watch_analyzer currently holds."""
    try:
        return await _forward("/api/watch/status", {})
    except Exception as e:
        return {"error": str(e)}


@app.on_event("startup")
async def startup():
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = "unknown"
    print(f"\n{'='*50}")
    print(f"  Watch Receiver Running  (port 5001)")
    print(f"  Forwards to: {MAIN_BACKEND}")
    print(f"  Apple Shortcuts URL:")
    print(f"  http://{local_ip}:5001/api/watch/apple")
    print(f"{'='*50}\n")