# 🧠 AffectSync – Multimodal Bio-Affective Emotional Regulation System

## Overview

AffectSync is an AI-powered emotional regulation platform that combines physiological, behavioral, and emotional signals to provide proactive mental health support.

Unlike traditional AI chatbots that rely only on text, AffectSync uses multimodal sensing through smartwatch biometrics, facial emotion analysis, and voice tone analysis to understand a user's emotional state in real time.

The system generates an **Emotional Instability Index (ELI)**, detects emotional masking, provides personalized CBT-based interventions, and escalates users to professional support when high-risk emotional states are detected.

---

## Problem Statement

Mental health issues such as stress, anxiety, burnout, and emotional exhaustion are increasing rapidly, particularly among students and young professionals.

Current solutions suffer from several limitations:

* Depend heavily on self-reported emotions
* Lack physiological awareness
* Provide generic interventions
* Fail to detect hidden emotional distress
* Offer limited personalization

Additionally, mental health remains highly stigmatized, preventing many individuals from seeking professional help.

AffectSync aims to bridge this gap through continuous, privacy-conscious emotional monitoring and adaptive support.

---

## Key Features

### 🫀 Physiological Monitoring

* Heart Rate (HR)
* Heart Rate Variability (HRV)
* Sleep quality metrics
* Activity level tracking

### 🙂 Facial Emotion Detection

* Real-time emotion recognition
* Stress and sadness detection
* Facial distress scoring

### 🎙️ Voice Stress Analysis

* Pitch variation analysis
* Speech energy analysis
* Stress pattern detection
* Emotional tone estimation

### 🧠 Emotional Instability Index (ELI)

Combines physiological, facial, and voice signals into a unified emotional risk score.

### 🔍 Contradiction Detection

Detects situations where user statements contradict physiological and emotional indicators.

Example:

User says:

> "I'm fine."

System detects:

* Elevated heart rate
* Low HRV
* Sad facial expression

Result:

> Emotional masking detected.

### 💬 Adaptive CBT-Based Therapy

Provides structured cognitive behavioral interventions including:

* Socratic questioning
* Cognitive reframing
* Grounding exercises
* Emotional validation

### 📈 Progress Tracking

Tracks:

* Stress trends
* Emotional stability
* Therapy effectiveness
* Baseline deviations

### 🚨 Crisis Escalation System

Provides:

* Mental health resources
* Helpline recommendations
* Professional support guidance

### 📄 Therapist Handoff Reports

Generates structured reports containing:

* Emotional trends
* Trigger patterns
* Session summaries
* Physiological indicators

---

## System Architecture

### Input Layer

* Smartwatch Biometrics
* Webcam Feed
* Microphone Input

### Processing Layer

* Physiological Signal Processing
* Facial Emotion Analysis
* Voice Stress Analysis

### Fusion Layer

* Feature Extraction
* Personal Baseline Modeling
* Emotional Instability Index Calculation

### Intelligence Layer

* Contradiction Detection
* Therapy Routing Engine
* CBT Agent
* Crisis Detection Agent

### Output Layer

* Real-Time Dashboard
* AI Therapy Chat Interface
* Explainability Panel
* Crisis Support Recommendations

---

## Technology Stack

### Frontend

* ReactJS
* Tailwind CSS
* Recharts
* React Webcam
* Zustand

### Backend

* FastAPI
* Python
* WebSockets
* MongoDB

### Machine Learning

* DeepFace
* OpenCV
* TensorFlow
* Librosa
* NumPy
* SciPy

### AI Layer

* LangChain
* Ollama
* Llama 3.1

---

## Workflow

1. User provides physiological, facial, and voice inputs.
2. Individual signal processors calculate stress scores.
3. Personal baseline deviations are computed.
4. Fusion engine generates Emotional Instability Index (ELI).
5. Contradiction detection identifies emotional masking.
6. Therapy router selects appropriate intervention.
7. AI generates personalized support responses.
8. Dashboard updates in real time.
9. Crisis protocol activates when necessary.
10. Session data is stored for future personalization.

---

## Expected Outcomes

* Real-time emotional state assessment
* Early detection of emotional distress
* Personalized CBT-based interventions
* Emotional masking identification
* Proactive stress management
* Improved accessibility to mental health support

---

## Limitations

* Not a replacement for licensed therapists
* Requires webcam and microphone access
* Dependent on input quality
* Requires further clinical validation

---

## Future Scope

* Multilingual support (Tamil, Hindi, Telugu, Kannada)
* Advanced stress forecasting models
* Mobile application deployment
* Integration with additional wearable devices
* Therapist collaboration platform
* Federated privacy-preserving learning

---

## Team

### Dev 1 – ML & AI Core

* Facial Emotion Detection
* Voice Analysis
* Fusion Engine
* Baseline Modeling

### Dev 2 – Backend & AI Agents

* FastAPI
* MongoDB
* LangChain
* Ollama Integration

### Dev 3 – Frontend & Dashboard

* ReactJS
* WebSocket Integration
* UI/UX Design
* Demo Preparation

---

## License

This project is developed for educational, research, and hackathon purposes.

---

## Tagline

**"Understanding emotions beyond words through multimodal AI."**
