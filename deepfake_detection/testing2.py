import os
import cv2
import numpy as np
import imghdr
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
from PIL import Image
from PIL.ExifTags import TAGS

# Load the saved model
# model_path = "deepfake_detector.h5"
# model = load_model(model_path)

# Use absolute path for the model
current_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(current_dir, "deepfake_detector.h5")
model = load_model(model_path)


# Image dimensions
img_height, img_width = 128, 128

# Trained model prediction
def predict_image(img_path):
    if not os.path.exists(img_path):
        return "Image path does not exist."
    img = image.load_img(img_path, target_size=(img_height, img_width))
    img_array = image.img_to_array(img) / 255.0
    img_array = np.expand_dims(img_array, axis=0)
    prediction = model.predict(img_array)
    return "Fake" if prediction[0][0] > 0.5 else "Real"

def predict_video(video_path):
    """Predict whether a video is real or fake by analyzing frames."""
    try:
        cap = cv2.VideoCapture(video_path)
        fake_count, real_count = 0, 0
        total_frames = 0
        results = {}

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # Process every 5th frame to improve performance
            if total_frames % 5 == 0:
                # Analyze frame using all detection methods
                frame_path = f"temp_frame_{total_frames}.jpg"
                cv2.imwrite(frame_path, frame)
                
                frame_results = combined_prediction(frame_path)
                if frame_results["Final Prediction"] == "Fake":
                    fake_count += 1
                else:
                    real_count += 1
                    
                os.remove(frame_path)
            
            total_frames += 1

        cap.release()

        # Calculate final results
        total_analyzed_frames = fake_count + real_count
        fake_percentage = (fake_count / total_analyzed_frames * 100) if total_analyzed_frames > 0 else 0
        
        results["Total Frames Analyzed"] = total_analyzed_frames
        results["Fake Frames"] = fake_count
        results["Real Frames"] = real_count
        results["Fake Percentage"] = round(fake_percentage, 2)
        results["Final Video Prediction"] = "Fake" if fake_percentage > 50 else "Real"
        results["Confidence Score"] = round(abs(50 - fake_percentage) / 50, 2)
        
        return results

    except Exception as e:
        return {"Error": f"Error analyzing video: {str(e)}"}

# Metadata analysis
def check_metadata(img_path):
    try:
        img = Image.open(img_path)
        exif_data = img._getexif()
        if not exif_data:
            return "Fake (missing metadata)"
        metadata = {TAGS.get(tag): value for tag, value in exif_data.items() if tag in TAGS}
        return "Real (metadata present)" if metadata else "Fake (missing metadata)"
    except Exception as e:
        return f"Error analyzing metadata: {str(e)}"

# Artifact density analysis
def analyze_artifacts(img_path):
    try:
        img = cv2.imread(img_path)
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        laplacian = cv2.Laplacian(img_gray, cv2.CV_64F)
        mean_var = np.mean(np.var(laplacian))
        return "Fake (high artifact density)" if mean_var > 10 else "Real"
    except Exception as e:
        return f"Error analyzing artifacts: {str(e)}"

# Noise pattern detection
def detect_noise_patterns(img_path):
    try:
        img = cv2.imread(img_path)
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        noise_std = np.std(img_gray)
        return "Fake (unnatural noise patterns)" if noise_std < 5 else "Real"
    except Exception as e:
        return f"Error analyzing noise patterns: {str(e)}"

# Symmetry analysis
def calculate_symmetry(img_path):
    try:
        img = cv2.imread(img_path)
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        img_flipped_v = cv2.flip(img_gray, 1)
        img_flipped_h = cv2.flip(img_gray, 0)
        vertical_symmetry = 1 - np.mean(np.abs(img_gray - img_flipped_v)) / 255
        horizontal_symmetry = 1 - np.mean(np.abs(img_gray - img_flipped_h)) / 255
        return {
            "Vertical Symmetry": round(vertical_symmetry, 2),
            "Horizontal Symmetry": round(horizontal_symmetry, 2)
        }
    except Exception as e:
        return {"Error": str(e)}

# Combine all methods
def combined_prediction(img_path):
    results = {}
    cnn_prediction = predict_image(img_path)
    results["CNN Prediction"] = cnn_prediction
    cnn_score = 1 if cnn_prediction == "Fake" else 0
    metadata_result = check_metadata(img_path)
    results["Metadata Analysis"] = metadata_result
    metadata_score = 1 if "Fake" in metadata_result else 0
    artifact_result = analyze_artifacts(img_path)
    results["Artifact Analysis"] = artifact_result
    artifact_score = 1 if "Fake" in artifact_result else 0
    noise_result = detect_noise_patterns(img_path)
    results["Noise Pattern Analysis"] = noise_result
    noise_score = 1 if "Fake" in noise_result else 0
    symmetry_results = calculate_symmetry(img_path)
    results["Symmetry Analysis"] = symmetry_results
    vertical_symmetry = symmetry_results.get("Vertical Symmetry", 0)
    horizontal_symmetry = symmetry_results.get("Horizontal Symmetry", 0)
    symmetry_score = 0
    if vertical_symmetry != "Unknown" and horizontal_symmetry != "Unknown":
        if vertical_symmetry > 0.9 or horizontal_symmetry > 0.9:
            symmetry_score = 1
    total_score = (cnn_score * 0.4 + metadata_score * 0.1 +
                   artifact_score * 0.15 + noise_score * 0.15 +
                   symmetry_score * 0.2)
    results["Final Prediction"] = "Fake" if total_score > 0.5 else "Real"
    results["Confidence Score"] = round(total_score, 2)
    return results

# Main function
if __name__ == "__main__":
    test_image_path = "C:/Users/ramya/OneDrive - iiit-b/Desktop/test1.jpg"
    if os.path.exists(test_image_path):
        final_results = combined_prediction(test_image_path)
        print("\nCombined Prediction Results:")
        for key, value in final_results.items():
            if isinstance(value, dict):
                print(f"{key}:")
                for sub_key, sub_value in value.items():
                    print(f"  {sub_key}: {sub_value}")
            else:
                print(f"{key}: {value}")

# if __name__ == "__main__":
#     # Test video
#     test_video_path = "path/to/your/video.mp4"
#     if os.path.exists(test_video_path):
#         video_results = predict_video(test_video_path)
#         print("\nVideo Analysis Results:")
#         for key, value in video_results.items():
#             print(f"{key}: {value}")
