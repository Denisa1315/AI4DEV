# services/ml/voice_analysis.py
#
# Combined Voice Modulation + Speech Transcript Analyzer
# Pipeline:
#   Audio → Whisper transcription  → Text sentiment score
#         → Acoustic features      → Voice stress score
#         → Combine both           → Unified vocal-linguistic score
#         → Contradiction detection (words vs voice)

import numpy as np
import sounddevice as sd
import soundfile as sf
import scipy.signal as signal
import tempfile
import threading
import time
import os
import io
from dataclasses import dataclass, field
from typing import Optional

from faster_whisper import WhisperModel
from transformers import pipeline as hf_pipeline

# ─────────────────────────────────────────────────────
SAMPLE_RATE    = 16000
WINDOW_SECONDS = 5
MIN_SPEECH_RMS = 0.005

POSITIVE_WORDS = {
    "fine", "okay", "ok", "good", "great", "happy", "well",
    "alright", "better", "calm", "relaxed", "cool", "nice",
    "wonderful", "fantastic", "amazing", "excellent", "perfect",
    "nothing", "normal", "all good", "doing well"
}

NEGATIVE_WORDS = {
    "stressed", "anxious", "worried", "scared", "afraid",
    "nervous", "angry", "upset", "sad", "depressed", "tired",
    "exhausted", "overwhelmed", "terrible", "awful", "horrible",
    "bad", "panicking", "crying", "hurt", "pain", "fail",
    "failing", "failed", "hate", "miserable"
}

CRISIS_WORDS = {
    "die", "death", "kill", "suicide", "end it", "give up",
    "no point", "worthless", "hopeless", "cant go on",
    "want to disappear", "not here anymore"
}

# ─────────────────────────────────────────────────────
@dataclass
class VoiceResult:
    voice_stress_score:      float
    text_sentiment_score:    float
    combined_score:          float
    dominant_emotion:        str
    emotion_scores:          dict
    transcript:              str
    transcript_sentiment:    str
    transcript_confidence:   float
    contradiction_detected:  bool
    contradiction_type:      str
    speech_detected:         bool
    acoustic_confidence:     float
    features:                dict
    timestamp: float = field(default_factory=time.time)


# ─────────────────────────────────────────────────────
class VoiceAnalyzer:

    def __init__(self):
        self._lock            = threading.Lock()
        self._emotion_history = []
        self._history_size    = 4
        self._recording       = False
        self._thread          = None
        self._baseline = {
            "pitch_mean":      150.0,
            "energy_mean":     0.05,
            "pitch_readings":  [],
            "energy_readings": [],
        }
        self._last_result = VoiceResult(
            voice_stress_score=50.0,
            text_sentiment_score=50.0,
            combined_score=50.0,
            dominant_emotion="neutral",
            emotion_scores={"angry":0.0,"sad":0.0,"fear":0.0,
                            "happy":0.0,"neutral":1.0},
            transcript="",
            transcript_sentiment="neutral",
            transcript_confidence=0.0,
            contradiction_detected=False,
            contradiction_type="none",
            speech_detected=False,
            acoustic_confidence=0.0,
            features={},
        )
        self._load_models()

    def _load_models(self):
        print("[VoiceAnalyzer] Loading Whisper ...")
        self._whisper = WhisperModel(
            "small", device="cpu", compute_type="int8"
        )
        print("[VoiceAnalyzer] Whisper ready ✓")
        print("[VoiceAnalyzer] Loading sentiment model ...")
        self._sentiment = hf_pipeline(
            "sentiment-analysis",
            model="distilbert-base-uncased-finetuned-sst-2-english",
            truncation=True, max_length=128
        )
        print("[VoiceAnalyzer] Sentiment ready ✓")

    # ── Public methods ────────────────────────────────
    def analyze_audio_bytes(self, audio_bytes: bytes) -> VoiceResult:
        try:
            audio = self._bytes_to_array(audio_bytes)
            if audio is None:
                return self._last_result
            return self._process(audio)
        except Exception as e:
            print(f"[VoiceAnalyzer] Bytes error: {e}")
            return self._last_result

    def analyze_file(self, filepath: str) -> VoiceResult:
        try:
            audio, sr = sf.read(filepath, dtype='float32')
            if len(audio.shape) > 1:
                audio = audio.mean(axis=1)
            if sr != SAMPLE_RATE:
                audio = self._resample(audio, sr, SAMPLE_RATE)
            return self._process(audio)
        except Exception as e:
            print(f"[VoiceAnalyzer] File error: {e}")
            return self._last_result

    def start_continuous_recording(self):
        self._recording = True
        self._thread = threading.Thread(
            target=self._recording_loop, daemon=True
        )
        self._thread.start()
        print("[VoiceAnalyzer] Recording started ✓")

    def stop_recording(self):
        self._recording = False

    def _recording_loop(self):
        while self._recording:
            try:
                audio = sd.rec(
                    int(WINDOW_SECONDS * SAMPLE_RATE),
                    samplerate=SAMPLE_RATE, channels=1, dtype='float32'
                )
                sd.wait()
                self._process(audio.flatten())
                time.sleep(1.0)
            except Exception as e:
                print(f"[VoiceAnalyzer] Rec error: {e}")
                time.sleep(2.0)

    # ── Core pipeline ─────────────────────────────────
    def _process(self, audio: np.ndarray) -> VoiceResult:
        audio = self._preprocess(audio)
        rms   = float(np.sqrt(np.mean(audio ** 2)))

        if rms < MIN_SPEECH_RMS:
            with self._lock:
                self._last_result.speech_detected = False
                self._last_result.timestamp = time.time()
            return self._last_result

        # Acoustic pipeline
        features       = self._extract_features(audio)
        self._update_baseline(features)
        emotion_scores = self._classify_emotion(features)
        emotion_scores = self._smooth_emotions(emotion_scores)
        dominant       = max(emotion_scores, key=emotion_scores.get)
        voice_stress   = self._calculate_acoustic_stress(
            features, emotion_scores
        )
        acoustic_conf  = min(100.0, (rms / 0.1) * 100)

        # Linguistic pipeline
        transcript, trans_conf = self._transcribe(audio)
        text_sentiment, sentiment_label = self._analyse_sentiment(
            transcript
        )
        crisis = self._check_crisis_words(transcript)

        # Combine
        combined = self._combine_scores(
            voice_stress, text_sentiment, transcript
        )

        # Contradiction detection
        contradiction, contra_type = self._detect_contradiction(
            transcript, sentiment_label, voice_stress, emotion_scores
        )

        result = VoiceResult(
            voice_stress_score=round(voice_stress, 2),
            text_sentiment_score=round(text_sentiment, 2),
            combined_score=round(combined, 2),
            dominant_emotion=dominant,
            emotion_scores={k: round(v,4) for k,v in emotion_scores.items()},
            transcript=transcript,
            transcript_sentiment=sentiment_label,
            transcript_confidence=round(trans_conf, 2),
            contradiction_detected=contradiction,
            contradiction_type="CRISIS" if crisis else contra_type,
            speech_detected=True,
            acoustic_confidence=round(acoustic_conf, 1),
            features={
                "pitch_mean":    round(features.get("pitch_mean",    0), 1),
                "energy_mean":   round(features.get("energy_mean",   0), 5),
                "speech_rate":   round(features.get("speech_rate",   0), 2),
                "pause_density": round(features.get("pause_density", 0), 2),
                "pitch_std":     round(features.get("pitch_std",     0), 2),
                "spectral_centroid": round(
                    features.get("spectral_centroid", 0), 1),
            }
        )

        with self._lock:
            self._last_result = result

        return result

    # ── Whisper transcription ─────────────────────────
    def _transcribe(self, audio: np.ndarray) -> tuple:
        rms = float(np.sqrt(np.mean(audio ** 2)))
        if rms < 0.003:   # stronger silence gate for Whisper
            return "", 0.0
        try:
            with tempfile.NamedTemporaryFile(
                suffix=".wav", delete=False
            ) as f:
                sf.write(f.name, audio, SAMPLE_RATE)
                temp_path = f.name

            segments, _ = self._whisper.transcribe(
                temp_path,
                language="en",
                beam_size=3,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=300)
            )
            os.unlink(temp_path)
            transcript = " ".join(
                seg.text.strip() for seg in segments
            ).strip()
            return transcript, 0.8

        except Exception as e:
            print(f"[VoiceAnalyzer] Transcription error: {e}")
            return "", 0.0

    # ── Sentiment analysis ────────────────────────────
    def _analyse_sentiment(self, transcript: str) -> tuple:
        if not transcript or len(transcript.strip()) < 3:
            return 50.0, "neutral"
        try:
            res   = self._sentiment(transcript)[0]
            label = res["label"]
            conf  = res["score"]
            score = (50 + conf*50) if label == "POSITIVE" else (50 - conf*50)

            words    = set(transcript.lower().split())
            pos_hits = len(words & POSITIVE_WORDS)
            neg_hits = len(words & NEGATIVE_WORDS)
            if neg_hits > pos_hits:
                score -= neg_hits * 5
            elif pos_hits > neg_hits:
                score += pos_hits * 3

            score = max(0.0, min(100.0, score))
            label = "positive" if score>=60 else ("negative" if score<=40 else "neutral")
            return round(score, 2), label

        except Exception as e:
            print(f"[VoiceAnalyzer] Sentiment error: {e}")
            return 50.0, "neutral"

    # ── Contradiction detection ───────────────────────
    def _detect_contradiction(
        self, transcript, sentiment_label, voice_stress, emotion_scores
    ) -> tuple:
        if not transcript:
            return False, "none"

        words = set(transcript.lower().split())
        positive_mask = any(w in transcript.lower() for w in POSITIVE_WORDS)
        negative_expr = any(w in transcript.lower() for w in NEGATIVE_WORDS)
        dominant_distress = (
            emotion_scores.get("sad",  0) +
            emotion_scores.get("fear", 0) +
            emotion_scores.get("angry",0)
        )

        # MASKING — says fine but voice is stressed
        if (sentiment_label == "positive" and positive_mask
                and voice_stress > 60 and dominant_distress > 0.4):
            return True, "masking"

        fine_words = {"fine","okay","ok","alright","good","nothing"}
        if words & fine_words and voice_stress > 70:
            return True, "masking"

        # SUPPRESSION — says negative but voice is calm
        if (sentiment_label == "negative" and negative_expr
                and voice_stress < 35):
            return True, "suppression"

        return False, "none"

    def _check_crisis_words(self, transcript: str) -> bool:
        if not transcript:
            return False
        t = transcript.lower()
        return any(w in t for w in CRISIS_WORDS)

    # ── Score combination ─────────────────────────────
    def _combine_scores(
        self, voice_stress, text_sentiment, transcript
    ) -> float:
        text_distress = 100 - text_sentiment
        if len(transcript.split()) < 4:
            vw, tw = 0.80, 0.20
        else:
            vw, tw = 0.55, 0.45
        return max(0.0, min(100.0,
            voice_stress * vw + text_distress * tw
        ))

    # ── Acoustic features ─────────────────────────────
    def _preprocess(self, audio: np.ndarray) -> np.ndarray:
        audio = audio.astype(np.float32) - np.mean(audio)
        b, a  = signal.butter(
            4, [80/(SAMPLE_RATE/2), 3400/(SAMPLE_RATE/2)], btype='band'
        )
        audio = signal.filtfilt(b, a, audio)
        mx    = np.max(np.abs(audio))
        if mx > 0:
            audio = audio / mx * 0.9
        return audio

    def _extract_features(self, audio: np.ndarray) -> dict:
        f          = {}
        frame_size = int(0.025 * SAMPLE_RATE)
        hop_size   = int(0.010 * SAMPLE_RATE)
        frames     = self._frame_signal(audio, frame_size, hop_size)
        rms_frames = np.sqrt(np.mean(frames**2, axis=1))

        f["energy_mean"]  = float(np.mean(rms_frames))
        f["energy_std"]   = float(np.std(rms_frames))
        f["energy_slope"] = float(self._linear_slope(rms_frames))

        pitches = self._extract_pitch(audio)
        if len(pitches) > 0:
            f["pitch_mean"]  = float(np.mean(pitches))
            f["pitch_std"]   = float(np.std(pitches))
            f["pitch_range"] = float(np.ptp(pitches))
            f["pitch_slope"] = float(self._linear_slope(pitches))
        else:
            f["pitch_mean"]  = 150.0
            f["pitch_std"]   = 10.0
            f["pitch_range"] = 20.0
            f["pitch_slope"] = 0.0

        f["speech_rate"]   = self._estimate_speech_rate(rms_frames)
        silence_thresh     = f["energy_mean"] * 0.2
        f["pause_density"] = float(
            np.sum(rms_frames < silence_thresh) / max(len(rms_frames),1)
        )

        zcr            = self._zero_crossing_rate(audio, frame_size, hop_size)
        f["zcr_mean"]  = float(np.mean(zcr))
        f.update(self._spectral_features(audio))

        f["pitch_deviation"]  = self._deviation(
            f["pitch_mean"],  self._baseline["pitch_mean"]
        )
        f["energy_deviation"] = self._deviation(
            f["energy_mean"], self._baseline["energy_mean"]
        )
        return f

    def _extract_pitch(self, audio: np.ndarray) -> np.ndarray:
        frame_size = int(0.040 * SAMPLE_RATE)
        hop_size   = int(0.010 * SAMPLE_RATE)
        min_lag    = int(SAMPLE_RATE / 400)
        max_lag    = int(SAMPLE_RATE / 60)
        frames     = self._frame_signal(audio, frame_size, hop_size)
        pitches    = []
        for frame in frames:
            w    = frame * np.hanning(len(frame))
            corr = np.correlate(w, w, mode='full')
            corr = corr[len(corr)//2:]
            if max_lag < len(corr):
                seg = corr[min_lag:max_lag]
                if len(seg)>0 and np.max(seg) > 0.1*corr[0]:
                    idx = np.argmax(seg) + min_lag
                    if idx > 0:
                        pitches.append(SAMPLE_RATE / idx)
        return np.array(pitches)

    def _estimate_speech_rate(self, rms_frames: np.ndarray) -> float:
        if len(rms_frames) < 10:
            return 0.08
        k        = np.hanning(10); k /= k.sum()
        smoothed = np.convolve(rms_frames, k, mode='same')
        thresh   = np.mean(smoothed) * 0.5
        peaks    = 0; in_peak = False
        for v in smoothed:
            if v > thresh and not in_peak:
                peaks += 1; in_peak = True
            elif v <= thresh:
                in_peak = False
        return float(peaks / max(len(rms_frames)*0.010, 1.0))

    def _zero_crossing_rate(self, audio, frame_size, hop_size):
        frames = self._frame_signal(audio, frame_size, hop_size)
        return np.array([
            np.sum(np.diff(np.sign(f))!=0)/frame_size for f in frames
        ])

    def _spectral_features(self, audio: np.ndarray) -> dict:
        frame_size = int(0.025 * SAMPLE_RATE)
        hop_size   = int(0.010 * SAMPLE_RATE)
        frames     = self._frame_signal(audio, frame_size, hop_size)
        freqs      = np.fft.rfftfreq(frame_size, d=1.0/SAMPLE_RATE)
        centroids, rolloffs, flatness = [], [], []
        for frame in frames:
            w     = frame * np.hanning(len(frame))
            spec  = np.abs(np.fft.rfft(w))
            power = spec**2; total = np.sum(power)
            if total < 1e-10: continue
            centroids.append(np.sum(freqs*power)/total)
            cum = np.cumsum(power)
            idx = np.searchsorted(cum, 0.85*total)
            rolloffs.append(freqs[min(idx, len(freqs)-1)])
            geo = np.exp(np.mean(np.log(power+1e-10)))
            flatness.append(geo/(np.mean(power)+1e-10))
        return {
            "spectral_centroid": float(np.mean(centroids)) if centroids else 1000.0,
            "spectral_rolloff":  float(np.mean(rolloffs))  if rolloffs  else 2000.0,
            "spectral_flatness": float(np.mean(flatness))  if flatness  else 0.1,
        }

    def _classify_emotion(self, features: dict) -> dict:
        scores   = {"angry":0.0,"sad":0.0,"fear":0.0,"happy":0.0,"neutral":0.0}
        p_mean   = features.get("pitch_mean",     150.0)
        p_std    = features.get("pitch_std",       10.0)
        p_slope  = features.get("pitch_slope",      0.0)
        p_dev    = features.get("pitch_deviation",  0.0)
        e_mean   = features.get("energy_mean",      0.05)
        e_std    = features.get("energy_std",       0.01)
        e_dev    = features.get("energy_deviation", 0.0)
        rate     = features.get("speech_rate",      0.08)
        pauses   = features.get("pause_density",    0.3)
        zcr      = features.get("zcr_mean",         0.05)
        centroid = features.get("spectral_centroid",1000.0)
        flatness = features.get("spectral_flatness",0.1)

        angry = 0.0
        if p_mean>180:   angry+=0.20
        if p_dev>15:     angry+=0.15
        if e_mean>0.07:  angry+=0.20
        if e_dev>20:     angry+=0.15
        if rate>5.0:     angry+=0.15
        if pauses<0.20:  angry+=0.10
        if centroid>1500:angry+=0.10
        scores["angry"] = min(1.0, angry)

        sad = 0.0
        if p_mean<130:   sad+=0.20
        if p_dev<-10:    sad+=0.15
        if p_slope<-2:   sad+=0.15
        if e_mean<0.03:  sad+=0.20
        if e_dev<-15:    sad+=0.10
        if rate<3.0:     sad+=0.15
        if pauses>0.45:  sad+=0.10
        if centroid<800: sad+=0.10
        scores["sad"] = min(1.0, sad)

        fear = 0.0
        if p_std>35:     fear+=0.25
        if p_mean>190:   fear+=0.20
        if flatness>0.3: fear+=0.20
        if zcr>0.08:     fear+=0.15
        if e_std>0.05:   fear+=0.15
        if pauses>0.35 and rate>4.0: fear+=0.10
        scores["fear"] = min(1.0, fear)

        happy = 0.0
        if 150<p_mean<250: happy+=0.20
        if p_slope>1:      happy+=0.15
        if e_mean>0.06:    happy+=0.20
        if rate>4.5:       happy+=0.15
        if pauses<0.25:    happy+=0.10
        if centroid>1200:  happy+=0.15
        scores["happy"] = min(1.0, happy)

        # Disambiguate
        if scores["angry"]>0.3 and scores["sad"]>0.3:
            if e_mean > self._baseline["energy_mean"]*1.2:
                scores["sad"]   *= 0.5
            else:
                scores["angry"] *= 0.5

        if scores["fear"]>0.3 and scores["angry"]>0.3:
            if p_std > 30:
                scores["angry"] *= 0.6
            else:
                scores["fear"]  *= 0.6

        max_e = max(scores["angry"],scores["sad"],
                    scores["fear"],scores["happy"])
        scores["neutral"] = max(0.0, 1.0 - max_e*1.5)

        total = sum(scores.values())
        if total > 0:
            scores = {k: round(v/total,4) for k,v in scores.items()}
        return scores

    def _calculate_acoustic_stress(self, features, emotion_scores) -> float:
        ec = max(0.0, (
            emotion_scores.get("angry",0)*0.30 +
            emotion_scores.get("fear", 0)*0.35 +
            emotion_scores.get("sad",  0)*0.25 -
            emotion_scores.get("happy",0)*0.10
        )) * 100
        fs = 0.0
        if abs(features.get("pitch_deviation",  0)) > 20: fs += 0.25
        if abs(features.get("energy_deviation", 0)) > 20: fs += 0.25
        if features.get("pitch_std",    0) > 35:          fs += 0.25
        if features.get("pause_density",0) > 0.50:        fs += 0.15
        if features.get("spectral_flatness",0) > 0.4:     fs += 0.10
        return max(0.0, min(100.0, ec*0.60 + min(100.0,fs*100)*0.40))

    def _smooth_emotions(self, emotions: dict) -> dict:
        self._emotion_history.append(emotions)
        if len(self._emotion_history) > self._history_size:
            self._emotion_history.pop(0)
        n = len(self._emotion_history)
        w = [i+1 for i in range(n)]; total = sum(w)
        smoothed = {
            e: round(
                sum(self._emotion_history[i].get(e,0)*w[i]
                    for i in range(n))/total, 4
            ) for e in emotions
        }
        t = sum(smoothed.values())
        if t > 0:
            smoothed = {k: round(v/t,4) for k,v in smoothed.items()}
        return smoothed

    def _update_baseline(self, features: dict):
        b = self._baseline
        b["pitch_readings"].append(features["pitch_mean"])
        b["energy_readings"].append(features["energy_mean"])
        if len(b["pitch_readings"])  > 50: b["pitch_readings"]  = b["pitch_readings"][-50:]
        if len(b["energy_readings"]) > 50: b["energy_readings"] = b["energy_readings"][-50:]
        if len(b["pitch_readings"])  >= 5: b["pitch_mean"]  = float(np.median(b["pitch_readings"]))
        if len(b["energy_readings"]) >= 5: b["energy_mean"] = float(np.median(b["energy_readings"]))

    # ── Dev 2 interface ───────────────────────────────
    def to_dict(self) -> dict:
        with self._lock:
            r = self._last_result
            return {
                "voice_stress_score":     r.voice_stress_score,
                "text_sentiment_score":   r.text_sentiment_score,
                "combined_score":         r.combined_score,
                "dominant_emotion":       r.dominant_emotion,
                "emotion_scores":         dict(r.emotion_scores),
                "transcript":             r.transcript,
                "transcript_sentiment":   r.transcript_sentiment,
                "contradiction_detected": r.contradiction_detected,
                "contradiction_type":     r.contradiction_type,
                "speech_detected":        r.speech_detected,
                "confidence":             r.acoustic_confidence,
                "timestamp":              r.timestamp,
                "features":               dict(r.features),
            }

    def warmup(self):
        print("[VoiceAnalyzer] Warming up ...")
        dummy = np.random.randn(
            SAMPLE_RATE * WINDOW_SECONDS
        ).astype(np.float32) * 0.01
        self._process(dummy)
        print("[VoiceAnalyzer] Warmup done ✓")

    # ── Utilities ─────────────────────────────────────
    def _bytes_to_array(self, audio_bytes: bytes) -> Optional[np.ndarray]:
        try:
            buf = io.BytesIO(audio_bytes)
            data, sr = sf.read(buf, dtype='float32')
            if len(data.shape) > 1: data = data.mean(axis=1)
            if sr != SAMPLE_RATE: data = self._resample(data, sr, SAMPLE_RATE)
            return data
        except Exception as e:
            print(f"[VoiceAnalyzer] Decode error: {e}")
            return None

    def _resample(self, audio, orig_sr, target_sr):
        return signal.resample(audio, int(len(audio)*target_sr/orig_sr))

    def _frame_signal(self, audio, frame_size, hop_size):
        num = 1 + (len(audio)-frame_size)//hop_size
        if num <= 0:
            pad = np.zeros(frame_size)
            pad[:len(audio)] = audio
            return np.array([pad])
        return np.stack([
            audio[i*hop_size: i*hop_size+frame_size]
            for i in range(num)
            if i*hop_size+frame_size <= len(audio)
        ])

    def _linear_slope(self, values):
        if len(values) < 2: return 0.0
        x = np.arange(len(values), dtype=float)
        return float(np.polyfit(x, values, 1)[0])

    def _deviation(self, current, baseline):
        if baseline == 0: return 0.0
        return float(((current-baseline)/baseline)*100)


# ─────────────────────────────────────────────────────
# Singleton
# ─────────────────────────────────────────────────────
voice_analyzer = VoiceAnalyzer()