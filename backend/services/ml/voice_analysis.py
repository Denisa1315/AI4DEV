class VoiceAnalyzer:
    def analyze_audio_bytes(self, audio_bytes: bytes):
        return {
            "status": "success",
            "message": "Mock voice analysis completed."
        }
        
    def to_dict(self):
        return {
            "combined_score": 40,
            "contradiction_detected": False,
            "contradiction_type": "none",
            "transcript": "Hello, I am feeling fine today.",
            "dominant_emotion": "calm"
        }

voice_analyzer = VoiceAnalyzer()
