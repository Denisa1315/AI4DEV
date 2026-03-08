from fastapi import WebSocket
from services.ml.facial_analysis import facial_analyzer
from services.ml.voice_analysis   import voice_analyzer
from services.ml.watch_analysis   import watch_analyzer
from services.ml.fusion_engine    import fusion_engine, SignalInput
from services.ml.baseline_model   import baseline_model
import asyncio, json

async def eli_stream_endpoint(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            # Read all Dev 1 modules
            facial  = facial_analyzer.to_dict()
            voice   = voice_analyzer.to_dict()
            watch   = watch_analyzer.to_dict()

            # Get typing score from frontend message if available
            typing_score = None
            try:
                msg = await asyncio.wait_for(
                    websocket.receive_text(), timeout=0.1
                )
                data = json.loads(msg)
                typing_score = data.get("typing_score")
            except asyncio.TimeoutError:
                pass

            # Fuse all signals
            eli_result = fusion_engine.calculate(SignalInput(
                physio_score           = watch.get("physio_score"),
                facial_score           = facial.get("distress_score"),
                voice_score            = voice.get("combined_score"),
                typing_score           = typing_score,
                contradiction_detected = voice.get("contradiction_detected", False),
                contradiction_type     = voice.get("contradiction_type", "none"),
                transcript             = voice.get("transcript", ""),
                facial_emotion         = facial.get("dominant_emotion", "neutral"),
                voice_emotion          = voice.get("dominant_emotion", "neutral"),
            ))

            # Update baseline
            baseline_model.update(
                user_id      = "demo_user",
                physio_score = watch.get("physio_score"),
                facial_score = facial.get("distress_score"),
                voice_score  = voice.get("combined_score"),
                eli          = eli_result.eli,
                hrv          = watch.get("hrv"),
                hr           = watch.get("heart_rate"),
            )

            # Build full payload for React
            payload = {
                "eli":     fusion_engine.to_dict(eli_result),
                "facial":  facial,
                "voice":   voice,
                "watch":   watch,
            }

            await websocket.send_json(payload)
            await asyncio.sleep(3)

    except Exception as e:
        print(f"WebSocket closed: {e}")