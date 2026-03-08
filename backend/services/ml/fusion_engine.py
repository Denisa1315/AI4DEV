from dataclasses import dataclass

@dataclass
class SignalInput:
    physio_score: float
    facial_score: float
    voice_score: float
    typing_score: float
    contradiction_detected: bool
    contradiction_type: str
    transcript: str
    facial_emotion: str
    voice_emotion: str

class EliResult:
    def __init__(self, eli):
        self.eli = eli

class FusionEngine:
    def calculate(self, signals: SignalInput):
        # A mock calculation combining all scores
        base_eli = (signals.physio_score + signals.facial_score + signals.voice_score) / 3
        return EliResult(eli=min(100, max(0, base_eli)))
    
    def to_dict(self, result: EliResult):
        return {
            "eli_score": result.eli,
            "status": "calculated"
        }

fusion_engine = FusionEngine()
