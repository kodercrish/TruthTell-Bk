from fastapi import APIRouter, HTTPException, UploadFile, File
import numpy as np
import librosa
import xgboost as xgb
import os
from typing import Dict
import tempfile

deepfake_audio_router = APIRouter()

# # Load trained model
# model = xgb.XGBClassifier()
# model.load_model("../deepfake audio/audio_model.json")

# Get the current file's directory
current_dir = os.path.dirname(os.path.abspath(__file__))
# Construct path to model file
model_path = os.path.join(current_dir, "..", "deepfake audio", "audio_model.json")

# Load model with correct path
model = xgb.XGBClassifier()
model.load_model(model_path)


def extract_features(y, sr, max_pad=128):
    mel_spec = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128)
    mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)

    if mel_spec_db.shape[1] < max_pad:
        pad_width = max_pad - mel_spec_db.shape[1]
        mel_spec_db = np.pad(mel_spec_db, ((0, 0), (0, pad_width)), mode='constant')
    else:
        mel_spec_db = mel_spec_db[:, :max_pad]

    return mel_spec_db.flatten()

def predict_long_audio(file_path, segment_length=2, overlap=1):
    y, sr = librosa.load(file_path, sr=22050)
    segment_samples = segment_length * sr
    overlap_samples = overlap * sr

    segments = []
    for start in range(0, len(y) - segment_samples, segment_samples - overlap_samples):
        segment = y[start : start + segment_samples]
        feature = extract_features(segment, sr)
        segments.append(feature)

    segments = np.array(segments)
    predictions = model.predict(segments)
    avg_prediction = np.mean(predictions)

    label = "real" if avg_prediction > 0.5 else "fake"
    confidence = float(avg_prediction)

    return label, confidence

@deepfake_audio_router.post("/detect-audio")
async def detect_audio(audio_file: UploadFile = File(...)) -> Dict:
    try:
        # Create temporary file to store the uploaded audio
        with tempfile.NamedTemporaryFile(delete=False) as temp_audio:
            content = await audio_file.read()
            temp_audio.write(content)
            temp_path = temp_audio.name

        # Process the audio file
        label, confidence = predict_long_audio(temp_path)
        
        # Clean up temporary file
        os.unlink(temp_path)

        return {
            "status": "success",
            "content": {
                "prediction": label,
                "confidence": confidence
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
