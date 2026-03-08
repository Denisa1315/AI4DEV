from fastapi import APIRouter, UploadFile, File
from services.ml.voice_analysis import voice_analyzer

router = APIRouter(prefix="/api")

@router.post("/analyze-voice")
async def analyze_voice(file: UploadFile = File(...)):
    audio_bytes = await file.read()
    result      = voice_analyzer.analyze_audio_bytes(audio_bytes)
    return voice_analyzer.to_dict()