# run this once: download_weights.py

import gdown
import os

print("Downloading pretrained emotion model...")

# Pretrained on FER2013 — 7 emotions, 66% accuracy
url = "https://drive.google.com/uc?id=1FUn0XNOXx-nFPinLmb7GbcIXFDviS3B4"
output = "emotion_model.pt"

gdown.download(url, output, quiet=False)
print("Downloaded!")