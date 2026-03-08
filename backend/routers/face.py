from fastapi import APIRouter, UploadFile, File
from services.ml.facial_analysis import facial_analyzer

router = APIRouter(prefix="/api")

@router.post("/analyze-face")
async def analyze_face(file: UploadFile = File(...)):
    """
    Accept a JPEG frame from the React webcam, run backend facial analysis,
    and return the result. The result is also stored in the singleton so
    the WebSocket ELI loop picks it up automatically.
    """
    image_bytes = await file.read()
    result = facial_analyzer.analyze_from_bytes(image_bytes)
    return {
        "distress_score":   result.distress_score,
        "dominant_emotion": result.dominant_emotion,
        "emotions":         result.emotions,
        "face_detected":    result.face_detected,
        "confidence":       result.confidence,
        "lighting":         result.lighting,
        "timestamp":        result.timestamp,
    }
