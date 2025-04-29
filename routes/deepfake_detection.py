import os
# import io
# import cv2
import numpy as np
from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from tensorflow.keras.models import load_model
from PIL import Image
from typing import Dict, Any
import sys

# Add the parent directory to the path to import testing2
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import functions from testing2
from deepfake_detection.testing2 import combined_prediction, predict_video

# Create router
deepfake_router = APIRouter()

# Load the model at startup
model = None

@deepfake_router.on_event("startup")
async def startup_event():
    global model
    try:
        # model = load_model("deepfake_detector.h5")
        # print("Deepfake detection model loaded successfully")
        # Use absolute path for the model
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        model_path = os.path.join(current_dir, "deepfake_detection", "deepfake_detector.h5")
        model = load_model(model_path)
        print("Deepfake detection model loaded successfully")
    except Exception as e:
        print(f"Error loading deepfake detection model: {e}")
        # We'll try to load it on first request

def process_image_in_memory(file_content: bytes) -> Dict[str, Any]:
    """Process an image from bytes and return detection results"""
    # Create a temporary file
    temp_path = "temp_image.jpg"
    
    try:
        # Save the bytes to a temporary file
        with open(temp_path, "wb") as f:
            f.write(file_content)
        
        # Process the image
        results = combined_prediction(temp_path)
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")
    finally:
        # Clean up
        if os.path.exists(temp_path):
            os.remove(temp_path)

def process_video_in_memory(file_content: bytes) -> Dict[str, Any]:
    """Process a video from bytes and return detection results"""
    # Create a temporary file
    temp_path = "temp_video.mp4"
    
    try:
        # Save the bytes to a temporary file
        with open(temp_path, "wb") as f:
            f.write(file_content)
        
        # Process the video
        results = predict_video(temp_path)
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing video: {str(e)}")
    finally:
        # Clean up
        if os.path.exists(temp_path):
            os.remove(temp_path)

@deepfake_router.post("/image", response_model=Dict[str, Any])
async def analyze_image(file: UploadFile = File(...)):
    """
    Analyze an image to detect if it's real or fake.
    
    - **file**: The image file to analyze (jpg, jpeg, png)
    
    Returns detailed analysis results including CNN prediction, metadata analysis,
    artifact analysis, noise pattern analysis, and symmetry measurements.
    """
    global model
    
    # Try to load the model if it's not loaded yet
    if model is None:
        try:
            model = load_model("deepfake_detector.h5")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Model not loaded: {str(e)}")
    
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Read file content
    file_content = await file.read()
    
    # Process the image
    results = process_image_in_memory(file_content)
    
    return results

@deepfake_router.post("/video", response_model=Dict[str, Any])
async def analyze_video(file: UploadFile = File(...)):
    """
    Analyze a video to detect if it's real or fake.
    
    - **file**: The video file to analyze (mp4, avi)
    
    Returns detailed analysis results including frame-by-frame analysis,
    fake/real frame counts, and overall prediction.
    """
    global model
    
    # Try to load the model if it's not loaded yet
    if model is None:
        try:
            model = load_model("deepfake_detector.h5")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Model not loaded: {str(e)}")
    
    if not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="File must be a video")
    
    # Read file content
    file_content = await file.read()
    
    # Process the video
    results = process_video_in_memory(file_content)
    
    return results

@deepfake_router.get("/health")
async def health_check():
    """Check if the API is running and the model is loaded"""
    if model is None:
        return {"status": "warning", "message": "Model not loaded yet, will attempt to load on first request"}
    return {"status": "ok", "message": "Deepfake detection model is loaded and ready"}
